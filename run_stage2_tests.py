import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
TESTS = ROOT / "tests" / "stage2"


def run():
    passed = 0
    failed = 0
    for source in sorted(TESTS.glob("*.txt")):
        expected = source.with_suffix(".expected")
        invalid = source.with_suffix(".error")
        with tempfile.TemporaryDirectory() as directory:
            ir_file = Path(directory) / "program.ll"
            executable = Path(directory) / "program"
            result = subprocess.run([sys.executable, str(ROOT / "compiler.py"), str(source), str(ir_file)], capture_output=True, text=True, cwd=ROOT)
            if invalid.exists():
                wanted = invalid.read_text()
                good = (
                        result.returncode != 0
                        and result.stderr == wanted
                        and result.stdout == ""
                        and not ir_file.exists()
                        and "Traceback" not in result.stderr
                )
            elif result.returncode != 0:
                good = False
            else:
                build = subprocess.run(["clang", "-Wno-override-module", str(ir_file), "-o", str(executable)], capture_output=True, text=True)
                if build.returncode != 0:
                    good = False
                    result = build
                else:
                    input_file = source.with_suffix(".in")
                    input_text = input_file.read_text() if input_file.exists() else ""
                    execution = subprocess.run([str(executable)], input=input_text, capture_output=True, text=True, timeout=5)
                    good = execution.stdout == expected.read_text() and execution.returncode == 0
                    result = execution
            print(("PASS" if good else "FAIL") + " " + source.name)
            if not good:
                print("  stdout:", repr(result.stdout))
                print("  stderr:", repr(result.stderr))
                failed += 1
            else:
                passed += 1
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(run())
