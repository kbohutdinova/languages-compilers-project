import subprocess
from pathlib import Path


def run_ok_tests():
    passed = 0
    failed = 0

    for test_file in sorted(Path("tests/ok").glob("*.txt")):
        expected_file = test_file.with_suffix(".expected")

        result = subprocess.run(
            [
                "python3",
                "compiler.py",
                "--ast",
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )

        expected = expected_file.read_text()

        if result.returncode == 0 and result.stdout == expected:
            print(f"PASS ok: {test_file.name}")
            passed += 1
        else:
            print(f"FAIL ok: {test_file.name}")

            if result.returncode != 0:
                print("  unexpected non-zero exit code")

            if result.stdout != expected:
                print("  AST output differs")

            if result.stderr:
                print("  stderr:")
                print(result.stderr.rstrip())

            failed += 1

    return passed, failed


def run_error_tests():
    passed = 0
    failed = 0

    for test_file in sorted(Path("tests/err").glob("*.txt")):
        expected_file = test_file.with_suffix(".expected")

        result = subprocess.run(
            [
                "python3",
                "compiler.py",
                "--ast",
                str(test_file),
            ],
            capture_output=True,
            text=True,
        )

        expected = expected_file.read_text()

        correct_exit_code = result.returncode != 0
        correct_stderr = result.stderr == expected
        no_stdout = result.stdout == ""

        if correct_exit_code and correct_stderr and no_stdout:
            print(f"PASS err: {test_file.name}")
            passed += 1
        else:
            print(f"FAIL err: {test_file.name}")

            if not correct_exit_code:
                print("  expected non-zero exit code")

            if not correct_stderr:
                print("  error output differs")

            if not no_stdout:
                print("  expected no stdout")

            failed += 1

    return passed, failed


def main():
    ok_passed, ok_failed = run_ok_tests()
    err_passed, err_failed = run_error_tests()

    total_passed = ok_passed + err_passed
    total_failed = ok_failed + err_failed

    print()
    print("====================")
    print(f"Passed: {total_passed}")
    print(f"Failed: {total_failed}")
    print("====================")

    if total_failed != 0:
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
