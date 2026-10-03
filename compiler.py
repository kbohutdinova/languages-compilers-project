class Token:
    def __init__(self, kind, text, line, column):
        self.kind = kind
        self.text = text
        self.line = line
        self.column = column

    def __repr__(self):
        return f"Token({self.kind}, {self.text!r}, {self.line}:{self.column})"


# Token kinds

TOKEN_EOF = "EOF"
TOKEN_IDENTIFIER = "IDENTIFIER"
TOKEN_INTEGER = "INTEGER"

TOKEN_NUM32 = "NUM32"
TOKEN_NUM64 = "NUM64"
TOKEN_BOOL = "BOOL"
TOKEN_MUT = "MUT"
TOKEN_TRUE = "TRUE"
TOKEN_FALSE = "FALSE"
TOKEN_IF = "IF"
TOKEN_ELSE = "ELSE"

TOKEN_ASSIGN = "ASSIGN"
TOKEN_EQUAL = "EQUAL"
TOKEN_NOT_EQUAL = "NOT_EQUAL"

TOKEN_PLUS = "PLUS"
TOKEN_MINUS = "MINUS"
TOKEN_STAR = "STAR"
TOKEN_SLASH = "SLASH"

TOKEN_LBRACE = "LBRACE"
TOKEN_RBRACE = "RBRACE"
TOKEN_LPAREN = "LPAREN"
TOKEN_RPAREN = "RPAREN"
TOKEN_SEMICOLON = "SEMICOLON"


KEYWORDS = {
    "num32": TOKEN_NUM32,
    "num64": TOKEN_NUM64,
    "bool": TOKEN_BOOL,
    "mut": TOKEN_MUT,
    "true": TOKEN_TRUE,
    "false": TOKEN_FALSE,
    "if": TOKEN_IF,
    "else": TOKEN_ELSE,
}


class Lexer:
    def __init__(self, source):
        self.source = source.encode("utf-8")
        self.index = 0
        self.line = 1
        self.column = 1

    def current(self):
        if self.index >= len(self.source):
            return None

        return self.source[self.index]

    def advance(self):
        if self.index >= len(self.source):
            return

        byte = self.source[self.index]
        self.index += 1

        if byte == ord("\n"):
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    def skip_whitespace(self):
        while self.current() is not None:
            byte = self.current()

            if byte in (
                ord(" "),
                ord("\t"),
                ord("\r"),
                ord("\n"),
            ):
                self.advance()
            else:
                break

    def lex_identifier(self):
        start_line = self.line
        start_column = self.column
        chars = []

        while self.current() is not None:
            byte = self.current()
            char = chr(byte)

            if char.isascii() and (
                char.isalpha()
                or char.isdigit()
                or char == "_"
            ):
                chars.append(char)
                self.advance()
            else:
                break

        text = "".join(chars)
        kind = KEYWORDS.get(text, TOKEN_IDENTIFIER)

        return Token(
            kind,
            text,
            start_line,
            start_column,
        )

    def lex_integer(self):
        start_line = self.line
        start_column = self.column
        chars = []

        while self.current() is not None:
            byte = self.current()
            char = chr(byte)

            if char.isascii() and char.isdigit():
                chars.append(char)
                self.advance()
            else:
                break

        text = "".join(chars)

        return Token(
            TOKEN_INTEGER,
            text,
            start_line,
            start_column,
        )


# =========================
# AST
# =========================

class ASTNode:
    def __init__(self, line, column):
        self.line = line
        self.column = column


class ProgramNode(ASTNode):
    def __init__(self, statements):
        super().__init__(1, 1)
        self.statements = statements


class StmtNode(ASTNode):
    pass


class ExprNode(ASTNode):
    pass


class DeclarationNode(StmtNode):
    def __init__(
        self,
        line,
        column,
        var_type,
        name,
        mutable,
        expression,
    ):
        super().__init__(line, column)
        self.var_type = var_type
        self.name = name
        self.mutable = mutable
        self.expression = expression


class AssignmentNode(StmtNode):
    def __init__(
        self,
        line,
        column,
        name,
        expression,
    ):
        super().__init__(line, column)
        self.name = name
        self.expression = expression


class IfNode(StmtNode):
    def __init__(
        self,
        line,
        column,
        condition,
        if_body,
        else_body=None,
    ):
        super().__init__(line, column)
        self.condition = condition
        self.if_body = if_body
        self.else_body = else_body


class IntegerNode(ExprNode):
    def __init__(
        self,
        line,
        column,
        value,
    ):
        super().__init__(line, column)
        self.value = value


class BooleanNode(ExprNode):
    def __init__(
        self,
        line,
        column,
        value,
    ):
        super().__init__(line, column)
        self.value = value


class IdentifierNode(ExprNode):
    def __init__(
        self,
        line,
        column,
        name,
    ):
        super().__init__(line, column)
        self.name = name


class BinaryExprNode(ExprNode):
    def __init__(
        self,
        line,
        column,
        left,
        operator,
        right,
    ):
        super().__init__(line, column)
        self.left = left
        self.operator = operator
        self.right = right
