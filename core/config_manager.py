"""
Configuration Manager Module

Manages all configuration settings for the ArkTS Knowledge Graph system.
Follows the zero-configuration principle by providing sensible defaults.
"""

import os
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
from dotenv import load_dotenv


@dataclass
class DatabaseConfig:
    """Database configuration settings."""
    path: str = "./data/code_knowledge_graph.db"
    
    def __post_init__(self):
        # Ensure directory exists
        Path(self.path).parent.mkdir(parents=True, exist_ok=True)


@dataclass
class LLMConfig:
    """LLM API configuration settings."""
    api_key: str = ""
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    timeout_seconds: int = 60
    max_retries: int = 3
    max_tokens: int = 4096


@dataclass
class WebServerConfig:
    """Web server configuration settings."""
    host: str = "0.0.0.0"
    port: int = 5000
    debug: bool = False
    secret_key: str = field(default_factory=lambda: os.urandom(24).hex())


@dataclass
class FileWatcherConfig:
    """File watcher configuration settings."""
    delay_seconds: float = 2.0
    patterns: list = field(default_factory=lambda: ["*.ets", "*.ts"])
    ignore_patterns: list = field(default_factory=lambda: [
        "node_modules/*", ".git/*", "build/*", "dist/*",
        "oh_modules/*", ".ohpm/*", ".preview/*"
    ])


@dataclass
class ArkAnalyzerConfig:
    """ArkAnalyzer configuration settings."""
    sdk_path: Optional[str] = None
    target_project_path: Optional[str] = None


class ConfigurationManager:
    """
    Centralized configuration management.
    
    Loads configuration from environment variables and provides
    access to all system settings.
    """
    
    _instance: Optional['ConfigurationManager'] = None
    
    def __new__(cls) -> 'ConfigurationManager':
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        # Load environment variables
        load_dotenv()
        
        # Initialize configurations
        self.database = self._load_database_config()
        self.llm = self._load_llm_config()
        self.web_server = self._load_web_server_config()
        self.file_watcher = self._load_file_watcher_config()
        self.ark_analyzer = self._load_ark_analyzer_config()
        
        self._initialized = True
    
    def _load_database_config(self) -> DatabaseConfig:
        """Load database configuration from environment."""
        return DatabaseConfig(
            path=os.getenv('DATABASE_PATH', './data/code_knowledge_graph.db')
        )
    
    def _load_llm_config(self) -> LLMConfig:
        """Load LLM configuration from environment."""
        return LLMConfig(
            api_key=os.getenv('SILICON_FLOW_API_KEY', ''),
            base_url=os.getenv('SILICON_FLOW_BASE_URL', 'https://api.siliconflow.cn/v1'),
            model=os.getenv('SILICON_FLOW_MODEL', 'Qwen/Qwen2.5-7B-Instruct'),
            timeout_seconds=int(os.getenv('LLM_TIMEOUT_SECONDS', '60')),
            max_retries=int(os.getenv('LLM_MAX_RETRIES', '3')),
            max_tokens=int(os.getenv('LLM_MAX_TOKENS', '4096'))
        )
    
    def _load_web_server_config(self) -> WebServerConfig:
        """Load web server configuration from environment."""
        return WebServerConfig(
            host=os.getenv('FLASK_HOST', '0.0.0.0'),
            port=int(os.getenv('FLASK_PORT', '5000')),
            debug=os.getenv('FLASK_DEBUG', 'false').lower() == 'true',
            secret_key=os.getenv('FLASK_SECRET_KEY', os.urandom(24).hex())
        )
    
    def _load_file_watcher_config(self) -> FileWatcherConfig:
        """Load file watcher configuration from environment."""
        patterns = os.getenv('WATCH_PATTERNS', '*.ets,*.ts').split(',')
        return FileWatcherConfig(
            delay_seconds=float(os.getenv('WATCH_DELAY_SECONDS', '2.0')),
            patterns=[p.strip() for p in patterns]
        )
    
    def _load_ark_analyzer_config(self) -> ArkAnalyzerConfig:
        """Load ArkAnalyzer configuration from environment."""
        return ArkAnalyzerConfig(
            sdk_path=os.getenv('ARKTS_SDK_PATH'),
            target_project_path=os.getenv('TARGET_PROJECT_PATH')
        )
    
    def validate(self) -> list[str]:
        """
        Validate all configurations.
        
        Returns:
            List of validation error messages. Empty if valid.
        """
        errors = []
        
        if not self.llm.api_key:
            errors.append("LLM API key is not configured")
        
        if not self.ark_analyzer.target_project_path:
            errors.append("Target project path is not configured")
        elif not Path(self.ark_analyzer.target_project_path).exists():
            errors.append(f"Target project path does not exist: {self.ark_analyzer.target_project_path}")
        
        return errors


# Global configuration instance
config = ConfigurationManager()
