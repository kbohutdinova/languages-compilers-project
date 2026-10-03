# KameLang

KameLang is a small programming language created for the Languages and Compilers course project.

Stage 1 includes a hand-written lexer, a recursive-descent parser, an Abstract Syntax Tree (AST), and lexical and syntax error handling.

## Language Features

KameLang supports:

- `num32` integer type;
- `num64` integer type;
- `bool` type;
- immutable variables;
- mutable variables;
- assignment;
- arithmetic expressions;
- comparison operators `==` and `!=`;
- `if` statements;
- optional `else` blocks.

Semantic checks, including type checking and integer overflow validation, belong to the next project stage.

## Variable Declarations

Immutable `num32` variable:

```text
num32 x {10};
```

Immutable `num64` variable:

```text
num64 y {100};
```

Boolean variable:

```text
bool active {true};
```

## Mutable Variables

The `mut` keyword is used to declare a mutable variable:

```text
num32 mut x {10};
```

## Assignment

Assignment uses the `:=` operator:

```text
x := 20;
```

## Boolean Values

KameLang supports two boolean values:

```text
true
false
```

Example:

```text
bool active {true};
```
## Integer Types and Overflow

`num32` represents a signed 32-bit integer with the range:

-2147483648 to 2147483647

`num64` represents a signed 64-bit integer with the range:

-9223372036854775808 to 9223372036854775807

Values outside the range of their declared type are considered overflow errors.

Stage 1 parses these constructs and builds the AST. Overflow validation is a semantic check and will be implemented in the next project stage.

## Comparison Operators

Equality:

```text
bool same {x == 10};
```

Inequality:

```text
bool different {x != 10};
```

## Arithmetic Expressions

KameLang supports the following arithmetic operators:

```text
+
-
*
/
```

Example:

```text
num32 x {10 + 5 * 2};
```

Parentheses can be used to change expression precedence:

```text
num32 x {(10 + 5) * 2};
```

## If Statement

An `if` statement contains a condition and a block with at least one statement:

```text
bool active {true};

if active {
    num32 x {10};
}
```

## If / Else Statement

The `else` block is optional.

```text
bool active {false};

if active {
    num32 x {10};
} else {
    num32 x {20};
}
```

Both `if` and `else` blocks must contain at least one statement.

## Example Program

```text
num32 mut x {10};
num64 y {100};
bool active {true};

x := 20;

if active {
    x := 30;
} else {
    x := 40;
}
```

## Grammar

The complete EBNF grammar of KameLang is stored in:

```text
grammar.ebnf
```

## Running the Compiler

Python 3 is required.

To parse a source file and print its AST, run:

```bash
python3 compiler.py --ast input.txt
```

Example AST output:

```text
Program
  Declaration line=1 column=1
    type=num32
    name=x
    mutable=true
    value
      Integer value=10 line=1 column=14
```

## Error Handling

Lexical and syntax errors are printed to `stderr` in the following format:

```text
compilation error: line L:C: message
```

When an error occurs, the compiler returns a non-zero exit code and does not print an AST.

## Tests

The project contains:

- at least 15 valid program tests in `tests/ok`;
- at least 15 lexical or syntax error tests in `tests/err`.

Each test has a corresponding `.expected` file.

To run all tests:

```bash
python3 run_tests.py
```

A successful test run ends with:

```text
====================
Passed: 30
Failed: 0
====================
```

## Project Structure

```text
.
├── compiler.py
├── grammar.ebnf
├── input.txt
├── run_tests.py
├── README.md
├── ai_usage.txt
└── tests
    ├── ok
    └── err
```