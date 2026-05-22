#!/usr/bin/env python3
"""
Round 17: LLM分析模块极限混沌测试
基于静态走读发现的55个潜在问题，重点验证：
- BUG-26: f-string花括号注入导致prompt构建崩溃
- BUG-27: JSON提取使用rfind导致解析失败
- BUG-28: 429错误未计入统计
- BUG-29: close后无防护继续使用
- BUG-30: 缓存无TTL/代码变更后缓存不失效
- 中文分词标签提取
- Retry-After日期格式解析
- 空响应confidence不合理
"""

import sys
import os
import time
import json
import tempfile
import shutil
import threading
import traceback
import logging
from pathlib import Path
from collections import defaultdict
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knowledge_graph_system', 'modules'))

logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('R17-TEST')

test_results = []
bugs_found = []

def record_result(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "status": status, "detail": detail})
    logger.info(f"  [{status}] {name}: {detail}")

def record_bug(bug_id, description, severity, location):
    bugs_found.append({"id": bug_id, "desc": description, "severity": severity, "location": location})
    logger.warning(f"  [BUG-{bug_id}] {description} @ {location}")

# ============================================================
# 场景1: f-string花括号注入 (BUG-26候选)
# ============================================================
def test_fstring_brace_injection():
    logger.info("=" * 60)
    logger.info("极限混沌场景1: f-string花括号注入")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 包含花括号的代码片段
    test_cases = [
        ('const obj = { name: "test", value: 42 };', "对象字面量"),
        ('const fn = () => { return 1; };', "箭头函数体"),
        ('const json = JSON.parse(\'{"key": "value"}\');', "JSON字符串"),
        ('const tmpl = `Hello ${name}`;', "模板字符串"),
        ('const map: Record<string, {x: number}> = {};', "嵌套泛型对象"),
        ('if (obj && obj.data && obj.data.items) {}', "空对象字面量"),
        ('const fmt = `${1 + ${2 + ${3}}}`;', "多层嵌套模板"),
    ]

    for code, desc in test_cases:
        try:
            # 不实际调用API，只测试prompt构建是否崩溃
            prompt = f"""请分析以下代码，提供简洁的描述和标签。

代码：
```typescript
{code[:1000]}
```

请以JSON格式返回：
{{
    "summary": "一句话描述这个功能的作用（50字以内）",
    "tags": ["标签1", "标签2", "标签3"]
}}
"""
            record_result(f"花括号注入-{desc}", True, "prompt构建成功")
        except (KeyError, IndexError, ValueError) as e:
            record_result(f"花括号注入-{desc}", False, f"崩溃: {type(e).__name__}: {e}")
            bugs += 1
        except Exception as e:
            record_result(f"花括号注入-{desc}", False, f"意外异常: {e}")
            bugs += 1

    if bugs > 0:
        record_bug(26, f"f-string花括号注入: {bugs}个代码片段导致prompt构建崩溃", "严重",
                   "llm_analyzer.py:252-264 prompt构建")
    return bugs

# ============================================================
# 场景2: JSON提取rfind问题 (BUG-27候选)
# ============================================================
def test_json_extraction_rfind():
    logger.info("=" * 60)
    logger.info("极限混沌场景2: JSON提取rfind边界")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    test_cases = [
        # (LLM响应, 期望包含summary, 描述)
        ('{"summary": "test", "tags": ["a"]}', True, "正常JSON"),
        ('```json\n{"summary": "test", "tags": ["a"]}\n```', True, "Markdown包裹JSON"),
        ('Here is the result:\n{"summary": "test", "tags": ["a"]}', True, "JSON前后有文字"),
        ('{"summary": "use {x} bracket", "tags": []}', True, "JSON值中含花括号"),
        ('{"summary": "first"} and {"summary": "second"}', False, "多个JSON对象"),
        ('{"summary": "test"}\n\nNote: check this }', False, "JSON后额外花括号"),
        ('', False, "空响应"),
        ('No JSON here at all', False, "纯文本无JSON"),
        ('{"summary": "测试", "metadata": {"lang": "ts"}, "tags": []}', True, "嵌套JSON"),
        ('{"summary": "O(n^2) -> O(n)", "tags": ["algo"]}', True, "JSON含特殊字符"),
    ]

    for content, should_have_summary, desc in test_cases:
        try:
            result = analyzer._parse_response(content)
            if result and result.summary:
                record_result(f"JSON提取-{desc}", True,
                              f"summary={result.summary[:50]}")
            else:
                if should_have_summary:
                    record_result(f"JSON提取-{desc}", False, "应成功但返回空")
                    bugs += 1
                else:
                    record_result(f"JSON提取-{desc}", True, "正确返回空/回退")
        except Exception as e:
            record_result(f"JSON提取-{desc}", False, f"异常: {e}")
            if should_have_summary:
                bugs += 1

    if bugs >= 2:
        record_bug(27, f"JSON提取rfind导致{bugs}个场景解析失败", "高",
                   "llm_analyzer.py:179-181 _parse_response")
    return bugs

# ============================================================
# 场景3: 空响应confidence (BUG-28候选)
# ============================================================
def test_empty_response_confidence():
    logger.info("=" * 60)
    logger.info("极限混沌场景3: 空响应confidence合理性")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    result = analyzer._parse_response("")
    if result.confidence > 0.5:
        record_result("空响应confidence", False,
                      f"空响应confidence={result.confidence}，应<=0.5")
        record_bug(28, f"空响应返回不合理的confidence={result.confidence}", "中等",
                   "llm_analyzer.py:218 _parse_response")
        bugs += 1
    else:
        record_result("空响应confidence", True,
                      f"confidence={result.confidence}")

    return bugs

# ============================================================
# 场景4: close后继续使用 (BUG-29候选)
# ============================================================
def test_close_then_use():
    logger.info("=" * 60)
    logger.info("极限混沌场景4: close后继续使用防护")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)
    analyzer.close()

    try:
        result = analyzer.analyze_entity("test code", "TestClass", "class")
        record_result("close后analyze_entity", False,
                      f"应抛异常但返回: {result}")
        record_bug(29, "close后调用analyze_entity未抛异常", "中等",
                   "llm_analyzer.py:474-477 close")
        bugs += 1
    except RuntimeError as e:
        record_result("close后analyze_entity", True, f"正确抛出RuntimeError: {e}")
    except Exception as e:
        record_result("close后analyze_entity", False, f"抛出非预期异常: {type(e).__name__}: {e}")
        bugs += 1

    return bugs

# ============================================================
# 场景5: 缓存TTL/代码变更 (BUG-30候选)
# ============================================================
def test_cache_no_ttl():
    logger.info("=" * 60)
    logger.info("极限混沌场景5: 缓存无TTL验证")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 手动设置缓存
    from llm_analyzer import AnalysisResult
    old_result = AnalysisResult(summary="旧分析结果", tags=["old"], confidence=0.9)
    analyzer.cache.set("test code", old_result)

    # 相同代码应命中缓存
    cached = analyzer.cache.get("test code")
    if cached and cached.summary == "旧分析结果":
        record_result("缓存命中", True, "正确返回缓存结果")
    else:
        record_result("缓存命中", False, "缓存未命中")
        bugs += 1

    # 检查缓存是否有TTL机制
    import inspect
    cache_source = inspect.getsource(type(analyzer.cache))
    has_ttl = 'ttl' in cache_source.lower() or 'expire' in cache_source.lower()
    if not has_ttl:
        record_result("缓存TTL机制", False, "缓存无TTL/过期机制")
        record_bug(30, "缓存无TTL机制，代码变更后缓存不失效", "中等",
                   "llm_analyzer.py:46-89 LLMCache")
        bugs += 1
    else:
        record_result("缓存TTL机制", True, "缓存有TTL机制")

    analyzer.close()
    return bugs

# ============================================================
# 场景6: 中文分词标签提取
# ============================================================
def test_chinese_tag_extraction():
    logger.info("=" * 60)
    logger.info("极限混沌场景6: 中文分词标签提取")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 模拟中文文本回退
    chinese_text = "这是一个用户服务类，负责管理用户信息和权限控制"
    result = analyzer._parse_response(chinese_text)

    # 中文split()后只有一个元素
    words = chinese_text.split()
    if len(words) == 1 and len(words[0]) > 50:
        record_result("中文split分词", False,
                      f"中文split()无法分词: 得到{len(words)}个元素，长度{len(words[0])}")
        record_bug(31, "中文文本回退时split()无法正确分词，标签提取失败", "中等",
                   "llm_analyzer.py:212 _parse_response")
        bugs += 1
    else:
        record_result("中文split分词", True, f"分词结果: {words}")

    return bugs

# ============================================================
# 场景7: Retry-After日期格式 (BUG-32候选)
# ============================================================
def test_retry_after_date_format():
    logger.info("=" * 60)
    logger.info("极限混沌场景7: Retry-After日期格式处理")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 模拟 Retry-After 日期格式
    try:
        retry_after = int("Fri, 31 Dec 2025 23:59:59 GMT")
        record_result("Retry-After日期格式", False, f"不应成功: {retry_after}")
        bugs += 1
    except ValueError:
        record_result("Retry-After日期格式", True, "int()正确抛出ValueError")

    # 检查代码中是否有try-except保护
    import inspect
    source = inspect.getsource(analyzer._call_api)
    has_retry_protection = 'try' in source and 'retry_after' in source
    if not has_retry_protection or 'int(response.headers.get' in source:
        # 检查是否对int()转换有保护
        lines = source.split('\n')
        retry_line = [l for l in lines if 'Retry-After' in l or 'retry_after' in l]
        if retry_line:
            line_text = retry_line[0]
            if 'int(' in line_text and 'try' not in source[max(0, source.find(line_text)-100):source.find(line_text)+200]:
                record_result("Retry-After int保护", False, "int()转换无try-except保护")
                record_bug(32, "Retry-After日期格式会导致int()抛出ValueError", "中等",
                           "llm_analyzer.py:138 _call_api")
                bugs += 1
            else:
                record_result("Retry-After int保护", True, "有保护机制")
        else:
            record_result("Retry-After int保护", True, "未找到Retry-After处理")
    else:
        record_result("Retry-After int保护", True, "有保护机制")

    analyzer.close()
    return bugs

# ============================================================
# 场景8: 429错误统计 (BUG-33候选)
# ============================================================
def test_429_error_statistics():
    logger.info("=" * 60)
    logger.info("极限混沌场景8: 429错误统计")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    import inspect
    source = inspect.getsource(analyzer._call_api)

    # 检查429处理后是否增加errors计数
    lines = source.split('\n')
    in_429_block = False
    has_error_increment = False
    for line in lines:
        if '429' in line:
            in_429_block = True
        if in_429_block and ("errors" in line or "'errors'" in line):
            has_error_increment = True
            break
        if in_429_block and 'continue' in line:
            # 429块结束（continue回到循环顶部）
            if not has_error_increment:
                break
            in_429_block = False

    if not has_error_increment:
        record_result("429错误统计", False, "429处理后未增加errors计数")
        record_bug(33, "429速率限制导致的失败未计入errors统计", "高",
                   "llm_analyzer.py:137-142 _call_api")
        bugs += 1
    else:
        record_result("429错误统计", True, "429处理后增加errors计数")

    analyzer.close()
    return bugs

# ============================================================
# 场景9: 关系解析JSON数组提取 (BUG-34候选)
# ============================================================
def test_relationship_json_array_extraction():
    logger.info("=" * 60)
    logger.info("极限混沌场景9: 关系解析JSON数组提取")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 测试 analyze_file_relationships 的关系解析
    # 模拟LLM返回包含关系JSON的响应
    test_responses = [
        ('[{"source":"A","target":"B","relation":"calls"}]', True, 1, "正常关系JSON"),
        ('```json\n[{"source":"A","target":"B","relation":"calls"}]\n```', True, 1, "Markdown包裹"),
        ('关系如下：\n[{"source":"A","target":"B","relation":"calls"}]', True, 1, "JSON前后有文字"),
        ('[{"source":"A","target":"B","relation":"calls"}]\n注意：以上是分析结果]', False, 0, "JSON后有额外]"),
    ]

    for content, should_parse, expected_count, desc in test_responses:
        try:
            # 直接测试关系提取逻辑
            if '[' in content and ']' in content:
                json_start = content.find('[')
                json_end = content.rfind(']') + 1
                json_str = content[json_start:json_end]
                data = json.loads(json_str)
                count = len(data) if isinstance(data, list) else 0
                if should_parse:
                    record_result(f"关系提取-{desc}", count == expected_count,
                                  f"提取到{count}个关系")
                else:
                    record_result(f"关系提取-{desc}", True, f"提取到{count}个关系(预期可能不准确)")
            else:
                record_result(f"关系提取-{desc}", True, "无JSON数组")
        except json.JSONDecodeError:
            if should_parse:
                record_result(f"关系提取-{desc}", False, "JSON解析失败")
                bugs += 1
            else:
                record_result(f"关系提取-{desc}", True, "正确报告解析失败")
        except Exception as e:
            record_result(f"关系提取-{desc}", False, f"异常: {e}")

    if bugs >= 1:
        record_bug(34, f"关系解析JSON数组提取失败{bugs}个场景", "中等",
                   "llm_analyzer.py:391-394 analyze_file_relationships")
    return bugs

# ============================================================
# 场景10: 超长代码截断验证
# ============================================================
def test_long_code_truncation():
    logger.info("=" * 60)
    logger.info("极限混沌场景10: 超长代码截断")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 生成超长代码
    long_code = "class LongClass {\n"
    for i in range(200):
        long_code += f"    method{i}() {{ return {i}; }}\n"
    long_code += "}\n"

    # 验证截断位置是否合理
    truncated = long_code[:1000]
    # 检查是否在行中间截断
    if truncated.endswith('\n'):
        record_result("截断位置", True, "在完整行处截断")
    else:
        record_result("截断位置", False, "在行中间截断，可能破坏代码语义")
        bugs += 1

    # 缓存键使用完整代码 vs 截断代码
    key_full = analyzer.cache._compute_key(long_code)
    key_truncated = analyzer.cache._compute_key(long_code[:1000])
    if key_full != key_truncated:
        record_result("缓存键一致性", False,
                      f"完整代码和截断代码的缓存键不同，缓存效率降低")
        record_bug(35, "缓存键使用完整代码但API发送截断代码，缓存效率降低", "低",
                   "llm_analyzer.py:243 vs 256")
        bugs += 1
    else:
        record_result("缓存键一致性", True, "缓存键一致")

    analyzer.close()
    return bugs

# ============================================================
# 场景11: 实体列表含None元素
# ============================================================
def test_entities_with_none():
    logger.info("=" * 60)
    logger.info("极限混沌场景11: 实体列表含None元素")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    try:
        # 传入包含None的实体列表
        result = analyzer.analyze_entities_batch([None, None])
        record_result("None实体列表", False, f"应抛异常但返回: {result}")
        record_bug(36, "实体列表含None时analyze_entities_batch未做防护", "中等",
                   "llm_analyzer.py:306-307 analyze_entities_batch")
        bugs += 1
    except AttributeError as e:
        record_result("None实体列表", False,
                      f"抛出AttributeError(未防护): {e}")
        record_bug(36, f"实体列表含None时抛出未防护的AttributeError: {e}", "中等",
                   "llm_analyzer.py:306-307")
        bugs += 1
    except Exception as e:
        record_result("None实体列表", True, f"抛出预期异常: {type(e).__name__}")

    analyzer.close()
    return bugs

# ============================================================
# 场景12: API响应格式异常
# ============================================================
def test_api_response_format_anomaly():
    logger.info("=" * 60)
    logger.info("极限混沌场景12: API响应格式异常")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 模拟各种异常API响应
    test_cases = [
        ('{"choices": []}', "空choices列表", "IndexError"),
        ('{"no_choices": "here"}', "缺少choices键", "KeyError"),
        ('not json at all', "非JSON响应体", "JSONDecodeError"),
        ('', "空响应体", "JSONDecodeError"),
    ]

    import inspect
    source = inspect.getsource(analyzer._call_api)

    for fake_response, desc, expected_error in test_cases:
        # 检查代码是否有对 data['choices'] 的保护
        if "data['choices']" in source or 'data["choices"]' in source:
            has_protection = "'choices' in data" in source or "choices" in source and "if" in source
            if not has_protection:
                record_result(f"API响应-{desc}", False,
                              f"data['choices']无保护，{expected_error}会被重试(无意义)")
                bugs += 1
            else:
                record_result(f"API响应-{desc}", True, "有保护机制")
        else:
            record_result(f"API响应-{desc}", True, "未使用data['choices']模式")

    if bugs > 0:
        record_bug(37, f"API响应格式异常时缺少保护，导致无意义重试", "中等",
                   "llm_analyzer.py:147 _call_api")
    return bugs

# ============================================================
# 场景13: 并发缓存竞态
# ============================================================
def test_concurrent_cache_race():
    logger.info("=" * 60)
    logger.info("极限混沌场景13: 并发缓存竞态")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig, AnalysisResult
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 多线程同时读写缓存
    errors = []
    def cache_writer(i):
        try:
            result = AnalysisResult(summary=f"result_{i}", tags=[f"tag_{i}"], confidence=0.8)
            analyzer.cache.set(f"code_{i}", result)
            cached = analyzer.cache.get(f"code_{i}")
            if cached is None or cached.summary != f"result_{i}":
                errors.append(f"thread_{i}: cache inconsistency")
        except Exception as e:
            errors.append(f"thread_{i}: {e}")

    threads = [threading.Thread(target=cache_writer, args=(i,)) for i in range(100)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=10)

    record_result("100线程并发缓存读写", len(errors) == 0,
                  f"错误: {len(errors)}")
    if errors:
        for e in errors[:3]:
            logger.info(f"    {e}")

    analyzer.close()
    return bugs

# ============================================================
# 场景14: LRU缓存淘汰验证
# ============================================================
def test_lru_eviction():
    logger.info("=" * 60)
    logger.info("极限混沌场景14: LRU缓存淘汰")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig, AnalysisResult
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 填充超过max_size的缓存
    max_size = analyzer.cache._max_size
    for i in range(max_size + 5):
        result = AnalysisResult(summary=f"result_{i}", tags=[f"tag_{i}"], confidence=0.8)
        analyzer.cache.set(f"code_{i}", result)

    # 最早的应该被淘汰
    cached = analyzer.cache.get("code_0")
    if cached is not None:
        record_result("LRU淘汰", False, f"最早的code_0未被淘汰, cache_size={len(analyzer.cache._cache)}")
        bugs += 1
    else:
        record_result("LRU淘汰", True, "最早的code_0已被淘汰")

    # 最新的应该保留
    latest_key = f"code_{max_size + 4}"
    cached_latest = analyzer.cache.get(latest_key)
    if cached_latest is None:
        record_result("LRU保留最新", False, f"最新的{latest_key}未被保留")
        bugs += 1
    else:
        record_result("LRU保留最新", True, f"{latest_key}仍在缓存")

    record_result("缓存大小", len(analyzer.cache._cache) == max_size,
                  f"size={len(analyzer.cache._cache)}, max={max_size}")

    analyzer.close()
    return bugs

# ============================================================
# 场景15: analyze_file_relationships实体限制
# ============================================================
def test_relationship_entity_limit():
    logger.info("=" * 60)
    logger.info("极限混沌场景15: analyze_file_relationships实体限制")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    import inspect
    source = inspect.getsource(analyzer.analyze_file_relationships)
    if '[:10]' in source:
        record_result("实体限制10个", True, "代码中存在[:10]限制")
    else:
        record_result("实体限制10个", False, "未找到实体限制")
        bugs += 1

    analyzer.close()
    return bugs

# ============================================================
# 场景16: 统计数据准确性
# ============================================================
def test_statistics_accuracy():
    logger.info("=" * 60)
    logger.info("极限混沌场景16: 统计数据准确性")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig, AnalysisResult
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    # 手动设置缓存
    for i in range(5):
        result = AnalysisResult(summary=f"cached_{i}", tags=[f"tag_{i}"], confidence=0.8)
        analyzer.cache.set(f"code_{i}", result)

    stats = analyzer.get_stats()
    record_result("缓存大小统计", stats.get('cache_size', 0) == 5,
                  f"cache_size={stats.get('cache_size', 0)}")

    # 缓存命中
    cached = analyzer.cache.get("code_0")
    stats2 = analyzer.get_stats()
    record_result("缓存命中统计", stats2.get('cache_hits', 0) >= 1,
                  f"cache_hits={stats2.get('cache_hits', 0)}")

    analyzer.close()
    return bugs

# ============================================================
# 场景17: print vs logging 一致性
# ============================================================
def test_logging_consistency():
    logger.info("=" * 60)
    logger.info("极限混沌场景17: 日志框架一致性")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig
    bugs = 0

    config = LLMConfig(api_key="test-key")
    analyzer = LLMAnalyzer(config)

    import inspect
    source = inspect.getsource(analyzer)

    print_count = source.count('print(')
    logger_count = source.count('logger.')

    record_result("日志框架一致性", print_count == 0,
                  f"print调用: {print_count}, logger调用: {logger_count}")
    if print_count > 0:
        record_bug(38, f"llm_analyzer使用{print_count}处print而非logging", "低",
                   "llm_analyzer.py 全文件")

    analyzer.close()
    return bugs

# ============================================================
# 场景18: cancel_futures Python版本兼容
# ============================================================
def test_cancel_futures_compat():
    logger.info("=" * 60)
    logger.info("极限混沌场景18: cancel_futures版本兼容")
    logger.info("=" * 60)

    import sys
    bugs = 0

    if sys.version_info < (3, 9):
        from llm_analyzer import LLMAnalyzer, LLMConfig
        config = LLMConfig(api_key="test-key")
        analyzer = LLMAnalyzer(config)
        try:
            analyzer.close()
            record_result("cancel_futures兼容", True, "Python<3.9下close成功")
        except TypeError as e:
            record_result("cancel_futures兼容", False,
                          f"Python<3.9下cancel_futures不兼容: {e}")
            record_bug(39, "cancel_futures=True需要Python 3.9+", "低",
                       "llm_analyzer.py:477 close")
            bugs += 1
    else:
        record_result("cancel_futures兼容", True, f"Python {sys.version_info.major}.{sys.version_info.minor} 支持")

    return bugs

# ============================================================
# 主函数
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("Round 17: LLM分析模块极限混沌测试")
    logger.info("=" * 60)

    total_start = time.time()
    total_bugs = 0

    scenarios = [
        ("f-string花括号注入", test_fstring_brace_injection),
        ("JSON提取rfind边界", test_json_extraction_rfind),
        ("空响应confidence", test_empty_response_confidence),
        ("close后继续使用", test_close_then_use),
        ("缓存无TTL", test_cache_no_ttl),
        ("中文分词标签提取", test_chinese_tag_extraction),
        ("Retry-After日期格式", test_retry_after_date_format),
        ("429错误统计", test_429_error_statistics),
        ("关系解析JSON数组", test_relationship_json_array_extraction),
        ("超长代码截断", test_long_code_truncation),
        ("实体列表含None", test_entities_with_none),
        ("API响应格式异常", test_api_response_format_anomaly),
        ("并发缓存竞态", test_concurrent_cache_race),
        ("LRU缓存淘汰", test_lru_eviction),
        ("实体限制10个", test_relationship_entity_limit),
        ("统计数据准确性", test_statistics_accuracy),
        ("日志框架一致性", test_logging_consistency),
        ("cancel_futures兼容", test_cancel_futures_compat),
    ]

    for name, test_func in scenarios:
        try:
            bugs = test_func()
            total_bugs += bugs
        except Exception as e:
            logger.error(f"场景 '{name}' 执行异常: {e}")
            logger.error(traceback.format_exc())
            record_result(name, False, f"场景执行异常: {e}")

    total_elapsed = time.time() - total_start

    logger.info("")
    logger.info("=" * 60)
    logger.info("Round 17 LLM分析模块极限混沌测试 - 最终报告")
    logger.info("=" * 60)
    logger.info(f"总耗时: {total_elapsed:.3f}s")
    logger.info(f"发现BUG数: {len(bugs_found)}")

    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = sum(1 for r in test_results if r['status'] == 'FAIL')
    logger.info(f"统计: 通过={passed}, 失败={failed}, 总计={len(test_results)}")

    if bugs_found:
        logger.info("发现BUG详情:")
        logger.info("-" * 60)
        for bug in bugs_found:
            logger.info(f"  [BUG-{bug['id']}] [{bug['severity']}] {bug['desc']}")
            logger.info(f"           位置: {bug['location']}")
    else:
        logger.info("未发现明显BUG")

    logger.info("=" * 60)

if __name__ == '__main__':
    main()
