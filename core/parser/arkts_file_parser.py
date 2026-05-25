"""
ArkTS 文件解析器（门面模块）
统一对外接口，组合词法分析、语法分析、符号表构建、调用提取
"""
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field, asdict
from core.parser.arkts_parser import ArkTSParser
from core.parser.symbol_table_builder import SymbolTableBuilder, SymbolTable
from core.parser.call_extractor import CallExtractor, CallRelation
from core.parser.ast_nodes import (
    FileNode, ClassNode, MethodNode, PropertyNode, ImportNode, ASTNode, NamespaceNode
)
from core.database.schema_definitions import get_flag_constants

logger = logging.getLogger(__name__)
FLAGS = get_flag_constants()


@dataclass
class ParseResult:
    """单个文件的解析结果"""
    file_path: str = ""
    file_hash: str = ""
    line_count: int = 0
    language: str = "arkts"

    # 解析出的实体
    classes: List[Dict] = field(default_factory=list)
    methods: List[Dict] = field(default_factory=list)
    properties: List[Dict] = field(default_factory=list)
    calls: List[Dict] = field(default_factory=list)
    imports: List[Dict] = field(default_factory=list)
    decorators: List[Dict] = field(default_factory=list)
    inheritance: List[Dict] = field(default_factory=list)
    namespaces: List[Dict] = field(default_factory=list)

    # 统计
    parse_time_ms: float = 0
    error: str = ""

    def to_dict(self) -> Dict:
        return asdict(self)


class ArkTSFileParser:
    """
    ArkTS 文件解析器
    对外提供统一的文件解析接口
    """

    def __init__(self):
        pass

    def parse_file(self, file_path: str, source_code: str) -> ParseResult:
        """
        解析单个ArkTS文件
        Args:
            file_path: 文件路径
            source_code: 源代码文本
        Returns:
            ParseResult 包含所有解析出的实体
        """
        import time
        start_time = time.time()

        result = ParseResult(
            file_path=file_path,
            file_hash=self._compute_hash(source_code),
            line_count=source_code.count('\n') + 1,
        )

        try:
            # 1. 语法分析 → AST
            parser = ArkTSParser(source_code, file_path)
            file_node = parser.parse()

            # 符号表构建已跳过（当前未使用，节省性能开销）

            # 3. 提取实体
            result.classes = self._extract_classes(file_node, file_path)
            result.methods = self._extract_methods(file_node, file_path)
            result.properties = self._extract_properties(file_node, file_path)
            result.namespaces = self._extract_namespaces(file_node, file_path)

            # 4. 提取调用关系
            source_lines = source_code.split('\n')
            call_extractor = CallExtractor(source_lines)
            call_relations = call_extractor.extract_calls(file_node)
            result.calls = [self._call_to_dict(cr) for cr in call_relations]

            # 5. 提取导入
            result.imports = self._extract_imports(file_node)

            # 6. 提取装饰器
            result.decorators = self._extract_decorators(file_node)

            # 7. 提取继承关系
            result.inheritance = self._extract_inheritance(file_node)

        except Exception as e:
            result.error = str(e)
            logger.error(f"解析文件失败 {file_path}: {e}")

        result.parse_time_ms = (time.time() - start_time) * 1000
        return result

    def _compute_hash(self, content: str) -> bytes:
        """计算文件内容的SHA256哈希（返回bytes）"""
        # 修复X: 返回bytes类型，与数据库BLOB字段匹配
        return hashlib.sha256(content.encode('utf-8')).digest()

    def _extract_classes(self, file_node: FileNode, file_path: str) -> List[Dict]:
        """提取所有类/接口/枚举（包括命名空间内的）"""
        classes = []
        self._collect_classes(file_node, file_path, classes)
        return classes

    def _collect_classes(self, node: ASTNode, file_path: str, classes: List[Dict]):
        """递归收集类/接口/枚举"""
        for child in node.children:
            if isinstance(child, ClassNode):
                flags = 0
                if child.is_interface:
                    flags |= FLAGS["CLASS_IS_INTERFACE"]
                if child.is_abstract:
                    flags |= FLAGS["CLASS_IS_ABSTRACT"]
                if child.is_enum:
                    flags |= FLAGS["CLASS_IS_ENUM"]
                if child.is_struct:
                    flags |= FLAGS["CLASS_IS_STRUCT"]
                if child.is_exported:
                    flags |= FLAGS["CLASS_IS_EXPORTED"]
                if "Entry" in child.decorators:
                    flags |= FLAGS["CLASS_IS_ENTRY"]

                classes.append({
                    "name": child.name,
                    "file_path": file_path,
                    "start_line": child.start_line,
                    "end_line": child.end_line,
                    "flags": flags,
                    "doc_comment": child.doc_comment,
                    "decorators": child.decorators,
                    "extends": child.extends,
                    "implements": child.implements,
                })
                # 递归进入类的子节点（如嵌套类）
                self._collect_classes(child, file_path, classes)
            else:
                # 递归进入非类节点（如命名空间）查找类
                self._collect_classes(child, file_path, classes)

    def _extract_methods(self, file_node: FileNode, file_path: str) -> List[Dict]:
        """提取所有方法/函数"""
        methods = []
        self._collect_methods(file_node, file_path, "", methods)
        return methods

    def _collect_methods(self, node: ASTNode, file_path: str,
                          class_name: str, methods: List[Dict]):
        """递归收集方法"""
        if isinstance(node, ClassNode):
            for child in node.children:
                if isinstance(child, MethodNode):
                    flags = 0
                    if child.is_static:
                        flags |= FLAGS["METHOD_IS_STATIC"]
                    if child.is_async:
                        flags |= FLAGS["METHOD_IS_ASYNC"]
                    if child.is_private:
                        flags |= FLAGS["METHOD_IS_PRIVATE"]
                    if child.is_protected:
                        flags |= FLAGS["METHOD_IS_PROTECTED"]
                    if child.is_override:
                        flags |= FLAGS["METHOD_IS_OVERRIDE"]
                    if child.is_getter:
                        flags |= FLAGS["METHOD_IS_GETTER"]
                    if child.is_setter:
                        flags |= FLAGS["METHOD_IS_SETTER"]
                    if child.is_constructor:
                        flags |= FLAGS["METHOD_IS_CONSTRUCTOR"]

                    # ArkUI 生命周期方法
                    lifecycle_methods = {
                        "aboutToAppear", "aboutToDisappear",
                        "onPageShow", "onPageHide", "onBackPress",
                        "onWindowStageCreate", "onWindowStageDestroy",
                        "onForeground", "onBackground",
                        "onCreate", "onDestroy", "onRequest",
                    }
                    if child.name in lifecycle_methods:
                        flags |= FLAGS["METHOD_IS_LIFECYCLE"]

                    params_str = ", ".join(
                        f"{p.get('name', '')}: {p.get('type', '')}"
                        for p in child.parameters
                    )

                    methods.append({
                        "name": child.name,
                        "class_name": node.name,
                        "file_path": file_path,
                        "start_line": child.start_line,
                        "end_line": child.end_line,
                        "flags": flags,
                        "return_type": child.return_type,
                        "parameters": params_str,
                        "doc_comment": child.doc_comment,
                        "decorators": child.decorators,
                    })

                elif isinstance(child, ClassNode):
                    self._collect_methods(child, file_path, child.name, methods)

        elif isinstance(node, MethodNode):
            # 顶层函数
            flags = 0
            if node.is_async:
                flags |= FLAGS["METHOD_IS_ASYNC"]
            methods.append({
                "name": node.name,
                "class_name": "",
                "file_path": file_path,
                "start_line": node.start_line,
                "end_line": node.end_line,
                "flags": flags,
                "return_type": node.return_type,
                "parameters": ", ".join(
                    f"{p.get('name', '')}: {p.get('type', '')}"
                    for p in node.parameters
                ),
                "doc_comment": node.doc_comment,
                "decorators": node.decorators,
            })

        else:
            for child in node.children:
                self._collect_methods(child, file_path, class_name, methods)

    def _extract_properties(self, file_node: FileNode, file_path: str) -> List[Dict]:
        """提取所有属性"""
        properties = []
        self._collect_properties(file_node, file_path, "", properties)
        return properties

    def _collect_properties(self, node: ASTNode, file_path: str,
                             class_name: str, properties: List[Dict]):
        """递归收集属性"""
        if isinstance(node, ClassNode):
            for child in node.children:
                if isinstance(child, PropertyNode):
                    flags = 0
                    if child.is_static:
                        flags |= FLAGS["PROP_IS_STATIC"]
                    if child.is_private:
                        flags |= FLAGS["PROP_IS_PRIVATE"]
                    if child.is_readonly:
                        flags |= FLAGS["PROP_IS_READONLY"]
                    if child.is_state:
                        flags |= FLAGS["PROP_IS_STATE"]
                    if child.is_link:
                        flags |= FLAGS["PROP_IS_LINK"]
                    if child.is_prop:
                        flags |= FLAGS["PROP_IS_PROP"]
                    if child.is_provide:
                        flags |= FLAGS["PROP_IS_PROVIDE"]

                    properties.append({
                        "name": child.name,
                        "class_name": node.name,
                        "file_path": file_path,
                        "type_annotation": child.type_annotation,
                        "flags": flags,
                        "default_value": child.default_value,
                        "start_line": child.start_line,
                        "decorators": child.decorators,
                    })

                elif isinstance(child, ClassNode):
                    self._collect_properties(child, file_path, child.name, properties)

        else:
            for child in node.children:
                self._collect_properties(child, file_path, class_name, properties)

    def _extract_namespaces(self, file_node: FileNode, file_path: str) -> List[Dict]:
        """提取命名空间"""
        namespaces = []
        for child in file_node.children:
            if isinstance(child, NamespaceNode):
                namespaces.append({
                    "name": getattr(child, 'name', ''),
                    "file_path": file_path,
                    "start_line": getattr(child, 'start_line', 0),
                    "end_line": getattr(child, 'end_line', 0),
                })
        return namespaces

    def _extract_imports(self, file_node: FileNode) -> List[Dict]:
        """提取导入关系"""
        imports = []
        for imp in file_node.imports:
            imports.append({
                "file_path": file_node.file_path,
                "import_path": imp.import_path,
                "is_default": imp.is_default,
                "imported_names": imp.imported_names,
                "start_line": imp.start_line,
            })
        return imports

    def _extract_decorators(self, file_node: FileNode) -> List[Dict]:
        """提取装饰器信息"""
        decorators = []
        self._collect_decorators(file_node, decorators)
        return decorators

    def _collect_decorators(self, node: ASTNode, decorators: List[Dict]) -> None:
        """递归收集装饰器"""
        if isinstance(node, ClassNode):
            for dec_name in node.decorators:
                decorators.append({
                    "name": dec_name,
                    "target_type": 0,  # class
                    "target_name": node.name,
                    "file_path": node.file_path if hasattr(node, 'file_path') else "",
                })
            for sub in node.children:
                if isinstance(sub, (MethodNode, PropertyNode)):
                    target_type = 1 if isinstance(sub, MethodNode) else 2
                    for dec_name in sub.decorators:
                        decorators.append({
                            "name": dec_name,
                            "target_type": target_type,
                            "target_name": sub.name,
                            "file_path": node.file_path if hasattr(node, 'file_path') else "",
                        })
                elif isinstance(sub, ClassNode):
                    # 递归处理嵌套类
                    self._collect_decorators(sub, decorators)
        else:
            for child in node.children:
                if isinstance(child, ClassNode):
                    self._collect_decorators(child, decorators)

    def _extract_inheritance(self, file_node: FileNode) -> List[Dict]:
        """提取继承关系"""
        inheritance = []
        for child in file_node.children:
            if isinstance(child, ClassNode):
                for parent in child.extends:
                    inheritance.append({
                        "child_name": child.name,
                        "parent_name": parent,
                        "type": 0,  # extends
                        "file_path": file_node.file_path,
                    })
                for parent in child.implements:
                    inheritance.append({
                        "child_name": child.name,
                        "parent_name": parent,
                        "type": 1,  # implements
                        "file_path": file_node.file_path,
                    })
        return inheritance

    def _call_to_dict(self, call: CallRelation) -> Dict:
        """将CallRelation转换为字典"""
        return {
            "caller_name": call.caller_name,
            "callee_name": call.callee_name,
            "caller_class": call.caller_class,
            "callee_class": call.callee_class,
            "callee_object": call.callee_object,
            "line_number": call.line_number,
            "call_type": call.call_type,
        }
