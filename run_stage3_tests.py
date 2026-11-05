"""Stage 3 native-code tests and optimizer output/AST regression tests."""
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent


def command(*args, input_text=''):
    return subprocess.run(list(args), text=True, input=input_text,
                          capture_output=True, timeout=10, cwd=ROOT)


def main():
    passed = failed = 0

    def record(name, ok, detail=''):
        nonlocal passed, failed
        passed += bool(ok)
        failed += not ok
        print(('PASS' if ok else 'FAIL') + ' ' + name)
        if not ok and detail:
            print(detail[:1000])

    cases = ([(p, 'normal') for p in sorted((ROOT / 'tests/stage3_feature_ok').glob('*.txt'))]
             + [(p, 'optimized') for p in sorted((ROOT / 'tests/stage3_feature_ok').glob('*.txt'))]
             + [(p, 'optimized') for p in sorted((ROOT / 'tests/opt').glob('*.txt'))])
    for source, mode in cases:
        with tempfile.TemporaryDirectory() as directory:
            ir = Path(directory) / 'output.ll'
            exe = Path(directory) / 'executable'
            args = ['--optimize'] if mode == 'optimized' else []
            compilation = command(sys.executable, 'compiler.py', *args, str(source), str(ir))
            if compilation.returncode:
                record(source.name + ':' + mode, False, compilation.stderr)
                continue
            build = command('clang', '-Wno-override-module', str(ir), '-o', str(exe))
            if build.returncode:
                record(source.name + ':' + mode, False, build.stderr)
                continue
            result = command(str(exe))
            expected = source.with_suffix('.expected').read_text()
            record(source.name + ':' + mode, result.returncode == 0 and result.stdout == expected, repr(result.stdout))

    for source in sorted((ROOT / 'tests/stage3_feature_err').glob('*.txt')):
        with tempfile.TemporaryDirectory() as directory:
            ir = Path(directory) / 'output.ll'
            result = command(sys.executable, 'compiler.py', '--optimize', str(source), str(ir))
            record(source.name + ':error', result.returncode != 0 and
                   result.stderr == source.with_suffix('.error').read_text() and
                   not ir.exists() and not result.stdout)

    for source in sorted((ROOT / 'tests/opt').glob('*.txt')):
        ast = command(sys.executable, 'compiler.py', '--optimize', '--ast', str(source))
        record(source.name + ':ast', ast.returncode == 0 and
               ast.stdout == source.with_suffix('.astc').read_text(), ast.stdout)
        for mode in ('normal', 'optimized'):
            with tempfile.TemporaryDirectory() as directory:
                ir = Path(directory) / 'program.ll'
                exe = Path(directory) / 'program'
                flags = ['--optimize'] if mode == 'optimized' else []
                c = command(sys.executable, 'compiler.py', *flags, str(source), str(ir))
                if c.returncode:
                    record(source.name + ':compare:' + mode, False, c.stderr)
                    continue
                b = command('clang', '-Wno-override-module', str(ir), '-o', str(exe))
                r = command(str(exe)) if b.returncode == 0 else b
                record(source.name + ':compare:' + mode, r.returncode == 0 and
                       r.stdout == source.with_suffix('.expected').read_text(), repr(r.stderr))

    program = ROOT / 'programs/weighted_sum.txt'

    for program_name in ('guess_number',):
        program = ROOT / f'programs/{program_name}.txt'

        with tempfile.TemporaryDirectory() as directory:
            ir = Path(directory) / 'program.ll'
            exe = Path(directory) / 'program'

            c = command(
                sys.executable, 'compiler.py',
                str(program), str(ir)
            )

            b = (
                command('clang', '-Wno-override-module',
                        str(ir), '-o', str(exe))
                if c.returncode == 0 else c
            )

            for label in (program_name, program_name + '_second'):
                stdin = (ROOT / f'programs/{label}.in').read_text()

                r = (
                    command(str(exe), input_text=stdin)
                    if b.returncode == 0 else b
                )

                record(
                    label + ':session',
                    r.returncode == 0 and
                    r.stdout == (
                        ROOT / f'programs/{label}.expected'
                    ).read_text(),
                    r.stderr
                )

    return int(failed > 0)

if __name__ == '__main__':
    raise SystemExit(main())
