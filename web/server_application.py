"""
Flask Server Application Module

Provides the web server for the ArkTS Knowledge Graph visualization system.
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

from flask import Flask, render_template, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_socketio import SocketIO, emit

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.config_manager import config
from core.file_watcher import FileWatcher, FileChangeEvent
from database.knowledge_repository import KnowledgeRepository
from llm.silicon_flow_client import SiliconFlowClient, QueryEngine


def create_application() -> Flask:
    """Create and configure the Flask application."""
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent.parent / 'templates'),
        static_folder=str(Path(__file__).parent.parent / 'static')
    )
    
    app.config['SECRET_KEY'] = config.web_server.secret_key
    app.config['DEBUG'] = config.web_server.debug
    
    # Enable CORS
    CORS(app)
    
    return app


class KnowledgeGraphServer:
    """
    Main server class that manages all components.
    
    Coordinates the database, file watcher, LLM client, and web server.
    """
    
    def __init__(self):
        self.app = create_application()
        self.socketio = SocketIO(self.app, cors_allowed_origins="*")
        
        # Initialize components
        self.repository = KnowledgeRepository(config.database.path)
        self.llm_client: Optional[SiliconFlowClient] = None
        self.query_engine: Optional[QueryEngine] = None
        self.file_watcher: Optional[FileWatcher] = None
        
        logger.debug("[DEBUG] [KnowledgeGraphServer] [__init__] 服务器初始化, db_path=%s", config.database.path)
        
        # Setup routes and socket events
        self._setup_routes()
        self._setup_socket_events()
        
        # Initialize LLM if API key is available
        if config.llm.api_key:
            self.llm_client = SiliconFlowClient(
                api_key=config.llm.api_key,
                base_url=config.llm.base_url,
                model=config.llm.model
            )
            self.query_engine = QueryEngine(
                llm_client=self.llm_client,
                schema_info=self.repository.get_schema_info()
            )
            logger.debug("[DEBUG] [KnowledgeGraphServer] [__init__] LLM已配置, model=%s", config.llm.model)
        else:
            logger.debug("[DEBUG] [KnowledgeGraphServer] [__init__] LLM未配置 (无API密钥)")
    
    def _setup_routes(self) -> None:
        """Setup HTTP routes."""
        
        @self.app.route('/')
        def index():
            """Render the main page."""
            return render_template('index.html')
        
        @self.app.route('/api/stats')
        def get_stats():
            """Get database statistics."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_stats] 收到统计请求")
            try:
                stats = self.repository.get_statistics()
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_stats] 返回统计成功")
                return jsonify({
                    'success': True,
                    'data': stats
                })
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_stats] 统计请求失败: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/files')
        def get_files():
            """Get all files."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_files] 收到文件列表请求")
            try:
                files = self.repository.get_all_files()
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_files] 返回 %d 个文件", len(files))
                return jsonify({
                    'success': True,
                    'data': files
                })
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_files] 文件列表请求失败: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/classes')
        def get_classes():
            """Get all classes."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_classes] 收到类列表请求")
            try:
                classes = self.repository.get_all_classes()
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_classes] 返回 %d 个类", len(classes))
                return jsonify({
                    'success': True,
                    'data': classes
                })
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_classes] 类列表请求失败: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/components')
        def get_components():
            """Get all components."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_components] 收到组件列表请求")
            try:
                components = self.repository.get_components()
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_components] 返回 %d 个组件", len(components))
                return jsonify({
                    'success': True,
                    'data': components
                })
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_components] 组件列表请求失败: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/classes/<class_id>/methods')
        def get_class_methods(class_id):
            """Get methods for a class."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_class_methods] 收到类方法请求: class_id=%s", class_id)
            try:
                methods = self.repository.get_methods_by_class(class_id)
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_class_methods] 返回 %d 个方法", len(methods))
                return jsonify({
                    'success': True,
                    'data': methods
                })
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_class_methods] 类方法请求失败: class_id=%s, 错误: %s", class_id, e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/classes/<class_id>/children')
        def get_component_children(class_id):
            """Get child components."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_component_children] 收到子组件请求: class_id=%s", class_id)
            try:
                children = self.repository.get_child_components(class_id)
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_component_children] 返回 %d 个子组件", len(children))
                return jsonify({
                    'success': True,
                    'data': children
                })
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_component_children] 子组件请求失败: class_id=%s, 错误: %s", class_id, e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/graph')
        def get_graph_data():
            """Get knowledge graph data for visualization."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_graph_data] 收到图谱数据请求")
            try:
                # Get all entities
                files = self.repository.get_all_files()
                classes = self.repository.get_all_classes()
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_graph_data] 获取到 %d 个文件, %d 个类", len(files), len(classes))
                
                # Build nodes
                nodes = []
                edges = []
                
                # Add file nodes
                for file in files:
                    nodes.append({
                        'id': file['id'],
                        'label': file['name'],
                        'type': 'file',
                        'path': file['relative_path']
                    })
                
                # Add class nodes and file-class edges
                for cls in classes:
                    node_type = 'component' if cls['is_component'] else 'class'
                    if cls['is_entry']:
                        node_type = 'entry'
                    
                    nodes.append({
                        'id': cls['id'],
                        'label': cls['name'],
                        'type': node_type,
                        'is_component': cls['is_component'],
                        'is_entry': cls['is_entry']
                    })
                    
                    # Edge from file to class
                    edges.append({
                        'from': cls['file_id'],
                        'to': cls['id'],
                        'label': 'contains'
                    })
                
                # Add inheritance edges
                inheritance = self.repository.execute_sql(
                    'SELECT child_class_id, parent_class_id, parent_name, relation_type FROM inheritance'
                )
                for inh in inheritance.get('results', []):
                    if inh['parent_class_id']:
                        edges.append({
                            'from': inh['child_class_id'],
                            'to': inh['parent_class_id'],
                            'label': inh['relation_type'],
                            'type': 'inheritance'
                        })
                
                # Add component nesting edges
                components = self.repository.execute_sql(
                    'SELECT parent_class_id, child_class_id, child_name FROM components'
                )
                for comp in components.get('results', []):
                    edges.append({
                        'from': comp['parent_class_id'],
                        'to': comp['child_class_id'] if comp['child_class_id'] else comp['child_name'],
                        'label': 'uses',
                        'type': 'component'
                    })
                
                # Add method call edges (limit to avoid clutter)
                calls = self.repository.execute_sql(
                    'SELECT caller_class_id, callee_class_id, callee_name FROM calls '
                    'GROUP BY caller_class_id, callee_class_id'
                )
                for call in calls.get('results', []):
                    if call['callee_class_id']:
                        edges.append({
                            'from': call['caller_class_id'],
                            'to': call['callee_class_id'],
                            'label': 'calls',
                            'type': 'call'
                        })
                
                return jsonify({
                    'success': True,
                    'data': {
                        'nodes': nodes,
                        'edges': edges
                    }
                })
                logger.debug("[DEBUG] [KnowledgeGraphServer] [get_graph_data] 返回图谱数据: %d 个节点, %d 条边", len(nodes), len(edges))
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_graph_data] 图谱数据请求失败: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/query', methods=['POST'])
        def query():
            """Execute natural language query."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [query] 收到自然语言查询请求")
            if not self.query_engine:
                logger.warn("[DEBUG] [KnowledgeGraphServer] [query] LLM未配置, 返回503")
                return jsonify({
                    'success': False,
                    'error': 'LLM not configured'
                }), 503
            
            try:
                data = request.get_json()
                if data is None:
                    logger.debug("[DEBUG] [KnowledgeGraphServer] [query] 请求体非JSON")
                    return jsonify({
                        'success': False,
                        'error': 'Request must be JSON with Content-Type application/json'
                    }), 400

                question = data.get('question', '')

                if not question or not isinstance(question, str):
                    logger.debug("[DEBUG] [KnowledgeGraphServer] [query] 问题参数无效")
                    return jsonify({
                        'success': False,
                        'error': 'Question is required and must be a non-empty string'
                    }), 400

                if len(question) > 2000:
                    logger.debug("[DEBUG] [KnowledgeGraphServer] [query] 问题过长: %d 字符", len(question))
                    return jsonify({
                        'success': False,
                        'error': 'Question is too long (maximum 2000 characters)'
                    }), 400
                
                logger.debug("[DEBUG] [KnowledgeGraphServer] [query] 执行查询: %s", question[:100])
                result = self.query_engine.ask(
                    question,
                    self.repository.execute_sql
                )
                
                logger.debug("[DEBUG] [KnowledgeGraphServer] [query] 查询完成, success=%s", result.get('success'))
                return jsonify(result)
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [query] 查询失败: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/schema')
        def get_schema():
            """Get database schema."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_schema] 收到schema请求")
            try:
                schema = self.repository.get_schema_info()
                return jsonify({
                    'success': True,
                    'data': schema
                })
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [get_schema] schema请求失败: %s", e)
                return jsonify({
                    'success': False,
                    'error': str(e)
                }), 500
        
        @self.app.route('/api/config')
        def get_config():
            """Get current configuration (safe values only)."""
            logger.debug("[DEBUG] [KnowledgeGraphServer] [get_config] 收到配置请求")
            return jsonify({
                'success': True,
                'data': {
                    'project_path': config.ark_analyzer.target_project_path,
                    'llm_configured': bool(config.llm.api_key),
                    'llm_model': config.llm.model if config.llm.api_key else None
                }
            })
    
    def _setup_socket_events(self) -> None:
        """Setup WebSocket events for real-time updates."""
        
        @self.socketio.on('connect')
        def handle_connect():
            """Handle client connection."""
            try:
                logger.debug("[DEBUG] [KnowledgeGraphServer] [handle_connect] WebSocket客户端已连接")
                emit('connected', {'data': 'Connected to ArkTS Knowledge Graph'})
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [handle_connect] WebSocket连接处理异常: %s", e)
                print(f"Error in WebSocket connect handler: {e}")

        @self.socketio.on('disconnect')
        def handle_disconnect():
            """Handle client disconnection."""
            try:
                logger.debug("[DEBUG] [KnowledgeGraphServer] [handle_disconnect] WebSocket客户端已断开")
                pass
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [handle_disconnect] WebSocket断开处理异常: %s", e)
                print(f"Error in WebSocket disconnect handler: {e}")

        @self.socketio.on('subscribe_updates')
        def handle_subscribe():
            """Subscribe to file change updates."""
            try:
                logger.debug("[DEBUG] [KnowledgeGraphServer] [handle_subscribe] 客户端订阅文件更新")
                emit('subscribed', {'data': 'Subscribed to file updates'})
            except Exception as e:
                logger.error("[DEBUG] [KnowledgeGraphServer] [handle_subscribe] 订阅处理异常: %s", e)
                print(f"Error in WebSocket subscribe_updates handler: {e}")
    
    def _on_file_change(self, event: FileChangeEvent) -> None:
        """Handle file change events."""
        logger.debug("[DEBUG] [KnowledgeGraphServer] [_on_file_change] 广播文件变更: type=%s, path=%s", event.event_type, event.file_path)
        # Broadcast to all connected clients
        self.socketio.emit('file_changed', {
            'event_type': event.event_type,
            'file_path': event.file_path,
            'timestamp': event.timestamp.isoformat()
        })
    
    def start_file_watcher(self) -> None:
        """Start the file watcher if project path is configured."""
        if not config.ark_analyzer.target_project_path:
            logger.debug("[DEBUG] [KnowledgeGraphServer] [start_file_watcher] 未配置项目路径, 文件监视器未启动")
            print("No project path configured, file watcher not started")
            return
        
        self.file_watcher = FileWatcher(
            project_path=config.ark_analyzer.target_project_path,
            patterns=config.file_watcher.patterns,
            debounce_seconds=config.file_watcher.delay_seconds
        )
        self.file_watcher.add_change_callback(self._on_file_change)
        self.file_watcher.start()
        logger.debug("[DEBUG] [KnowledgeGraphServer] [start_file_watcher] 文件监视器已启动")
    
    def stop_file_watcher(self) -> None:
        """Stop the file watcher."""
        if self.file_watcher:
            logger.debug("[DEBUG] [KnowledgeGraphServer] [stop_file_watcher] 停止文件监视器")
            self.file_watcher.stop()
    
    def run(self, host: str = None, port: int = None, debug: bool = None) -> None:
        """
        Run the server.
        
        Args:
            host: Host to bind to (default from config)
            port: Port to bind to (default from config)
            debug: Debug mode (default from config)
        """
        host = host or config.web_server.host
        port = port or config.web_server.port
        debug = debug if debug is not None else config.web_server.debug
        
        # Start file watcher
        self.start_file_watcher()
        
        try:
            logger.debug("[DEBUG] [KnowledgeGraphServer] [run] 启动服务器: %s:%d, debug=%s", host, port, debug)
            print(f"Starting server on {host}:{port}")
            self.socketio.run(
                self.app,
                host=host,
                port=port,
                debug=debug,
                use_reloader=False,  # Disable reloader to prevent double startup
                allow_unsafe_werkzeug=True  # Allow Werkzeug for development/testing
            )
        finally:
            logger.debug("[DEBUG] [KnowledgeGraphServer] [run] 服务器关闭, 停止文件监视器")
            self.stop_file_watcher()


# Create global server instance
server = KnowledgeGraphServer()

if __name__ == '__main__':
    # Validate configuration
    errors = config.validate()
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        print("\nPlease check your .env file or environment variables.")
        sys.exit(1)
    
    server.run()
