#!/usr/bin/env python3
"""
极限混乱场景测试文件生成器

创建用于测试知识图谱系统的极限复杂场景：
- 大量文件（200+）
- 深层继承链（10+层）
- 复杂的多重继承
- 循环导入链
- 深度组件嵌套（20+层）
- 海量方法调用关系
- 各种边界情况
"""

import os
import random
import string
from pathlib import Path
from typing import List, Dict, Any

# 随机种子，保证可复现
random.seed(42)

# 配置
TEST_PROJECT_ROOT = Path(__file__).parent / "extreme_chaos_test_project"
NUM_FILES = 200
INHERITANCE_DEPTH = 15
COMPONENT_NESTING_DEPTH = 25
MAX_METHODS_PER_CLASS = 30
MAX_PROPERTIES_PER_CLASS = 20


def generate_random_name(length: int = 8) -> str:
    """生成随机名称。"""
    return ''.join(random.choices(string.ascii_letters, k=1)) + \
           ''.join(random.choices(string.ascii_letters + string.digits, k=length - 1))


def generate_method_content(method_name: str, class_name: str, depth: int = 0) -> str:
    """生成包含随机调用的方法内容。"""
    indent = "    " * (depth + 2)
    lines = []
    
    # 随机调用其他方法
    num_calls = random.randint(0, 8)
    for i in range(num_calls):
        target_method = f"method{random.randint(0, MAX_METHODS_PER_CLASS)}"
        args = ', '.join([f"arg{j}" for j in range(random.randint(0, 5))])
        lines.append(f"{indent}this.{target_method}({args});")
    
    # 随机组件使用
    num_components = random.randint(0, 5)
    for i in range(num_components):
        comp_name = f"ChaosComponent{random.randint(0, 50)}"
        lines.append(f"{indent}// 使用组件: {comp_name}")
    
    # 返回语句
    lines.append(f"{indent}return '{method_name} result';")
    
    return '\n'.join(lines)


def create_base_file(file_index: int) -> str:
    """创建基础文件内容。"""
    class_name = f"ChaosClass{file_index}"
    
    # 生成随机导入
    imports = []
    num_imports = random.randint(1, 10)
    for i in range(num_imports):
        target_file = random.randint(0, NUM_FILES - 1)
        imports.append(f"import {{ ChaosClass{target_file} }} from './ChaosFile{target_file}';")
    
    # 生成类定义
    methods = []
    num_methods = random.randint(5, MAX_METHODS_PER_CLASS)
    for method_idx in range(num_methods):
        method_name = f"method{method_idx}"
        is_async = random.choice([True, False])
        async_key = "async " if is_async else ""
        methods.append(f"""
    {async_key}{method_name}() {{
{generate_method_content(method_name, class_name)}
    }}
""")
    
    # 生成属性
    properties = []
    num_props = random.randint(3, MAX_PROPERTIES_PER_CLASS)
    for prop_idx in range(num_props):
        prop_type = random.choice(['string', 'number', 'boolean', 'any', f'ChaosClass{random.randint(0, NUM_FILES - 1)}'])
        properties.append(f"    private prop{prop_idx}: {prop_type};")
    
    content = f"""/**
 * 混乱测试文件 {file_index}
 * 自动生成的极限测试场景
 */

{chr(10).join(imports)}

export class {class_name} {{
{chr(10).join(properties)}

{chr(10).join(methods)}
}}

export default {class_name};
"""
    return content


def create_inheritance_chain_file(file_index: int, parent_index: int, depth: int) -> str:
    """创建继承链文件。"""
    class_name = f"InheritanceClass{file_index}"
    parent_name = f"InheritanceClass{parent_index}" if parent_index >= 0 else "BaseChaosClass"
    
    methods = []
    num_methods = random.randint(3, MAX_METHODS_PER_CLASS)
    for method_idx in range(num_methods):
        method_name = f"method{method_idx}"
        methods.append(f"""
    method{method_idx}() {{
        super.method{random.randint(0, 5)}?.();
        return 'Inheritance {depth} result';
    }}
""")
    
    content = f"""/**
 * 继承链文件 - 深度 {depth}
 */

{f"import {{ {parent_name} }} from './InheritanceFile{parent_index}';" if parent_index >= 0 else ""}

export class {class_name}{f" extends {parent_name}" if parent_index >= 0 or depth == 0 else ""} {{
{chr(10).join(methods)}
}}
"""
    return content


def create_component_nesting_file(file_index: int, child_index: int, depth: int) -> str:
    """创建组件嵌套文件。"""
    class_name = f"NestedComponent{file_index}"
    child_name = f"NestedComponent{child_index}" if child_index >= 0 else None
    
    # 模拟ArkTS组件
    build_content = ""
    if child_name:
        build_content = f"""
    build() {{
        Column() {{
            {child_name}()
            {child_name}()
            {child_name}()
        }}
    }}
"""
    else:
        build_content = """
    build() {
        Column() {
            Text('Leaf Component')
        }
    }
"""
    
    content = f"""/**
 * 嵌套组件文件 - 深度 {depth}
 */

{f"import {{ {child_name} }} from './NestedComponentFile{child_index}';" if child_name else ""}

@Component
export struct {class_name} {{
{build_content}
}}
"""
    return content


def create_circular_import_files() -> List[Dict[str, Any]]:
    """创建循环导入文件。"""
    files = []
    
    # 3文件循环: A->B->C->A
    files.append({
        'name': 'CircularA.ets',
        'content': """/**
 * 循环导入文件 A
 */

import { CircularB } from './CircularB';

export class CircularA {
    useB() {
        return new CircularB();
    }
}
"""
    })
    
    files.append({
        'name': 'CircularB.ets',
        'content': """/**
 * 循环导入文件 B
 */

import { CircularC } from './CircularC';

export class CircularB {
    useC() {
        return new CircularC();
    }
}
"""
    })
    
    files.append({
        'name': 'CircularC.ets',
        'content': """/**
 * 循环导入文件 C
 */

import { CircularA } from './CircularA';

export class CircularC {
    useA() {
        return new CircularA();
    }
}
"""
    })
    
    # 5文件循环链
    for i in range(5):
        next_idx = (i + 1) % 5
        files.append({
            'name': f'ChainFile{i}.ets',
            'content': f"""/**
 * 循环链文件 {i}
 */

import {{ ChainClass{next_idx} }} from './ChainFile{next_idx}';

export class ChainClass{i} {{
    next() {{
        return new ChainClass{next_idx}();
    }}
}}
"""
        })
    
    return files


def create_edge_case_files() -> List[Dict[str, Any]]:
    """创建边界情况文件。"""
    files = []
    
    # 空文件
    files.append({
        'name': 'EmptyFile.ets',
        'content': ""
    })
    
    # 只有注释的文件
    files.append({
        'name': 'CommentOnlyFile.ets',
        'content': """/**
 * 只有注释的文件
 * 没有实际代码
 */

// 这是一个注释
/* 这也是一个注释 */
"""
    })
    
    # 超大文件（1000+ 行）
    large_content = """/**
 * 超大文件 - 测试大文件处理
 */

"""
    for i in range(100):
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
    files.append({
        'name': 'LargeFile.ets',
        'content': large_content
    })
    
    # 特殊字符文件名
    files.append({
        'name': 'Special_Chars-File.Name@123.ets',
        'content': """/**
 * 特殊字符文件名测试
 */

export class SpecialCharsClass {
    test() {
        return 'special chars';
    }
}
"""
    })
    
    # 单字符标识符
    files.append({
        'name': 'SingleChar.ets',
        'content': """/**
 * 单字符标识符测试
 */

export class A {
    b: string;
    c() {
        return this.b;
    }
}

export class B {
    a: A;
    d() {
        return new A();
    }
}
"""
    })
    
    # 超长标识符
    very_long_name = "ThisIsAVeryLongClassNameThatTestsTheLimitsOfIdentifierLengthHandlingInTheParser"
    files.append({
        'name': 'LongIdentifiers.ets',
        'content': f"""/**
 * 超长标识符测试
 */

export class {very_long_name} {{
    thisIsAlsoAVeryLongPropertyNameThatShouldBeHandledProperly: string;
    
    thisIsAVeryLongMethodNameThatTestsTheParserLimits() {{
        return 'long identifier test';
    }}
}}
"""
    })
    
    return files


def create_multi_inheritance_file() -> str:
    """创建多重继承/混合文件（TypeScript接口实现）。"""
    content = """/**
 * 多重继承/接口实现测试
 */

interface InterfaceA {
    methodA(): void;
}

interface InterfaceB {
    methodB(): string;
}

interface InterfaceC {
    propC: number;
}

interface InterfaceD extends InterfaceA, InterfaceB {
    methodD(): boolean;
}

export class MultiImplClass implements InterfaceA, InterfaceB, InterfaceC, InterfaceD {
    propC: number = 42;
    
    methodA(): void {
        console.log('methodA');
    }
    
    methodB(): string {
        return 'methodB';
    }
    
    methodD(): boolean {
        return true;
    }
}

export abstract class AbstractBase {
    abstract abstractMethod(): void;
    
    concreteMethod() {
        return 'concrete';
    }
}

export class ConcreteImpl extends AbstractBase {
    abstractMethod(): void {
        console.log('implemented');
    }
}
"""
    return content


def create_call_chain_files() -> List[Dict[str, Any]]:
    """创建复杂调用链文件。"""
    files = []
    
    # 深度调用链
    for i in range(10):
        next_idx = i + 1 if i < 9 else 0
        files.append({
            'name': f'CallChain{i}.ets',
            'content': f"""/**
 * 调用链文件 {i}
 */

import {{ CallChainClass{next_idx} }} from './CallChain{next_idx}';

export class CallChainClass{i} {{
    callNext() {{
        const next = new CallChainClass{next_idx}();
        return next.execute();
    }}
    
    execute() {{
        return 'CallChain{i} executed';
    }}
}}
"""
        })
    
    return files


def main():
    """主函数 - 生成测试项目。"""
    print("=" * 80)
    print("极限混乱场景测试项目生成器")
    print("=" * 80)
    
    # 清理并创建项目目录
    if TEST_PROJECT_ROOT.exists():
        import shutil
        shutil.rmtree(TEST_PROJECT_ROOT)
    TEST_PROJECT_ROOT.mkdir(parents=True, exist_ok=True)
    
    print(f"\n项目目录: {TEST_PROJECT_ROOT}")
    print("\n开始生成文件...")
    
    total_files = 0
    
    # 1. 创建基础文件
    print(f"\n[1/7] 创建 {NUM_FILES} 个基础文件...")
    for i in range(NUM_FILES):
        file_path = TEST_PROJECT_ROOT / f"ChaosFile{i}.ets"
        file_path.write_text(create_base_file(i), encoding='utf-8')
        total_files += 1
    print(f"  完成: {NUM_FILES} 个文件")
    
    # 2. 创建深层继承链
    print(f"\n[2/7] 创建 {INHERITANCE_DEPTH} 层继承链...")
    for i in range(INHERITANCE_DEPTH):
        parent_idx = i - 1
        file_path = TEST_PROJECT_ROOT / f"InheritanceFile{i}.ets"
        file_path.write_text(create_inheritance_chain_file(i, parent_idx, i), encoding='utf-8')
        total_files += 1
    print(f"  完成: {INHERITANCE_DEPTH} 个文件")
    
    # 3. 创建深层组件嵌套
    print(f"\n[3/7] 创建 {COMPONENT_NESTING_DEPTH} 层组件嵌套...")
    for i in range(COMPONENT_NESTING_DEPTH):
        child_idx = i + 1 if i < COMPONENT_NESTING_DEPTH - 1 else -1
        file_path = TEST_PROJECT_ROOT / f"NestedComponentFile{i}.ets"
        file_path.write_text(create_component_nesting_file(i, child_idx, i), encoding='utf-8')
        total_files += 1
    print(f"  完成: {COMPONENT_NESTING_DEPTH} 个文件")
    
    # 4. 创建循环导入文件
    print(f"\n[4/7] 创建循环导入文件...")
    circular_files = create_circular_import_files()
    for f in circular_files:
        file_path = TEST_PROJECT_ROOT / f['name']
        file_path.write_text(f['content'], encoding='utf-8')
        total_files += 1
    print(f"  完成: {len(circular_files)} 个文件")
    
    # 5. 创建边界情况文件
    print(f"\n[5/7] 创建边界情况文件...")
    edge_files = create_edge_case_files()
    for f in edge_files:
        file_path = TEST_PROJECT_ROOT / f['name']
        file_path.write_text(f['content'], encoding='utf-8')
        total_files += 1
    print(f"  完成: {len(edge_files)} 个文件")
    
    # 6. 创建多重继承文件
    print(f"\n[6/7] 创建多重继承文件...")
    file_path = TEST_PROJECT_ROOT / "MultiInheritance.ets"
    file_path.write_text(create_multi_inheritance_file(), encoding='utf-8')
    total_files += 1
    print(f"  完成: 1 个文件")
    
    # 7. 创建调用链文件
    print(f"\n[7/7] 创建调用链文件...")
    call_chain_files = create_call_chain_files()
    for f in call_chain_files:
        file_path = TEST_PROJECT_ROOT / f['name']
        file_path.write_text(f['content'], encoding='utf-8')
        total_files += 1
    print(f"  完成: {len(call_chain_files)} 个文件")
    
    # 创建 package.json
    print(f"\n创建项目配置文件...")
    package_json = {
        "name": "extreme-chaos-test",
        "version": "1.0.0",
        "description": "极限混乱测试项目",
        "main": "index.js"
    }
    import json
    (TEST_PROJECT_ROOT / "package.json").write_text(json.dumps(package_json, indent=2), encoding='utf-8')
    
    # 完成
    print("\n" + "=" * 80)
    print(f"生成完成! 总计 {total_files} 个文件")
    print("=" * 80)
    print(f"\n项目位置: {TEST_PROJECT_ROOT.absolute()}")
    print("\n包含场景:")
    print(f"  - {NUM_FILES} 个基础文件")
    print(f"  - {INHERITANCE_DEPTH} 层继承链")
    print(f"  - {COMPONENT_NESTING_DEPTH} 层组件嵌套")
    print(f"  - 循环导入链")
    print(f"  - 边界情况（空文件、大文件、特殊字符等）")
    print(f"  - 多重继承/接口实现")
    print(f"  - 复杂调用链")
    print("\n现在可以使用此项目测试知识图谱系统!")


if __name__ == '__main__':
    main()
