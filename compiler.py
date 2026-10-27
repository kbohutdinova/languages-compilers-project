import sys

class CompilationError(Exception):
    def __init__(self, line, column, message):
        self.line = line
        self.column = column
        self.message = message
        super().__init__(message)

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
TOKEN_ACTION = "ACTION"
TOKEN_SHAPE = "SHAPE"
TOKEN_GIVE = "GIVE"
TOKEN_READ = "READ"
TOKEN_PRINT = "PRINT"

TOKEN_ARROW = "ARROW"
TOKEN_DOT = "DOT"
TOKEN_COMMA = "COMMA"
TOKEN_STRING = "STRING"

KEYWORDS = {
    "num32": TOKEN_NUM32,
    "num64": TOKEN_NUM64,
    "bool": TOKEN_BOOL,
    "mut": TOKEN_MUT,
    "true": TOKEN_TRUE,
    "false": TOKEN_FALSE,
    "if": TOKEN_IF,
    "else": TOKEN_ELSE,
    "action": TOKEN_ACTION,
    "shape": TOKEN_SHAPE,
    "give": TOKEN_GIVE,
    "read": TOKEN_READ,
    "print": TOKEN_PRINT,
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

    def lex_string(self):
        start_line = self.line
        start_column = self.column

        self.advance()
        chars = []

        while self.current() is not None:
            byte = self.current()

            if byte == ord('"'):
                self.advance()
                return Token(
                    TOKEN_STRING,
                    "".join(chars),
                    start_line,
                    start_column,
                )

            if byte == ord("\n"):
                raise CompilationError(
                    start_line,
                    start_column,
                    "unterminated string literal",
                )

            if byte == ord("\\"):
                self.advance()
                escaped = self.current()

                escapes = {
                    ord("n"): "\n",
                    ord("t"): "\t",
                    ord('"'): '"',
                    ord("\\"): "\\",
                }

                if escaped not in escapes:
                    raise CompilationError(
                        self.line,
                        self.column,
                        "invalid string escape",
                    )

                chars.append(escapes[escaped])
                self.advance()
                continue

            if byte < 32 or byte > 126:
                raise CompilationError(
                    self.line,
                    self.column,
                    "invalid character in string",
                )

            chars.append(chr(byte))
            self.advance()

        raise CompilationError(
            start_line,
            start_column,
            "unterminated string literal",
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

        if byte > 127:
            raise CompilationError(
                start_line,
                start_column,
                "unexpected byte",
            )

        char = chr(byte)

        if char == '"':
            return self.lex_string()

        if char.isalpha():
            return self.lex_identifier()

        if char.isdigit():
            return self.lex_integer()

        if char == "{":
            self.advance()
            return Token(
                TOKEN_LBRACE,
                "{",
                start_line,
                start_column,
            )

        if char == "}":
            self.advance()
            return Token(
                TOKEN_RBRACE,
                "}",
                start_line,
                start_column,
            )

        if char == "(":
            self.advance()
            return Token(
                TOKEN_LPAREN,
                "(",
                start_line,
                start_column,
            )

        if char == ")":
            self.advance()
            return Token(
                TOKEN_RPAREN,
                ")",
                start_line,
                start_column,
            )

        if char == ";":
            self.advance()
            return Token(
                TOKEN_SEMICOLON,
                ";",
                start_line,
                start_column,
            )

        if char == ".":
            self.advance()
            return Token(
                TOKEN_DOT,
                ".",
                start_line,
                start_column,
            )

        if char == ",":
            self.advance()
            return Token(
                TOKEN_COMMA,
                ",",
                start_line,
                start_column,
            )

        if char == "+":
            self.advance()
            return Token(
                TOKEN_PLUS,
                "+",
                start_line,
                start_column,
            )

        if char == "-":
            self.advance()

            if self.current() == ord(">"):
                self.advance()
                return Token(
                    TOKEN_ARROW,
                    "->",
                    start_line,
                    start_column,
                )

            return Token(
                TOKEN_MINUS,
                "-",
                start_line,
                start_column,
            )

        if char == "*":
            self.advance()
            return Token(
                TOKEN_STAR,
                "*",
                start_line,
                start_column,
            )

        if char == "/":
            self.advance()
            return Token(
                TOKEN_SLASH,
                "/",
                start_line,
                start_column,
            )

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

class ParameterNode(ASTNode):
    def __init__(self, line, column, param_type, name):
        super().__init__(line, column)
        self.param_type = param_type
        self.name = name

class FunctionNode(ASTNode):
    def __init__(self, line, column, name, parameters, result_type, body):
        super().__init__(line, column)
        self.name = name
        self.parameters = parameters
        self.result_type = result_type
        self.body = body

class ReturnNode(StmtNode):
    def __init__(self, line, column, expression):
        super().__init__(line, column)
        self.expression = expression

class FieldNode(ASTNode):
    def __init__(self, line, column, field_type, name, mutable):
        super().__init__(line, column)
        self.field_type = field_type
        self.name = name
        self.mutable = mutable

class StructNode(ASTNode):
    def __init__(self, line, column, name, fields, methods):
        super().__init__(line, column)
        self.name = name
        self.fields = fields
        self.methods = methods

class CallNode(ExprNode):
    def __init__(self, line, column, callee, arguments):
        super().__init__(line, column)
        self.callee = callee
        self.arguments = arguments

class MemberAccessNode(ExprNode):
    def __init__(self, line, column, object_expression, name):
        super().__init__(line, column)
        self.object_expression = object_expression
        self.name = name

class ObjectCreationNode(ExprNode):
    def __init__(self, line, column, type_name, arguments):
        super().__init__(line, column)
        self.type_name = type_name
        self.arguments = arguments

class FieldAssignmentNode(StmtNode):
    def __init__(self, line, column, target, expression):
        super().__init__(line, column)
        self.target = target
        self.expression = expression

class PrintNode(StmtNode):
    def __init__(self, line, column, expression):
        super().__init__(line, column)
        self.expression = expression

class ReadNode(ExprNode):
    def __init__(self, line, column):
        super().__init__(line, column)

class StringNode(ExprNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = value

class ExpressionStatementNode(StmtNode):
    def __init__(self, line, column, expression):
        super().__init__(line, column)
        self.expression = expression

class UnaryExprNode(ExprNode):
    def __init__(self, line, column, operator, operand):
        super().__init__(line, column)
        self.operator = operator
        self.operand = operand

class Parser:
    def __init__(self, tokens):
        self.tokens = tokens
        self.index = 0
        self.condition_depth = 0

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
            if self.peek().kind == TOKEN_ACTION:
                statements.append(self.parse_function())
            elif self.peek().kind == TOKEN_SHAPE:
                statements.append(self.parse_struct())
            else:
                statements.append(self.parse_statement())

        self.eat(TOKEN_EOF)
        return ProgramNode(statements)

    def parse_type(self):
        token = self.peek()

        if token.kind in (
                TOKEN_NUM32,
                TOKEN_NUM64,
                TOKEN_BOOL,
                TOKEN_IDENTIFIER,
        ):
            self.eat(token.kind)
            return token.text

        raise CompilationError(
            token.line,
            token.column,
            "expected type",
        )

    def parse_function(self):
        start = self.eat(TOKEN_ACTION)
        name = self.eat(TOKEN_IDENTIFIER)
        self.eat(TOKEN_LPAREN)
        parameters = []

        if self.peek().kind != TOKEN_RPAREN:
            while True:
                token = self.peek()
                param_type = self.parse_type()
                param_name = self.eat(TOKEN_IDENTIFIER)
                parameters.append(ParameterNode(token.line, token.column, param_type, param_name.text))
                if self.peek().kind != TOKEN_COMMA:
                    break
                self.eat(TOKEN_COMMA)

        self.eat(TOKEN_RPAREN)
        self.eat(TOKEN_ARROW)
        result_type = self.parse_type()
        self.eat(TOKEN_LBRACE)
        body = []

        while self.peek().kind != TOKEN_RBRACE:
            if self.peek().kind == TOKEN_EOF:
                token = self.peek()
                raise CompilationError(token.line, token.column, "expected '}'")
            body.append(self.parse_statement())

        if not body:
            token = self.peek()
            raise CompilationError(token.line, token.column, "function body must contain at least one statement")

        self.eat(TOKEN_RBRACE)
        return FunctionNode(start.line, start.column, name.text, parameters, result_type, body)

    def parse_struct(self):
        start = self.eat(TOKEN_SHAPE)
        name = self.eat(TOKEN_IDENTIFIER)
        self.eat(TOKEN_LBRACE)
        fields = []
        methods = []

        while self.peek().kind != TOKEN_RBRACE:
            if self.peek().kind == TOKEN_EOF:
                token = self.peek()
                raise CompilationError(token.line, token.column, "expected '}'")
            if self.peek().kind == TOKEN_ACTION:
                methods.append(self.parse_function())
            else:
                fields.append(self.parse_field())

        if not fields and not methods:
            token = self.peek()
            raise CompilationError(token.line, token.column, "structure must contain at least one member")

        self.eat(TOKEN_RBRACE)
        return StructNode(start.line, start.column, name.text, fields, methods)

    def parse_field(self):
        token = self.peek()
        field_type = self.parse_type()
        mutable = False
        if self.peek().kind == TOKEN_MUT:
            self.eat(TOKEN_MUT)
            mutable = True
        name = self.eat(TOKEN_IDENTIFIER)
        self.eat(TOKEN_SEMICOLON)
        return FieldNode(token.line, token.column, field_type, name.text, mutable)

    def parse_return(self):
        token = self.eat(TOKEN_GIVE)
        expression = self.parse_expression()
        self.eat(TOKEN_SEMICOLON)
        return ReturnNode(token.line, token.column, expression)

    def parse_statement(self):
        token = self.peek()
        if token.kind in (TOKEN_NUM32, TOKEN_NUM64, TOKEN_BOOL):
            return self.parse_declaration()
        if token.kind == TOKEN_GIVE:
            return self.parse_return()
        if token.kind == TOKEN_IF:
            return self.parse_if_statement()
        if token.kind == TOKEN_PRINT:
            return self.parse_print()
        if token.kind == TOKEN_IDENTIFIER:
            if self.index + 1 < len(self.tokens) and self.tokens[self.index + 1].kind in (TOKEN_IDENTIFIER, TOKEN_MUT):
                return self.parse_declaration()
            return self.parse_assignment_or_call()
        raise CompilationError(token.line, token.column, f"unexpected token {token.text!r}")

    def parse_declaration(self):
        start = self.peek()
        var_type = self.parse_type()
        mutable = False

        if self.peek().kind == TOKEN_MUT:
            self.eat(TOKEN_MUT)
            mutable = True

        name = self.eat(TOKEN_IDENTIFIER)
        self.eat(TOKEN_LBRACE)

        if var_type in ("num32", "num64", "bool"):
            expression = self.parse_expression()
        else:
            arguments = []
            if self.peek().kind != TOKEN_RBRACE:
                arguments.append(self.parse_expression())
                while self.peek().kind == TOKEN_COMMA:
                    self.eat(TOKEN_COMMA)
                    arguments.append(self.parse_expression())
            expression = ObjectCreationNode(start.line, start.column, var_type, arguments)

        self.eat(TOKEN_RBRACE)
        self.eat(TOKEN_SEMICOLON)
        return DeclarationNode(start.line, start.column, var_type, name.text, mutable, expression)

    def parse_arguments(self):
        arguments = []
        if self.peek().kind != TOKEN_RPAREN:
            arguments.append(self.parse_expression())
            while self.peek().kind == TOKEN_COMMA:
                self.eat(TOKEN_COMMA)
                arguments.append(self.parse_expression())
        return arguments

    def parse_postfix(self, expression):
        while self.peek().kind in (TOKEN_DOT, TOKEN_LPAREN):
            if self.peek().kind == TOKEN_DOT:
                self.eat(TOKEN_DOT)
                member = self.eat(TOKEN_IDENTIFIER)
                expression = MemberAccessNode(member.line, member.column, expression, member.text)
            else:
                opening = self.eat(TOKEN_LPAREN)
                arguments = self.parse_arguments()
                self.eat(TOKEN_RPAREN)
                expression = CallNode(opening.line, opening.column, expression, arguments)
        return expression

    def parse_assignment_or_call(self):
        name = self.eat(TOKEN_IDENTIFIER)
        expression = self.parse_postfix(IdentifierNode(name.line, name.column, name.text))
        if self.peek().kind == TOKEN_ASSIGN:
            self.eat(TOKEN_ASSIGN)
            if not isinstance(expression, (IdentifierNode, MemberAccessNode)):
                raise CompilationError(name.line, name.column, "invalid assignment target")
            target_value = self.parse_expression()
            self.eat(TOKEN_SEMICOLON)
            if isinstance(expression, IdentifierNode):
                return AssignmentNode(name.line, name.column, name.text, target_value)
            return FieldAssignmentNode(name.line, name.column, expression, target_value)
        self.eat(TOKEN_SEMICOLON)
        if not isinstance(expression, CallNode):
            raise CompilationError(name.line, name.column, "expected assignment or call")
        return ExpressionStatementNode(name.line, name.column, expression)

    def parse_print(self):
        token = self.eat(TOKEN_PRINT)
        self.eat(TOKEN_LPAREN)
        if self.peek().kind == TOKEN_STRING:
            value = self.eat(TOKEN_STRING)
            expression = StringNode(value.line, value.column, value.text)
        else:
            expression = self.parse_expression()
        self.eat(TOKEN_RPAREN)
        self.eat(TOKEN_SEMICOLON)
        return PrintNode(token.line, token.column, expression)

    def parse_if_statement(self):
        if_token = self.eat(TOKEN_IF)

        self.condition_depth += 1
        try:
            condition = self.parse_expression()
        finally:
            self.condition_depth -= 1

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

    def parse_expression(self):
        return self.parse_equality()

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

    def parse_multiplicative(self):
        left = self.parse_unary()
        while self.peek().kind in (TOKEN_STAR, TOKEN_SLASH):
            operator = self.peek()
            self.eat(operator.kind)
            right = self.parse_unary()
            left = BinaryExprNode(operator.line, operator.column, left, operator.text, right)
        return left

    def parse_unary(self):
        if self.peek().kind == TOKEN_MINUS:
            token = self.eat(TOKEN_MINUS)
            return UnaryExprNode(token.line, token.column, "-", self.parse_unary())
        return self.parse_postfix(self.parse_primary())

    def parse_primary(self):
        token = self.peek()
        if token.kind == TOKEN_INTEGER:
            self.eat(TOKEN_INTEGER)
            return IntegerNode(token.line, token.column, int(token.text))
        if token.kind in (TOKEN_TRUE, TOKEN_FALSE):
            self.eat(token.kind)
            return BooleanNode(token.line, token.column, token.kind == TOKEN_TRUE)
        if token.kind == TOKEN_READ:
            self.eat(TOKEN_READ)
            self.eat(TOKEN_LPAREN)
            self.eat(TOKEN_RPAREN)
            return ReadNode(token.line, token.column)
        if token.kind == TOKEN_IDENTIFIER:
            self.eat(TOKEN_IDENTIFIER)
            if self.peek().kind == TOKEN_LBRACE and not self.condition_depth:
                self.eat(TOKEN_LBRACE)
                arguments = []
                if self.peek().kind != TOKEN_RBRACE:
                    arguments.append(self.parse_expression())
                    while self.peek().kind == TOKEN_COMMA:
                        self.eat(TOKEN_COMMA)
                        arguments.append(self.parse_expression())
                self.eat(TOKEN_RBRACE)
                return ObjectCreationNode(token.line, token.column, token.text, arguments)
            return IdentifierNode(token.line, token.column, token.text)
        if token.kind == TOKEN_LPAREN:
            self.eat(TOKEN_LPAREN)
            expression = self.parse_expression()
            self.eat(TOKEN_RPAREN)
            return expression
        raise CompilationError(token.line, token.column, f"expected expression, got {token.text!r}")


def dump_ast(node, depth=0):
    indent = "  " * depth

    if isinstance(node, ProgramNode):
        print(f"{indent}Program")

        for statement in node.statements:
            dump_ast(statement, depth + 1)

    elif isinstance(node, FunctionNode):
        print(f"{indent}Function name={node.name} result_type={node.result_type} line={node.line} column={node.column}")
        for param in node.parameters:
            dump_ast(param, depth + 1)
        for statement in node.body:
            dump_ast(statement, depth + 1)

    elif isinstance(node, ParameterNode):
        print(f"{indent}Parameter type={node.param_type} name={node.name} line={node.line} column={node.column}")

    elif isinstance(node, StructNode):
        print(f"{indent}Struct name={node.name} line={node.line} column={node.column}")
        for field in node.fields:
            dump_ast(field, depth + 1)
        for method in node.methods:
            dump_ast(method, depth + 1)

    elif isinstance(node, FieldNode):
        print(f"{indent}Field type={node.field_type} name={node.name} mutable={str(node.mutable).lower()} line={node.line} column={node.column}")

    elif isinstance(node, ReturnNode):
        print(f"{indent}Return line={node.line} column={node.column}")
        dump_ast(node.expression, depth + 1)

    elif isinstance(node, CallNode):
        print(f"{indent}Call line={node.line} column={node.column} arguments={len(node.arguments)}")
        dump_ast(node.callee, depth + 1)
        for argument in node.arguments:
            dump_ast(argument, depth + 1)

    elif isinstance(node, MemberAccessNode):
        print(f"{indent}MemberAccess name={node.name} line={node.line} column={node.column}")
        dump_ast(node.object_expression, depth + 1)

    elif isinstance(node, ObjectCreationNode):
        print(f"{indent}ObjectCreation type={node.type_name} line={node.line} column={node.column}")
        for argument in node.arguments:
            dump_ast(argument, depth + 1)

    elif isinstance(node, FieldAssignmentNode):
        print(f"{indent}FieldAssignment line={node.line} column={node.column}")
        dump_ast(node.target, depth + 1)
        dump_ast(node.expression, depth + 1)

    elif isinstance(node, PrintNode):
        print(f"{indent}Print line={node.line} column={node.column}")
        dump_ast(node.expression, depth + 1)

    elif isinstance(node, ReadNode):
        print(f"{indent}Read line={node.line} column={node.column}")

    elif isinstance(node, StringNode):
        print(f"{indent}String value={node.value!r} line={node.line} column={node.column}")

    elif isinstance(node, ExpressionStatementNode):
        print(f"{indent}ExpressionStatement line={node.line} column={node.column}")
        dump_ast(node.expression, depth + 1)

    elif isinstance(node, UnaryExprNode):
        print(f"{indent}UnaryExpr operator={node.operator} line={node.line} column={node.column}")
        dump_ast(node.operand, depth + 1)

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

def compile_source(source):
    lexer = Lexer(source)
    tokens = lexer.tokenize()

    parser = Parser(tokens)

    return parser.parse_program()

def main():
    if len(sys.argv) != 3:
        print("usage: python3 compiler.py --ast <input-file> | <input-file> <output.ll>", file=sys.stderr)
        return 1

    ast_mode = sys.argv[1] == "--ast"
    filename = sys.argv[2] if ast_mode else sys.argv[1]
    output = None if ast_mode else sys.argv[2]
    try:
        with open(filename, "r", encoding="utf-8") as source_file:
            ast = compile_source(source_file.read())
        if ast_mode:
            dump_ast(ast)
            return 0
        sys.modules["compiler"] = sys.modules["__main__"]
        from src.semantic import SemanticAnalyzer
        from src.codegen import CodeGenerator
        analyzer = SemanticAnalyzer()
        analyzer.analyze(ast)
        result = CodeGenerator(analyzer).generate(ast)
        with open(output, "w", encoding="utf-8") as target:
            target.write(result)
        return 0
    except CompilationError as error:
        if output is not None:
            import os
            if os.path.exists(output):
                os.remove(output)
        print(f"compilation error: line {error.line}:{error.column}: {error.message}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError, TypeError, OverflowError) as error:
        if output is not None:
            import os
            if os.path.exists(output):
                os.remove(output)
        print(f"compilation error: line 1:1: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
