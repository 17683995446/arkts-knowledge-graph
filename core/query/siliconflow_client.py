"""
硅基流动 LLM 客户端
调用硅基流动API，将自然语言转换为SQL查询
"""
import json
import logging
import requests
from typing import Dict, Any, Optional, List
from config.global_settings import (
    LLM_API_BASE_URL, LLM_API_KEY, LLM_MODEL_NAME,
    LLM_MAX_TOKENS, LLM_TEMPERATURE
)

logger = logging.getLogger(__name__)


class SiliconFlowClient:
    """
    硅基流动API客户端
    负责与Qwen2.5-7B模型通信
    """

    def __init__(self):
        self._api_base = LLM_API_BASE_URL
        self._api_key = LLM_API_KEY
        self._model = LLM_MODEL_NAME
        self._max_tokens = LLM_MAX_TOKENS
        self._temperature = LLM_TEMPERATURE

    def chat_completion(self, messages: List[Dict[str, str]],
                        temperature: float = None) -> str:
        """
        调用聊天补全API
        Args:
            messages: 消息列表 [{"role": "user", "content": "..."}]
            temperature: 温度参数
        Returns:
            模型回复文本
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self._model,
            "messages": messages,
            "max_tokens": self._max_tokens,
            "temperature": temperature or self._temperature,
            "top_p": 0.9,
        }

        try:
            response = requests.post(
                self._api_base,
                headers=headers,
                json=payload,
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except requests.exceptions.Timeout:
            logger.error("LLM API 请求超时")
            return "请求超时，请稍后重试"
        except requests.exceptions.RequestException as e:
            logger.error(f"LLM API 请求失败: {e}")
            return f"API请求失败: {e}"
        except (KeyError, IndexError) as e:
            logger.error(f"LLM API 响应解析失败: {e}")
            return "API响应格式异常"

    def test_connection(self) -> bool:
        """测试API连接"""
        try:
            result = self.chat_completion([
                {"role": "user", "content": "你好，请回复'连接成功'"}
            ])
            return len(result) > 0
        except Exception:
            return False
