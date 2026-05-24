#!/usr/bin/env python3
"""
超大规模极限测试脚本 v2.0

对知识图谱系统进行全面的极限测试：
- 超大规模项目解析（693个文件）
- 添加详细日志追踪
- 发现并记录潜在问题
- 性能监控
"""

import os
import sys
import time
import logging
import gc
from pathlib import Path
from typing import Dict, Any, List

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('ultra_test_detailed.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_section(title: str) -> None:
    """打印分隔标题。"""
    logger.debug("\n" + "="*80)
    logger.debug(f"  {title}")
    logger.debug("="*80)


def run_ultra_test(project_path: Path) -> Dict[str, Any]:
    """运行超大规模测试。"""
    print_section("超大规模极限测试")
    
    logger.debug(f"测试项目路径: {project_path}")
    logger.debug(f"项目是否存在: {project_path.exists()}")
    
    if not project_path.exists():
        logger.error(f"✗ 测试项目不存在: {project_path}")
        return {'success': False, 'error': 'Project not found'}
    
    # 统计文件数
    ets_files = list(project_path.rglob("*.ets"))
    logger.debug(f"ETS 文件总数: {len(ets_files)}")
    
    ts_files = list(project_path.rglob("*.ts"))
    logger.debug(f"TS 文件总数: {len(ts_files)}")
    
    total_files = len(ets_files) + len(ts_files)
    logger.debug(f"总文件数: {total_files}")
    
    try:
        from parser.ark_analyzer_adapter import TypeScriptRegexParser, ParserConfig
        
        print_section("开始解析项目")
        
        config = ParserConfig(
            target_project_path=str(project_path),
            file_patterns=['*.ets', '*.ts']
        )
        
        parser = TypeScriptRegexParser(config)
        
        # 解析前记录
        logger.debug("解析前 - 强制垃圾回收")
        gc.collect()
        
        # 开始解析
        logger.debug("开始调用 parse_project()")
        start_time = time.time()
        
        knowledge_graph = parser.parse_project()
        
        elapsed = time.time() - start_time
        
        # 解析后记录
        logger.debug(f"解析完成!")
        logger.debug(f"总耗时: {elapsed:.2f}s")
        logger.debug(f"平均每文件: {elapsed/total_files*1000:.2f}ms")
        
        print_section("解析结果统计")
        
        # 统计实体
        entities = knowledge_graph.entities
        logger.debug(f"实体总数: {len(entities)}")
        
        # 分类统计
        file_entities = [e for e in entities.values() if e.__class__.__name__ == 'FileEntity']
        class_entities = [e for e in entities.values() if e.__class__.__name__ == 'ClassEntity']
        method_entities = [e for e in entities.values() if e.__class__.__name__ == 'MethodEntity']
        property_entities = [e for e in entities.values() if e.__class__.__name__ == 'PropertyEntity']
        
        logger.debug(f"文件实体: {len(file_entities)}")
        logger.debug(f"类实体: {len(class_entities)}")
        logger.debug(f"方法实体: {len(method_entities)}")
        logger.debug(f"属性实体: {len(property_entities)}")
        
        # 统计关系
        metadata = knowledge_graph.metadata
        logger.debug(f"\n关系统计:")
        
        inheritance = metadata.get('inheritance', [])
        imports = metadata.get('imports', [])
        calls = metadata.get('calls', [])
        components = metadata.get('components', [])
        
        logger.debug(f"继承关系: {len(inheritance)}")
        logger.debug(f"导入关系: {len(imports)}")
        logger.debug(f"调用关系: {len(calls)}")
        logger.debug(f"组件关系: {len(components)}")
        
        # 分析问题
        print_section("潜在问题分析")
        issues = []
        
        # 检查文件解析率
        expected_files = total_files
        actual_files = len(file_entities)
        file_coverage = (actual_files / expected_files) * 100 if expected_files > 0 else 0
        
        logger.debug(f"文件解析覆盖率: {file_coverage:.2f}%")
        
        if file_coverage < 80:
            issues.append(f"文件解析覆盖率过低: {file_coverage:.2f}%")
            logger.warning(f"⚠️  警告: 文件解析覆盖率过低 ({file_coverage:.2f}%)")
        
        # 检查语法错误文件的处理
        error_files = [f for f in ets_files if 'ErrorFile' in f.name]
        logger.debug(f"语法错误文件数: {len(error_files)}")
        
        # 检查 Unicode 文件
        unicode_files = [f for f in ets_files if 'UnicodeFile' in f.name]
        unicode_classes = [c for c in class_entities if any(ord(ch) > 127 for ch in c.name)]
        logger.debug(f"Unicode 文件数: {len(unicode_files)}")
        logger.debug(f"Unicode 类数: {len(unicode_classes)}")
        
        # 检查超大文件
        ultra_large_files = [f for f in ets_files if 'UltraLargeFile' in f.name]
        if ultra_large_files:
            ultra_large_classes = [c for c in class_entities if 'LargeClass' in c.name]
            logger.debug(f"超大文件类数: {len(ultra_large_classes)}")
        
        # 检查继承链
        if inheritance:
            depths = {}
            for inh in inheritance:
                parent_name = inh.get('parent_class_name', '')
                if parent_name:
                    depths[parent_name] = depths.get(parent_name, 0) + 1
            
            if depths:
                max_depth = max(len(d) for d in depths.keys()) if depths else 0
                logger.debug(f"继承关系深度: {max_depth}")
        
        # 检查组件嵌套
        if components:
            nesting_depths = {}
            for comp in components:
                child_name = comp.get('child_name', '')
                if child_name and 'NestedComponent' in child_name:
                    match = [c for c in child_name if c.isdigit()]
                    if match:
                        depth = int(match[0])
                        nesting_depths[depth] = nesting_depths.get(depth, 0) + 1
            
            if nesting_depths:
                max_nesting = max(nesting_depths.keys())
                logger.debug(f"组件嵌套最大深度: {max_nesting}")
        
        # 性能评估
        print_section("性能评估")
        
        if elapsed < 5:
            logger.debug(f"✅ 解析性能优秀: {elapsed:.2f}s")
        elif elapsed < 10:
            logger.debug(f"⚠️  解析性能一般: {elapsed:.2f}s")
        else:
            logger.debug(f"❌ 解析性能较差: {elapsed:.2f}s")
        
        # 实体密度评估
        entity_density = len(entities) / total_files if total_files > 0 else 0
        logger.debug(f"实体密度: {entity_density:.2f} 实体/文件")
        
        if entity_density < 3:
            logger.warning(f"⚠️  实体密度偏低: {entity_density:.2f}")
        
        # 返回结果
        return {
            'success': True,
            'total_files': total_files,
            'elapsed': elapsed,
            'entities': {
                'total': len(entities),
                'files': len(file_entities),
                'classes': len(class_entities),
                'methods': len(method_entities),
                'properties': len(property_entities)
            },
            'relations': {
                'inheritance': len(inheritance),
                'imports': len(imports),
                'calls': len(calls),
                'components': len(components)
            },
            'metrics': {
                'file_coverage': file_coverage,
                'entity_density': entity_density,
                'avg_time_per_file': elapsed/total_files*1000
            },
            'issues': issues
        }
        
    except Exception as e:
        logger.error(f"✗ 测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def test_database_operations() -> Dict[str, Any]:
    """测试数据库操作。"""
    print_section("数据库操作测试")
    
    try:
        from database.knowledge_repository import KnowledgeRepository
        
        db_path = project_root / "data" / "test_ultra.db"
        db_path.parent.mkdir(exist_ok=True)
        
        if db_path.exists():
            db_path.unlink()
        
        logger.debug("创建数据库仓库...")
        repo = KnowledgeRepository(str(db_path))
        
        # 测试统计查询
        logger.debug("测试统计查询...")
        stats = repo.get_statistics()
        logger.debug(f"统计查询成功: {stats}")
        
        # 测试 SQL 执行
        logger.debug("测试 SQL 执行...")
        result = repo.execute_sql("SELECT COUNT(*) as cnt FROM files")
        logger.debug(f"SQL 执行成功: {result}")
        
        return {'success': True}
        
    except Exception as e:
        logger.error(f"✗ 数据库测试失败: {e}")
        return {'success': False, 'error': str(e)}


def test_edge_cases() -> Dict[str, Any]:
    """测试边界情况。"""
    print_section("边界情况测试")
    
    edge_cases_dir = project_root / "test_edge_cases"
    edge_cases_dir.mkdir(exist_ok=True)
    
    tests = []
    
    # 测试 1: 特殊字符文件名
    logger.debug("测试 1: 特殊字符文件名")
    special_file = edge_cases_dir / "Special-File@#$%.ets"
    special_file.write_text("""
export class SpecialClass {
    test() { return 'special'; }
}
""", encoding='utf-8')
    tests.append(("特殊字符文件名", special_file.exists()))
    
    # 测试 2: 超长文件名
    logger.debug("测试 2: 超长文件名")
    long_name = "A" * 200 + ".ets"
    long_file = edge_cases_dir / long_name
    long_file.write_text("""
export class LongNameClass {
    test() { return 'long'; }
}
""", encoding='utf-8')
    tests.append(("超长文件名", long_file.exists()))
    
    # 测试 3: 空文件
    logger.debug("测试 3: 空文件")
    empty_file = edge_cases_dir / "Empty.ets"
    empty_file.write_text("", encoding='utf-8')
    tests.append(("空文件", empty_file.exists()))
    
    # 测试 4: 只有注释的文件
    logger.debug("测试 4: 只有注释的文件")
    comment_file = edge_cases_dir / "CommentOnly.ets"
    comment_file.write_text("""
// 只有注释的文件
/* 多行注释 */
""", encoding='utf-8')
    tests.append(("只有注释的文件", comment_file.exists()))
    
    # 测试 5: Unicode 标识符
    logger.debug("测试 5: Unicode 标识符")
    unicode_file = edge_cases_dir / "Unicode.ets"
    unicode_file.write_text("""
// 中文标识符
export class 中文类 {
    中文属性: string;
    中文方法() {
        return this.中文属性;
    }
}
""", encoding='utf-8')
    tests.append(("Unicode 标识符", unicode_file.exists()))
    
    # 统计
    passed = sum(1 for _, result in tests if result)
    total = len(tests)
    
    logger.debug(f"\n边界情况测试结果: {passed}/{total} 通过")
    for name, result in tests:
        status = "✓" if result else "✗"
        logger.debug(f"  {status} {name}")
    
    # 清理
    import shutil
    if edge_cases_dir.exists():
        shutil.rmtree(edge_cases_dir)
    
    return {
        'success': passed == total,
        'passed': passed,
        'total': total,
        'tests': tests
    }


def main():
    """主函数。"""
    print("\n" + "="*80)
    print("  知识图谱系统 - 超大规模极限测试 v2.0")
    print("="*80)
    
    # 测试项目路径
    test_project_path = project_root / "ultra_chaos_test_project"
    
    results = {}
    
    # 测试 1: 超大规模项目
    logger.debug("\n" + "="*80)
    logger.debug("测试 1: 超大规模项目解析 (693 文件)")
    logger.debug("="*80)
    ultra_result = run_ultra_test(test_project_path)
    results['ultra_test'] = ultra_result
    
    # 测试 2: 数据库操作
    logger.debug("\n" + "="*80)
    logger.debug("测试 2: 数据库操作")
    logger.debug("="*80)
    db_result = test_database_operations()
    results['database'] = db_result
    
    # 测试 3: 边界情况
    logger.debug("\n" + "="*80)
    logger.debug("测试 3: 边界情况")
    logger.debug("="*80)
    edge_result = test_edge_cases()
    results['edge_cases'] = edge_result
    
    # 总结
    print("\n" + "="*80)
    print("  测试总结报告")
    print("="*80)
    
    if ultra_result.get('success'):
        print(f"\n✅ 超大规模测试: 通过")
        print(f"   - 文件数: {ultra_result['total_files']}")
        print(f"   - 耗时: {ultra_result['elapsed']:.2f}s")
        print(f"   - 实体数: {ultra_result['entities']['total']}")
        print(f"   - 文件覆盖率: {ultra_result['metrics']['file_coverage']:.2f}%")
    else:
        print(f"\n❌ 超大规模测试: 失败")
        if 'error' in ultra_result:
            print(f"   错误: {ultra_result['error']}")
    
    if db_result.get('success'):
        print(f"\n✅ 数据库测试: 通过")
    else:
        print(f"\n❌ 数据库测试: 失败")
        if 'error' in db_result:
            print(f"   错误: {db_result['error']}")
    
    if edge_result.get('success'):
        print(f"\n✅ 边界情况测试: 通过 ({edge_result['passed']}/{edge_result['total']})")
    else:
        print(f"\n⚠️  边界情况测试: 部分通过 ({edge_result['passed']}/{edge_result['total']})")
    
    # 潜在问题
    if ultra_result.get('success') and ultra_result.get('issues'):
        print(f"\n⚠️  发现的问题:")
        for issue in ultra_result['issues']:
            print(f"   - {issue}")
    
    print("\n" + "="*80)
    
    all_success = (
        ultra_result.get('success', False) and
        db_result.get('success', False) and
        edge_result.get('success', False)
    )
    
    if all_success:
        print("🎉 所有测试通过!")
    else:
        print("⚠️  部分测试失败，请查看详细日志")
    
    print("="*80)
    
    return 0 if all_success else 1


if __name__ == '__main__':
    sys.exit(main())
