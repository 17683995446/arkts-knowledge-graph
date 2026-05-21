"""
文件监控模块 (file_watcher)

职责：
1. 监听指定目录的文件变化
2. 防抖处理（停手1秒后触发）
3. 计算文件指纹（SHA256）
4. 只报告真正内容变化的文件

第一性原理：
- 文件修改事件可能频繁触发，必须防抖
- 文件时间变化不代表内容变化，必须用指纹判断
"""

import hashlib
import os
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List, Optional, Set

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileMovedEvent


@dataclass
class FileChangeEvent:
    """文件变更事件"""
    file_path: str
    content: Optional[str]
    change_type: str  # 'modified', 'created', 'deleted'
    timestamp: float


class FileFingerprintCache:
    """文件指纹缓存 - 用于判断内容是否真的变化"""
    
    def __init__(self):
        self._fingerprints: Dict[str, str] = {}
        self._lock = threading.RLock()
    
    def compute_hash(self, content: str) -> str:
        """计算内容SHA256哈希"""
        return hashlib.sha256(content.encode('utf-8')).hexdigest()
    
    def has_changed(self, file_path: str, content: str) -> bool:
        """检查文件内容是否真正变化"""
        new_hash = self.compute_hash(content)
        with self._lock:
            old_hash = self._fingerprints.get(file_path)
            if old_hash != new_hash:
                self._fingerprints[file_path] = new_hash
                return True
            return False
    
    def get_hash(self, file_path: str) -> Optional[str]:
        """获取文件指纹"""
        with self._lock:
            return self._fingerprints.get(file_path)
    
    def update_hash(self, file_path: str, content: str) -> None:
        """更新文件指纹"""
        with self._lock:
            self._fingerprints[file_path] = self.compute_hash(content)
    
    def remove_file(self, file_path: str) -> None:
        """删除文件指纹记录"""
        with self._lock:
            self._fingerprints.pop(file_path, None)


class DebouncedChangeHandler(FileSystemEventHandler):
    """
    防抖文件变化处理器
    
    核心逻辑：
    1. 收到文件变化事件后，启动定时器
    2. 如果在延迟时间内再次收到同一文件的事件，重置定时器
    3. 只有停手超过延迟时间后，才真正触发回调
    """
    
    def __init__(
        self,
        callback: Callable[[FileChangeEvent], None],
        delay_ms: int = 1000,
        file_extensions: Optional[Set[str]] = None,
        fingerprint_cache: Optional[FileFingerprintCache] = None
    ):
        self.callback = callback
        self.delay_ms = delay_ms
        self.file_extensions = file_extensions or {'.ets', '.ts', '.js'}
        self.fingerprint_cache = fingerprint_cache or FileFingerprintCache()

        # 待处理的定时器 {file_path: threading.Timer}
        self._pending_timers: Dict[str, threading.Timer] = {}
        self._timers_lock = threading.RLock()

        # 修复：添加 stopping 标志，防止 flush 和 observer.stop 之间的事件丢失
        self._stopping = False

        # 修复：flushed_paths 防止 flush 和 Timer 线程重复执行同一文件
        self._flushed_paths: Set[str] = set()
        self._flushed_lock = threading.Lock()

        # 修复：统计信息加锁保护
        self._stats_lock = threading.Lock()
        self.stats = {
            'events_received': 0,
            'events_triggered': 0,
            'events_filtered': 0
        }

        # 修复：大文件大小限制（5MB）
        self.MAX_FILE_SIZE = 5 * 1024 * 1024
    
    def _should_watch(self, file_path: str) -> bool:
        """判断是否应该监控此文件"""
        # 检查扩展名
        ext = Path(file_path).suffix.lower()
        if ext not in self.file_extensions:
            return False
        
        # 忽略隐藏文件
        if any(part.startswith('.') for part in Path(file_path).parts):
            return False
        
        # [修复] 使用路径分段匹配，避免子字符串误杀合法路径
        # 列表必须与 orchestrator.SKIP_DIRECTORY_NAMES 保持一致
        ignore_dirs = {
            'node_modules', '.git', '.hg', '.svn', 'build', 'dist',
            '.gradle', '.idea', '.vscode', '__pycache__', '.cache',
            'oh_modules', 'ohpm', '.preview', 'entry_modules'
        }
        if any(part in ignore_dirs for part in Path(file_path).parts):
            return False
        
        return True
    
    def _read_file_content(self, file_path: str) -> Optional[str]:
        """安全读取文件内容"""
        try:
            # 修复：检查文件大小，跳过超大文件
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                print(f"[file_watcher] 文件过大，跳过: {file_path} ({file_size} bytes)")
                return None
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            print(f"[file_watcher] 读取文件失败: {file_path}, 错误: {e}")
            return None
    
    def _process_change(self, file_path: str, change_type: str) -> None:
        """处理文件变化（在防抖后调用）"""
        # 修复：检查是否已被 flush 处理过，防止重复执行
        with self._flushed_lock:
            if file_path in self._flushed_paths:
                self._flushed_paths.discard(file_path)
                return
        try:
            if change_type == 'deleted':
                self.fingerprint_cache.remove_file(file_path)
                event = FileChangeEvent(
                    file_path=file_path,
                    content=None,
                    change_type=change_type,
                    timestamp=time.time()
                )
                self.callback(event)
                with self._stats_lock:
                    self.stats['events_triggered'] += 1
                return

            # 读取文件内容
            content = self._read_file_content(file_path)
            if content is None:
                # 文件不存在（可能已被重命名或删除），视为删除事件
                if not os.path.exists(file_path):
                    self.fingerprint_cache.remove_file(file_path)
                    event = FileChangeEvent(
                        file_path=file_path,
                        content=None,
                        change_type='deleted',
                        timestamp=time.time()
                    )
                    self.callback(event)
                    with self._stats_lock:
                        self.stats['events_triggered'] += 1
                return

            # 检查内容是否真的变化（指纹比对）
            if not self.fingerprint_cache.has_changed(file_path, content):
                with self._stats_lock:
                    self.stats['events_filtered'] += 1
                return  # 内容没变，跳过

            event = FileChangeEvent(
                file_path=file_path,
                content=content,
                change_type=change_type,
                timestamp=time.time()
            )
            self.callback(event)
            with self._stats_lock:
                self.stats['events_triggered'] += 1
        except Exception as e:
            # [修复] 捕获callback异常，防止统计不准确且避免崩溃定时器线程
            print(f"[file_watcher] 处理文件变化时出错: {file_path}, 错误: {e}")
    
    def _debounced_trigger(self, file_path: str, change_type: str) -> None:
        """防抖触发器"""
        # 修复：stopping 期间拒绝新事件，防止数据丢失窗口
        if self._stopping:
            return
        
        with self._timers_lock:
            # 取消之前的定时器
            if file_path in self._pending_timers:
                self._pending_timers[file_path].cancel()
            
            # 创建新定时器
            timer = threading.Timer(
                self.delay_ms / 1000.0,
                self._process_change,
                args=[file_path, change_type]
            )
            self._pending_timers[file_path] = timer
            timer.start()
    
    def on_modified(self, event):
        """文件修改事件"""
        try:  # [修复] 异常保护，防止watchdog线程崩溃
            if event.is_directory:
                return

            with self._stats_lock:
                self.stats['events_received'] += 1
            file_path = event.src_path

            if not self._should_watch(file_path):
                return

            self._debounced_trigger(file_path, 'modified')
        except Exception as e:
            print(f"[file_watcher] on_modified 异常: {e}")

    def on_created(self, event):
        """文件创建事件"""
        try:  # [修复] 异常保护，防止watchdog线程崩溃
            if event.is_directory:
                return

            with self._stats_lock:
                self.stats['events_received'] += 1
            file_path = event.src_path

            if not self._should_watch(file_path):
                return

            self._debounced_trigger(file_path, 'created')
        except Exception as e:
            print(f"[file_watcher] on_created 异常: {e}")

    def on_deleted(self, event):
        """文件删除事件"""
        try:  # [修复] 异常保护，防止watchdog线程崩溃
            if event.is_directory:
                return

            with self._stats_lock:
                self.stats['events_received'] += 1
            file_path = event.src_path

            if not self._should_watch(file_path):
                return

            # 修复：删除事件也走防抖，防止与 modified/created 事件竞态导致重复 deleted 事件
            self._debounced_trigger(file_path, 'deleted')
        except Exception as e:
            print(f"[file_watcher] on_deleted 异常: {e}")

    def on_moved(self, event):
        """文件移动/重命名事件"""
        try:
            if event.is_directory:
                return

            with self._stats_lock:
                self.stats['events_received'] += 1
            src_path = event.src_path
            dest_path = event.dest_path

            # 修复：源文件删除也走防抖，防止与未触发的 modified Timer 竞态
            if self._should_watch(src_path):
                self._debounced_trigger(src_path, 'deleted')

            # 目标文件视为创建
            if self._should_watch(dest_path):
                self._debounced_trigger(dest_path, 'created')
        except Exception as e:
            print(f"[file_watcher] on_moved 异常: {e}")
    
    def get_stats(self) -> Dict:
        """获取统计信息"""
        with self._stats_lock:
            return self.stats.copy()

    def flush_pending(self) -> None:
        """强制刷新所有待处理的事件"""
        # 修复 BUG-2: 先标记所有待 flush 的文件，再取消定时器
        # 避免 Timer 线程在标记前开始执行
        self._stopping = True

        with self._timers_lock:
            # 先收集所有待处理的文件路径
            pending_paths = list(self._pending_timers.keys())
            
            # 先标记为已 flush（在取消定时器之前）
            with self._flushed_lock:
                for file_path in pending_paths:
                    self._flushed_paths.add(file_path)
            
            # 再取消定时器
            pending_items = []
            for file_path, timer in self._pending_timers.items():
                timer.cancel()
                if timer.function and timer.args:
                    pending_items.append((file_path, timer.function, timer.args))
            self._pending_timers.clear()

        for file_path, func, args in pending_items:
            try:
                func(*args)
            except Exception as e:
                print(f"[file_watcher] flush回调异常: {e}")


class FileWatcher:
    """
    文件监控器
    
    使用示例：
        def on_change(event: FileChangeEvent):
            print(f"文件变化: {event.file_path}")
        
        watcher = FileWatcher(
            watch_paths=['/path/to/project'],
            callback=on_change,
            delay_ms=1000
        )
        watcher.start()
        # ... 运行中 ...
        watcher.stop()
    """
    
    def __init__(
        self,
        watch_paths: List[str],
        callback: Callable[[FileChangeEvent], None],
        delay_ms: int = 1000,
        file_extensions: Optional[Set[str]] = None,
        recursive: bool = True
    ):
        self.watch_paths = [Path(p).resolve() for p in watch_paths]
        self.callback = callback
        self.delay_ms = delay_ms
        self.file_extensions = file_extensions
        self.recursive = recursive
        
        self._observer: Optional[Observer] = None
        self._handler: Optional[DebouncedChangeHandler] = None
        self._is_running = False
    
    def start(self) -> None:
        """启动文件监控"""
        if self._is_running:
            return
        
        self._handler = DebouncedChangeHandler(
            callback=self.callback,
            delay_ms=self.delay_ms,
            file_extensions=self.file_extensions
        )
        
        self._observer = Observer()
        
        for path in self.watch_paths:
            if path.exists():
                self._observer.schedule(
                    self._handler,
                    str(path),
                    recursive=self.recursive
                )
                print(f"[file_watcher] 开始监控: {path}")
        
        self._observer.start()
        self._is_running = True
    
    def stop(self) -> None:
        """停止文件监控"""
        if not self._is_running:
            return
        
        # 先刷新所有待处理的事件
        if self._handler:
            self._handler.flush_pending()
        
        if self._observer:
            self._observer.stop()
            # 修复：添加超时，防止 observer 线程阻塞导致 stop() 无限挂起
            self._observer.join(timeout=5.0)
        
        self._is_running = False
        print("[file_watcher] 已停止")
    
    def add_watch(self, path: str) -> None:
        """添加新的监控路径"""
        if not self._is_running or not self._observer:
            return
        
        resolved_path = Path(path).resolve()
        if resolved_path.exists():
            self._observer.schedule(
                self._handler,
                str(resolved_path),
                recursive=self.recursive
            )
            self.watch_paths.append(resolved_path)
    
    def get_stats(self) -> Dict:
        """获取监控统计信息"""
        if self._handler:
            return self._handler.get_stats()
        return {}


# 简单测试
if __name__ == '__main__':
    import signal
    
    def on_change(event: FileChangeEvent):
        print(f"\n[事件] {event.change_type}: {event.file_path}")
        if event.content:
            print(f"  内容长度: {len(event.content)} 字符")
    
    # 创建测试目录
    test_dir = Path('/tmp/test_watch')
    test_dir.mkdir(exist_ok=True)
    
    watcher = FileWatcher(
        watch_paths=[str(test_dir)],
        callback=on_change,
        delay_ms=1000
    )
    
    def signal_handler(sig, frame):
        print("\n正在停止...")
        watcher.stop()
        exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    
    watcher.start()
    print(f"监控目录: {test_dir}")
    print("请修改该目录下的.ets或.ts文件测试，按Ctrl+C停止")
    
    # 保持运行
    while True:
        time.sleep(1)
