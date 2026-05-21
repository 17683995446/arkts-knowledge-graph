"""
ArkTS AST 节点定义
定义语法树中所有节点类型
"""
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any


@dataclass
class ASTNode:
    """AST 基础节点"""
    node_type: str = ""
    name: str = ""
    start_line: int = 0
    end_line: int = 0
    start_column: int = 0
    end_column: int = 0
    children: List['ASTNode'] = field(default_factory=list)
    parent: Optional['ASTNode'] = field(default=None, repr=False)
    attributes: Dict[str, Any] = field(default_factory=dict)

    def add_child(self, child: 'ASTNode') -> 'ASTNode':
        """添加子节点"""
        child.parent = self
        self.children.append(child)
        return child

    def find_children(self, node_type: str) -> List['ASTNode']:
        """查找所有指定类型的子节点"""
        result = []
        for child in self.children:
            if child.node_type == node_type:
                result.append(child)
            result.extend(child.find_children(node_type))
        return result

    def find_first(self, node_type: str) -> Optional['ASTNode']:
        """查找第一个指定类型的子节点"""
        for child in self.children:
            if child.node_type == node_type:
                return child
            found = child.find_first(node_type)
            if found:
                return found
        return None

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        result = {
            "type": self.node_type,
            "name": self.name,
            "line": self.start_line,
            "endLine": self.end_line,
        }
        if self.attributes:
            result["attrs"] = self.attributes
        if self.children:
            result["children"] = [c.to_dict() for c in self.children]
        return result


@dataclass
class FileNode(ASTNode):
    """文件节点"""
    file_path: str = ""
    imports: List['ImportNode'] = field(default_factory=list)
    language: str = "arkts"


@dataclass
class ImportNode(ASTNode):
    """导入节点"""
    import_path: str = ""
    is_default: bool = False
    imported_names: List[str] = field(default_factory=list)
    alias: str = ""


@dataclass
class ClassNode(ASTNode):
    """类/接口/结构体/枚举节点"""
    extends: List[str] = field(default_factory=list)
    implements: List[str] = field(default_factory=list)
    type_parameters: List[str] = field(default_factory=list)
    doc_comment: str = ""
    decorators: List[str] = field(default_factory=list)
    is_interface: bool = False
    is_abstract: bool = False
    is_enum: bool = False
    is_struct: bool = False
    is_exported: bool = False


@dataclass
class MethodNode(ASTNode):
    """方法/函数节点"""
    return_type: str = ""
    parameters: List[Dict[str, str]] = field(default_factory=list)
    doc_comment: str = ""
    decorators: List[str] = field(default_factory=list)
    is_static: bool = False
    is_async: bool = False
    is_private: bool = False
    is_protected: bool = False
    is_override: bool = False
    is_getter: bool = False
    is_setter: bool = False
    is_constructor: bool = False
    is_arrow: bool = False
    is_abstract: bool = False
    body_text: str = ""


@dataclass
class PropertyNode(ASTNode):
    """属性/字段节点"""
    type_annotation: str = ""
    default_value: str = ""
    decorators: List[str] = field(default_factory=list)
    is_static: bool = False
    is_private: bool = False
    is_readonly: bool = False
    is_state: bool = False
    is_link: bool = False
    is_prop: bool = False
    is_provide: bool = False


@dataclass
class DecoratorNode(ASTNode):
    """装饰器节点"""
    arguments: str = ""


@dataclass
class CallExpression(ASTNode):
    """函数调用表达式"""
    callee_name: str = ""
    callee_object: str = ""
    arguments: List[str] = field(default_factory=list)
    is_method_call: bool = False
    is_chained: bool = False


@dataclass
class NamespaceNode(ASTNode):
    """命名空间/模块节点"""


@dataclass
class EnumMemberNode(ASTNode):
    """枚举成员节点"""
    value: str = ""


@dataclass
class TypeAliasNode(ASTNode):
    """类型别名节点"""
    type_definition: str = ""
