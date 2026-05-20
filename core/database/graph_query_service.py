"""
知识图谱查询器
提供高层API查询知识图谱数据
"""
import logging
from typing import List, Dict, Any, Optional
from core.database.connection_manager import get_connection_manager

logger = logging.getLogger(__name__)


class GraphQueryService:
    """知识图谱查询服务 - 提供丰富的图查询API"""

    def __init__(self):
        self._conn_mgr = get_connection_manager()

    # ==================== 基础统计 ====================

    def get_overview_stats(self) -> Dict[str, Any]:
        """获取项目总览统计"""
        stats = self._conn_mgr.execute_query("""
            SELECT
                (SELECT COUNT(*) FROM files) as file_count,
                (SELECT COUNT(*) FROM classes) as class_count,
                (SELECT COUNT(*) FROM methods) as method_count,
                (SELECT COUNT(*) FROM properties) as property_count,
                (SELECT COUNT(*) FROM calls) as call_count,
                (SELECT COUNT(*) FROM imports) as import_count,
                (SELECT COUNT(*) FROM decorators) as decorator_count,
                (SELECT COUNT(*) FROM components) as component_count,
                (SELECT COUNT(*) FROM inheritance) as inheritance_count
        """)
        result = dict(stats[0]) if stats else {}
        result["database_size_mb"] = round(self._conn_mgr.get_database_size_mb(), 2)

        # 获取构建时间
        build_info = self._conn_mgr.execute_query(
            "SELECT * FROM build_metadata WHERE key IN ('last_build_time', 'schema_version')"
        )
        for row in build_info:
            result[row["key"]] = row["value"]

        return result

    # ==================== 类查询 ====================

    def get_all_classes(self, limit: int = 500, offset: int = 0) -> List[Dict]:
        """获取所有类"""
        return self._conn_mgr.execute_query("""
            SELECT c.*, f.path as file_path
            FROM classes c
            JOIN files f ON c.file_id = f.id
            ORDER BY c.name
            LIMIT ? OFFSET ?
        """, (limit, offset))

    def get_class_by_id(self, class_id: int) -> Optional[Dict]:
        """根据ID获取类详情"""
        results = self._conn_mgr.execute_query("""
            SELECT c.*, f.path as file_path
            FROM classes c
            JOIN files f ON c.file_id = f.id
            WHERE c.id = ?
        """, (class_id,))
        return results[0] if results else None

    def get_class_by_name(self, name: str) -> List[Dict]:
        """根据名称模糊搜索类"""
        return self._conn_mgr.execute_query("""
            SELECT c.*, f.path as file_path
            FROM classes c
            JOIN files f ON c.file_id = f.id
            WHERE c.name LIKE ?
            ORDER BY c.name
        """, (f"%{name}%",))

    def get_class_methods(self, class_id: int) -> List[Dict]:
        """获取类的所有方法"""
        return self._conn_mgr.execute_query("""
            SELECT m.*, f.path as file_path
            FROM methods m
            JOIN files f ON m.file_id = f.id
            WHERE m.class_id = ?
            ORDER BY m.start_line
        """, (class_id,))

    def get_class_properties(self, class_id: int) -> List[Dict]:
        """获取类的所有属性"""
        return self._conn_mgr.execute_query("""
            SELECT p.*, f.path as file_path
            FROM properties p
            JOIN files f ON p.file_id = f.id
            WHERE p.class_id = ?
            ORDER BY p.start_line
        """, (class_id,))

    def get_class_children(self, class_id: int) -> List[Dict]:
        """获取继承此类的子类"""
        return self._conn_mgr.execute_query("""
            SELECT c.*, f.path as file_path
            FROM classes c
            JOIN files f ON c.file_id = f.id
            JOIN inheritance i ON i.child_id = c.id
            WHERE i.parent_id = ?
        """, (class_id,))

    def get_class_parents(self, class_id: int) -> List[Dict]:
        """获取此类继承的父类"""
        return self._conn_mgr.execute_query("""
            SELECT c.*, f.path as file_path
            FROM classes c
            JOIN files f ON c.file_id = f.id
            JOIN inheritance i ON i.parent_id = c.id
            WHERE i.child_id = ?
        """, (class_id,))

    # ==================== 方法查询 ====================

    def get_method_by_id(self, method_id: int) -> Optional[Dict]:
        """根据ID获取方法详情"""
        results = self._conn_mgr.execute_query("""
            SELECT m.*, f.path as file_path,
                   c.name as class_name
            FROM methods m
            JOIN files f ON m.file_id = f.id
            LEFT JOIN classes c ON m.class_id = c.id
            WHERE m.id = ?
        """, (method_id,))
        return results[0] if results else None

    def get_method_callers(self, method_id: int) -> List[Dict]:
        """获取调用此方法的所有方法"""
        return self._conn_mgr.execute_query("""
            SELECT m.*, f.path as file_path, c.name as class_name
            FROM methods m
            JOIN files f ON m.file_id = f.id
            LEFT JOIN classes c ON m.class_id = c.id
            JOIN calls ca ON ca.callee_id = m.id
            WHERE ca.caller_id = ?
        """, (method_id,))

    def get_method_callees(self, method_id: int) -> List[Dict]:
        """获取此方法调用的所有方法"""
        return self._conn_mgr.execute_query("""
            SELECT m.*, f.path as file_path, c.name as class_name
            FROM methods m
            JOIN files f ON m.file_id = f.id
            LEFT JOIN classes c ON m.class_id = c.id
            JOIN calls ca ON ca.caller_id = m.id
            WHERE ca.callee_id = ?
        """, (method_id,))

    # ==================== 调用图查询 ====================

    def get_call_graph(self, class_id: int, depth: int = 1) -> Dict[str, Any]:
        """获取类的调用图（BFS遍历）"""
        methods = self.get_class_methods(class_id)
        nodes = []
        edges = []
        visited_method_ids = set()

        for method in methods:
            nodes.append({
                "id": method["id"],
                "name": method["name"],
                "type": "method",
                "class_name": method.get("class_name", ""),
            })
            visited_method_ids.add(method["id"])

            # 获取调用关系
            callees = self.get_method_callees(method["id"])
            for callee in callees:
                edges.append({
                    "source": method["id"],
                    "target": callee["id"],
                    "type": "calls"
                })
                if callee["id"] not in visited_method_ids:
                    nodes.append({
                        "id": callee["id"],
                        "name": callee["name"],
                        "type": "method",
                        "class_name": callee.get("class_name", ""),
                    })
                    visited_method_ids.add(callee["id"])

        return {"nodes": nodes, "edges": edges}

    def get_full_graph_data(self, limit: int = 2000) -> Dict[str, Any]:
        """获取完整的知识图谱数据（用于可视化）"""
        # 节点
        class_nodes = self._conn_mgr.execute_query("""
            SELECT id, name, 'class' as node_type, file_id FROM classes LIMIT ?
        """, (limit,))

        method_nodes = self._conn_mgr.execute_query("""
            SELECT id, name, 'method' as node_type, class_id, file_id FROM methods LIMIT ?
        """, (limit,))

        # 边
        call_edges = self._conn_mgr.execute_query("""
            SELECT caller_id as source, callee_id as target, 'calls' as edge_type
            FROM calls LIMIT ?
        """, (limit * 2,))

        inherit_edges = self._conn_mgr.execute_query("""
            SELECT child_id as source, parent_id as target, 'extends' as edge_type
            FROM inheritance LIMIT ?
        """, (limit,))

        component_edges = self._conn_mgr.execute_query("""
            SELECT parent_id as source, child_id as target, 'component' as edge_type
            FROM components LIMIT ?
        """, (limit,))

        import_edges = self._conn_mgr.execute_query("""
            SELECT source_file_id as source, target_file_id as target, 'imports' as edge_type
            FROM imports LIMIT ?
        """, (limit,))

        nodes = []
        for c in class_nodes:
            nodes.append({"id": c["id"], "name": c["name"], "type": "class"})
        for m in method_nodes:
            nodes.append({"id": m["id"], "name": m["name"], "type": "method", "classId": m.get("class_id")})

        edges = []
        for e in call_edges:
            edges.append({"source": e["source"], "target": e["target"], "type": "calls"})
        for e in inherit_edges:
            edges.append({"source": e["source"], "target": e["target"], "type": "extends"})
        for e in component_edges:
            edges.append({"source": e["source"], "target": e["target"], "type": "component"})
        for e in import_edges:
            edges.append({"source": e["source"], "target": e["target"], "type": "imports"})

        return {"nodes": nodes, "edges": edges}

    # ==================== 文件查询 ====================

    def get_all_files(self, limit: int = 500) -> List[Dict]:
        """获取所有文件"""
        files = self._conn_mgr.execute_query(
            "SELECT id, path, line_count, language, last_scanned FROM files ORDER BY path LIMIT ?", (limit,)
        )
        return files

    def get_file_by_path(self, path: str) -> Optional[Dict]:
        """根据路径获取文件"""
        results = self._conn_mgr.execute_query(
            "SELECT * FROM files WHERE path = ?", (path,)
        )
        return results[0] if results else None

    def get_file_classes(self, file_id: int) -> List[Dict]:
        """获取文件中的所有类"""
        return self._conn_mgr.execute_query(
            "SELECT * FROM classes WHERE file_id = ? ORDER BY start_line", (file_id,)
        )

    def get_file_imports(self, file_id: int) -> List[Dict]:
        """获取文件的所有导入"""
        return self._conn_mgr.execute_query("""
            SELECT i.*, f.path as target_path
            FROM imports i
            JOIN files f ON i.target_file_id = f.id
            WHERE i.source_file_id = ?
        """, (file_id,))

    # ==================== 组件查询 ====================

    def get_component_tree(self) -> List[Dict]:
        """获取组件层级树"""
        return self._conn_mgr.execute_query("""
            SELECT c1.name as parent_name, c2.name as child_name,
                   f1.path as parent_file, f2.path as child_file
            FROM components comp
            JOIN classes c1 ON comp.parent_id = c1.id
            JOIN classes c2 ON comp.child_id = c2.id
            JOIN files f1 ON c1.file_id = f1.id
            JOIN files f2 ON c2.file_id = f2.id
        """)

    # ==================== 装饰器查询 ====================

    def get_decorators_by_target(self, target_id: int) -> List[Dict]:
        """获取目标的所有装饰器"""
        return self._conn_mgr.execute_query(
            "SELECT * FROM decorators WHERE target_id = ?", (target_id,)
        )

    def get_entry_components(self) -> List[Dict]:
        """获取 @Entry 装饰的组件"""
        return self._conn_mgr.execute_query("""
            SELECT c.*, f.path as file_path
            FROM classes c
            JOIN files f ON c.file_id = f.id
            JOIN decorators d ON d.target_id = c.id
            WHERE d.name = 'Entry' AND d.target_type = 0
        """)

    # ==================== 搜索 ====================

    def search_symbols(self, keyword: str, limit: int = 50) -> Dict[str, List[Dict]]:
        """全局符号搜索"""
        pattern = f"%{keyword}%"
        return {
            "classes": self._conn_mgr.execute_query(
                "SELECT * FROM classes WHERE name LIKE ? LIMIT ?", (pattern, limit)
            ),
            "methods": self._conn_mgr.execute_query(
                "SELECT * FROM methods WHERE name LIKE ? LIMIT ?", (pattern, limit)
            ),
            "properties": self._conn_mgr.execute_query(
                "SELECT * FROM properties WHERE name LIKE ? LIMIT ?", (pattern, limit)
            ),
            "files": self._conn_mgr.execute_query(
                "SELECT * FROM files WHERE path LIKE ? LIMIT ?", (pattern, limit)
            ),
        }

    # ==================== 原始SQL执行 ====================

    def execute_raw_sql(self, sql: str) -> List[Dict]:
        """执行原始SQL查询（只允许SELECT）"""
        sql_stripped = sql.strip().upper()
        if not sql_stripped.startswith("SELECT"):
            raise ValueError("只允许执行 SELECT 查询")
        return self._conn_mgr.execute_query(sql)
