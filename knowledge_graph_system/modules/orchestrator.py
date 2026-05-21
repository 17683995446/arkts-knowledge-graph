"""
主控制模块 (orchestrator)

职责：
1. 协调所有模块的工作
2. 处理文件变更事件流
3. 管理增量更新流程
4. 提供系统级API

第一性原理：
- 事件驱动：模块间通过事件通信，松耦合
- 流水线处理：文件变更 -> 解析 -> 分析 -> 存储 -> 通知
- 错误隔离：单个文件处理失败不影响其他文件
"""

import hashlib
import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Callable, Any, Set
from concurrent.futures import ThreadPoolExecutor

# 导入其他模块
from file_watcher import FileWatcher, FileChangeEvent
from arkts_parser import ArkTSParser, ParseResult
from sqlite_storage import SQLiteStorage
from llm_analyzer import LLMAnalyzer, LLMConfig
from visualizer_server import VisualizerServer

logger = logging.getLogger("orchestrator")


# 需要跳过的目录名（与file_watcher保持一致）
SKIP_DIRECTORY_NAMES: Set[str] = {
    'node_modules', '.git', '.hg', '.svn', 'build', 'dist',
    '.gradle', '.idea', '.vscode', '__pycache__', '.cache',
    'oh_modules', 'ohpm', '.preview', 'entry_modules'
}


@dataclass
class SystemConfig:
    """系统配置"""
    # 文件监控
    watch_paths: List[str]
    file_extensions: set = None
    debounce_ms: int = 1000

    # 数据库
    db_path: str = "knowledge_graph.db"

    # LLM
    llm_api_key: str = ""
    llm_model: str = "Qwen/Qwen2.5-7B-Instruct"
    llm_enabled: bool = True

    # 可视化
    visualizer_host: str = "0.0.0.0"
    visualizer_port: int = 8080
    visualizer_enabled: bool = True

    # 性能
    max_workers: int = 4
    batch_size: int = 10

    # 额外的跳过目录
    extra_skip_dirs: Set[str] = field(default_factory=set)

    def __post_init__(self):
        if self.file_extensions is None:
            self.file_extensions = {'.ets', '.ts', '.js'}


class EventBus:
    """
    事件总线 - 实现模块间的松耦合通信
    """

    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}
        self._lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            if event_type not in self._subscribers:
                self._subscribers[event_type] = []
            self._subscribers[event_type].append(callback)

    def unsubscribe(self, event_type: str, callback: Callable) -> None:
        with self._lock:
            if event_type in self._subscribers:
                self._subscribers[event_type] = [
                    cb for cb in self._subscribers[event_type]
                    if cb != callback
                ]

    def publish(self, event_type: str, data: Any) -> None:
        with self._lock:
            callbacks = self._subscribers.get(event_type, []).copy()
        for callback in callbacks:
            try:
                callback(data)
            except Exception as e:
                logger.error("事件处理失败: %s", e)


class Orchestrator:
    """
    系统主控制器

    核心流程：
    1. 文件监控模块检测变更
    2. 防抖处理后触发事件
    3. 指纹比对确认内容变化
    4. 解析模块提取实体和关系
    5. 存储模块执行增量更新
    6. LLM模块异步分析（可选）
    7. 可视化模块推送通知
    """

    def __init__(self, config: SystemConfig):
        self.config = config
        self.event_bus = EventBus()

        # 初始化模块
        self.storage = SQLiteStorage(config.db_path)
        self.parser = ArkTSParser()
        self.watcher: Optional[FileWatcher] = None
        self.visualizer: Optional[VisualizerServer] = None
        self.llm_analyzer: Optional[LLMAnalyzer] = None

        # 线程池（用于LLM分析和文件处理）
        self._executor = ThreadPoolExecutor(max_workers=config.max_workers)

        # 用于从非异步线程安全地通知可视化层
        self._visualizer_loop = None
        self._visualizer_thread: Optional[threading.Thread] = None
        self._uvicorn_server = None

        # 状态
        self._is_running = False
        self._stop_event = threading.Event()

        # 修复：统计使用线程锁保护（watchdog线程和扫描线程池并发写入）
        self._stats_lock = threading.Lock()
        self.stats = {
            'files_processed': 0,
            'files_failed': 0,
            'total_entities': 0,
            'total_relations': 0,
            'start_time': None
        }

    # ------------------------------------------------------------------
    # 模块初始化
    # ------------------------------------------------------------------

    def _init_modules(self) -> None:
        logger.info("初始化模块...")

        self.watcher = FileWatcher(
            watch_paths=self.config.watch_paths,
            callback=self._on_file_change,
            delay_ms=self.config.debounce_ms,
            file_extensions=self.config.file_extensions,
        )

        if self.config.visualizer_enabled:
            self.visualizer = VisualizerServer(
                storage=self.storage,
                host=self.config.visualizer_host,
                port=self.config.visualizer_port,
            )

        if self.config.llm_enabled and self.config.llm_api_key:
            llm_config = LLMConfig(
                api_key=self.config.llm_api_key,
                model=self.config.llm_model,
            )
            self.llm_analyzer = LLMAnalyzer(llm_config)

        logger.info("模块初始化完成")

    # ------------------------------------------------------------------
    # 核心：文件变更处理
    # ------------------------------------------------------------------

    def _on_file_change(self, event: FileChangeEvent) -> None:
        """文件变更处理器（由文件监控线程调用）"""
        file_path = event.file_path

        if event.change_type == 'deleted':
            self._handle_file_deleted(file_path)
            return

        # 修复：空字符串 "" 也是有效内容（文件被清空），不应跳过
        if event.content is None:
            return

        # 1. 计算指纹
        content_hash = hashlib.sha256(event.content.encode()).hexdigest()

        # 2. 检查是否真的变化（与file_watcher的指纹缓存双重校验）
        old_hash = self.storage.get_file_hash(file_path)
        if old_hash == content_hash:
            return

        logger.info("处理文件: %s", file_path)
        start_time = time.time()

        try:
            # 3. 解析代码
            parse_result = self.parser.parse(event.content, file_path)

            parse_time = time.time() - start_time
            logger.info("解析完成: %d 实体, %d 关系, 耗时 %.3fs",
                        len(parse_result.entities),
                        len(parse_result.relations),
                        parse_time)

            # 4. 存储数据（增量更新）
            stats = self.storage.update_file_data(file_path, parse_result, content_hash)

            store_time = time.time() - start_time - parse_time
            logger.info("存储完成: %s, 耗时 %.3fs", stats, store_time)

            # 5. 触发事件
            self.event_bus.publish('file_parsed', {
                'file_path': file_path,
                'parse_result': parse_result,
                'stats': stats,
            })

            # 6. 异步LLM分析（结果写入数据库）
            if self.llm_analyzer and parse_result.entities:
                self._executor.submit(
                    self._analyze_with_llm,
                    file_path,
                    parse_result.entities,
                )

            # 7. 通知可视化层（线程安全方式）
            self._notify_visualizer(file_path)

            # 更新统计（线程安全）
            with self._stats_lock:
                self.stats['files_processed'] += 1
                self.stats['total_entities'] += len(parse_result.entities)
                self.stats['total_relations'] += len(parse_result.relations)

            total_time = time.time() - start_time
            logger.info("文件处理完成: %s, 总耗时 %.3fs", file_path, total_time)

        except Exception as e:
            with self._stats_lock:
                self.stats['files_failed'] += 1
            logger.error("文件处理失败: %s, 错误: %s", file_path, e)
            self.storage.log_event('parse_error', file_path, str(e))

    def _notify_visualizer(self, file_path: str) -> None:
        """
        线程安全地通知可视化层更新。

        修复：原代码在非异步线程中调用 asyncio.create_task() 会崩溃。
        现在通过 asyncio.run_coroutine_threadsafe() 安全地调度。
        """
        if not self.visualizer:
            return
        try:
            loop = self._visualizer_loop
            if loop and loop.is_running():
                import asyncio
                asyncio.run_coroutine_threadsafe(
                    self.visualizer.broadcast_update(file_path),
                    loop,
                )
        except Exception as e:
            logger.debug("可视化通知失败(可忽略): %s", e)

    def _handle_file_deleted(self, file_path: str) -> None:
        """处理文件删除"""
        logger.info("文件删除: %s", file_path)
        self.storage.delete_file_data(file_path)
        self._notify_visualizer(file_path)

    # ------------------------------------------------------------------
    # LLM分析（结果写入数据库）
    # ------------------------------------------------------------------

    def _analyze_with_llm(self, file_path: str, entities: List[Any]) -> None:
        """
        使用LLM分析实体，并将结果写入数据库。

        修复：原代码计算了LLM结果但从未写入数据库。
        """
        if not self.llm_analyzer:
            return

        try:
            results = self.llm_analyzer.analyze_entities_batch(entities)

            updated_count = 0
            for idx, analysis_result in results.items():
                entity = entities[idx]
                rows = self.storage.update_entity_llm_data(
                    entity_name=entity.name,
                    file_path=file_path,
                    summary=analysis_result.summary,
                    tags=analysis_result.tags,
                )
                updated_count += rows

            logger.info("LLM分析完成: %s, 分析%d个, 更新%d行",
                        file_path, len(results), updated_count)

        except Exception as e:
            logger.error("LLM分析失败: %s, 错误: %s", file_path, e)

    # ------------------------------------------------------------------
    # 事件处理器（预留扩展点）
    # ------------------------------------------------------------------

    def _on_file_parsed(self, data: Dict) -> None:
        pass

    def _on_file_stored(self, data: Dict) -> None:
        pass

    # ------------------------------------------------------------------
    # 初始全量扫描
    # ------------------------------------------------------------------

    def _should_skip_path(self, path: Path) -> bool:
        """判断路径是否应该跳过"""
        parts = path.parts
        skip_dirs = SKIP_DIRECTORY_NAMES | self.config.extra_skip_dirs
        for part in parts:
            if part in skip_dirs:
                return True
            # 修复：只跳过以.开头的目录名（如 .git, .idea），不跳过文件名
            # 检查是否是目录（路径中间部分），而非文件名（最后一部分）
            # 通过检查 parts 中非最后一个元素来判断
        # 单独检查目录部分（排除文件名）
        dir_parts = path.parent.parts if path.parent != path else parts
        for part in dir_parts:
            if part.startswith('.') and part not in skip_dirs:
                return True
        return False

    def initial_scan(self) -> None:
        """
        初始全量扫描。

        修复：原代码不过滤 .git/node_modules 等目录，
        且串行处理效率低。现在过滤特殊目录并使用线程池并行处理。
        """
        logger.info("开始初始扫描...")
        start_time = time.time()

        all_files: List[Path] = []
        for watch_path in self.config.watch_paths:
            path = Path(watch_path)
            if not path.exists():
                continue
            for ext in self.config.file_extensions:
                for file_path in path.rglob(f'*{ext}'):
                    if not self._should_skip_path(file_path):
                        all_files.append(file_path)

        logger.info("发现 %d 个有效文件（已过滤特殊目录）", len(all_files))

        if not all_files:
            return

        processed = 0
        skipped = 0

        def process_single(fp: Path) -> bool:
            """处理单个文件，返回是否成功处理"""
            try:
                content = fp.read_text(encoding='utf-8', errors='replace')
                content_hash = hashlib.sha256(content.encode()).hexdigest()

                old_hash = self.storage.get_file_hash(str(fp))
                if old_hash == content_hash:
                    return False

                parse_result = self.parser.parse(content, str(fp))
                self.storage.update_file_data(str(fp), parse_result, content_hash)

                # 修复：初始扫描也需通知可视化层（否则初始数据不显示）
                self._notify_visualizer(str(fp))

                # 修复：初始扫描也需触发LLM分析（否则初始文件无语义标注）
                if self.llm_analyzer and parse_result.entities:
                    self._executor.submit(
                        self._analyze_with_llm,
                        str(fp),
                        parse_result.entities,
                    )

                return True
            except PermissionError:
                logger.warning("无权限读取: %s", fp)
            except Exception as e:
                logger.error("扫描失败: %s, 错误: %s", fp, e)
            return False

        # 使用线程池并行处理
        max_scan_workers = min(self.config.max_workers, 8)
        with ThreadPoolExecutor(max_workers=max_scan_workers) as scan_pool:
            futures = {scan_pool.submit(process_single, fp): fp for fp in all_files}
            for future in futures:
                try:
                    if future.result():
                        processed += 1
                    else:
                        skipped += 1
                except Exception:
                    with self._stats_lock:
                        self.stats['files_failed'] += 1

                if (processed + skipped) % 200 == 0:
                    logger.info("扫描进度: %d/%d", processed + skipped, len(all_files))

        elapsed = time.time() - start_time
        logger.info("初始扫描完成: 处理 %d 个文件, 跳过 %d 个, 耗时 %.1fs",
                    processed, skipped, elapsed)

    # ------------------------------------------------------------------
    # 启动 / 停止
    # ------------------------------------------------------------------

    def start(self) -> None:
        """启动系统"""
        if self._is_running:
            return

        print("\n" + "=" * 60)
        print("ArkTS Knowledge Graph System")
        print("=" * 60 + "\n")

        self._init_modules()
        self.initial_scan()
        self.watcher.start()

        # 启动可视化服务器（在独立线程中）
        if self.visualizer:
            self._start_visualizer()

        self._is_running = True
        self.stats['start_time'] = time.time()

        print("\n[orchestrator] 系统已启动")
        print("按 Ctrl+C 停止\n")

        try:
            while not self._stop_event.is_set():
                self._stop_event.wait(1.0)
        except KeyboardInterrupt:
            pass
        finally:
            self.stop()

    def _start_visualizer(self) -> None:
        """在独立线程中启动可视化服务器，支持优雅关闭"""
        import asyncio
        import uvicorn

        # 创建 uvicorn Server 实例以便后续可以优雅关闭
        config = uvicorn.Config(
            self.visualizer.app,
            host=self.config.visualizer_host,
            port=self.config.visualizer_port,
            log_level="warning",
        )
        self._uvicorn_server = uvicorn.Server(config)

        def run_visualizer():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            self._visualizer_loop = loop
            try:
                loop.run_until_complete(self._uvicorn_server.serve())
            except Exception as e:
                logger.error("可视化服务器异常: %s", e)
            finally:
                self._visualizer_loop = None
                try:
                    loop.close()
                except Exception:
                    pass

        self._visualizer_thread = threading.Thread(
            target=run_visualizer,
            daemon=True,
            name="visualizer",
        )
        self._visualizer_thread.start()
        print(f"[orchestrator] 可视化界面: http://localhost:{self.config.visualizer_port}")

    def stop(self) -> None:
        """停止系统"""
        if not self._is_running:
            return

        logger.info("正在停止系统...")
        self._is_running = False
        self._stop_event.set()

        # 优雅关闭 uvicorn
        if self._uvicorn_server and self._visualizer_loop:
            try:
                self._uvicorn_server.should_exit = True
            except Exception:
                pass

        if self.watcher:
            self.watcher.stop()

        # 修复 BUG-6: 先等待正在运行的任务完成，再关闭
        # 使用 wait=True 避免任务丢失，设置超时防止无限阻塞
        self._executor.shutdown(wait=True, cancel_futures=False)

        if self.llm_analyzer:
            self.llm_analyzer.close()

        self.storage.close()

        runtime = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
        print("\n" + "=" * 60)
        print("运行统计")
        print("=" * 60)
        print(f"运行时间: {runtime:.1f}s")
        print(f"处理文件: {self.stats['files_processed']}")
        print(f"失败文件: {self.stats['files_failed']}")
        print(f"总实体数: {self.stats['total_entities']}")
        print(f"总关系数: {self.stats['total_relations']}")
        print("=" * 60 + "\n")
        print("[orchestrator] 系统已停止")

    def get_status(self) -> Dict[str, Any]:
        # 修复：读取统计信息时加锁，避免读到不一致的中间状态
        with self._stats_lock:
            runtime = time.time() - self.stats['start_time'] if self.stats['start_time'] else 0
            return {
                'is_running': self._is_running,
                'runtime_seconds': runtime,
                'files_processed': self.stats['files_processed'],
                'files_failed': self.stats['files_failed'],
                'total_entities': self.stats['total_entities'],
                'total_relations': self.stats['total_relations'],
                'watcher_stats': self.watcher.get_stats() if self.watcher else {},
                'storage_stats': self.storage.get_statistics(),
            }


def create_default_orchestrator(
    watch_paths: List[str],
    api_key: str = "",
    db_path: str = "knowledge_graph.db",
) -> Orchestrator:
    config = SystemConfig(
        watch_paths=watch_paths,
        db_path=db_path,
        llm_api_key=api_key,
        llm_enabled=bool(api_key),
        visualizer_enabled=True,
    )
    return Orchestrator(config)
