"""
数据库Schema迁移模块 (schema_migration)

职责：
1. 管理数据库schema版本
2. 执行schema升级迁移
3. 确保多线程/多进程并发安全
4. 支持迁移失败回滚

第一性原理：
- 版本控制：每个schema变更都有版本号
- 幂等性：重复执行迁移不会导致错误
- 原子性：迁移要么完全成功，要么完全回滚
- 兼容性：支持从任意版本升级到最新版本
"""

import sqlite3
import threading
import time
from pathlib import Path
from typing import List, Tuple, Optional, Callable
from dataclasses import dataclass
from contextlib import contextmanager


@dataclass
class Migration:
    """迁移定义"""
    version: int
    name: str
    description: str
    upgrade_sql: str
    downgrade_sql: Optional[str] = None


class SchemaMigration:
    """
    Schema迁移管理器
    
    核心设计：
    - 使用schema_version表记录当前版本
    - 每个迁移都是独立的事务
    - 支持并发安全（使用数据库锁）
    - 幂等操作（重复执行不会出错）
    """
    
    # 当前schema版本
    CURRENT_VERSION = 1
    
    # 迁移定义列表
    MIGRATIONS: List[Migration] = [
        Migration(
            version=1,
            name="initial_schema",
            description="初始schema版本",
            upgrade_sql="""
                CREATE TABLE IF NOT EXISTS schema_version (
                    version INTEGER PRIMARY KEY,
                    applied_at REAL NOT NULL,
                    migration_name TEXT,
                    description TEXT
                );
            """,
            downgrade_sql=None
        ),
    ]
    
    def __init__(self, db_path: str):
        self.db_path = Path(db_path)
        self._lock = threading.Lock()
    
    @contextmanager
    def _get_connection(self):
        """获取数据库连接上下文"""
        conn = sqlite3.connect(str(self.db_path), timeout=30.0)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()
    
    def get_current_version(self) -> int:
        """获取当前schema版本"""
        try:
            with self._get_connection() as conn:
                # 检查schema_version表是否存在
                cursor = conn.execute("""
                    SELECT name FROM sqlite_master 
                    WHERE type='table' AND name='schema_version'
                """)
                if not cursor.fetchone():
                    return 0  # 无版本表，视为版本0
                
                # 获取当前版本
                cursor = conn.execute("""
                    SELECT version FROM schema_version 
                    ORDER BY version DESC LIMIT 1
                """)
                row = cursor.fetchone()
                return row['version'] if row else 0
        except sqlite3.Error:
            return 0
    
    def migrate(self, target_version: Optional[int] = None) -> Tuple[bool, str]:
        """
        执行数据库迁移
        
        Args:
            target_version: 目标版本，None表示最新版本
            
        Returns:
            (成功标志, 消息)
        """
        if target_version is None:
            target_version = self.CURRENT_VERSION
        
        with self._lock:
            current_version = self.get_current_version()
            
            if current_version == target_version:
                return True, f"数据库已是最新版本 (v{current_version})"
            
            if current_version > target_version:
                return False, f"无法降级: 当前v{current_version} > 目标v{target_version}"
            
            # 执行升级
            try:
                for migration in self.MIGRATIONS:
                    if current_version < migration.version <= target_version:
                        success, msg = self._apply_migration(migration)
                        if not success:
                            return False, f"迁移到v{migration.version}失败: {msg}"
                        current_version = migration.version
                
                return True, f"成功迁移到v{current_version}"
            except Exception as e:
                return False, f"迁移失败: {e}"
    
    def _apply_migration(self, migration: Migration) -> Tuple[bool, str]:
        """
        应用单个迁移
        
        设计要点：
        1. 使用事务确保原子性
        2. 捕获所有异常以便回滚
        3. 记录迁移历史
        
        注意：executescript()会自动提交，所以需要使用isolation_level=None
        并手动控制事务
        """
        conn = None
        try:
            conn = sqlite3.connect(str(self.db_path), timeout=30.0, isolation_level=None)
            conn.row_factory = sqlite3.Row
            
            # 开始事务
            conn.execute("BEGIN IMMEDIATE")
            
            try:
                # 执行迁移SQL（注意：executescript会提交事务，需要拆分执行）
                # 将SQL按分号分割并逐个执行
                statements = [s.strip() for s in migration.upgrade_sql.split(';') if s.strip()]
                for stmt in statements:
                    conn.execute(stmt)
                
                # 更新版本记录
                conn.execute("""
                    INSERT OR REPLACE INTO schema_version 
                    (version, applied_at, migration_name, description)
                    VALUES (?, ?, ?, ?)
                """, (
                    migration.version,
                    time.time(),
                    migration.name,
                    migration.description
                ))
                
                conn.execute("COMMIT")
                return True, f"已应用迁移: {migration.name}"
                
            except Exception as e:
                try:
                    conn.execute("ROLLBACK")
                except sqlite3.OperationalError:
                    pass  # 没有活跃事务时忽略
                raise e
                
        except sqlite3.OperationalError as e:
            # 处理并发冲突
            if "database is locked" in str(e):
                return False, "数据库被锁定，可能有其他进程正在执行迁移"
            return False, str(e)
        except Exception as e:
            return False, str(e)
        finally:
            if conn:
                conn.close()
    
    def verify_schema(self) -> Tuple[bool, List[str]]:
        """
        验证当前schema完整性
        
        Returns:
            (是否有效, 错误列表)
        """
        errors = []
        
        try:
            with self._get_connection() as conn:
                # 检查必需的表
                required_tables = [
                    'schema_version',
                    'file_fingerprints',
                    'code_entities',
                    'entity_relations',
                    'file_dependencies',
                    'system_events'
                ]
                
                for table in required_tables:
                    cursor = conn.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='table' AND name=?
                    """, (table,))
                    if not cursor.fetchone():
                        errors.append(f"缺少表: {table}")
                
                # 检查必需的索引
                required_indexes = [
                    'idx_entities_file',
                    'idx_entities_type',
                    'idx_entities_name',
                    'idx_relations_source',
                    'idx_relations_target',
                    'idx_deps_source',
                    'idx_deps_target',
                    'idx_events_type'
                ]
                
                for index in required_indexes:
                    cursor = conn.execute("""
                        SELECT name FROM sqlite_master 
                        WHERE type='index' AND name=?
                    """, (index,))
                    if not cursor.fetchone():
                        errors.append(f"缺少索引: {index}")
                
                # 检查版本
                current_version = self.get_current_version()
                if current_version < self.CURRENT_VERSION:
                    errors.append(f"schema版本过旧: v{current_version} < v{self.CURRENT_VERSION}")
                
        except Exception as e:
            errors.append(f"验证失败: {e}")
        
        return len(errors) == 0, errors
    
    def create_backup(self) -> Optional[str]:
        """
        创建数据库备份
        
        Returns:
            备份文件路径，失败返回None
        """
        try:
            backup_path = str(self.db_path) + f".backup.{int(time.time())}.db"
            
            with self._get_connection() as source_conn:
                backup_conn = sqlite3.connect(backup_path)
                source_conn.backup(backup_conn)
                backup_conn.close()
            
            return backup_path
        except Exception:
            return None
    
    def get_migration_history(self) -> List[dict]:
        """获取迁移历史"""
        try:
            with self._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT version, applied_at, migration_name, description
                    FROM schema_version
                    ORDER BY version ASC
                """)
                return [dict(row) for row in cursor.fetchall()]
        except Exception:
            return []


def ensure_schema_up_to_date(db_path: str) -> Tuple[bool, str]:
    """
    确保数据库schema是最新的（便捷函数）
    
    在系统启动时调用，自动处理所有迁移
    """
    migrator = SchemaMigration(db_path)
    return migrator.migrate()


# 测试代码
if __name__ == '__main__':
    import tempfile
    import os
    
    print("=== Schema迁移模块测试 ===\n")
    
    # 创建临时数据库
    db_path = tempfile.mktemp(suffix='.db')
    
    try:
        migrator = SchemaMigration(db_path)
        
        # 测试1: 初始版本检测
        print("1. 测试初始版本检测")
        version = migrator.get_current_version()
        print(f"   当前版本: {version}")
        assert version == 0, "新数据库版本应为0"
        
        # 测试2: 执行迁移
        print("\n2. 测试执行迁移")
        success, msg = migrator.migrate()
        print(f"   结果: {msg}")
        assert success, "迁移应成功"
        
        version = migrator.get_current_version()
        print(f"   迁移后版本: {version}")
        assert version == SchemaMigration.CURRENT_VERSION
        
        # 测试3: 重复迁移（幂等性）
        print("\n3. 测试重复迁移（幂等性）")
        success, msg = migrator.migrate()
        print(f"   结果: {msg}")
        assert success, "重复迁移应成功"
        
        # 测试4: 迁移历史
        print("\n4. 测试迁移历史")
        history = migrator.get_migration_history()
        print(f"   历史记录数: {len(history)}")
        for h in history:
            print(f"   - v{h['version']}: {h['migration_name']}")
        
        print("\n=== 所有测试通过 ===")
        
    finally:
        if os.path.exists(db_path):
            os.unlink(db_path)
