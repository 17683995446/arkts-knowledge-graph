"""
ArkTS 语法分析器
将Token流转换为AST（抽象语法树）
使用递归下降解析策略
"""
import re
import logging
from typing import List, Optional, Tuple
from core.parser.arkts_lexer import ArkTSLexer, Token, TokenType
from core.parser.ast_nodes import (
    FileNode, ImportNode, ClassNode, MethodNode, PropertyNode,
    DecoratorNode, CallExpression, NamespaceNode, EnumMemberNode,
    TypeAliasNode, ASTNode
)

logger = logging.getLogger(__name__)


class ArkTSParser:
    """
    ArkTS 语法分析器
    将Token流解析为AST
    """

    def __init__(self, source: str, file_path: str = ""):
        self._lexer = ArkTSLexer(source)
        self._tokens = self._lexer.tokenize()
        self._pos = 0
        self._file_path = file_path
        self._source_lines = source.split('\n')

    def parse(self) -> FileNode:
        """解析整个文件"""
        file_node = FileNode(
            node_type="File",
            file_path=self._file_path,
            start_line=1,
            end_line=len(self._source_lines),
        )

        while self._current().type != TokenType.EOF:
            self._skip_semicolons()

            if self._current().type == TokenType.EOF:
                break

            # 解析装饰器
            decorators = self._parse_decorators()

            # 解析导入
            if self._is_keyword("import"):
                import_node = self._parse_import()
                file_node.imports.append(import_node)
                file_node.children.append(import_node)
                continue

            # 解析导出
            is_exported = False
            if self._is_keyword("export"):
                self._advance()
                is_exported = True
                # 修复O: 跳过 export default 语法中的 default 关键字
                if self._is_keyword("default"):
                    self._advance()

            # 解析各种声明
            node = self._parse_declaration(decorators, is_exported)
            if node:
                file_node.add_child(node)

        return file_node

    def _current(self) -> Token:
        """获取当前Token"""
        if self._pos < len(self._tokens):
            return self._tokens[self._pos]
        return Token(TokenType.EOF, "", 0, 0)

    def _advance(self) -> Token:
        """前进一个Token"""
        token = self._current()
        if self._pos < len(self._tokens) - 1:
            self._pos += 1
        return token

    def _is_keyword(self, keyword: str) -> bool:
        """检查当前Token是否是指定关键字"""
        tok = self._current()
        return tok.type == TokenType.KEYWORD and tok.value == keyword

    def _is_identifier(self) -> bool:
        """检查当前Token是否是标识符"""
        return self._current().type == TokenType.IDENTIFIER

    def _is_type_name(self) -> bool:
        """检查当前Token是否可以作为类型名（标识符或可用作模块名的关键字）"""
        if self._current().type == TokenType.IDENTIFIER:
            return True
        # 某些关键字在类型路径中可用作模块名，如 module.IInterface
        if self._current().type == TokenType.KEYWORD and self._current().value in ('module', 'namespace', 'type'):
            return True
        return False

    def _is_punctuation(self, ch: str) -> bool:
        """检查当前Token是否是指定标点"""
        tok = self._current()
        if tok.type == TokenType.PUNCTUATION and tok.value == ch:
            return True
        # < 和 > 可能被识别为 OPERATOR
        if tok.type == TokenType.OPERATOR and tok.value == ch:
            return True
        return False

    def _expect_punctuation(self, ch: str) -> bool:
        """期望当前Token是指定标点"""
        if self._is_punctuation(ch):
            self._advance()
            return True
        return False

    def _skip_semicolons(self):
        """跳过分号"""
        while self._is_punctuation(';'):
            self._advance()

    def _skip_block(self) -> Tuple[int, int]:
        """跳过花括号块，返回起止行号
        
        注意：ArkTS中 } 后面可以跟 . 进行链式调用，如：
        Row() { }
          .width('100%')
          .padding({ left: 16 })
        """
        start_line = self._current().line
        if not self._is_punctuation('{'):
            return start_line, start_line
        self._advance()  # skip {
        depth = 1
        while depth > 0 and self._current().type != TokenType.EOF:
            # 修复K: 遇到 STRING token 时直接 advance 跳过
            if self._current().type == TokenType.STRING:
                self._advance()
                continue
            if self._is_punctuation('{'):
                depth += 1
            elif self._is_punctuation('}'):
                # 修复M: depth 下限保护
                if depth > 0:
                    depth -= 1
            self._advance()
        
        # 处理链式调用：.methodName(...) 或 ?.methodName(...)
        # 跳过所有 .xxx() 或 ?.xxx() 形式的链式调用
        while (self._is_punctuation('.') or
               (self._current().type == TokenType.OPERATOR and self._current().value == '?.')):
            self._advance()  # skip . or ?.
            # 跳过方法名
            if self._is_identifier():
                self._advance()
            # 跳过参数列表 (可能包含嵌套)
            if self._is_punctuation('('):
                self._advance()
                paren_depth = 1
                while paren_depth > 0 and self._current().type != TokenType.EOF:
                    if self._is_punctuation('('):
                        paren_depth += 1
                    elif self._is_punctuation(')'):
                        if paren_depth > 0:
                            paren_depth -= 1
                    elif self._is_punctuation('{'):
                        # 处理对象字面量参数
                        self._advance()
                        brace_depth = 1
                        while brace_depth > 0 and self._current().type != TokenType.EOF:
                            # 修复K: 字符串token跳过
                            if self._current().type == TokenType.STRING:
                                self._advance()
                                continue
                            if self._is_punctuation('{'):
                                brace_depth += 1
                            elif self._is_punctuation('}'):
                                # 修复L: 内层 brace_depth 循环在 depth==0 时 break
                                if brace_depth > 0:
                                    brace_depth -= 1
                                if brace_depth == 0:
                                    self._advance()
                                    break
                            self._advance()
                        continue
                    self._advance()
        
        return start_line, self._current().line

    def _parse_decorators(self) -> List[str]:
        """解析装饰器列表"""
        decorators = []
        while self._current().type == TokenType.DECORATOR:
            dec_token = self._advance()
            # 提取装饰器名称
            dec_text = dec_token.value
            name_match = re.match(r'@(\w+)', dec_text)
            if name_match:
                decorators.append(name_match.group(1))
        return decorators

    def _parse_import(self) -> ImportNode:
        """解析import语句"""
        start_tok = self._current()
        self._advance()  # skip 'import'

        # 修复N: 跳过 import type 语法中的 type 关键字
        if self._is_keyword("type"):
            self._advance()

        is_default = False
        imported_names = []
        import_path = ""

        # import Name from 'path'
        if self._is_identifier():
            imported_names.append(self._current().value)
            self._advance()
            is_default = True

        # import { A, B } from 'path'
        elif self._is_punctuation('{'):
            self._advance()
            while not self._is_punctuation('}') and self._current().type != TokenType.EOF:
                # 修复J: 允许关键字名称（如 Component, State 等），避免无限循环
                if self._is_identifier() or self._current().type == TokenType.KEYWORD:
                    imported_names.append(self._current().value)
                    self._advance()
                    # 处理 as 别名: import { D as DD }
                    if self._is_keyword("as"):
                        self._advance()  # skip 'as'
                        if self._is_identifier():
                            self._advance()  # skip alias
                elif self._is_keyword("type"):
                    # import { type Foo } 中的 type 关键字
                    self._advance()
                    if self._is_identifier():
                        imported_names.append(self._current().value)
                        self._advance()
                    if self._is_keyword("as"):
                        self._advance()
                        if self._is_identifier():
                            self._advance()
                if self._is_punctuation(','):
                    self._advance()
            self._expect_punctuation('}')

        # import * as Name from 'path'
        elif self._is_punctuation('*'):
            self._advance()
            if self._is_keyword("as"):
                self._advance()
                if self._is_identifier():
                    imported_names.append(self._current().value)
                    self._advance()

        # from 'path'
        if self._is_keyword("from"):
            self._advance()

        # 'path' or "path"
        if self._current().type == TokenType.STRING:
            import_path = self._current().value
            self._advance()

        return ImportNode(
            node_type="ImportDeclaration",
            start_line=start_tok.line,
            end_line=self._current().line,
            import_path=import_path,
            is_default=is_default,
            imported_names=imported_names,
        )

    def _parse_declaration(self, decorators: List[str], is_exported: bool) -> Optional[ASTNode]:
        """解析声明"""
        tok = self._current()

        # BUG-43修复：识别顶层 async 关键字
        is_async = False
        if self._is_keyword("async"):
            is_async = True
            self._advance()

        # abstract class/interface
        is_abstract = False
        if self._is_keyword("abstract"):
            is_abstract = True
            self._advance()

        # class/interface/struct/enum
        if self._is_keyword("class"):
            return self._parse_class_declaration(decorators, is_exported, is_abstract=is_abstract)
        elif self._is_keyword("interface"):
            return self._parse_class_declaration(decorators, is_exported, is_interface=True, is_abstract=is_abstract)
        elif self._is_keyword("struct"):
            return self._parse_class_declaration(decorators, is_exported, is_struct=True)
        elif self._is_keyword("enum"):
            return self._parse_enum_declaration(decorators, is_exported)

        # function
        elif self._is_keyword("function"):
            return self._parse_function_declaration(decorators, is_exported, is_async=is_async)

        # namespace/module
        elif self._is_keyword("namespace") or self._is_keyword("module"):
            return self._parse_namespace_declaration(decorators, is_exported)

        # type alias
        elif self._is_keyword("type"):
            return self._parse_type_alias(is_exported)

        # const/let/var (可能包含函数表达式)
        elif self._is_keyword("const") or self._is_keyword("let") or self._is_keyword("var"):
            return self._parse_variable_declaration(decorators, is_exported)

        # 跳过无法识别的Token
        self._advance()
        return None

    def _parse_class_declaration(self, decorators: List[str], is_exported: bool,
                                  is_interface: bool = False, is_struct: bool = False,
                                  is_abstract: bool = False) -> ClassNode:
        """解析类声明"""
        start_tok = self._current()
        self._advance()  # skip 'class'/'interface'/'struct'

        name = ""
        if self._is_identifier():
            name = self._current().value
            self._advance()

        # 泛型参数
        type_params = []
        if self._is_punctuation('<'):
            self._advance()
            while not self._is_punctuation('>') and self._current().type != TokenType.EOF:
                if self._is_identifier():
                    type_params.append(self._current().value)
                    self._advance()
                
                # 处理 extends 约束，如 <T extends SomeType>
                if self._is_keyword("extends"):
                    self._advance()
                    # 跳过约束类型，直到遇到 , 或 > 或 =
                    depth = 0
                    while (self._current().type != TokenType.EOF and
                           not (self._is_punctuation(',') and depth == 0) and
                           not (self._is_punctuation('>') and depth == 0) and
                           not (self._is_punctuation('=') and depth == 0)):
                        if self._is_punctuation('<') or self._is_punctuation('{') or self._is_punctuation('('):
                            depth += 1
                        elif depth > 0 and (self._is_punctuation('>') or self._is_punctuation('}') or self._is_punctuation(')')):
                            depth -= 1
                        self._advance()
                
                # 处理默认值，如 <T = string>
                if self._is_punctuation('='):
                    self._advance()
                    # 跳过默认类型，直到遇到 , 或 >
                    depth = 0
                    while (self._current().type != TokenType.EOF and
                           not (self._is_punctuation(',') and depth == 0) and
                           not (self._is_punctuation('>') and depth == 0)):
                        if self._is_punctuation('<') or self._is_punctuation('{') or self._is_punctuation('('):
                            depth += 1
                        elif depth > 0 and (self._is_punctuation('>') or self._is_punctuation('}') or self._is_punctuation(')')):
                            depth -= 1
                        self._advance()
                
                if self._is_punctuation(','):
                    self._advance()
            self._expect_punctuation('>')

        # extends
        extends_list = []
        if self._is_keyword("extends"):
            self._advance()
            while self._is_type_name():
                # BUG-M1修复：拼接点号路径，如 a.b.c.Base
                full_name = self._current().value
                self._advance()
                while self._is_punctuation('.'):
                    self._advance()  # skip .
                    if self._is_identifier():
                        full_name += '.' + self._current().value
                        self._advance()
                    else:
                        break
                extends_list.append(full_name)
                # 跳过泛型参数 <...>
                if self._is_punctuation('<'):
                    self._advance()  # skip <
                    depth = 1
                    while depth > 0 and self._current().type != TokenType.EOF:
                        if self._is_punctuation('<'):
                            depth += 1
                            self._advance()
                        # BUG-44修复：处理 >> 被lexer解析为单个OPERATOR token的情况
                        elif (self._current().type == TokenType.OPERATOR and self._current().value == '>>'):
                            depth -= 2
                            self._advance()
                        elif self._is_punctuation('>'):
                            depth -= 1
                            self._advance()
                        else:
                            self._advance()
                if self._is_punctuation(','):
                    self._advance()
                else:
                    break

        # implements
        implements_list = []
        if self._is_keyword("implements"):
            self._advance()
            while self._is_type_name():
                # BUG-PARSE-006修复：拼接点号路径（与extends一致）
                full_name = self._current().value
                self._advance()
                while self._is_punctuation('.'):
                    self._advance()  # skip .
                    if self._is_identifier():
                        full_name += '.' + self._current().value
                        self._advance()
                    else:
                        break
                implements_list.append(full_name)
                # 跳过泛型参数 <...>
                if self._is_punctuation('<'):
                    self._advance()  # skip <
                    depth = 1
                    while depth > 0 and self._current().type != TokenType.EOF:
                        if self._is_punctuation('<'):
                            depth += 1
                            self._advance()
                        # BUG-44修复：处理 >> 被lexer解析为单个OPERATOR token的情况
                        elif (self._current().type == TokenType.OPERATOR and self._current().value == '>>'):
                            depth -= 2
                            self._advance()
                        elif self._is_punctuation('>'):
                            depth -= 1
                            self._advance()
                        else:
                            self._advance()
                if self._is_punctuation(','):
                    self._advance()
                else:
                    break

        # 解析类体
        class_node = ClassNode(
            node_type="ClassDeclaration",
            name=name,
            start_line=start_tok.line,
            end_line=start_tok.line,
            decorators=decorators,
            is_interface=is_interface,
            is_exported=is_exported,
            is_struct=is_struct,
            is_abstract=is_abstract,  # BUG-36修复：传入is_abstract参数
            extends=extends_list,
            implements=implements_list,
            type_parameters=type_params,
        )

        # 解析类体内容
        if self._is_punctuation('{'):
            self._advance()
            while not self._is_punctuation('}') and self._current().type != TokenType.EOF:
                member = self._parse_class_member(decorators=[])
                if member:
                    class_node.add_child(member)
            self._expect_punctuation('}')
            class_node.end_line = self._current().line

        return class_node

    def _parse_class_member(self, decorators: List[str]) -> Optional[ASTNode]:
        """解析类成员"""
        self._skip_semicolons()

        if self._is_punctuation('}') or self._current().type == TokenType.EOF:
            return None

        # 解析装饰器
        decorators = self._parse_decorators()

        # 访问修饰符
        is_private = False
        is_protected = False
        is_static = False
        is_readonly = False
        is_override = False
        is_abstract = False

        while True:
            if self._is_keyword("private"):
                is_private = True
                self._advance()
            elif self._is_keyword("protected"):
                is_protected = True
                self._advance()
            elif self._is_keyword("public"):
                self._advance()
            elif self._is_keyword("static"):
                is_static = True
                self._advance()
            elif self._is_keyword("readonly"):
                is_readonly = True
                self._advance()
            elif self._is_keyword("override"):
                is_override = True
                self._advance()
            elif self._is_keyword("abstract"):
                is_abstract = True
                self._advance()
            else:
                break

        # constructor
        if self._is_keyword("constructor"):
            return self._parse_constructor(decorators, is_static, is_private, is_protected)

        # getter/setter
        if self._is_keyword("get") or self._is_keyword("set"):
            return self._parse_accessor(decorators, is_static, is_private, is_protected)

        # async
        is_async = False
        if self._is_keyword("async"):
            is_async = True
            self._advance()

        # function keyword
        if self._is_keyword("function"):
            return self._parse_function_declaration(decorators, False, is_static, is_async, is_private, is_protected, is_abstract=is_abstract)

        # 方法或属性：以标识符开头
        if self._is_identifier():
            name_tok = self._current()
            name = name_tok.value
            self._advance()

            # 泛型参数
            if self._is_punctuation('<'):
                self._advance()  # skip <
                depth = 1
                while depth > 0 and self._current().type != TokenType.EOF:
                    if self._is_punctuation('<'):
                        depth += 1
                        self._advance()
                    elif (self._current().type == TokenType.OPERATOR and self._current().value == '>>'):
                        depth -= 2
                        self._advance()
                    elif self._is_punctuation('>'):
                        depth -= 1
                        self._advance()
                    else:
                        self._advance()

            # 如果后面是 ( 则是方法
            if self._is_punctuation('('):
                return self._parse_method_parameters(
                    name, name_tok.line, decorators, is_static, is_async, is_private, is_protected, is_override, is_abstract
                )

            # 如果后面是 ? 也可能是属性
            if self._is_punctuation('?'):
                self._advance()

            # 否则是属性
            return self._parse_property_declaration(
                name, name_tok.line, decorators, is_static, is_private, is_readonly
            )

        # 跳过无法识别的
        self._advance()
        return None

    def _parse_constructor(self, decorators, is_static, is_private, is_protected) -> MethodNode:
        """解析构造函数"""
        start_tok = self._current()
        self._advance()  # skip 'constructor'
        # 跳过参数列表
        if self._is_punctuation('('):
            self._advance()
            depth = 1
            while depth > 0 and self._current().type != TokenType.EOF:
                if self._is_punctuation('('):
                    depth += 1
                elif self._is_punctuation(')'):
                    depth -= 1
                self._advance()
        start_line, end_line = self._skip_block()
        return MethodNode(
            node_type="MethodDeclaration",
            name="constructor",
            start_line=start_tok.line,
            end_line=end_line,
            decorators=decorators,
            is_constructor=True,
            is_private=is_private,
            is_protected=is_protected,
        )

    def _parse_accessor(self, decorators, is_static, is_private, is_protected) -> MethodNode:
        """解析 getter/setter"""
        start_tok = self._current()
        accessor_type = self._current().value  # 'get' or 'set'
        self._advance()
        name = ""
        if self._is_identifier():
            name = self._current().value
            self._advance()
        # 跳过参数列表 (setter可能有参数)
        if self._is_punctuation('('):
            self._advance()
            depth = 1
            while depth > 0 and self._current().type != TokenType.EOF:
                if self._is_punctuation('('):
                    depth += 1
                elif self._is_punctuation(')'):
                    depth -= 1
                self._advance()
        # BUG-45修复：跳过返回类型注解（如 get count(): number { ... }）
        if self._is_punctuation(':'):
            self._advance()
            while (self._current().type != TokenType.EOF and
                   not self._is_punctuation('{')):
                self._advance()
        start_line, end_line = self._skip_block()
        return MethodNode(
            node_type="MethodDeclaration",
            name=f"{accessor_type} {name}",
            start_line=start_tok.line,
            end_line=end_line,
            decorators=decorators,
            is_static=is_static,
            is_getter=(accessor_type == "get"),
            is_setter=(accessor_type == "set"),
            is_private=is_private,
            is_protected=is_protected,
        )

    def _parse_method_parameters(self, name, start_line, decorators, is_static, is_async,
                                  is_private, is_protected, is_override, is_abstract=False) -> MethodNode:
        """解析方法参数和方法体"""
        parameters = []
        self._expect_punctuation('(')
        while not self._is_punctuation(')') and self._current().type != TokenType.EOF:
            param_name = ""
            param_type = ""
            is_rest = False  # 剩余参数标记
            
            # 处理剩余参数 ...args
            if self._is_punctuation('.'):
                # 检查是否是 ... (三个连续的点)
                if self._pos + 2 < len(self._tokens):
                    if (self._tokens[self._pos].value == '.' and 
                        self._tokens[self._pos + 1].value == '.' and 
                        self._tokens[self._pos + 2].value == '.'):
                        is_rest = True
                        self._advance()  # skip first .
                        self._advance()  # skip second .
                        self._advance()  # skip third .
            
            if self._is_identifier() or self._is_keyword("this"):
                param_name = self._current().value
                self._advance()
            if self._is_punctuation(':'):
                self._advance()
                type_start = self._pos
                depth = 0
                while (self._current().type != TokenType.EOF and
                       not (self._is_punctuation(',') and depth == 0) and
                       not (self._is_punctuation(')') and depth == 0)):
                    if self._is_punctuation('<') or self._is_punctuation('('):
                        depth += 1
                    elif depth > 0 and (self._is_punctuation('>') or self._is_punctuation(')')):
                        depth -= 1
                    self._advance()
                # 提取实际类型注解文本
                type_tokens = self._tokens[type_start:self._pos]
                param_type = " ".join(t.value for t in type_tokens if t.type not in (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.COMMENT)).strip()
                if not param_type:
                    param_type = "param"
            if param_name:
                param_info = {"name": param_name, "type": param_type}
                if is_rest:
                    param_info["rest"] = True
                parameters.append(param_info)
            else:
                # 无法识别的参数token，跳过以避免死循环
                if (not self._is_punctuation(',') and 
                    not self._is_punctuation(')') and
                    self._current().type != TokenType.EOF):
                    self._advance()
            if self._is_punctuation(','):
                self._advance()

        self._expect_punctuation(')')

        # 返回类型
        return_type = ""
        if self._is_punctuation(':'):
            self._advance()
            # 读取返回类型，需要处理嵌套的 < > { } ( )
            depth = 0
            while self._current().type != TokenType.EOF:
                # depth==0 时遇到终止符才退出
                if depth == 0 and self._is_punctuation('{'):
                    break
                if depth == 0 and self._is_punctuation(';'):
                    break
                if depth == 0 and self._is_punctuation('}'):
                    break
                # 检查是否遇到下一个成员（标识符后跟 ( 或 :）
                if (depth == 0 and self._is_identifier() and
                    self._pos + 1 < len(self._tokens) and
                    self._tokens[self._pos + 1].value in ('(', ':')):
                    break
                if self._is_punctuation('<') or self._is_punctuation('(') or self._is_punctuation('{'):
                    depth += 1
                elif depth > 0 and (self._is_punctuation('>') or self._is_punctuation(')') or self._is_punctuation('}')):
                    depth -= 1
                self._advance()

        # 方法体
        _, end_line = self._skip_block()
        self._skip_semicolons()

        return MethodNode(
            node_type="MethodDeclaration",
            name=name,
            start_line=start_line,
            end_line=end_line,
            decorators=decorators,
            is_static=is_static,
            is_async=is_async,
            is_private=is_private,
            is_protected=is_protected,
            is_override=is_override,
            is_abstract=is_abstract,
            parameters=parameters,
            return_type=return_type,
        )

    def _parse_property_declaration(self, name, start_line, decorators, is_static,
                                     is_private, is_readonly) -> PropertyNode:
        """解析属性声明"""
        type_annotation = ""
        default_value = ""

        # 类型注解
        if self._is_punctuation(':'):
            self._advance()
            type_parts = []
            depth = 0  # BUG-37修复：添加深度计数处理泛型 < >
            # 读取类型，直到遇到 = 或 ; 或换行后的标识符
            while (self._current().type != TokenType.EOF and
                   not (self._is_punctuation('=') or (self._current().type == TokenType.OPERATOR and self._current().value == '=')) and
                   not self._is_punctuation(';') and
                   # 修复P: 遇到 } 时停止类型注解
                   not self._is_punctuation('}') and
                   not (depth == 0 and self._current().type == TokenType.KEYWORD and
                        self._current().value in ('static', 'private', 'public', 'protected', 'async', 'readonly')) and
                   # 修复：depth==0时遇到换行后的标识符停止（无分号属性声明）
                   not (depth == 0 and self._current().type == TokenType.IDENTIFIER and
                        type_parts and self._current().line > start_line) and
                   # BUG-107修复：depth==0时遇到标识符+(停止（方法声明，同一行）
                   not (depth == 0 and self._current().type == TokenType.IDENTIFIER and
                        type_parts and
                        self._pos + 1 < len(self._tokens) and self._tokens[self._pos + 1].type == TokenType.PUNCTUATION and
                        self._tokens[self._pos + 1].value == '(')):
                # BUG-37修复：深度计数处理泛型
                if self._is_punctuation('<') or (self._current().type == TokenType.OPERATOR and self._current().value == '<'):
                    depth += 1
                elif self._is_punctuation('>') or (self._current().type == TokenType.OPERATOR and self._current().value == '>'):
                    depth -= 1
                elif self._current().type == TokenType.OPERATOR and self._current().value == '>>':
                    depth -= 2
                type_parts.append(self._current().value)
                self._advance()
            type_annotation = " ".join(type_parts)

        # 默认值
        if self._is_punctuation('='):
            self._advance()
            val_parts = []
            depth = 0
            # 读取默认值，遇到 ; 或换行后的关键字停止
            while (self._current().type != TokenType.EOF and
                   not (self._is_punctuation(';') and depth == 0) and
                   not (self._is_punctuation('}') and depth == 0)):
                # 检查是否遇到下一个成员的关键字
                if (depth == 0 and self._current().type == TokenType.KEYWORD and
                    self._current().value in ('static', 'private', 'public', 'protected', 'async', 'readonly', 'constructor', 'get', 'set',
                                              # 修复R: 添加 import 和 abstract 关键字检查
                                              'import', 'abstract')):
                    break
                # BUG-37修复：depth==0时遇到标识符+括号(方法声明)也停止
                # BUG-107修复：移除val_parts为空的限制，避免默认值后方法被跳过
                # 当IDENTIFIER后跟()且再跟:或)时，一定是方法声明
                if (depth == 0 and
                    self._current().type == TokenType.IDENTIFIER and
                    self._pos + 1 < len(self._tokens) and self._tokens[self._pos + 1].type == TokenType.PUNCTUATION and
                    self._tokens[self._pos + 1].value == '(' and
                    self._pos + 2 < len(self._tokens) and self._tokens[self._pos + 2].type == TokenType.PUNCTUATION and
                    self._tokens[self._pos + 2].value in (':', ')', '{')):
                    break
                if self._is_punctuation('{') or self._is_punctuation('(') or self._is_punctuation('['):
                    depth += 1
                elif depth > 0 and (self._is_punctuation('}') or self._is_punctuation(')') or self._is_punctuation(']')):
                    depth -= 1
                # BUG-37修复：处理泛型 < > 深度计数
                elif self._current().type == TokenType.OPERATOR and self._current().value in ('<', '>'):
                    if self._current().value == '<':
                        depth += 1
                    else:
                        depth -= 1
                elif self._current().type == TokenType.OPERATOR and self._current().value == '>>':
                    depth -= 2
                val_parts.append(self._current().value)
                self._advance()
            default_value = " ".join(val_parts)

        self._skip_semicolons()

        # 检查装饰器中的状态管理
        is_state = "State" in decorators
        is_link = "Link" in decorators
        is_prop = "Prop" in decorators
        is_provide = "Provide" in decorators

        return PropertyNode(
            node_type="PropertyDeclaration",
            name=name,
            start_line=start_line,
            end_line=self._current().line,
            decorators=decorators,
            type_annotation=type_annotation,
            default_value=default_value,
            is_static=is_static,
            is_private=is_private,
            is_readonly=is_readonly,
            is_state=is_state,
            is_link=is_link,
            is_prop=is_prop,
            is_provide=is_provide,
        )

    def _parse_function_declaration(self, decorators, is_exported, is_static=False,
                                     is_async=False, is_private=False,
                                     is_protected=False, is_abstract=False) -> MethodNode:
        """解析函数声明"""
        start_tok = self._current()
        self._advance()  # skip 'function'

        name = ""
        if self._is_identifier():
            name = self._current().value
            self._advance()

        # 泛型参数
        if self._is_punctuation('<'):
            self._advance()  # skip <
            depth = 1
            while depth > 0 and self._current().type != TokenType.EOF:
                if self._is_punctuation('<'):
                    depth += 1
                    self._advance()
                elif (self._current().type == TokenType.OPERATOR and self._current().value == '>>'):
                    depth -= 2
                    self._advance()
                elif self._is_punctuation('>'):
                    depth -= 1
                    self._advance()
                else:
                    self._advance()

        # 参数
        parameters = []
        if self._is_punctuation('('):
            self._advance()
            while not self._is_punctuation(')') and self._current().type != TokenType.EOF:
                # 处理剩余参数
                is_rest = False
                if self._is_punctuation('.'):
                    if (self._pos + 2 < len(self._tokens) and
                        self._tokens[self._pos].value == '.' and
                        self._tokens[self._pos + 1].value == '.' and
                        self._tokens[self._pos + 2].value == '.'):
                        is_rest = True
                        self._advance()
                        self._advance()
                        self._advance()
                
                param_name = ""
                if self._is_identifier() or self._is_keyword("this"):
                    param_name = self._current().value
                    self._advance()
                
                # 提取类型注解
                param_type = ""
                if self._is_punctuation(':'):
                    self._advance()
                    type_start = self._pos
                    depth = 0
                    while (self._current().type != TokenType.EOF and
                           not (self._is_punctuation(',') and depth == 0) and
                           not (self._is_punctuation(')') and depth == 0)):
                        if self._is_punctuation('<') or self._is_punctuation('('):
                            depth += 1
                        elif depth > 0 and (self._is_punctuation('>') or self._is_punctuation(')')):
                            depth -= 1
                        self._advance()
                    type_tokens = self._tokens[type_start:self._pos]
                    param_type = " ".join(t.value for t in type_tokens if t.type not in (TokenType.WHITESPACE, TokenType.NEWLINE, TokenType.COMMENT)).strip()

                if param_name:
                    param_info = {"name": param_name, "type": param_type}
                    if is_rest:
                        param_info["rest"] = True
                    parameters.append(param_info)
                else:
                    # 跳过无法识别的token
                    if (not self._is_punctuation(',') and
                        not self._is_punctuation(')') and
                        self._current().type != TokenType.EOF):
                        self._advance()
                
                if self._is_punctuation(','):
                    self._advance()
            self._expect_punctuation(')')

        # 返回类型
        return_type = ""
        if self._is_punctuation(':'):
            self._advance()
            depth = 0
            while (self._current().type != TokenType.EOF and
                   not (self._is_punctuation('{') and depth == 0)):
                if self._is_punctuation('<') or self._is_punctuation('(') or self._is_punctuation('{'):
                    depth += 1
                elif depth > 0 and (self._is_punctuation('>') or self._is_punctuation(')') or self._is_punctuation('}')):
                    depth -= 1
                self._advance()

        # 函数体
        _, end_line = self._skip_block()
        self._skip_semicolons()

        return MethodNode(
            node_type="FunctionDeclaration",
            name=name,
            start_line=start_tok.line,
            end_line=end_line,
            decorators=decorators,
            is_static=is_static,
            is_async=is_async,
            is_private=is_private,
            is_protected=is_protected,
            is_abstract=is_abstract,
            parameters=parameters,
            return_type=return_type,
        )

    def _parse_namespace_declaration(self, decorators, is_exported) -> NamespaceNode:
        """解析命名空间声明"""
        start_tok = self._current()
        self._advance()  # skip 'namespace'/'module'

        name = ""
        if self._is_identifier():
            name = self._current().value
            self._advance()

        namespace_node = NamespaceNode(
            node_type="NamespaceDeclaration",
            name=name,
            start_line=start_tok.line,
            end_line=start_tok.line,
        )

        # BUG-PARSE-001修复：解析命名空间内容而非跳过
        if self._is_punctuation('{'):
            self._advance()
            while not self._is_punctuation('}') and self._current().type != TokenType.EOF:
                self._skip_semicolons()
                if self._is_punctuation('}') or self._current().type == TokenType.EOF:
                    break

                # 解析装饰器
                ns_decorators = self._parse_decorators()

                # 解析导出
                ns_is_exported = False
                if self._is_keyword("export"):
                    self._advance()
                    ns_is_exported = True

                # 解析各种声明
                node = self._parse_declaration(ns_decorators, ns_is_exported)
                if node:
                    namespace_node.add_child(node)
            self._expect_punctuation('}')
            namespace_node.end_line = self._current().line
        else:
            _, end_line = self._skip_block()
            namespace_node.end_line = end_line

        return namespace_node

    def _parse_enum_declaration(self, decorators, is_exported) -> ClassNode:
        """解析枚举声明"""
        start_tok = self._current()
        self._advance()  # skip 'enum'

        name = ""
        if self._is_identifier():
            name = self._current().value
            self._advance()

        enum_node = ClassNode(
            node_type="EnumDeclaration",
            name=name,
            start_line=start_tok.line,
            end_line=start_tok.line,
            decorators=decorators,
            is_enum=True,
            is_exported=is_exported,
        )

        if self._is_punctuation('{'):
            self._advance()
            while not self._is_punctuation('}') and self._current().type != TokenType.EOF:
                if self._is_identifier():
                    member_name = self._current().value
                    member_line = self._current().line
                    self._advance()
                    member_value = ""
                    if self._is_punctuation('='):
                        self._advance()
                        while (self._current().type != TokenType.EOF and
                               not self._is_punctuation(',') and
                               not self._is_punctuation('}')):
                            member_value += self._current().value
                            self._advance()
                    enum_node.add_child(EnumMemberNode(
                        node_type="EnumMember",
                        name=member_name,
                        start_line=member_line,
                        value=member_value.strip(),
                    ))
                if self._is_punctuation(','):
                    self._advance()
            self._expect_punctuation('}')
            enum_node.end_line = self._current().line

        return enum_node

    def _parse_type_alias(self, is_exported) -> Optional[TypeAliasNode]:
        """解析类型别名"""
        start_tok = self._current()
        self._advance()  # skip 'type'

        name = ""
        if self._is_identifier():
            name = self._current().value
            self._advance()

        # 跳过泛型参数
        if self._is_punctuation('<'):
            self._advance()  # skip <
            depth = 1
            # BUG-34修复：使用深度计数器跳过泛型参数，正确处理嵌套 < > 和 >> 的情况
            while depth > 0 and self._current().type != TokenType.EOF:
                if self._is_punctuation('<'):
                    depth += 1
                    self._advance()
                elif (self._current().type == TokenType.OPERATOR and self._current().value == '>>'):
                    depth -= 2
                    self._advance()
                elif self._is_punctuation('>'):
                    depth -= 1
                    self._advance()
                else:
                    self._advance()

        if self._is_punctuation('='):
            self._advance()
            type_parts = []
            while (self._current().type != TokenType.EOF and
                   not self._is_punctuation(';')):
                type_parts.append(self._current().value)
                self._advance()
            self._skip_semicolons()
            return TypeAliasNode(
                node_type="TypeAlias",
                name=name,
                start_line=start_tok.line,
                end_line=self._current().line,
                type_definition=" ".join(type_parts),
            )

        return None

    def _parse_variable_declaration(self, decorators, is_exported) -> Optional[ASTNode]:
        """解析变量声明（可能包含箭头函数）"""
        start_tok = self._current()
        self._advance()  # skip 'const'/'let'/'var'

        if not self._is_identifier():
            return None

        name = self._current().value
        self._advance()

        # 类型注解
        if self._is_punctuation(':'):
            self._advance()
            while (self._current().type != TokenType.EOF and
                   not self._is_punctuation('=') and
                   not self._is_punctuation(';')):
                self._advance()

        # 箭头函数
        # BUG-42修复：lexer将 => 解析为单个OPERATOR token
        if self._is_punctuation('=') and self._peek_is_arrow():
            self._advance()  # skip =
            # 跳过参数列表 (...)，如果有的话
            if self._is_punctuation('('):
                self._advance()
                depth = 1
                while depth > 0 and self._current().type != TokenType.EOF:
                    if self._is_punctuation('('):
                        depth += 1
                    elif self._is_punctuation(')'):
                        depth -= 1
                    self._advance()
            # 跳过 => token
            if self._current().type == TokenType.OPERATOR and self._current().value == '=>':
                self._advance()
            _, end_line = self._skip_block()
            self._skip_semicolons()
            return MethodNode(
                node_type="ArrowFunction",
                name=name,
                start_line=start_tok.line,
                end_line=end_line,
                decorators=decorators,
                is_arrow=True,
            )

        # 普通变量 - 跳过
        while (self._current().type != TokenType.EOF and
               not self._is_punctuation(';')):
            self._advance()
        self._skip_semicolons()

        return PropertyNode(
            node_type="VariableDeclaration",
            name=name,
            start_line=start_tok.line,
            end_line=self._current().line,
            decorators=decorators,
        )

    def _peek_is_arrow(self) -> bool:
        """检查后续Token中是否包含 =>（箭头函数标记）"""
        # BUG-42修复：lexer将 => 解析为单个OPERATOR token，而非两个独立token
        # 检查下一个token是否直接是 =>
        next_pos = self._pos + 1
        if next_pos < len(self._tokens):
            if (self._tokens[next_pos].type == TokenType.OPERATOR and
                    self._tokens[next_pos].value == '=>'):
                return True
            # BUG-H5修复：检查单参数无括号箭头函数模式: = identifier =>
            # 例如: const fn = x => x + 1
            if (self._tokens[next_pos].type == TokenType.IDENTIFIER and
                    next_pos + 1 < len(self._tokens) and
                    self._tokens[next_pos + 1].type == TokenType.OPERATOR and
                    self._tokens[next_pos + 1].value == '=>'):
                return True
            # 也检查跳过参数列表 (...) 后是否有 =>
            # 例如: = (...) => { ... }
            if self._tokens[next_pos].type == TokenType.PUNCTUATION and self._tokens[next_pos].value == '(':
                search_pos = next_pos + 1
                depth = 1
                while search_pos < len(self._tokens) and depth > 0:
                    if self._tokens[search_pos].type == TokenType.PUNCTUATION and self._tokens[search_pos].value == '(':
                        depth += 1
                    elif self._tokens[search_pos].type == TokenType.PUNCTUATION and self._tokens[search_pos].value == ')':
                        depth -= 1
                    search_pos += 1
                if search_pos < len(self._tokens):
                    return (self._tokens[search_pos].type == TokenType.OPERATOR and
                            self._tokens[search_pos].value == '=>')
        return False
