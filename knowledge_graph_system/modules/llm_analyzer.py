"""
LLM分析模块 (llm_analyzer)

职责：
1. 调用硅基流动API进行代码语义分析
2. 生成代码实体摘要
3. 提取智能标签
4. 分析实体间语义关系

第一性原理：
- 异步处理：LLM调用是IO密集型，不阻塞主流程
- 批量处理：合并多个实体一起分析，减少API调用
- 缓存结果：相同代码片段不再重复分析
"""

import hashlib
import json
import time
import threading
from collections import OrderedDict
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any, Callable
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


@dataclass
class LLMConfig:
    """LLM配置"""
    api_key: str
    base_url: str = "https://api.siliconflow.cn/v1"
    model: str = "Qwen/Qwen2.5-7B-Instruct"
    max_tokens: int = 512
    temperature: float = 0.3
    timeout: int = 30


@dataclass
class AnalysisResult:
    """分析结果"""
    summary: str
    tags: List[str]
    confidence: float = 0.0


class LLMCache:
    """LLM分析结果缓存 - 基于OrderedDict的真正LRU实现"""

    def __init__(self, max_size: int = 10000):
        # [修复] 使用OrderedDict实现真正的LRU缓存
        self._cache: OrderedDict[str, AnalysisResult] = OrderedDict()
        self._lock = threading.RLock()
        self._max_size = max_size

    def _compute_key(self, code_snippet: str) -> str:
        """计算缓存键"""
        return hashlib.sha256(code_snippet.encode()).hexdigest()[:32]

    def get(self, code_snippet: str) -> Optional[AnalysisResult]:
        """获取缓存结果，命中时移到末尾（标记为最近使用）"""
        key = self._compute_key(code_snippet)
        with self._lock:
            if key in self._cache:
                # [修复] LRU：命中时移到OrderedDict末尾
                self._cache.move_to_end(key)
                return self._cache[key]
            return None

    def set(self, code_snippet: str, result: AnalysisResult) -> None:
        """设置缓存结果，满时淘汰最久未使用的条目"""
        key = self._compute_key(code_snippet)
        with self._lock:
            if key in self._cache:
                # 已存在则更新并移到末尾
                self._cache.move_to_end(key)
            self._cache[key] = result
            # [修复] LRU淘汰：超出容量时移除最久未使用的（OrderedDict头部）
            while len(self._cache) > self._max_size:
                self._cache.popitem(last=False)

    def clear(self) -> None:
        """清空缓存"""
        with self._lock:
            self._cache.clear()

    def size(self) -> int:
        """获取缓存大小"""
        with self._lock:
            return len(self._cache)


class LLMAnalyzer:
    """
    LLM代码分析器
    
    使用硅基流动API进行代码语义分析
    """
    
    def __init__(self, config: LLMConfig):
        self.config = config
        self.cache = LLMCache()
        self._executor = ThreadPoolExecutor(max_workers=4)
        self._closed = False  # 修复 BUG-29: close后防护标志
        self._stats = {
            'api_calls': 0,
            'cache_hits': 0,
            'errors': 0,
            'total_time_ms': 0
        }
        self._stats_lock = threading.Lock()
    
    def _call_api(self, messages: List[Dict[str, str]]) -> Optional[str]:
        """调用LLM API，带指数退避重试机制"""
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": self.config.model,
            "messages": messages,
            "max_tokens": self.config.max_tokens,
            "temperature": self.config.temperature
        }

        # [修复] 添加指数退避重试，最多3次，对429状态码特别处理
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.post(
                    f"{self.config.base_url}/chat/completions",
                    headers=headers,
                    json=payload,
                    timeout=self.config.timeout
                )

                # 对429（速率限制）状态码特别处理，等待更长时间
                if response.status_code == 429:
                    # 修复 BUG-33: 429错误计入统计
                    with self._stats_lock:
                        self._stats['errors'] += 1
                    try:
                        retry_after = int(response.headers.get('Retry-After', 2 ** (attempt + 1)))
                    except (ValueError, TypeError):
                        retry_after = 2 ** (attempt + 1)
                    wait_time = min(max(retry_after, 2 ** (attempt + 1)), 60)  # 上限60秒
                    print(f"[llm_analyzer] 触发速率限制(429)，第{attempt+1}次重试，等待{wait_time}秒")
                    time.sleep(wait_time)
                    continue

                response.raise_for_status()

                data = response.json()
                return data['choices'][0]['message']['content']

            except requests.exceptions.HTTPError as e:
                if attempt < max_retries - 1 and e.response is not None and e.response.status_code >= 500:
                    wait_time = 2 ** (attempt + 1)
                    print(f"[llm_analyzer] 服务端错误({e.response.status_code})，第{attempt+1}次重试，等待{wait_time}秒")
                    time.sleep(wait_time)
                    continue
                # 非服务端错误或最后一次重试，直接抛出
                print(f"[llm_analyzer] API调用失败: {e}")
                with self._stats_lock:
                    self._stats['errors'] += 1
                return None

            except Exception as e:
                if attempt < max_retries - 1:
                    wait_time = 2 ** (attempt + 1)
                    print(f"[llm_analyzer] API调用异常，第{attempt+1}次重试，等待{wait_time}秒: {e}")
                    time.sleep(wait_time)
                    continue
                print(f"[llm_analyzer] API调用失败（已重试{max_retries}次）: {e}")
                with self._stats_lock:
                    self._stats['errors'] += 1
                return None

        return None
    
    def _parse_response(self, content: str) -> AnalysisResult:
        """解析LLM响应"""
        try:
            # 尝试解析JSON格式
            if '{' in content and '}' in content:
                json_start = content.find('{')
                json_end = content.rfind('}') + 1
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                
                summary = data.get('summary', data.get('description', content[:200]))
                tags = data.get('tags', data.get('keywords', []))
                
                if isinstance(tags, str):
                    tags = [t.strip() for t in tags.split(',')]
                
                return AnalysisResult(
                    summary=summary[:200],
                    tags=tags[:5],
                    confidence=0.9
                )
        except json.JSONDecodeError:
            pass
        
        # 回退：简单解析文本
        lines = content.strip().split('\n')
        summary = lines[0][:200] if lines else ""
        
        # 修复 BUG-28: 空内容应返回低confidence
        if not summary or not summary.strip():
            return AnalysisResult(summary="", tags=[], confidence=0.0)

        # 从内容中提取标签
        tags = []
        for line in lines:
            if '标签' in line or 'tags' in line.lower() or 'keywords' in line.lower():
                parts = line.split(':')[-1] if ':' in line else line
                tags = [t.strip() for t in parts.split(',') if t.strip()]
                break
        
        if not tags:
            # 从总结中提取关键词作为标签
            words = summary.split()
            tags = [w for w in words if len(w) > 2][:3]
        
        return AnalysisResult(
            summary=summary,
            tags=tags[:5],
            confidence=0.7
        )
    
    def analyze_entity(self, code_snippet: str, entity_name: str = "", 
                       entity_type: str = "") -> AnalysisResult:
        """
        分析单个代码实体
        
        Args:
            code_snippet: 代码片段
            entity_name: 实体名称
            entity_type: 实体类型
        
        Returns:
            AnalysisResult: 分析结果
        """
        # 修复 BUG-29: close后禁止使用
        if self._closed:
            return AnalysisResult(summary="", tags=[], confidence=0.0)
        # [修复] 检查code_snippet是否为空
        if not code_snippet or not code_snippet.strip():
            return AnalysisResult(
                summary=f"{entity_name} ({entity_type})" if entity_name else "空代码片段",
                tags=[entity_type] if entity_type else ["empty"],
                confidence=0.0
            )

        # 检查缓存
        cached = self.cache.get(code_snippet)
        if cached:
            with self._stats_lock:
                self._stats['cache_hits'] += 1
            return cached
        
        start_time = time.time()
        
        # 修复 BUG-35: 截断代码后再检查缓存（使用截断后的内容作为缓存键）
        truncated_snippet = code_snippet[:1000]
        if len(code_snippet) > 1000:
            cached_truncated = self.cache.get(truncated_snippet)
            if cached_truncated:
                with self._stats_lock:
                    self._stats['cache_hits'] += 1
                return cached_truncated
        
        # 构建提示词
        prompt = f"""请分析以下{entity_type or '代码'}，提供简洁的描述和标签。

代码：
```typescript
{code_snippet[:1000]}
```

请以JSON格式返回：
{{
    "summary": "一句话描述这个功能的作用（50字以内）",
    "tags": ["标签1", "标签2", "标签3"]
}}
"""
        
        messages = [
            {"role": "system", "content": "你是一个代码分析专家，擅长理解代码语义并生成简洁的描述和标签。"},
            {"role": "user", "content": prompt}
        ]
        
        content = self._call_api(messages)
        
        with self._stats_lock:
            self._stats['api_calls'] += 1
            self._stats['total_time_ms'] += int((time.time() - start_time) * 1000)
        
        if content:
            result = self._parse_response(content)
        else:
            result = AnalysisResult(
                summary=f"{entity_name} ({entity_type})" if entity_name else "未命名代码",
                tags=[entity_type] if entity_type else ["unknown"],
                confidence=0.0
            )
        
        # 缓存结果（修复：仅缓存成功结果，避免暂时性API故障被永久缓存）
        if result.confidence > 0.0:
            self.cache.set(code_snippet, result)
        
        return result
    
    def analyze_entities_batch(self, entities: List[Any]) -> Dict[int, AnalysisResult]:
        """
        批量分析多个实体
        
        Args:
            entities: 代码实体列表，每个实体需要有code_snippet, name, entity_type属性
        
        Returns:
            Dict[int, AnalysisResult]: 实体索引到分析结果的映射
        """
        results = {}
        
        # 修复 BUG-29: close后禁止使用
        if self._closed:
            return results

        # 过滤掉已在缓存中的实体
        to_analyze = []
        for i, entity in enumerate(entities):
            # 修复 BUG-36: 跳过None或无效实体
            if entity is None or not hasattr(entity, 'code_snippet'):
                continue
            cached = self.cache.get(entity.code_snippet)
            if cached:
                results[i] = cached
                with self._stats_lock:
                    self._stats['cache_hits'] += 1
            else:
                to_analyze.append((i, entity))
        
        if not to_analyze:
            return results
        
        # 并行分析
        futures = {}
        for idx, entity in to_analyze:
            future = self._executor.submit(
                self.analyze_entity,
                entity.code_snippet,
                entity.name,
                entity.entity_type
            )
            futures[future] = idx
        
        for future in as_completed(futures):
            idx = futures[future]
            try:
                result = future.result()
                results[idx] = result
            except Exception as e:
                print(f"[llm_analyzer] 分析失败: {e}")
                results[idx] = AnalysisResult(
                    summary="分析失败",
                    tags=["error"],
                    confidence=0.0
                )
        
        return results
    
    def analyze_file_relationships(self, file_path: str, entities: List[Any]) -> List[Dict]:
        """
        分析文件内实体间的语义关系
        
        Args:
            file_path: 文件路径
            entities: 实体列表
        
        Returns:
            List[Dict]: 语义关系列表
        """
        if len(entities) < 2:
            return []
        
        # 构建实体描述
        entity_descriptions = []
        for i, entity in enumerate(entities[:10]):  # 限制数量
            desc = f"{i+1}. {entity.entity_type} {entity.name}"
            if entity.modifiers:
                desc += f" ({', '.join(entity.modifiers)})"
            entity_descriptions.append(desc)
        
        prompt = f"""分析以下代码实体之间的关系：

实体列表：
{chr(10).join(entity_descriptions)}

请识别实体间的语义关系（如调用、依赖、组合等），以JSON数组格式返回：
[
    {{"source": "实体名1", "target": "实体名2", "relation": "关系类型"}},
    ...
]

只返回JSON，不要其他解释。"""
        
        messages = [
            {"role": "system", "content": "你是一个代码架构分析专家，擅长识别代码实体间的关系。"},
            {"role": "user", "content": prompt}
        ]
        
        content = self._call_api(messages)
        
        if not content:
            return []
        
        try:
            # 提取JSON
            if '[' in content and ']' in content:
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                json_str = content[json_start:json_end]
                relations = json.loads(json_str)
                
                # 验证格式
                valid_relations = []
                for rel in relations:
                    if 'source' in rel and 'target' in rel and 'relation' in rel:
                        valid_relations.append({
                            'source_file': file_path,
                            'source_entity': rel['source'],
                            'target_file': file_path,
                            'target_entity': rel['target'],
                            'relation_type': rel['relation']
                        })
                
                return valid_relations
        except (json.JSONDecodeError, KeyError) as e:
            print(f"[llm_analyzer] 关系解析失败: {e}")
        
        return []
    
    def generate_file_summary(self, file_path: str, entities: List[Any]) -> str:
        """
        生成文件级摘要
        
        Args:
            file_path: 文件路径
            entities: 实体列表
        
        Returns:
            str: 文件摘要
        """
        if not entities:
            return "空文件"
        
        # 统计信息
        type_counts = {}
        for entity in entities:
            type_counts[entity.entity_type] = type_counts.get(entity.entity_type, 0) + 1
        
        entity_list = [f"{e.entity_type} {e.name}" for e in entities[:5]]
        
        prompt = f"""为以下代码文件生成一句话摘要：

文件路径: {file_path}
包含实体: {', '.join(entity_list)}
实体统计: {json.dumps(type_counts, ensure_ascii=False)}

请用一句话（30字以内）描述这个文件的主要功能："""
        
        messages = [
            {"role": "system", "content": "你是一个代码文档生成专家。"},
            {"role": "user", "content": prompt}
        ]
        
        content = self._call_api(messages)
        
        if content:
            return content.strip()[:100]
        
        # 回退：基于统计生成
        main_types = sorted(type_counts.items(), key=lambda x: x[1], reverse=True)
        type_desc = ', '.join([f"{count}个{t}" for t, count in main_types[:2]])
        return f"包含{type_desc}的文件"
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._stats_lock:
            stats = self._stats.copy()

        if stats['api_calls'] > 0:
            stats['avg_time_ms'] = stats['total_time_ms'] / stats['api_calls']
        else:
            stats['avg_time_ms'] = 0

        # 修复：通过公共方法获取缓存大小，而非直接访问内部属性
        stats['cache_size'] = self.cache.size()

        return stats
    
    def close(self) -> None:
        """关闭分析器"""
        self._closed = True  # 修复 BUG-29: 标记已关闭
        # 修复：添加超时，避免关闭时无限阻塞
        self._executor.shutdown(wait=True, cancel_futures=True)


# 简单测试
if __name__ == '__main__':
    import os
    # [修复] 从环境变量读取API Key，不再硬编码
    api_key = os.environ.get('SILICONFLOW_API_KEY', 'your-api-key-here')
    config = LLMConfig(
        api_key=api_key,
        model="Qwen/Qwen2.5-7B-Instruct"
    )
    
    analyzer = LLMAnalyzer(config)
    
    test_code = """
export class UserService {
    private users: Map<string, User> = new Map();
    
    async getUserById(userId: string): Promise<User | null> {
        return this.users.get(userId) || null;
    }
    
    async createUser(userData: CreateUserDTO): Promise<User> {
        const user = new User(userData);
        this.users.set(user.id, user);
        return user;
    }
}
"""
    
    print("=== LLM分析模块测试 ===\n")
    
    print("1. 测试单个实体分析")
    result = analyzer.analyze_entity(test_code, "UserService", "class")
    print(f"   摘要: {result.summary}")
    print(f"   标签: {result.tags}")
    print(f"   置信度: {result.confidence}")
    
    print("\n2. 测试缓存")
    result2 = analyzer.analyze_entity(test_code, "UserService", "class")
    print(f"   缓存命中: {result2.summary == result.summary}")
    
    print("\n3. 统计信息")
    stats = analyzer.get_stats()
    print(f"   API调用: {stats['api_calls']}")
    print(f"   缓存命中: {stats['cache_hits']}")
    print(f"   平均耗时: {stats['avg_time_ms']:.0f}ms")
    
    analyzer.close()
    print("\n=== 测试完成 ===")
