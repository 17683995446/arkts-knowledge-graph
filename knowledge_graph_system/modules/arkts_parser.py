"""
ArkTS解析模块 (arkts_parser)

职责：
1. 解析ArkTS/TypeScript代码
2. 提取代码实体（函数、类、接口、变量等）
3. 分析实体间关系（调用、继承、引用等）
4. 构建代码依赖图

第一性原理：
- 使用tree-sitter进行语法解析，准确率高
- 只提取需要的实体和关系，不存储完整AST
- 解析结果直接用于数据库插入
"""

import json
import re
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set, Tuple, Any
from pathlib import Path


try:
    from tree_sitter import Language, Parser, Tree, Node
    import tree_sitter_typescript as ts_typescript
    TREESITTER_AVAILABLE = True
except ImportError:
    TREESITTER_AVAILABLE = False
    print("[arkts_parser] tree-sitter未安装，将使用正则回退方案")


@dataclass
class CodeEntity:
    """代码实体"""
    file_path: str
    entity_type: str  # 'function', 'class', 'interface', 'variable', 'enum', 'type_alias', 'import'
    name: str
    signature: str = ""
    start_line: int = 0
    end_line: int = 0
    code_snippet: str = ""
    modifiers: List[str] = field(default_factory=list)  # export, async, static, private等
    parent_name: Optional[str] = None  # 父级实体名称（如类中的方法）
    parameters: List[Dict] = field(default_factory=list)  # 函数参数
    return_type: Optional[str] = None  # 返回类型
    decorators: List[str] = field(default_factory=list)  # ArkTS装饰器如@Entry, @Component


@dataclass
class EntityRelation:
    """实体关系"""
    source_file: str
    source_entity: str
    target_file: str
    target_entity: str
    relation_type: str  # 'calls', 'extends', 'implements', 'imports', 'references', 'contains'


@dataclass
class FileDependency:
    """文件依赖"""
    source_file: str
    target_file: str
    dependency_type: str  # 'import', 'dynamic_import', 'require'
    imported_names: List[str] = field(default_factory=list)


@dataclass
class ParseResult:
    """解析结果"""
    entities: List[CodeEntity] = field(default_factory=list)
    relations: List[EntityRelation] = field(default_factory=list)
    dependencies: List[FileDependency] = field(default_factory=list)
    
    def merge(self, other: 'ParseResult') -> 'ParseResult':
        """合并另一个解析结果"""
        self.entities.extend(other.entities)
        self.relations.extend(other.relations)
        self.dependencies.extend(other.dependencies)
        return self


class ArkTSParser:
    """
    ArkTS代码解析器
    
    支持：
    - 函数声明/表达式/箭头函数
    - 类定义（含@Component等装饰器）
    - 接口定义
    - 类型别名
    - 枚举
    - 变量声明
    - import/export语句
    """
    
    # ArkTS/TS装饰器列表
    ARKTS_DECORATORS = {
        '@Entry', '@Component', '@State', '@Prop', '@Link', '@Provide', '@Consume',
        '@Watch', '@Builder', '@Styles', '@Extend', '@CustomDialog', '@Preview',
        '@StorageLink', '@StorageProp', '@LocalStorageLink', '@LocalStorageProp'
    }
    
    def __init__(self):
        self._parser: Optional[Any] = None
        self._language: Optional[Any] = None
        self._init_parser()
    
    def _init_parser(self) -> None:
        """初始化tree-sitter解析器"""
        if not TREESITTER_AVAILABLE:
            return
        
        try:
            self._language = ts_typescript.language()
            self._parser = Parser(self._language)
        except Exception as e:
            print(f"[arkts_parser] 初始化tree-sitter失败: {e}")
            self._parser = None
    
    def parse(self, content: str, file_path: str) -> ParseResult:
        """
        解析ArkTS代码
        
        Args:
            content: 文件内容
            file_path: 文件路径（用于关系分析）
        
        Returns:
            ParseResult: 解析结果
        """
        if self._parser and TREESITTER_AVAILABLE:
            return self._parse_with_treesitter(content, file_path)
        else:
            return self._parse_with_regex(content, file_path)
    
    def _parse_with_treesitter(self, content: str, file_path: str) -> ParseResult:
        """使用tree-sitter解析"""
        result = ParseResult()
        
        try:
            tree = self._parser.parse(content.encode('utf-8'))
            root_node = tree.root_node
            
            # 提取所有实体
            entities = self._extract_entities(root_node, content, file_path)
            result.entities = entities
            
            # 提取import依赖
            dependencies = self._extract_imports(root_node, content, file_path)
            result.dependencies = dependencies
            
            # 提取实体间关系
            relations = self._extract_relations(root_node, content, file_path, entities)
            result.relations = relations
            
        except Exception as e:
            print(f"[arkts_parser] tree-sitter解析失败: {e}，回退到正则解析")
            return self._parse_with_regex(content, file_path)
        
        return result
    
    def _extract_entities(self, node: Any, content: str, file_path: str) -> List[CodeEntity]:
        """提取代码实体"""
        entities = []
        lines = content.split('\n')
        
        def traverse(node: Any, parent_name: Optional[str] = None):
            entity_type = None
            name = None
            modifiers = []
            decorators = []
            start_line = node.start_point[0] + 1
            end_line = node.end_point[0] + 1
            
            # 获取装饰器
            if node.type in ['class_declaration', 'function_declaration', 'method_definition']:
                decorators = self._get_decorators(node, content)
            
            # 类定义
            if node.type == 'class_declaration':
                entity_type = 'class'
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                
                # 获取修饰符
                for child in node.children:
                    if child.type in ['export', 'default', 'abstract', 'declare']:
                        modifiers.append(child.type)
                
                # 获取继承和实现
                heritage = node.child_by_field_name('heritage')
                if heritage:
                    for child in heritage.children:
                        if child.type == 'extends_clause':
                            modifiers.append('extends')
                        elif child.type == 'implements_clause':
                            modifiers.append('implements')
            
            # 函数声明
            elif node.type == 'function_declaration':
                entity_type = 'function'
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                
                for child in node.children:
                    if child.type in ['export', 'default', 'async', 'declare']:
                        modifiers.append(child.type)
            
            # 函数表达式/箭头函数（作为变量值）
            elif node.type in ['function_expression', 'arrow_function']:
                # 检查是否是变量声明的值
                if parent_name:
                    entity_type = 'function'
                    name = parent_name
            
            # 方法定义
            elif node.type == 'method_definition':
                entity_type = 'method'
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                
                for child in node.children:
                    if child.type in ['static', 'async', 'get', 'set', 'private', 'protected', 'public']:
                        modifiers.append(child.type)
            
            # 接口定义
            elif node.type == 'interface_declaration':
                entity_type = 'interface'
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                
                for child in node.children:
                    if child.type == 'export':
                        modifiers.append(child.type)
            
            # 类型别名
            elif node.type == 'type_alias_declaration':
                entity_type = 'type_alias'
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                
                for child in node.children:
                    if child.type == 'export':
                        modifiers.append(child.type)
            
            # 枚举定义
            elif node.type == 'enum_declaration':
                entity_type = 'enum'
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                
                for child in node.children:
                    if child.type in ['export', 'const']:
                        modifiers.append(child.type)
            
            # 修复：ArkTS struct 定义（tree-sitter-typescript 可能不识别 struct，
            # 但如果未来支持或使用兼容语法树，这里可以捕获）
            elif node.type == 'struct_declaration':
                entity_type = 'struct'
                name_node = node.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                
                # 获取装饰器
                decorators = self._get_decorators(node, content)
                
                for child in node.children:
                    if child.type in ['export', 'default', 'declare']:
                        modifiers.append(child.type)
            
            # 变量声明
            elif node.type == 'variable_declaration':
                # 修复：tree-sitter-typescript 中 variable_declaration 没有 'declarator' 字段
                # 需要遍历子节点找到 variable_declarator
                for child in node.children:
                    if child.type == 'variable_declarator':
                        name_node = child.child_by_field_name('name')
                        if name_node:
                            name = content[name_node.start_byte:name_node.end_byte]

                            # 检查是否是函数（箭头函数或函数表达式）
                            value = child.child_by_field_name('value')
                            if value and value.type in ['function_expression', 'arrow_function']:
                                entity_type = 'function'
                            else:
                                entity_type = 'variable'
                            break

                for child in node.children:
                    if child.type == 'export':
                        modifiers.append(child.type)
                    if child.type in ['const', 'let', 'var']:
                        modifiers.append(child.type)
            
            # 创建实体
            if entity_type and name:
                code_snippet = '\n'.join(lines[start_line-1:end_line])
                signature = self._extract_signature(node, content)
                
                entity = CodeEntity(
                    file_path=file_path,
                    entity_type=entity_type,
                    name=name,
                    signature=signature,
                    start_line=start_line,
                    end_line=end_line,
                    code_snippet=code_snippet,
                    modifiers=modifiers,
                    parent_name=parent_name,
                    decorators=decorators
                )
                entities.append(entity)
                
                # 递归处理子节点，传递父级名称
                new_parent = name if entity_type == 'class' else parent_name
                for child in node.children:
                    traverse(child, new_parent)
            else:
                for child in node.children:
                    traverse(child, parent_name)
        
        traverse(node)
        return entities
    
    def _get_decorators(self, node: Any, content: str) -> List[str]:
        """获取装饰器列表"""
        decorators = []
        for child in node.children:
            if child.type == 'decorator':
                decorator_text = content[child.start_byte:child.end_byte]
                decorators.append(decorator_text)
        return decorators
    
    def _extract_signature(self, node: Any, content: str) -> str:
        """提取函数/方法签名"""
        signature_parts = []
        
        # 获取参数
        params = node.child_by_field_name('parameters')
        if params:
            params_text = content[params.start_byte:params.end_byte]
            signature_parts.append(params_text)
        
        # 获取返回类型
        return_type = node.child_by_field_name('return_type')
        if return_type:
            return_type_text = content[return_type.start_byte:return_type.end_byte]
            signature_parts.append(return_type_text)
        
        return ' '.join(signature_parts)
    
    def _extract_imports(self, node: Any, content: str, file_path: str) -> List[FileDependency]:
        """提取import依赖"""
        dependencies = []
        
        def traverse(node: Any):
            if node.type == 'import_statement':
                source = node.child_by_field_name('source')
                if source:
                    module_path = content[source.start_byte:source.end_byte].strip('"\'')
                    
                    # 解析导入的名称
                    imported_names = []
                    clause = node.child_by_field_name('clause')
                    if clause:
                        if clause.type == 'import_clause':
                            # import { a, b } from 'x'
                            for child in clause.children:
                                if child.type == 'identifier':
                                    imported_names.append(content[child.start_byte:child.end_byte])
                                elif child.type == 'named_imports':
                                    for spec in child.children:
                                        if spec.type == 'import_specifier':
                                            name = spec.child_by_field_name('name')
                                            if name:
                                                imported_names.append(content[name.start_byte:name.end_byte])
                        elif clause.type == 'identifier':
                            # import x from 'x'
                            imported_names.append(content[clause.start_byte:clause.end_byte])
                    
                    # 解析目标文件路径
                    target_file = self._resolve_module_path(module_path, file_path)
                    if target_file:
                        dep = FileDependency(
                            source_file=file_path,
                            target_file=target_file,
                            dependency_type='import',
                            imported_names=imported_names
                        )
                        dependencies.append(dep)
            
            for child in node.children:
                traverse(child)
        
        traverse(node)
        return dependencies
    
    def _resolve_module_path(self, module_path: str, current_file: str) -> Optional[str]:
        """解析模块路径为实际文件路径"""
        # 相对路径
        if module_path.startswith('.'):
            current_dir = Path(current_file).parent
            resolved = (current_dir / module_path).resolve()

            # 修复：如果module_path已有后缀，直接检查该文件
            if resolved.suffix in {'.ets', '.ts', '.js', '.tsx', '.jsx'}:
                if resolved.exists():
                    return str(resolved)
                # 修复：文件不存在时也返回解析后的路径（可能尚未创建）
                return str(resolved)
            else:
                # 尝试添加扩展名
                for ext in ['.ets', '.ts', '.tsx', '.js', '.jsx']:
                    candidate = resolved.with_suffix(ext)
                    if candidate.exists():
                        return str(candidate)

                # 尝试index文件
                for ext in ['.ets', '.ts', '.js']:
                    index_path = resolved / f'index{ext}'
                    if index_path.exists():
                        return str(index_path)

                # 修复：所有候选都不存在时，返回带 .ts 后缀的路径（最常见）
                return str(resolved.with_suffix('.ts'))

        # 第三方库或别名，无法解析为本地文件
        return None
    
    def _extract_relations(self, node: Any, content: str, file_path: str, entities: List[CodeEntity]) -> List[EntityRelation]:
        """提取实体间关系"""
        relations = []
        entity_names = {e.name: e for e in entities}
        
        def traverse(node: Any, current_entity: Optional[str] = None):
            # 函数调用
            if node.type == 'call_expression':
                func = node.child_by_field_name('function')
                if func:
                    func_name = content[func.start_byte:func.end_byte]
                    # 简化函数名（去掉命名空间）
                    simple_name = func_name.split('.')[-1]
                    
                    if current_entity and simple_name in entity_names:
                        relations.append(EntityRelation(
                            source_file=file_path,
                            source_entity=current_entity,
                            target_file=file_path,
                            target_entity=simple_name,
                            relation_type='calls'
                        ))
            
            # 继承关系
            if node.type == 'class_declaration':
                name_node = node.child_by_field_name('name')
                if name_node:
                    class_name = content[name_node.start_byte:name_node.end_byte]
                    
                    heritage = node.child_by_field_name('heritage')
                    if heritage:
                        for child in heritage.children:
                            if child.type == 'extends_clause':
                                type_node = child.child_by_field_name('type')
                                if type_node:
                                    parent_name = content[type_node.start_byte:type_node.end_byte]
                                    relations.append(EntityRelation(
                                        source_file=file_path,
                                        source_entity=class_name,
                                        target_file=file_path,
                                        target_entity=parent_name,
                                        relation_type='extends'
                                    ))
                            elif child.type == 'implements_clause':
                                for type_child in child.children:
                                    if type_child.type == 'type_identifier':
                                        interface_name = content[type_child.start_byte:type_child.end_byte]
                                        relations.append(EntityRelation(
                                            source_file=file_path,
                                            source_entity=class_name,
                                            target_file=file_path,
                                            target_entity=interface_name,
                                            relation_type='implements'
                                        ))
            
            # 确定当前实体
            new_entity = current_entity
            if node.type in ['function_declaration', 'method_definition', 'class_declaration']:
                name_node = node.child_by_field_name('name')
                if name_node:
                    new_entity = content[name_node.start_byte:name_node.end_byte]
            
            for child in node.children:
                traverse(child, new_entity)
        
        traverse(node)
        return relations
    
    def _is_import_statement(self, content: str, pos: int) -> bool:
        """检查 pos 位置是否是 import 语句的开头"""
        # 向前检查是否只有空白字符
        j = pos - 1
        while j >= 0 and content[j] in (' ', '\t'):
            j -= 1
        # 如果前面有非空白字符（不是行首），不是 import
        if j >= 0 and content[j] != '\n':
            return False
        # 检查是否以 'import' 开头
        return content[pos:pos + 6] == 'import'

    def _preprocess_for_parsing(self, content: str) -> str:
        """
        预处理代码，排除字符串和注释中的内容。

        修复 EXT-1: 将字符串（单引号、双引号、模板字符串）和注释（单行、多行）
        中的内容替换为空白字符，保留换行符以维持行号一致。

        修复 CRITICAL: 保留 import 语句中的引号和路径，确保 import 提取正常工作。

        这样可以避免字符串中的伪代码（如 "export class FakeClass {}"）被错误解析。
        """
        result = []
        i = 0
        n = len(content)

        while i < n:
            ch = content[i]

            # 修复 CRITICAL: 保留 import 语句（不预处理 import 行）
            # 检查是否在行首（允许前导空白）
            if ch == 'i' and self._is_import_statement(content, i):
                # 找到行尾，原样保留
                line_end = content.find('\n', i)
                if line_end == -1:
                    line_end = n
                result.append(content[i:line_end])
                i = line_end
                continue

            # 单行注释 //
            if ch == '/' and i + 1 < n and content[i + 1] == '/':
                # 替换到行尾
                j = i
                while j < n and content[j] != '\n':
                    result.append(' ')
                    j += 1
                if j < n:
                    result.append('\n')
                    j += 1
                i = j
                continue

            # 多行注释 /* */
            if ch == '/' and i + 1 < n and content[i + 1] == '*':
                result.append('  ')  # 替换 /*
                i += 2
                while i < n:
                    if content[i] == '*' and i + 1 < n and content[i + 1] == '/':
                        result.append('  ')  # 替换 */
                        i += 2
                        break
                    elif content[i] == '\n':
                        result.append('\n')
                    else:
                        result.append(' ')
                    i += 1
                continue

            # 单引号字符串
            if ch == "'":
                result.append(' ')  # 替换开头的 '
                i += 1
                while i < n and content[i] != "'":
                    if content[i] == '\\' and i + 1 < n:
                        # 转义字符
                        result.append('  ')
                        i += 2
                    elif content[i] == '\n':
                        result.append('\n')
                        i += 1
                    else:
                        result.append(' ')
                        i += 1
                if i < n:
                    result.append(' ')  # 替换结尾的 '
                    i += 1
                continue

            # 双引号字符串
            if ch == '"':
                result.append(' ')  # 替换开头的 "
                i += 1
                while i < n and content[i] != '"':
                    if content[i] == '\\' and i + 1 < n:
                        # 转义字符
                        result.append('  ')
                        i += 2
                    elif content[i] == '\n':
                        result.append('\n')
                        i += 1
                    else:
                        result.append(' ')
                        i += 1
                if i < n:
                    result.append(' ')  # 替换结尾的 "
                    i += 1
                continue

            # 模板字符串（反引号）
            if ch == '`':
                result.append(' ')  # 替换开头的 `
                i += 1
                while i < n and content[i] != '`':
                    if content[i] == '\\' and i + 1 < n:
                        # 转义字符
                        result.append('  ')
                        i += 2
                    elif content[i] == '\n':
                        result.append('\n')
                        i += 1
                    elif content[i] == '$' and i + 1 < n and content[i + 1] == '{':
                        # 模板插值 ${...}，保留内容（简化处理）
                        result.append('  ')
                        i += 2
                        brace_count = 1
                        while i < n and brace_count > 0:
                            if content[i] == '{':
                                brace_count += 1
                                result.append(' ')
                            elif content[i] == '}':
                                brace_count -= 1
                                result.append(' ')
                            elif content[i] == '\n':
                                result.append('\n')
                            else:
                                result.append(' ')
                            i += 1
                    else:
                        result.append(' ')
                        i += 1
                if i < n:
                    result.append(' ')  # 替换结尾的 `
                    i += 1
                continue

            # 普通字符
            result.append(ch)
            i += 1

        return ''.join(result)

    def _parse_with_regex(self, content: str, file_path: str) -> ParseResult:
        """使用正则表达式解析（回退方案）"""
        result = ParseResult()
        
        # 修复 EXT-1: 预处理代码，排除字符串和注释中的内容
        # 将字符串和注释中的内容替换为空白字符，避免伪代码被错误解析
        content_for_parsing = self._preprocess_for_parsing(content)
        
        lines = content_for_parsing.split('\n')
        # 保存原始行用于 code_snippet
        original_lines = content.split('\n')

        # 收集所有实体名称（用于后续关系分析）
        all_entity_names: set = set()

        # 提取类定义（含implements关系）
        class_pattern = re.compile(
            r'^(?P<decorators>(?:@\w+(?:\([^)]*\))?\s*)*)'
            r'(?P<modifiers>(?:(?:export|abstract|default|async|static|readonly|declare)\s+)*)?'
            r'class\s+(?P<name>\w+)'
            r'(?:\s+extends\s+(?P<extends>[\w.<>]+))?'
            r'(?:\s+implements\s+(?P<implements>[\w,\s]+))?',
            re.MULTILINE
        )

        for match in class_pattern.finditer(content_for_parsing):
            start_line = content_for_parsing[:match.start()].count('\n') + 1
            end_line = self._find_block_end(lines, start_line - 1)

            # 提取装饰器（支持 @Name 和 @Name(args) 形式）
            decorators = re.findall(r'@\w+', match.group('decorators')) if match.group('decorators') else []

            entity = CodeEntity(
                file_path=file_path,
                entity_type='class',
                name=match.group('name'),
                signature=match.group(0),
                start_line=start_line,
                end_line=end_line,
                code_snippet='\n'.join(original_lines[start_line-1:end_line]),
                modifiers=[m for m in ['export', 'abstract', 'default'] if match.group('modifiers') and m in match.group('modifiers')],
                decorators=decorators
            )
            result.entities.append(entity)
            all_entity_names.add(match.group('name'))

            # 修复：提取类中的方法（OOP 代码的核心组织单元）
            class_body = '\n'.join(lines[start_line-1:end_line])
            class_methods = self._extract_class_methods(class_body, start_line, match.group('name'), file_path)
            for method_entity in class_methods:
                if method_entity.name not in all_entity_names:
                    result.entities.append(method_entity)
                    all_entity_names.add(method_entity.name)

            # 添加继承关系
            if match.group('extends'):
                result.relations.append(EntityRelation(
                    source_file=file_path,
                    source_entity=match.group('name'),
                    target_file=file_path,
                    target_entity=match.group('extends'),
                    relation_type='extends'
                ))

            # 添加实现关系
            if match.group('implements'):
                impl_names = [n.strip() for n in match.group('implements').split(',')]
                for impl_name in impl_names:
                    if impl_name:
                        result.relations.append(EntityRelation(
                            source_file=file_path,
                            source_entity=match.group('name'),
                            target_file=file_path,
                            target_entity=impl_name,
                            relation_type='implements'
                        ))

        # 提取ArkTS struct定义（@Component struct Xxx, @Entry @Component struct Xxx 等）
        struct_pattern = re.compile(
            r'^(?P<decorators>(?:@\w+\s*)*)'
            r'(?P<modifiers>export\s+)?'
            r'struct\s+(?P<name>\w+)'
            r'(?:\s+extends\s+(?P<extends>\w+))?'
            r'(?:\s+implements\s+(?P<implements>[\w,\s]+))?',
            re.MULTILINE
        )

        for match in struct_pattern.finditer(content_for_parsing):
            name = match.group('name')
            # 避免与class重复
            if name in all_entity_names:
                continue

            start_line = content_for_parsing[:match.start()].count('\n') + 1
            end_line = self._find_block_end(lines, start_line - 1)

            # 提取装饰器
            decorators = re.findall(r'@\w+', match.group('decorators'))

            entity = CodeEntity(
                file_path=file_path,
                entity_type='class',
                name=name,
                signature=match.group(0).strip(),
                start_line=start_line,
                end_line=end_line,
                code_snippet='\n'.join(original_lines[start_line-1:end_line]),
                modifiers=['export'] if match.group('modifiers') else [],
                decorators=decorators
            )
            result.entities.append(entity)
            all_entity_names.add(name)

            # 修复：提取 struct 中的方法
            struct_body = '\n'.join(original_lines[start_line-1:end_line])
            struct_methods = self._extract_class_methods(struct_body, start_line, name, file_path)
            for method_entity in struct_methods:
                if method_entity.name not in all_entity_names:
                    result.entities.append(method_entity)
                    all_entity_names.add(method_entity.name)

            # 添加继承关系
            if match.group('extends'):
                result.relations.append(EntityRelation(
                    source_file=file_path,
                    source_entity=name,
                    target_file=file_path,
                    target_entity=match.group('extends'),
                    relation_type='extends'
                ))

            # 添加实现关系
            if match.group('implements'):
                impl_names = [n.strip() for n in match.group('implements').split(',')]
                for impl_name in impl_names:
                    if impl_name:
                        result.relations.append(EntityRelation(
                            source_file=file_path,
                            source_entity=name,
                            target_file=file_path,
                            target_entity=impl_name,
                            relation_type='implements'
                        ))

        # 提取函数定义
        func_pattern = re.compile(
            r'^(?P<modifiers>(?:(?:export|default|async|static|readonly|declare)\s+)*)?'
            r'function\s+(?P<name>\w+)\s*\(',
            re.MULTILINE
        )

        for match in func_pattern.finditer(content_for_parsing):
            start_line = content_for_parsing[:match.start()].count('\n') + 1
            end_line = self._find_block_end(lines, start_line - 1)

            entity = CodeEntity(
                file_path=file_path,
                entity_type='function',
                name=match.group('name'),
                signature=match.group(0),
                start_line=start_line,
                end_line=end_line,
                code_snippet='\n'.join(lines[start_line-1:end_line]),
                modifiers=[m for m in ['export', 'async', 'default'] if match.group('modifiers') and m in match.group('modifiers')]
            )
            result.entities.append(entity)
            all_entity_names.add(match.group('name'))

        # 提取接口定义（含extends关系）
        interface_pattern = re.compile(
            r'^(?P<modifiers>export\s+)?interface\s+(?P<name>\w+)'
            r'(?:\s*<[^>]*>)?'  # 修复：支持泛型参数 <T>
            r'(?:\s+extends\s+(?P<extends>[\w,\s]+))?',
            re.MULTILINE
        )

        for match in interface_pattern.finditer(content_for_parsing):
            start_line = content_for_parsing[:match.start()].count('\n') + 1
            end_line = self._find_block_end(lines, start_line - 1)

            entity = CodeEntity(
                file_path=file_path,
                entity_type='interface',
                name=match.group('name'),
                signature=match.group(0),
                start_line=start_line,
                end_line=end_line,
                code_snippet='\n'.join(lines[start_line-1:end_line]),
                modifiers=['export'] if match.group('modifiers') else []
            )
            result.entities.append(entity)
            all_entity_names.add(match.group('name'))

            # 添加接口继承关系
            if match.group('extends'):
                ext_names = [n.strip() for n in match.group('extends').split(',')]
                for ext_name in ext_names:
                    if ext_name:
                        result.relations.append(EntityRelation(
                            source_file=file_path,
                            source_entity=match.group('name'),
                            target_file=file_path,
                            target_entity=ext_name,
                            relation_type='extends'
                        ))

        # 提取枚举定义
        enum_pattern = re.compile(
            r'^(?P<modifiers>(?:export\s+)?(?:const\s+)?)enum\s+(?P<name>\w+)',
            re.MULTILINE
        )

        for match in enum_pattern.finditer(content_for_parsing):
            start_line = content_for_parsing[:match.start()].count('\n') + 1
            end_line = self._find_block_end(lines, start_line - 1)

            entity = CodeEntity(
                file_path=file_path,
                entity_type='enum',
                name=match.group('name'),
                signature=match.group(0),
                start_line=start_line,
                end_line=end_line,
                code_snippet='\n'.join(lines[start_line-1:end_line]),
                modifiers=[m for m in ['export', 'const'] if match.group('modifiers') and m in match.group('modifiers')]
            )
            result.entities.append(entity)
            all_entity_names.add(match.group('name'))

        # 提取类型别名
        type_alias_pattern = re.compile(
            r'^(?P<modifiers>export\s+)?type\s+(?P<name>\w+)'
            r'(?:\s*<[^>]*>)?'  # 修复：支持泛型参数 <T>, <T, U>
            r'\s*=',
            re.MULTILINE
        )

        for match in type_alias_pattern.finditer(content_for_parsing):
            start_line = content_for_parsing[:match.start()].count('\n') + 1
            # 修复：type alias 通常不使用花括号，找到包含分号的行或下一行
            # type Foo = string | number;
            # type Bar = { x: number; y: number };  (有花括号的情况)
            end_line = self._find_type_alias_end(lines, start_line - 1)

            entity = CodeEntity(
                file_path=file_path,
                entity_type='type_alias',
                name=match.group('name'),
                signature=match.group(0),
                start_line=start_line,
                end_line=end_line,
                code_snippet='\n'.join(original_lines[start_line-1:end_line]),
                modifiers=['export'] if match.group('modifiers') else []
            )
            result.entities.append(entity)
            all_entity_names.add(match.group('name'))

        # 提取解构导出 (export const { a, b } = obj;)
        destructure_pattern = re.compile(
            r'^(?P<modifiers>export\s+)?(?:const|let|var)\s+\{(?P<names>[^}]+)\}\s*=\s*(?P<source>.+?)\s*;',
            re.MULTILINE
        )

        for match in destructure_pattern.finditer(content_for_parsing):
            names_str = match.group('names')
            destructure_names = [n.strip() for n in names_str.split(',') if n.strip()]
            start_line = content_for_parsing[:match.start()].count('\n') + 1
            for dname in destructure_names:
                if dname not in all_entity_names:
                    entity = CodeEntity(
                        file_path=file_path,
                        entity_type='variable',
                        name=dname,
                        signature=match.group(0).strip(),
                        start_line=start_line,
                        end_line=start_line,
                        code_snippet=match.group(0).strip(),
                        modifiers=['export'] if match.group('modifiers') else []
                    )
                    result.entities.append(entity)
                    all_entity_names.add(dname)

        # 提取变量声明（const/let/var，含箭头函数）
        var_pattern = re.compile(
            r'^(?P<modifiers>export\s+)?(?:const|let|var)\s+(?P<name>\w+)\s*'
            r'(?::\s*[^=]+?)?\s*=\s*(?P<value>.+?)\s*;',
            re.MULTILINE
        )

        for match in var_pattern.finditer(content_for_parsing):
            name = match.group('name')
            if name in all_entity_names:
                continue
            value = match.group('value') or ''
            start_line = content_for_parsing[:match.start()].count('\n') + 1

            # 判断是否是箭头函数
            if '=>' in value:
                entity_type = 'function'
            else:
                entity_type = 'variable'

            entity = CodeEntity(
                file_path=file_path,
                entity_type=entity_type,
                name=name,
                signature=match.group(0).strip(),
                start_line=start_line,
                end_line=start_line,
                code_snippet=match.group(0).strip(),
                modifiers=['export'] if match.group('modifiers') else []
            )
            result.entities.append(entity)
            all_entity_names.add(name)

        # 提取import（支持多种import语法）
        import_patterns = [
            # import { Foo, Bar } from './module'
            re.compile(
                r'^import\s+(?P<type_keyword>type\s+)?(?P<names>\{[^}]+\})\s*from\s+[\'"](?P<path>[^\'"]+)[\'"]',
                re.MULTILINE
            ),
            # import Default from './module'
            re.compile(
                r'^import\s+(?P<type_keyword>type\s+)?(?P<default>\w+)\s+from\s+[\'"](?P<path>[^\'"]+)[\'"]',
                re.MULTILINE
            ),
            # import * as alias from './module'
            re.compile(
                r'^import\s+(?P<type_keyword>type\s+)?\*\s+as\s+(?P<default>\w+)\s+from\s+[\'"](?P<path>[^\'"]+)[\'"]',
                re.MULTILINE
            ),
            # import './module' (副作用导入)
            re.compile(
                r'^import\s+[\'"](?P<path>[^\'"]+)[\'"]',
                re.MULTILINE
            ),
        ]

        for pattern in import_patterns:
            for match in pattern.finditer(content_for_parsing):
                module_path = match.group('path')
                imported_names = []

                names_group = match.groupdict().get('names')
                default_group = match.groupdict().get('default')

                if names_group:
                    imported_names = [n.strip() for n in names_group[1:-1].split(',')]
                elif default_group:
                    imported_names = [default_group]

                target_file = self._resolve_module_path(module_path, file_path)
                if target_file:
                    result.dependencies.append(FileDependency(
                        source_file=file_path,
                        target_file=target_file,
                        dependency_type='import',
                        imported_names=imported_names
                    ))

        # 提取函数调用关系（calls）
        # 匹配 entity_name.method() 或 entity_name() 形式的调用
        # 排除 new 关键字后的实例化（new Foo() 不是函数调用）
        call_pattern = re.compile(
            r'(?<!\w)'  # 确保前面不是单词字符（避免匹配定义）
            r'(?<!new\s)'  # 排除 new 关键字后的实例化
            r'(?P<called>\w+)'  # 被调用的名称
            r'\s*\(',  # 左括号
        )
        
        # 收集当前文件中所有已定义实体的名称和定义位置
        defined_names = {e.name for e in result.entities}
        # 收集所有定义行的行号，用于排除定义本身
        definition_lines = set()
        for entity in result.entities:
            definition_lines.add(entity.start_line)
        
        for match in call_pattern.finditer(content_for_parsing):
            called_name = match.group('called')
            # 只记录对已知实体的调用（避免噪声）
            if called_name in defined_names:
                # 跳过语言关键字
                if called_name in ('if', 'for', 'while', 'switch', 'catch', 'return', 'throw', 'new', 'typeof', 'instanceof'):
                    continue
                # 确定调用位置
                call_line = content_for_parsing[:match.start()].count('\n') + 1
                # 排除定义行本身（class Foo { ... } 中的Foo不是调用）
                if call_line in definition_lines:
                    continue
                # 找到包含此调用的实体（选择最内层/最小范围的实体）
                caller_entity = None
                caller_size = float('inf')
                for entity in result.entities:
                    if entity.start_line <= call_line <= entity.end_line:
                        entity_size = entity.end_line - entity.start_line
                        if entity_size < caller_size:
                            caller_entity = entity
                            caller_size = entity_size
                if caller_entity and caller_entity.name != called_name:
                    result.relations.append(EntityRelation(
                        source_file=file_path,
                        source_entity=caller_entity.name,
                        target_file=file_path,
                        target_entity=called_name,
                        relation_type='calls'
                    ))

        return result
    
    def _extract_class_methods(self, class_body: str, class_start_line: int,
                                class_name: str, file_path: str) -> List[CodeEntity]:
        """
        提取类/struct 中的方法定义。

        修复：正则回退方案此前不提取类方法，导致 OOP 代码中最重要的
        代码组织单元（方法）完全丢失。

        支持的方法语法：
        - public/private/protected/static/async/get/set 修饰符
        - 可选参数列表和返回类型
        - 箭头函数属性: methodName = () => { }
        """
        methods = []
        body_lines = class_body.split('\n')

        # 方法模式：修饰符 + 方法名 + 参数列表
        method_pattern = re.compile(
            r'^\s*'
            r'(?P<modifiers>(?:(?:public|private|protected|static|async|readonly|abstract|override|get|set)\s+)*)'
            r'(?P<name>\w+)\s*'
            r'(?P<params>\([^()]*(?:\([^()]*\)[^()]*)*\))'  # 修复：支持一层嵌套括号
            r'(?:\s*:\s*(?P<return_type>[^{=]+?))?'  # 返回类型
            r'\s*\{',
            re.MULTILINE
        )

        # 箭头函数属性模式：methodName = () => { }
        # 修复：参数列表支持嵌套括号 (x: (a: number) => void)
        arrow_method_pattern = re.compile(
            r'^\s*'
            r'(?P<modifiers>(?:(?:public|private|protected|static|async|readonly|abstract|override)\s+)*)'
            r'(?P<name>\w+)\s*=\s*'
            r'(?P<params>\([^()]*(?:\([^()]*\)[^()]*)*\))'  # 支持一层嵌套括号
            r'(?:\s*:\s*[^{=]+?)?'  # 返回类型（可选）
            r'\s*=>\s*\{',
            re.MULTILINE
        )

        for match in method_pattern.finditer(class_body):
            method_name = match.group('name')
            # 跳过构造函数（constructor 是特殊方法，保留为 function 类型）
            if method_name == 'constructor':
                continue
            # 跳过 if/for/while/switch/catch 等关键字
            if method_name in ('if', 'for', 'while', 'switch', 'catch', 'return', 'throw', 'new', 'typeof', 'instanceof'):
                continue

            # 计算方法在文件中的行号
            method_start_in_body = class_body[:match.start()].count('\n')
            method_start_line = class_start_line + method_start_in_body
            method_end_line = self._find_block_end(body_lines, method_start_in_body)
            method_end_line = class_start_line + method_end_line - 1  # 转换为文件行号

            # 提取修饰符
            modifiers_str = match.group('modifiers') or ''
            modifiers = [m for m in modifiers_str.split() if m]

            code_snippet = match.group(0)
            # 尝试获取完整方法体
            if method_end_line > method_start_line:
                snippet_lines = body_lines[method_start_in_body:min(method_end_line - class_start_line + 1, len(body_lines))]
                code_snippet = '\n'.join(snippet_lines)

            method_entity = CodeEntity(
                file_path=file_path,
                entity_type='function',
                name=method_name,
                signature=match.group('params'),
                start_line=method_start_line,
                end_line=method_end_line,
                code_snippet=code_snippet,
                modifiers=modifiers,
                parent_name=class_name,
            )
            methods.append(method_entity)

        # 箭头函数属性
        for match in arrow_method_pattern.finditer(class_body):
            method_name = match.group('name')
            if method_name in ('if', 'for', 'while', 'switch', 'catch', 'constructor'):
                continue

            method_start_in_body = class_body[:match.start()].count('\n')
            method_start_line = class_start_line + method_start_in_body
            method_end_line = self._find_block_end(body_lines, method_start_in_body)
            method_end_line = class_start_line + method_end_line - 1

            modifiers_str = match.group('modifiers') or ''
            modifiers = [m for m in modifiers_str.split() if m]

            code_snippet = match.group(0)
            if method_end_line > method_start_line:
                snippet_lines = body_lines[method_start_in_body:min(method_end_line - class_start_line + 1, len(body_lines))]
                code_snippet = '\n'.join(snippet_lines)

            method_entity = CodeEntity(
                file_path=file_path,
                entity_type='function',
                name=method_name,
                signature=match.group('params'),
                start_line=method_start_line,
                end_line=method_end_line,
                code_snippet=code_snippet,
                modifiers=modifiers,
                parent_name=class_name,
            )
            methods.append(method_entity)

        return methods

    def _find_type_alias_end(self, lines: List[str], start_idx: int) -> int:
        """
        找到 type alias 的结束行。

        type alias 有两种形式：
        1. type Foo = string | number;  (单行，到分号结束)
        2. type Bar = { x: number; y: number };  (多行对象类型，到 }; 结束)
        """
        if start_idx >= len(lines):
            return start_idx + 1

        brace_count = 0
        for i in range(start_idx, len(lines)):
            line = lines[i]
            for ch in line:
                if ch == '{':
                    brace_count += 1
                elif ch == '}':
                    brace_count -= 1
            # 找到分号且花括号已平衡
            if ';' in line and brace_count <= 0:
                return i + 1

        return len(lines)

    def _find_block_end(self, lines: List[str], start_idx: int) -> int:
        """
        找到代码块的结束行（基于花括号计数）。

        修复：原实现基于缩进判断，对花括号不换行的代码（如 class Foo { method() {} }）
        和嵌套结构会返回错误结果。现在使用花括号计数，正确处理：
        - 花括号在同一行: class Foo { bar() {} }
        - 嵌套结构: if (...) { for (...) { } }
        - 字符串和注释中的花括号（简化处理）
        """
        if start_idx >= len(lines):
            return start_idx + 1

        brace_count = 0
        found_open = False
        in_single_quote = False
        in_double_quote = False
        in_template = False
        in_line_comment = False
        in_block_comment = False

        for i in range(start_idx, len(lines)):
            line = lines[i]
            j = 0
            while j < len(line):
                ch = line[j]

                # 处理行注释
                if in_line_comment:
                    break  # 行注释剩余部分全部忽略

                # 处理块注释
                if in_block_comment:
                    if ch == '*' and j + 1 < len(line) and line[j + 1] == '/':
                        in_block_comment = False
                        j += 2
                        continue
                    j += 1
                    continue

                # 检测注释开始
                if ch == '/' and j + 1 < len(line):
                    if line[j + 1] == '/':
                        in_line_comment = True
                        break
                    elif line[j + 1] == '*':
                        in_block_comment = True
                        j += 2
                        continue

                # 处理字符串（简化：不处理转义引号）
                if ch == "'" and not in_double_quote and not in_template:
                    in_single_quote = not in_single_quote
                elif ch == '"' and not in_single_quote and not in_template:
                    in_double_quote = not in_double_quote
                elif ch == '`' and not in_single_quote and not in_double_quote:
                    in_template = not in_template

                # 只在非字符串/注释状态下计数花括号
                if not in_single_quote and not in_double_quote and not in_template:
                    if ch == '{':
                        brace_count += 1
                        found_open = True
                    elif ch == '}':
                        brace_count -= 1
                        if found_open and brace_count == 0:
                            return i + 1  # 返回下一行（1-based）

                j += 1

        # 花括号未闭合，返回文件末尾
        return len(lines)


# 简单测试
if __name__ == '__main__':
    test_code = '''
import { UserService } from './services';
import utils from '../utils';

export class UserComponent {
    private userService: UserService;
    
    constructor() {
        this.userService = new UserService();
    }
    
    async getUserInfo(userId: string): Promise<UserInfo> {
        return this.userService.fetchUser(userId);
    }
}

export interface UserInfo {
    id: string;
    name: string;
}

function helperFunction() {
    return 'helper';
}
'''
    
    parser = ArkTSParser()
    result = parser.parse(test_code, '/test/file.ts')
    
    print("=== 解析结果 ===")
    print(f"\n实体数量: {len(result.entities)}")
    for entity in result.entities:
        print(f"  - {entity.entity_type}: {entity.name} (行{entity.start_line}-{entity.end_line})")
        if entity.modifiers:
            print(f"    修饰符: {entity.modifiers}")
    
    print(f"\n关系数量: {len(result.relations)}")
    for rel in result.relations:
        print(f"  - {rel.source_entity} --{rel.relation_type}--> {rel.target_entity}")
    
    print(f"\n依赖数量: {len(result.dependencies)}")
    for dep in result.dependencies:
        print(f"  - {dep.source_file} --> {dep.target_file}")
        print(f"    导入: {dep.imported_names}")
