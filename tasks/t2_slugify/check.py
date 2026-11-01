#!/usr/bin/env python3
"""t2 검사: textutil.slugify 규칙 + 기존 word_count가 그대로인지. 종료 코드 0 = PASS."""
import importlib.util
import sys
from pathlib import Path

work = Path(sys.argv[1])
spec = importlib.util.spec_from_file_location("textutil", work / "textutil.py")
m = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(m)
    cases = [("Hello World", "hello-world"), ("  Claude Code 2.1 -- Token Meter!  ", "claude-code-2-1-token-meter"),
             ("a__b", "a-b"), ("---", ""), ("ABC123", "abc123")]
    bad = [f"slugify({a!r}) = {m.slugify(a)!r}, want {w!r}" for a, w in cases if m.slugify(a) != w]
    if m.word_count("a b  c") != 3:
        bad.append("word_count changed")
except Exception as e:  # noqa: BLE001
    bad = [f"error: {type(e).__name__}: {e}"]
print("PASS" if not bad else "FAIL\n" + "\n".join(bad))
sys.exit(1 if bad else 0)
