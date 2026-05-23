#!/usr/bin/env python3
"""
Build Knowledge Graph Script

Standalone script to build the knowledge graph from an ArkTS project.
Can be run independently or imported as a module.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def build_graph(project_path: str, db_path: str = None, force: bool = False) -> bool:
    """
    Build the knowledge graph from an ArkTS project.
    
    Args:
        project_path: Path to the ArkTS project directory
        db_path: Path to the SQLite database (optional)
        force: Whether to force rebuild (clear existing data)
    
    Returns:
        True if successful, False otherwise
    """
    # Add project root to path
    script_dir = Path(__file__).parent.resolve()
    sys.path.insert(0, str(script_dir))
    
    from core.config_manager import ConfigurationManager
    from database.knowledge_repository import KnowledgeRepository
    from parser.ark_analyzer_adapter import ArkAnalyzerAdapter, ParserConfig
    from core.entity_models import FileEntity, ClassEntity, MethodEntity, PropertyEntity
    
    # Validate project path
    project_path = Path(project_path).resolve()
    if not project_path.exists():
        logger.error(f"Project path does not exist: {project_path}")
        return False
    
    if not project_path.is_dir():
        logger.error(f"Project path is not a directory: {project_path}")
        return False
    
    logger.info(f"Building knowledge graph for: {project_path}")
    
    # Setup database path
    if db_path is None:
        data_dir = script_dir / 'data'
        data_dir.mkdir(exist_ok=True)
        db_path = data_dir / 'code_knowledge_graph.db'
    else:
        db_path = Path(db_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)
    
    logger.info(f"Database path: {db_path}")
    
    # Initialize repository
    repository = KnowledgeRepository(str(db_path))
    
    # Clear existing data if force rebuild
    if force:
        logger.info("Clearing existing data...")
        repository.clear_all_data()
    
    # Initialize parser
    parser_config = ParserConfig(
        target_project_path=str(project_path),
        file_patterns=['*.ets', '*.ts']
    )
    adapter = ArkAnalyzerAdapter(parser_config)
    
    # Parse project
    try:
        logger.info("Parsing project files...")
        knowledge_graph = adapter.parse_project()
        
        logger.info(f"Parsed {len(knowledge_graph.entities)} entities")
        
        # Store entities in database
        logger.info("Storing entities in database...")
        
        repository.begin_transaction()
        try:
            entity_counts = {
                'files': 0,
                'classes': 0,
                'methods': 0,
                'properties': 0
            }
            
            for entity in knowledge_graph.entities.values():
                if isinstance(entity, FileEntity):
                    repository.save_file(entity)
                    entity_counts['files'] += 1
                elif isinstance(entity, ClassEntity):
                    repository.save_class(entity)
                    entity_counts['classes'] += 1
                elif isinstance(entity, MethodEntity):
                    repository.save_method(entity)
                    entity_counts['methods'] += 1
                elif isinstance(entity, PropertyEntity):
                    repository.save_property(entity)
                    entity_counts['properties'] += 1
            
            # 处理继承关系
            relation_counts = {'inheritance': 0, 'imports': 0}
            if 'inheritance' in knowledge_graph.metadata:
                for inh in knowledge_graph.metadata['inheritance']:
                    # 查找父类的ID
                    parent_class_id = None
                    for entity in knowledge_graph.entities.values():
                        if isinstance(entity, ClassEntity) and entity.name == inh['parent_class_name']:
                            parent_class_id = entity.id
                            break
                    
                    repository.save_inheritance(
                        inh['child_class_id'],
                        parent_class_id,
                        inh['parent_class_name'],
                        inh['relation_type']
                    )
                    relation_counts['inheritance'] += 1
            
            # 处理导入关系
            if 'imports' in knowledge_graph.metadata:
                for imp in knowledge_graph.metadata['imports']:
                    repository.save_import(
                        imp['source_file_id'],
                        imp['import_path']
                    )
                    relation_counts['imports'] += 1
            
            # 处理方法调用关系
            relation_counts['calls'] = 0
            if 'calls' in knowledge_graph.metadata:
                for call in knowledge_graph.metadata['calls']:
                    repository.save_call(call)
                    relation_counts['calls'] += 1
            
            # 处理组件嵌套关系
            relation_counts['components'] = 0
            if 'components' in knowledge_graph.metadata:
                for comp in knowledge_graph.metadata['components']:
                    repository.save_component_nesting(comp)
                    relation_counts['components'] += 1
            
            repository.commit_transaction()
        except Exception:
            repository.rollback_transaction()
            raise
        
        logger.info("=" * 50)
        logger.info("Knowledge graph built successfully!")
        logger.info("=" * 50)
        logger.info(f"Files:      {entity_counts['files']}")
        logger.info(f"Classes:    {entity_counts['classes']}")
        logger.info(f"Methods:    {entity_counts['methods']}")
        logger.info(f"Properties: {entity_counts['properties']}")
        logger.info(f"Inheritance: {relation_counts['inheritance']}")
        logger.info(f"Imports:    {relation_counts['imports']}")
        logger.info(f"Calls:      {relation_counts['calls']}")
        logger.info(f"Components: {relation_counts['components']}")
        logger.info("=" * 50)
        
        # Show statistics
        stats = repository.get_statistics()
        logger.info("\nDatabase Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error building knowledge graph: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description='Build ArkTS Knowledge Graph from project source code'
    )
    parser.add_argument(
        '--path', '-p',
        required=True,
        help='Path to the ArkTS project directory'
    )
    parser.add_argument(
        '--db', '-d',
        help='Path to the SQLite database file (optional)'
    )
    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force rebuild (clear existing data)'
    )
    
    args = parser.parse_args()
    
    success = build_graph(args.path, args.db, args.force)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()
