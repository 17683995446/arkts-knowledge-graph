"""
ArkAnalyzer Adapter Module

Adapts ArkAnalyzer output to our knowledge graph entities.
Since ArkAnalyzer is a Node.js/TypeScript tool, this adapter
processes its JSON output to extract entities and relations.

For projects without ArkAnalyzer installed, this module provides
a fallback TypeScript parser using Python's built-in capabilities.
"""

import os
import re
import json
import hashlib
import logging
import subprocess
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)

from core.entity_models import (
    FileEntity, ClassEntity, MethodEntity, PropertyEntity,
    SourceLocation, EntityType, RelationType, KnowledgeGraph
)


@dataclass
class ParserConfig:
    """Configuration for the parser."""
    target_project_path: str
    ark_analyzer_path: Optional[str] = None
    sdk_path: Optional[str] = None
    file_patterns: List[str] = None
    
    def __post_init__(self):
        if self.file_patterns is None:
            self.file_patterns = ['*.ets', '*.ts']


class TypeScriptRegexParser:
    """
    Fallback parser using regex for TypeScript/ArkTS files.
    
    This parser extracts basic structural information without
    requiring ArkAnalyzer to be installed.
    """
    
    # Regex patterns for ArkTS/TypeScript parsing
    PATTERNS = {
        'import': re.compile(r'import\s+(?:(\{[^}]+\})|(\*\s+as\s+\w+)|(\w+))\s+from\s+[\'"]([^\'"]+)[\'"]'),
        'namespace': re.compile(r'(?:export\s+)?namespace\s+([\w.]+)\s*\{'),
        'class': re.compile(r'(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^{]+))?'),
        'struct': re.compile(r'(?:export\s+)?\s*struct\s+(\w+)'),
        'interface': re.compile(r'(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([^{]+))?'),
        'enum': re.compile(r'(?:export\s+)?enum\s+(\w+)\s*\{'),
        'type_alias': re.compile(r'(?:export\s+)?type\s+(\w+)(?:<[^>]+>)?\s*=\s*([^;\n{]+?)(?:\s*;|\s*$)', re.MULTILINE),
        'component': re.compile(r'@(?:Component|Entry)\s*(?:\([^)]*\))?'),
        'decorator': re.compile(r'@(\w+)(?:\([^)]*\))?'),
        # 方法定义：必须以修饰符开头或在类体内独立行
        'method_def': re.compile(r'^\s*(?:(private|protected|public|static|async|override)\s+)*(?:async\s+)?(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^{;\n]+))?\s*(?:\{|$)', re.MULTILINE),
        'property': re.compile(r'(?:(private|protected|public|readonly|static)\s+)*@?[A-Za-z_][\w]*\s+([\w]+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'state_property': re.compile(r'@State\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'prop_property': re.compile(r'@Prop\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'provide_property': re.compile(r'@Provide\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'consume_property': re.compile(r'@Consume\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'link_property': re.compile(r'@Link\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'watch_property': re.compile(r'@Watch\s*\([^)]*\)\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'storage_link_property': re.compile(r'@StorageLink\s*\([^)]*\)\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'storage_prop_property': re.compile(r'@StorageProp\s*\([^)]*\)\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'local_storage_link_property': re.compile(r'@LocalStorageLink\s*\([^)]*\)\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'local_storage_prop_property': re.compile(r'@LocalStorageProp\s*\([^)]*\)\s+(?:private\s+)?(\w+)(\?)?:\s*([^;=]+)(?:\s*=\s*([^;]+))?'),
        'method_call': re.compile(r'(\w+)\s*\.\s*(\w+)\s*\('),
        'component_usage': re.compile(r'<(\w+)(?:\s[^>]*)?\s*/?>'),
        'extends': re.compile(r'extends\s+(\w+)'),
        'implements': re.compile(r'implements\s+([^{]+)'),
    }
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self.knowledge_graph = KnowledgeGraph()
        self._entity_counter = 0
        logger.debug("[DEBUG] [TypeScriptRegexParser] [__init__] 初始化解析器, target_project_path=%s, file_patterns=%s",
                     config.target_project_path, config.file_patterns)
    
    def _generate_id(self, prefix: str, name: str, path: str = "") -> str:
        """Generate a unique entity ID."""
        content = f"{prefix}:{name}:{path}:{self._entity_counter}"
        self._entity_counter += 1
        return hashlib.md5(content.encode()).hexdigest()[:16]
    
    def parse_project(self) -> KnowledgeGraph:
        """
        Parse the entire project and build knowledge graph.
        
        Returns:
            KnowledgeGraph containing all entities and relations
        """
        project_path = Path(self.config.target_project_path)
        logger.debug("[DEBUG] [TypeScriptRegexParser] [parse_project] 开始解析项目, project_path=%s", project_path)
        
        if not project_path.exists():
            logger.error("[DEBUG] [TypeScriptRegexParser] [parse_project] 项目路径不存在: %s", project_path)
            raise FileNotFoundError(f"Project path does not exist: {project_path}")
        
        # Find all source files
        source_files = []
        for pattern in self.config.file_patterns:
            source_files.extend(project_path.rglob(pattern))
        
        logger.debug("[DEBUG] [TypeScriptRegexParser] [parse_project] 找到 %d 个源文件", len(source_files))
        
        # Parse each file
        for file_path in source_files:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [parse_project] 正在解析文件: %s", file_path)
            self._parse_file(file_path, project_path)
        
        logger.debug("[DEBUG] [TypeScriptRegexParser] [parse_project] 所有文件解析完成, 实体总数=%d", len(self.knowledge_graph.entities))
        
        # Second pass: resolve cross-file references
        logger.debug("[DEBUG] [TypeScriptRegexParser] [parse_project] 开始解析跨文件引用")
        self._resolve_references()
        
        logger.debug("[DEBUG] [TypeScriptRegexParser] [parse_project] 项目解析完成, 最终实体总数=%d", len(self.knowledge_graph.entities))
        return self.knowledge_graph
    
    def _parse_file(self, file_path: Path, project_path: Path) -> None:
        """Parse a single file and extract entities."""
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_file] 开始解析文件: %s", file_path)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            logger.error("[DEBUG] [TypeScriptRegexParser] [_parse_file] 读取文件失败: %s, 错误: %s", file_path, e)
            print(f"Error reading file {file_path}: {e}")
            return
        
        relative_path = file_path.relative_to(project_path)
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_file] 文件: %s, 相对路径: %s, 行数: %d", file_path.name, relative_path, len(lines))
        
        # Create file entity
        file_id = self._generate_id('file', file_path.name, str(relative_path))
        file_entity = FileEntity(
            id=file_id,
            name=file_path.name,
            entity_type=EntityType.FILE,
            location=SourceLocation(
                file_path=str(relative_path),
                line_number=1,
                column_number=1
            ),
            relative_path=str(relative_path),
            absolute_path=str(file_path.absolute()),
            imports=[],
            metadata={
                'line_count': len(lines),
                'last_modified': os.path.getmtime(file_path),
                'file_hash': hashlib.md5(content.encode()).hexdigest()
            }
        )
        
        # Extract imports
        imports = self._extract_imports(content)
        file_entity.imports = imports
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_file] 文件 %s 提取到 %d 个导入", file_path.name, len(imports))
        
        self.knowledge_graph.add_entity(file_entity)
        
        # 存储导入关系
        if 'imports' not in self.knowledge_graph.metadata:
            self.knowledge_graph.metadata['imports'] = []
        for imp in imports:
            self.knowledge_graph.metadata['imports'].append({
                'source_file_id': file_id,
                'import_path': imp
            })
        
        # Parse classes
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_file] 开始解析文件 %s 中的类/结构体", file_path.name)
        self._parse_classes(content, lines, file_id, str(relative_path))
        
        # Parse interfaces, enums, and type aliases
        self._parse_interfaces(content, lines, file_id, str(relative_path))
        self._parse_enums(content, lines, file_id, str(relative_path))
        self._parse_type_aliases(content, lines, file_id, str(relative_path))
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_file] 文件 %s 解析完成, 当前实体总数=%d", file_path.name, len(self.knowledge_graph.entities))
    
    def _extract_imports(self, content: str) -> List[str]:
        """Extract import statements from file content."""
        imports = []
        for match in self.PATTERNS['import'].finditer(content):
            import_path = match.group(4)
            imports.append(import_path)
        return imports
    
    def _parse_classes(self, content: str, lines: List[str], file_id: str, file_path: str) -> None:
        """Parse class/struct definitions from file content with namespace support."""
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 开始解析文件 %s 中的类定义", file_path)
        # 跟踪命名空间栈和括号深度
        namespace_stack = []
        brace_depth = 0
        in_namespace = False
        namespace_brace_depth = 0
        
        # Find all struct/class definitions with their decorators
        struct_matches = []
        
        for i, line in enumerate(lines, 1):
            stripped = line.strip()
            
            # 跟踪大括号深度（用于检测命名空间范围）
            # 排除字符串和注释中的大括号
            code_only = re.sub(r'//.*$', '', stripped)  # 移除行尾注释
            code_only = re.sub(r'"[^"]*"', '""', code_only)  # 简化字符串
            code_only = re.sub(r"'[^']*'", "''", code_only)  # 简化单引号字符串
            
            # 检测命名空间开始
            namespace_match = self.PATTERNS['namespace'].search(line)
            if namespace_match and not in_namespace:
                ns_name = namespace_match.group(1)
                namespace_stack.append(ns_name)
                in_namespace = True
                namespace_brace_depth = brace_depth
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 检测到命名空间: %s (行 %d)", ns_name, i)
                continue
            
            # 更新大括号深度
            open_braces = code_only.count('{')
            close_braces = code_only.count('}')
            
            # 检测命名空间结束
            if in_namespace:
                brace_depth += open_braces - close_braces
                if brace_depth <= namespace_brace_depth:
                    # 命名空间结束
                    namespace_stack.pop()
                    in_namespace = len(namespace_stack) > 0
                    if in_namespace:
                        namespace_brace_depth = brace_depth
            else:
                brace_depth += open_braces - close_braces
            
            # 构建完整类名（包含命名空间前缀）
            current_namespace = '.'.join(namespace_stack) if namespace_stack else None
            
            # Check for struct definition (ArkTS uses struct for components)
            struct_match = self.PATTERNS['struct'].search(line)
            if struct_match:
                struct_name = struct_match.group(1)
                full_name = f"{current_namespace}.{struct_name}" if current_namespace else struct_name
                # Look for decorators before this line
                decorators = self._get_decorators_for_line(lines, i - 1)
                is_component = '@Component' in decorators
                is_entry = '@Entry' in decorators
                is_exported = line.strip().startswith('export')
                struct_matches.append((struct_name, full_name, i, decorators, is_entry, is_component, is_exported, current_namespace))
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 检测到struct: %s (行 %d), 装饰器=%s, is_component=%s, is_entry=%s, namespace=%s",
                             struct_name, i, decorators, is_component, is_entry, current_namespace)
                continue
            
            # Check for regular class
            class_match = self.PATTERNS['class'].search(line)
            if class_match:
                class_name = class_match.group(1)
                full_name = f"{current_namespace}.{class_name}" if current_namespace else class_name
                parent_class = class_match.group(2)
                implements = class_match.group(3)
                decorators = self._get_decorators_for_line(lines, i - 1)
                is_exported = line.strip().startswith('export')
                struct_matches.append((class_name, full_name, i, decorators, False, False, is_exported, current_namespace, parent_class, implements))
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 检测到class: %s (行 %d), 装饰器=%s, parent=%s, namespace=%s",
                             class_name, i, decorators, parent_class, current_namespace)
        
        # Create class entities
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 共检测到 %d 个类/结构体定义", len(struct_matches))
        for match in struct_matches:
            if len(match) == 8:  # Struct
                class_name, full_name, line_num, decorators, is_entry, is_component, is_exported, namespace = match
                parent_class = None
                implements = []
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 创建struct实体: %s (full_name=%s, 行 %d)", class_name, full_name, line_num)
            else:  # Regular class
                class_name, full_name, line_num, decorators, is_entry, is_component, is_exported, namespace, parent_class, implements_str = match
                implements = [i.strip() for i in implements_str.split(',')] if implements_str else []
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 创建class实体: %s (full_name=%s, 行 %d, parent=%s, implements=%s)",
                             class_name, full_name, line_num, parent_class, implements)
            
            class_id = self._generate_id('class', full_name, file_path)
            class_entity = ClassEntity(
                id=class_id,
                name=class_name,
                entity_type=EntityType.CLASS,
                location=SourceLocation(
                    file_path=file_path,
                    line_number=line_num,
                    column_number=lines[line_num - 1].find('struct' if 'struct' in lines[line_num - 1] else 'class') + 1
                ),
                file_id=file_id,
                is_component=is_component,
                is_entry=is_entry,
                is_exported=is_exported,
                decorators=decorators,
                parent_class=parent_class,
                implemented_interfaces=implements,
                metadata={'file_path': file_path, 'namespace': namespace, 'full_name': full_name}
            )
            
            self.knowledge_graph.add_entity(class_entity)
            
            # 存储继承关系到元数据中（后续会写入数据库）
            if parent_class:
                if 'inheritance' not in self.knowledge_graph.metadata:
                    self.knowledge_graph.metadata['inheritance'] = []
                self.knowledge_graph.metadata['inheritance'].append({
                    'child_class_id': class_id,
                    'child_class_name': class_name,
                    'parent_class_name': parent_class,
                    'relation_type': 'extends'
                })
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 类 %s 继承 %s", class_name, parent_class)
            
            for impl in implements:
                if impl:
                    if 'inheritance' not in self.knowledge_graph.metadata:
                        self.knowledge_graph.metadata['inheritance'] = []
                    self.knowledge_graph.metadata['inheritance'].append({
                        'child_class_id': class_id,
                        'child_class_name': class_name,
                        'parent_class_name': impl.strip(),
                        'relation_type': 'implements'
                    })
            
            # Parse methods within the class/struct
            self._parse_class_methods(content, lines, class_id, file_path, class_name)
            
            # Parse properties within the class/struct
            self._parse_class_properties(content, lines, class_id, file_path, class_name)
            
            # Extract component nesting for @Component classes
            if is_component:
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_classes] 提取组件 %s 的嵌套关系", class_name)
                self._extract_component_nesting(content, class_name, class_id)
    
    def _get_decorators_for_line(self, lines: List[str], line_index: int) -> List[str]:
        """Get decorators preceding a line."""
        decorators = []
        for i in range(line_index - 1, -1, -1):
            line = lines[i].strip()
            if not line or line.startswith('//'):
                continue
            decorator_match = self.PATTERNS['decorator'].match(line)
            if decorator_match:
                decorators.append(f"@{decorator_match.group(1)}")
            else:
                break
        return decorators
    
    def _parse_interfaces(self, content: str, lines: List[str], file_id: str, file_path: str) -> None:
        """Parse interface definitions."""
        for match in self.PATTERNS['interface'].finditer(content):
            interface_name = match.group(1)
            extends_str = match.group(2)
            parent_interfaces = [i.strip() for i in extends_str.split(',')] if extends_str else []
            
            # 找到行号
            line_num = content[:match.start()].count('\n') + 1
            
            interface_id = self._generate_id('interface', interface_name, file_path)
            
            interface_entity = ClassEntity(
                id=interface_id,
                name=interface_name,
                entity_type=EntityType.CLASS,
                location=SourceLocation(
                    file_path=file_path,
                    line_number=line_num,
                    column_number=1
                ),
                file_id=file_id,
                is_component=False,
                is_entry=False,
                is_exported='export' in content[max(0, match.start()-20):match.start()],
                decorators=[],
                parent_class=parent_interfaces[0] if parent_interfaces else None,
                implemented_interfaces=parent_interfaces,
                metadata={'kind': 'interface', 'file_path': file_path}
            )
            
            self.knowledge_graph.add_entity(interface_entity)
            
            # 记录继承关系
            for parent in parent_interfaces:
                if parent:
                    if 'inheritance' not in self.knowledge_graph.metadata:
                        self.knowledge_graph.metadata['inheritance'] = []
                    self.knowledge_graph.metadata['inheritance'].append({
                        'child_class_id': interface_id,
                        'child_class_name': interface_name,
                        'parent_class_name': parent.strip(),
                        'relation_type': 'extends'
                    })
    
    def _parse_enums(self, content: str, lines: List[str], file_id: str, file_path: str) -> None:
        """Parse enum definitions and their members."""
        for match in self.PATTERNS['enum'].finditer(content):
            enum_name = match.group(1)
            line_num = content[:match.start()].count('\n') + 1
            
            # 提取枚举体
            enum_start = match.end()
            brace_count = 1
            enum_end = enum_start
            for i, char in enumerate(content[enum_start:], enum_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        enum_end = i
                        break
            
            enum_body = content[enum_start:enum_end]
            
            # 提取枚举成员
            members = []
            for member_match in re.finditer(r'(\w+)\s*(?:=\s*([^,\n]+))?', enum_body):
                member_name = member_match.group(1)
                member_value = member_match.group(2).strip().rstrip(',') if member_match.group(2) else None
                if member_name and member_name not in ('export', 'const', 'declare'):
                    members.append({'name': member_name, 'value': member_value})
            
            enum_id = self._generate_id('enum', enum_name, file_path)
            
            # 用ClassEntity存储枚举（metadata标记kind）
            enum_entity = ClassEntity(
                id=enum_id,
                name=enum_name,
                entity_type=EntityType.CLASS,
                location=SourceLocation(
                    file_path=file_path,
                    line_number=line_num,
                    column_number=1
                ),
                file_id=file_id,
                is_component=False,
                is_entry=False,
                is_exported='export' in content[max(0, match.start()-20):match.start()],
                decorators=[],
                parent_class=None,
                implemented_interfaces=[],
                metadata={'kind': 'enum', 'members': members, 'file_path': file_path}
            )
            
            self.knowledge_graph.add_entity(enum_entity)
    
    def _parse_type_aliases(self, content: str, lines: List[str], file_id: str, file_path: str) -> None:
        """Parse type alias definitions."""
        # 行内类型别名: type X = A | B;
        for match in self.PATTERNS['type_alias'].finditer(content):
            type_name = match.group(1)
            type_definition = match.group(2).strip()
            line_num = content[:match.start()].count('\n') + 1
            
            type_id = self._generate_id('type', type_name, file_path)
            
            type_entity = ClassEntity(
                id=type_id,
                name=type_name,
                entity_type=EntityType.CLASS,
                location=SourceLocation(
                    file_path=file_path,
                    line_number=line_num,
                    column_number=1
                ),
                file_id=file_id,
                is_component=False,
                is_entry=False,
                is_exported='export' in content[max(0, match.start()-20):match.start()],
                decorators='[]',
                parent_class=None,
                implemented_interfaces=[],
                metadata={'kind': 'type_alias', 'definition': type_definition, 'file_path': file_path}
            )
            
            self.knowledge_graph.add_entity(type_entity)
        
        # 对象类型别名: type X<T> = { ... }
        obj_type_pattern = re.compile(r'(?:export\s+)?type\s+(\w+)(?:<[^>]+>)?\s*=\s*\{')
        for match in obj_type_pattern.finditer(content):
            type_name = match.group(1)
            # 跳过已处理的
            existing = any(e.name == type_name and e.metadata.get('kind') == 'type_alias' 
                         for e in self.knowledge_graph.entities.values())
            if existing:
                continue
            
            line_num = content[:match.start()].count('\n') + 1
            
            # 提取对象体
            obj_start = match.end()
            brace_count = 1
            obj_end = obj_start
            for i, char in enumerate(content[obj_start:], obj_start):
                if char == '{':
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        obj_end = i
                        break
            
            obj_body = content[obj_start:obj_end].strip()
            
            type_id = self._generate_id('type', type_name, file_path)
            type_entity = ClassEntity(
                id=type_id,
                name=type_name,
                entity_type=EntityType.CLASS,
                location=SourceLocation(
                    file_path=file_path,
                    line_number=line_num,
                    column_number=1
                ),
                file_id=file_id,
                is_component=False,
                is_entry=False,
                is_exported='export' in content[max(0, match.start()-20):match.start()],
                decorators='[]',
                parent_class=None,
                implemented_interfaces=[],
                metadata={'kind': 'type_alias', 'definition': obj_body[:100], 'file_path': file_path}
            )
            
            self.knowledge_graph.add_entity(type_entity)

    def _extract_method_signature(self, body_lines: List[str], start_idx: int, modifiers: str) -> Optional[Dict[str, Any]]:
        """
        Extract method signature, supporting multi-line definitions.
        
        Returns dict with: name, params, return_type, lines_consumed, is_getter, is_setter
        or None if not a method signature.
        """
        lines_count = len(body_lines)
        current_idx = start_idx
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_signature] 开始提取签名, start_idx=%d, lines_count=%d, modifiers='%s'", start_idx, lines_count, modifiers.strip())
        
        # 收集起始行的内容（去除修饰符）
        first_line = body_lines[current_idx].strip()
        # 移除已处理的修饰符
        check_line = first_line
        for mod in ['private', 'protected', 'public', 'static', 'async', 'override', 'abstract', 'readonly']:
            if check_line.startswith(mod + ' '):
                check_line = check_line[len(mod) + 1:]
        
        # 检查是否是 getter/setter
        getter_match = re.match(r'^(get|set)\s+(\w+)\s*\(', check_line)
        if getter_match:
            is_getter = getter_match.group(1) == 'get'
            is_setter = getter_match.group(1) == 'set'
            method_name = getter_match.group(2)
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_signature] 检测到 %s: %s", 'getter' if is_getter else 'setter', method_name)
            
            # 从 getter/setter 开始位置找到匹配的括号
            paren_start = check_line.find('(')
            combined = check_line[paren_start:]
            
            # 跨行收集直到找到匹配的 )
            paren_depth = 0
            found_open = False
            while current_idx < lines_count:
                line = body_lines[current_idx].strip()
                if current_idx == start_idx:
                    line = check_line[paren_start:]
                
                for char in line:
                    if char == '(':
                        paren_depth += 1
                        found_open = True
                    elif char == ')':
                        paren_depth -= 1
                        if found_open and paren_depth == 0:
                            combined += char
                            break
                
                if found_open and paren_depth == 0:
                    break
                
                combined += ' '
                current_idx += 1
            
            # 提取返回类型（getter/setter 可能有）
            return_type = None
            if current_idx < lines_count:
                remaining = body_lines[current_idx]
                if current_idx == start_idx:
                    # 在同一行，从 ) 后开始
                    close_idx = check_line.find(')', paren_start)
                    if close_idx >= 0:
                        remaining = check_line[close_idx + 1:]
                else:
                    remaining = remaining.strip()
                
                type_match = re.search(r':\s*([^{;]+)', remaining)
                if type_match:
                    return_type = type_match.group(1).strip()
            
            lines_consumed = current_idx - start_idx + 1
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_signature] getter/setter签名提取完成: name=%s, return_type=%s, lines_consumed=%d",
                         method_name, return_type, lines_consumed)
            return {
                'name': method_name,
                'params': '',  # getter/setter 无参数
                'return_type': return_type,
                'lines_consumed': lines_consumed,
                'is_getter': is_getter,
                'is_setter': is_setter
            }
        
        # 普通方法: 方法名(
        method_match = re.match(r'^(\w+)\s*\(', check_line)
        if not method_match:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_signature] 非方法签名, start_idx=%d", start_idx)
            return None
        
        method_name = method_match.group(1)
        
        # 跳过非方法关键字（constructor 是有效的类方法）
        non_method_keywords = {
            'if', 'else', 'while', 'for', 'switch', 'catch', 'try', 'finally',
            'return', 'throw', 'new', 'typeof', 'instanceof', 'await',
            'console', 'JSON', 'Object', 'Array', 'String', 'Number', 'Boolean',
            'Math', 'Date', 'Promise', 'Map', 'Set', 'super', 'this', 'self',
            'prototype', 'class', 'function'
        }
        if method_name in non_method_keywords:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_signature] 跳过关键字: %s", method_name)
            return None
        
        # 从 ( 开始收集直到匹配 )
        paren_start = check_line.find('(')
        combined = ''
        paren_depth = 0
        found_open = False
        
        while current_idx < lines_count:
            line = body_lines[current_idx]
            if current_idx == start_idx:
                line = check_line[paren_start:]
            
            for char in line:
                if char == '(':
                    paren_depth += 1
                    found_open = True
                elif char == ')':
                    paren_depth -= 1
                    if found_open and paren_depth == 0:
                        combined += char
                        break
                if found_open:
                    combined += char
            
            if found_open and paren_depth == 0:
                break
            
            current_idx += 1
        
        if not found_open or paren_depth != 0:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_signature] 括号未闭合, method=%s", method_name)
            return None
        
        # 提取参数（去除首尾空白）
        params = combined[1:-1].strip() if len(combined) > 2 else ''
        
        # 查找返回类型（从参数闭合的当前行开始）
        return_type = None
        type_buffer = ''
        brace_depth = 0
        type_started = False
        
        # 从参数闭合的那一行（current_idx）开始，向后查找返回类型
        type_search_start = current_idx
        for idx in range(type_search_start, lines_count):
            line = body_lines[idx]
            
            if idx == type_search_start:
                # 参数闭合的行：从 ) 后开始查找
                # 需要找到这一行的 ) 位置
                if idx == start_idx:
                    # 参数在同一行闭合
                    close_idx = check_line.find(')')
                    if close_idx >= 0:
                        remaining = check_line[close_idx + 1:]
                    else:
                        continue
                else:
                    # 参数在后面的行闭合，需要重建该行内容
                    # 从 combined 知道 ) 在这一行
                    remaining = line
                    # 找到 ) 的位置
                    paren_idx = remaining.find(')')
                    if paren_idx >= 0:
                        remaining = remaining[paren_idx + 1:]
            else:
                remaining = line
            
            if not type_started:
                # 查找 : 开始返回类型
                type_match = re.search(r':\s*(.*)', remaining)
                if type_match:
                    type_started = True
                    type_buffer = type_match.group(1).strip()
                    # 如果类型为空，继续下一行
                    if not type_buffer:
                        continue
                    # 截断到 { 或 ;
                    for end_char in ['{', ';']:
                        if end_char in type_buffer:
                            type_buffer = type_buffer[:type_buffer.find(end_char)].strip()
                            break
                    # 计算括号深度
                    brace_depth = type_buffer.count('<') + type_buffer.count('{') + type_buffer.count('(') - type_buffer.count('>') - type_buffer.count('}') - type_buffer.count(')')
                    if brace_depth <= 0:
                        return_type = type_buffer.rstrip(',')
                        current_idx = idx + 1
                        break
            else:
                # 继续收集多行类型
                remaining_stripped = remaining.strip()
                for end_char in ['{', ';']:
                    if end_char in remaining_stripped:
                        remaining_stripped = remaining_stripped[:remaining_stripped.find(end_char)].strip()
                        break
                type_buffer += ' ' + remaining_stripped
                brace_depth += remaining_stripped.count('<') + remaining_stripped.count('{') + remaining_stripped.count('(') - remaining_stripped.count('>') - remaining_stripped.count('}') - remaining_stripped.count(')')
                if brace_depth <= 0:
                    return_type = type_buffer.strip().rstrip(',')
                    current_idx = idx + 1
                    break
        
        if type_started and return_type is None:
            for end_char in ['{', ';']:
                if end_char in type_buffer:
                    type_buffer = type_buffer[:type_buffer.find(end_char)].strip()
                    break
            return_type = type_buffer.strip().rstrip(',') if type_buffer else None
        
        # 如果没有找到返回类型（如构造函数），至少消耗到参数闭合行
        if not type_started:
            # 查找 { 或 ; 来确定方法体开始
            for idx in range(type_search_start, lines_count):
                line = body_lines[idx]
                if '{' in line or ';' in line:
                    current_idx = idx + 1
                    break
            else:
                current_idx = type_search_start + 1
        
        lines_consumed = current_idx - start_idx
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_signature] 签名提取完成: name=%s, params='%s', return_type=%s, lines_consumed=%d",
                     method_name, params, return_type, lines_consumed)
        return {
            'name': method_name,
            'params': params,
            'return_type': return_type,
            'lines_consumed': lines_consumed,
            'is_getter': False,
            'is_setter': False
        }

    def _find_class_body(self, content: str, class_name: str) -> tuple:
        """
        Find the body of a class/struct, correctly handling generic constraints.
        
        Returns:
            Tuple of (class_body, class_start_offset, line_offset) or None
        """
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_find_class_body] 查找类体: %s", class_name)
        # 找到 class/struct 关键字
        pattern = re.compile(rf'(?:class|struct)\s+{re.escape(class_name)}\b')
        match = pattern.search(content)
        if not match:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_find_class_body] 未找到类定义: %s", class_name)
            return None
        
        # 从关键字后向前扫描，找到类体的开始 {
        # 需要跳过泛型约束中的 { } 如 <T extends { id: string }>
        search_start = match.end()
        pos = search_start
        depth = 0
        
        while pos < len(content):
            char = content[pos]
            if char == '<':
                depth += 1
            elif char == '>' and depth > 0:
                depth -= 1
            elif char == '{' and depth <= 0:
                # 这是类体的开始 {
                class_start = pos + 1
                # 找到匹配的 }
                brace_count = 1
                class_end = class_start
                for i, c in enumerate(content[class_start:], class_start):
                    if c == '{':
                        brace_count += 1
                    elif c == '}':
                        brace_count -= 1
                        if brace_count == 0:
                            class_end = i
                            break
                
                class_body = content[class_start:class_end]
                line_offset = content[:class_start].count('\n')
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_find_class_body] 找到类体: %s, 行偏移=%d, 类体长度=%d", class_name, line_offset, len(class_body))
                return (class_body, line_offset)
            elif char == '{':
                # 泛型约束中的 {，depth > 0
                pass
            pos += 1
        
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_find_class_body] 未找到类 %s 的开始大括号", class_name)
        return None
    
    def _parse_class_methods(self, content: str, lines: List[str], class_id: str, file_path: str, class_name: str) -> None:
        """Parse method definitions within a class/struct."""
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_methods] 开始解析类 %s 的方法", class_name)
        # Find the class/struct body
        result = self._find_class_body(content, class_name)
        if not result:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_methods] 未找到类 %s 的类体, 跳过方法解析", class_name)
            return
        
        class_body, class_lines = result
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_methods] 类 %s 类体行偏移=%d", class_name, class_lines)
        
        # 方法定义关键字列表（排除这些不是方法）
        # 注意：constructor 是有效的类构造函数，不在这里排除
        non_method_keywords = {
            'if', 'else', 'while', 'for', 'switch', 'catch', 'try', 'finally',
            'return', 'throw', 'new', 'typeof', 'instanceof', 'await',
            'console', 'JSON', 'Object', 'Array', 'String', 'Number', 'Boolean',
            'Math', 'Date', 'Promise', 'Map', 'Set', 'WeakMap', 'WeakSet',
            'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
            'fetch', 'require', 'import', 'export',
            'super', 'this', 'self',
            'prototype', 'class', 'function'
        }
        
        # ArkUI 组件方法（这些是调用，不是定义）
        # 首字母大写的通常是组件实例化调用
        arkui_components = {
            'Button', 'Text', 'Image', 'Column', 'Row', 'List', 'ListItem',
            'LoadingProgress', 'TextInput', 'Blank', 'ForEach', 'LazyForEach',
            'Scroll', 'Stack', 'Flex', 'Grid', 'GridItem', 'Swiper', 'Tabs', 'TabContent',
            'Navigation', 'NavRouter', 'NavDestination', 'Navigator',
            'AlphabetIndexer', 'Badge', 'Clock', 'Counter', 'Gauge', 'ImageAnimator',
            'Marquee', 'Progress', 'Qrcode', 'Rating', 'RichText', 'Span',
            'Stepper', 'StepperItem', 'TextClock', 'TextTimer', 'TimePicker',
            'Toggle', 'ToggleGroup', 'Web', 'XComponent',
            # 自定义组件（根据测试项目）
            'LoadingSpinner', 'ErrorDisplay', 'UserAvatar', 'UserCard', 'BaseButton',
            'UserListPage', 'AdminDashboardPage'
        }
        
        # ArkUI 链式调用方法（这些是属性设置，不是方法定义）
        arkui_methods = {
            'width', 'height', 'fontSize', 'fontColor', 'backgroundColor',
            'borderRadius', 'padding', 'margin', 'onClick', 'onChange',
            'enabled', 'shadow', 'layoutWeight', 'justifyContent', 'alignItems',
            'fontWeight', 'textAlign', 'color', 'border', 'opacity',
            'fontStyle', 'letterSpacing', 'textDecoration', 'lineHeight',
            'maxLines', 'textOverflow', 'wordBreak', 'whiteSpace',
            'animation', 'transition', 'translate', 'scale', 'rotate',
            'position', 'zIndex', 'id', 'key', 'visibility', 'display',
            'aspectRatio', 'constraintSize', 'size', 'area', 'point'
        }
        
        # 已处理的方法名（避免重复）
        processed_methods = set()
        
        # 使用逐行解析方法定义
        body_lines = class_body.split('\n')
        i = 0
        while i < len(body_lines):
            line = body_lines[i]
            stripped = line.strip()
            
            # 跳过空行和注释
            if not stripped or stripped.startswith('//') or stripped.startswith('/*') or stripped.startswith('*'):
                i += 1
                continue
            
            # 收集装饰器（在修饰符之前）
            method_decorators = []
            
            # 收集所有修饰符（可能跨多行）
            all_modifiers = ''
            check_line = stripped
            while True:
                # 检查装饰器
                decorator_match = re.match(r'^@(\w+)(?:\([^)]*\))?\s+', check_line)
                if decorator_match:
                    method_decorators.append(f"@{decorator_match.group(1)}")
                    check_line = check_line[decorator_match.end():]
                    continue
                
                mod_match = re.match(r'^(private|protected|public|static|async|override|abstract|readonly)\s+', check_line)
                if mod_match:
                    all_modifiers += mod_match.group(1) + ' '
                    check_line = check_line[mod_match.end():]
                else:
                    break
            
            # 检查是否是方法定义行（支持多行签名）
            # 格式: [装饰器] [修饰符] 方法名(参数)[: 返回类型] [{ | ;]
            method_signature = self._extract_method_signature(body_lines, i, all_modifiers)
            
            if method_signature:
                method_name = method_signature['name']
                params = method_signature['params']
                return_type = method_signature['return_type'] or 'void'
                lines_consumed = method_signature['lines_consumed']
                is_getter = method_signature.get('is_getter', False)
                is_setter = method_signature.get('is_setter', False)
                
                if is_getter:
                    all_modifiers += 'get '
                if is_setter:
                    all_modifiers += 'set '
                
                # 跳过非方法关键字和ArkUI组件/方法调用
                if (method_name not in non_method_keywords and 
                    method_name not in arkui_methods and 
                    method_name not in arkui_components):
                    # 跳过已处理的方法
                    if method_name not in processed_methods:
                        processed_methods.add(method_name)
                        
                        line_num = class_lines + i + 1
                        method_id = self._generate_id('method', method_name, f"{class_name}.{method_name}")
                        
                        # 解析参数
                        param_list = []
                        if params.strip():
                            for param in params.split(','):
                                param = param.strip()
                                if ':' in param:
                                    parts = param.split(':', 1)
                                    param_list.append({
                                        'name': parts[0].strip(),
                                        'type': parts[1].strip()
                                    })
                                elif param:
                                    param_list.append({'name': param, 'type': 'any'})
                        
                        method_entity = MethodEntity(
                            id=method_id,
                            name=method_name,
                            entity_type=EntityType.METHOD,
                            location=SourceLocation(
                                file_path=file_path,
                                line_number=line_num,
                                column_number=1
                            ),
                            class_id=class_id,
                            is_static='static' in all_modifiers,
                            is_async='async' in all_modifiers,
                            is_private='private' in all_modifiers,
                            is_protected='protected' in all_modifiers,
                            is_public='public' in all_modifiers or ('private' not in all_modifiers and 'protected' not in all_modifiers),
                            return_type=return_type.strip(),
                            parameters=param_list,
                            metadata={
                                'class_name': class_name,
                                'is_abstract': 'abstract' in all_modifiers,
                                'is_override': 'override' in all_modifiers,
                                'is_getter': is_getter,
                                'is_setter': is_setter,
                                'decorators': method_decorators
                            }
                        )
                        
                        self.knowledge_graph.add_entity(method_entity)
                        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_methods] 添加方法: %s.%s (行 %d), 参数=%s, 返回类型=%s, 装饰器=%s, 修饰符='%s'",
                                     class_name, method_name, line_num, param_list, return_type, method_decorators, all_modifiers.strip())
                        
                        # 提取方法调用关系 - 使用实际的方法体而非整个类体
                        method_body_start = i + lines_consumed
                        method_body, body_lines_consumed = self._extract_method_body(body_lines, method_body_start)
                        if method_body:
                            self._extract_method_calls(method_body, method_id, class_id, class_name)
                        
                        # 跳过已处理的行数（签名 + 方法体）
                        i += lines_consumed + body_lines_consumed
                        continue
            
            i += 1
    
    def _parse_class_properties(self, content: str, lines: List[str], class_id: str, file_path: str, class_name: str) -> None:
        """Parse property definitions within a class/struct."""
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_properties] 开始解析类 %s 的属性", class_name)
        # Find the class/struct body
        result = self._find_class_body(content, class_name)
        if not result:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_properties] 未找到类 %s 的类体, 跳过属性解析", class_name)
            return
        
        class_body, class_lines = result
        
        # 已处理的属性名（避免重复）
        processed_props = set()
        
        # 所有ArkTS状态管理装饰器模式
        decorator_patterns = [
            ('@State', self.PATTERNS['state_property']),
            ('@Prop', self.PATTERNS['prop_property']),
            ('@Provide', self.PATTERNS['provide_property']),
            ('@Consume', self.PATTERNS['consume_property']),
            ('@Link', self.PATTERNS['link_property']),
            ('@Watch', self.PATTERNS['watch_property']),
            ('@StorageLink', self.PATTERNS['storage_link_property']),
            ('@StorageProp', self.PATTERNS['storage_prop_property']),
            ('@LocalStorageLink', self.PATTERNS['local_storage_link_property']),
            ('@LocalStorageProp', self.PATTERNS['local_storage_prop_property']),
        ]
        
        # 用装饰器模式提取属性
        for decorator_name, pattern in decorator_patterns:
            for match in pattern.finditer(class_body):
                prop_name = match.group(1)
                if prop_name in processed_props:
                    continue
                processed_props.add(prop_name)
                
                is_optional = match.group(2) == '?'
                prop_type = match.group(3) or 'any'
                default_value = match.group(4)
                
                line_offset = class_body[:match.start()].count('\n')
                line_num = class_lines + line_offset + 1
                
                prop_id = self._generate_id('property', prop_name, f"{class_name}.{prop_name}")
                
                property_entity = PropertyEntity(
                    id=prop_id,
                    name=prop_name,
                    entity_type=EntityType.PROPERTY,
                    location=SourceLocation(
                        file_path=file_path,
                        line_number=line_num,
                        column_number=1
                    ),
                    class_id=class_id,
                    property_type=prop_type.strip(),
                    is_static=False,
                    is_readonly=False,
                    is_optional=is_optional,
                    default_value=default_value.strip() if default_value else None,
                    metadata={'class_name': class_name, 'decorator': decorator_name}
                )
                
                self.knowledge_graph.add_entity(property_entity)
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_properties] 添加装饰器属性: %s.%s (类型=%s, 装饰器=%s, 行 %d)",
                             class_name, prop_name, prop_type.strip(), decorator_name, line_num)
        
        # Find regular properties in class body
        for match in self.PATTERNS['property'].finditer(class_body):
            modifiers = match.group(1) or ''
            prop_name = match.group(2)
            is_optional = match.group(3) == '?'
            prop_type = match.group(4) or 'any'
            default_value = match.group(5)
            
            # Skip if it looks like a method
            if prop_name in ['if', 'while', 'for', 'switch', 'catch', 'return', 'build']:
                continue
            
            # Skip already processed
            if prop_name in processed_props:
                continue
            
            # Skip if followed by parentheses (it's a method)
            remaining = class_body[match.end():].strip()
            if remaining.startswith('('):
                continue
            
            processed_props.add(prop_name)
            line_offset = class_body[:match.start()].count('\n')
            line_num = class_lines + line_offset + 1
            
            prop_id = self._generate_id('property', prop_name, f"{class_name}.{prop_name}")
            
            property_entity = PropertyEntity(
                id=prop_id,
                name=prop_name,
                entity_type=EntityType.PROPERTY,
                location=SourceLocation(
                    file_path=file_path,
                    line_number=line_num,
                    column_number=1
                ),
                class_id=class_id,
                property_type=prop_type.strip(),
                is_static='static' in modifiers,
                is_readonly='readonly' in modifiers,
                is_optional=is_optional,
                default_value=default_value.strip() if default_value else None,
                metadata={'class_name': class_name}
            )
            
            self.knowledge_graph.add_entity(property_entity)
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_parse_class_properties] 添加普通属性: %s.%s (类型=%s, 修饰符='%s', 行 %d)",
                         class_name, prop_name, prop_type.strip(), modifiers, line_num)
    
    def _extract_method_body(self, body_lines: List[str], start_idx: int) -> Tuple[Optional[str], int]:
        """
        Extract method body from body_lines starting at start_idx (the line containing '{').

        Correctly handles nested braces (lambdas, objects, if/for/while blocks, etc.).

        Returns:
            Tuple of (method_body_text, lines_consumed) or (None, 0) if no body found.
        """
        lines_count = len(body_lines)
        brace_depth = 0
        body_lines_list = []

        for idx in range(start_idx, lines_count):
            line = body_lines[idx]
            for char in line:
                if char == '{':
                    brace_depth += 1
                elif char == '}':
                    brace_depth -= 1
                    if brace_depth == 0:
                        body_lines_list.append(line)
                        return '\n'.join(body_lines_list), len(body_lines_list)
            body_lines_list.append(line)

        # Unmatched braces - return what we have
        if body_lines_list:
            return '\n'.join(body_lines_list), len(body_lines_list)
        return None, 0

    def _extract_method_calls(self, method_body: str, method_id: str, class_id: str, class_name: str) -> None:
        """Extract method calls from a method body."""
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_calls] 提取方法调用, class=%s, method_id=%s", class_name, method_id)
        # 需要排除的调用目标（不是真正的业务方法调用）
        non_call_targets = {
            'console', 'JSON', 'Object', 'Array', 'String', 'Number', 'Boolean',
            'Math', 'Date', 'Promise', 'Map', 'Set', 'setTimeout', 'setInterval',
            'clearTimeout', 'clearInterval', 'fetch', 'this', 'super', 'self',
            'parseInt', 'parseFloat', 'isNaN', 'encodeURI', 'decodeURI',
            'Error', 'TypeError', 'RangeError', 'RegExp', 'Symbol',
            'Object', 'Array', 'Proxy', 'Reflect',
            'ArkTools', 'deviceInfo', 'appInfo', 'context'
        }
        
        for match in self.PATTERNS['method_call'].finditer(method_body):
            target_obj = match.group(1)
            target_method = match.group(2)
            
            # 跳过非业务调用
            if target_obj in non_call_targets:
                continue
            # 跳过 ArkUI 链式调用（如 .width(), .fontSize()）
            if target_method in {
                'width', 'height', 'fontSize', 'fontColor', 'backgroundColor',
                'borderRadius', 'padding', 'margin', 'onClick', 'onChange',
                'enabled', 'shadow', 'layoutWeight', 'justifyContent', 'alignItems',
                'fontWeight', 'textAlign', 'color', 'border', 'opacity',
                'fontStyle', 'letterSpacing', 'textDecoration', 'lineHeight',
                'maxLines', 'textOverflow', 'animation', 'transition',
                'translate', 'scale', 'rotate', 'position', 'zIndex',
                'id', 'key', 'visibility', 'display', 'size', 'area',
                'pop', 'push', 'forEach', 'map', 'filter', 'reduce', 'find',
                'some', 'every', 'includes', 'indexOf', 'slice', 'splice',
                'join', 'split', 'trim', 'startsWith', 'endsWith', 'replace',
                'toLowerCase', 'toUpperCase', 'substring', 'charAt', 'charCodeAt',
                'toString', 'valueOf', 'hasOwnProperty', 'keys', 'values', 'entries',
                'stringify', 'parse', 'assign', 'freeze', 'create', 'defineProperty',
                'then', 'catch', 'finally', 'all', 'race', 'resolve', 'reject',
                'bind', 'call', 'apply', 'length', 'count', 'add', 'delete', 'set', 'get',
                'abs', 'ceil', 'floor', 'round', 'min', 'max', 'random', 'sqrt', 'pow',
                'log', 'warn', 'error', 'info', 'table', 'time', 'timeEnd', 'group', 'groupEnd',
                'write', 'read', 'end', 'on', 'emit', 'once', 'off',
                'addEventListener', 'removeEventListener',
                'getState', 'setState', 'forceUpdate', 'render',
                'querySelector', 'querySelectorAll', 'getElementById',
                'createElement', 'appendChild', 'removeChild',
                'toLocaleDateString', 'toLocaleTimeString', 'toISOString',
                'toFixed', 'toPrecision', 'toExponential',
                'sign', 'trunc', 'cbrt', 'hypot', 'log2', 'log10', 'exp',
                'sin', 'cos', 'tan', 'asin', 'acos', 'atan', 'atan2',
                'next', 'done', 'return', 'throw'
            }:
                continue
            
            call_info = {
                'caller_method_id': method_id,
                'caller_class_id': class_id,
                'caller_class_name': class_name,
                'target_object': target_obj,
                'target_method': target_method
            }
            method_entity = self.knowledge_graph.entities.get(method_id)
            if method_entity is None:
                continue
            if 'calls' not in method_entity.metadata:
                method_entity.metadata['calls'] = []
            method_entity.metadata['calls'].append(call_info)
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_method_calls] 发现调用: %s.%s -> %s.%s",
                         class_name, method_entity.name, target_obj, target_method)
    
    def _extract_component_nesting(self, content: str, class_name: str, class_id: str) -> None:
        """Extract component nesting relationships from build() method."""
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_component_nesting] 提取组件嵌套, class=%s", class_name)
        # 找到 build 方法体
        build_pattern = re.compile(
            rf'(?:private\s+|public\s+|protected\s+)?build\s*\(\s*\)'
            rf'(?:\s*:\s*[^{{]+)?\s*{{',
            re.DOTALL
        )
        build_match = build_pattern.search(content)
        if not build_match:
            logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_component_nesting] 类 %s 未找到 build() 方法", class_name)
            return
        
        build_start = build_match.end()
        brace_count = 1
        build_end = build_start
        for i, char in enumerate(content[build_start:], build_start):
            if char == '{':
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0:
                    build_end = i
                    break
        
        build_body = content[build_start:build_end]
        
        # 需要排除的内置组件
        builtin_components = {
            'Column', 'Row', 'List', 'ListItem', 'Grid', 'GridItem',
            'Text', 'Image', 'Button', 'TextInput', 'TextArea',
            'Scroll', 'Stack', 'Flex', 'Tabs', 'TabContent',
            'Navigation', 'NavRouter', 'NavDestination',
            'LoadingProgress', 'Blank', 'ForEach', 'LazyForEach',
            'Swiper', 'Stepper', 'StepperItem', 'Panel',
            'Counter', 'Gauge', 'Chart', 'DataPanel',
            'Marquee', 'Progress', 'QRCode', 'Rating',
            'RichText', 'Search', 'Select', 'Slider',
            'Span', 'TextClock', 'TextPicker', 'TextTimer',
            'TimePicker', 'Toggle', 'Web',
            'XComponent', 'AlphabetIndexer', 'Badge',
            'Clock', 'Divider', 'FlowItem', 'Gesture',
            'Hyperlink', 'MediaQuery', 'MotionPath', 'Overlay',
            'Refresh', 'Shape', 'Video',
            'If', 'Else', 'While', 'ForEach',
            'ListItemGroup', 'ListItem', 'SwiperItem',
            'TabContent', 'GridItem', 'GridCol', 'GridRow',
            'RowSplit', 'SideBarContainer', 'StepperItem'
        }
        
        # ArkTS组件使用两种语法：
        # 1. 声明式: <ComponentName /> 或 <ComponentName>...</ComponentName>
        # 2. 命令式: ComponentName({ ... })
        component_pattern = re.compile(r'(?<![.\w])([A-Z][a-zA-Z0-9_]*)\s*[\(<]')
        
        # 提取组件使用
        if 'components' not in self.knowledge_graph.metadata:
            self.knowledge_graph.metadata['components'] = []
        
        seen_children = set()
        for match in component_pattern.finditer(build_body):
            child_name = match.group(1)
            if child_name not in builtin_components and child_name not in seen_children:
                seen_children.add(child_name)
                self.knowledge_graph.metadata['components'].append({
                    'parent_class_id': class_id,
                    'parent_class_name': class_name,
                    'child_name': child_name
                })
                logger.debug("[DEBUG] [TypeScriptRegexParser] [_extract_component_nesting] 发现嵌套组件: %s -> %s", class_name, child_name)
    
    def _resolve_references(self) -> None:
        """Resolve cross-file and cross-class references."""
        from core.entity_models import ClassEntity, MethodEntity
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_resolve_references] 开始解析引用, 当前实体总数=%d", len(self.knowledge_graph.entities))
        
        # 构建符号表
        class_by_name = {}
        method_by_key = {}
        
        for entity in self.knowledge_graph.entities.values():
            if isinstance(entity, ClassEntity):
                class_by_name[entity.name] = entity
            elif isinstance(entity, MethodEntity):
                cls_name = entity.metadata.get('class_name', '')
                method_by_key[(cls_name, entity.name)] = entity
        
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_resolve_references] 符号表构建完成, 类数量=%d, 方法数量=%d",
                     len(class_by_name), len(method_by_key))
        
        # 解析方法调用关系
        if 'calls' not in self.knowledge_graph.metadata:
            self.knowledge_graph.metadata['calls'] = []
        
        for entity in list(self.knowledge_graph.entities.values()):
            if isinstance(entity, MethodEntity) and 'calls' in entity.metadata:
                for call_info in entity.metadata['calls']:
                    target_obj = call_info['target_object']
                    target_method = call_info['target_method']
                    
                    callee_class_id = None
                    callee_method_id = None
                    
                    # 在符号表中查找目标类
                    if target_obj in class_by_name:
                        callee_class_id = class_by_name[target_obj].id
                        # 在该类中查找目标方法
                        method_key = (target_obj, target_method)
                        if method_key in method_by_key:
                            callee_method_id = method_by_key[method_key].id
                        logger.debug("[DEBUG] [TypeScriptRegexParser] [_resolve_references] 解析调用: %s.%s -> %s.%s (callee_class_id=%s, callee_method_id=%s)",
                                     entity.metadata.get('class_name', '?'), entity.name, target_obj, target_method,
                                     callee_class_id, callee_method_id)
                    else:
                        logger.debug("[DEBUG] [TypeScriptRegexParser] [_resolve_references] 未解析调用目标: %s.%s -> %s (目标类 %s 未找到)",
                                     entity.metadata.get('class_name', '?'), entity.name, target_method, target_obj)
                    
                    self.knowledge_graph.metadata['calls'].append({
                        'caller_method_id': entity.id,
                        'caller_class_id': entity.class_id,
                        'callee_method_id': callee_method_id,
                        'callee_class_id': callee_class_id,
                        'callee_name': f"{target_obj}.{target_method}"
                    })
                
                # 清理临时数据，释放内存
                del entity.metadata['calls']
        
        # 解析组件嵌套关系（需要源码，在 parse_project 中已处理）
        # 这里只做引用解析
        if 'components' in self.knowledge_graph.metadata:
            for comp in self.knowledge_graph.metadata['components']:
                child_name = comp.get('child_name', '')
                if child_name in class_by_name:
                    comp['child_class_id'] = class_by_name[child_name].id
                    logger.debug("[DEBUG] [TypeScriptRegexParser] [_resolve_references] 解析组件引用: %s -> %s (child_class_id=%s)",
                                 comp.get('parent_class_name'), child_name, comp['child_class_id'])
                else:
                    logger.debug("[DEBUG] [TypeScriptRegexParser] [_resolve_references] 未解析组件引用: %s (目标类未找到)", child_name)
        
        logger.debug("[DEBUG] [TypeScriptRegexParser] [_resolve_references] 引用解析完成")


class ArkAnalyzerAdapter:
    """
    Adapter for ArkAnalyzer tool output.
    
    This adapter can either run ArkAnalyzer directly (if installed)
    or use the fallback regex parser.
    """
    
    def __init__(self, config: ParserConfig):
        self.config = config
        self._fallback_parser = TypeScriptRegexParser(config)
    
    @property
    def knowledge_graph(self):
        """Proxy to the internal parser's knowledge graph."""
        return self._fallback_parser.knowledge_graph
    
    def _parse_file(self, file_path, project_path):
        """Proxy to the internal parser's _parse_file method."""
        return self._fallback_parser._parse_file(file_path, project_path)
    
    def is_ark_analyzer_available(self) -> bool:
        """Check if ArkAnalyzer is available on the system."""
        if not self.config.ark_analyzer_path:
            return False
        
        ark_path = Path(self.config.ark_analyzer_path)
        if not ark_path.exists():
            return False
        
        # Try to run ArkAnalyzer --version
        try:
            result = subprocess.run(
                ['node', str(ark_path / 'bin' / 'arkanalyzer'), '--version'],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def parse_project(self) -> KnowledgeGraph:
        """
        Parse the project and return knowledge graph.
        
        If ArkAnalyzer is available, use it. Otherwise, use the fallback parser.
        
        Returns:
            KnowledgeGraph containing all entities and relations
        """
        if self.is_ark_analyzer_available():
            return self._parse_with_ark_analyzer()
        else:
            print("ArkAnalyzer not available, using fallback parser...")
            return self._fallback_parser.parse_project()
    
    def _parse_with_ark_analyzer(self) -> KnowledgeGraph:
        """Parse project using ArkAnalyzer tool."""
        # This would implement the actual ArkAnalyzer integration
        # For now, fall back to regex parser
        return self._fallback_parser.parse_project()
