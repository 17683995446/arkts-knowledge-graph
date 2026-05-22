"""
全局配置模块 - ArkTS 知识图谱系统
所有可配置参数的单一来源
"""
import os
import multiprocessing

# ==================== 项目根路径 ====================
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# ==================== 数据库配置 ====================
DATABASE_DIRECTORY = os.path.join(PROJECT_ROOT, "data")
DATABASE_FILENAME = "knowledge_graph.db"
DATABASE_FULL_PATH = os.path.join(DATABASE_DIRECTORY, DATABASE_FILENAME)

# ==================== 批量写入配置 ====================
BATCH_SIZE = 1000          # 攒够1000条再写一次硬盘（IO铁律）
MAX_WORKERS = max(1, multiprocessing.cpu_count() - 1)  # 用满CPU但留一个核给系统

# ==================== 文件扫描配置 ====================
SUPPORTED_EXTENSIONS = {".ets", ".ts", ".tsx", ".js", ".jsx"}
IGNORED_DIRECTORIES = {
    "node_modules", ".git", ".idea", ".vscode",
    "build", "dist", "oh_modules", ".hvigor",
    "coverage", ".test", "__test__"
}
IGNORED_FILES = {".DS_Store", "Thumbs.db", "package-lock.json", "yarn.lock"}

# ==================== 硅基流动 LLM 配置 ====================
LLM_API_BASE_URL = "https://api.siliconflow.cn/v1/chat/completions"
# 需要通过环境变量 LLM_API_KEY 设置，请勿在此处硬编码密钥
LLM_API_KEY = os.environ.get("LLM_API_KEY", "")
LLM_MODEL_NAME = "Qwen/Qwen2.5-7B-Instruct"
LLM_MAX_TOKENS = 2048
LLM_TEMPERATURE = 0.1      # 低温度确保SQL生成稳定

# ==================== Web 服务配置 ====================
WEB_HOST = "0.0.0.0"
WEB_PORT = 5000
WEB_DEBUG = False

# ==================== 日志配置 ====================
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"

# ==================== 性能监控配置 ====================
ENABLE_PROFILING = False
PROFILING_OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "profiles")
