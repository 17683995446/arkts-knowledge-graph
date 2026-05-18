"""
调用关系提取器
从源代码中提取函数/方法调用关系
"""
import re
import logging
from dataclasses import dataclass
from typing import List, Dict, Tuple, Set, Optional
from core.parser.ast_nodes import (
    FileNode, ClassNode, MethodNode, PropertyNode, ASTNode
)

logger = logging.getLogger(__name__)


@dataclass
class CallRelation:
    """调用关系"""
    caller_name: str
    callee_name: str
    caller_class: str = ""
    callee_class: str = ""
    callee_object: str = ""  # 调用目标对象 (this.xxx 中的 this)
    line_number: int = 0
    call_type: int = 0  # 0=direct, 1=method, 2=callback, 3=event


class CallExtractor:
    """
    调用关系提取器
    从源代码文本中提取函数调用关系
    使用正则表达式匹配调用模式
    """

    # 调用模式正则
    PATTERNS = {
        # this.method()
        "this_method": re.compile(r'\bthis\.(\w+)\s*\(', re.MULTILINE),
        # object.method()
        "object_method": re.compile(r'(\w+)\.(\w+)\s*\(', re.MULTILINE),
        # 直接函数调用()
        "direct_call": re.compile(r'\b(\w+)\s*\(', re.MULTILINE),
        # new ClassName()
        "new_call": re.compile(r'\bnew\s+(\w+)\s*\(', re.MULTILINE),
        # callback: .then(() => {}), .catch(), .subscribe()
        "callback": re.compile(r'\.(then|catch|finally|subscribe|onSuccess|onError|onComplete)\s*\(', re.MULTILINE),
        # event handler: onClick, onChange 等
        "event_handler": re.compile(r'\b(on\w+|handle\w+)\s*[=(]', re.MULTILINE),
        # 链式调用: a.b().c()
        "chain_call": re.compile(r'(\w+(?:\.\w+)+)\s*\(', re.MULTILINE),
        # ArkUI 特有: router.pushUrl, promptAction, etc.
        "api_call": re.compile(r'(\w+(?:\.\w+)*)\s*\(', re.MULTILINE),
    }

    # 排除的关键字（不是函数调用）
    EXCLUDED_KEYWORDS = {
        "if", "else", "for", "while", "do", "switch", "case", "return",
        "function", "class", "interface", "enum", "type", "import", "export",
        "new", "delete", "typeof", "instanceof", "void", "throw", "try",
        "catch", "finally", "const", "let", "var", "extends", "implements",
        "public", "private", "protected", "static", "readonly", "abstract",
        "async", "await", "of", "in", "true", "false", "null", "undefined",
        "super", "this", "yield", "from", "as", "default",
    }

    def __init__(self, source_lines: List[str]):
        self._source_lines = source_lines
        self._source_text = "\n".join(source_lines)

    def extract_calls(self, file_node: FileNode) -> List[CallRelation]:
        """从整个文件中提取调用关系"""
        calls = []

        # 遍历所有类
        for child in file_node.children:
            if isinstance(child, ClassNode):
                class_calls = self._extract_class_calls(child)
                calls.extend(class_calls)

            # 顶层函数
            elif isinstance(child, MethodNode):
                method_calls = self._extract_method_calls(child, class_name="")
                calls.extend(method_calls)

        return calls

    def _extract_class_calls(self, class_node: ClassNode) -> List[CallRelation]:
        """提取类中所有方法的调用关系"""
        calls = []
        class_name = class_node.name

        for child in class_node.children:
            if isinstance(child, MethodNode):
                method_calls = self._extract_method_calls(child, class_name)
                calls.extend(method_calls)

        return calls

    def _extract_method_calls(self, method_node: MethodNode,
                               class_name: str = "") -> List[CallRelation]:
        """提取单个方法中的调用关系"""
        calls = []
        caller_name = method_node.name

        # 获取方法体文本
        start = max(0, method_node.start_line - 1)
        end = min(len(self._source_lines), method_node.end_line)
        body_lines = self._source_lines[start:end]
        body_text = "\n".join(body_lines)

        # 提取各种调用模式
        callees = self._extract_callees_from_text(body_text, start + 1)

        for callee_info in callees:
            calls.append(CallRelation(
                caller_name=caller_name,
                callee_name=callee_info["name"],
                caller_class=class_name,
                callee_class=callee_info.get("object", ""),
                callee_object=callee_info.get("object", ""),
                line_number=callee_info.get("line", 0),
                call_type=callee_info.get("type", 0),
            ))

        return calls

    def _extract_callees_from_text(self, text: str, base_line: int) -> List[Dict]:
        """从文本中提取被调用函数"""
        callees = []
        seen = set()

        # this.method() 模式
        for match in self.PATTERNS["this_method"].finditer(text):
            name = match.group(1)
            if name not in self.EXCLUDED_KEYWORDS and name not in seen:
                line = text[:match.start()].count('\n') + base_line
                callees.append({"name": name, "object": "this", "line": line, "type": 1})
                seen.add(name)

        # object.method() 模式
        for match in self.PATTERNS["object_method"].finditer(text):
            obj = match.group(1)
            name = match.group(2)
            if (obj != "this" and name not in self.EXCLUDED_KEYWORDS
                    and f"{obj}.{name}" not in seen):
                line = text[:match.start()].count('\n') + base_line
                callees.append({"name": name, "object": obj, "line": line, "type": 1})
                seen.add(f"{obj}.{name}")

        # 直接函数调用
        for match in self.PATTERNS["direct_call"].finditer(text):
            name = match.group(1)
            if (name not in self.EXCLUDED_KEYWORDS and name not in seen
                    and not name[0].isupper()):  # 排除大写开头（可能是类名）
                line = text[:match.start()].count('\n') + base_line
                callees.append({"name": name, "object": "", "line": line, "type": 0})
                seen.add(name)

        # new ClassName()
        for match in self.PATTERNS["new_call"].finditer(text):
            name = match.group(1)
            if name not in seen:
                line = text[:match.start()].count('\n') + base_line
                callees.append({"name": name, "object": "", "line": line, "type": 0})
                seen.add(name)

        return callees


class ComponentRelationExtractor:
    """
    组件关系提取器
    提取 ArkUI 组件层级关系（@Component 嵌套）
    """

    # ArkUI 内置组件
    ARKUI_COMPONENTS = {
        "Column", "Row", "Stack", "List", "Grid", "Scroll", "Swiper",
        "Tabs", "TabContent", "Navigation", "NavDestination",
        "Text", "Button", "Image", "TextInput", "TextArea",
        "Select", "Slider", "Toggle", "Checkbox", "Radio",
        "Blank", "Divider", "Progress", "Rating", "Marquee",
        "Badge", "LoadingProgress", "Gauge", "QRCode",
        "Web", "Video", "XComponent", "Canvas",
        "AlertDialog", "ActionSheet", "CustomDialog",
        "Panel", "Popup", "Toast", "PromptAction",
        "If", "ForEach", "LazyForEach", "Repeat",
        "ListItem", "ListItemGroup", "GridItem", "GridColumn",
        "RowSplit", "ColumnSplit", "Flex", "RelativeContainer",
        "WaterFlow", "FlowItem",
    }

    def extract_component_relations(self, file_node: FileNode) -> List[Dict]:
        """提取组件关系"""
        relations = []

        for child in file_node.children:
            if isinstance(child, ClassNode):
                self._extract_from_class(child, relations)

        return relations

    def _extract_from_class(self, class_node: ClassNode, relations: List[Dict]):
        """从类中提取组件关系"""
        # 检查是否是 @Component
        is_component = "Component" in class_node.decorators

        if is_component:
            # 查找类中使用的子组件
            for method_child in class_node.children:
                if isinstance(method_child, MethodNode) and method_child.name == "build":
                    # build 方法中使用的组件
                    pass  # 需要更深入的分析

        # 查找 @Builder 装饰的方法
        for child in class_node.children:
            if isinstance(child, MethodNode) and "Builder" in child.decorators:
                pass
