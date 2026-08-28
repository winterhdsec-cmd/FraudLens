"""零依赖运行器：本机无 pytest 时用于跑 test_otel.py（CI 仍用 pytest）。

注入一个最小 pytest stub（skip/import pytest 可用），然后收集并运行 test_* 函数。
"""
import os
import sys
import types
import importlib.util

HERE = os.path.dirname(os.path.abspath(__file__))


class _FakePytest:
    class SkipTest(Exception):
        pass

    @staticmethod
    def skip(msg=""):
        raise _FakePytest.SkipTest(msg)


# 注入 pytest stub，使 test_otel.py 顶部的 `import pytest` 不报错
sys.modules.setdefault("pytest", _FakePytest)

spec = importlib.util.spec_from_file_location(
    "test_otel_standalone", os.path.join(HERE, "test_otel.py")
)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

passed = skipped = failed = 0
for name in dir(mod):
    if not name.startswith("test_"):
        continue
    fn = getattr(mod, name)
    if not callable(fn):
        continue
    try:
        fn()
        print(f"PASS  {name}")
        passed += 1
    except _FakePytest.SkipTest as e:
        print(f"SKIP  {name} ({e})")
        skipped += 1
    except Exception as e:  # noqa: BLE001
        print(f"FAIL  {name}: {e!r}")
        failed += 1

print(f"\n{passed} passed, {skipped} skipped, {failed} failed (total {passed+skipped+failed})")
sys.exit(1 if failed else 0)
