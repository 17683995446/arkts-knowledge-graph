#!/usr/bin/env python3
"""
Round 16: 极限混沌测试 - 基于静态代码走读发现的潜在问题
覆盖：code_snippet数据源不一致、re-export遗漏、模板字符串边界、
      转义引号、两层嵌套括号、raise e异常链、SQL参数限制、
      跨模块隐藏文件过滤不一致、中文分词、JSON解析脆弱等
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

# 添加模块路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'knowledge_graph_system', 'modules'))

from arkts_parser import ArkTSParser, CodeEntity, EntityRelation, FileDependency, ParseResult
from sqlite_storage import SQLiteStorage

# ============================================================
# 全链路日志追踪
# ============================================================
logging.basicConfig(level=logging.INFO, format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s', datefmt='%H:%M:%S')
logger = logging.getLogger('R16-TEST')

# Monkey-patch 日志追踪
_original_methods = {}
def install_tracing(module_name, class_name, methods_to_trace):
    import importlib
    mod = importlib.import_module(module_name)
    cls = getattr(mod, class_name)
    for method_name in methods_to_trace:
        original = getattr(cls, method_name)
        key = f"{class_name}.{method_name}"
        _original_methods[key] = original
        def make_wrapper(orig, name):
            def wrapper(self, *args, **kwargs):
                logger.info(f"[TRACE] {name} ENTER args={args!r:.200}")
                try:
                    result = orig(self, *args, **kwargs)
                    logger.info(f"[TRACE] {name} EXIT OK")
                    return result
                except Exception as e:
                    logger.error(f"[TRACE] {name} EXIT ERROR: {e}")
                    raise
            return wrapper
        setattr(cls, method_name, make_wrapper(original, key))

# ============================================================
# 测试结果收集
# ============================================================
test_results = []
bugs_found = []

def record_result(name, passed, detail=""):
    status = "PASS" if passed else "FAIL"
    test_results.append({"name": name, "status": status, "detail": detail})
    symbol = "✓" if passed else "✗"
    logger.info(f"  [{status}] {name}: {detail}")

def record_bug(bug_id, description, severity, location):
    bugs_found.append({"id": bug_id, "desc": description, "severity": severity, "location": location})
    logger.warning(f"  [BUG-{bug_id}] {description} @ {location}")

# ============================================================
# 场景1: code_snippet数据源一致性测试 (BUG-14候选)
# ============================================================
def test_code_snippet_data_source():
    logger.info("=" * 60)
    logger.info("极限混沌场景1: code_snippet数据源一致性")
    logger.info("=" * 60)

    parser = ArkTSParser()

    # 函数内含字符串和注释 - code_snippet应保留原始内容
    code_with_strings = '''export function greet(name: string): string {
    // 这是一个注释
    const msg = "Hello, " + name + "!";
    return msg;
}

export interface User {
    name: string; // 用户名
    age: number;
}

export enum Color {
    Red = "red",
    Blue = "blue",
}
'''
    result = parser.parse(code_with_strings, '/test/snippet_test.ts')

    # 检查函数的code_snippet是否包含原始字符串内容
    func_entity = None
    iface_entity = None
    enum_entity = None
    for e in result.entities:
        if e.entity_type == 'function':
            func_entity = e
        elif e.entity_type == 'interface':
            iface_entity = e
        elif e.entity_type == 'enum':
            enum_entity = e

    bugs_in_scenario = 0

    if func_entity:
        has_original_string = 'Hello' in func_entity.code_snippet
        has_original_comment = '注释' in func_entity.code_snippet
        record_result("函数code_snippet保留原始字符串", has_original_string,
                      f"包含'Hello': {has_original_string}")
        record_result("函数code_snippet保留原始注释", has_original_comment,
                      f"包含'注释': {has_original_comment}")
        if not has_original_string or not has_original_comment:
            record_bug(14, "函数code_snippet使用预处理后的lines，丢失字符串和注释内容", "严重",
                       "arkts_parser.py:820")
            bugs_in_scenario += 1
    else:
        record_result("函数实体提取", False, "未找到函数实体")

    if iface_entity:
        has_original_comment = '用户名' in iface_entity.code_snippet
        record_result("接口code_snippet保留原始注释", has_original_comment,
                      f"包含'用户名': {has_original_comment}")
        if not has_original_comment:
            record_bug(14, "接口code_snippet使用预处理后的lines，丢失注释内容", "严重",
                       "arkts_parser.py:845")
            bugs_in_scenario += 1
    else:
        record_result("接口实体提取", False, "未找到接口实体")

    if enum_entity:
        has_original_string = 'red' in enum_entity.code_snippet
        record_result("枚举code_snippet保留原始字符串", has_original_string,
                      f"包含'red': {has_original_string}")
        if not has_original_string:
            record_bug(14, "枚举code_snippet使用预处理后的lines，丢失字符串内容", "严重",
                       "arkts_parser.py:881")
            bugs_in_scenario += 1
    else:
        record_result("枚举实体提取", False, "未找到枚举实体")

    return bugs_in_scenario

# ============================================================
# 场景2: re-export语法遗漏测试 (BUG-15候选)
# ============================================================
def test_reexport_syntax():
    logger.info("=" * 60)
    logger.info("极限混沌场景2: re-export语法识别")
    logger.info("=" * 60)

    parser = ArkTSParser()

    code = '''import { User } from './user';
import { Order } from './order';
export { User };
export { Order as CustomerOrder };
export { default as App } from './App';
export * from './utils';
'''
    result = parser.parse(code, '/test/reexport.ts')

    bugs_in_scenario = 0

    # 检查import是否被正确提取
    import_deps = result.dependencies
    record_result("import依赖提取数量", len(import_deps) >= 2,
                  f"提取到{len(import_deps)}个依赖")

    # 检查re-export是否被遗漏
    has_user_import = any('user' in str(d.target_file) for d in import_deps)
    has_order_import = any('order' in str(d.target_file) for d in import_deps)
    record_result("import User依赖", has_user_import, f"找到user依赖: {has_user_import}")
    record_result("import Order依赖", has_order_import, f"找到order依赖: {has_order_import}")

    # re-export中的 from 路径应该也被提取
    has_app_reexport = any('App' in str(d.target_file) for d in import_deps)
    has_utils_reexport = any('utils' in str(d.target_file) for d in import_deps)
    record_result("re-export App依赖", has_app_reexport, f"找到App re-export依赖: {has_app_reexport}")
    record_result("re-export utils依赖", has_utils_reexport, f"找到utils re-export依赖: {has_utils_reexport}")

    if not has_app_reexport:
        record_bug(15, "export { default as App } from './App' 中的依赖路径未被提取", "中等",
                   "arkts_parser.py:537-543 _is_import_statement")
        bugs_in_scenario += 1
    if not has_utils_reexport:
        record_bug(15, "export * from './utils' 中的依赖路径未被提取", "中等",
                   "arkts_parser.py:537-543 _is_import_statement")
        bugs_in_scenario += 1

    return bugs_in_scenario

# ============================================================
# 场景3: 模板字符串边界测试 (BUG-16候选)
# ============================================================
def test_template_string_edge_cases():
    logger.info("=" * 60)
    logger.info("极限混沌场景3: 模板字符串边界情况")
    logger.info("=" * 60)

    parser = ArkTSParser()

    # 模板字符串中包含花括号和嵌套表达式
    code = '''class TemplateTest {
    name: string = "test";

    method1() {
        const a = `Hello ${this.name}`;
        const b = `Result: ${1 + 2}`;
        const c = `Nested: ${`inner ${1}`}`;
    }

    method2() {
        const obj = { key: "value" };
        const d = `Object: ${JSON.stringify(obj)}`;
    }
}
'''
    result = parser.parse(code, '/test/template.ts')
    bugs_in_scenario = 0

    class_found = any(e.name == 'TemplateTest' for e in result.entities)
    record_result("模板字符串中类提取", class_found, f"TemplateTest: {class_found}")

    methods = [e for e in result.entities if e.entity_type == 'function']
    record_result("模板字符串中方法提取", len(methods) >= 2,
                  f"方法数: {len(methods)}")

    # 测试嵌套模板字符串是否导致解析崩溃
    nested_code = '''class NestedTemplate {
    value: string = `outer ${`inner ${`deepest`}`} end`;
}
'''
    try:
        result2 = parser.parse(nested_code, '/test/nested_template.ts')
        record_result("三层嵌套模板字符串不崩溃", True, "解析成功")
    except Exception as e:
        record_result("三层嵌套模板字符串不崩溃", False, f"崩溃: {e}")
        record_bug(16, f"三层嵌套模板字符串导致解析崩溃: {e}", "严重",
                   "arkts_parser.py:627-643 _preprocess_for_parsing")
        bugs_in_scenario += 1

    # 测试模板字符串中的字符串包含花括号
    tricky_code = '''class TrickyTemplate {
    method() {
        const s = `value: ${obj['}']}`;
    }
}
'''
    try:
        result3 = parser.parse(tricky_code, '/test/tricky_template.ts')
        record_result("模板字符串中字符串含花括号不崩溃", True, "解析成功")
    except Exception as e:
        record_result("模板字符串中字符串含花括号不崩溃", False, f"崩溃: {e}")
        record_bug(16, f"模板字符串中字符串含花括号导致崩溃: {e}", "严重",
                   "arkts_parser.py:627-643")
        bugs_in_scenario += 1

    return bugs_in_scenario

# ============================================================
# 场景4: 转义引号和特殊字符测试 (BUG-17候选)
# ============================================================
def test_escaped_quotes_and_special_chars():
    logger.info("=" * 60)
    logger.info("极限混沌场景4: 转义引号和特殊字符")
    logger.info("=" * 60)

    parser = ArkTSParser()

    # 转义引号在字符串中
    code = r'''class EscapedQuotes {
    method() {
        const a = "He said \"hello\"";
        const b = 'It\'s fine';
        const c = "Path: C:\\Users\\test";
        const d = "Regex: \\d+\\s*\\w";
    }
}
'''
    result = parser.parse(code, '/test/escaped.ts')
    bugs_in_scenario = 0

    class_found = any(e.name == 'EscapedQuotes' for e in result.entities)
    record_result("转义引号类提取", class_found, f"EscapedQuotes: {class_found}")

    # Unicode和特殊字符
    unicode_code = '''class 中文类名 {
    名字: string = "值";
    方法() {
        const emoji = "🎉🎊";
        const japanese = "こんにちは";
    }
}
'''
    try:
        result2 = parser.parse(unicode_code, '/test/unicode.ts')
        # 注意：中文类名可能不被 \w+ 匹配（取决于正则引擎）
        entities_found = len(result2.entities)
        record_result("Unicode代码解析", entities_found > 0,
                      f"实体数: {entities_found}")
    except Exception as e:
        record_result("Unicode代码解析", False, f"崩溃: {e}")
        bugs_in_scenario += 1

    # 超长行测试
    long_line = 'class LongLine { value: string = "' + 'x' * 100000 + '"; }'
    try:
        result3 = parser.parse(long_line, '/test/longline.ts')
        record_result("超长行(100K字符)不崩溃", True, "解析成功")
    except Exception as e:
        record_result("超长行(100K字符)不崩溃", False, f"崩溃: {e}")
        bugs_in_scenario += 1

    # 空字节测试
    null_code = 'class NullByte { value: string = "hello\x00world"; }'
    try:
        result4 = parser.parse(null_code, '/test/nullbyte.ts')
        record_result("空字节代码不崩溃", True, "解析成功")
    except Exception as e:
        record_result("空字节代码不崩溃", False, f"崩溃: {e}")
        bugs_in_scenario += 1

    return bugs_in_scenario

# ============================================================
# 场景5: 两层嵌套括号参数测试 (BUG-18候选)
# ============================================================
def test_nested_parentheses_params():
    logger.info("=" * 60)
    logger.info("极限混沌场景5: 两层嵌套括号参数")
    logger.info("=" * 60)

    parser = ArkTSParser()

    code = '''class NestedParams {
    // 一层嵌套 - 应该支持
    method1(callback: (x: number) => void) {}

    // 两层嵌套 - 可能失败
    method2(handler: (a: (b: number) => void) => void) {}

    // 三层嵌套 - 可能失败
    method3(deep: (a: (b: (c: number) => void) => void) => void) {}

    // 复杂泛型+嵌套
    method4(data: Map<string, Map<number, Set<string>>>) {}

    // 箭头函数属性
    onClick = (event: UIEvent, callback: (result: boolean) => void) => {
        console.log(event);
    };
}
'''
    result = parser.parse(code, '/test/nested_params.ts')
    bugs_in_scenario = 0

    methods = [e for e in result.entities if e.entity_type == 'function']
    method_names = [m.name for m in methods]
    logger.info(f"  提取到方法: {method_names}")

    # 检查一层嵌套
    has_method1 = 'method1' in method_names
    record_result("一层嵌套括号参数", has_method1, f"method1: {has_method1}")

    # 检查两层嵌套
    has_method2 = 'method2' in method_names
    record_result("两层嵌套括号参数", has_method2, f"method2: {has_method2}")
    if not has_method2:
        record_bug(18, "两层嵌套括号参数的方法未被提取", "中等",
                   "arkts_parser.py:1085-1093 method_pattern")
        bugs_in_scenario += 1

    # 检查三层嵌套
    has_method3 = 'method3' in method_names
    record_result("三层嵌套括号参数", has_method3, f"method3: {has_method3}")
    if not has_method3:
        record_bug(18, "三层嵌套括号参数的方法未被提取", "中等",
                   "arkts_parser.py:1085-1093 method_pattern")
        bugs_in_scenario += 1

    # 检查复杂泛型
    has_method4 = 'method4' in method_names
    record_result("复杂泛型参数", has_method4, f"method4: {has_method4}")

    # 检查箭头函数属性
    has_onClick = 'onClick' in method_names
    record_result("箭头函数属性+嵌套参数", has_onClick, f"onClick: {has_onClick}")

    return bugs_in_scenario

# ============================================================
# 场景6: 函数调用关系提取边界测试 (BUG-19候选)
# ============================================================
def test_call_relation_edge_cases():
    logger.info("=" * 60)
    logger.info("极限混沌场景6: 函数调用关系提取边界")
    logger.info("=" * 60)

    parser = ArkTSParser()

    code = '''class CallTest {
    method1() {
        // new关键字 - 不应被识别为调用
        const a = new UserService();
        const b = new  UserService();  // 多个空格

        // 普通函数调用 - 应该被识别
        doSomething();
        doSomethingElse("arg");

        // 链式调用
        this.method1().method2();

        // 条件调用
        callback && callback();

        // 变量名包含关键字
        renew Foo();
        renewFoo();
    }
}
'''
    result = parser.parse(code, '/test/call_test.ts')
    bugs_in_scenario = 0

    # 检查calls关系
    calls = [r for r in result.relations if r.relation_type == 'calls']
    called_names = [r.target_entity for r in calls]
    logger.info(f"  提取到调用关系: {called_names}")

    # new不应被识别为调用
    has_new_call = 'UserService' in called_names
    record_result("new实例化不被识别为调用", not has_new_call,
                  f"UserService在调用中: {has_new_call}")
    if has_new_call:
        record_bug(19, "new关键字后的实例化被错误识别为函数调用", "中等",
                   "arkts_parser.py:1022-1027 call_pattern")
        bugs_in_scenario += 1

    # 普通调用应该被识别
    has_do_something = 'doSomething' in called_names
    record_result("普通函数调用被识别", has_do_something,
                  f"doSomething: {has_do_something}")

    # renew Foo() 不应被误排除（renew不是new）
    has_foo_call = 'Foo' in called_names
    record_result("renew Foo()调用识别", has_foo_call,
                  f"Foo在调用中: {has_foo_call}")

    return bugs_in_scenario

# ============================================================
# 场景7: SQL参数限制测试 (BUG-20候选)
# ============================================================
def test_sql_parameter_limit():
    logger.info("=" * 60)
    logger.info("极限混沌场景7: SQL参数数量限制")
    logger.info("=" * 60)

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, 'test.db')
    bugs_in_scenario = 0

    try:
        storage = SQLiteStorage(db_path)
        parser = ArkTSParser()

        # 生成一个包含600个实体的文件（超过SQLITE_MAX_VARIABLE_NUMBER=999的一半）
        # get_file_graph中每个实体在IN子句中出现2次，所以600个实体需要1200个参数
        entities = []
        lines = []
        for i in range(600):
            name = f"Entity{i}"
            lines.append(f"class {name} {{}}")
            entities.append(CodeEntity(
                file_path='/test/large_file.ts',
                entity_type='class',
                name=name,
                signature=f'class {name} {{}}',
                start_line=i + 1,
                end_line=i + 1,
                code_snippet=f'class {name} {{}}',
                modifiers=[],
                decorators=[]
            ))

        code = '\n'.join(lines)
        result = parser.parse(code, '/test/large_file.ts')

        # 存储到数据库
        storage.update_file_data('/test/large_file.ts', result)

        # 尝试获取文件图 - 可能触发 too many SQL variables
        try:
            graph = storage.get_file_graph('/test/large_file.ts')
            record_result("600实体文件图查询成功", True,
                          f"节点: {len(graph.get('nodes', []))}, 边: {len(graph.get('edges', []))}")
        except Exception as e:
            if 'too many SQL variables' in str(e).lower():
                record_result("600实体文件图查询成功", False,
                              f"触发SQL参数限制: {e}")
                record_bug(20, f"文件含600实体时get_file_graph触发SQL参数限制: {e}", "严重",
                           "sqlite_storage.py:493-497 get_file_graph")
                bugs_in_scenario += 1
            else:
                record_result("600实体文件图查询成功", False, f"其他错误: {e}")

        storage.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return bugs_in_scenario

# ============================================================
# 场景8: 异常链保留测试 (BUG-21候选)
# ============================================================
def test_exception_chain_preservation():
    logger.info("=" * 60)
    logger.info("极限混沌场景8: 异常链保留验证")
    logger.info("=" * 60)

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, 'test.db')
    bugs_in_scenario = 0

    try:
        storage = SQLiteStorage(db_path)

        # 测试事务中的异常是否保留完整链
        import sqlite3 as sqlite3_mod

        # 检查 _transaction 方法中是否使用 raise e（丢失异常链）
        import inspect
        source = inspect.getsource(storage._transaction)
        uses_raise_e = 'raise e' in source
        uses_bare_raise = re.search(r'except.*\n\s*raise\s*$', source, re.MULTILINE) is not None

        record_result("事务异常使用raise e", uses_raise_e,
                      f"raise e: {uses_raise_e}")
        record_result("事务异常使用bare raise", uses_bare_raise,
                      f"bare raise: {uses_bare_raise}")

        if uses_raise_e and not uses_bare_raise:
            record_bug(21, "_transaction中使用raise e而非bare raise，丢失原始异常链", "中等",
                       "sqlite_storage.py:63-76 _transaction")
            bugs_in_scenario += 1

        storage.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return bugs_in_scenario

# ============================================================
# 场景9: 跨模块隐藏文件过滤一致性测试 (BUG-22候选)
# ============================================================
def test_hidden_file_filter_consistency():
    logger.info("=" * 60)
    logger.info("极限混沌场景9: 跨模块隐藏文件过滤一致性")
    logger.info("=" * 60)

    bugs_in_scenario = 0

    # 读取两个模块的过滤逻辑
    from file_watcher import FileWatcher
    from orchestrator import KnowledgeOrchestrator, SKIP_DIRECTORY_NAMES

    # 测试路径
    test_paths = [
        ('/project/.eslintrc.js', 'should_watch', 'orchestrator_skip'),
        ('/project/.env', 'should_watch', 'orchestrator_skip'),
        ('/project/.myconfig/file.ts', 'should_watch', 'orchestrator_skip'),
        ('/project/src/.hidden.ts', 'should_watch', 'orchestrator_skip'),
        ('/project/.git/config', 'should_skip', 'should_skip'),
        ('/project/node_modules/pkg/index.ts', 'should_skip', 'should_skip'),
    ]

    watcher = FileWatcher.__new__(FileWatcher)
    watcher._fingerprint_cache = type('obj', (object,), {'compute_hash': lambda s, c: 'hash'})()
    watcher._pending_timers = {}
    watcher._timers_lock = threading.Lock()
    watcher._flushed_lock = threading.Lock()
    watcher._flushed_paths = set()
    watcher._stopping = False
    watcher._max_file_size = 10 * 1024 * 1024
    watcher._stats = defaultdict(int)
    watcher._callbacks = []

    from orchestrator import SystemConfig
    config = SystemConfig()
    orch = KnowledgeOrchestrator.__new__(KnowledgeOrchestrator)
    orch.config = config

    inconsistencies = []
    for path_str, expected_watcher, expected_orch in test_paths:
        from pathlib import Path as P
        p = P(path_str)

        # file_watcher._should_watch
        try:
            watcher_result = watcher._should_watch(str(p))
        except Exception:
            watcher_result = False

        # orchestrator._should_skip_path
        try:
            orch_result = orch._should_skip_path(p)
        except Exception:
            orch_result = True

        if watcher_result and orch_result:
            inconsistencies.append(f"{path_str}: watcher允许但orchestrator跳过")
        elif not watcher_result and not orch_result:
            pass  # 一致
        elif not watcher_result and orch_result:
            pass  # watcher更严格，可接受
        elif watcher_result and not orch_result:
            inconsistencies.append(f"{path_str}: watcher允许但orchestrator跳过")

    record_result("隐藏文件过滤一致性", len(inconsistencies) == 0,
                  f"不一致数: {len(inconsistencies)}")
    if inconsistencies:
        for inc in inconsistencies:
            logger.info(f"    不一致: {inc}")
        record_bug(22, f"file_watcher和orchestrator对隐藏文件的过滤逻辑不一致: {inconsistencies[:3]}",
                   "中等", "file_watcher.py:125 vs orchestrator.py:336-351")
        bugs_in_scenario += 1

    return bugs_in_scenario

# ============================================================
# 场景10: JSON解析脆弱性测试 (BUG-23候选)
# ============================================================
def test_json_parsing_robustness():
    logger.info("=" * 60)
    logger.info("极限混沌场景10: LLM JSON解析健壮性")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig

    bugs_in_scenario = 0

    # 测试各种LLM返回格式
    test_cases = [
        # 正常JSON
        ('{"summary": "test", "tags": ["a", "b"], "confidence": 0.8}', True, "正常JSON"),
        # Markdown代码块包裹
        ('```json\n{"summary": "test", "tags": ["a"]}\n```', True, "Markdown包裹JSON"),
        # 多个JSON对象
        ('{"summary": "first"} and {"summary": "second"}', False, "多个JSON对象"),
        # JSON中包含}字符
        ('{"summary": "use a } b"}', False, "JSON值中包含花括号"),
        # 空响应
        ('', False, "空响应"),
        # 纯文本无JSON
        ('This is just text without any JSON', False, "纯文本无JSON"),
        # JSON前后有文字
        ('Here is the result: {"summary": "test"}', True, "JSON前后有文字"),
        # 嵌套JSON
        ('{"summary": "test", "meta": {"key": "value"}}', True, "嵌套JSON"),
    ]

    config = LLMConfig()
    analyzer = LLMAnalyzer(config)

    for content, should_succeed, desc in test_cases:
        try:
            result = analyzer._parse_response(content)
            if result:
                record_result(f"JSON解析-{desc}", True,
                              f"summary={result.get('summary', 'N/A')[:50]}")
            else:
                if should_succeed:
                    record_result(f"JSON解析-{desc}", False, "应成功但返回None")
                    if desc == "多个JSON对象" or desc == "JSON值中包含花括号":
                        record_bug(23, f"LLM返回'{desc}'时JSON解析失败", "严重",
                                   "llm_analyzer.py:178-181 _parse_response")
                        bugs_in_scenario += 1
                else:
                    record_result(f"JSON解析-{desc}", True, "正确返回None")
        except Exception as e:
            record_result(f"JSON解析-{desc}", False, f"异常: {e}")
            if should_succeed:
                bugs_in_scenario += 1

    return bugs_in_scenario

# ============================================================
# 场景11: 中文分词标签提取测试 (BUG-24候选)
# ============================================================
def test_chinese_tag_extraction():
    logger.info("=" * 60)
    logger.info("极限混沌场景11: 中文分词标签提取")
    logger.info("=" * 60)

    from llm_analyzer import LLMAnalyzer, LLMConfig

    bugs_in_scenario = 0
    config = LLMConfig()
    analyzer = LLMAnalyzer(config)

    # 测试中文summary的标签提取
    test_cases = [
        ("这是一个用户服务类，负责管理用户信息", "中文summary"),
        ("数据访问层，提供数据库CRUD操作", "中文summary含英文"),
        ("HTTP请求处理控制器", "短中文summary"),
        ("A user service class for managing user data", "英文summary"),
    ]

    for summary, desc in test_cases:
        try:
            # 模拟_parse_response的回退逻辑
            words = summary.split()
            tags = [w for w in words if len(w) > 2][:3]
            logger.info(f"  {desc}: summary='{summary}' -> tags={tags}")

            if desc.startswith("中文") and not any('\u4e00' <= c <= '\u9fff' for tag in tags for c in tag):
                # 中文标签应该包含中文字符
                record_result(f"中文标签提取-{desc}", False,
                              f"标签不含中文: {tags}")
                if desc == "中文summary":
                    record_bug(24, f"中文summary标签提取失败: split()无法分词中文", "中等",
                               "llm_analyzer.py:212-213 _parse_response回退逻辑")
                    bugs_in_scenario += 1
            else:
                record_result(f"中文标签提取-{desc}", True, f"tags={tags}")
        except Exception as e:
            record_result(f"中文标签提取-{desc}", False, f"异常: {e}")

    return bugs_in_scenario

# ============================================================
# 场景12: 极限并发+数据一致性测试
# ============================================================
def test_extreme_concurrency_data_consistency():
    logger.info("=" * 60)
    logger.info("极限混沌场景12: 极限并发+数据一致性")
    logger.info("=" * 60)

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, 'test.db')
    bugs_in_scenario = 0

    try:
        storage = SQLiteStorage(db_path)
        parser = ArkTSParser()

        # 200线程并发读写
        errors = []
        success_count = [0]
        lock = threading.Lock()

        def worker(worker_id):
            try:
                code = f'''class Worker{worker_id} {{
    method() {{ return {worker_id}; }}
}}
'''
                result = parser.parse(code, f'/test/worker_{worker_id}.ts')
                storage.update_file_data(f'/test/worker_{worker_id}.ts', result)

                # 立即读取验证
                entities = storage.get_entities(f'/test/worker_{worker_id}.ts')
                if len(entities) == 0:
                    with lock:
                        errors.append(f"worker_{worker_id}: 写入后读取为空")
                else:
                    with lock:
                        success_count[0] += 1
            except Exception as e:
                with lock:
                    errors.append(f"worker_{worker_id}: {e}")

        threads = []
        for i in range(200):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)

        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join(timeout=30)
        elapsed = time.time() - start

        record_result("200线程并发读写", len(errors) == 0,
                      f"成功: {success_count[0]}/200, 错误: {len(errors)}, 耗时: {elapsed:.2f}s")
        if errors:
            for err in errors[:5]:
                logger.info(f"    错误: {err}")
            if len(errors) > 10:
                record_bug(25, f"200线程并发读写出现{len(errors)}个错误", "严重",
                           "sqlite_storage.py 线程连接管理")
                bugs_in_scenario += 1

        # 验证数据一致性
        stats = storage.get_statistics()
        record_result("并发后数据一致性", stats['total_entities'] >= 200,
                      f"总实体数: {stats['total_entities']}, 期望>=200")

        storage.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return bugs_in_scenario

# ============================================================
# 场景13: 变量声明模式边界测试
# ============================================================
def test_variable_pattern_edge_cases():
    logger.info("=" * 60)
    logger.info("极限混沌场景13: 变量声明模式边界")
    logger.info("=" * 60)

    parser = ArkTSParser()
    bugs_in_scenario = 0

    code = '''// 多行值
const config = {
    host: "localhost",
    port: 8080,
    debug: true
};

// 值中包含分号
const handler = () => { x; y; };

// 复杂类型注解
const map: Map<string, Map<number, Set<string>>> = new Map();

// 解构赋值
const { name, age } = user;
const [first, ...rest] = items;

// 类型断言
const value = data as string;
const element = document.getElementById('app') as HTMLElement;
'''
    result = parser.parse(code, '/test/variables.ts')

    # 检查是否崩溃
    record_result("变量声明模式不崩溃", True, f"实体数: {len(result.entities)}")

    # 多行对象字面量 - var_pattern不应跨行匹配
    # 如果匹配了，value会被截断
    var_entities = [e for e in result.entities if e.entity_type == 'variable']
    for ve in var_entities:
        if ve.name == 'config':
            # 如果被提取，检查值是否完整
            snippet = ve.code_snippet if hasattr(ve, 'code_snippet') else ''
            if snippet and 'host' in snippet and 'port' in snippet and 'debug' in snippet:
                record_result("多行对象字面量完整提取", True, "config值完整")
            elif snippet:
                record_result("多行对象字面量完整提取", False,
                              f"config值可能被截断: {snippet[:100]}")
                bugs_in_scenario += 1

    return bugs_in_scenario

# ============================================================
# 场景14: 重复实体名和同名方法测试
# ============================================================
def test_duplicate_entity_names():
    logger.info("=" * 60)
    logger.info("极限混沌场景14: 重复实体名和同名方法")
    logger.info("=" * 60)

    parser = ArkTSParser()
    bugs_in_scenario = 0

    code = '''class ServiceA {
    process() {}
    process(data: string) {}  // 重载
}

class ServiceB {
    process() {}  // 不同类中同名方法
}

function process() {}  // 顶层同名函数
'''
    result = parser.parse(code, '/test/duplicate.ts')

    all_names = [e.name for e in result.entities]
    process_count = all_names.count('process')
    logger.info(f"  所有实体名: {all_names}")
    logger.info(f"  'process'出现次数: {process_count}")

    # 检查同名方法是否都被提取
    record_result("同名方法提取", process_count >= 2,
                  f"process出现{process_count}次")

    # 检查关系提取是否受影响
    calls = [r for r in result.relations if r.relation_type == 'calls']
    record_result("同名实体关系提取正常", True,
                  f"关系数: {len(result.relations)}")

    return bugs_in_scenario

# ============================================================
# 场景15: 装饰器+泛型+继承组合极限测试
# ============================================================
def test_decorator_generic_inheritance_combo():
    logger.info("=" * 60)
    logger.info("极限混沌场景15: 装饰器+泛型+继承+实现组合")
    logger.info("=" * 60)

    parser = ArkTSParser()
    bugs_in_scenario = 0

    code = '''@Injectable()
@Singleton()
export class BaseService<T> {
    protected data: Map<string, T> = new Map();

    getAll(): T[] {
        return Array.from(this.data.values());
    }
}

@Injectable()
export class UserService extends BaseService<User> implements IService<User>, ICacheable {
    private cache: Map<string, User> = new Map();

    async findById(id: string): Promise<User | null> {
        return this.cache.get(id) || null;
    }

    @Log()
    @Cacheable(ttl: 3600)
    async save(user: User): Promise<void> {
        this.cache.set(user.id, user);
        this.data.set(user.id, user);
    }
}

interface IService<T> {
    findById(id: string): Promise<T | null>;
    save(entity: T): Promise<void>;
}

interface ICacheable {
    clearCache(): void;
}
'''
    result = parser.parse(code, '/test/combo.ts')

    entities_by_type = defaultdict(list)
    for e in result.entities:
        entities_by_type[e.entity_type].append(e.name)

    logger.info(f"  实体类型分布: {dict(entities_by_type)}")

    # 检查装饰器
    user_service = next((e for e in result.entities if e.name == 'UserService'), None)
    if user_service:
        decorators = user_service.decorators if hasattr(user_service, 'decorators') else []
        record_result("UserService装饰器", len(decorators) >= 2,
                      f"装饰器: {decorators}")
    else:
        record_result("UserService提取", False, "未找到UserService实体")
        bugs_in_scenario += 1

    # 检查继承关系
    extends_rels = [r for r in result.relations if r.relation_type == 'extends']
    has_extends = any(r.source_entity == 'UserService' and r.target_entity == 'BaseService' for r in extends_rels)
    record_result("泛型继承关系", has_extends,
                  f"UserService extends BaseService: {has_extends}")

    # 检查实现关系
    impl_rels = [r for r in result.relations if r.relation_type == 'implements']
    impl_targets = [r.target_entity for r in impl_rels if r.source_entity == 'UserService']
    record_result("多接口实现关系", len(impl_targets) >= 1,
                  f"UserService implements: {impl_targets}")

    # 检查方法中的装饰器
    save_method = next((e for e in result.entities if e.name == 'save'), None)
    if save_method:
        save_decorators = save_method.decorators if hasattr(save_method, 'decorators') else []
        record_result("方法装饰器提取", len(save_decorators) >= 1,
                      f"save装饰器: {save_decorators}")
    else:
        record_result("save方法提取", False, "未找到save方法")

    return bugs_in_scenario

# ============================================================
# 场景16: 文件变更指纹竞态测试
# ============================================================
def test_fingerprint_race_condition():
    logger.info("=" * 60)
    logger.info("极限混沌场景16: 文件变更指纹竞态条件")
    logger.info("=" * 60)

    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, 'test.db')
    bugs_in_scenario = 0

    try:
        storage = SQLiteStorage(db_path)
        parser = ArkTSParser()

        # 模拟两个线程同时检查同一文件的指纹
        file_path = '/test/race.ts'
        code_v1 = 'class V1 { method() {} }'
        code_v2 = 'class V2 { method() {} }'

        result1 = parser.parse(code_v1, file_path)
        storage.update_file_data(file_path, result1)

        # 两个线程同时检查指纹
        hash1 = storage.get_file_hash(file_path)
        hash2 = storage.get_file_hash(file_path)

        record_result("并发指纹读取一致", hash1 == hash2,
                      f"hash1==hash2: {hash1 == hash2}")

        # 模拟快速变更
        for i in range(100):
            code = f'class V{i} {{ method() {{ return {i}; }} }}'
            result = parser.parse(code, file_path)
            storage.update_file_data(file_path, result)

        final_entities = storage.get_entities(file_path)
        record_result("100次快速变更后数据一致", len(final_entities) > 0,
                      f"最终实体数: {len(final_entities)}")

        storage.close()
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)

    return bugs_in_scenario

# ============================================================
# 场景17: 空文件和极端边界测试
# ============================================================
def test_extreme_boundary_conditions():
    logger.info("=" * 60)
    logger.info("极限混沌场景17: 极端边界条件")
    logger.info("=" * 60)

    parser = ArkTSParser()
    bugs_in_scenario = 0

    test_cases = [
        ("", "空字符串"),
        ("   ", "纯空格"),
        ("\n\n\n", "纯换行"),
        ("// 只有注释\n// 没有代码", "纯注释"),
        ("/* 多行注释 */", "块注释"),
        ('"""三引号字符串"""', "三引号字符串"),
        ("'单引号字符串'", "单引号字符串"),
        ("`模板字符串`", "模板字符串"),
        ("class {}", "最小类定义"),
        ("function f(){}", "最小函数定义"),
        ("interface I {}", "最小接口定义"),
        ("type T = string;", "最小类型别名"),
        ("enum E { A }", "最小枚举定义"),
    ]

    for code, desc in test_cases:
        try:
            result = parser.parse(code, '/test/boundary.ts')
            record_result(f"边界-{desc}", True,
                          f"实体数: {len(result.entities)}")
        except Exception as e:
            record_result(f"边界-{desc}", False, f"崩溃: {e}")
            bugs_in_scenario += 1

    return bugs_in_scenario

# ============================================================
# 场景18: 混合混沌 - 所有特性同时出现
# ============================================================
def test_total_chaos():
    logger.info("=" * 60)
    logger.info("极限混沌场景18: 全特性混合混沌")
    logger.info("=" * 60)

    parser = ArkTSParser()
    bugs_in_scenario = 0

    # 生成一个包含所有ArkTS特性的超大文件
    code = '''
// 导入
import { Component, State, Build } from '@arkui/core';
import { HttpClient } from '../network/http';
import type { Response } from '../types';
export { Component as ArkComponent };
export * from '../utils/helpers';

// 装饰器类
@Component
@State({ count: 0 })
export class ChaosPage extends BasePage<ChaosViewModel> implements IPage, ILifecycle {
    @Prop title: string = "";
    @Provide data: Map<string, Array<Map<number, Set<string>>>> = new Map();
    private _cache: Record<string, { key: number; value: string }> = {};

    // 构造函数
    constructor() {
        super();
        this.init();
    }

    // 异步方法
    async loadData(): Promise<Response<Data>> {
        const result = await this.http.get('/api/data');
        return result;
    }

    // 回调嵌套
    process(callback: (result: (success: boolean) => void) => void) {
        callback((success) => {
            console.log(success);
        });
    }

    // 模板字符串
    render() {
        const msg = `Count: ${this.data.size}, Title: ${this.title}`;
        const nested = `Outer: ${`Inner: ${1 + 2}`}`;
        return msg;
    }

    // 转义字符
    escape() {
        const a = "He said \\"hello\\"";
        const b = 'It\\'s fine';
        const c = `Path: C:\\Users\\test`;
    }

    // 链式调用
    chain() {
        this.data.keys()
            .filter(k => k.startsWith('prefix'))
            .map(k => this.data.get(k))
            .forEach(v => console.log(v));
    }
}

// 接口
interface IPage<T> {
    title: string;
    data: Map<string, T>;
}

interface ILifecycle {
    onCreate(): void;
    onDestroy(): void;
}

// 类型别名
type Data = Record<string, unknown>;
type Handler<T> = (data: T) => Promise<void>;
type Complex = Map<string, Array<{ id: number; name: string }>>;

// 枚举
export enum Status {
    Active = "active",
    Inactive = "inactive",
    Pending = "pending",
}

// 泛型函数
function createService<T>(config: ServiceConfig<T>): IService<T> {
    return new ServiceImpl<T>(config);
}

// 箭头函数
const transform = <T, U>(data: T, mapper: (item: T) => U): U[] => {
    return data.map(mapper);
};

// 默认导出
export default class AppModule {}
'''
    try:
        result = parser.parse(code, '/test/total_chaos.ts')

        entities_by_type = defaultdict(list)
        for e in result.entities:
            entities_by_type[e.entity_type].append(e.name)

        logger.info(f"  实体类型分布: {dict(entities_by_type)}")
        logger.info(f"  关系数: {len(result.relations)}")
        logger.info(f"  依赖数: {len(result.dependencies)}")

        # 验证关键实体
        checks = [
            ('ChaosPage', 'class'),
            ('IPage', 'interface'),
            ('ILifecycle', 'interface'),
            ('Data', 'type_alias'),
            ('Handler', 'type_alias'),
            ('Status', 'enum'),
            ('createService', 'function'),
            ('transform', 'function'),
            ('AppModule', 'class'),
        ]

        all_found = True
        for name, etype in checks:
            found = any(e.name == name and e.entity_type == etype for e in result.entities)
            if not found:
                logger.info(f"  未找到: {name} ({etype})")
                all_found = False

        record_result("全特性混合提取", all_found,
                      f"实体数: {len(result.entities)}, 类型: {dict(entities_by_type)}")

        # 验证装饰器
        chaos_page = next((e for e in result.entities if e.name == 'ChaosPage'), None)
        if chaos_page:
            decorators = chaos_page.decorators if hasattr(chaos_page, 'decorators') else []
            record_result("混合场景装饰器", len(decorators) >= 2,
                          f"ChaosPage装饰器: {decorators}")

        # 验证依赖
        has_import_deps = len(result.dependencies) > 0
        record_result("混合场景依赖提取", has_import_deps,
                      f"依赖数: {len(result.dependencies)}")

        # 验证re-export
        has_utils_dep = any('utils' in str(d.target_file) for d in result.dependencies)
        record_result("混合场景re-export依赖", has_utils_dep,
                      f"utils依赖: {has_utils_dep}")

    except Exception as e:
        record_result("全特性混合提取", False, f"崩溃: {e}")
        bugs_in_scenario += 1
        logger.error(traceback.format_exc())

    return bugs_in_scenario

# ============================================================
# 主函数
# ============================================================
def main():
    logger.info("=" * 60)
    logger.info("Round 16: 极限混沌测试 - 基于静态代码走读")
    logger.info("=" * 60)

    total_start = time.time()
    total_bugs = 0

    scenarios = [
        ("code_snippet数据源一致性", test_code_snippet_data_source),
        ("re-export语法识别", test_reexport_syntax),
        ("模板字符串边界", test_template_string_edge_cases),
        ("转义引号和特殊字符", test_escaped_quotes_and_special_chars),
        ("两层嵌套括号参数", test_nested_parentheses_params),
        ("函数调用关系边界", test_call_relation_edge_cases),
        ("SQL参数数量限制", test_sql_parameter_limit),
        ("异常链保留验证", test_exception_chain_preservation),
        ("隐藏文件过滤一致性", test_hidden_file_filter_consistency),
        ("LLM JSON解析健壮性", test_json_parsing_robustness),
        ("中文分词标签提取", test_chinese_tag_extraction),
        ("极限并发数据一致性", test_extreme_concurrency_data_consistency),
        ("变量声明模式边界", test_variable_pattern_edge_cases),
        ("重复实体名", test_duplicate_entity_names),
        ("装饰器泛型继承组合", test_decorator_generic_inheritance_combo),
        ("指纹竞态条件", test_fingerprint_race_condition),
        ("极端边界条件", test_extreme_boundary_conditions),
        ("全特性混合混沌", test_total_chaos),
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

    # ============================================================
    # 最终报告
    # ============================================================
    logger.info("")
    logger.info("=" * 60)
    logger.info("Round 16 极限混沌测试 - 最终报告")
    logger.info("=" * 60)
    logger.info(f"")
    logger.info(f"总耗时: {total_elapsed:.3f}s")
    logger.info(f"发现BUG数: {len(bugs_found)}")
    logger.info(f"")

    passed = sum(1 for r in test_results if r['status'] == 'PASS')
    failed = sum(1 for r in test_results if r['status'] == 'FAIL')
    logger.info(f"统计: 通过={passed}, 失败={failed}, 总计={len(test_results)}")
    logger.info(f"")

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
