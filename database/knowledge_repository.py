"""
Knowledge Repository Module

Provides data access layer for the knowledge graph database.
Implements CRUD operations and query methods.
"""

import sqlite3
import json
import hashlib
import logging
import re
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime
from contextlib import contextmanager

logger = logging.getLogger(__name__)

from core.entity_models import (
    Entity, FileEntity, ClassEntity, MethodEntity, PropertyEntity, Relation,
    EntityType, RelationType, SourceLocation, KnowledgeGraph
)
from database.schema_definitions import (
    CREATE_TABLES_SQL, CLEAR_ALL_DATA_SQL, GET_STATISTICS_SQL, FIND_ORPHANS_SQL
)


class KnowledgeRepository:
    """
    Repository for knowledge graph data persistence.
    
    Provides methods for storing and retrieving entities and relations
    from the SQLite database.
    """
    
    def __init__(self, db_path: str):
        """
        Initialize the repository.
        
        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._conn = None  # 事务连接
        self._in_transaction = False
        logger.debug("[DEBUG] [KnowledgeRepository] [__init__] 初始化仓库, db_path=%s", db_path)
        self._ensure_directory()
        self._initialize_schema()
        logger.debug("[DEBUG] [KnowledgeRepository] [__init__] 仓库初始化完成")
    
    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
    
    @contextmanager
    def _get_connection(self):
        """Get a database connection with proper configuration.
        
        If a transaction is active, returns the transaction connection.
        Otherwise, creates a new connection that is automatically closed.
        """
        if self._in_transaction and self._conn is not None:
            yield self._conn
            return
        conn = None
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            logger.debug("[DEBUG] [KnowledgeRepository] [_get_connection] 获取数据库连接: %s", self.db_path)
            yield conn
        except Exception:
            if conn is not None:
                conn.rollback()
            logger.error("[DEBUG] [KnowledgeRepository] [_get_connection] 数据库连接异常, 已回滚")
            raise
        finally:
            if conn is not None:
                conn.close()

    def begin_transaction(self):
        """开始事务"""
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("BEGIN")
        self._in_transaction = True
        logger.debug("[DEBUG] [KnowledgeRepository] [begin_transaction] 事务已开始")

    def commit_transaction(self):
        """提交事务"""
        if self._conn:
            self._conn.commit()
            self._conn.close()
            self._conn = None
            self._in_transaction = False
            logger.debug("[DEBUG] [KnowledgeRepository] [commit_transaction] 事务已提交")

    def rollback_transaction(self):
        """回滚事务"""
        if self._conn:
            self._conn.rollback()
            self._conn.close()
            self._conn = None
            self._in_transaction = False
            logger.debug("[DEBUG] [KnowledgeRepository] [rollback_transaction] 事务已回滚")
    
    def _initialize_schema(self) -> None:
        """Initialize the database schema."""
        with self._get_connection() as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
    
    def clear_all_data(self) -> None:
        """Clear all data from the database."""
        logger.debug("[DEBUG] [KnowledgeRepository] [clear_all_data] 开始清除所有数据")
        with self._get_connection() as conn:
            conn.executescript(CLEAR_ALL_DATA_SQL)
            conn.commit()
        logger.debug("[DEBUG] [KnowledgeRepository] [clear_all_data] 所有数据已清除")
    
    # File operations
    def save_file(self, file_entity: FileEntity) -> None:
        """Save or update a file entity."""
        logger.debug("[DEBUG] [KnowledgeRepository] [save_file] 保存文件实体: id=%s, name=%s, path=%s",
                     file_entity.id, file_entity.name, file_entity.relative_path)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO files 
                (id, name, relative_path, absolute_path, line_count, last_modified, file_hash)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                file_entity.id,
                file_entity.name,
                file_entity.relative_path,
                file_entity.absolute_path,
                file_entity.metadata.get('line_count', 0),
                file_entity.metadata.get('last_modified'),
                file_entity.metadata.get('file_hash')
            ))
            conn.commit()
    
    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get a file by ID."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_file] 查询文件: file_id=%s", file_id)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE id = ?", (file_id,)
            ).fetchone()
            result = dict(row) if row else None
            logger.debug("[DEBUG] [KnowledgeRepository] [get_file] 查询结果: %s", 'found' if result else 'not found')
            return result
    
    def get_all_files(self) -> List[Dict[str, Any]]:
        """Get all files."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_all_files] 查询所有文件")
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM files ORDER BY relative_path").fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_all_files] 查询到 %d 个文件", len(result))
            return result
    
    # Class operations
    def save_class(self, class_entity: ClassEntity) -> None:
        """Save or update a class entity."""
        logger.debug("[DEBUG] [KnowledgeRepository] [save_class] 保存类实体: id=%s, name=%s, file_id=%s, is_component=%s",
                     class_entity.id, class_entity.name, class_entity.file_id, class_entity.is_component)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO classes 
                (id, name, file_id, is_component, is_entry, is_exported, decorators, 
                 parent_class, implemented_interfaces, metadata, line_number, column_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                class_entity.id,
                class_entity.name,
                class_entity.file_id,
                class_entity.is_component,
                class_entity.is_entry,
                class_entity.is_exported,
                json.dumps(class_entity.decorators),
                class_entity.parent_class,
                json.dumps(class_entity.implemented_interfaces),
                json.dumps(class_entity.metadata),
                class_entity.location.line_number,
                class_entity.location.column_number
            ))
            conn.commit()
    
    def get_class(self, class_id: str) -> Optional[Dict[str, Any]]:
        """Get a class by ID."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_class] 查询类: class_id=%s", class_id)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM classes WHERE id = ?", (class_id,)
            ).fetchone()
            result = dict(row) if row else None
            logger.debug("[DEBUG] [KnowledgeRepository] [get_class] 查询结果: %s", 'found' if result else 'not found')
            return result
    
    def get_classes_by_file(self, file_id: str) -> List[Dict[str, Any]]:
        """Get all classes in a file."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_classes_by_file] 查询文件中的类: file_id=%s", file_id)
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM classes WHERE file_id = ? ORDER BY line_number",
                (file_id,)
            ).fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_classes_by_file] 查询到 %d 个类", len(result))
            return result
    
    def get_all_classes(self) -> List[Dict[str, Any]]:
        """Get all classes."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_all_classes] 查询所有类")
        with self._get_connection() as conn:
            rows = conn.execute("SELECT * FROM classes ORDER BY name").fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_all_classes] 查询到 %d 个类", len(result))
            return result
    
    def get_components(self) -> List[Dict[str, Any]]:
        """Get all component classes."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_components] 查询所有组件")
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM classes WHERE is_component = 1 ORDER BY name"
            ).fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_components] 查询到 %d 个组件", len(result))
            return result
    
    # Method operations
    def save_method(self, method_entity: MethodEntity) -> None:
        """Save or update a method entity."""
        logger.debug("[DEBUG] [KnowledgeRepository] [save_method] 保存方法实体: id=%s, name=%s, class_id=%s, return_type=%s",
                     method_entity.id, method_entity.name, method_entity.class_id, method_entity.return_type)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO methods 
                (id, name, class_id, is_static, is_async, is_private, is_protected, 
                 is_public, return_type, parameters, line_number, column_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                method_entity.id,
                method_entity.name,
                method_entity.class_id,
                method_entity.is_static,
                method_entity.is_async,
                method_entity.is_private,
                method_entity.is_protected,
                method_entity.is_public,
                method_entity.return_type,
                json.dumps(method_entity.parameters),
                method_entity.location.line_number,
                method_entity.location.column_number
            ))
            conn.commit()
    
    def get_methods_by_class(self, class_id: str) -> List[Dict[str, Any]]:
        """Get all methods in a class."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_methods_by_class] 查询类的方法: class_id=%s", class_id)
        with self._get_connection() as conn:
            rows = conn.execute(
                "SELECT * FROM methods WHERE class_id = ? ORDER BY line_number",
                (class_id,)
            ).fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_methods_by_class] 查询到 %d 个方法", len(result))
            return result
    
    # Property operations
    def save_property(self, property_entity: PropertyEntity) -> None:
        """Save or update a property entity."""
        logger.debug("[DEBUG] [KnowledgeRepository] [save_property] 保存属性实体: id=%s, name=%s, class_id=%s, type=%s",
                     property_entity.id, property_entity.name, property_entity.class_id, property_entity.property_type)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO properties 
                (id, name, class_id, property_type, is_static, is_readonly, 
                 is_optional, default_value, metadata, line_number, column_number)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                property_entity.id,
                property_entity.name,
                property_entity.class_id,
                property_entity.property_type,
                property_entity.is_static,
                property_entity.is_readonly,
                property_entity.is_optional,
                property_entity.default_value,
                json.dumps(property_entity.metadata),
                property_entity.location.line_number,
                property_entity.location.column_number
            ))
            conn.commit()
    
    # Call operations
    def save_call(self, call_relation: Dict[str, Any]) -> None:
        """Save a method call relation."""
        call_id = hashlib.md5(
            f"{call_relation['caller_method_id']}->{call_relation.get('callee_method_id', call_relation.get('callee_name'))}".encode()
        ).hexdigest()
        logger.debug("[DEBUG] [KnowledgeRepository] [save_call] 保存调用关系: id=%s, caller=%s, callee=%s",
                     call_id[:8], call_relation.get('caller_method_id', '?')[:8],
                     call_relation.get('callee_name', call_relation.get('callee_method_id', '?')))
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO calls 
                (id, caller_method_id, caller_class_id, callee_method_id, 
                 callee_class_id, callee_name, line_number)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                call_id,
                call_relation['caller_method_id'],
                call_relation['caller_class_id'],
                call_relation.get('callee_method_id'),
                call_relation.get('callee_class_id'),
                call_relation.get('callee_name'),
                call_relation.get('line_number')
            ))
            conn.commit()
    
    def get_calls_by_method(self, method_id: str) -> List[Dict[str, Any]]:
        """Get all calls made by a method."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_calls_by_method] 查询方法的调用: method_id=%s", method_id)
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT c.*, m.name as callee_method_name, cls.name as callee_class_name
                FROM calls c
                LEFT JOIN methods m ON c.callee_method_id = m.id
                LEFT JOIN classes cls ON c.callee_class_id = cls.id
                WHERE c.caller_method_id = ?
            """, (method_id,)).fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_calls_by_method] 查询到 %d 个调用", len(result))
            return result
    
    def get_callers_of_method(self, method_id: str) -> List[Dict[str, Any]]:
        """Get all methods that call a given method."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_callers_of_method] 查询方法的调用者: method_id=%s", method_id)
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT c.*, m.name as caller_method_name, cls.name as caller_class_name
                FROM calls c
                LEFT JOIN methods m ON c.caller_method_id = m.id
                LEFT JOIN classes cls ON c.caller_class_id = cls.id
                WHERE c.callee_method_id = ?
            """, (method_id,)).fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_callers_of_method] 查询到 %d 个调用者", len(result))
            return result
    
    # Component operations
    def save_component_nesting(self, nesting: Dict[str, Any]) -> None:
        """Save a component nesting relation."""
        nesting_id = hashlib.md5(
            f"{nesting['parent_class_id']}->{nesting.get('child_class_id', nesting.get('child_name'))}".encode()
        ).hexdigest()
        logger.debug("[DEBUG] [KnowledgeRepository] [save_component_nesting] 保存组件嵌套: parent=%s, child=%s",
                     nesting.get('parent_class_id', '?')[:8], nesting.get('child_name', nesting.get('child_class_id', '?')))
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO components 
                (id, parent_class_id, child_class_id, child_name, build_method_id, line_number)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                nesting_id,
                nesting['parent_class_id'],
                nesting.get('child_class_id'),
                nesting.get('child_name'),
                nesting.get('build_method_id'),
                nesting.get('line_number')
            ))
            conn.commit()
    
    def get_child_components(self, parent_class_id: str) -> List[Dict[str, Any]]:
        """Get all child components of a parent component."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_child_components] 查询子组件: parent_class_id=%s", parent_class_id)
        with self._get_connection() as conn:
            rows = conn.execute("""
                SELECT c.*, cls.name as child_class_name
                FROM components c
                LEFT JOIN classes cls ON c.child_class_id = cls.id
                WHERE c.parent_class_id = ?
            """, (parent_class_id,)).fetchall()
            result = [dict(row) for row in rows]
            logger.debug("[DEBUG] [KnowledgeRepository] [get_child_components] 查询到 %d 个子组件", len(result))
            return result
    
    # Statistics
    def get_statistics(self) -> Dict[str, int]:
        """Get database statistics."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_statistics] 查询数据库统计")
        with self._get_connection() as conn:
            row = conn.execute(GET_STATISTICS_SQL).fetchone()
            if row:
                result = {
                    'file_count': row[0],
                    'class_count': row[1],
                    'method_count': row[2],
                    'property_count': row[3],
                    'call_count': row[4],
                    'component_count': row[5],
                    'inheritance_count': row[6],
                    'import_count': row[7],
                    'component_class_count': row[8],
                    'entry_class_count': row[9]
                }
                logger.debug("[DEBUG] [KnowledgeRepository] [get_statistics] 统计结果: files=%d, classes=%d, methods=%d, properties=%d",
                             row[0], row[1], row[2], row[3])
                return result
            logger.debug("[DEBUG] [KnowledgeRepository] [get_statistics] 未获取到统计数据")
            return {}
    
    def save_inheritance(self, child_class_id: str, parent_class_id: str, 
                         parent_name: str, relation_type: str) -> None:
        """Save an inheritance relationship."""
        inh_id = hashlib.md5(
            f"{child_class_id}-{parent_name}-{relation_type}".encode()
        ).hexdigest()[:16]
        logger.debug("[DEBUG] [KnowledgeRepository] [save_inheritance] 保存继承关系: child=%s, parent=%s, type=%s",
                     child_class_id[:8], parent_name, relation_type)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO inheritance 
                (id, child_class_id, parent_class_id, parent_name, relation_type)
                VALUES (?, ?, ?, ?, ?)
            """, (inh_id, child_class_id, parent_class_id, parent_name, relation_type))
            conn.commit()
    
    def save_import(self, source_file_id: str, import_path: str) -> None:
        """Save an import relationship."""
        imp_id = hashlib.md5(
            f"{source_file_id}-{import_path}".encode()
        ).hexdigest()[:16]
        logger.debug("[DEBUG] [KnowledgeRepository] [save_import] 保存导入关系: source=%s, import_path=%s",
                     source_file_id[:8], import_path)
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR IGNORE INTO imports 
                (id, source_file_id, import_path)
                VALUES (?, ?, ?)
            """, (imp_id, source_file_id, import_path))
            conn.commit()
    
    def delete_file_cascade(self, file_id: str) -> None:
        """Delete a file and all its related entities (cascade)."""
        logger.debug("[DEBUG] [KnowledgeRepository] [delete_file_cascade] 级联删除文件: file_id=%s", file_id)
        with self._get_connection() as conn:
            # 获取该文件下所有类的ID
            class_ids = [r[0] for r in conn.execute(
                "SELECT id FROM classes WHERE file_id = ?", (file_id,)
            ).fetchall()]
            
            logger.debug("[DEBUG] [KnowledgeRepository] [delete_file_cascade] 文件下有 %d 个类", len(class_ids))
            
            if class_ids:
                placeholders = ','.join(['?'] * len(class_ids))
                
                # 获取这些类下所有方法的ID
                method_ids = [r[0] for r in conn.execute(
                    f"SELECT id FROM methods WHERE class_id IN ({placeholders})", class_ids
                ).fetchall()]
                
                logger.debug("[DEBUG] [KnowledgeRepository] [delete_file_cascade] 类下有 %d 个方法", len(method_ids))
                
                # 删除与这些方法相关的调用关系
                if method_ids:
                    m_placeholders = ','.join(['?'] * len(method_ids))
                    conn.execute(
                        f"DELETE FROM calls WHERE caller_method_id IN ({m_placeholders}) OR callee_method_id IN ({m_placeholders})",
                        method_ids * 2
                    )
                    logger.debug("[DEBUG] [KnowledgeRepository] [delete_file_cascade] 已删除方法相关的调用关系")

                # 删除与这些类相关的调用关系（基于class_id）
                conn.execute(
                    f"DELETE FROM calls WHERE caller_class_id IN ({placeholders}) OR callee_class_id IN ({placeholders})",
                    class_ids * 2
                )
                
                # 删除与这些类相关的组件嵌套关系
                conn.execute(
                    f"DELETE FROM components WHERE parent_class_id IN ({placeholders}) OR child_class_id IN ({placeholders})",
                    class_ids * 2
                )
                
                # 删除与这些类相关的继承关系
                conn.execute(
                    f"DELETE FROM inheritance WHERE child_class_id IN ({placeholders}) OR parent_class_id IN ({placeholders})",
                    class_ids * 2
                )
                
                # 删除这些类下的方法
                conn.execute(
                    f"DELETE FROM methods WHERE class_id IN ({placeholders})", class_ids
                )
                
                # 删除这些类下的属性
                conn.execute(
                    f"DELETE FROM properties WHERE class_id IN ({placeholders})", class_ids
                )
                
                # 删除这些类
                conn.execute(
                    f"DELETE FROM classes WHERE file_id = ?", (file_id,)
                )
            
            # 删除与该文件相关的导入关系
            conn.execute("DELETE FROM imports WHERE source_file_id = ?", (file_id,))
            
            # 删除文件本身
            conn.execute("DELETE FROM files WHERE id = ?", (file_id,))
            conn.commit()
        logger.debug("[DEBUG] [KnowledgeRepository] [delete_file_cascade] 级联删除完成: file_id=%s", file_id)
    
    def get_file_by_path(self, relative_path: str) -> Optional[Dict[str, Any]]:
        """Get a file by its relative path."""
        logger.debug("[DEBUG] [KnowledgeRepository] [get_file_by_path] 按路径查询文件: relative_path=%s", relative_path)
        with self._get_connection() as conn:
            row = conn.execute(
                "SELECT * FROM files WHERE relative_path = ?", (relative_path,)
            ).fetchone()
            result = dict(row) if row else None
            logger.debug("[DEBUG] [KnowledgeRepository] [get_file_by_path] 查询结果: %s", 'found' if result else 'not found')
            return result
    
    # Query methods for LLM
    # 只允许执行的SQL操作关键字
    _READ_ONLY_PREFIXES = ('SELECT', 'EXPLAIN', 'PRAGMA', 'WITH')
    # 只匹配语句开头位置的写操作关键字，避免误拒 REPLACE() 等函数调用
    _WRITE_KEYWORDS = re.compile(
        r'^\s*(INSERT|UPDATE|DELETE|DROP|ALTER|CREATE|REPLACE\s+INTO|REPLACE\s+VIEW|ATTACH|DETACH|REINDEX)\b',
        re.IGNORECASE | re.MULTILINE
    )

    @staticmethod
    def _remove_string_literals(sql: str) -> str:
        """移除 SQL 中的字符串字面量，用于安全检查时避免误判字符串内容。"""
        # 先将转义的单引号替换为占位符，避免破坏匹配
        result = sql.replace("''", '\x00\x00')
        # 移除单引号字符串字面量
        result = re.sub(r"'[^']*'", "''", result)
        # 恢复转义的单引号
        result = result.replace('\x00\x00', "''")
        return result

    def execute_sql(self, sql: str, params: Tuple = ()) -> Dict[str, Any]:
        """
        Execute a read-only SQL query and return results.

        Only SELECT, EXPLAIN, PRAGMA, and WITH queries are allowed.
        Raises ValueError for any write operations or multi-statement injection.

        Returns:
            Dict with keys: 'results' (list of row dicts), 'columns' (list of column names),
            'row_count' (int)
        """
        logger.debug("[DEBUG] [KnowledgeRepository] [execute_sql] 执行SQL: %s (params=%s)", sql[:200], params)
        normalized = sql.strip().upper()
        first_word = normalized.split()[0] if normalized.split() else ''

        # 1. 检查第一个关键字是否为只读操作
        if first_word not in self._READ_ONLY_PREFIXES:
            logger.error("[DEBUG] [KnowledgeRepository] [execute_sql] 非只读SQL被拒绝: %s", normalized[:20])
            raise ValueError(
                f"Only read-only queries are allowed. "
                f"Query started with: {normalized[:20]}"
            )

        # 2. 二次检查：在移除字符串字面量后的 SQL 中检查写操作关键字
        #    只匹配语句开头位置，避免误拒 SELECT ... REPLACE(...) 等合法查询
        sql_for_check = self._remove_string_literals(sql)
        write_match = self._WRITE_KEYWORDS.search(sql_for_check)
        if write_match:
            logger.error("[DEBUG] [KnowledgeRepository] [execute_sql] SQL中包含写操作关键字: %s", write_match.group(1))
            raise ValueError(
                f"Write operation '{write_match.group(1)}' detected in read-only query"
            )

        # 3. 防止多语句注入：在移除字符串字面量后，检查分号后面是否有非空白字符
        #    允许以分号结尾的合法 SQL（如 SELECT name FROM classes LIMIT 5;）
        #    允许字符串字面量中包含分号（如 WHERE name LIKE '%test%;%'）
        stripped_for_check = sql_for_check.strip()
        if ';' in stripped_for_check:
            # 找到最后一个分号的位置
            last_semi_pos = stripped_for_check.rfind(';')
            after_semi = stripped_for_check[last_semi_pos + 1:]
            # 如果分号后面还有非空白字符，说明存在多语句
            if after_semi.strip():
                logger.error("[DEBUG] [KnowledgeRepository] [execute_sql] 多语句SQL被拒绝")
                raise ValueError(
                    "Multi-statement queries are not allowed for security reasons"
                )

        # 去除末尾分号后执行
        clean_sql = sql.strip().rstrip(';').strip()

        with self._get_connection() as conn:
            cursor = conn.execute(clean_sql, params)
            rows = cursor.fetchall()
            columns = [desc[0] for desc in cursor.description] if cursor.description else []
            result_list = [dict(row) for row in rows]
            result = {
                'results': result_list,
                'columns': columns,
                'row_count': len(result_list)
            }
            logger.debug("[DEBUG] [KnowledgeRepository] [execute_sql] SQL执行完成, 返回 %d 行", len(result_list))
            return result
    
    def get_schema_info(self) -> str:
        """Get database schema information for LLM context."""
        return """
Database Schema for ArkTS Knowledge Graph:

## Tables (use exact table names):

### files
- id (TEXT PRIMARY KEY)
- name (TEXT) - file name
- relative_path (TEXT) - relative path from project root
- absolute_path (TEXT) - full file path
- line_count (INTEGER)

### classes
- id (TEXT PRIMARY KEY)
- name (TEXT) - class or component name
- file_id (TEXT) - foreign key to files.id
- is_component (BOOLEAN) - 1 if @Component, 0 otherwise
- is_entry (BOOLEAN) - 1 if @Entry, 0 otherwise
- parent_class (TEXT) - parent class name

### methods
- id (TEXT PRIMARY KEY)
- name (TEXT) - method name
- class_id (TEXT) - foreign key to classes.id
- return_type (TEXT)

### properties
- id (TEXT PRIMARY KEY)
- name (TEXT) - property name
- class_id (TEXT) - foreign key to classes.id
- property_type (TEXT)

### inheritance
- id (TEXT PRIMARY KEY)
- child_class_id (TEXT) - foreign key to classes.id
- parent_class_id (TEXT) - foreign key to classes.id
- parent_name (TEXT) - parent class/interface name
- relation_type (TEXT) - 'extends' or 'implements'

### imports
- id (TEXT PRIMARY KEY)
- source_file_id (TEXT) - foreign key to files.id
- import_path (TEXT) - the import path string

### calls
- id (TEXT PRIMARY KEY)
- caller_method_id (TEXT) - foreign key to methods.id
- caller_class_id (TEXT) - foreign key to classes.id
- callee_method_id (TEXT) - foreign key to methods.id
- callee_class_id (TEXT) - foreign key to classes.id
- callee_name (TEXT) - e.g. "UserService.getUserById"

### components
- id (TEXT PRIMARY KEY)
- parent_class_id (TEXT) - foreign key to classes.id
- child_class_id (TEXT) - foreign key to classes.id
- child_name (TEXT) - child component name

## Example Queries (copy these patterns):

1. SELECT COUNT(*) as count FROM classes WHERE is_component = 1;

2. SELECT c.name as child_class, i.parent_name
   FROM classes c JOIN inheritance i ON c.id = i.child_class_id;

3. SELECT m.name FROM methods m
   JOIN classes c ON m.class_id = c.id
   WHERE c.name = 'ClassName';

4. SELECT parent.name, comp.child_name
   FROM components comp
   JOIN classes parent ON comp.parent_class_id = parent.id
   WHERE parent.name = 'ComponentName';

5. SELECT f.name, COUNT(c.id) as class_count
   FROM files f LEFT JOIN classes c ON f.id = c.file_id
   GROUP BY f.id;

6. SELECT caller_cls.name, caller_m.name, ca.callee_name
   FROM calls ca
   JOIN methods caller_m ON ca.caller_method_id = caller_m.id
   JOIN classes caller_cls ON caller_m.class_id = caller_cls.id;

RULES:
- Use exact table names: files, classes, methods, properties, inheritance, imports, calls, components
- Always use JOIN ... ON syntax, never comma joins
- Use single quotes for string values
- Boolean columns use 1/0 not true/false
"""
