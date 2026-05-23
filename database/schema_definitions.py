"""
Database Schema Definitions Module

Defines the SQLite database schema for storing the knowledge graph.
Follows the minimization principle: only store necessary structural information.
"""

# SQL statements for creating tables
CREATE_TABLES_SQL = """
-- Entity Tables

-- Files table: stores source file information
CREATE TABLE IF NOT EXISTS files (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    absolute_path TEXT NOT NULL,
    line_count INTEGER DEFAULT 0,
    last_modified TIMESTAMP,
    file_hash TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Classes table: stores class and component definitions
CREATE TABLE IF NOT EXISTS classes (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    file_id TEXT NOT NULL,
    is_component BOOLEAN DEFAULT 0,
    is_entry BOOLEAN DEFAULT 0,
    is_exported BOOLEAN DEFAULT 0,
    decorators TEXT,  -- JSON array of decorator names
    parent_class TEXT,
    implemented_interfaces TEXT,  -- JSON array
    metadata TEXT,  -- JSON object for additional info (kind, etc.)
    line_number INTEGER,
    column_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Methods table: stores method and function definitions
CREATE TABLE IF NOT EXISTS methods (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    class_id TEXT NOT NULL,
    is_static BOOLEAN DEFAULT 0,
    is_async BOOLEAN DEFAULT 0,
    is_private BOOLEAN DEFAULT 0,
    is_protected BOOLEAN DEFAULT 0,
    is_public BOOLEAN DEFAULT 1,
    return_type TEXT DEFAULT 'void',
    parameters TEXT,  -- JSON array of parameter objects
    line_number INTEGER,
    column_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- Properties table: stores property and field definitions
CREATE TABLE IF NOT EXISTS properties (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    class_id TEXT NOT NULL,
    property_type TEXT,
    is_static BOOLEAN DEFAULT 0,
    is_readonly BOOLEAN DEFAULT 0,
    is_optional BOOLEAN DEFAULT 0,
    default_value TEXT,
    metadata TEXT,  -- JSON object for decorator info
    line_number INTEGER,
    column_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- Relation Tables

-- Calls table: stores method call relationships
CREATE TABLE IF NOT EXISTS calls (
    id TEXT PRIMARY KEY,
    caller_method_id TEXT NOT NULL,
    caller_class_id TEXT NOT NULL,
    callee_method_id TEXT,
    callee_class_id TEXT,
    callee_name TEXT,  -- For external/unresolved calls
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (caller_method_id) REFERENCES methods(id) ON DELETE CASCADE,
    FOREIGN KEY (caller_class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (callee_method_id) REFERENCES methods(id) ON DELETE CASCADE,
    FOREIGN KEY (callee_class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- Components table: stores component nesting relationships
CREATE TABLE IF NOT EXISTS components (
    id TEXT PRIMARY KEY,
    parent_class_id TEXT NOT NULL,
    child_class_id TEXT,
    child_name TEXT,  -- For unresolved component references
    build_method_id TEXT,
    line_number INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (parent_class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (child_class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (build_method_id) REFERENCES methods(id) ON DELETE CASCADE
);

-- Inheritance table: stores class inheritance relationships
CREATE TABLE IF NOT EXISTS inheritance (
    id TEXT PRIMARY KEY,
    child_class_id TEXT NOT NULL,
    parent_class_id TEXT,
    parent_name TEXT,  -- For external/unresolved parents
    relation_type TEXT DEFAULT 'extends',  -- 'extends' or 'implements'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (child_class_id) REFERENCES classes(id) ON DELETE CASCADE,
    FOREIGN KEY (parent_class_id) REFERENCES classes(id) ON DELETE CASCADE
);

-- Imports table: stores file import relationships
CREATE TABLE IF NOT EXISTS imports (
    id TEXT PRIMARY KEY,
    source_file_id TEXT NOT NULL,
    target_file_id TEXT,
    import_path TEXT NOT NULL,
    is_default_import BOOLEAN DEFAULT 0,
    imported_names TEXT,  -- JSON array for named imports
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (source_file_id) REFERENCES files(id) ON DELETE CASCADE,
    FOREIGN KEY (target_file_id) REFERENCES files(id) ON DELETE CASCADE
);

-- Metadata table: stores system metadata
CREATE TABLE IF NOT EXISTS metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_classes_file_id ON classes(file_id);
CREATE INDEX IF NOT EXISTS idx_methods_class_id ON methods(class_id);
CREATE INDEX IF NOT EXISTS idx_properties_class_id ON properties(class_id);
CREATE INDEX IF NOT EXISTS idx_calls_caller ON calls(caller_method_id);
CREATE INDEX IF NOT EXISTS idx_calls_callee ON calls(callee_method_id);
CREATE INDEX IF NOT EXISTS idx_components_parent ON components(parent_class_id);
CREATE INDEX IF NOT EXISTS idx_inheritance_child ON inheritance(child_class_id);
CREATE INDEX IF NOT EXISTS idx_imports_source ON imports(source_file_id);
"""

# SQL for clearing all data (for rebuild)
CLEAR_ALL_DATA_SQL = """
DELETE FROM imports;
DELETE FROM inheritance;
DELETE FROM components;
DELETE FROM calls;
DELETE FROM properties;
DELETE FROM methods;
DELETE FROM classes;
DELETE FROM files;
DELETE FROM metadata;
"""

# SQL for getting statistics
GET_STATISTICS_SQL = """
SELECT 
    (SELECT COUNT(*) FROM files) as file_count,
    (SELECT COUNT(*) FROM classes) as class_count,
    (SELECT COUNT(*) FROM methods) as method_count,
    (SELECT COUNT(*) FROM properties) as property_count,
    (SELECT COUNT(*) FROM calls) as call_count,
    (SELECT COUNT(*) FROM components) as component_count,
    (SELECT COUNT(*) FROM inheritance) as inheritance_count,
    (SELECT COUNT(*) FROM imports) as import_count,
    (SELECT COUNT(*) FROM classes WHERE is_component = 1) as component_class_count,
    (SELECT COUNT(*) FROM classes WHERE is_entry = 1) as entry_class_count;
"""

# SQL for finding orphaned records (for validation)
FIND_ORPHANS_SQL = """
-- Methods without valid class
SELECT 'method' as type, id, name, class_id as parent_id 
FROM methods 
WHERE class_id NOT IN (SELECT id FROM classes);

-- Properties without valid class
SELECT 'property' as type, id, name, class_id as parent_id 
FROM properties 
WHERE class_id NOT IN (SELECT id FROM classes);

-- Classes without valid file
SELECT 'class' as type, id, name, file_id as parent_id 
FROM classes 
WHERE file_id NOT IN (SELECT id FROM files);

-- Calls without valid caller
SELECT 'call' as type, id, caller_method_id as name, caller_method_id as parent_id 
FROM calls 
WHERE caller_method_id NOT IN (SELECT id FROM methods);
"""
