"""
符号表构建器
从AST中提取符号信息，建立名称→实体的映射
"""
import logging
from typing import Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from core.parser.ast_nodes import (
    FileNode, ClassNode, MethodNode, PropertyNode,
    ImportNode, NamespaceNode, EnumMemberNode, ASTNode
)

logger = logging.getLogger(__name__)


@dataclass
class SymbolInfo:
    """符号信息"""
    name: str
    symbol_type: str  # class, method, property, function, enum, namespace, import
    node: ASTNode
    fully_qualified_name: str = ""
    file_path: str = ""


class SymbolTable:
    """
    符号表
    管理所有解析出的符号，支持按名称/类型/文件查找
    """

    def __init__(self, file_path: str = ""):
        self._file_path = file_path
        self._symbols: Dict[str, List[SymbolInfo]] = {}  # name -> symbols
        self._qualified_names: Dict[str, SymbolInfo] = {}  # fully qualified name -> symbol
        self._all_symbols: List[SymbolInfo] = []
        self._current_scope: List[str] = ["<global>"]

    def add_symbol(self, name: str, symbol_type: str, node: ASTNode) -> SymbolInfo:
        """添加符号到符号表"""
        fqn = ".".join(self._current_scope[1:] + [name]) if len(self._current_scope) > 1 else name

        info = SymbolInfo(
            name=name,
            symbol_type=symbol_type,
            node=node,
            fully_qualified_name=fqn,
            file_path=self._file_path,
        )

        if name not in self._symbols:
            self._symbols[name] = []
        self._symbols[name].append(info)
        self._qualified_names[fqn] = info
        self._all_symbols.append(info)

        return info

    def push_scope(self, scope_name: str):
        """进入新作用域"""
        self._current_scope.append(scope_name)

    def pop_scope(self):
        """退出当前作用域"""
        if len(self._current_scope) > 1:
            self._current_scope.pop()

    def lookup(self, name: str) -> List[SymbolInfo]:
        """按名称查找符号"""
        return self._symbols.get(name, [])

    def lookup_fqn(self, fqn: str) -> Optional[SymbolInfo]:
        """按全限定名查找符号"""
        return self._qualified_names.get(fqn)

    def get_symbols_by_type(self, symbol_type: str) -> List[SymbolInfo]:
        """按类型获取所有符号"""
        return [s for s in self._all_symbols if s.symbol_type == symbol_type]

    def get_all_symbols(self) -> List[SymbolInfo]:
        """获取所有符号"""
        return self._all_symbols

    def get_class_count(self) -> int:
        return len(self.get_symbols_by_type("class"))

    def get_method_count(self) -> int:
        return len(self.get_symbols_by_type("method")) + len(self.get_symbols_by_type("function"))

    def get_property_count(self) -> int:
        return len(self.get_symbols_by_type("property"))


class SymbolTableBuilder:
    """
    符号表构建器
    遍历AST，提取所有符号信息
    """

    def __init__(self, file_path: str = ""):
        self._file_path = file_path

    def build(self, file_node: FileNode) -> SymbolTable:
        """从文件AST构建符号表"""
        table = SymbolTable(self._file_path)

        # 处理导入
        for imp in file_node.imports:
            for name in imp.imported_names:
                table.add_symbol(name, "import", imp)

        # 处理顶层声明
        for child in file_node.children:
            self._process_node(child, table)

        return table

    def _process_node(self, node: ASTNode, table: SymbolTable) -> None:
        """递归处理AST节点"""
        if isinstance(node, ClassNode):
            self._process_class(node, table)
        elif isinstance(node, MethodNode):
            self._process_method(node, table)
        elif isinstance(node, PropertyNode):
            self._process_property(node, table)
        elif isinstance(node, NamespaceNode):
            self._process_namespace(node, table)
        else:
            # 递归处理子节点
            for child in node.children:
                self._process_node(child, table)

    def _process_class(self, class_node: ClassNode, table: SymbolTable) -> None:
        """处理类声明"""
        table.add_symbol(class_node.name, "class", class_node)
        table.push_scope(class_node.name)

        # 处理类成员
        for child in class_node.children:
            if isinstance(child, MethodNode):
                self._process_method(child, table)
            elif isinstance(child, PropertyNode):
                self._process_property(child, table)
            elif isinstance(child, EnumMemberNode):
                table.add_symbol(child.name, "enum_member", child)

        table.pop_scope()

    def _process_method(self, method_node: MethodNode, table: SymbolTable) -> None:
        """处理方法声明"""
        sym_type = "function" if method_node.node_type == "FunctionDeclaration" else "method"
        table.add_symbol(method_node.name, sym_type, method_node)

    def _process_property(self, prop_node: PropertyNode, table: SymbolTable) -> None:
        """处理属性声明"""
        table.add_symbol(prop_node.name, "property", prop_node)

    def _process_namespace(self, ns_node: NamespaceNode, table: SymbolTable) -> None:
        """处理命名空间"""
        table.add_symbol(ns_node.name, "namespace", ns_node)
        table.push_scope(ns_node.name)

        for child in ns_node.children:
            self._process_node(child, table)

        table.pop_scope()
