#!/usr/bin/env python3
"""Stand-in for `claude -p … --output-format json` so tests never call the real CLI.

Answer length depends on the condition it can see: a skill file in the folder (C/D) or the
「간결하게 답해.」 prefix (B). CTM_FAKE_OFF=1 makes `/caveman status` report `off`.
Every call is appended to $CTM_FAKE_LOG (one JSON line) so tests can count calls.
"""
import json
import os
import sys
import uuid
from pathlib import Path

args = sys.argv[1:]
if args == ["--version"]:
    print("0.0.0 (fake)")
    sys.exit(0)
prompt = args[args.index("-p") + 1]
resume = args[args.index("--resume") + 1] if "--resume" in args else None
skills = sorted(p.name for p in Path(".claude/skills").glob("*")) if Path(".claude/skills").exists() else []
log = os.environ.get("CTM_FAKE_LOG")
if log:
    with open(log, "a") as f:
        f.write(json.dumps({"prompt": prompt, "resume": resume, "skills": skills, "args": args}) + "\n")
if prompt.startswith("/caveman status"):
    mode = "off" if os.environ.get("CTM_FAKE_OFF") else (skills[0] if skills else "off")
    text = f"Caveman mode: {mode} (not tracked by this host)"
elif prompt.startswith("/"):
    text = "on."
elif skills:
    text = "리스트 가변. 튜플 불변." if skills == ["ultracave"] else "리스트는 가변, 튜플은 불변."
elif prompt.startswith("간결하게"):
    text = "리스트는 가변(mutable)이고 튜플은 불변(immutable)입니다."
else:
    text = "리스트는 가변(mutable)이라 바꿀 수 있고, 튜플은 불변(immutable)이라 만든 뒤 바꿀 수 없습니다. " * 3
out = len(text) // 2
print(json.dumps({"type": "result", "is_error": False, "result": text, "session_id": resume or str(uuid.uuid4()),
                  "num_turns": 1, "duration_ms": 1000 + out, "total_cost_usd": out / 100000,
                  "usage": {"input_tokens": 3, "cache_creation_input_tokens": 100 + 500 * len(skills),
                            "cache_read_input_tokens": 1000, "output_tokens": out,
                            "output_tokens_details": {"thinking_tokens": 0}},
                  "modelUsage": {"fake-model": {}}}))
