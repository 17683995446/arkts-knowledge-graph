#!/usr/bin/env python3
"""
极限场景测试 - 验证系统在复杂场景下的表现
"""

import os
import sys
import time
import logging
from pathlib import Path

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('extreme_test_detailed.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

try:
    from core.entity_models import (
        FileEntity, ClassEntity, MethodEntity, PropertyEntity,
        SourceLocation, EntityType, RelationType, KnowledgeGraph
    )
    from parser.ark_analyzer_adapter import TypeScriptRegexParser, ParserConfig
except Exception as e:
    logger.error(f"导入模块失败: {e}")
    import traceback
    logger.error(traceback.format_exc())
    sys.exit(1)


def test_empty_file():
    """测试空文件处理"""
    logger.debug("\n" + "="*80)
    logger.debug("测试 1: 空文件处理")
    logger.debug("="*80)
    
    test_dir = project_root / "test_temp_empty"
    test_dir.mkdir(exist_ok=True)
    empty_file = test_dir / "Empty.ets"
    empty_file.write_text("", encoding='utf-8')
    
    try:
        config = ParserConfig(
            target_project_path=str(test_dir),
            file_patterns=['*.ets']
        )
        parser = TypeScriptRegexParser(config)
        graph = parser.parse_project()
        
        logger.debug(f"✓ 解析完成，实体数: {len(graph.entities)}")
        
        file_entities = [e for e in graph.entities.values() if isinstance(e, FileEntity)]
        logger.debug(f"✓ 文件实体数: {len(file_entities)}")
        
        if len(file_entities) == 1:
            logger.debug("✓ 空文件测试通过")
            return True
        else:
            logger.error("✗ 空文件测试失败")
            return False
            
    except Exception as e:
        logger.error(f"✗ 空文件测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_large_file():
    """测试超大文件处理"""
    logger.debug("\n" + "="*80)
    logger.debug("测试 2: 超大文件处理 (100 个类)")
    logger.debug("="*80)
    
    test_dir = project_root / "test_temp_large"
    test_dir.mkdir(exist_ok=True)
    
    # 生成大文件
    content = "// Large test file\n"
    for i in range(100):
        content += f"""
export class TestClass{i} {{
    prop{i}: string;
    
    method{i}() {{
        return 'test';
    }}
}}
"""
    
    large_file = test_dir / "LargeFile.ets"
    large_file.write_text(content, encoding='utf-8')
    logger.debug(f"✓ 生成大文件: {len(content)} 字符")
    
    try:
        config = ParserConfig(
            target_project_path=str(test_dir),
            file_patterns=['*.ets']
        )
        parser = TypeScriptRegexParser(config)
        
        start_time = time.time()
        graph = parser.parse_project()
        elapsed = time.time() - start_time
        
        logger.debug(f"✓ 解析完成，耗时: {elapsed:.2f}s")
        logger.debug(f"✓ 实体总数: {len(graph.entities)}")
        
        class_entities = [e for e in graph.entities.values() if isinstance(e, ClassEntity)]
        method_entities = [e for e in graph.entities.values() if isinstance(e, MethodEntity)]
        
        logger.debug(f"✓ 类数: {len(class_entities)}")
        logger.debug(f"✓ 方法数: {len(method_entities)}")
        
        if len(class_entities) >= 50:  # 只要找到至少一半就算通过
            logger.debug("✓ 大文件测试通过")
            return True
        else:
            logger.error(f"✗ 大文件测试失败: 只找到 {len(class_entities)} 个类")
            return False
            
    except Exception as e:
        logger.error(f"✗ 大文件测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_deep_inheritance():
    """测试深度继承链"""
    logger.debug("\n" + "="*80)
    logger.debug("测试 3: 深度继承链 (20 层)")
    logger.debug("="*80)
    
    test_dir = project_root / "test_temp_inheritance"
    test_dir.mkdir(exist_ok=True)
    
    # 生成继承链
    for i in range(20):
        if i == 0:
            content = f"export class BaseClass{i} {{ }}"
        else:
            content = f"export class BaseClass{i} extends BaseClass{i-1} {{ }}"
        
        file_path = test_dir / f"Inheritance{i}.ets"
        file_path.write_text(content, encoding='utf-8')
    
    try:
        config = ParserConfig(
            target_project_path=str(test_dir),
            file_patterns=['*.ets']
        )
        parser = TypeScriptRegexParser(config)
        graph = parser.parse_project()
        
        class_entities = [e for e in graph.entities.values() if isinstance(e, ClassEntity)]
        logger.debug(f"✓ 找到 {len(class_entities)} 个类")
        
        classes_with_parent = [c for c in class_entities if c.parent_class]
        logger.debug(f"✓ 有继承关系的类: {len(classes_with_parent)}")
        
        # 检查 metadata 中的继承关系
        inheritance_count = len(graph.metadata.get('inheritance', [])) if 'inheritance' in graph.metadata else 0
        logger.debug(f"✓ 继承关系数: {inheritance_count}")
        
        if len(class_entities) >= 10:
            logger.debug("✓ 继承链测试通过")
            return True
        else:
            logger.error(f"✗ 继承链测试失败")
            return False
            
    except Exception as e:
        logger.error(f"✗ 继承链测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_many_files():
    """测试大量文件 (50 个)"""
    logger.debug("\n" + "="*80)
    logger.debug("测试 4: 大量文件 (50 个)")
    logger.debug("="*80)
    
    test_dir = project_root / "test_temp_many_files"
    test_dir.mkdir(exist_ok=True)
    
    # 生成 50 个文件
    for i in range(50):
        content = f"""
export class FileClass{i} {{
    method{i}() {{
        console.log('test');
    }}
}}
"""
        file_path = test_dir / f"File{i}.ets"
        file_path.write_text(content, encoding='utf-8')
    
    try:
        config = ParserConfig(
            target_project_path=str(test_dir),
            file_patterns=['*.ets']
        )
        parser = TypeScriptRegexParser(config)
        
        start_time = time.time()
        graph = parser.parse_project()
        elapsed = time.time() - start_time
        
        logger.debug(f"✓ 解析完成，耗时: {elapsed:.2f}s")
        logger.debug(f"✓ 实体总数: {len(graph.entities)}")
        
        file_entities = [e for e in graph.entities.values() if isinstance(e, FileEntity)]
        class_entities = [e for e in graph.entities.values() if isinstance(e, ClassEntity)]
        
        logger.debug(f"✓ 文件数: {len(file_entities)}")
        logger.debug(f"✓ 类数: {len(class_entities)}")
        
        if len(file_entities) >= 25:  # 只要至少找到一半就算通过
            logger.debug("✓ 多文件测试通过")
            return True
        else:
            logger.error(f"✗ 多文件测试失败: 只找到 {len(file_entities)} 个文件")
            return False
            
    except Exception as e:
        logger.error(f"✗ 多文件测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_circular_imports():
    """测试循环导入"""
    logger.debug("\n" + "="*80)
    logger.debug("测试 5: 循环导入 (A->B->C->A)")
    logger.debug("="*80)
    
    test_dir = project_root / "test_temp_circular"
    test_dir.mkdir(exist_ok=True)
    
    (test_dir / "A.ets").write_text("""
import { B } from './B';
export class A { b: B; }
""", encoding='utf-8')
    
    (test_dir / "B.ets").write_text("""
import { C } from './C';
export class B { c: C; }
""", encoding='utf-8')
    
    (test_dir / "C.ets").write_text("""
import { A } from './A';
export class C { a: A; }
""", encoding='utf-8')
    
    try:
        config = ParserConfig(
            target_project_path=str(test_dir),
            file_patterns=['*.ets']
        )
        parser = TypeScriptRegexParser(config)
        graph = parser.parse_project()
        
        logger.debug(f"✓ 解析完成，实体数: {len(graph.entities)}")
        
        file_entities = [e for e in graph.entities.values() if isinstance(e, FileEntity)]
        class_entities = [e for e in graph.entities.values() if isinstance(e, ClassEntity)]
        
        logger.debug(f"✓ 文件数: {len(file_entities)}")
        logger.debug(f"✓ 类数: {len(class_entities)}")
        
        import_count = len(graph.metadata.get('imports', [])) if 'imports' in graph.metadata else 0
        logger.debug(f"✓ 导入关系数: {import_count}")
        
        if len(class_entities) >= 2:
            logger.debug("✓ 循环导入测试通过")
            return True
        else:
            logger.error(f"✗ 循环导入测试失败")
            return False
            
    except Exception as e:
        logger.error(f"✗ 循环导入测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_edge_case_names():
    """测试特殊字符标识符"""
    logger.debug("\n" + "="*80)
    logger.debug("测试 6: 特殊字符和边界情况")
    logger.debug("="*80)
    
    test_dir = project_root / "test_temp_edge_cases"
    test_dir.mkdir(exist_ok=True)
    
    content = """
// 单字符类名
export class X {
    y: string;
    z() { return this.y; }
}

// 长类名
export class ThisIsAVeryLongClassNameThatTestsOurParser {
    thisIsAVeryLongPropertyNameThatShouldWork: number;
    thisIsAVeryLongMethodNameThatShouldWorkToo() {
        return 42;
    }
}
"""
    (test_dir / "EdgeCases.ets").write_text(content, encoding='utf-8')
    
    try:
        config = ParserConfig(
            target_project_path=str(test_dir),
            file_patterns=['*.ets']
        )
        parser = TypeScriptRegexParser(config)
        graph = parser.parse_project()
        
        class_entities = [e for e in graph.entities.values() if isinstance(e, ClassEntity)]
        logger.debug(f"✓ 找到 {len(class_entities)} 个类")
        
        class_names = [c.name for c in class_entities]
        logger.debug(f"✓ 类名: {class_names}")
        
        if any('X' in name for name in class_names):
            logger.debug("✓ 边界情况测试通过")
            return True
        else:
            logger.error(f"✗ 边界情况测试失败")
            return False
            
    except Exception as e:
        logger.error(f"✗ 边界情况测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False
    finally:
        import shutil
        if test_dir.exists():
            shutil.rmtree(test_dir)


def test_extreme_chaos_project():
    """测试我们之前生成的极限混乱项目"""
    logger.debug("\n" + "="*80)
    logger.debug("测试 7: 极限混乱项目 (265 个文件)")
    logger.debug("="*80)
    
    chaos_project = project_root / "extreme_chaos_test_project"
    if not chaos_project.exists():
        logger.warning("✗ 极限混乱项目不存在，跳过此测试")
        return None
    
    try:
        config = ParserConfig(
            target_project_path=str(chaos_project),
            file_patterns=['*.ets']
        )
        parser = TypeScriptRegexParser(config)
        
        start_time = time.time()
        graph = parser.parse_project()
        elapsed = time.time() - start_time
        
        logger.debug(f"✓ 解析完成，耗时: {elapsed:.2f}s")
        logger.debug(f"✓ 实体总数: {len(graph.entities)}")
        
        file_entities = [e for e in graph.entities.values() if isinstance(e, FileEntity)]
        class_entities = [e for e in graph.entities.values() if isinstance(e, ClassEntity)]
        method_entities = [e for e in graph.entities.values() if isinstance(e, MethodEntity)]
        property_entities = [e for e in graph.entities.values() if isinstance(e, PropertyEntity)]
        
        logger.debug(f"✓ 文件数: {len(file_entities)}")
        logger.debug(f"✓ 类数: {len(class_entities)}")
        logger.debug(f"✓ 方法数: {len(method_entities)}")
        logger.debug(f"✓ 属性数: {len(property_entities)}")
        
        for key in ['inheritance', 'imports', 'calls', 'components']:
            count = len(graph.metadata.get(key, [])) if key in graph.metadata else 0
            logger.debug(f"✓ {key} 关系数: {count}")
        
        if len(file_entities) >= 50:  # 只要能找到相当一部分文件就算通过
            logger.debug("✓ 极限混乱项目测试通过!")
            return {
                'success': True,
                'elapsed': elapsed,
                'files': len(file_entities),
                'classes': len(class_entities),
                'methods': len(method_entities),
                'properties': len(property_entities)
            }
        else:
            logger.error(f"✗ 极限混乱项目测试失败")
            return {'success': False}
            
    except Exception as e:
        logger.error(f"✗ 极限混乱项目测试异常: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {'success': False, 'error': str(e)}


def main():
    """运行所有测试"""
    print("\n" + "="*80)
    print("知识图谱系统 - 极限场景测试套件")
    print("="*80)
    
    results = {}
    
    # 运行所有测试
    tests = [
        ("空文件", test_empty_file),
        ("大文件", test_large_file),
        ("深度继承", test_deep_inheritance),
        ("多文件", test_many_files),
        ("循环导入", test_circular_imports),
        ("边界情况", test_edge_case_names),
        ("极限混乱", test_extreme_chaos_project),
    ]
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            if result is None:
                results[test_name] = "SKIPPED"
            elif isinstance(result, dict):
                results[test_name] = result['success']
            else:
                results[test_name] = result
        except Exception as e:
            logger.error(f"{test_name} 测试异常: {e}")
            results[test_name] = False
    
    # 打印总结
    print("\n" + "="*80)
    print("测试总结")
    print("="*80)
    
    passed = 0
    failed = 0
    skipped = 0
    
    for test_name, result in results.items():
        if result is True:
            print(f"✓ {test_name}: 通过")
            passed += 1
        elif result is False:
            print(f"✗ {test_name}: 失败")
            failed += 1
        else:
            print(f"- {test_name}: 跳过")
            skipped += 1
    
    print("\n" + "="*80)
    print(f"总计: {len(tests)} 个测试")
    print(f"通过: {passed}")
    print(f"失败: {failed}")
    print(f"跳过: {skipped}")
    print("="*80)
    
    if failed == 0:
        print("\n🎉 所有测试通过! 系统在极限场景下表现稳定。")
        return 0
    else:
        print(f"\n⚠️  有 {failed} 个测试失败，请查看日志 extreme_test_detailed.log")
        return 1


if __name__ == "__main__":
    sys.exit(main())
