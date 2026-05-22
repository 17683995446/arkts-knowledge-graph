"""
构建编排器
协调扫描、解析、写入的完整构建流程
"""
import os
import sqlite3
import time
import logging
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

from core.scanner.project_scanner import ProjectScanner, ChangeDetector, ScannedFile
from core.scheduler.parallel_scheduler import ParallelScheduler, SchedulerResult
from core.database.connection_manager import get_connection_manager
from core.database.database_initializer import DatabaseInitializer
from core.database.batch_writer import BatchWriter
from core.database.schema_definitions import get_flag_constants

logger = logging.getLogger(__name__)
FLAGS = get_flag_constants()


@dataclass
class BuildReport:
    """构建报告"""
    build_mode: str = "full"           # full / incremental
    total_files_scanned: int = 0
    total_lines_scanned: int = 0
    files_changed: int = 0
    files_deleted: int = 0
    files_parsed: int = 0
    parse_success: int = 0
    parse_failure: int = 0
    classes_extracted: int = 0
    methods_extracted: int = 0
    properties_extracted: int = 0
    calls_extracted: int = 0
    imports_extracted: int = 0
    decorators_extracted: int = 0
    inheritance_extracted: int = 0
    namespaces_extracted: int = 0
    database_size_mb: float = 0
    scan_time_ms: float = 0
    parse_time_ms: float = 0
    write_time_ms: float = 0
    total_time_ms: float = 0
    error: str = ""


class BuildOrchestrator:
    """
    构建编排器
    协调完整的构建流程：
    1. 扫描项目 → 找出变更文件
    2. 多进程并行解析
    3. 批量写入数据库
    """

    def __init__(self, project_root: str):
        self._project_root = project_root
        self._scanner = ProjectScanner(project_root)
        self._change_detector = ChangeDetector()
        self._scheduler = ParallelScheduler(project_root)
        self._conn_mgr = get_connection_manager()
        self._db_initializer = DatabaseInitializer()
        self._bw = BatchWriter()
        self._last_stats = {}

    def full_build(self, show_progress: bool = True) -> BuildReport:
        """
        全量构建
        重建整个知识图谱数据库
        """
        logger.info(f"开始全量构建: {self._project_root}")
        start_time = time.time()

        report = BuildReport(build_mode="full")

        # 步骤1: 初始化数据库
        self._db_initializer.initialize_database(force_recreate=True)

        # 步骤2: 扫描所有文件
        scan_result = self._scanner.scan_all_files()
        report.total_files_scanned = scan_result.total_files
        report.total_lines_scanned = scan_result.total_lines
        report.scan_time_ms = scan_result.scan_time_ms
        report.files_changed = scan_result.total_files

        if not scan_result.files:
            report.error = "未找到任何源代码文件"
            report.total_time_ms = (time.time() - start_time) * 1000
            return report

        # 步骤3: 并行解析
        file_paths = [f.file_path for f in scan_result.files]
        sched_result = self._scheduler.parse_files(file_paths, show_progress)
        report.files_parsed = sched_result.total_files
        report.parse_success = sched_result.success_count
        report.parse_failure = sched_result.failure_count
        report.parse_time_ms = sched_result.parse_time_ms

        # 步骤4: 写入数据库
        write_start = time.time()
        self._write_parse_results(sched_result.all_parse_results, scan_result.files)
        report.write_time_ms = (time.time() - write_start) * 1000

        # 步骤5: 更新报告统计
        report.classes_extracted = self._last_stats.get("classes", 0)
        report.methods_extracted = self._last_stats.get("methods", 0)
        report.properties_extracted = self._last_stats.get("properties", 0)
        report.calls_extracted = self._last_stats.get("calls", 0)
        report.imports_extracted = self._last_stats.get("imports", 0)
        report.decorators_extracted = self._last_stats.get("decorators", 0)
        report.inheritance_extracted = self._last_stats.get("inheritance", 0)
        report.namespaces_extracted = self._last_stats.get("namespaces", 0)

        # 步骤6: 更新构建元数据
        self._update_build_metadata(report)

        # 汇总统计
        report.database_size_mb = round(self._conn_mgr.get_database_size_mb(), 2)
        report.total_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"全量构建完成: {report.total_time_ms/1000:.1f}s, "
            f"数据库 {report.database_size_mb}MB"
        )

        return report

    def incremental_build(self, show_progress: bool = True) -> BuildReport:
        """
        增量构建
        只解析变更的文件
        """
        logger.info(f"开始增量构建: {self._project_root}")
        start_time = time.time()

        report = BuildReport(build_mode="incremental")

        # 检查数据库是否就绪
        if not self._db_initializer.is_database_ready():
            logger.info("数据库未初始化，执行全量构建")
            return self.full_build(show_progress)

        # 步骤1: 加载已有哈希
        existing_hashes = self._load_existing_file_hashes()
        self._change_detector.load_existing_hashes(existing_hashes)

        # 步骤2: 扫描文件
        scan_result = self._scanner.scan_all_files()
        report.total_files_scanned = scan_result.total_files
        report.total_lines_scanned = scan_result.total_lines
        report.scan_time_ms = scan_result.scan_time_ms

        # 步骤3: 检测变更
        changed_files, deleted_files = self._change_detector.detect_changes(scan_result)
        report.files_changed = len(changed_files)
        report.files_deleted = len(deleted_files)

        if not changed_files and not deleted_files:
            logger.info("没有文件变更，跳过构建")
            report.total_time_ms = (time.time() - start_time) * 1000
            report.database_size_mb = round(self._conn_mgr.get_database_size_mb(), 2)
            return report

        # 步骤4: 删除已移除文件的数据
        if deleted_files:
            self._delete_files_data(deleted_files)

        # 步骤5: 并行解析变更文件
        if changed_files:
            file_paths = [f.file_path for f in changed_files]
            sched_result = self._scheduler.parse_files(file_paths, show_progress)
            report.files_parsed = sched_result.total_files
            report.parse_success = sched_result.success_count
            report.parse_failure = sched_result.failure_count
            report.parse_time_ms = sched_result.parse_time_ms

            # 步骤6: 写入数据库
            write_start = time.time()
            self._write_parse_results(sched_result.all_parse_results, changed_files)
            report.write_time_ms = (time.time() - write_start) * 1000

        # 步骤7: 更新哈希和元数据
        self._change_detector.update_hashes(changed_files)
        self._change_detector.remove_hashes(deleted_files)
        self._update_build_metadata(report)

        report.database_size_mb = round(self._conn_mgr.get_database_size_mb(), 2)
        report.total_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"增量构建完成: {report.files_changed} 个文件变更, "
            f"耗时 {report.total_time_ms/1000:.1f}s"
        )

        return report

    def _write_parse_results(self, parse_results: List[Dict],
                              scanned_files: List[ScannedFile]) -> None:
        """将解析结果批量写入数据库"""
        # 修复W/BUG-7: 事务跨连接失效 - 使用同一个连接执行 BEGIN/写入/COMMIT
        conn_mgr = get_connection_manager()
        conn = sqlite3.connect(conn_mgr._db_path)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        conn.execute("PRAGMA cache_size=-64000")
        conn.execute("PRAGMA temp_store=MEMORY")
        conn.execute("PRAGMA foreign_keys=ON")
        conn.row_factory = sqlite3.Row
        try:
            conn.execute("BEGIN")
            self._do_write_parse_results_with_conn(parse_results, scanned_files, conn)
            conn.execute("COMMIT")
        except Exception as e:
            logger.error(f"写入解析结果失败，执行ROLLBACK: {e}")
            try:
                conn.execute("ROLLBACK")
            except Exception:
                pass
            raise
        finally:
            conn.close()

    def _do_write_parse_results_with_conn(self, parse_results: List[Dict],
                              scanned_files: List[ScannedFile], conn) -> None:
        """实际执行写入解析结果（使用指定连接，在事务内）"""
        def execute_query(sql, params=()):
            cursor = conn.execute(sql, params)
            return [dict(row) for row in cursor.fetchall()]

        def execute_update(sql, params=()):
            cursor = conn.execute(sql, params)
            return cursor.rowcount

        def write_batch(table_name, records):
            """直接在指定连接上执行批量写入"""
            if not records:
                return []
            columns = list(records[0].keys())
            placeholders = ", ".join(["?"] * len(columns))
            col_names = ", ".join(columns)
            values = [tuple(r.get(c) for c in columns) for r in records]
            relation_tables = {'calls', 'components', 'imports', 'inheritance', 'build_metadata'}
            if table_name in relation_tables:
                sql = f"INSERT OR IGNORE INTO {table_name} ({col_names}) VALUES ({placeholders})"
                conn.executemany(sql, values)
                return []
            else:
                sql = f"INSERT OR REPLACE INTO {table_name} ({col_names}) VALUES ({placeholders}) RETURNING id"
                inserted_ids = []
                for vals in values:
                    cursor = conn.execute(sql, vals)
                    row = cursor.fetchone()
                    if row:
                        inserted_ids.append(row[0])
                return inserted_ids

        # 建立路径→文件信息的映射
        scanned_map = {f.file_path: f for f in scanned_files}

        # 建立名称→ID的映射（用于关联）
        file_id_map = {}      # path -> file_id
        class_id_map = {}     # (file_path, class_name) -> class_id
        method_id_map = {}    # (file_path, class_name, method_name) -> method_id

        # 批量写入缓冲区
        buffers = {}

        def add_record(table_name, record):
            if table_name not in buffers:
                buffers[table_name] = []
            buffers[table_name].append(record)

        def flush_table(table_name):
            if table_name not in buffers or not buffers[table_name]:
                return []
            records = buffers[table_name]
            buffers[table_name] = []
            return write_batch(table_name, records)

        def flush_all():
            for table_name in list(buffers.keys()):
                flush_table(table_name)

        # 1. 写入文件表
        # BUG-C修复: 增量构建时文件可能已存在，先删除旧记录避免UNIQUE约束冲突
        for pr in parse_results:
            file_path = pr["file_path"]
            execute_update("DELETE FROM files WHERE path = ?", (file_path,))

        for pr in parse_results:
            file_path = pr["file_path"]
            scanned = scanned_map.get(file_path)
            if not scanned:
                continue

            add_record("files", {
                "path": file_path,
                "hash": scanned.file_hash,
                "line_count": scanned.line_count,
                "language": "arkts",
                "last_scanned": time.time(),
            })
            file_id_map[file_path] = 0  # placeholder

        flush_table("files")

        # 获取实际分配的ID
        for pr in parse_results:
            file_path = pr["file_path"]
            rows = execute_query(
                "SELECT id FROM files WHERE path = ?", (file_path,)
            )
            if rows:
                file_id_map[file_path] = rows[0]["id"]

        # 2. 写入类表
        for pr in parse_results:
            file_path = pr["file_path"]
            file_id = file_id_map.get(file_path)
            if not file_id:
                continue

            for cls in pr.get("classes", []):
                add_record("classes", {
                    "name": cls["name"],
                    "file_id": file_id,
                    "start_line": cls.get("start_line", 0),
                    "end_line": cls.get("end_line", 0),
                    "flags": cls.get("flags", 0),
                    "doc_comment": cls.get("doc_comment", ""),
                })

        flush_table("classes")

        # 获取类ID映射
        for pr in parse_results:
            file_path = pr["file_path"]
            file_id = file_id_map.get(file_path)
            if not file_id:
                continue
            for cls in pr.get("classes", []):
                rows = execute_query(
                    "SELECT id FROM classes WHERE name = ? AND file_id = ?",
                    (cls["name"], file_id)
                )
                if rows:
                    class_id_map[(file_path, cls["name"])] = rows[0]["id"]

        # 3. 写入方法表
        for pr in parse_results:
            file_path = pr["file_path"]
            file_id = file_id_map.get(file_path)
            if not file_id:
                continue

            for method in pr.get("methods", []):
                class_name = method.get("class_name", "")
                class_id = class_id_map.get((file_path, class_name)) if class_name else None

                add_record("methods", {
                    "name": method["name"],
                    "class_id": class_id,
                    "file_id": file_id,
                    "start_line": method.get("start_line", 0),
                    "end_line": method.get("end_line", 0),
                    "flags": method.get("flags", 0),
                    "return_type": method.get("return_type", ""),
                    "parameters": method.get("parameters", ""),
                    "doc_comment": method.get("doc_comment", ""),
                })

        flush_table("methods")

        # 获取方法ID映射
        for pr in parse_results:
            file_path = pr["file_path"]
            file_id = file_id_map.get(file_path)
            if not file_id:
                continue
            for method in pr.get("methods", []):
                class_name = method.get("class_name", "")
                class_id = class_id_map.get((file_path, class_name)) if class_name else None
                rows = execute_query(
                    "SELECT id FROM methods WHERE name = ? AND file_id = ? AND class_id IS ?",
                    (method["name"], file_id, class_id)
                )
                if rows:
                    method_id_map[(file_path, class_name, method["name"])] = rows[0]["id"]

        # 4. 写入属性表
        for pr in parse_results:
            file_path = pr["file_path"]
            file_id = file_id_map.get(file_path)
            if not file_id:
                continue

            for prop in pr.get("properties", []):
                class_name = prop.get("class_name", "")
                class_id = class_id_map.get((file_path, class_name)) if class_name else None

                add_record("properties", {
                    "name": prop["name"],
                    "class_id": class_id,
                    "file_id": file_id,
                    "type_annotation": prop.get("type_annotation", ""),
                    "flags": prop.get("flags", 0),
                    "default_value": prop.get("default_value", ""),
                    "start_line": prop.get("start_line", 0),
                })

        flush_table("properties")

        # 5. 写入调用关系（需要解析方法名→ID）
        calls_written = 0
        for pr in parse_results:
            file_path = pr["file_path"]
            for call in pr.get("calls", []):
                caller_class = call.get("caller_class", "")
                callee_name = call.get("callee_name", "")

                caller_id = method_id_map.get((file_path, caller_class, call.get("caller_name", "")))

                # 尝试在被调用方文件中查找方法
                callee_id = method_id_map.get((file_path, call.get("callee_class", ""), callee_name))

                # BUG-58修复: 跨文件查找callee_id
                if not callee_id and callee_name:
                    for key, mid in method_id_map.items():
                        if key[2] == callee_name:
                            callee_id = mid
                            break

                if caller_id and callee_id:
                    add_record("calls", {
                        "caller_id": caller_id,
                        "callee_id": callee_id,
                        "call_type": call.get("call_type", 0),
                        "line_number": call.get("line_number", 0),
                    })
                    calls_written += 1

        flush_table("calls")

        # 6. 写入装饰器
        for pr in parse_results:
            file_path = pr["file_path"]
            for dec in pr.get("decorators", []):
                target_name = dec.get("target_name", "")
                target_type = dec.get("target_type", 0)
                target_id = None

                if target_type == 0:  # class
                    target_id = class_id_map.get((file_path, target_name))
                elif target_type == 1:  # method
                    # 查找方法ID
                    for key, mid in method_id_map.items():
                        if key[0] == file_path and key[2] == target_name:
                            target_id = mid
                            break

                if target_id:
                    add_record("decorators", {
                        "name": dec["name"],
                        "target_type": target_type,
                        "target_id": target_id,
                        "arguments": "",
                    })

        flush_table("decorators")

        # 7. 写入继承关系
        for pr in parse_results:
            file_path = pr["file_path"]
            for inh in pr.get("inheritance", []):
                child_id = class_id_map.get((file_path, inh.get("child_name", "")))
                parent_id = class_id_map.get((file_path, inh.get("parent_name", "")))
                # 也尝试在其他文件中查找父类
                if not parent_id:
                    for key, cid in class_id_map.items():
                        if key[1] == inh.get("parent_name", ""):
                            parent_id = cid
                            break
                if child_id and parent_id:
                    add_record("inheritance", {
                        "child_id": child_id,
                        "parent_id": parent_id,
                        "type": inh.get("type", 0),
                    })

        flush_table("inheritance")

        # BUG-B修复: 写入imports表（在写入namespaces之前）
        for pr in parse_results:
            file_path = pr["file_path"]
            source_file_id = file_id_map.get(file_path)
            if not source_file_id:
                continue
            for imp in pr.get("imports", []):
                import_path = imp.get("import_path", "")
                if not import_path:
                    continue
                # 通过import_path查找target_file_id
                # import_path可能是相对路径如 './B' 或 '../utils/Helper'
                # 提取文件名部分进行匹配
                import_basename = os.path.basename(import_path)
                # 优先精确匹配文件名
                target_rows = execute_query(
                    "SELECT id FROM files WHERE path LIKE ? ORDER BY LENGTH(path) ASC",
                    (f"%/{import_basename}",)
                )
                if not target_rows:
                    # 尝试仅匹配文件名（无路径前缀）
                    target_rows = execute_query(
                        "SELECT id FROM files WHERE path = ? OR path LIKE ?",
                        (import_path, f"%{import_basename}.ets")
                    )
                if not target_rows:
                    # 找不到目标文件则跳过
                    continue
                target_file_id = target_rows[0]["id"]
                add_record("imports", {
                    "source_file_id": source_file_id,
                    "target_file_id": target_file_id,
                    "import_path": import_path,
                    "is_default": 1 if imp.get("is_default") else 0,
                })

        flush_table("imports")

        # 8. 写入命名空间
        for pr in parse_results:
            file_path = pr["file_path"]
            file_id = file_id_map.get(file_path)
            if not file_id:
                continue
            for ns in pr.get("namespaces", []):
                add_record("namespaces", {
                    "name": ns.get("name", ""),
                    "file_id": file_id,
                    "start_line": ns.get("start_line", 0),
                    "end_line": ns.get("end_line", 0),
                })

        flush_all()

        # 更新报告统计
        total_classes = sum(len(pr.get("classes", [])) for pr in parse_results)
        total_methods = sum(len(pr.get("methods", [])) for pr in parse_results)
        total_props = sum(len(pr.get("properties", [])) for pr in parse_results)
        total_calls = sum(len(pr.get("calls", [])) for pr in parse_results)
        total_imports = sum(len(pr.get("imports", [])) for pr in parse_results)
        total_decs = sum(len(pr.get("decorators", [])) for pr in parse_results)
        total_inhs = sum(len(pr.get("inheritance", [])) for pr in parse_results)
        total_nss = sum(len(pr.get("namespaces", [])) for pr in parse_results)

        # 这些统计会通过引用写入到report中
        self._last_stats = {
            "classes": total_classes,
            "methods": total_methods,
            "properties": total_props,
            "calls": total_calls,
            "imports": total_imports,
            "decorators": total_decs,
            "inheritance": total_inhs,
            "namespaces": total_nss,
        }

    def _delete_files_data(self, file_paths: List[str]) -> None:
        """删除指定文件的所有关联数据"""
        for path in file_paths:
            rows = self._conn_mgr.execute_query(
                "SELECT id FROM files WHERE path = ?", (path,)
            )
            if rows:
                file_id = rows[0]["id"]

                # 批量删除关联数据
                method_ids = [r["id"] for r in self._conn_mgr.execute_query(
                    "SELECT id FROM methods WHERE file_id = ?", (file_id,)
                )]
                class_ids = [r["id"] for r in self._conn_mgr.execute_query(
                    "SELECT id FROM classes WHERE file_id = ?", (file_id,)
                )]

                # 使用 IN 批量删除
                if method_ids:
                    placeholders = ",".join(["?"] * len(method_ids))
                    self._conn_mgr.execute_update(
                        f"DELETE FROM calls WHERE caller_id IN ({placeholders})",
                        tuple(method_ids)
                    )
                    self._conn_mgr.execute_update(
                        f"DELETE FROM calls WHERE callee_id IN ({placeholders})",
                        tuple(method_ids)
                    )
                    self._conn_mgr.execute_update(
                        f"DELETE FROM decorators WHERE target_id IN ({placeholders}) AND target_type = 1",
                        tuple(method_ids)
                    )

                if class_ids:
                    placeholders = ",".join(["?"] * len(class_ids))
                    self._conn_mgr.execute_update(
                        f"DELETE FROM decorators WHERE target_id IN ({placeholders}) AND target_type = 0",
                        tuple(class_ids)
                    )
                    self._conn_mgr.execute_update(
                        f"DELETE FROM inheritance WHERE child_id IN ({placeholders})",
                        tuple(class_ids)
                    )
                    self._conn_mgr.execute_update(
                        f"DELETE FROM inheritance WHERE parent_id IN ({placeholders})",
                        tuple(class_ids)
                    )
                    self._conn_mgr.execute_update(
                        f"DELETE FROM components WHERE parent_id IN ({placeholders})",
                        tuple(class_ids)
                    )
                    self._conn_mgr.execute_update(
                        f"DELETE FROM components WHERE child_id IN ({placeholders})",
                        tuple(class_ids)
                    )

                self._conn_mgr.execute_update("DELETE FROM imports WHERE source_file_id = ?", (file_id,))
                self._conn_mgr.execute_update("DELETE FROM files WHERE id = ?", (file_id,))
                self._conn_mgr.execute_update("DELETE FROM classes WHERE file_id = ?", (file_id,))
                self._conn_mgr.execute_update("DELETE FROM methods WHERE file_id = ?", (file_id,))
                self._conn_mgr.execute_update("DELETE FROM properties WHERE file_id = ?", (file_id,))
                self._conn_mgr.execute_update("DELETE FROM namespaces WHERE file_id = ?", (file_id,))
                logger.debug(f"已删除文件数据: {path}")

    def _load_existing_file_hashes(self) -> Dict[str, bytes]:
        """从数据库加载已有文件哈希"""
        rows = self._conn_mgr.execute_query("SELECT path, hash FROM files")
        return {r["path"]: bytes(r["hash"]) if r["hash"] else b"" for r in rows}

    def _update_build_metadata(self, report: 'BuildReport') -> None:
        """更新构建元数据"""
        stats = getattr(self, '_last_stats', {})
        now = time.time()

        metadata = [
            ("last_build_time", str(now), now),
            ("build_mode", report.build_mode, now),
            ("total_files", str(report.total_files_scanned), now),
            ("total_lines", str(report.total_lines_scanned), now),
            ("classes_count", str(stats.get("classes", 0)), now),
            ("methods_count", str(stats.get("methods", 0)), now),
            ("properties_count", str(stats.get("properties", 0)), now),
            ("calls_count", str(stats.get("calls", 0)), now),
        ]

        with self._conn_mgr.get_connection() as conn:
            for key, value, ts in metadata:
                conn.execute(
                    "INSERT OR REPLACE INTO build_metadata (key, value, updated_at) VALUES (?, ?, ?)",
                    (key, value, ts)
                )


