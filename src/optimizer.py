"""Conservative checked-AST optimizations for KameLang Stage 3.

The optimizer deliberately leaves unsupported inlining shapes unchanged, and never
eliminates effectful expressions (including arithmetic that can trap).
"""
import copy
from collections import Counter
from compiler import (
    ProgramNode, FunctionNode, StructNode, DeclarationNode, AssignmentNode,
    FieldAssignmentNode, IfNode, WhileNode, ForNode, ReturnNode, PrintNode,
    ExpressionStatementNode, IdentifierNode, MemberAccessNode, CallNode,
    IntegerNode, BooleanNode, UnaryExprNode, BinaryExprNode, ObjectCreationNode,
    ReadNode, StringNode,
)


def walk(node):
    if isinstance(node, list):
        for child in node:
            yield from walk(child)
    elif hasattr(node, '__dict__'):
        yield node
        for value in vars(node).values():
            if isinstance(value, list) or hasattr(value, 'line'):
                yield from walk(value)


def inline_pure(expr):
    if pure(expr):
        return True
    if isinstance(expr, (UnaryExprNode, BinaryExprNode)):
        return all(inline_pure(x) for x in ([expr.operand] if isinstance(expr, UnaryExprNode) else [expr.left, expr.right]))
    return False


def pure(expr):
    # Arithmetic is not pure for this purpose because it can trap at run time.
    if isinstance(expr, (IntegerNode, BooleanNode, IdentifierNode, StringNode)):
        return True
    if isinstance(expr, ObjectCreationNode):
        return all(pure(x) for x in expr.arguments)
    return False


def direct_call(node):
    return isinstance(node, CallNode) and isinstance(node.callee, IdentifierNode)


def calls_in(node):
    return [n.callee.name for n in walk(node) if direct_call(n)]


def function_counts(program):
    counts = Counter()
    for node in program.statements:
        if isinstance(node, FunctionNode):
            counts.update(calls_in(node.body))
        elif isinstance(node, StructNode):
            for m in node.methods:
                counts.update(calls_in(m.body))
        else:
            counts.update(calls_in(node))
    return counts


def remove_unused_functions(program):
    changed = False
    while True:
        counts = function_counts(program)
        unused = {n.name for n in program.statements if isinstance(n, FunctionNode) and counts[n.name] == 0}
        if not unused:
            break
        program.statements = [n for n in program.statements if not (isinstance(n, FunctionNode) and n.name in unused)]
        changed = True
    return changed


class Binding:
    def __init__(self, declaration=None, protected=False):
        self.declaration = declaration
        self.protected = protected
        self.reads = 0
        self.assignments = []


def prune_body(statements, protected=()):
    """Analyze each lexical scope using binding identities, not variable names."""
    changed_any = False
    while True:
        all_bindings = []
        scopes = [{name: Binding(protected=True) for name in protected}]

        def lookup(name):
            for scope in reversed(scopes):
                if name in scope:
                    return scope[name]
            return None  # struct field, or otherwise outside this body

        def expression(expr):
            if isinstance(expr, IdentifierNode):
                b = lookup(expr.name)
                if b is not None:
                    b.reads += 1
            elif isinstance(expr, CallNode):
                if not isinstance(expr.callee, IdentifierNode):
                    expression(expr.callee)
                for arg in expr.arguments:
                    expression(arg)
            elif isinstance(expr, MemberAccessNode):
                expression(expr.object_expression)
            elif isinstance(expr, BinaryExprNode):
                expression(expr.left)
                expression(expr.right)
            elif isinstance(expr, UnaryExprNode):
                expression(expr.operand)
            elif isinstance(expr, ObjectCreationNode):
                for arg in expr.arguments:
                    expression(arg)

        def analyze_block(body, new_scope=False):
            if new_scope:
                scopes.append({})
            for stmt in body:
                if isinstance(stmt, DeclarationNode):
                    expression(stmt.expression)
                    b = Binding(stmt)
                    scopes[-1][stmt.name] = b
                    all_bindings.append(b)
                elif isinstance(stmt, AssignmentNode):
                    b = lookup(stmt.name)
                    if b is not None:
                        b.assignments.append(stmt)
                    expression(stmt.expression)
                elif isinstance(stmt, FieldAssignmentNode):
                    expression(stmt.target)
                    expression(stmt.expression)
                elif isinstance(stmt, IfNode):
                    expression(stmt.condition)
                    analyze_block(stmt.if_body, True)
                    analyze_block(stmt.else_body or [], True)
                elif isinstance(stmt, WhileNode):
                    expression(stmt.condition)
                    analyze_block(stmt.body, True)
                elif isinstance(stmt, ForNode):
                    expression(stmt.start)
                    expression(stmt.end)
                    scopes.append({stmt.name: Binding(protected=True)})
                    analyze_block(stmt.body)
                    scopes.pop()
                elif isinstance(stmt, (PrintNode, ReturnNode, ExpressionStatementNode)):
                    expression(stmt.expression)
            if new_scope:
                scopes.pop()

        analyze_block(statements)
        dead = [b for b in all_bindings if b.reads == 0 and not b.protected]
        if not dead:
            break
        targets = {id(x.declaration) for x in dead}
        targets.update(id(a) for b in dead for a in b.assignments)

        def rewrite(body):
            rewritten = []
            for stmt in body:
                if id(stmt) in targets:
                    # Keep side effects and runtime errors in their original order.
                    if not pure(stmt.expression):
                        rewritten.append(ExpressionStatementNode(stmt.line, stmt.column, stmt.expression))
                else:
                    if isinstance(stmt, IfNode):
                        stmt.if_body = rewrite(stmt.if_body)
                        if stmt.else_body is not None:
                            stmt.else_body = rewrite(stmt.else_body)
                    if isinstance(stmt, (WhileNode, ForNode)):
                        stmt.body = rewrite(stmt.body)
                    rewritten.append(stmt)
            return rewritten

        statements[:] = rewrite(statements)
        changed_any = True
    return changed_any


def unused_variables(program):
    changed = prune_body(program.statements)
    for node in program.statements:
        if isinstance(node, FunctionNode):
            changed |= prune_body(node.body, (p.name for p in node.parameters))
        elif isinstance(node, StructNode):
            for method in node.methods:
                changed |= prune_body(method.body, (p.name for p in method.parameters))
    return changed


def substitute(expr, mapping):
    result = copy.deepcopy(expr)
    def recurse(node):
        if isinstance(node, IdentifierNode) and node.name in mapping:
            node.name = mapping[node.name]
        elif isinstance(node, CallNode):
            if not isinstance(node.callee, IdentifierNode):
                recurse(node.callee)
            for x in node.arguments:
                recurse(x)
        elif isinstance(node, MemberAccessNode):
            recurse(node.object_expression)
        elif isinstance(node, BinaryExprNode):
            recurse(node.left)
            recurse(node.right)
        elif isinstance(node, UnaryExprNode):
            recurse(node.operand)
        elif isinstance(node, ObjectCreationNode):
            for x in node.arguments:
                recurse(x)
    recurse(result)
    return result


def inline_once(program, serial):
    counts = function_counts(program)
    used_names = {n.name for n in walk(program) if isinstance(n, IdentifierNode)}
    used_names.update(n.name for n in walk(program) if isinstance(n, DeclarationNode))
    used_names.update(n.name for n in walk(program) if isinstance(n, ForNode))
    def fresh(base):
        candidate = base
        i = 0
        while candidate in used_names:
            i += 1
            candidate = f"{base}x{i}"
        used_names.add(candidate)
        return candidate
    fn_map = {n.name: n for n in program.statements if isinstance(n, FunctionNode)}
    graph = {name: {dep for dep in calls_in(fn.body) if dep in fn_map}
             for name, fn in fn_map.items()}
    def recursive(name):
        pending = list(graph[name])
        visited = set()
        while pending:
            dep = pending.pop()
            if dep == name:
                return True
            if dep not in visited:
                visited.add(dep)
                pending.extend(graph[dep])
        return False
    candidates = {}
    for node in program.statements:
        if (isinstance(node, FunctionNode) and counts[node.name] == 1 and
                len(node.body) == 1 and isinstance(node.body[0], ReturnNode) and
                not recursive(node.name)):
            candidates[node.name] = node

    def safe_inline(call):
        if not direct_call(call) or call.callee.name not in candidates:
            return False
        fn = candidates[call.callee.name]
        # Avoid inlining an indirectly recursive call chain, and avoid moving effects.
        return all(pure(x) for x in call.arguments) and inline_pure(fn.body[0].expression)

    def rewrite_block(body):
        nonlocal serial
        for idx, stmt in enumerate(body):
            expr = None
            if isinstance(stmt, (DeclarationNode, AssignmentNode, PrintNode, ReturnNode, ExpressionStatementNode)):
                expr = stmt.expression
            elif isinstance(stmt, FieldAssignmentNode):
                expr = stmt.expression
            if expr is not None and safe_inline(expr):
                fn = candidates[expr.callee.name]
                serial += 1
                mapping = {}
                prelude = []
                for p, arg in zip(fn.parameters, expr.arguments):
                    name = fresh(f"kameinline{serial}param{len(prelude)}")
                    mapping[p.name] = name
                    prelude.append(DeclarationNode(expr.line, expr.column, p.param_type, name, False, copy.deepcopy(arg)))
                value_name = fresh(f"kameinline{serial}result")
                prelude.append(DeclarationNode(expr.line, expr.column, fn.result_type, value_name, False,
                                               substitute(fn.body[0].expression, mapping)))
                stmt.expression = IdentifierNode(expr.line, expr.column, value_name)
                body[idx:idx+1] = prelude + [stmt]
                return True, serial
            for child in ([stmt.if_body, stmt.else_body] if isinstance(stmt, IfNode)
                          else [stmt.body] if isinstance(stmt, (WhileNode, ForNode)) else []):
                if child is not None:
                    found, serial = rewrite_block(child)
                    if found:
                        return True, serial
        return False, serial

    for node in program.statements:
        if isinstance(node, FunctionNode):
            found, serial = rewrite_block(node.body)
        elif isinstance(node, StructNode):
            found = False
            for method in node.methods:
                found, serial = rewrite_block(method.body)
                if found:
                    break
        else:
            temp = [node]
            found, serial = rewrite_block(temp)
            if found:
                index = program.statements.index(node)
                program.statements[index:index+1] = temp
        if found:
            return True, serial
    return False, serial


def optimize(program):
    serial = 0
    # Inlining before dead-code cleanup exposes additional unused bindings.
    for _ in range(100):
        changed, serial = inline_once(program, serial)
        if not changed:
            break
    for _ in range(100):
        changed = unused_variables(program)
        changed |= remove_unused_functions(program)
        if not changed:
            break
    return program
