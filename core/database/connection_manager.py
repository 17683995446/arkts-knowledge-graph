"""
数据库连接管理器
提供线程安全的数据库连接池和基础操作
"""
import sqlite3
import os
import threading
import logging
from contextlib import contextmanager
from config.global_settings import DATABASE_DIRECTORY, DATABASE_FULL_PATH

logger = logging.getLogger(__name__)


class DatabaseConnectionManager:
    """
    数据库连接管理器
    - 确保数据库目录存在
    - 提供上下文管理器连接
    - 支持WAL模式提升并发性能
    """

    def __init__(self, db_path: str = DATABASE_FULL_PATH):
        self._db_path = db_path
        self._initialized = False

    def initialize(self) -> None:
        """初始化数据库目录和文件"""
        os.makedirs(DATABASE_DIRECTORY, exist_ok=True)
        self._initialized = True
        logger.info(f"数据库路径已就绪: {self._db_path}")

    @contextmanager
    def get_connection(self) -> sqlite3.Connection:
        """
        获取数据库连接的上下文管理器
        使用WAL模式提升并发读写性能
        """
        if not self._initialized:
            self.initialize()

        conn = sqlite3.connect(self._db_path)
        conn.execute("PRAGMA journal_mode=WAL")       # WAL模式，读写不互斥
        conn.execute("PRAGMA synchronous=NORMAL")      # 平衡安全与速度
        conn.execute("PRAGMA cache_size=-64000")       # 64MB缓存
        conn.execute("PRAGMA temp_store=MEMORY")       # 临时表放内存
        conn.execute("PRAGMA foreign_keys=ON")         # 启用外键约束
        conn.row_factory = sqlite3.Row                 # 返回字典风格行

        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_script(self, ddl_statements: list) -> None:
        """执行DDL语句列表（建表、建索引）"""
        with self.get_connection() as conn:
            for stmt in ddl_statements:
                conn.execute(stmt)
        logger.info(f"已执行 {len(ddl_statements)} 条DDL语句")

    def execute_query(self, sql: str, params: tuple = ()) -> list:
        """执行查询并返回结果列表"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

    def execute_update(self, sql: str, params: tuple = ()) -> int:
        """执行更新并返回影响的行数"""
        with self.get_connection() as conn:
            cursor = conn.execute(sql, params)
            return cursor.rowcount

    def get_table_count(self, table_name: str) -> int:
        """获取表的行数"""
        # 安全校验：只允许字母、数字、下划线
        import re
        if not re.match(r'^[a-zA-Z_][a-zA-Z0-9_]*$', table_name):
            raise ValueError(f"非法表名: {table_name}")
        result = self.execute_query(f"SELECT COUNT(*) as cnt FROM {table_name}")
        return result[0]["cnt"] if result else 0

    def get_all_table_names(self) -> list:
        """获取所有表名"""
        result = self.execute_query(
            "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
        )
        return [r["name"] for r in result]

    def get_database_size_mb(self) -> float:
        """获取数据库文件大小（MB）"""
        if os.path.exists(self._db_path):
            return os.path.getsize(self._db_path) / (1024 * 1024)
        return 0.0


# 全局单例
_connection_manager = None
_connection_manager_lock = threading.Lock()


def get_connection_manager() -> DatabaseConnectionManager:
    """获取全局数据库连接管理器单例"""
    global _connection_manager
    if _connection_manager is None:
        with _connection_manager_lock:
            if _connection_manager is None:
                _connection_manager = DatabaseConnectionManager()
    return _connection_manager
