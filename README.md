# KameLang, Stage 2

KameLang is a small statically typed language compiled to LLVM IR using Python 3 and `llvmlite.ir`. It retains the Stage 1 syntax and extends it with typed functions, structures, methods, input, and output.

## Requirements

- Python 3
- `pip install llvmlite`
- `clang` on PATH for building and executing programs

## How to use

```bash
python3 compiler.py --ast input.txt
python3 compiler.py input.txt output.ll
clang output.ll -o program
./program
python3 -m unittest -v test_semantic
python3 run_stage2_tests.py
python3 run_tests.py
```

The third command requires Clang and the C standard library. On macOS, install the Xcode command-line tools if `clang` is unavailable.

The AST mode is syntax-only for backward compatibility with Stage 1 tests. Compilation mode runs semantic checks before generating LLVM IR. The compiler reports lexical, syntax, and semantic errors to stderr and returns a nonzero status without producing a new `.ll` file.

## Syntax

Immutable variables are the default, and `mut` permits assignment:

```text
num32 x {10};
num64 big {100};
bool ready {true};
num32 mut count {0};
count := count + 1;
```

`num32` and `num64` are signed 32-bit and 64-bit integers. Constant expressions outside these ranges are rejected. Arithmetic supports `+`, `-`, `*`, `/`. Equality supports `==` and `!=`. `if` conditions must have type `bool`, and each branch has its own local scope:

```text
if count == 1 {
    print("One");
} else {
    print("Other");
}
```

Functions declare typed parameters and one result type. `give` returns a value of that type. A call is an expression, can be nested, and may refer to a later function:

```text
action double(num32 a) -> num32 {
    give a + a;
}
print(double(3));
```

Functions can be recursive. Parameters and local variables have their own scope. Global variables referenced inside functions are not supported by the current compiler; top-level function declarations and calls are supported.

Structures define fields in declaration order. Each field is immutable unless declared `mut`, and construction supplies a value for every field:

```text
shape Point {
    num32 mut x;
    num32 y;
    action sum() -> num32 {
        give x + y;
    }
}
Point mut p {10, 20};
p.x := 15;
print(p.sum());
```

Inside a member function, parameters and locals take precedence over fields. Structure fields and other methods can be referenced by name. Assignments through a field chain require every link to be mutable. Methods that modify fields cannot be called on immutable objects. Named fields must exist.

`read()` reads one signed integer from stdin. `print` prints integers, booleans (`true` or `false`), string literals, and structure values. `print` appends one newline. Structures print in field declaration order, e.g. `Point{x=15, y=20}`.

```text
num32 number {read()};
print(number);
print("Done");
```

## Validation and errors

Semantic checks include named types, duplicate declarations in a scope, mutability, typed arithmetic, integer literal bounds, function argument count and types, return types, field existence, and structure initializer arity. Source errors are formatted as `compilation error: line L:C: message`.

The LLVM generator uses `llvmlite.ir.IRBuilder`, actual LLVM identified structure types, `alloca`, `gep`, `load`, `store`, conditional basic blocks, and declared `printf` / `scanf`. The generated LLVM IR is obtained from `str(module)` rather than concatenated IR strings.


## Tests

`test_semantic.py` runs 17 semantic unit tests.
`run_stage2_tests.py` compiles and runs valid programs from `tests/stage2`, compares their exact stdout with `.expected` files, and uses `.in` files as standard input when present.
For invalid programs, the test runner compares the complete stderr output with the corresponding `.error` file, checks for a non-zero exit code, and verifies that no LLVM IR output file was created.
`run_tests.py` runs the original Stage 1 regression tests.


## Known Limitations

The compiler detects integer constant overflow during semantic analysis.

Runtime arithmetic overflow is checked for signed `num32` and `num64` operations, including addition, subtraction, multiplication, unary negation, and division. Division by zero is also checked.

When runtime integer overflow occurs, the program prints `integer overflow` and exits with a non-zero status.

Some limitations remain:
- Nested structure printing does not recursively display nested objects.
- Function bodies referencing top-level variables are not fully supported.
- Some advanced temporary-object access chains are not fully supported.
