from llvmlite import ir
from compiler import (CompilationError, DeclarationNode, AssignmentNode, IfNode, IntegerNode, BooleanNode, IdentifierNode, BinaryExprNode, UnaryExprNode, FunctionNode, StructNode, ReturnNode, FieldAssignmentNode, MemberAccessNode, CallNode, ObjectCreationNode, PrintNode, ReadNode, StringNode, ExpressionStatementNode)


class CodeGenerator:
    def __init__(self, analyzer):
        self.semantic = analyzer
        self.module = ir.Module(name="KameLang")
        self.module.triple = ""
        self.i32 = ir.IntType(32)
        self.i64 = ir.IntType(64)
        self.i8 = ir.IntType(8)
        self.bool = ir.IntType(1)
        self.struct_types = {}
        self.functions = {}
        self.methods = {}
        self.builder = None
        self.scopes = []
        self.current_struct = None
        self.self_ptr = None
        self.current_return = None
        self.string_counter = 0
        self.printf = ir.Function(self.module, ir.FunctionType(self.i32, [self.i8.as_pointer()], var_arg=True), name="printf")
        self.scanf = ir.Function(self.module, ir.FunctionType(self.i32, [self.i8.as_pointer()], var_arg=True), name="scanf")
        self.exit_function = ir.Function(self.module, ir.FunctionType(ir.VoidType(), [self.i32]), name="exit")
        self.overflow_functions = {}

    def type(self, name):
        if name == "num32":
            return self.i32
        if name == "num64":
            return self.i64
        if name == "bool":
            return self.bool
        return self.struct_types[name]

    def literal(self, text):
        data = text.encode("utf-8") + b"\0"
        arr_type = ir.ArrayType(self.i8, len(data))
        name = f".str.{self.string_counter}"
        self.string_counter += 1
        global_var = ir.GlobalVariable(self.module, arr_type, name=name)
        global_var.linkage = "internal"
        global_var.global_constant = True
        global_var.initializer = ir.Constant(arr_type, bytearray(data))
        return self.builder.gep(global_var, [ir.Constant(self.i32, 0), ir.Constant(self.i32, 0)], inbounds=True)

    def fmt_print(self, fmt, *values):
        self.builder.call(self.printf, [self.literal(fmt), *values])

    def alloca(self, typ, name):
        return self.builder.alloca(typ, name=name)

    def enter(self):
        self.scopes.append({})

    def leave(self):
        self.scopes.pop()

    def bind(self, name, address, typ):
        self.scopes[-1][name] = (address, typ)

    def lookup(self, name):
        for scope in reversed(self.scopes):
            if name in scope:
                return scope[name]
        if self.current_struct is not None:
            fields = self.semantic.structures[self.current_struct][0]
            if name in fields:
                index = list(fields).index(name)
                field = fields[name]
                ptr = self.builder.gep(self.self_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, index)], inbounds=True)
                return ptr, field.field_type
        raise ValueError(f"unknown identifier {name}")

    def as_type(self, value, target):
        if value.type == target:
            return value
        if isinstance(value, ir.Constant) and isinstance(value.type, ir.IntType) and isinstance(target, ir.IntType):
            return ir.Constant(target, value.constant)
        if isinstance(value.type, ir.IntType) and isinstance(target, ir.IntType):
            if value.type.width < target.width:
                return self.builder.sext(value, target)
            if value.type.width > target.width:
                return self.builder.trunc(value, target)
        raise ValueError(f"cannot convert {value.type} to {target}")

    def failure_if(self, condition, message):
        function = self.builder.function
        failure = function.append_basic_block("arith.error")
        continuation = function.append_basic_block("arith.ok")
        self.builder.cbranch(condition, failure, continuation)
        self.builder.position_at_end(failure)
        self.fmt_print(message + "\n")
        self.builder.call(self.exit_function, [ir.Constant(self.i32, 1)])
        self.builder.unreachable()
        self.builder.position_at_end(continuation)

    def checked_operation(self, operator, left, right):
        width = left.type.width
        if operator in ("+", "-", "*"):
            names = {"+": "sadd", "-": "ssub", "*": "smul"}
            operation = names[operator]
            key = (operation, width)
            if key not in self.overflow_functions:
                result_type = ir.LiteralStructType([left.type, self.bool])
                signature = ir.FunctionType(result_type, [left.type, left.type])
                self.overflow_functions[key] = ir.Function(
                    self.module,
                    signature,
                    name=f"llvm.{operation}.with.overflow.i{width}",
                )
            packed = self.builder.call(self.overflow_functions[key], [left, right])
            result = self.builder.extract_value(packed, 0)
            overflow = self.builder.extract_value(packed, 1)
            self.failure_if(overflow, "integer overflow")
            return result
        if operator == "/":
            is_zero = self.builder.icmp_signed("==", right, ir.Constant(left.type, 0))
            self.failure_if(is_zero, "division by zero")
            minimum = -(1 << (width - 1))
            is_min = self.builder.icmp_signed("==", left, ir.Constant(left.type, minimum))
            is_negative_one = self.builder.icmp_signed("==", right, ir.Constant(left.type, -1))
            overflow = self.builder.and_(is_min, is_negative_one)
            self.failure_if(overflow, "integer overflow")
            return self.builder.sdiv(left, right)
        raise ValueError(f"unsupported arithmetic operator {operator}")

    def address(self, expr):
        if isinstance(expr, IdentifierNode):
            return self.lookup(expr.name)
        if isinstance(expr, MemberAccessNode):
            parent_ptr, parent_type = self.address(expr.object_expression)
            fields = self.semantic.structures[parent_type][0]
            index = list(fields).index(expr.name)
            field = fields[expr.name]
            ptr = self.builder.gep(parent_ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, index)], inbounds=True)
            return ptr, field.field_type
        value, typ = self.expr(expr)
        ptr = self.alloca(self.type(typ), "temporary")
        self.builder.store(value, ptr)
        return ptr, typ

    def expr(self, node, hint=None):
        if isinstance(node, IntegerNode):
            typ = hint if hint in ("num32", "num64") else "num32"
            return ir.Constant(self.type(typ), node.value), typ
        if isinstance(node, BooleanNode):
            return ir.Constant(self.bool, int(node.value)), "bool"
        if isinstance(node, IdentifierNode):
            ptr, typ = self.lookup(node.name)
            return self.builder.load(ptr), typ
        if isinstance(node, MemberAccessNode):
            ptr, typ = self.address(node)
            return self.builder.load(ptr), typ
        if isinstance(node, UnaryExprNode):
            val, typ = self.expr(node.operand, hint)
            return self.checked_operation("-", ir.Constant(val.type, 0), val), typ
        if isinstance(node, BinaryExprNode):
            a, at = self.expr(node.left, hint)
            b, bt = self.expr(node.right, at if at in ("num32", "num64") else hint)
            if at != bt and at in ("num32", "num64") and isinstance(node.right, IntegerNode):
                b = self.as_type(b, a.type)
            elif at != bt and bt in ("num32", "num64") and isinstance(node.left, IntegerNode):
                a = self.as_type(a, b.type)
            op = node.operator
            if op in ("+", "-", "*", "/"):
                result_type = at if at == bt else (bt if isinstance(node.left, IntegerNode) else at)
                return self.checked_operation(op, a, b), result_type
            return self.builder.icmp_signed(op, a, b), "bool"
        if isinstance(node, ObjectCreationNode):
            fields = self.semantic.structures[node.type_name][0]
            value = ir.Constant(self.type(node.type_name), None)
            for index, (arg, field) in enumerate(zip(node.arguments, fields.values())):
                part, _ = self.expr(arg, field.field_type)
                value = self.builder.insert_value(value, self.as_type(part, self.type(field.field_type)), index)
            return value, node.type_name
        if isinstance(node, CallNode):
            if isinstance(node.callee, IdentifierNode):
                name = node.callee.name
                if self.current_struct and (self.current_struct, name) in self.methods:
                    function = self.methods[(self.current_struct, name)]
                    args = [self.self_ptr]
                else:
                    function = self.functions[name]
                    args = []
            else:
                ptr, receiver_type = self.address(node.callee.object_expression)
                function = self.methods[(receiver_type, node.callee.name)]
                args = [ptr]
            for param, arg in zip(list(function.args)[len(args):], node.arguments):
                value, _ = self.expr(arg, "num64" if param.type == self.i64 else "num32" if param.type == self.i32 else None)
                args.append(self.as_type(value, param.type))
            result = self.builder.call(function, args)
            return result, self.name_type(function.function_type.return_type)
        if isinstance(node, ReadNode):
            typ = "num64" if hint == "num64" else "num32"
            slot = self.alloca(self.type(typ), "readvalue")
            self.builder.call(self.scanf, [self.literal("%lld" if typ == "num64" else "%d"), slot])
            return self.builder.load(slot), typ
        if isinstance(node, StringNode):
            return self.literal(node.value), "string"
        raise ValueError(f"unsupported expression {type(node).__name__}")

    def name_type(self, typ):
        if typ == self.i32:
            return "num32"
        if typ == self.i64:
            return "num64"
        if typ == self.bool:
            return "bool"
        for name, struct_type in self.struct_types.items():
            if typ == struct_type:
                return name
        raise ValueError(str(typ))

    def output(self, expr):
        if isinstance(expr, StringNode):
            self.fmt_print("%s\n", self.literal(expr.value))
            return
        value, typ = self.expr(expr)
        if typ == "bool":
            true_block = self.builder.function.append_basic_block("bool.true")
            false_block = self.builder.function.append_basic_block("bool.false")
            end_block = self.builder.function.append_basic_block("bool.end")
            self.builder.cbranch(value, true_block, false_block)
            self.builder.position_at_end(true_block)
            self.fmt_print("true\n")
            self.builder.branch(end_block)
            self.builder.position_at_end(false_block)
            self.fmt_print("false\n")
            self.builder.branch(end_block)
            self.builder.position_at_end(end_block)
        elif typ in self.semantic.structures:
            ptr = self.alloca(self.type(typ), "printobject")
            self.builder.store(value, ptr)
            self.fmt_print(typ + "{")
            fields = list(self.semantic.structures[typ][0].values())
            for i, field in enumerate(fields):
                if i:
                    self.fmt_print(", ")
                self.fmt_print(field.name + "=")
                address = self.builder.gep(ptr, [ir.Constant(self.i32, 0), ir.Constant(self.i32, i)])
                field_value = self.builder.load(address)
                if field.field_type == "bool":
                    self.fmt_print("%s", self.builder.select(field_value, self.literal("true"), self.literal("false")))
                elif field.field_type in ("num32", "num64"):
                    self.fmt_print("%lld" if field.field_type == "num64" else "%d", field_value)
                else:
                    self.fmt_print("<object>")
            self.fmt_print("}\n")
        else:
            self.fmt_print("%lld\n" if typ == "num64" else "%d\n", value)

    def statement(self, node):
        if self.builder.block.is_terminated:
            return
        if isinstance(node, DeclarationNode):
            value, _ = self.expr(node.expression, node.var_type)
            ptr = self.alloca(self.type(node.var_type), node.name)
            self.builder.store(self.as_type(value, self.type(node.var_type)), ptr)
            self.bind(node.name, ptr, node.var_type)
        elif isinstance(node, AssignmentNode):
            ptr, typ = self.lookup(node.name)
            value, _ = self.expr(node.expression, typ)
            self.builder.store(self.as_type(value, self.type(typ)), ptr)
        elif isinstance(node, FieldAssignmentNode):
            ptr, typ = self.address(node.target)
            value, _ = self.expr(node.expression, typ)
            self.builder.store(self.as_type(value, self.type(typ)), ptr)
        elif isinstance(node, PrintNode):
            self.output(node.expression)
        elif isinstance(node, ExpressionStatementNode):
            self.expr(node.expression)
        elif isinstance(node, ReturnNode):
            value, _ = self.expr(node.expression, self.current_return)
            self.builder.ret(self.as_type(value, self.type(self.current_return)))
        elif isinstance(node, IfNode):
            condition, _ = self.expr(node.condition)
            function = self.builder.function
            then_block = function.append_basic_block("if.then")
            else_block = function.append_basic_block("if.else")
            end_block = function.append_basic_block("if.end")
            self.builder.cbranch(condition, then_block, else_block)
            self.builder.position_at_end(then_block)
            self.enter()
            for child in node.if_body:
                self.statement(child)
            self.leave()
            if not self.builder.block.is_terminated:
                self.builder.branch(end_block)
            self.builder.position_at_end(else_block)
            self.enter()
            for child in node.else_body or []:
                self.statement(child)
            self.leave()
            if not self.builder.block.is_terminated:
                self.builder.branch(end_block)
            self.builder.position_at_end(end_block)
        else:
            raise ValueError(f"unsupported statement {type(node).__name__}")

    def generate(self, program):
        for node in program.statements:
            if isinstance(node, StructNode):
                self.struct_types[node.name] = self.module.context.get_identified_type("kame." + node.name)
        for name, (fields, _) in self.semantic.structures.items():
            self.struct_types[name].set_body(*(self.type(field.field_type) for field in fields.values()))
        for node in program.statements:
            if isinstance(node, FunctionNode):
                args = [self.type(param.param_type) for param in node.parameters]
                self.functions[node.name] = ir.Function(self.module, ir.FunctionType(self.type(node.result_type), args), name="kame_fn_" + node.name)
            if isinstance(node, StructNode):
                for method in node.methods:
                    args = [self.type(node.name).as_pointer()] + [self.type(param.param_type) for param in method.parameters]
                    self.methods[(node.name, method.name)] = ir.Function(self.module, ir.FunctionType(self.type(method.result_type), args), name="kame_method_" + node.name + "_" + method.name)
        for node in program.statements:
            if isinstance(node, FunctionNode):
                self.function_body(node, self.functions[node.name])
            if isinstance(node, StructNode):
                for method in node.methods:
                    self.function_body(method, self.methods[(node.name, method.name)], node.name)
        main = ir.Function(self.module, ir.FunctionType(self.i32, []), name="main")
        self.builder = ir.IRBuilder(main.append_basic_block("entry"))
        self.scopes = []
        self.enter()
        self.current_struct = None
        self.current_return = "num32"
        for node in program.statements:
            if not isinstance(node, (FunctionNode, StructNode)):
                self.statement(node)
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(self.i32, 0))
        return str(self.module)

    def function_body(self, node, function, struct_name=None):
        self.builder = ir.IRBuilder(function.append_basic_block("entry"))
        self.scopes = []
        self.enter()
        self.current_struct = struct_name
        self.current_return = node.result_type
        self.self_ptr = function.args[0] if struct_name else None
        offset = 1 if struct_name else 0
        for parameter, value in zip(node.parameters, list(function.args)[offset:]):
            ptr = self.alloca(value.type, parameter.name)
            self.builder.store(value, ptr)
            self.bind(parameter.name, ptr, parameter.param_type)
        for statement in node.body:
            self.statement(statement)
        if not self.builder.block.is_terminated:
            self.builder.ret(ir.Constant(self.type(node.result_type), None))
