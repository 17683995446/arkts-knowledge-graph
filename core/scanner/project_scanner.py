"""
项目文件扫描器
扫描项目目录，找出所有需要解析的源代码文件
"""
import os
import hashlib
import logging
from typing import List, Dict, Tuple, Optional, Set
from dataclasses import dataclass, field
from config.global_settings import SUPPORTED_EXTENSIONS, IGNORED_DIRECTORIES, IGNORED_FILES

logger = logging.getLogger(__name__)


@dataclass
class ScannedFile:
    """扫描到的文件信息"""
    file_path: str = ""         # 相对路径
    absolute_path: str = ""     # 绝对路径
    file_hash: bytes = b""      # SHA256 哈希
    line_count: int = 0         # 行数
    file_size: int = 0          # 字节大小
    extension: str = ""         # 文件扩展名


@dataclass
class ScanResult:
    """扫描结果"""
    total_files: int = 0
    total_lines: int = 0
    total_size_bytes: int = 0
    files: List[ScannedFile] = field(default_factory=list)
    scan_time_ms: float = 0
    error: str = ""


class ProjectScanner:
    """
    项目文件扫描器
    - 递归扫描目录
    - 过滤支持的文件类型
    - 计算文件哈希（用于增量更新）
    - 统计代码行数
    """

    def __init__(self, project_root: str):
        self._project_root = os.path.abspath(project_root)
        if not os.path.isdir(self._project_root):
            raise ValueError(f"项目目录不存在: {self._project_root}")

    def scan_all_files(self) -> ScanResult:
        """
        扫描项目中的所有源代码文件
        """
        import time
        start_time = time.time()

        result = ScanResult()
        files = []

        for dirpath, dirnames, filenames in os.walk(self._project_root):
            # 过滤忽略的目录（原地修改dirnames，阻止递归进入）
            dirnames[:] = [
                d for d in dirnames
                if d not in IGNORED_DIRECTORIES
                and not d.startswith('.')
                and not d.startswith('__')
            ]

            for filename in filenames:
                if filename in IGNORED_FILES:
                    continue

                ext = os.path.splitext(filename)[1].lower()
                if ext not in SUPPORTED_EXTENSIONS:
                    continue

                abs_path = os.path.join(dirpath, filename)
                rel_path = os.path.relpath(abs_path, self._project_root)

                try:
                    file_info = self._scan_single_file(abs_path, rel_path, ext)
                    files.append(file_info)
                except Exception as e:
                    logger.warning(f"扫描文件失败 {rel_path}: {e}")

        # 按路径排序，确保顺序一致
        files.sort(key=lambda f: f.file_path)

        result.files = files
        result.total_files = len(files)
        result.total_lines = sum(f.line_count for f in files)
        result.total_size_bytes = sum(f.file_size for f in files)
        result.scan_time_ms = (time.time() - start_time) * 1000

        logger.info(
            f"扫描完成: {result.total_files} 个文件, "
            f"{result.total_lines} 行代码, "
            f"耗时 {result.scan_time_ms:.0f}ms"
        )

        return result

    def _scan_single_file(self, abs_path: str, rel_path: str,
                           ext: str) -> ScannedFile:
        """扫描单个文件"""
        file_size = os.path.getsize(abs_path)

        # 计算哈希
        file_hash = self._compute_file_hash(abs_path)

        # 统计行数
        line_count = self._count_lines(abs_path)

        return ScannedFile(
            file_path=rel_path,
            absolute_path=abs_path,
            file_hash=file_hash,
            line_count=line_count,
            file_size=file_size,
            extension=ext,
        )

    def _compute_file_hash(self, file_path: str) -> bytes:
        """计算文件的SHA256哈希"""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for chunk in iter(lambda: f.read(8192), b''):
                sha256.update(chunk)
        return sha256.digest()

    def _count_lines(self, file_path: str) -> int:
        """统计文件行数"""
        count = 0
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            for _ in f:
                count += 1
        return count


class ChangeDetector:
    """
    变更检测器
    比较文件哈希，找出需要重新解析的文件
    """

    def __init__(self):
        self._file_hashes: Dict[str, bytes] = {}

    def load_existing_hashes(self, hash_dict: Dict[str, bytes]) -> None:
        """加载已有的文件哈希"""
        self._file_hashes = dict(hash_dict)

    def detect_changes(self, scan_result: ScanResult) -> Tuple[List[ScannedFile], List[str]]:
        """
        检测变更
        Returns:
            (changed_files, deleted_files)
        """
        current_paths = set()
        changed_files = []

        for scanned in scan_result.files:
            current_paths.add(scanned.file_path)

            existing_hash = self._file_hashes.get(scanned.file_path)
            if existing_hash != scanned.file_hash:
                changed_files.append(scanned)

        # 检测删除的文件
        deleted_files = [
            path for path in self._file_hashes
            if path not in current_paths
        ]

        logger.info(
            f"变更检测: {len(changed_files)} 个文件变更, "
            f"{len(deleted_files)} 个文件删除"
        )

        return changed_files, deleted_files

    def update_hashes(self, files: List[ScannedFile]) -> None:
        """更新哈希缓存"""
        for f in files:
            self._file_hashes[f.file_path] = f.file_hash

    def remove_hashes(self, paths: List[str]) -> None:
        """移除指定路径的哈希"""
        for path in paths:
            self._file_hashes.pop(path, None)

    def get_all_hashes(self) -> Dict[str, bytes]:
        """获取所有哈希"""
        return dict(self._file_hashes)
