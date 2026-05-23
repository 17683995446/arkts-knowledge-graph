"""
ArkTS Knowledge Graph - Main Application

Entry point for the ArkTS code knowledge graph system.
Provides commands for building the graph and running the web server.
"""

import os
import sys
import argparse
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def setup_environment():
    """Setup the environment and paths."""
    # Add project root to path
    project_root = Path(__file__).parent.resolve()
    sys.path.insert(0, str(project_root))
    
    # Ensure data directory exists
    data_dir = project_root / 'data'
    data_dir.mkdir(exist_ok=True)


def build_knowledge_graph(project_path: str, force_rebuild: bool = False) -> bool:
    """
    Build the knowledge graph from an ArkTS project.
    
    Args:
        project_path: Path to the ArkTS project
        force_rebuild: Whether to clear existing data and rebuild
    
    Returns:
        True if successful, False otherwise
    """
    from core.config_manager import config
    from database.knowledge_repository import KnowledgeRepository
    from parser.ark_analyzer_adapter import ArkAnalyzerAdapter, ParserConfig
    
    logger.info(f"Building knowledge graph for: {project_path}")
    
    # Validate project path
    project_path = Path(project_path).resolve()
    if not project_path.exists():
        logger.error(f"Project path does not exist: {project_path}")
        return False
    
    # Initialize repository
    repository = KnowledgeRepository(config.database.path)
    
    # Clear existing data if force rebuild
    if force_rebuild:
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
        logger.info("Parsing project...")
        knowledge_graph = adapter.parse_project()
        
        logger.info(f"Found {len(knowledge_graph.entities)} entities")
        
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
                from core.entity_models import FileEntity, ClassEntity, MethodEntity, PropertyEntity
                
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
        
        logger.info("Knowledge graph built successfully!")
        logger.info(f"  Files: {entity_counts['files']}")
        logger.info(f"  Classes: {entity_counts['classes']}")
        logger.info(f"  Methods: {entity_counts['methods']}")
        logger.info(f"  Properties: {entity_counts['properties']}")
        logger.info(f"  Inheritance: {relation_counts['inheritance']}")
        logger.info(f"  Imports: {relation_counts['imports']}")
        logger.info(f"  Calls: {relation_counts['calls']}")
        logger.info(f"  Components: {relation_counts['components']}")
        
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


def run_web_server(host: str = None, port: int = None, debug: bool = None):
    """
    Run the web server for visualization.
    
    Args:
        host: Host to bind to
        port: Port to bind to
        debug: Debug mode
    """
    from web.server_application import server
    
    logger.info("Starting web server...")
    server.run(host=host, port=port, debug=debug)


def run_query(question: str):
    """
    Execute a natural language query.
    
    Args:
        question: Natural language question about the code
    """
    from core.config_manager import config
    from database.knowledge_repository import KnowledgeRepository
    from llm.silicon_flow_client import SiliconFlowClient, QueryEngine
    
    # Check if LLM is configured
    if not config.llm.api_key:
        logger.error("LLM API key not configured. Please set SILICON_FLOW_API_KEY in .env")
        return
    
    # Initialize components
    repository = KnowledgeRepository(config.database.path)
    llm_client = SiliconFlowClient(
        api_key=config.llm.api_key,
        base_url=config.llm.base_url,
        model=config.llm.model
    )
    query_engine = QueryEngine(
        llm_client=llm_client,
        schema_info=repository.get_schema_info()
    )
    
    # Execute query
    logger.info(f"Query: {question}")
    result = query_engine.ask(question, repository.execute_sql)
    
    if result['success']:
        print(f"\nSQL: {result['sql']}\n")
        print("Results:")
        if result['results']:
            # Print as table
            if result['results']:
                columns = list(result['results'][0].keys())
                # Print header
                print(" | ".join(columns))
                print("-" * (sum(len(c) for c in columns) + 3 * len(columns)))
                # Print rows
                for row in result['results'][:20]:  # Limit to 20 rows
                    print(" | ".join(str(row.get(c, '')) for c in columns))
                if len(result['results']) > 20:
                    print(f"\n... and {len(result['results']) - 20} more rows")
        else:
            print("No results found.")
    else:
        logger.error(f"Query failed: {result.get('error', 'Unknown error')}")


def main():
    """Main entry point."""
    setup_environment()
    
    parser = argparse.ArgumentParser(
        description='ArkTS Knowledge Graph - Code structure visualization and analysis',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Build knowledge graph from a project
  python main_application.py build --path /path/to/arkts/project
  
  # Run the web server
  python main_application.py server
  
  # Run a query
  python main_application.py query "Which components are used in UserPage?"
        """
    )
    
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build the knowledge graph')
    build_parser.add_argument(
        '--path', '-p',
        required=True,
        help='Path to the ArkTS project'
    )
    build_parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force rebuild (clear existing data)'
    )
    
    # Server command
    server_parser = subparsers.add_parser('server', help='Run the web server')
    server_parser.add_argument(
        '--host', '-H',
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )
    server_parser.add_argument(
        '--port', '-P',
        type=int,
        default=5000,
        help='Port to bind to (default: 5000)'
    )
    server_parser.add_argument(
        '--debug', '-d',
        action='store_true',
        help='Enable debug mode'
    )
    
    # Query command
    query_parser = subparsers.add_parser('query', help='Execute a natural language query')
    query_parser.add_argument(
        'question',
        help='Natural language question about the code'
    )
    
    # Parse arguments
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    # Execute command
    if args.command == 'build':
        success = build_knowledge_graph(args.path, args.force)
        sys.exit(0 if success else 1)
    
    elif args.command == 'server':
        run_web_server(args.host, args.port, args.debug)
    
    elif args.command == 'query':
        run_query(args.question)


if __name__ == '__main__':
    main()
