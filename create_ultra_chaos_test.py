#!/usr/bin/env python3
"""
超大规模混乱场景测试文件生成器 v2.0

创建用于测试知识图谱系统的超大规模极限场景：
- 500+ 个文件
- 多层复杂继承关系
- 深度组件嵌套
- 多重循环导入链
- 海量方法调用关系
- 各种边界和极端情况
- Unicode 标识符
- 语法错误文件（测试容错）
"""

import os
import random
import string
from pathlib import Path
from typing import List, Dict, Any

random.seed(123)

TEST_PROJECT_ROOT = Path(__file__).parent / "ultra_chaos_test_project"
NUM_FILES = 500
INHERITANCE_DEPTH = 20
COMPONENT_NESTING_DEPTH = 30
MAX_METHODS_PER_CLASS = 40
MAX_PROPERTIES_PER_CLASS = 25


def generate_random_name(length: int = 8) -> str:
    """生成随机名称。"""
    return ''.join(random.choices(string.ascii_letters, k=1)) + \
           ''.join(random.choices(string.ascii_letters + string.digits, k=length - 1))


def generate_unicode_name() -> str:
    """生成包含 Unicode 的标识符。"""
    unicode_chars = ['\u4e00', '\u7b49', '\u5b57', '\u6d77', '\u5c71', '\u4e9b']
    return ''.join(random.choices(unicode_chars, k=3))


def create_base_file(file_index: int) -> str:
    """创建基础文件内容。"""
    class_name = f"ChaosClass{file_index}"
    
    imports = []
    num_imports = random.randint(1, 15)
    for i in range(num_imports):
        target_file = random.randint(0, NUM_FILES - 1)
        imports.append(f"import {{ ChaosClass{target_file} }} from './ChaosFile{target_file}';")
    
    methods = []
    num_methods = random.randint(5, MAX_METHODS_PER_CLASS)
    for method_idx in range(num_methods):
        method_name = f"method{method_idx}"
        is_async = random.choice([True, False])
        async_key = "async " if is_async else ""
        lines = []
        
        num_calls = random.randint(0, 10)
        for i in range(num_calls):
            target_method = f"method{random.randint(0, MAX_METHODS_PER_CLASS)}"
            args = ', '.join([f"arg{j}" for j in range(random.randint(0, 5))])
            lines.append(f"        this.{target_method}({args});")
        
        lines.append(f"        return '{method_name} result';")
        
        content = f"""
    {async_key}{method_name}() {{
{chr(10).join(lines)}
    }}
"""
        methods.append(content)
    
    properties = []
    num_props = random.randint(3, MAX_PROPERTIES_PER_CLASS)
    for prop_idx in range(num_props):
        prop_type = random.choice(['string', 'number', 'boolean', 'any', f'ChaosClass{random.randint(0, NUM_FILES - 1)}'])
        properties.append(f"    private prop{prop_idx}: {prop_type};")
    
    content = f"""/**
 * 混乱测试文件 {file_index}
 * 超大规模测试场景 v2.0
 */

{chr(10).join(imports)}

export class {class_name} {{
{chr(10).join(properties)}

{chr(10).join(methods)}
}}

export default {class_name};
"""
    return content


def create_unicode_file(file_index: int) -> str:
    """创建包含 Unicode 标识符的文件。"""
    unicode_name = generate_unicode_name()
    
    content = f"""/**
 * Unicode 标识符测试文件
 */

export class {unicode_name} {{
    数据: string;
    数量: number;
    
    获取数据() {{
        return this.数据;
    }}
}}

export class TestClass_{file_index} {{
    海底生物: string;
    
    获取海洋() {{
        return this.海底生物;
    }}
}}
"""
    return content


def create_syntax_error_file(file_index: int) -> str:
    """创建包含语法错误的文件（测试容错能力）。"""
    error_type = random.choice(['unclosed_brace', 'missing_semicolon', 'invalid_syntax', 'unclosed_comment'])
    
    if error_type == 'unclosed_brace':
        content = f"""/**
 * 语法错误文件 - 未闭合的大括号
 */

export class ErrorClass{file_index} {{
    test() {{
        if (true) {{
            console.log('test');
"""
    elif error_type == 'missing_semicolon':
        content = f"""/**
 * 语法错误文件 - 缺少分号
 */

export class ErrorClass{file_index} {{
    test() {{
        let x = 10
        return x
    }}
}}
"""
    elif error_type == 'invalid_syntax':
        content = f"""/**
 * 语法错误文件 - 无效语法
 */

export class ErrorClass{file_index} {{
    test() {{
        const x === 10;
        return x
    }}
}}
"""
    else:
        content = f"""/**
 * 语法错误文件 - 未闭合的注释
 *

export class ErrorClass{file_index} {{
    test() {{
        return 42;
    }}
}}
"""
    
    return content


def create_generic_file(file_index: int) -> str:
    """创建包含泛型的文件。"""
    content = f"""/**
 * 泛型测试文件
 */

interface GenericInterface<T, U> {{
    getValue(): T;
    setValue(value: T): void;
}}

export class GenericClass<T> {{
    private data: T;
    
    constructor(initial: T) {{
        this.data = initial;
    }}
    
    getData(): T {{
        return this.data;
    }}
    
    setData(value: T): void {{
        this.data = value;
    }}
}}

export class SpecificClass extends GenericClass<string> {{
    constructor() {{
        super('initial');
    }}
    
    getUpperCase(): string {{
        return this.getData().toUpperCase();
    }}
}}

export type Result<T, E = Error> = {{
    ok: boolean;
    value?: T;
    error?: E;
}};
"""
    return content


def create_decorator_file(file_index: int) -> str:
    """创建包含各种装饰器的文件。"""
    content = f"""/**
 * 装饰器测试文件
 */

@Observed
export class ObservedClass{file_index} {{
    @State count: number = 0;
    @Prop title: string = '';
    @Link linkedValue: number = 0;
    
    @StorageProp('key1') storageProp: string = '';
    @StorageLink('key2') storageLink: number = 0;
    
    @Watch('onCountChange')
    @State watchedValue: number = 0;
    
    private onCountChange(): void {{
        console.log('count changed');
    }}
    
    increment(): void {{
        this.count++;
    }}
}}

@Component
export struct DecoratedComponent{file_index} {{
    @BuilderParam content: () => void;
    @Consume('theme') theme: string;
    
    build() {{
        Column() {{
            this.content()
        }}
    }}
}}
"""
    return content


def create_namespace_file(file_index: int) -> str:
    """创建包含命名空间的文件。"""
    content = f"""/**
 * 命名空间测试文件
 */

namespace Namespace{file_index} {{
    export const VERSION = '1.0.0';
    
    export class InternalClass {{
        name: string;
        
        constructor(name: string) {{
            this.name = name;
        }}
        
        greet(): string {{
            return `Hello, ${{this.name}}`;
        }}
    }}
    
    export function helper(): void {{
        console.log('helper function');
    }}
    
    export namespace Inner {{
        export const INNER_CONST = 42;
    }}
}}

export class UsingNamespace{file_index} {{
    useHelper(): void {{
        Namespace{file_index}.helper();
        const cls = new Namespace{file_index}.InternalClass('test');
        cls.greet();
    }}
}}
"""
    return content


def create_deeply_nested_file(file_index: int) -> str:
    """创建深度嵌套结构的文件。"""
    content = f"""/**
 * 深度嵌套结构测试文件
 */

export class Outer{file_index} {{
    middle: Middle{file_index} = new Middle{file_index}();
    
    outerMethod(): void {{
        this.middle.inner.innerMethod();
    }}
}}

class Middle{file_index} {{
    inner: Inner{file_index} = new Inner{file_index}();
    
    middleMethod(): void {{
        this.inner.innerMethod();
    }}
}}

class Inner{file_index} {{
    deeplyNested: DeeplyNested{file_index} = new DeeplyNested{file_index}();
    
    innerMethod(): void {{
        this.deeplyNested.deepMethod();
    }}
}}

class DeeplyNested{file_index} {{
    deepMethod(): void {{
        console.log('deeply nested method called');
    }}
}}
"""
    return content


def create_complex_call_chain_file(file_index: int) -> str:
    """创建复杂调用链文件。"""
    chain_length = random.randint(5, 15)
    files = []
    
    for i in range(chain_length):
        next_idx = (i + 1) % chain_length
        files.append({
            'name': f'CallChain{i}.ets',
            'content': f"""/**
 * 调用链文件 {i}
 */

import {{ ChainClass{next_idx} }} from './CallChain{next_idx}';

export class ChainClass{i} {{
    methodA() {{
        const next = new ChainClass{next_idx}();
        return next.methodB();
    }}
    
    methodB() {{
        return 'Chain{i} B';
    }}
    
    methodC() {{
        this.methodA();
        this.methodB();
        return 'Chain{i} C';
    }}
}}
"""
        })
    
    return files


def create_complex_inheritance_hierarchy() -> List[Dict[str, Any]]:
    """创建复杂的继承层次结构。"""
    files = []
    
    for i in range(INHERITANCE_DEPTH):
        if i == 0:
            content = f"""/**
 * 继承层次结构 - 基类
 */

export abstract class BaseClass{i} {{
    abstract operation(): void;
    
    commonOperation(): void {{
        console.log('common operation');
    }}
}}
"""
        elif i < INHERITANCE_DEPTH // 2:
            content = f"""/**
 * 继承层次结构 - 中间层 {i}
 */

import {{ BaseClass{i-1} }} from './Inheritance{i-1}';

export abstract class BaseClass{i} extends BaseClass{i-1} {{
    intermediateMethod(): void {{
        console.log('intermediate method {i}');
    }}
}}
"""
        else:
            parent_idx = i - 1
            content = f"""/**
 * 继承层次结构 - 实现层 {i}
 */

import {{ BaseClass{parent_idx} }} from './Inheritance{parent_idx}';

export class Implementation{i} extends BaseClass{parent_idx} {{
    operation(): void {{
        console.log('implementation {i}');
    }}
    
    specificMethod{i}(): void {{
        console.log('specific method {i}');
    }}
}}
"""
        
        files.append({
            'name': f'Inheritance{i}.ets',
            'content': content
        })
    
    return files


def create_component_nesting_chain() -> List[Dict[str, Any]]:
    """创建组件嵌套链。"""
    files = []
    
    for i in range(COMPONENT_NESTING_DEPTH):
        child_idx = i + 1 if i < COMPONENT_NESTING_DEPTH - 1 else -1
        
        if child_idx >= 0:
            content = f"""/**
 * 嵌套组件文件 - 深度 {i}
 */

import {{ NestedComponent{child_idx} }} from './NestedComponent{child_idx}';

@Component
export struct NestedComponent{i} {{
    build() {{
        Column() {{
            NestedComponent{child_idx}()
            NestedComponent{child_idx}()
        }}
    }}
}}
"""
        else:
            content = f"""/**
 * 嵌套组件文件 - 深度 {i} (叶子节点)
 */

@Component
export struct NestedComponent{i} {{
    build() {{
        Column() {{
            Text('Leaf Component {i}')
        }}
    }}
}}
"""
        
        files.append({
            'name': f'NestedComponent{i}.ets',
            'content': content
        })
    
    return files


def main():
    """主函数 - 生成超大规模测试项目。"""
    print("=" * 80)
    print("超大规模混乱场景测试项目生成器 v2.0")
    print("=" * 80)
    
    if TEST_PROJECT_ROOT.exists():
        import shutil
        shutil.rmtree(TEST_PROJECT_ROOT)
    TEST_PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    
    print(f"\n项目目录: {TEST_PROJECT_ROOT}")
    print("\n开始生成文件...")
    
    total_files = 0
    
    # 1. 创建基础文件
    print(f"\n[1/12] 创建 {NUM_FILES} 个基础文件...")
    for i in range(NUM_FILES):
        file_path = TEST_PROJECT_ROOT / f"ChaosFile{i}.ets"
        file_path.write_text(create_base_file(i), encoding='utf-8')
        total_files += 1
        if (i + 1) % 100 == 0:
            print(f"  已完成: {i + 1} 个文件")
    print(f"  完成: {NUM_FILES} 个文件")
    
    # 2. 创建 Unicode 文件
    print(f"\n[2/12] 创建 Unicode 标识符文件...")
    for i in range(20):
        file_path = TEST_PROJECT_ROOT / f"UnicodeFile{i}.ets"
        file_path.write_text(create_unicode_file(i), encoding='utf-8')
        total_files += 1
    print(f"  完成: 20 个文件")
    
    # 3. 创建语法错误文件
    print(f"\n[3/12] 创建语法错误文件...")
    for i in range(30):
        file_path = TEST_PROJECT_ROOT / f"ErrorFile{i}.ets"
        file_path.write_text(create_syntax_error_file(i), encoding='utf-8')
        total_files += 1
    print(f"  完成: 30 个文件")
    
    # 4. 创建泛型文件
    print(f"\n[4/12] 创建泛型文件...")
    for i in range(15):
        file_path = TEST_PROJECT_ROOT / f"GenericFile{i}.ets"
        file_path.write_text(create_generic_file(i), encoding='utf-8')
        total_files += 1
    print(f"  完成: 15 个文件")
    
    # 5. 创建装饰器文件
    print(f"\n[5/12] 创建装饰器文件...")
    for i in range(15):
        file_path = TEST_PROJECT_ROOT / f"DecoratorFile{i}.ets"
        file_path.write_text(create_decorator_file(i), encoding='utf-8')
        total_files += 1
    print(f"  完成: 15 个文件")
    
    # 6. 创建命名空间文件
    print(f"\n[6/12] 创建命名空间文件...")
    for i in range(15):
        file_path = TEST_PROJECT_ROOT / f"NamespaceFile{i}.ets"
        file_path.write_text(create_namespace_file(i), encoding='utf-8')
        total_files += 1
    print(f"  完成: 15 个文件")
    
    # 7. 创建深度嵌套文件
    print(f"\n[7/12] 创建深度嵌套文件...")
    for i in range(20):
        file_path = TEST_PROJECT_ROOT / f"NestedFile{i}.ets"
        file_path.write_text(create_deeply_nested_file(i), encoding='utf-8')
        total_files += 1
    print(f"  完成: 20 个文件")
    
    # 8. 创建复杂调用链
    print(f"\n[8/12] 创建复杂调用链...")
    chain_files = create_complex_call_chain_file(0)
    for f in chain_files:
        file_path = TEST_PROJECT_ROOT / f['name']
        file_path.write_text(f['content'], encoding='utf-8')
        total_files += 1
    print(f"  完成: {len(chain_files)} 个文件")
    
    # 9. 创建继承层次结构
    print(f"\n[9/12] 创建继承层次结构...")
    inheritance_files = create_complex_inheritance_hierarchy()
    for f in inheritance_files:
        file_path = TEST_PROJECT_ROOT / f['name']
        file_path.write_text(f['content'], encoding='utf-8')
        total_files += 1
    print(f"  完成: {len(inheritance_files)} 个文件")
    
    # 10. 创建组件嵌套链
    print(f"\n[10/12] 创建组件嵌套链...")
    nesting_files = create_component_nesting_chain()
    for f in nesting_files:
        file_path = TEST_PROJECT_ROOT / f['name']
        file_path.write_text(f['content'], encoding='utf-8')
        total_files += 1
    print(f"  完成: {len(nesting_files)} 个文件")
    
    # 11. 创建多个循环导入链
    print(f"\n[11/12] 创建循环导入链...")
    for chain_idx in range(5):
        for i in range(3):
            next_i = (i + 1) % 3
            content = f"""/**
 * 循环导入链 {chain_idx}, 文件 {i}
 */

import {{ Class{next_i} }} from './CircularChain{chain_idx}_{next_i}';

export class Class{i} {{
    use{next_i}() {{
        return new Class{next_i}();
    }}
}}
"""
            file_path = TEST_PROJECT_ROOT / f"CircularChain{chain_idx}_{i}.ets"
            file_path.write_text(content, encoding='utf-8')
            total_files += 1
    print(f"  完成: 15 个文件")
    
    # 12. 创建超大文件
    print(f"\n[12/12] 创建超大文件...")
    large_content = """/**
 * 超大文件 - 包含 200 个类的巨型文件
 * 测试解析器处理超大文件的能力
 */

"""
    for i in range(200):
        large_content += f"""
export class LargeClass{i} {{
    prop0: string;
    prop1: number;
    prop2: boolean;
    prop3: any;
    
    method0() {{ return 'method0'; }}
    method1() {{ return 'method1'; }}
    method2() {{ return 'method2'; }}
    method3() {{ return 'method3'; }}
    method4() {{ return 'method4'; }}
    method5() {{ return 'method5'; }}
    method6() {{ return 'method6'; }}
    method7() {{ return 'method7'; }}
    method8() {{ return 'method8'; }}
    method9() {{ return 'method9'; }}
}}
"""
    
    file_path = TEST_PROJECT_ROOT / "UltraLargeFile.ets"
    file_path.write_text(large_content, encoding='utf-8')
    total_files += 1
    print(f"  完成: 1 个文件")
    
    # 创建 package.json
    print(f"\n创建项目配置文件...")
    import json
    package_json = {
        "name": "ultra-chaos-test",
        "version": "2.0.0",
        "description": "超大规模混乱测试项目 v2.0",
        "main": "index.js"
    }
    (TEST_PROJECT_ROOT / "package.json").write_text(json.dumps(package_json, indent=2), encoding='utf-8')
    
    # 完成
    print("\n" + "=" * 80)
    print(f"生成完成! 总计 {total_files} 个文件")
    print("=" * 80)
    print(f"\n项目位置: {TEST_PROJECT_ROOT.absolute()}")
    print("\n包含场景:")
    print(f"  - {NUM_FILES} 个基础文件")
    print(f"  - 20 个 Unicode 标识符文件")
    print(f"  - 30 个语法错误文件")
    print(f"  - 15 个泛型文件")
    print(f"  - 15 个装饰器文件")
    print(f"  - 15 个命名空间文件")
    print(f"  - 20 个深度嵌套文件")
    print(f"  - {INHERITANCE_DEPTH} 层继承层次")
    print(f"  - {COMPONENT_NESTING_DEPTH} 层组件嵌套")
    print(f"  - 5 条循环导入链")
    print(f"  - 1 个超大文件 (200 类)")
    print("\n现在可以使用此项目测试知识图谱系统!")


if __name__ == '__main__':
    main()
