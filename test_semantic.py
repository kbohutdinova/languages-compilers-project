import unittest

from compiler import CompilationError, compile_source
from src.semantic import SemanticAnalyzer


class SemanticTests(unittest.TestCase):
    def check_valid(self, source):
        SemanticAnalyzer().analyze(compile_source(source))

    def check_invalid(self, source, message):
        with self.assertRaises(CompilationError) as caught:
            SemanticAnalyzer().analyze(compile_source(source))
        self.assertIn(message, str(caught.exception))

    def test_valid_variables(self):
        self.check_valid('num32 mut x {10}; x := 20; bool active {true};')

    def test_valid_function(self):
        self.check_valid('action add(num32 a, num32 b) -> num32 { give a + b; } print(add(5, 10));')

    def test_valid_struct_and_method(self):
        self.check_valid('shape Point { num32 mut x; num32 y; action sum() -> num32 { give x + y; } } Point mut p {10, 20}; p.x := 15; print(p.sum());')

    def test_valid_function_declared_later(self):
        self.check_valid('print(add(1, 2)); action add(num32 x, num32 y) -> num32 { give x + y; }')

    def test_overflow_num32(self):
        self.check_invalid('num32 x {2147483648};', 'integer overflow for num32')

    def test_overflow_num64(self):
        self.check_invalid('num64 x {9223372036854775808};', 'integer overflow for num64')

    def test_immutable_variable(self):
        self.check_invalid('num32 x {10}; x := 20;', 'immutable variable')

    def test_unknown_variable(self):
        self.check_invalid('num32 x {missing};', 'unknown variable')

    def test_duplicate_declaration(self):
        self.check_invalid('num32 x {1}; num32 x {2};', 'duplicate declaration')

    def test_wrong_argument_count(self):
        self.check_invalid('action add(num32 a, num32 b) -> num32 { give a + b; } print(add(5));', 'wrong argument count')

    def test_wrong_argument_type(self):
        self.check_invalid('action identity(num32 a) -> num32 { give a; } print(identity(true));', 'expected num32')

    def test_wrong_return_type(self):
        self.check_invalid('action f() -> num32 { give true; }', 'expected num32')

    def test_unknown_field(self):
        self.check_invalid('shape Point { num32 x; } Point p {1}; print(p.y);', 'unknown field')

    def test_wrong_field_count(self):
        self.check_invalid('shape Point { num32 x; num32 y; } Point p {1};', 'wrong field count')

    def test_immutable_field(self):
        self.check_invalid('shape Point { num32 x; } Point mut p {1}; p.x := 2;', 'immutable chain')

    def test_immutable_object(self):
        self.check_invalid('shape Point { num32 mut x; } Point p {1}; p.x := 2;', 'immutable chain')

    def test_mutating_method_on_constant_object(self):
        self.check_invalid('shape Point { num32 mut x; action update() -> num32 { x := 2; give x; } } Point p {1}; print(p.update());', 'mutating method')


if __name__ == '__main__':
    unittest.main(verbosity=2)
