#!/usr/bin/env python3
"""t1 검사: calc.average가 평균을 맞게 내고, 빈 리스트면 0을 돌려주는지. 종료 코드 0 = PASS."""
import importlib.util
import sys
from pathlib import Path

work = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("calc", work / "calc.py")
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    cases = [([1, 2, 3], 2), ([5], 5), ([], 0), ([1.5, 2.5], 2.0), ([-2, 2, 6], 2)]
    bad = [f"average({a}) = {m.average(a)!r}, want {w!r}" for a, w in cases if abs(m.average(a) - w) > 1e-9]
except Exception as e:  # noqa: BLE001 — 어떤 오류든 FAIL
    bad = [f"error: {type(e).__name__}: {e}"]
print("PASS" if not bad else "FAIL\n" + "\n".join(bad))
sys.exit(1 if bad else 0)
