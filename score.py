#!/usr/bin/env python3
"""Deterministic answer scoring — no AI judge.

    python3 score.py q01 "리스트는 가변, 튜플은 불변입니다."     # score one answer by hand
    python3 score.py --list                                      # show the criteria

Rule (prompts/questions.json): every group in `required` must match at least one of its words
(case-insensitive substring) and no `forbidden` regex may match (case-insensitive).
Markdown `**`, `__` and backticks are removed first (2026-10-31: bold text split 6 correct answers).
Same text in -> same score out, every time.
"""
import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
QUESTIONS = HERE / "prompts" / "questions.json"


def load_questions(path=QUESTIONS):
    return {q["id"]: q for q in json.loads(Path(path).read_text(encoding="utf-8"))["questions"]}


def normalize(text):
    """Markdown emphasis and code ticks are not words: 「가능한 한 **많이**」 must match 「가능한 한 많이」."""
    return re.sub(r"\*\*|__|`", "", text or "")


def score(text, q):
    text = normalize(text)
    t = text.lower()
    missing = [i for i, group in enumerate(q.get("required", [])) if not any(w.lower() in t for w in group)]
    hits = [rx for rx in q.get("forbidden", []) if re.search(rx, text or "", re.I)]
    return {"pass": not missing and not hits, "missing_groups": missing, "forbidden_hits": hits}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("qid", nargs="?")
    ap.add_argument("text", nargs="?")
    ap.add_argument("--list", action="store_true")
    a = ap.parse_args(argv)
    qs = load_questions()
    if a.list or not a.qid:
        for q in qs.values():
            print(f"{q['id']}  {q['prompt']}")
            for i, g in enumerate(q["required"]):
                print(f"     need[{i}] any of: {' | '.join(g)}")
            for rx in q["forbidden"]:
                print(f"     never: /{rx}/")
        return 0
    r = score(a.text if a.text is not None else sys.stdin.read(), qs[a.qid])
    print(json.dumps(r, ensure_ascii=False))
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
