import sys


# ============================================================
# ERRORS
# ============================================================

class CompilationError(Exception):
    def __init__(self, line, column, message):
        self.line = line
        self.column = column
        self.message = message
        super().__init__(message)


# ============================================================
# TOKENS
# ============================================================

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


class Token:
    def __init__(self, kind, text, line, column):
        self.kind = kind
        self.text = text
        self.line = line
        self.column = column

    def __repr__(self):
        return (
            f"Token({self.kind}, {self.text!r}, "
            f"{self.line}:{self.column})"
        )


# ============================================================
# LEXER
# ============================================================

class Lexer:
    def __init__(self, source):
        # Task requirement: lexer works over bytes.
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

            # Language identifiers are ASCII.
            if byte > 127:
                break

            char = chr(byte)

            if (
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

            if byte > 127:
                break

            char = chr(byte)

            if char.isdigit():
                chars.append(char)
                self.advance()
            else:
                break

        return Token(
            TOKEN_INTEGER,
            "".join(chars),
            start_line,
            start_column,
        )

    def next_token(self):
        self.skip_whitespace()

        start_line = self.line
        start_column = self.column

        byte = self.current()

        if byte is None:
            return Token(
                TOKEN_EOF,
                "",
                start_line,
                start_column,
            )

        # We currently use ASCII language symbols.
        if byte > 127:
            raise CompilationError(
                start_line,
                start_column,
                "unexpected byte",
            )

        char = chr(byte)

        # Identifier / keyword
        if char.isalpha() or char == "_":
            return self.lex_identifier()

        # Integer
        if char.isdigit():
            return self.lex_integer()

        # {
        if char == "{":
            self.advance()
            return Token(
                TOKEN_LBRACE,
                "{",
                start_line,
                start_column,
            )

        # }
        if char == "}":
            self.advance()
            return Token(
                TOKEN_RBRACE,
                "}",
                start_line,
                start_column,
            )

        # (
        if char == "(":
            self.advance()
            return Token(
                TOKEN_LPAREN,
                "(",
                start_line,
                start_column,
            )

        # )
        if char == ")":
            self.advance()
            return Token(
                TOKEN_RPAREN,
                ")",
                start_line,
                start_column,
            )

        # ;
        if char == ";":
            self.advance()
            return Token(
                TOKEN_SEMICOLON,
                ";",
                start_line,
                start_column,
            )

        # +
        if char == "+":
            self.advance()
            return Token(
                TOKEN_PLUS,
                "+",
                start_line,
                start_column,
            )

        # -
        if char == "-":
            self.advance()
            return Token(
                TOKEN_MINUS,
                "-",
                start_line,
                start_column,
            )

        # *
        if char == "*":
            self.advance()
            return Token(
                TOKEN_STAR,
                "*",
                start_line,
                start_column,
            )

        # /
        if char == "/":
            self.advance()
            return Token(
                TOKEN_SLASH,
                "/",
                start_line,
                start_column,
            )

        # :=
        if char == ":":
            self.advance()

            if self.current() == ord("="):
                self.advance()

                return Token(
                    TOKEN_ASSIGN,
                    ":=",
                    start_line,
                    start_column,
                )

            raise CompilationError(
                start_line,
                start_column,
                "expected '=' after ':'",
            )

        # ==
        if char == "=":
            self.advance()

            if self.current() == ord("="):
                self.advance()

                return Token(
                    TOKEN_EQUAL,
                    "==",
                    start_line,
                    start_column,
                )

            raise CompilationError(
                start_line,
                start_column,
                "expected '=' after '='",
            )

        # !=
        if char == "!":
            self.advance()

            if self.current() == ord("="):
                self.advance()

                return Token(
                    TOKEN_NOT_EQUAL,
                    "!=",
                    start_line,
                    start_column,
                )

            raise CompilationError(
                start_line,
                start_column,
                "expected '=' after '!'",
            )

        raise CompilationError(
            start_line,
            start_column,
            f"unexpected character {char!r}",
        )

    def tokenize(self):
        tokens = []

        while True:
            token = self.next_token()
            tokens.append(token)

            if token.kind == TOKEN_EOF:
                break

        return tokens


# ============================================================
# AST
# ============================================================

class ASTNode:
    def __init__(self, line, column):
        self.line = line
        self.column = column


class ProgramNode(ASTNode):
    def __init__(self, statements):
        if statements:
            line = statements[0].line
            column = statements[0].column
        else:
            line = 1
            column = 1

        super().__init__(line, column)
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
        else_body,
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


# ============================================================
# PARSER
# ============================================================

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0

    def peek(self):
        return self.tokens[self.index]

    def eat(self, kind):
        token = self.peek()

        if token.kind != kind:
            raise CompilationError(
                token.line,
                token.column,
                f"expected {kind}, got {token.kind}",
            )

        self.index += 1
        return token

    def parse_program(self):
        statements = []

        while self.peek().kind != TOKEN_EOF:
            statements.append(self.parse_statement())

        self.eat(TOKEN_EOF)

        return ProgramNode(statements)

    def parse_statement(self):
        token = self.peek()

        if token.kind in (
            TOKEN_NUM32,
            TOKEN_NUM64,
            TOKEN_BOOL,
        ):
            return self.parse_declaration()

        if token.kind == TOKEN_IDENTIFIER:
            return self.parse_assignment()

        if token.kind == TOKEN_IF:
            return self.parse_if_statement()

        raise CompilationError(
            token.line,
            token.column,
            f"unexpected token {token.text!r}",
        )

    def parse_declaration(self):
        type_token = self.peek()

        if type_token.kind == TOKEN_NUM32:
            self.eat(TOKEN_NUM32)
            var_type = "num32"

        elif type_token.kind == TOKEN_NUM64:
            self.eat(TOKEN_NUM64)
            var_type = "num64"

        elif type_token.kind == TOKEN_BOOL:
            self.eat(TOKEN_BOOL)
            var_type = "bool"

        else:
            raise CompilationError(
                type_token.line,
                type_token.column,
                "expected type",
            )

        mutable = False

        if self.peek().kind == TOKEN_MUT:
            self.eat(TOKEN_MUT)
            mutable = True

        name_token = self.eat(TOKEN_IDENTIFIER)

        self.eat(TOKEN_LBRACE)

        expression = self.parse_expression()

        self.eat(TOKEN_RBRACE)
        self.eat(TOKEN_SEMICOLON)

        return DeclarationNode(
            type_token.line,
            type_token.column,
            var_type,
            name_token.text,
            mutable,
            expression,
        )

    def parse_assignment(self):
        name_token = self.eat(TOKEN_IDENTIFIER)

        self.eat(TOKEN_ASSIGN)

        expression = self.parse_expression()

        self.eat(TOKEN_SEMICOLON)

        return AssignmentNode(
            name_token.line,
            name_token.column,
            name_token.text,
            expression,
        )

    def parse_if_statement(self):
        if_token = self.eat(TOKEN_IF)

        condition = self.parse_expression()

        self.eat(TOKEN_LBRACE)

        if_body = []

        if self.peek().kind == TOKEN_RBRACE:
            token = self.peek()

            raise CompilationError(
                token.line,
                token.column,
                "if block must contain at least one statement",
            )

        while self.peek().kind != TOKEN_RBRACE:
            if self.peek().kind == TOKEN_EOF:
                token = self.peek()

                raise CompilationError(
                    token.line,
                    token.column,
                    "expected '}'",
                )

            if_body.append(self.parse_statement())

        self.eat(TOKEN_RBRACE)

        else_body = None

        if self.peek().kind == TOKEN_ELSE:
            self.eat(TOKEN_ELSE)
            self.eat(TOKEN_LBRACE)

            else_body = []

            if self.peek().kind == TOKEN_RBRACE:
                token = self.peek()

                raise CompilationError(
                    token.line,
                    token.column,
                    "else block must contain at least one statement",
                )

            while self.peek().kind != TOKEN_RBRACE:
                if self.peek().kind == TOKEN_EOF:
                    token = self.peek()

                    raise CompilationError(
                        token.line,
                        token.column,
                        "expected '}'",
                    )

                else_body.append(self.parse_statement())

            self.eat(TOKEN_RBRACE)

        return IfNode(
            if_token.line,
            if_token.column,
            condition,
            if_body,
            else_body,
        )

    # expression = equality

    def parse_expression(self):
        return self.parse_equality()

    # equality = additive { ("==" | "!=") additive }

    def parse_equality(self):
        left = self.parse_additive()

        while self.peek().kind in (
            TOKEN_EQUAL,
            TOKEN_NOT_EQUAL,
        ):
            operator_token = self.peek()

            if operator_token.kind == TOKEN_EQUAL:
                self.eat(TOKEN_EQUAL)
            else:
                self.eat(TOKEN_NOT_EQUAL)

            right = self.parse_additive()

            left = BinaryExprNode(
                operator_token.line,
                operator_token.column,
                left,
                operator_token.text,
                right,
            )

        return left

    # additive = multiplicative { ("+" | "-") multiplicative }

    def parse_additive(self):
        left = self.parse_multiplicative()

        while self.peek().kind in (
            TOKEN_PLUS,
            TOKEN_MINUS,
        ):
            operator_token = self.peek()

            if operator_token.kind == TOKEN_PLUS:
                self.eat(TOKEN_PLUS)
            else:
                self.eat(TOKEN_MINUS)

            right = self.parse_multiplicative()

            left = BinaryExprNode(
                operator_token.line,
                operator_token.column,
                left,
                operator_token.text,
                right,
            )

        return left

    # multiplicative = primary { ("*" | "/") primary }

    def parse_multiplicative(self):
        left = self.parse_primary()

        while self.peek().kind in (
            TOKEN_STAR,
            TOKEN_SLASH,
        ):
            operator_token = self.peek()

            if operator_token.kind == TOKEN_STAR:
                self.eat(TOKEN_STAR)
            else:
                self.eat(TOKEN_SLASH)

            right = self.parse_primary()

            left = BinaryExprNode(
                operator_token.line,
                operator_token.column,
                left,
                operator_token.text,
                right,
            )

        return left

    def parse_primary(self):
        token = self.peek()

        if token.kind == TOKEN_INTEGER:
            self.eat(TOKEN_INTEGER)

            return IntegerNode(
                token.line,
                token.column,
                int(token.text),
            )

        if token.kind == TOKEN_TRUE:
            self.eat(TOKEN_TRUE)

            return BooleanNode(
                token.line,
                token.column,
                True,
            )

        if token.kind == TOKEN_FALSE:
            self.eat(TOKEN_FALSE)

            return BooleanNode(
                token.line,
                token.column,
                False,
            )

        if token.kind == TOKEN_IDENTIFIER:
            self.eat(TOKEN_IDENTIFIER)

            return IdentifierNode(
                token.line,
                token.column,
                token.text,
            )

        if token.kind == TOKEN_LPAREN:
            self.eat(TOKEN_LPAREN)

            expression = self.parse_expression()

            self.eat(TOKEN_RPAREN)

            return expression

        raise CompilationError(
            token.line,
            token.column,
            f"expected expression, got {token.text!r}",
        )


# ============================================================
# AST DUMP
# ============================================================

def dump_ast(node, depth=0):
    indent = "  " * depth

    if isinstance(node, ProgramNode):
        print(f"{indent}Program")

        for statement in node.statements:
            dump_ast(statement, depth + 1)

    elif isinstance(node, DeclarationNode):
        print(
            f"{indent}Declaration "
            f"line={node.line} "
            f"column={node.column}"
        )

        print(
            f"{indent}  type={node.var_type}"
        )

        print(
            f"{indent}  name={node.name}"
        )

        print(
            f"{indent}  mutable="
            f"{str(node.mutable).lower()}"
        )

        print(f"{indent}  value")
        dump_ast(node.expression, depth + 2)

    elif isinstance(node, AssignmentNode):
        print(
            f"{indent}Assignment "
            f"line={node.line} "
            f"column={node.column}"
        )

        print(
            f"{indent}  name={node.name}"
        )

        print(f"{indent}  value")
        dump_ast(node.expression, depth + 2)

    elif isinstance(node, IfNode):
        print(
            f"{indent}If "
            f"line={node.line} "
            f"column={node.column}"
        )

        print(f"{indent}  condition")
        dump_ast(node.condition, depth + 2)

        print(f"{indent}  then")

        for statement in node.if_body:
            dump_ast(statement, depth + 2)

        if node.else_body is not None:
            print(f"{indent}  else")

            for statement in node.else_body:
                dump_ast(statement, depth + 2)

    elif isinstance(node, IntegerNode):
        print(
            f"{indent}Integer "
            f"value={node.value} "
            f"line={node.line} "
            f"column={node.column}"
        )

    elif isinstance(node, BooleanNode):
        print(
            f"{indent}Boolean "
            f"value={str(node.value).lower()} "
            f"line={node.line} "
            f"column={node.column}"
        )

    elif isinstance(node, IdentifierNode):
        print(
            f"{indent}Identifier "
            f"name={node.name} "
            f"line={node.line} "
            f"column={node.column}"
        )

    elif isinstance(node, BinaryExprNode):
        print(
            f"{indent}BinaryExpr "
            f"operator={node.operator} "
            f"line={node.line} "
            f"column={node.column}"
        )

        print(f"{indent}  left")
        dump_ast(node.left, depth + 2)

        print(f"{indent}  right")
        dump_ast(node.right, depth + 2)

    else:
        raise RuntimeError(
            f"unknown AST node: {type(node).__name__}"
        )


# ============================================================
# COMPILER
# ============================================================

def compile_source(source):
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)

    return parser.parse_program()


# ============================================================
# CLI
# ============================================================

def main():
    if len(sys.argv) != 3 or sys.argv[1] != "--ast":
        print(
            "usage: python3 compiler.py --ast <input-file>",
            file=sys.stderr,
        )
        return 1

    filename = sys.argv[2]

    try:
        with open(
            filename,
            "r",
            encoding="utf-8",
        ) as file:
            source = file.read()

        ast = compile_source(source)

        dump_ast(ast)

        return 0

    except FileNotFoundError:
        print(
            f"compilation error: file not found: {filename}",
            file=sys.stderr,
        )
        return 1

    except CompilationError as error:
        print(
            "compilation error: "
            f"line {error.line}:{error.column}: "
            f"{error.message}",
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    sys.exit(main())