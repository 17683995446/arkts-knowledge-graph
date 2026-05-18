"""
批量写入器模块
攒够BATCH_SIZE条再写一次硬盘（IO铁律实现）
"""
import logging
from typing import List, Dict, Any, Optional
from core.database.connection_manager import get_connection_manager
from config.global_settings import BATCH_SIZE

logger = logging.getLogger(__name__)


class BatchWriter:
    """
    批量写入器
    - 缓冲区攒够 BATCH_SIZE 条再执行一次 INSERT
    - 支持多种实体的批量写入
    - flush() 强制将缓冲区写入数据库
    """

    def __init__(self):
        self._buffers: Dict[str, List[Dict[str, Any]]] = {}
        self._total_written = 0
        self._total_flushes = 0

    def add_record(self, table_name: str, record: Dict[str, Any]) -> int:
        """
        向缓冲区添加一条记录
        如果缓冲区满了，自动flush
        返回当前缓冲区大小
        """
        if table_name not in self._buffers:
            self._buffers[table_name] = []

        self._buffers[table_name].append(record)

        if len(self._buffers[table_name]) >= BATCH_SIZE:
            self.flush_table(table_name)

        return len(self._buffers[table_name])

    def add_records(self, table_name: str, records: List[Dict[str, Any]]) -> int:
        """批量添加多条记录到缓冲区"""
        for record in records:
            self.add_record(table_name, record)
        return len(self._buffers.get(table_name, []))

    def flush_table(self, table_name: str) -> int:
        """将指定表的缓冲区写入数据库"""
        if table_name not in self._buffers or not self._buffers[table_name]:
            return 0

        records = self._buffers[table_name]
        count = len(records)

        try:
            self._write_batch(table_name, records)
            self._total_written += count
            self._total_flushes += 1
            logger.debug(f"批量写入 {table_name}: {count} 条记录")
        except Exception as e:
            logger.error(f"批量写入 {table_name} 失败: {e}")
            raise

        self._buffers[table_name] = []
        return count

    def flush_all(self) -> int:
        """将所有缓冲区写入数据库"""
        total = 0
        for table_name in list(self._buffers.keys()):
            total += self.flush_table(table_name)
        if total > 0:
            logger.info(f"全部flush完成: {total} 条记录, 累计flush {self._total_flushes} 次")
        return total

    def _write_batch(self, table_name: str, records: List[Dict[str, Any]]) -> None:
        """使用 executemany 高效批量写入"""
        if not records:
            return

        columns = list(records[0].keys())
        placeholders = ", ".join(["?"] * len(columns))
        col_names = ", ".join(columns)
        sql = f"INSERT OR IGNORE INTO {table_name} ({col_names}) VALUES ({placeholders})"

        values = [tuple(r.get(c) for c in columns) for r in records]

        conn_mgr = get_connection_manager()
        with conn_mgr.get_connection() as conn:
            conn.executemany(sql, values)

    def get_buffer_sizes(self) -> Dict[str, int]:
        """获取各表缓冲区大小"""
        return {k: len(v) for k, v in self._buffers.items()}

    def get_stats(self) -> Dict[str, Any]:
        """获取写入统计"""
        return {
            "total_written": self._total_written,
            "total_flushes": self._total_flushes,
            "current_buffers": self.get_buffer_sizes(),
        }

    def clear(self) -> None:
        """清空所有缓冲区（不写入）"""
        self._buffers.clear()
