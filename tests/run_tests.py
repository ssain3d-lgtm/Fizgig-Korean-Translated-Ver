"""Tiny test runner (no pytest dependency): runs every test_* function in tests/test_*.py."""
import importlib.util
import os
import sys
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    failed = passed = 0
    for fn in sorted(os.listdir(HERE)):
        if not (fn.startswith("test_") and fn.endswith(".py")):
            continue
        spec = importlib.util.spec_from_file_location(fn[:-3], os.path.join(HERE, fn))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        for name in dir(mod):
            if name.startswith("test_") and callable(getattr(mod, name)):
                try:
                    getattr(mod, name)()
                    passed += 1
                except Exception:
                    failed += 1
                    print(f"FAIL {fn}::{name}")
                    traceback.print_exc()
    print(f"{passed} passed, {failed} failed")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
