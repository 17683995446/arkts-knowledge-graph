#!/usr/bin/env python3
"""
极限压力测试脚本

对知识图谱系统进行全面的极限测试：
- 大规模项目解析（265个文件）
- 压力测试（多次重复构建）
- 内存和性能监控
- 详细的日志输出用于问题诊断
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
        logging.FileHandler('extreme_test.log', encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))


def print_memory_usage(stage: str) -> None:
    """打印内存使用情况（简单版本）。"""
    try:
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        logger.debug(f"[内存监控] {stage}: {memory_mb:.2f} MB")
    except ImportError:
        pass


def run_test_build(project_path: Path, force_rebuild: bool = True) -> Dict[str, Any]:
    """
    运行单次知识图谱构建测试。
    
    返回测试结果统计。
    """
    from core.config_manager import config
    from database.knowledge_repository import KnowledgeRepository
    from parser.ark_analyzer_adapter import ArkAnalyzerAdapter, ParserConfig
    
    logger.debug("=" * 80)
    logger.debug(f"[测试开始] 构建知识图谱: {project_path}")
    logger.debug("=" * 80)
    
    start_time = time.time()
    print_memory_usage("开始前")
    
    try:
        # 初始化
        logger.debug("[步骤 1/5] 初始化数据库仓库...")
        db_path = project_root / "data" / "test_extreme.db"
        db_path.parent.mkdir(exist_ok=True)
        if db_path.exists() and force_rebuild:
            db_path.unlink()
        repo = KnowledgeRepository(str(db_path))
        
        # 清除已有数据
        if force_rebuild:
            logger.debug("[步骤 2/5] 清除已有数据...")
            repo.clear_all_data()
        
        # 初始化解析器
        logger.debug("[步骤 3/5] 初始化解析器...")
        parser_config = ParserConfig(
            target_project_path=str(project_path),
            file_patterns=['*.ets', '*.ts']
        )
        adapter = ArkAnalyzerAdapter(parser_config)
        
        # 解析项目
        logger.debug("[步骤 4/5] 开始解析项目...")
        parse_start = time.time()
        knowledge_graph = adapter.parse_project()
        parse_time = time.time() - parse_start
        logger.debug(f"[解析完成] 耗时: {parse_time:.2f}s, 实体数: {len(knowledge_graph.entities)}")
        print_memory_usage("解析后")
        
        # 保存到数据库
        logger.debug("[步骤 5/5] 保存到数据库...")
        save_start = time.time()
        repo.begin_transaction()
        
        entity_counts = {
            'files': 0,
            'classes': 0,
            'methods': 0,
            'properties': 0
        }
        
        from core.entity_models import FileEntity, ClassEntity, MethodEntity, PropertyEntity
        
        for entity_id, entity in knowledge_graph.entities.items():
            logger.debug(f"[保存实体] ID: {entity_id}, 类型: {type(entity).__name__}")
            
            if isinstance(entity, FileEntity):
                repo.save_file(entity)
                entity_counts['files'] += 1
            elif isinstance(entity, ClassEntity):
                repo.save_class(entity)
                entity_counts['classes'] += 1
            elif isinstance(entity, MethodEntity):
                repo.save_method(entity)
                entity_counts['methods'] += 1
            elif isinstance(entity, PropertyEntity):
                repo.save_property(entity)
                entity_counts['properties'] += 1
        
        # 保存关系
        relation_counts = {
            'inheritance': 0,
            'imports': 0,
            'calls': 0,
            'components': 0
        }
        
        if 'inheritance' in knowledge_graph.metadata:
            for inh in knowledge_graph.metadata['inheritance']:
                parent_class_id = None
                for entity in knowledge_graph.entities.values():
                    if isinstance(entity, ClassEntity) and entity.name == inh.get('parent_class_name'):
                        parent_class_id = entity.id
                        break
                repo.save_inheritance(
                    inh.get('child_class_id'),
                    parent_class_id,
                    inh.get('parent_class_name'),
                    inh.get('relation_type', 'extends')
                )
                relation_counts['inheritance'] += 1
        
        if 'imports' in knowledge_graph.metadata:
            for imp in knowledge_graph.metadata['imports']:
                repo.save_import(
                    imp.get('source_file_id'),
                    imp.get('import_path', '')
                )
                relation_counts['imports'] += 1
        
        if 'calls' in knowledge_graph.metadata:
            for call in knowledge_graph.metadata['calls']:
                repo.save_call(call)
                relation_counts['calls'] += 1
        
        if 'components' in knowledge_graph.metadata:
            for comp in knowledge_graph.metadata['components']:
                repo.save_component_nesting(comp)
                relation_counts['components'] += 1
        
        repo.commit_transaction()
        save_time = time.time() - save_start
        
        # 获取统计数据
        stats = repo.get_statistics()
        
        total_time = time.time() - start_time
        print_memory_usage("保存后")
        
        logger.debug("=" * 80)
        logger.debug("[测试完成] 构建成功!")
        logger.debug("=" * 80)
        logger.debug(f"  总耗时: {total_time:.2f}s")
        logger.debug(f"  解析耗时: {parse_time:.2f}s")
        logger.debug(f"  保存耗时: {save_time:.2f}s")
        logger.debug(f"  文件数: {entity_counts['files']}")
        logger.debug(f"  类数: {entity_counts['classes']}")
        logger.debug(f"  方法数: {entity_counts['methods']}")
        logger.debug(f"  属性数: {entity_counts['properties']}")
        logger.debug(f"  继承关系: {relation_counts['inheritance']}")
        logger.debug(f"  导入关系: {relation_counts['imports']}")
        logger.debug(f"  调用关系: {relation_counts['calls']}")
        logger.debug(f"  组件关系: {relation_counts['components']}")
        logger.debug("  数据库统计:")
        for key, value in stats.items():
            logger.debug(f"    {key}: {value}")
        
        return {
            'success': True,
            'total_time': total_time,
            'parse_time': parse_time,
            'save_time': save_time,
            'entity_counts': entity_counts,
            'relation_counts': relation_counts,
            'stats': stats
        }
        
    except Exception as e:
        logger.error(f"[测试失败] 构建过程出错: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e),
            'traceback': traceback.format_exc()
        }


def run_stress_test(project_path: Path, iterations: int = 5) -> List[Dict[str, Any]]:
    """
    运行压力测试 - 多次重复构建。
    """
    logger.debug("\n" + "=" * 80)
    logger.debug(f"压力测试开始 - {iterations} 次迭代")
    logger.debug("=" * 80)
    
    results = []
    
    for i in range(iterations):
        logger.debug(f"\n[迭代 {i+1}/{iterations}]")
        gc.collect()  # 垃圾回收
        result = run_test_build(project_path, force_rebuild=(i > 0))
        results.append(result)
        
        if not result['success']:
            logger.error(f"迭代 {i+1} 失败，停止测试")
            break
        
        time.sleep(1)  # 短暂暂停
    
    # 汇总结果
    success_count = sum(1 for r in results if r['success'])
    logger.debug("\n" + "=" * 80)
    logger.debug("压力测试汇总")
    logger.debug("=" * 80)
    logger.debug(f"  总迭代: {iterations}")
    logger.debug(f"  成功: {success_count}")
    logger.debug(f"  失败: {iterations - success_count}")
    
    if success_count > 0:
        times = [r['total_time'] for r in results if r['success']]
        logger.debug(f"  平均耗时: {sum(times)/len(times):.2f}s")
        logger.debug(f"  最小耗时: {min(times):.2f}s")
        logger.debug(f"  最大耗时: {max(times):.2f}s")
    
    return results


def run_api_test() -> Dict[str, Any]:
    """
    测试 API 接口。
    """
    logger.debug("\n" + "=" * 80)
    logger.debug("API 接口测试")
    logger.debug("=" * 80)
    
    from core.config_manager import config
    from database.knowledge_repository import KnowledgeRepository
    
    try:
        db_path = project_root / "data" / "test_extreme.db"
        repo = KnowledgeRepository(str(db_path))
        
        # 测试获取统计
        logger.debug("[API 测试] 获取统计数据...")
        stats = repo.get_statistics()
        logger.debug(f"[成功] 统计: {stats}")
        
        # 测试获取文件列表
        logger.debug("[API 测试] 获取文件列表...")
        files = repo.get_all_files()
        logger.debug(f"[成功] 文件数: {len(files)}")
        
        # 测试获取类列表
        logger.debug("[API 测试] 获取类列表...")
        classes = repo.get_all_classes()
        logger.debug(f"[成功] 类数: {len(classes)}")
        
        # 测试获取组件
        logger.debug("[API 测试] 获取组件...")
        components = repo.get_components()
        logger.debug(f"[成功] 组件数: {len(components)}")
        
        # 测试获取类方法
        if classes:
            logger.debug("[API 测试] 获取类方法...")
            methods = repo.get_methods_by_class(classes[0]['id'])
            logger.debug(f"[成功] 方法数: {len(methods)}")
        
        # 测试查询
        logger.debug("[API 测试] 执行 SQL 查询...")
        result = repo.execute_sql("SELECT COUNT(*) as cnt FROM files")
        logger.debug(f"[成功] 查询结果: {result}")
        
        return {
            'success': True,
            'stats': stats,
            'file_count': len(files),
            'class_count': len(classes)
        }
        
    except Exception as e:
        logger.error(f"[API 测试失败] {e}")
        import traceback
        logger.error(traceback.format_exc())
        return {
            'success': False,
            'error': str(e)
        }


def main():
    """主函数。"""
    print("=" * 80)
    print("知识图谱系统 - 极限压力测试")
    print("=" * 80)
    
    # 测试项目路径
    test_project_path = project_root / "extreme_chaos_test_project"
    
    if not test_project_path.exists():
        logger.error(f"测试项目不存在: {test_project_path}")
        logger.error("请先运行 create_extreme_chaos_test.py 生成测试项目")
        return 1
    
    # 第1阶段: 单次完整构建
    logger.debug("\n[阶段 1] 单次完整构建测试")
    single_result = run_test_build(test_project_path, force_rebuild=True)
    
    if not single_result['success']:
        logger.error("单次构建失败，停止测试")
        return 1
    
    # 第2阶段: API 接口测试
    logger.debug("\n[阶段 2] API 接口测试")
    api_result = run_api_test()
    
    # 第3阶段: 压力测试（3次迭代）
    logger.debug("\n[阶段 3] 压力测试")
    stress_results = run_stress_test(test_project_path, iterations=3)
    
    # 最终总结
    print("\n" + "=" * 80)
    print("测试总结报告")
    print("=" * 80)
    
    print(f"\n单次构建: {'✅ 成功' if single_result['success'] else '❌ 失败'}")
    if single_result['success']:
        print(f"  耗时: {single_result['total_time']:.2f}s")
        print(f"  文件: {single_result['entity_counts']['files']}")
        print(f"  类: {single_result['entity_counts']['classes']}")
        print(f"  方法: {single_result['entity_counts']['methods']}")
        print(f"  属性: {single_result['entity_counts']['properties']}")
    
    print(f"\nAPI 测试: {'✅ 成功' if api_result['success'] else '❌ 失败'}")
    
    stress_success = sum(1 for r in stress_results if r['success'])
    print(f"\n压力测试: {stress_success}/{len(stress_results)} 次成功")
    
    # 检查是否有问题
    all_success = single_result['success'] and api_result['success'] and stress_success == len(stress_results)
    
    if all_success:
        print("\n🎉 所有测试通过！系统运行稳定。")
        return 0
    else:
        print("\n⚠️  部分测试失败，请查看日志文件 extreme_test.log 了解详情。")
        return 1


if __name__ == '__main__':
    sys.exit(main())
