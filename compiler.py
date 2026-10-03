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
    def __init__(self, line, column, var_type, name, mutable, expression):
        super().__init__(line, column)
        self.var_type = var_type
        self.name = name
        self.mutable = mutable
        self.expression = expression

class AssignmentNode(StmtNode):
    def __init__(self, line, column, name, expression):
        super().__init__(line, column)
        self.name = name
        self.expression = expression

class IfNode(StmtNode):
    def __init__(self, line, column, condition, if_body, else_body=None):
        super().__init__(line, column)
        self.condition = condition
        self.if_body = if_body
        self.else_body = else_body

class IntegerNode(ExprNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = value

class BooleanNode(ExprNode):
    def __init__(self, line, column, value):
        super().__init__(line, column)
        self.value = value

class IdentifierNode(ExprNode):
    def __init__(self, line, column, name):
        super().__init__(line, column)
        self.name = name

class BinaryExprNode(ExprNode):
    def __init__(self, line, column, left, operator, right):
        super().__init__(line, column)
        self.left = left
        self.operator = operator
        self.right = right


