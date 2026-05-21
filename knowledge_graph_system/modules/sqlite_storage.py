"""
SQLite存储模块 (sqlite_storage)

职责：
1. 管理SQLite数据库连接和表结构
2. 实现增量更新（删除旧数据 + 插入新数据）
3. 提供高效的查询接口
4. 维护文件指纹表

第一性原理：
- 文件级事务：一个文件的更新是一个原子操作
- 删了再加：更新=删除旧数据+插入新数据
- 索引优化：所有查询字段都有索引
"""

import json
import logging
import sqlite3
import threading
import time
from contextlib import contextmanager
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

from arkts_parser import CodeEntity, EntityRelation, FileDependency, ParseResult

logger = logging.getLogger(__name__)


class SQLiteStorage:
    """
    SQLite存储管理器
    
    核心设计：
    - 每个文件的所有数据操作在同一个事务中
    - 使用外键约束确保数据一致性
    - 预编译语句提高性能
    """
    
    def __init__(self, db_path: str = "knowledge_graph.db"):
        self.db_path = Path(db_path)
        self._local = threading.local()
        self._all_connections = {}  # tid -> connection，用于close()时清理所有线程连接
        self._connections_lock = threading.Lock()  # 保护_all_connections的并发访问
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取线程本地连接"""
        if not hasattr(self._local, 'connection') or self._local.connection is None:
            conn = sqlite3.connect(str(self.db_path), isolation_level=None, timeout=10.0)
            conn.row_factory = sqlite3.Row
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute("PRAGMA synchronous = NORMAL")
            self._local.connection = conn
            # 注册到全局连接表，以便close()时清理
            tid = threading.current_thread().ident
            with self._connections_lock:
                self._all_connections[tid] = conn
        return self._local.connection
    
    @contextmanager
    def _transaction(self):
        """事务上下文管理器"""
        conn = self._get_connection()
        try:
            conn.execute("BEGIN IMMEDIATE")
            yield conn
            conn.execute("COMMIT")
        except Exception as e:
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise e
    
    def _init_database(self) -> None:
        """初始化数据库表结构"""
        with self._transaction() as conn:
            # 文件指纹表 - 核心：判断文件是否真正变化
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_fingerprints (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE NOT NULL,
                    content_hash TEXT NOT NULL,
                    modified_at INTEGER NOT NULL,
                    last_parsed_at INTEGER,
                    entity_count INTEGER DEFAULT 0
                )
            """)
            
            # 代码实体表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS code_entities (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT NOT NULL,
                    entity_type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    signature TEXT,
                    start_line INTEGER,
                    end_line INTEGER,
                    code_snippet TEXT,
                    modifiers TEXT,  -- JSON数组
                    parent_name TEXT,
                    decorators TEXT,  -- JSON数组
                    llm_summary TEXT,
                    llm_tags TEXT,  -- JSON数组
                    created_at INTEGER DEFAULT (strftime('%s', 'now')),
                    updated_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # 实体关系表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS entity_relations (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL,
                    source_entity TEXT NOT NULL,
                    target_file TEXT NOT NULL,
                    target_entity TEXT NOT NULL,
                    relation_type TEXT NOT NULL,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # 文件依赖表
            conn.execute("""
                CREATE TABLE IF NOT EXISTS file_dependencies (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source_file TEXT NOT NULL,
                    target_file TEXT NOT NULL,
                    dependency_type TEXT NOT NULL,
                    imported_names TEXT,  -- JSON数组
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # 系统事件日志
            conn.execute("""
                CREATE TABLE IF NOT EXISTS system_events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_type TEXT NOT NULL,
                    file_path TEXT,
                    details TEXT,
                    duration_ms INTEGER,
                    created_at INTEGER DEFAULT (strftime('%s', 'now'))
                )
            """)
            
            # 创建索引
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_file 
                ON code_entities(file_path)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_type 
                ON code_entities(entity_type)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_entities_name 
                ON code_entities(name)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_relations_source 
                ON entity_relations(source_file, source_entity)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_relations_target 
                ON entity_relations(target_file, target_entity)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_deps_source 
                ON file_dependencies(source_file)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_deps_target 
                ON file_dependencies(target_file)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_events_type 
                ON system_events(event_type, created_at)
            """)
    
    # ==================== 文件指纹操作 ====================
    
    def get_file_hash(self, file_path: str) -> Optional[str]:
        """获取文件指纹"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT content_hash FROM file_fingerprints WHERE file_path = ?",
            (file_path,)
        )
        row = cursor.fetchone()
        return row['content_hash'] if row else None
    
    def update_file_hash(self, file_path: str, content_hash: str, entity_count: int = 0) -> None:
        """更新文件指纹"""
        with self._transaction() as conn:
            conn.execute("""
                INSERT INTO file_fingerprints (file_path, content_hash, modified_at, last_parsed_at, entity_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    modified_at = excluded.modified_at,
                    last_parsed_at = excluded.last_parsed_at,
                    entity_count = excluded.entity_count
            """, (file_path, content_hash, int(time.time()), int(time.time()), entity_count))
    
    def remove_file_hash(self, file_path: str) -> None:
        """删除文件指纹"""
        with self._transaction() as conn:
            conn.execute(
                "DELETE FROM file_fingerprints WHERE file_path = ?",
                (file_path,)
            )
    
    # ==================== 增量更新操作 ====================
    
    def update_file_data(self, file_path: str, parse_result: ParseResult, content_hash: str) -> Dict[str, int]:
        """
        更新文件的所有数据（核心方法）
        
        流程：
        1. 删除该文件的所有旧数据
        2. 插入新数据
        3. 更新文件指纹
        
        这是一个原子操作
        """
        start_time = time.time()
        stats = {'entities': 0, 'relations': 0, 'dependencies': 0}
        
        with self._transaction() as conn:
            # 1. 删除旧数据
            conn.execute("DELETE FROM code_entities WHERE file_path = ?", (file_path,))
            # 修复：同时删除以该文件为目标的实体关系（悬空边清理）
            conn.execute("DELETE FROM entity_relations WHERE source_file = ? OR target_file = ?", (file_path, file_path))
            conn.execute("DELETE FROM file_dependencies WHERE source_file = ? OR target_file = ?", (file_path, file_path))
            
            # 2. 插入新实体
            for entity in parse_result.entities:
                conn.execute("""
                    INSERT INTO code_entities 
                    (file_path, entity_type, name, signature, start_line, end_line, 
                     code_snippet, modifiers, parent_name, decorators)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entity.file_path,
                    entity.entity_type,
                    entity.name,
                    entity.signature,
                    entity.start_line,
                    entity.end_line,
                    entity.code_snippet,
                    json.dumps(entity.modifiers),
                    entity.parent_name,
                    json.dumps(entity.decorators)
                ))
                stats['entities'] += 1
            
            # 3. 插入新关系
            for relation in parse_result.relations:
                conn.execute("""
                    INSERT INTO entity_relations 
                    (source_file, source_entity, target_file, target_entity, relation_type)
                    VALUES (?, ?, ?, ?, ?)
                """, (
                    relation.source_file,
                    relation.source_entity,
                    relation.target_file,
                    relation.target_entity,
                    relation.relation_type
                ))
                stats['relations'] += 1
            
            # 4. 插入新依赖
            for dep in parse_result.dependencies:
                conn.execute("""
                    INSERT INTO file_dependencies 
                    (source_file, target_file, dependency_type, imported_names)
                    VALUES (?, ?, ?, ?)
                """, (
                    dep.source_file,
                    dep.target_file,
                    dep.dependency_type,
                    json.dumps(dep.imported_names)
                ))
                stats['dependencies'] += 1
            
            # 5. 更新文件指纹
            conn.execute("""
                INSERT INTO file_fingerprints (file_path, content_hash, modified_at, last_parsed_at, entity_count)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(file_path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    modified_at = excluded.modified_at,
                    last_parsed_at = excluded.last_parsed_at,
                    entity_count = excluded.entity_count
            """, (file_path, content_hash, int(time.time()), int(time.time()), stats['entities']))
        
        duration_ms = int((time.time() - start_time) * 1000)
        self.log_event('file_update', file_path, json.dumps(stats), duration_ms)
        
        return stats
    
    def delete_file_data(self, file_path: str) -> None:
        """删除文件的所有数据（包括指向该文件实体的关系）"""
        with self._transaction() as conn:
            conn.execute("DELETE FROM code_entities WHERE file_path = ?", (file_path,))
            # 同时删除以该文件为目标的关系（悬空边清理）
            conn.execute("DELETE FROM entity_relations WHERE source_file = ? OR target_file = ?", (file_path, file_path))
            conn.execute("DELETE FROM file_dependencies WHERE source_file = ? OR target_file = ?", (file_path, file_path))
            conn.execute("DELETE FROM file_fingerprints WHERE file_path = ?", (file_path,))
    
    # ==================== 查询操作 ====================
    
    def get_entities(self, file_path: Optional[str] = None, entity_type: Optional[str] = None) -> List[Dict]:
        """获取代码实体"""
        conn = self._get_connection()
        
        query = "SELECT * FROM code_entities WHERE 1=1"
        params = []
        
        if file_path:
            query += " AND file_path = ?"
            params.append(file_path)
        
        if entity_type:
            query += " AND entity_type = ?"
            params.append(entity_type)
        
        query += " ORDER BY file_path, start_line"
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_entity_by_name(self, name: str) -> Optional[Dict]:
        """根据名称获取实体"""
        conn = self._get_connection()
        cursor = conn.execute(
            "SELECT * FROM code_entities WHERE name = ? LIMIT 1",
            (name,)
        )
        row = cursor.fetchone()
        return self._row_to_dict(row) if row else None
    
    def get_relations(self, file_path: Optional[str] = None, entity_name: Optional[str] = None) -> List[Dict]:
        """获取实体关系"""
        conn = self._get_connection()
        
        query = "SELECT * FROM entity_relations WHERE 1=1"
        params = []
        
        if file_path:
            query += " AND source_file = ?"
            params.append(file_path)
        
        if entity_name:
            query += " AND (source_entity = ? OR target_entity = ?)"
            params.extend([entity_name, entity_name])
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_dependencies(self, file_path: Optional[str] = None) -> List[Dict]:
        """获取文件依赖"""
        conn = self._get_connection()
        
        query = "SELECT * FROM file_dependencies"
        params = []
        
        if file_path:
            query += " WHERE source_file = ?"
            params.append(file_path)
        
        cursor = conn.execute(query, params)
        rows = cursor.fetchall()
        
        return [self._row_to_dict(row) for row in rows]
    
    def get_dependency_graph(self) -> Dict[str, Any]:
        """
        获取完整的依赖图（用于可视化）
        
        Returns:
            {
                'nodes': [{'id': str, 'type': str, 'name': str, 'file_path': str}],
                'edges': [{'source': str, 'target': str, 'type': str}]
            }
        """
        conn = self._get_connection()
        
        # 获取所有实体作为节点
        cursor = conn.execute("""
            SELECT id, file_path, entity_type, name 
            FROM code_entities
        """)
        entity_rows = cursor.fetchall()
        
        nodes = []
        node_ids = {}
        
        for row in entity_rows:
            node_id = f"{row['file_path']}#{row['name']}"
            node_ids[row['id']] = node_id
            nodes.append({
                'id': node_id,
                'type': row['entity_type'],
                'name': row['name'],
                'file_path': row['file_path']
            })
        
        # 获取所有关系作为边
        cursor = conn.execute("""
            SELECT source_file, source_entity, target_file, target_entity, relation_type
            FROM entity_relations
        """)
        relation_rows = cursor.fetchall()
        
        edges = []
        # 修复：收集所有有效的节点ID，用于过滤悬空边
        valid_node_ids = set(node_ids.values())

        for row in relation_rows:
            source_id = f"{row['source_file']}#{row['source_entity']}"
            target_id = f"{row['target_file']}#{row['target_entity']}"
            # 修复：只添加两端节点都存在的边，避免悬空边
            if source_id in valid_node_ids and target_id in valid_node_ids:
                edges.append({
                    'source': source_id,
                    'target': target_id,
                    'type': row['relation_type']
                })
        
        # 获取文件依赖作为边
        # 修复：使用与节点一致的 ID 格式 "file_path#file" 表示文件级节点
        cursor = conn.execute("""
            SELECT source_file, target_file, dependency_type
            FROM file_dependencies
        """)
        dep_rows = cursor.fetchall()
        
        # 收集所有涉及的文件路径，创建文件级节点
        dep_files = set()
        for row in dep_rows:
            dep_files.add(row['source_file'])
            dep_files.add(row['target_file'])
        
        # 添加文件级节点（如果不存在）
        for fp in dep_files:
            file_node_id = fp  # 文件级节点使用路径作为 ID
            if file_node_id not in valid_node_ids:
                nodes.append({
                    'id': file_node_id,
                    'label': Path(fp).name,
                    'type': 'file',
                    'file_path': fp
                })
                valid_node_ids.add(file_node_id)
        
        for row in dep_rows:
            # 修复：验证两端节点都存在
            if row['source_file'] in valid_node_ids and row['target_file'] in valid_node_ids:
                edges.append({
                    'source': row['source_file'],
                    'target': row['target_file'],
                    'type': row['dependency_type']
                })
        
        return {'nodes': nodes, 'edges': edges}
    
    def get_file_graph(self, file_path: str) -> Dict[str, Any]:
        """获取单个文件的知识图谱"""
        conn = self._get_connection()
        
        # 获取文件中的实体
        cursor = conn.execute("""
            SELECT * FROM code_entities WHERE file_path = ?
        """, (file_path,))
        entity_rows = cursor.fetchall()
        
        entities = [self._row_to_dict(row) for row in entity_rows]
        
        # 获取与这些实体相关的关系
        entity_names = [e['name'] for e in entities]
        if entity_names:
            placeholders = ','.join('?' * len(entity_names))
            cursor = conn.execute(f"""
                SELECT * FROM entity_relations 
                WHERE source_entity IN ({placeholders})
                OR target_entity IN ({placeholders})
            """, entity_names + entity_names)
            relation_rows = cursor.fetchall()
            relations = [self._row_to_dict(row) for row in relation_rows]
        else:
            relations = []
        
        # 获取文件依赖
        cursor = conn.execute("""
            SELECT * FROM file_dependencies WHERE source_file = ?
        """, (file_path,))
        dep_rows = cursor.fetchall()
        dependencies = [self._row_to_dict(row) for row in dep_rows]
        
        return {
            'file_path': file_path,
            'entities': entities,
            'relations': relations,
            'dependencies': dependencies
        }
    
    def get_statistics(self) -> Dict[str, Any]:
        """获取统计信息"""
        conn = self._get_connection()
        
        stats = {}
        
        # 文件数量
        cursor = conn.execute("SELECT COUNT(*) as count FROM file_fingerprints")
        stats['total_files'] = cursor.fetchone()['count']
        
        # 实体数量
        cursor = conn.execute("SELECT COUNT(*) as count FROM code_entities")
        stats['total_entities'] = cursor.fetchone()['count']
        
        # 按类型统计实体
        cursor = conn.execute("""
            SELECT entity_type, COUNT(*) as count 
            FROM code_entities 
            GROUP BY entity_type
        """)
        stats['entities_by_type'] = {row['entity_type']: row['count'] for row in cursor.fetchall()}
        
        # 关系数量
        cursor = conn.execute("SELECT COUNT(*) as count FROM entity_relations")
        stats['total_relations'] = cursor.fetchone()['count']
        
        # 依赖数量
        cursor = conn.execute("SELECT COUNT(*) as count FROM file_dependencies")
        stats['total_dependencies'] = cursor.fetchone()['count']
        
        # 最近更新的文件
        cursor = conn.execute("""
            SELECT file_path, last_parsed_at, entity_count
            FROM file_fingerprints
            ORDER BY last_parsed_at DESC
            LIMIT 10
        """)
        stats['recent_files'] = [self._row_to_dict(row) for row in cursor.fetchall()]
        
        return stats
    
    def search_entities(self, query: str, limit: int = 20) -> List[Dict]:
        """搜索实体"""
        conn = self._get_connection()
        
        # 转义LIKE通配符，防止%和_被当作通配符
        escaped = query.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
        
        cursor = conn.execute("""
            SELECT * FROM code_entities
            WHERE name LIKE ? ESCAPE '\\' OR code_snippet LIKE ? ESCAPE '\\'
            ORDER BY 
                CASE WHEN name LIKE ? ESCAPE '\\' THEN 0 ELSE 1 END,
                name
            LIMIT ?
        """, (f'%{escaped}%', f'%{escaped}%', f'{escaped}%', limit))
        
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]
    
    # ==================== LLM更新操作 ====================
    
    def update_entity_llm_data(self, entity_name: str, file_path: str,
                                summary: str, tags: List[str]) -> int:
        """更新实体的LLM分析结果，返回受影响行数"""
        conn = self._get_connection()
        cursor = conn.execute("""
            UPDATE code_entities
            SET llm_summary = ?, llm_tags = ?, updated_at = ?
            WHERE name = ? AND file_path = ?
        """, (summary, json.dumps(tags), int(time.time()), entity_name, file_path))
        # autocommit模式下不需要显式COMMIT
        return cursor.rowcount
    
    # ==================== 日志操作 ====================
    
    def log_event(self, event_type: str, file_path: Optional[str] = None, 
                  details: Optional[str] = None, duration_ms: Optional[int] = None) -> None:
        """记录系统事件（独立事务，不影响主操作）"""
        try:
            conn = self._get_connection()
            conn.execute("""
                INSERT INTO system_events (event_type, file_path, details, duration_ms, created_at)
                VALUES (?, ?, ?, ?, ?)
            """, (event_type, file_path, details, duration_ms, int(time.time())))
            # autocommit模式下不需要显式COMMIT
        except sqlite3.OperationalError as e:
            # 修复 BUG-4: 记录关键错误但不影响主流程
            logger.warning(f"事件日志写入失败: {e}")
        except Exception:
            # 其他异常静默处理
            pass
    
    def get_recent_events(self, limit: int = 50) -> List[Dict]:
        """获取最近的事件日志"""
        conn = self._get_connection()
        cursor = conn.execute("""
            SELECT * FROM system_events
            ORDER BY created_at DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        return [self._row_to_dict(row) for row in rows]
    
    # ==================== 工具方法 ====================
    
    def _row_to_dict(self, row: sqlite3.Row) -> Dict:
        """将数据库行转换为字典"""
        result = dict(row)
        
        # 解析JSON字段
        json_fields = ['modifiers', 'decorators', 'llm_tags', 'imported_names']
        for field in json_fields:
            if field in result and result[field]:
                try:
                    result[field] = json.loads(result[field])
                except json.JSONDecodeError:
                    pass
        
        return result
    
    def close(self) -> None:
        """关闭所有线程的数据库连接"""
        # 修复 BUG-1: 先关闭连接再清理引用
        # 关闭所有已注册的线程连接
        with self._connections_lock:
            for tid, conn in list(self._all_connections.items()):
                try:
                    conn.close()
                except Exception:
                    pass
            self._all_connections.clear()
        
        # 关闭当前线程的连接
        if hasattr(self._local, 'connection') and self._local.connection:
            try:
                self._local.connection.close()
            except Exception:
                pass
            self._local.connection = None


# 简单测试
if __name__ == '__main__':
    import tempfile
    import os
    
    # 创建临时数据库
    db_path = tempfile.mktemp(suffix='.db')
    storage = SQLiteStorage(db_path)
    
    print("=== SQLite存储模块测试 ===\n")
    
    # 测试数据
    from arkts_parser import CodeEntity, EntityRelation, FileDependency, ParseResult
    
    test_result = ParseResult(
        entities=[
            CodeEntity(
                file_path='/test/file.ts',
                entity_type='class',
                name='UserService',
                signature='()',
                start_line=1,
                end_line=10,
                code_snippet='class UserService {}',
                modifiers=['export'],
                decorators=[]
            ),
            CodeEntity(
                file_path='/test/file.ts',
                entity_type='function',
                name='getUser',
                signature='(id: string)',
                start_line=12,
                end_line=15,
                code_snippet='function getUser(id: string) {}',
                modifiers=['export', 'async'],
                decorators=[]
            )
        ],
        relations=[
            EntityRelation(
                source_file='/test/file.ts',
                source_entity='getUser',
                target_file='/test/file.ts',
                target_entity='UserService',
                relation_type='calls'
            )
        ],
        dependencies=[
            FileDependency(
                source_file='/test/file.ts',
                target_file='/test/other.ts',
                dependency_type='import',
                imported_names=['OtherClass']
            )
        ]
    )
    
    # 测试更新
    print("1. 测试文件数据更新")
    stats = storage.update_file_data('/test/file.ts', test_result, 'abc123hash')
    print(f"   插入: {stats}")
    
    # 测试查询
    print("\n2. 测试实体查询")
    entities = storage.get_entities(file_path='/test/file.ts')
    for e in entities:
        print(f"   - {e['entity_type']}: {e['name']}")
    
    # 测试统计
    print("\n3. 测试统计信息")
    stats = storage.get_statistics()
    print(f"   文件数: {stats['total_files']}")
    print(f"   实体数: {stats['total_entities']}")
    print(f"   关系数: {stats['total_relations']}")
    
    # 测试依赖图
    print("\n4. 测试依赖图")
    graph = storage.get_dependency_graph()
    print(f"   节点数: {len(graph['nodes'])}")
    print(f"   边数: {len(graph['edges'])}")
    
    # 清理
    storage.close()
    os.unlink(db_path)
    
    print("\n=== 测试完成 ===")
