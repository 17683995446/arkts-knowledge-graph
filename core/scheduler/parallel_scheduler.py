"""
多进程并行调度器
用满所有CPU核心，并行解析文件
"""
import os
import multiprocessing
import logging
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm

from config.global_settings import MAX_WORKERS, BATCH_SIZE

logger = logging.getLogger(__name__)


@dataclass
class WorkerResult:
    """单个工作进程的结果"""
    file_path: str = ""
    success: bool = True
    parse_time_ms: float = 0
    error: str = ""
    stats: Dict[str, int] = field(default_factory=dict)


@dataclass
class SchedulerResult:
    """调度器总结果"""
    total_files: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_time_ms: float = 0
    parse_time_ms: float = 0
    worker_results: List[WorkerResult] = field(default_factory=list)
    all_parse_results: List[Dict] = field(default_factory=list)


def _worker_parse_file(args: Tuple[str, str]) -> Dict[str, Any]:
    """
    工作进程函数：解析单个文件
    在独立进程中运行，避免GIL限制
    """
    file_path, project_root = args
    abs_path = os.path.join(project_root, file_path)

    try:
        # 在子进程中导入，避免fork后的状态问题
        from core.parser.arkts_file_parser import ArkTSFileParser

        with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
            source_code = f.read()

        parser = ArkTSFileParser()
        result = parser.parse_file(file_path, source_code)

        return {
            "success": True,
            "file_path": file_path,
            "parse_result": result.to_dict(),
            "parse_time_ms": result.parse_time_ms,
            "error": "",
        }
    except Exception as e:
        return {
            "success": False,
            "file_path": file_path,
            "parse_result": None,
            "parse_time_ms": 0,
            "error": str(e),
        }


class ParallelScheduler:
    """
    多进程并行调度器
    - 使用进程池并行解析文件
    - 自动适配CPU核心数
    - 提供进度条
    """

    def __init__(self, project_root: str, max_workers: int = MAX_WORKERS):
        self._project_root = os.path.abspath(project_root)
        self._max_workers = max_workers

    def parse_files(self, file_paths: List[str],
                    show_progress: bool = True) -> SchedulerResult:
        """
        并行解析多个文件
        Args:
            file_paths: 文件相对路径列表
            show_progress: 是否显示进度条
        Returns:
            SchedulerResult 包含所有解析结果
        """
        import time
        start_time = time.time()

        result = SchedulerResult(total_files=len(file_paths))

        if not file_paths:
            return result

        # 默认使用单进程模式（沙箱环境通常不支持多进程）
        # 用户可以通过环境变量 FORCE_MULTIPROCESS=1 强制启用多进程
        use_multiprocess = os.environ.get('FORCE_MULTIPROCESS', '').lower() in ('1', 'true', 'yes')
        
        if use_multiprocess:
            logger.info("启用多进程模式")
            return self._parse_multiprocess(file_paths, show_progress, start_time, result)
        else:
            logger.info("使用单进程模式")
            return self._parse_sequential(file_paths, show_progress, start_time, result)

    def _parse_multiprocess(self, file_paths, show_progress, start_time, result):
        """多进程并行解析"""
        import time as _time
        tasks = [(fp, self._project_root) for fp in file_paths]
        workers = min(self._max_workers, len(file_paths))
        logger.info(f"启动并行解析: {len(file_paths)} 个文件, {workers} 个工作进程")

        parse_results = []
        try:
            with ProcessPoolExecutor(max_workers=workers) as executor:
                futures = {
                    executor.submit(_worker_parse_file, task): task[0]
                    for task in tasks
                }

                iterator = as_completed(futures)
                if show_progress:
                    iterator = tqdm(iterator, total=len(file_paths), desc="解析文件", unit="文件", ncols=100)

                for future in iterator:
                    file_path = futures[future]
                    try:
                        data = future.result()
                        wr = WorkerResult(
                            file_path=file_path, success=data["success"],
                            parse_time_ms=data["parse_time_ms"],
                            error=data.get("error", ""),
                            stats=self._extract_stats(data.get("parse_result")),
                        )
                        result.worker_results.append(wr)
                        if data["success"] and data["parse_result"]:
                            parse_results.append(data["parse_result"])
                            result.success_count += 1
                        else:
                            result.failure_count += 1
                            if data.get("error"):
                                logger.warning(f"解析失败 {file_path}: {data['error']}")
                    except Exception as e:
                        result.failure_count += 1
                        result.worker_results.append(WorkerResult(file_path=file_path, success=False, error=str(e)))
                        logger.error(f"工作进程异常 {file_path}: {e}")
        except Exception as e:
            logger.error(f"多进程执行失败，回退到单进程: {e}")
            return self._parse_sequential(file_paths, show_progress, start_time, result)

        result.all_parse_results = parse_results
        # BUG-E修复: 多进程模式中time被重命名为_time，此处应使用_time.time()
        result.total_time_ms = (_time.time() - start_time) * 1000
        result.parse_time_ms = sum(wr.parse_time_ms for wr in result.worker_results)
        logger.info(f"并行解析完成: {result.success_count}/{result.total_files} 成功, 耗时 {result.total_time_ms/1000:.1f}s")
        return result

    def _parse_sequential(self, file_paths, show_progress, start_time, result):
        """单进程顺序解析（回退模式）"""
        import time
        from core.parser.arkts_file_parser import ArkTSFileParser
        logger.info(f"单进程解析: {len(file_paths)} 个文件")

        parse_results = []
        parser = ArkTSFileParser()

        iterator = file_paths
        if show_progress:
            iterator = tqdm(file_paths, desc="解析文件", unit="文件", ncols=100)

        for file_path in iterator:
            abs_path = os.path.join(self._project_root, file_path)
            try:
                with open(abs_path, 'r', encoding='utf-8', errors='ignore') as f:
                    source_code = f.read()
                pr = parser.parse_file(file_path, source_code)
                wr = WorkerResult(
                    file_path=file_path, success=True,
                    parse_time_ms=pr.parse_time_ms,
                    stats=self._extract_stats(pr.to_dict()),
                )
                result.worker_results.append(wr)
                result.success_count += 1
                parse_results.append(pr.to_dict())
            except Exception as e:
                result.failure_count += 1
                result.worker_results.append(WorkerResult(file_path=file_path, success=False, error=str(e)))
                logger.warning(f"解析失败 {file_path}: {e}")

        result.all_parse_results = parse_results
        result.total_time_ms = (time.time() - start_time) * 1000
        result.parse_time_ms = sum(wr.parse_time_ms for wr in result.worker_results)
        logger.info(f"单进程解析完成: {result.success_count}/{result.total_files} 成功, 耗时 {result.total_time_ms/1000:.1f}s")
        return result

    def _extract_stats(self, parse_result: Optional[Dict]) -> Dict[str, int]:
        """从解析结果中提取统计信息"""
        if not parse_result:
            return {}
        return {
            "classes": len(parse_result.get("classes", [])),
            "methods": len(parse_result.get("methods", [])),
            "properties": len(parse_result.get("properties", [])),
            "calls": len(parse_result.get("calls", [])),
            "imports": len(parse_result.get("imports", [])),
        }
