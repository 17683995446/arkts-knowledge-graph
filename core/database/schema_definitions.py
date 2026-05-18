"""
数据库 Schema 定义模块
定义所有表结构、索引和约束
"""
import sqlite3


def get_schema_ddl() -> list:
    """
    返回完整的数据库建表DDL语句列表
    所有表使用 INTEGER 主键（数字比文字小10倍，快10倍）
    """
    return [
        # ==================== 文件表 ====================
        # 存储项目中的所有源代码文件
        """CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            path TEXT UNIQUE NOT NULL,
            hash BLOB NOT NULL,
            line_count INTEGER DEFAULT 0,
            language TEXT DEFAULT 'arkts',
            last_scanned REAL DEFAULT 0
        )""",

        # ==================== 类/接口/结构体表 ====================
        # 存储所有类型定义
        """CREATE TABLE IF NOT EXISTS classes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            start_line INTEGER DEFAULT 0,
            end_line INTEGER DEFAULT 0,
            flags INTEGER DEFAULT 0,
            parent_class_id INTEGER,
            doc_comment TEXT DEFAULT '',
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        )""",

        # ==================== 方法/函数表 ====================
        # 存储所有方法、函数、构造函数
        """CREATE TABLE IF NOT EXISTS methods (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_id INTEGER,
            file_id INTEGER NOT NULL,
            start_line INTEGER DEFAULT 0,
            end_line INTEGER DEFAULT 0,
            flags INTEGER DEFAULT 0,
            return_type TEXT DEFAULT '',
            parameters TEXT DEFAULT '',
            doc_comment TEXT DEFAULT '',
            body_hash BLOB,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        )""",

        # ==================== 属性/字段表 ====================
        # 存储类属性和全局变量
        """CREATE TABLE IF NOT EXISTS properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            class_id INTEGER,
            file_id INTEGER NOT NULL,
            type_annotation TEXT DEFAULT '',
            flags INTEGER DEFAULT 0,
            default_value TEXT DEFAULT '',
            start_line INTEGER DEFAULT 0,
            FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE SET NULL,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        )""",

        # ==================== 调用关系表 ====================
        # 只存两个数字编号（最小存储开销）
        """CREATE TABLE IF NOT EXISTS calls (
            caller_id INTEGER NOT NULL,
            callee_id INTEGER NOT NULL,
            call_type INTEGER DEFAULT 0,
            line_number INTEGER DEFAULT 0,
            PRIMARY KEY (caller_id, callee_id)
        )""",

        # ==================== 组件层级关系表 ====================
        # UI组件树（ArkUI @Component装饰器）
        """CREATE TABLE IF NOT EXISTS components (
            parent_id INTEGER NOT NULL,
            child_id INTEGER NOT NULL,
            relation_type INTEGER DEFAULT 0,
            PRIMARY KEY (parent_id, child_id)
        )""",

        # ==================== 导入关系表 ====================
        """CREATE TABLE IF NOT EXISTS imports (
            source_file_id INTEGER NOT NULL,
            target_file_id INTEGER NOT NULL,
            import_path TEXT DEFAULT '',
            is_default INTEGER DEFAULT 0,
            PRIMARY KEY (source_file_id, target_file_id)
        )""",

        # ==================== 装饰器表 ====================
        """CREATE TABLE IF NOT EXISTS decorators (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            target_type INTEGER DEFAULT 0,
            target_id INTEGER NOT NULL,
            arguments TEXT DEFAULT ''
        )""",

        # ==================== 继承关系表 ====================
        """CREATE TABLE IF NOT EXISTS inheritance (
            child_id INTEGER NOT NULL,
            parent_id INTEGER NOT NULL,
            type INTEGER DEFAULT 0,
            PRIMARY KEY (child_id, parent_id)
        )""",

        # ==================== 命名空间/模块表 ====================
        """CREATE TABLE IF NOT EXISTS namespaces (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            file_id INTEGER NOT NULL,
            start_line INTEGER DEFAULT 0,
            end_line INTEGER DEFAULT 0,
            FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
        )""",

        # ==================== 构建元数据表 ====================
        """CREATE TABLE IF NOT EXISTS build_metadata (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at REAL DEFAULT 0
        )""",
    ]


def get_index_ddl() -> list:
    """返回所有索引的DDL语句"""
    return [
        "CREATE INDEX IF NOT EXISTS idx_classes_file ON classes(file_id)",
        "CREATE INDEX IF NOT EXISTS idx_classes_name ON classes(name)",
        "CREATE INDEX IF NOT EXISTS idx_methods_class ON methods(class_id)",
        "CREATE INDEX IF NOT EXISTS idx_methods_file ON methods(file_id)",
        "CREATE INDEX IF NOT EXISTS idx_methods_name ON methods(name)",
        "CREATE INDEX IF NOT EXISTS idx_properties_class ON properties(class_id)",
        "CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_id)",
        "CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_id)",
        "CREATE INDEX IF NOT EXISTS idx_components_parent ON components(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_components_child ON components(child_id)",
        "CREATE INDEX IF NOT EXISTS idx_imports_source ON imports(source_file_id)",
        "CREATE INDEX IF NOT EXISTS idx_imports_target ON imports(target_file_id)",
        "CREATE INDEX IF NOT EXISTS idx_decorators_target ON decorators(target_id)",
        "CREATE INDEX IF NOT EXISTS idx_inheritance_child ON inheritance(child_id)",
        "CREATE INDEX IF NOT EXISTS idx_inheritance_parent ON inheritance(parent_id)",
        "CREATE INDEX IF NOT EXISTS idx_namespaces_file ON namespaces(file_id)",
        "CREATE INDEX IF NOT EXISTS idx_files_hash ON files(hash)",
        "CREATE INDEX IF NOT EXISTS idx_files_path ON files(path)",
    ]


def get_flag_constants() -> dict:
    """
    返回 flags 字段的位掩码常量
    用一个整数存储多个布尔属性（极致空间优化）
    """
    return {
        # 类/接口标志
        "CLASS_IS_INTERFACE": 1 << 0,
        "CLASS_IS_ABSTRACT": 1 << 1,
        "CLASS_IS_ENUM": 1 << 2,
        "CLASS_IS_STRUCT": 1 << 3,
        "CLASS_IS_GENERIC": 1 << 4,
        "CLASS_IS_EXPORTED": 1 << 5,
        "CLASS_IS_ENTRY": 1 << 6,

        # 方法标志
        "METHOD_IS_STATIC": 1 << 0,
        "METHOD_IS_ASYNC": 1 << 1,
        "METHOD_IS_PRIVATE": 1 << 2,
        "METHOD_IS_PROTECTED": 1 << 3,
        "METHOD_IS_OVERRIDE": 1 << 4,
        "METHOD_IS_GETTER": 1 << 5,
        "METHOD_IS_SETTER": 1 << 6,
        "METHOD_IS_CONSTRUCTOR": 1 << 7,
        "METHOD_IS_LIFECYCLE": 1 << 8,

        # 属性标志
        "PROP_IS_STATIC": 1 << 0,
        "PROP_IS_PRIVATE": 1 << 1,
        "PROP_IS_READONLY": 1 << 2,
        "PROP_IS_STATE": 1 << 3,
        "PROP_IS_LINK": 1 << 4,
        "PROP_IS_PROP": 1 << 5,
        "PROP_IS_PROVIDE": 1 << 6,

        # 调用类型
        "CALL_DIRECT": 0,
        "CALL_METHOD": 1,
        "CALL_CALLBACK": 2,
        "CALL_EVENT": 3,
        "CALL_CHAIN": 4,

        # 组件关系类型
        "COMP_CHILD": 0,
        "COMP_NESTED": 1,
        "COMP_BUILDER": 2,

        # 继承类型
        "INHERIT_EXTENDS": 0,
        "INHERIT_IMPLEMENTS": 1,

        # 装饰器目标类型
        "DEC_CLASS": 0,
        "DEC_METHOD": 1,
        "DEC_PROPERTY": 2,
    }
