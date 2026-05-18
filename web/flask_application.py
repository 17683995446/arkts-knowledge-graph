"""
Flask Web 服务器
提供REST API和静态页面服务
"""
import logging
import traceback
from flask import Flask, jsonify, request, send_from_directory, render_template
from flask_cors import CORS

from config.global_settings import WEB_HOST, WEB_PORT, WEB_DEBUG, PROJECT_ROOT
from core.database.database_initializer import DatabaseInitializer
from core.database.graph_query_service import GraphQueryService
from core.query.natural_language_engine import NaturalLanguageQueryEngine

logger = logging.getLogger(__name__)


def create_app() -> Flask:
    """创建Flask应用"""
    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
        static_url_path="/static",
    )
    CORS(app)

    # 确保数据库已初始化
    db_init = DatabaseInitializer()
    if not db_init.is_database_ready():
        db_init.initialize_database()

    query_service = GraphQueryService()
    nl_engine = NaturalLanguageQueryEngine()

    # ==================== 页面路由 ====================

    @app.route("/")
    def index_page():
        """主页"""
        return render_template("index.html")

    @app.route("/graph")
    def graph_page():
        """知识图谱可视化页面"""
        return render_template("graph.html")

    @app.route("/query")
    def query_page():
        """智能查询页面"""
        return render_template("query.html")

    @app.route("/classes")
    def classes_page():
        """类浏览器页面"""
        return render_template("classes.html")

    @app.route("/stats")
    def stats_page():
        """统计页面"""
        return render_template("stats.html")

    # ==================== API 路由 ====================

    @app.route("/api/overview")
    def api_overview():
        """获取项目总览"""
        try:
            stats = query_service.get_overview_stats()
            return jsonify({"success": True, "data": stats})
        except Exception as e:
            logger.error(f"获取总览失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/graph/data")
    def api_graph_data():
        """获取知识图谱数据"""
        try:
            limit = request.args.get("limit", 2000, type=int)
            data = query_service.get_full_graph_data(limit)
            return jsonify({"success": True, "data": data})
        except Exception as e:
            logger.error(f"获取图谱数据失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/classes")
    def api_classes():
        """获取类列表"""
        try:
            limit = request.args.get("limit", 100, type=int)
            offset = request.args.get("offset", 0, type=int)
            search = request.args.get("search", "", type=str)
            if search:
                classes = query_service.get_class_by_name(search)
            else:
                classes = query_service.get_all_classes(limit, offset)
            return jsonify({"success": True, "data": classes})
        except Exception as e:
            logger.error(f"获取类列表失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/classes/<int:class_id>")
    def api_class_detail(class_id):
        """获取类详情"""
        try:
            cls = query_service.get_class_by_id(class_id)
            if not cls:
                return jsonify({"success": False, "error": "类不存在"}), 404

            methods = query_service.get_class_methods(class_id)
            properties = query_service.get_class_properties(class_id)
            parents = query_service.get_class_parents(class_id)
            children = query_service.get_class_children(class_id)
            decorators = query_service.get_decorators_by_target(class_id)

            return jsonify({
                "success": True,
                "data": {
                    "class": cls,
                    "methods": methods,
                    "properties": properties,
                    "parents": parents,
                    "children": children,
                    "decorators": decorators,
                }
            })
        except Exception as e:
            logger.error(f"获取类详情失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/classes/<int:class_id>/callgraph")
    def api_class_callgraph(class_id):
        """获取类的调用图"""
        try:
            data = query_service.get_call_graph(class_id)
            return jsonify({"success": True, "data": data})
        except Exception as e:
            logger.error(f"获取调用图失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/methods/<int:method_id>")
    def api_method_detail(method_id):
        """获取方法详情"""
        try:
            method = query_service.get_method_by_id(method_id)
            if not method:
                return jsonify({"success": False, "error": "方法不存在"}), 404

            callers = query_service.get_method_callers(method_id)
            callees = query_service.get_method_callees(method_id)

            return jsonify({
                "success": True,
                "data": {
                    "method": method,
                    "callers": callers,
                    "callees": callees,
                }
            })
        except Exception as e:
            logger.error(f"获取方法详情失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/files")
    def api_files():
        """获取文件列表"""
        try:
            limit = request.args.get("limit", 100, type=int)
            files = query_service.get_all_files(limit)
            return jsonify({"success": True, "data": files})
        except Exception as e:
            logger.error(f"获取文件列表失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/files/<int:file_id>")
    def api_file_detail(file_id):
        """获取文件详情"""
        try:
            classes = query_service.get_file_classes(file_id)
            imports = query_service.get_file_imports(file_id)
            return jsonify({
                "success": True,
                "data": {"classes": classes, "imports": imports}
            })
        except Exception as e:
            logger.error(f"获取文件详情失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/search")
    def api_search():
        """全局搜索"""
        try:
            keyword = request.args.get("q", "", type=str)
            if not keyword:
                return jsonify({"success": False, "error": "请输入搜索关键词"}), 400
            results = query_service.search_symbols(keyword)
            return jsonify({"success": True, "data": results})
        except Exception as e:
            logger.error(f"搜索失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/entry-components")
    def api_entry_components():
        """获取入口组件"""
        try:
            components = query_service.get_entry_components()
            return jsonify({"success": True, "data": components})
        except Exception as e:
            logger.error(f"获取入口组件失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/component-tree")
    def api_component_tree():
        """获取组件树"""
        try:
            tree = query_service.get_component_tree()
            return jsonify({"success": True, "data": tree})
        except Exception as e:
            logger.error(f"获取组件树失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/query", methods=["POST"])
    def api_natural_query():
        """自然语言查询"""
        try:
            data = request.get_json()
            question = data.get("question", "").strip()
            if not question:
                return jsonify({"success": False, "error": "请输入问题"}), 400

            result = nl_engine.query(question)
            return jsonify({"success": True, "data": result})
        except Exception as e:
            logger.error(f"自然语言查询失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/query/history")
    def api_query_history():
        """获取查询历史"""
        try:
            history = nl_engine.get_history()
            return jsonify({"success": True, "data": history})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/query/clear", methods=["POST"])
    def api_clear_history():
        """清空查询历史"""
        try:
            nl_engine.clear_history()
            return jsonify({"success": True})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/sql", methods=["POST"])
    def api_execute_sql():
        """执行原始SQL"""
        try:
            data = request.get_json()
            sql = data.get("sql", "").strip()
            if not sql:
                return jsonify({"success": False, "error": "请输入SQL"}), 400

            results = query_service.execute_raw_sql(sql)
            return jsonify({"success": True, "data": results})
        except ValueError as e:
            return jsonify({"success": False, "error": str(e)}), 400
        except Exception as e:
            logger.error(f"SQL执行失败: {e}")
            return jsonify({"success": False, "error": str(e)}), 500

    @app.route("/api/database/stats")
    def api_database_stats():
        """获取数据库统计"""
        try:
            db_init = DatabaseInitializer()
            stats = db_init.get_database_stats()
            return jsonify({"success": True, "data": stats})
        except Exception as e:
            return jsonify({"success": False, "error": str(e)}), 500

    # 错误处理
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"success": False, "error": "页面不存在"}), 404

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"success": False, "error": "服务器内部错误"}), 500

    return app


def run_server(host: str = WEB_HOST, port: int = WEB_PORT,
               debug: bool = WEB_DEBUG):
    """启动Web服务器"""
    app = create_app()
    logger.info(f"启动Web服务器: http://{host}:{port}")
    app.run(host=host, port=port, debug=debug, threaded=True)
