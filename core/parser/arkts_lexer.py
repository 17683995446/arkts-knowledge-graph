"""
ArkTS 词法分析器
将源代码文本转换为Token流
"""
import re
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass, field
from enum import Enum, auto


class TokenType(Enum):
    """Token类型枚举"""
    # 关键字
    KEYWORD = auto()
    DECORATOR = auto()
    # 标识符
    IDENTIFIER = auto()
    # 字面量
    STRING = auto()
    NUMBER = auto()
    # 运算符
    OPERATOR = auto()
    # 分隔符
    PUNCTUATION = auto()
    # 特殊
    COMMENT = auto()
    WHITESPACE = auto()
    NEWLINE = auto()
    EOF = auto()


@dataclass
class Token:
    """词法单元"""
    type: TokenType
    value: str
    line: int = 0
    column: int = 0
    end_line: int = 0
    end_column: int = 0


# ArkTS/TypeScript 关键字集合
ARKTS_KEYWORDS = {
    "import", "export", "from", "default", "as", "const", "let", "var",
    "function", "return", "if", "else", "for", "while", "do", "switch",
    "case", "break", "continue", "new", "this", "super", "class", "extends",
    "implements", "interface", "enum", "type", "struct", "namespace", "module",
    "public", "private", "protected", "static", "readonly", "abstract",
    "override", "get", "set", "constructor",
    "async", "await", "try", "catch", "finally", "throw", "typeof", "instanceof",
    "void", "null", "undefined", "true", "false", "of", "in", "yield",
    # ArkUI 特有
    "Entry", "Component", "Builder", "Extend", "Styles", "State",
    "Link", "Prop", "Provide", "Consume", "ObjectLink", "Watch",
    "StorageLink", "StorageProp", "LocalStorage", "AppStorage",
    # 鸿蒙特有
    "ets", "UIAbility", "Ability", "Window", "Want",
}

# ArkTS 装饰器集合
ARKTS_DECORATORS = {
    "Component", "Entry", "Builder", "Extend", "Styles", "Watch",
    "State", "Link", "Prop", "Provide", "Consume", "ObjectLink",
    "StorageLink", "StorageProp", "BuilderParam", "Reusable",
    "Observed", "ObjectLink", "Track", "Volatile",
}


class ArkTSLexer:
    """
    ArkTS 词法分析器
    将源代码文本转换为Token流
    """

    def __init__(self, source: str):
        self._source = source
        self._pos = 0
        self._line = 1
        self._column = 1
        self._tokens: List[Token] = []

    def tokenize(self) -> List[Token]:
        """执行词法分析，返回Token列表"""
        self._tokens = []
        while self._pos < len(self._source):
            self._skip_whitespace_and_comments()
            if self._pos >= len(self._source):
                break

            ch = self._source[self._pos]

            if ch == '@':
                self._read_decorator()
            elif ch == '"' or ch == "'" or ch == '`':
                self._read_string()
            elif ch.isdigit():
                self._read_number()
            elif ch.isalpha() or ch == '_' or ch == '$':
                self._read_identifier()
            elif ch == '.':
                # 修复F: .5 小数 - 当点号后面是数字时，按数字处理
                if self._pos + 1 < len(self._source) and self._source[self._pos + 1].isdigit():
                    self._read_number()
                elif not self._read_punctuation():
                    # _read_punctuation 返回 None 表示 ... 等需要由 _read_operator 处理
                    self._read_operator()
            elif ch in '{}()[];,?:':
                if not self._read_punctuation():
                    self._read_operator()
            elif ch in '+-*/%=!<>&|^~':
                self._read_operator()
            else:
                self._pos += 1
                self._column += 1

        self._tokens.append(Token(TokenType.EOF, "", self._line, self._column))
        return self._tokens

    def _skip_whitespace_and_comments(self):
        """跳过空白和注释"""
        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch in ' \t\r':
                self._pos += 1
                self._column += 1
            elif ch == '\n':
                self._pos += 1
                self._line += 1
                self._column = 1
            elif self._pos + 1 < len(self._source) and self._source[self._pos:self._pos+2] == '//':
                self._skip_line_comment()
            elif self._pos + 1 < len(self._source) and self._source[self._pos:self._pos+2] == '/*':
                self._skip_block_comment()
            else:
                break

    def _skip_line_comment(self):
        """跳过单行注释"""
        while self._pos < len(self._source) and self._source[self._pos] != '\n':
            self._pos += 1

    def _skip_block_comment(self):
        """跳过块注释"""
        self._pos += 2
        while self._pos + 1 < len(self._source):
            if self._source[self._pos:self._pos+2] == '*/':
                self._pos += 2
                return
            if self._source[self._pos] == '\n':
                self._line += 1
                self._column = 1
            self._pos += 1
        # 修复I: 块注释未闭合时，安全跳到末尾
        self._pos = len(self._source)

    def _read_decorator(self):
        """读取装饰器 @Component 等"""
        start_line, start_col = self._line, self._column
        self._pos += 1
        self._column += 1
        name_start = self._pos
        while self._pos < len(self._source) and (self._source[self._pos].isalnum() or self._source[self._pos] == '_'):
            self._pos += 1
            self._column += 1
        name = self._source[name_start:self._pos]
        # 读取装饰器参数
        args = ""
        if self._pos < len(self._source) and self._source[self._pos] == '(':
            depth = 1
            args_start = self._pos
            self._pos += 1
            while self._pos < len(self._source) and depth > 0:
                if self._source[self._pos] == '(':
                    depth += 1
                elif self._source[self._pos] == ')':
                    depth -= 1
                elif self._source[self._pos] == '\n':
                    self._line += 1
                    self._column = 1
                self._pos += 1
            args = self._source[args_start:self._pos]
            self._column += len(args)

        self._tokens.append(Token(
            TokenType.DECORATOR, f"@{name}{args}", start_line, start_col, self._line, self._column
        ))

    def _read_string(self):
        """读取字符串字面量"""
        start_line, start_col = self._line, self._column
        quote = self._source[self._pos]
        self._pos += 1
        self._column += 1
        # BUG-38修复：保存字符串实际内容
        chars = []
        while self._pos < len(self._source) and self._source[self._pos] != quote:
            if self._source[self._pos] == '\\':
                # 修复H: 转义越界检查
                if self._pos + 1 < len(self._source):
                    self._pos += 2
                    self._column += 2
                    chars.append(self._source[self._pos - 2:self._pos])  # 保留转义序列
                else:
                    chars.append(self._source[self._pos])
                    self._pos += 1
                    self._column += 1
                    break
            else:
                ch = self._source[self._pos]
                if ch == '\n':
                    self._line += 1
                    self._column = 1
                else:
                    self._column += 1
                chars.append(ch)
                self._pos += 1
        if self._pos < len(self._source):
            self._pos += 1
            self._column += 1
        string_value = ''.join(chars)
        self._tokens.append(Token(TokenType.STRING, string_value, start_line, start_col, self._line, self._column))

    def _read_number(self):
        """读取数字字面量"""
        start_line, start_col = self._line, self._column
        start_pos = self._pos  # BUG-39修复：记录起始位置
        has_dot = False  # BUG-11修复：标记是否已遇到小数点，防止 1.2.3 被匹配为一个token
        has_exponent = False  # 科学计数法标记

        # 处理进制前缀: 0x, 0X, 0b, 0B, 0o, 0O
        if (self._pos + 1 < len(self._source) and self._source[self._pos] == '0'
                and self._source[self._pos + 1] in 'xXbBoO'):
            prefix = self._source[self._pos:self._pos + 2]
            self._pos += 2
            self._column += 2
            # 读取进制前缀后的数字
            if prefix[1] in 'xX':
                # 十六进制: 0-9, a-f, A-F
                while self._pos < len(self._source) and (self._source[self._pos] in '0123456789abcdefABCDEF'):
                    self._pos += 1
                    self._column += 1
            elif prefix[1] in 'bB':
                # 二进制: 0-1
                while self._pos < len(self._source) and self._source[self._pos] in '01':
                    self._pos += 1
                    self._column += 1
            elif prefix[1] in 'oO':
                # 八进制: 0-7
                while self._pos < len(self._source) and self._source[self._pos] in '01234567':
                    self._pos += 1
                    self._column += 1
            number_value = self._source[start_pos:self._pos]
            self._tokens.append(Token(TokenType.NUMBER, number_value, start_line, start_col, self._line, self._column))
            return

        while self._pos < len(self._source):
            ch = self._source[self._pos]
            if ch.isdigit():
                self._pos += 1
                self._column += 1
            elif ch == '.' and not has_dot:
                has_dot = True
                self._pos += 1
                self._column += 1
            elif ch in 'eE' and not has_exponent:
                # 科学计数法: e/E 后面可以跟 +/-
                has_exponent = True
                self._pos += 1
                self._column += 1
                if self._pos < len(self._source) and self._source[self._pos] in '+-':
                    self._pos += 1
                    self._column += 1
            else:
                break
        number_value = self._source[start_pos:self._pos]
        self._tokens.append(Token(TokenType.NUMBER, number_value, start_line, start_col, self._line, self._column))

    def _read_identifier(self):
        """读取标识符或关键字"""
        start_line, start_col = self._line, self._column
        start = self._pos
        while self._pos < len(self._source) and (self._source[self._pos].isalnum() or self._source[self._pos] in '_$'):
            self._pos += 1
            self._column += 1
        value = self._source[start:self._pos]
        if value in ARKTS_KEYWORDS:
            self._tokens.append(Token(TokenType.KEYWORD, value, start_line, start_col, self._line, self._column))
        else:
            self._tokens.append(Token(TokenType.IDENTIFIER, value, start_line, start_col, self._line, self._column))

    def _read_punctuation(self):
        """读取标点符号，返回True表示已处理，返回None表示需要由_read_operator处理"""
        start_line, start_col = self._line, self._column
        value = self._source[self._pos]
        # ?? 应该作为运算符处理
        if value == '?' and self._pos + 1 < len(self._source) and self._source[self._pos + 1] == '?':
            return None
        # ?. 可选链应该作为运算符处理
        if value == '?' and self._pos + 1 < len(self._source) and self._source[self._pos + 1] == '.':
            return None
        # ... 展开运算符应该作为运算符处理
        if value == '.' and self._pos + 2 < len(self._source) and self._source[self._pos + 1] == '.' and self._source[self._pos + 2] == '.':
            return None
        self._pos += 1
        self._column += 1
        self._tokens.append(Token(TokenType.PUNCTUATION, value, start_line, start_col, self._line, self._column))
        return True

    # 修复D: 有效运算符集合，用于最大匹配策略
    VALID_OPERATORS = {
        '>>>=', '>>=', '<<=', '**=', '&&=', '||=', '??=',
        '===', '!==', '>>>', '<<=', '>>=',
        '==', '!=', '<=', '>=', '&&', '||', '??', '?.', '...',
        '**', '++', '--', '=>', '<<', '>>',
        '+', '-', '*', '/', '%', '=', '!', '<', '>', '&', '|', '^', '~', '?', '.',
    }

    def _read_operator(self):
        """读取运算符"""
        start_line, start_col = self._line, self._column
        # 修复D: 使用最大匹配策略，从最长到最短尝试匹配
        best_match = ""
        best_len = 0
        for op in sorted(self.VALID_OPERATORS, key=len, reverse=True):
            if self._source[self._pos:self._pos+len(op)] == op:
                if len(op) > best_len:
                    best_match = op
                    best_len = len(op)
        if best_match:
            self._pos += best_len
            self._column += best_len
            # 修复B: 空token防御
            if best_match:
                self._tokens.append(Token(TokenType.OPERATOR, best_match, start_line, start_col, self._line, self._column))
