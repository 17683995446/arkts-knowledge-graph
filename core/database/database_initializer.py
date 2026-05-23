"""
数据库初始化器
负责建表、建索引、初始化元数据
"""
import time
import logging
import threading
from core.database.connection_manager import get_connection_manager
from core.database.schema_definitions import get_schema_ddl, get_index_ddl

logger = logging.getLogger(__name__)

# 全局初始化锁，防止并发初始化
_init_lock = threading.Lock()


class DatabaseInitializer:
    """数据库初始化器 - 确保数据库Schema正确"""

    def __init__(self):
        self._conn_mgr = get_connection_manager()

    def initialize_database(self, force_recreate: bool = False) -> None:
        """
        初始化数据库
        Args:
            force_recreate: 是否强制重建（删除旧数据库）
        """
        # 使用全局锁防止并发初始化
        with _init_lock:
            import os
            from config.global_settings import DATABASE_FULL_PATH

            if force_recreate and os.path.exists(DATABASE_FULL_PATH):
                os.remove(DATABASE_FULL_PATH)
                # 同时删除WAL和SHM文件
                for suffix in ['-wal', '-shm']:
                    wal_path = DATABASE_FULL_PATH + suffix
                    if os.path.exists(wal_path):
                        os.remove(wal_path)
                logger.warning("已删除旧数据库文件（含WAL/SHM），将重新创建")

            self._conn_mgr.initialize()

            # 建表
            schema_ddl = get_schema_ddl()
            self._conn_mgr.execute_script(schema_ddl)
            logger.info(f"已创建 {len(schema_ddl)} 张表")

            # 建索引
            index_ddl = get_index_ddl()
            self._conn_mgr.execute_script(index_ddl)
            logger.info(f"已创建 {len(index_ddl)} 个索引")

            # 初始化元数据
            self._init_metadata()

    def _init_metadata(self) -> None:
        """初始化构建元数据"""
        self._conn_mgr.execute_update(
            "INSERT OR REPLACE INTO build_metadata (key, value, updated_at) VALUES (?, ?, ?)",
            ("schema_version", "1.0.0", time.time())
        )

    def is_database_ready(self) -> bool:
        """检查数据库是否已初始化"""
        tables = self._conn_mgr.get_all_table_names()
        required = {"files", "classes", "methods", "properties", "calls",
                    "components", "imports", "decorators", "inheritance",
                    "namespaces", "build_metadata"}
        return required.issubset(set(tables))

    def get_database_stats(self) -> dict:
        """获取数据库统计信息"""
        stats = {}
        tables = self._conn_mgr.get_all_table_names()
        for table in tables:
            if table == "sqlite_sequence":
                continue
            stats[table] = self._conn_mgr.get_table_count(table)
        stats["database_size_mb"] = round(self._conn_mgr.get_database_size_mb(), 2)
        return stats
