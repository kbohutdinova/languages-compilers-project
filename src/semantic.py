from compiler import (
    CompilationError,
    ProgramNode,
    DeclarationNode,
    AssignmentNode,
    IfNode,
    IntegerNode,
    BooleanNode,
    IdentifierNode,
    BinaryExprNode,
    UnaryExprNode,
    FunctionNode, StructNode, ReturnNode, FieldAssignmentNode,
    MemberAccessNode, CallNode, ObjectCreationNode, PrintNode,
    ReadNode, StringNode, ExpressionStatementNode,
)


class Symbol:
    def __init__(self, name, symbol_type, mutable=False):
        self.name = name
        self.symbol_type = symbol_type
        self.mutable = mutable


class Scope:
    def __init__(self, parent=None):
        self.parent = parent
        self.symbols = {}

    def declare(self, symbol):
        if symbol.name in self.symbols:
            return False
        self.symbols[symbol.name] = symbol
        return True

    def lookup(self, name):
        if name in self.symbols:
            return self.symbols[name]
        if self.parent is not None:
            return self.parent.lookup(name)
        return None


class SemanticAnalyzer:
    LIMITS = {
        "num32": (-2147483648, 2147483647),
        "num64": (-9223372036854775808, 9223372036854775807),
    }

    def __init__(self):
        self.global_scope = Scope()
        self.current_scope = self.global_scope
        self.functions = {}
        self.structures = {}
        self.active_function = None
        self.active_struct = None
        self.fields_changed = set()

    def enter_scope(self):
        self.current_scope = Scope(self.current_scope)

    def leave_scope(self):
        if self.current_scope.parent is not None:
            self.current_scope = self.current_scope.parent

    def error(self, node, message):
        raise CompilationError(node.line, node.column, message)

    def analyze(self, program):
        if not isinstance(program, ProgramNode):
            self.error(program, "expected program")
        for node in program.statements:
            if isinstance(node, StructNode):
                if node.name in self.structures or node.name in self.functions or node.name in self.LIMITS or node.name == "bool":
                    self.error(node, f"duplicate name '{node.name}'")
                fields = {}
                for field in node.fields:
                    if field.name in fields:
                        self.error(field, f"duplicate field '{field.name}'")
                    fields[field.name] = field
                methods = {}
                for method in node.methods:
                    if method.name in methods or method.name in fields:
                        self.error(method, f"duplicate member '{method.name}'")
                    methods[method.name] = method
                self.structures[node.name] = (fields, methods)
        for node in program.statements:
            if isinstance(node, FunctionNode):
                if node.name in self.functions or node.name in self.structures:
                    self.error(node, f"duplicate function '{node.name}'")
                self.functions[node.name] = node
        for node in program.statements:
            if isinstance(node, StructNode):
                for field in node.fields:
                    self.check_known_type(field, field.field_type)
                for method in node.methods:
                    self.check_function_signature(method)
            elif isinstance(node, FunctionNode):
                self.check_function_signature(node)
        for node in program.statements:
            if isinstance(node, StructNode):
                for method in node.methods:
                    self.analyze_function(method, node.name)
            elif isinstance(node, FunctionNode):
                self.analyze_function(node)
            else:
                self.analyze_statement(node)

    def analyze_statement(self, node):
        if isinstance(node, DeclarationNode):
            self.check_known_type(node, node.var_type)
            value_type, constant = self.expression_type(node.expression)
            self.check_assignment_type(node.expression, node.var_type, value_type, constant)
            if not self.current_scope.declare(Symbol(node.name, node.var_type, node.mutable)):
                self.error(node, f"duplicate declaration '{node.name}'")
            return

        if isinstance(node, AssignmentNode):
            symbol = self.current_scope.lookup(node.name)
            if symbol is None and self.active_struct is not None:
                fields, _ = self.structures[self.active_struct]
                if node.name in fields:
                    field = fields[node.name]
                    if not field.mutable:
                        self.error(node, f"cannot assign to immutable field '{node.name}'")
                    value_type, constant = self.expression_type(node.expression)
                    self.check_assignment_type(node.expression, field.field_type, value_type, constant)
                    self.fields_changed.add((self.active_struct, self.active_function.name))
                    return
            if symbol is None:
                self.error(node, f"unknown variable '{node.name}'")
            if not symbol.mutable:
                self.error(node, f"cannot assign to immutable variable '{node.name}'")
            value_type, constant = self.expression_type(node.expression)
            self.check_assignment_type(node.expression, symbol.symbol_type, value_type, constant)
            return

        if isinstance(node, IfNode):
            condition_type, _ = self.expression_type(node.condition)
            if condition_type != "bool":
                self.error(node.condition, "if condition must be bool")
            self.enter_scope()
            try:
                for statement in node.if_body:
                    self.analyze_statement(statement)
            finally:
                self.leave_scope()
            if node.else_body is not None:
                self.enter_scope()
                try:
                    for statement in node.else_body:
                        self.analyze_statement(statement)
                finally:
                    self.leave_scope()
            return

        if isinstance(node, ReturnNode):
            if self.active_function is None:
                self.error(node, "give outside function")
            value_type, constant = self.expression_type(node.expression)
            self.check_assignment_type(node.expression, self.active_function.result_type, value_type, constant)
            return
        if isinstance(node, FieldAssignmentNode):
            target_type, mutable, field = self.resolve_access(node.target)
            if not mutable:
                self.error(node, "cannot assign through immutable chain")
            value_type, constant = self.expression_type(node.expression)
            self.check_assignment_type(node.expression, target_type, value_type, constant)
            if self.active_struct is not None and isinstance(node.target.object_expression, IdentifierNode):
                if self.current_scope.lookup(node.target.object_expression.name) is None:
                    self.fields_changed.add((self.active_struct, self.active_function.name))
            return
        if isinstance(node, (PrintNode, ExpressionStatementNode)):
            kind, _ = self.expression_type(node.expression)
            if isinstance(node, PrintNode) and kind == "string":
                return
            return
        self.error(node, f"semantic analysis not implemented for {type(node).__name__}")

    def check_assignment_type(self, node, target_type, value_type, constant):
        if target_type in self.structures:
            if value_type != target_type:
                self.error(node, f"expected {target_type}, got {value_type}")
            return
        if target_type == "bool":
            if value_type != "bool":
                self.error(node, "expected bool value")
            return

        if value_type == "integer_literal":
            low, high = self.LIMITS[target_type]
            if constant is not None and not low <= constant <= high:
                self.error(node, f"integer overflow for {target_type}")
            return

        if value_type != target_type:
            self.error(node, f"expected {target_type}, got {value_type}")

    def expression_type(self, node):
        if isinstance(node, IntegerNode):
            return "integer_literal", node.value

        if isinstance(node, BooleanNode):
            return "bool", node.value

        if isinstance(node, IdentifierNode):
            symbol = self.current_scope.lookup(node.name)
            if symbol is not None:
                return symbol.symbol_type, None
            if self.active_struct is not None:
                fields, _ = self.structures[self.active_struct]
                if node.name in fields:
                    return fields[node.name].field_type, None
            self.error(node, f"unknown variable '{node.name}'")

        if isinstance(node, UnaryExprNode):
            operand_type, constant = self.expression_type(node.operand)
            if node.operator != "-" or operand_type not in ("num32", "num64", "integer_literal"):
                self.error(node, "invalid unary operation")
            if operand_type == "integer_literal":
                return "integer_literal", -constant
            return operand_type, None

        if isinstance(node, BinaryExprNode):
            left_type, left_constant = self.expression_type(node.left)
            right_type, right_constant = self.expression_type(node.right)
            if node.operator in ("==", "!="):
                if left_type == "integer_literal" and right_type in self.LIMITS:
                    self.check_assignment_type(node.left, right_type, left_type, left_constant)
                elif right_type == "integer_literal" and left_type in self.LIMITS:
                    self.check_assignment_type(node.right, left_type, right_type, right_constant)
                elif left_type != right_type:
                    self.error(node, "incompatible comparison types")
                return "bool", None

            if node.operator not in ("+", "-", "*", "/"):
                self.error(node, f"unknown operator '{node.operator}'")
            if left_type not in (*self.LIMITS, "integer_literal") or right_type not in (*self.LIMITS, "integer_literal"):
                self.error(node, "arithmetic requires integers")
            if left_type == "integer_literal" and right_type == "integer_literal":
                if node.operator == "+":
                    return "integer_literal", left_constant + right_constant
                if node.operator == "-":
                    return "integer_literal", left_constant - right_constant
                if node.operator == "*":
                    return "integer_literal", left_constant * right_constant
                if right_constant == 0:
                    self.error(node, "division by zero")
                magnitude = abs(left_constant) // abs(right_constant)
                return "integer_literal", -magnitude if (left_constant < 0) != (right_constant < 0) else magnitude
            if left_type == "integer_literal":
                self.check_assignment_type(node.left, right_type, left_type, left_constant)
                return right_type, None
            if right_type == "integer_literal":
                self.check_assignment_type(node.right, left_type, right_type, right_constant)
                return left_type, None
            if left_type != right_type:
                self.error(node, "arithmetic operands must have the same type")
            return left_type, None

        if isinstance(node, ReadNode):
            return "integer_literal", None
        if isinstance(node, StringNode):
            return "string", None
        if isinstance(node, ObjectCreationNode):
            if node.type_name not in self.structures:
                self.error(node, f"unknown structure '{node.type_name}'")
            fields, _ = self.structures[node.type_name]
            if len(node.arguments) != len(fields):
                self.error(node, f"wrong field count for {node.type_name}")
            for arg, field in zip(node.arguments, fields.values()):
                actual, constant = self.expression_type(arg)
                self.check_assignment_type(arg, field.field_type, actual, constant)
            return node.type_name, None
        if isinstance(node, MemberAccessNode):
            kind, _, _ = self.resolve_access(node)
            return kind, None
        if isinstance(node, CallNode):
            if isinstance(node.callee, IdentifierNode):
                name = node.callee.name
                symbol = self.current_scope.lookup(name)
                if symbol is not None:
                    self.error(node, f"'{name}' is not a function")
                if self.active_struct is not None and name in self.structures[self.active_struct][1]:
                    method = self.structures[self.active_struct][1][name]
                    return self.check_call(node, method)
                if name not in self.functions:
                    self.error(node, f"unknown function '{name}'")
                return self.check_call(node, self.functions[name])
            if isinstance(node.callee, MemberAccessNode):
                receiver = node.callee.object_expression
                receiver_type, _ = self.expression_type(receiver)
                if receiver_type not in self.structures:
                    self.error(node, "method call requires an object")
                methods = self.structures[receiver_type][1]
                name = node.callee.name
                if name not in methods:
                    self.error(node, f"unknown method '{name}'")
                method = methods[name]
                if self.method_is_mutating(receiver_type, method.name, set()):
                    _, mutable = self.resolve_receiver(receiver)
                    if not mutable:
                        self.error(node, "cannot call mutating method on immutable object")
                return self.check_call(node, method)
            self.error(node, "invalid function call")
        self.error(node, f"expression type not implemented for {type(node).__name__}")

    def check_known_type(self, node, name):
        if name not in (*self.LIMITS, "bool") and name not in self.structures:
            self.error(node, f"unknown type '{name}'")

    def check_function_signature(self, function):
        self.check_known_type(function, function.result_type)
        names = set()
        for parameter in function.parameters:
            self.check_known_type(parameter, parameter.param_type)
            if parameter.name in names:
                self.error(parameter, f"duplicate parameter '{parameter.name}'")
            names.add(parameter.name)

    def analyze_function(self, function, struct_name=None):
        old_scope = self.current_scope
        old_function = self.active_function
        old_struct = self.active_struct
        self.current_scope = Scope(self.global_scope)
        self.active_function = function
        self.active_struct = struct_name
        try:
            for parameter in function.parameters:
                self.current_scope.declare(Symbol(parameter.name, parameter.param_type, True))
            for stmt in function.body:
                self.analyze_statement(stmt)
            if not any(isinstance(stmt, ReturnNode) for stmt in self.walk_statements(function.body)):
                self.error(function, "function has no give statement")
        finally:
            self.current_scope = old_scope
            self.active_function = old_function
            self.active_struct = old_struct

    def check_call(self, node, function):
        if len(node.arguments) != len(function.parameters):
            self.error(node, f"wrong argument count for '{function.name}': expected {len(function.parameters)}, got {len(node.arguments)}")
        for argument, parameter in zip(node.arguments, function.parameters):
            kind, constant = self.expression_type(argument)
            self.check_assignment_type(argument, parameter.param_type, kind, constant)
        return function.result_type, None

    def resolve_receiver(self, node):
        if isinstance(node, IdentifierNode):
            symbol = self.current_scope.lookup(node.name)
            if symbol is not None:
                return symbol.symbol_type, symbol.mutable
            if self.active_struct is not None:
                fields, _ = self.structures[self.active_struct]
                if node.name in fields:
                    field = fields[node.name]
                    return field.field_type, field.mutable
            self.error(node, f"unknown variable '{node.name}'")
        if isinstance(node, MemberAccessNode):
            kind, mutable, _ = self.resolve_access(node)
            return kind, mutable
        kind, _ = self.expression_type(node)
        return kind, False

    def resolve_access(self, node):
        parent_type, parent_mutable = self.resolve_receiver(node.object_expression)
        if parent_type not in self.structures:
            self.error(node, "field access requires a structure")
        fields, _ = self.structures[parent_type]
        if node.name not in fields:
            self.error(node, f"unknown field '{node.name}'")
        field = fields[node.name]
        return field.field_type, parent_mutable and field.mutable, field

    def method_is_mutating(self, struct_name, method_name, visiting):
        key = (struct_name, method_name)
        if key in self.fields_changed:
            return True
        if key in visiting:
            return False
        visiting.add(key)
        method = self.structures[struct_name][1][method_name]
        for stmt in self.walk_statements(method.body):
            if isinstance(stmt, AssignmentNode) and stmt.name in self.structures[struct_name][0] and stmt.name not in {p.name for p in method.parameters}:
                return True
            if isinstance(stmt, FieldAssignmentNode):
                first = stmt.target
                while isinstance(first, MemberAccessNode):
                    first = first.object_expression
                if isinstance(first, IdentifierNode):
                    if first.name in self.structures[struct_name][0] and first.name not in {p.name for p in method.parameters}:
                        return True
            for expr in self.statement_expressions(stmt):
                for call in self.walk_calls(expr):
                    if isinstance(call.callee, IdentifierNode) and call.callee.name in self.structures[struct_name][1]:
                        if self.method_is_mutating(struct_name, call.callee.name, visiting):
                            return True
        return False

    def walk_statements(self, statements):
        for stmt in statements:
            yield stmt
            if isinstance(stmt, IfNode):
                yield from self.walk_statements(stmt.if_body)
                if stmt.else_body:
                    yield from self.walk_statements(stmt.else_body)

    def statement_expressions(self, stmt):
        return [getattr(stmt, name) for name in ("expression", "condition") if hasattr(stmt, name)]

    def walk_calls(self, node):
        if isinstance(node, CallNode):
            yield node
            yield from self.walk_calls(node.callee)
            for arg in node.arguments:
                yield from self.walk_calls(arg)
        elif isinstance(node, MemberAccessNode):
            yield from self.walk_calls(node.object_expression)
        elif isinstance(node, BinaryExprNode):
            yield from self.walk_calls(node.left)
            yield from self.walk_calls(node.right)
        elif isinstance(node, UnaryExprNode):
            yield from self.walk_calls(node.operand)
