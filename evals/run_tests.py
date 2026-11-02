"""Run legacy, MCP and evaluation suites together; paid API requests are never used."""
import argparse
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))


def main(argv=None):
    parser=argparse.ArgumentParser()
    parser.add_argument('--output',help='Optional UTF-8 test log file')
    args=parser.parse_args(argv)
    suite=unittest.TestSuite(unittest.TestLoader().discover(str(ROOT/folder)) for folder in ('tests','evals'))
    if args.output:
        path=Path(args.output);path.parent.mkdir(parents=True,exist_ok=True)
        with path.open('w',encoding='utf-8') as stream,redirect_stdout(stream),redirect_stderr(stream):
            result=unittest.TextTestRunner(stream=stream,verbosity=2).run(suite)
        print(f'Tests: {result.testsRun}, passed: {result.testsRun-len(result.failures)-len(result.errors)-len(result.skipped)}, skipped: {len(result.skipped)}, failures: {len(result.failures)}, errors: {len(result.errors)}')
    else:
        result=unittest.TextTestRunner(verbosity=2).run(suite)
    return 0 if result.wasSuccessful() else 1


if __name__=='__main__':
    raise SystemExit(main())
