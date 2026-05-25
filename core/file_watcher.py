"""
File Watcher Module

Monitors the project directory for changes and triggers knowledge graph updates.
Uses watchdog for efficient file system monitoring.
"""

import time
import threading
import logging
from pathlib import Path
from typing import Callable, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

logger = logging.getLogger(__name__)

from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent, FileCreatedEvent, FileDeletedEvent


@dataclass
class FileChangeEvent:
    """Represents a file change event."""
    event_type: str  # 'modified', 'created', 'deleted'
    file_path: str
    timestamp: datetime
    file_hash: Optional[str] = None


class CodeFileHandler(FileSystemEventHandler):
    """
    Handler for code file change events.
    
    Filters events based on file patterns and debounces rapid changes.
    """
    
    def __init__(
        self,
        patterns: List[str],
        ignore_patterns: List[str],
        callback: Callable[[FileChangeEvent], None],
        debounce_seconds: float = 2.0
    ):
        """
        Initialize the handler.
        
        Args:
            patterns: File patterns to watch (e.g., ['*.ets', '*.ts'])
            ignore_patterns: Patterns to ignore (e.g., ['node_modules/*'])
            callback: Function to call when a file changes
            debounce_seconds: Minimum time between processing the same file
        """
        self.patterns = patterns
        self.ignore_patterns = ignore_patterns
        self.callback = callback
        self.debounce_seconds = debounce_seconds
        self._last_processed: dict = {}
        self._lock = threading.Lock()
    
    def _should_process(self, file_path: str) -> bool:
        """Check if a file should be processed based on patterns."""
        path = Path(file_path)
        
        # Check ignore patterns
        for ignore in self.ignore_patterns:
            if ignore.endswith('*'):
                ignore_dir = ignore.rstrip('/*')
                if ignore_dir in path.parts:
                    return False
            elif path.match(ignore):
                return False
        
        # Check include patterns
        for pattern in self.patterns:
            if path.match(pattern):
                return True
        
        return False
    
    def _is_debounced(self, file_path: str) -> bool:
        """Check if the file change should be debounced."""
        with self._lock:
            now = time.time()
            last_time = self._last_processed.get(file_path, 0)
            if now - last_time < self.debounce_seconds:
                return True
            self._last_processed[file_path] = now
            return False
    
    def on_modified(self, event):
        """Handle file modification events."""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        if self._is_debounced(event.src_path):
            logger.debug("[DEBUG] [CodeFileHandler] [on_modified] 文件变更被防抖跳过: %s", event.src_path)
            return
        
        logger.debug("[DEBUG] [CodeFileHandler] [on_modified] 文件修改事件: %s", event.src_path)
        change_event = FileChangeEvent(
            event_type='modified',
            file_path=event.src_path,
            timestamp=datetime.now()
        )
        self.callback(change_event)
    
    def on_created(self, event):
        """Handle file creation events."""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        logger.debug("[DEBUG] [CodeFileHandler] [on_created] 文件创建事件: %s", event.src_path)
        change_event = FileChangeEvent(
            event_type='created',
            file_path=event.src_path,
            timestamp=datetime.now()
        )
        self.callback(change_event)
    
    def on_deleted(self, event):
        """Handle file deletion events."""
        if event.is_directory:
            return
        
        if not self._should_process(event.src_path):
            return
        
        logger.debug("[DEBUG] [CodeFileHandler] [on_deleted] 文件删除事件: %s", event.src_path)
        change_event = FileChangeEvent(
            event_type='deleted',
            file_path=event.src_path,
            timestamp=datetime.now()
        )
        self.callback(change_event)


class FileWatcher:
    """
    File system watcher for code changes.
    
    Monitors the project directory and triggers updates when files change.
    """
    
    def __init__(
        self,
        project_path: str,
        patterns: List[str] = None,
        ignore_patterns: List[str] = None,
        debounce_seconds: float = 2.0
    ):
        """
        Initialize the file watcher.
        
        Args:
            project_path: Path to the project directory to watch
            patterns: File patterns to watch (default: ['*.ets', '*.ts'])
            ignore_patterns: Patterns to ignore (default: ['node_modules/*', '.git/*'])
            debounce_seconds: Debounce time between changes
        """
        self.project_path = Path(project_path).resolve()
        self.patterns = patterns or ['*.ets', '*.ts']
        self.ignore_patterns = ignore_patterns or ['node_modules/*', '.git/*', 'build/*', 'dist/*']
        self.debounce_seconds = debounce_seconds
        
        self._observer: Optional[Observer] = None
        self._handler: Optional[CodeFileHandler] = None
        self._change_callbacks: List[Callable[[FileChangeEvent], None]] = []
        self._is_running = False
        self._lock = threading.Lock()
    
    def add_change_callback(self, callback: Callable[[FileChangeEvent], None]) -> None:
        """Add a callback to be called when files change."""
        with self._lock:
            self._change_callbacks.append(callback)
    
    def remove_change_callback(self, callback: Callable[[FileChangeEvent], None]) -> None:
        """Remove a change callback."""
        with self._lock:
            if callback in self._change_callbacks:
                self._change_callbacks.remove(callback)
    
    def _on_file_change(self, event: FileChangeEvent) -> None:
        """Internal handler for file changes."""
        logger.debug("[DEBUG] [FileWatcher] [_on_file_change] 文件变更事件: type=%s, path=%s", event.event_type, event.file_path)
        with self._lock:
            callbacks = self._change_callbacks.copy()
        
        for callback in callbacks:
            try:
                callback(event)
            except Exception as e:
                logger.error("[DEBUG] [FileWatcher] [_on_file_change] 回调执行异常: %s", e)
                print(f"Error in change callback: {e}")
    
    def start(self) -> None:
        """Start watching for file changes."""
        if self._is_running:
            logger.debug("[DEBUG] [FileWatcher] [start] 文件监视器已在运行中")
            return
        
        if not self.project_path.exists():
            logger.error("[DEBUG] [FileWatcher] [start] 项目路径不存在: %s", self.project_path)
            raise FileNotFoundError(f"Project path does not exist: {self.project_path}")
        
        self._handler = CodeFileHandler(
            patterns=self.patterns,
            ignore_patterns=self.ignore_patterns,
            callback=self._on_file_change,
            debounce_seconds=self.debounce_seconds
        )
        
        self._observer = Observer()
        self._observer.schedule(self._handler, str(self.project_path), recursive=True)
        self._observer.start()
        
        self._is_running = True
        logger.debug("[DEBUG] [FileWatcher] [start] 文件监视器已启动: %s, patterns=%s", self.project_path, self.patterns)
        print(f"File watcher started for: {self.project_path}")
    
    def stop(self) -> None:
        """Stop watching for file changes."""
        if not self._is_running:
            logger.debug("[DEBUG] [FileWatcher] [stop] 文件监视器未在运行中")
            return
        
        if self._observer:
            self._observer.stop()
            self._observer.join()
        
        self._is_running = False
        logger.debug("[DEBUG] [FileWatcher] [stop] 文件监视器已停止")
        print("File watcher stopped")
    
    def is_running(self) -> bool:
        """Check if the watcher is currently running."""
        return self._is_running
    
    def get_watched_files(self) -> List[str]:
        """Get a list of all files currently being watched."""
        watched = []
        for pattern in self.patterns:
            for file_path in self.project_path.rglob(pattern):
                # Check ignore patterns
                should_ignore = False
                for ignore in self.ignore_patterns:
                    if ignore.endswith('*'):
                        ignore_dir = ignore.rstrip('/*')
                        if ignore_dir in file_path.parts:
                            should_ignore = True
                            break
                    elif file_path.match(ignore):
                        should_ignore = True
                        break
                
                if not should_ignore:
                    watched.append(str(file_path))
        
        return sorted(watched)


class IncrementalUpdater:
    """
    Manages incremental updates to the knowledge graph.
    
    When a file changes, only that file needs to be re-parsed and updated
    in the database, rather than rebuilding the entire graph.
    """
    
    def __init__(self, repository, parser):
        """
        Initialize the incremental updater.
        
        Args:
            repository: KnowledgeRepository instance
            parser: Parser instance for re-parsing files
        """
        self.repository = repository
        self.parser = parser
        self._pending_updates: Set[str] = set()
        self._lock = threading.Lock()
    
    def queue_update(self, file_path: str) -> None:
        """Queue a file for incremental update."""
        with self._lock:
            self._pending_updates.add(file_path)
    
    def process_updates(self) -> List[str]:
        """
        Process all pending updates.
        
        Returns:
            List of file paths that were updated
        """
        with self._lock:
            updates = list(self._pending_updates)
            self._pending_updates.clear()
        
        updated = []
        for file_path in updates:
            try:
                self._update_file(file_path)
                updated.append(file_path)
            except Exception as e:
                print(f"Error updating file {file_path}: {e}")
        
        return updated
    
    def _update_file(self, file_path: str) -> None:
        """
        Update a single file in the database.

        This involves:
        1. Re-parsing the file (into temporary storage)
        2. Removing old entities for this file (cascade)
        3. Inserting new entities
        """
        logger.debug("[DEBUG] [IncrementalUpdater] [_update_file] 开始增量更新: %s", file_path)
        from core.entity_models import FileEntity, ClassEntity, MethodEntity, PropertyEntity
        from parser.ark_analyzer_adapter import TypeScriptRegexParser, ParserConfig, KnowledgeGraph

        abs_path = str(file_path)
        project_path = str(self.parser.config.target_project_path)

        # 计算相对路径
        if abs_path.startswith(project_path):
            relative_path = abs_path[len(project_path):].lstrip('/\\')
        else:
            relative_path = abs_path

        # Check if file still exists
        file_path_obj = __import__('pathlib').Path(abs_path)
        project_path_obj = __import__('pathlib').Path(project_path)

        if not file_path_obj.exists():
            # File was deleted - remove old entities
            old_file = self.repository.get_file_by_path(relative_path)
            if old_file:
                logger.debug("[DEBUG] [IncrementalUpdater] [_update_file] 文件已被删除, 清理旧实体: %s", file_path)
                self.repository.delete_file_cascade(old_file['id'])
                # Clean metadata for this file
                old_file_id = old_file['id']
                for key in ['imports', 'inheritance', 'calls', 'components']:
                    if key in self.parser.knowledge_graph.metadata:
                        self.parser.knowledge_graph.metadata[key] = [
                            item for item in self.parser.knowledge_graph.metadata[key]
                            if item.get('source_file_id') != old_file_id
                        ]
            return

        # 1. Parse the file into a TEMPORARY knowledge_graph (don't touch global state)
        temp_kg = KnowledgeGraph()
        temp_parser = TypeScriptRegexParser(ParserConfig(
            target_project_path=project_path,
            file_patterns=self.parser.config.file_patterns
        ))
        temp_parser.knowledge_graph = temp_kg

        try:
            temp_parser._parse_file(file_path_obj, project_path_obj)
        except Exception as parse_error:
            logger.error("[DEBUG] [IncrementalUpdater] [_update_file] 解析文件异常, 跳过更新: %s, error=%s",
                         file_path, parse_error)
            return  # Don't delete old data if parsing fails

        # 2. Now safely delete old data and insert new data
        old_file = self.repository.get_file_by_path(relative_path)
        old_file_id = old_file.get('id', '') if old_file else ''

        if old_file:
            logger.debug("[DEBUG] [IncrementalUpdater] [_update_file] 删除旧实体: file_id=%s", old_file['id'])
            self.repository.delete_file_cascade(old_file['id'])

        # 3. Insert new entities into database
        logger.debug("[DEBUG] [IncrementalUpdater] [_update_file] 解析完成, 新实体数量=%d", len(temp_kg.entities))
        for entity in temp_kg.entities.values():
            if isinstance(entity, FileEntity):
                self.repository.save_file(entity)
            elif isinstance(entity, ClassEntity):
                self.repository.save_class(entity)
                if entity.parent_class:
                    # 查找父类ID
                    parent_class_id = None
                    for e in temp_kg.entities.values():
                        if isinstance(e, ClassEntity) and e.name == entity.parent_class:
                            parent_class_id = e.id
                            break
                    self.repository.save_inheritance(
                        entity.id, parent_class_id,
                        entity.parent_class, 'extends'
                    )
                if hasattr(entity, 'implemented_interfaces') and entity.implemented_interfaces:
                    for iface in entity.implemented_interfaces:
                        self.repository.save_inheritance(
                            entity.id, None, iface.strip(), 'implements'
                        )
            elif isinstance(entity, MethodEntity):
                self.repository.save_method(entity)
            elif isinstance(entity, PropertyEntity):
                self.repository.save_property(entity)

        # 4. Save relationships
        for rel_type in ['imports', 'inheritance', 'calls', 'components']:
            if rel_type in temp_kg.metadata:
                for item in temp_kg.metadata[rel_type]:
                    if rel_type == 'imports':
                        self.repository.save_import(
                            item.get('source_file_id'),
                            item.get('import_path')
                        )
                    elif rel_type == 'calls':
                        self.repository.save_call(item)
                    elif rel_type == 'components':
                        self.repository.save_component_nesting(item)
                    elif rel_type == 'inheritance':
                        self.repository.save_inheritance(
                            item.get('child_class_id'),
                            item.get('parent_class_id'),
                            item.get('parent_class_name'),
                            item.get('relation_type')
                        )

        # 5. Update global knowledge_graph metadata (clean old, add new)
        if old_file_id:
            for key in ['imports', 'inheritance', 'calls', 'components']:
                if key in self.parser.knowledge_graph.metadata:
                    self.parser.knowledge_graph.metadata[key] = [
                        item for item in self.parser.knowledge_graph.metadata[key]
                        if item.get('source_file_id') != old_file_id
                    ]

        # Add new metadata
        for rel_type in ['imports', 'inheritance', 'calls', 'components']:
            if rel_type in temp_kg.metadata:
                if rel_type not in self.parser.knowledge_graph.metadata:
                    self.parser.knowledge_graph.metadata[rel_type] = []
                self.parser.knowledge_graph.metadata[rel_type].extend(temp_kg.metadata[rel_type])

        # Update global entities (only for this file)
        for entity in temp_kg.entities.values():
            self.parser.knowledge_graph.entities[entity.id] = entity

        logger.debug("[DEBUG] [IncrementalUpdater] [_update_file] 增量更新完成: %s", file_path)
