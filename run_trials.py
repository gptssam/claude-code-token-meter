#!/usr/bin/env python3
"""Measure tokens: same prompt, only the condition changes (A baseline · B "간결하게 답해." · C /caveman · D /ultracave).

    python3 run_trials.py                      # DRY RUN (default): shows the plan and call count, calls nothing
    python3 run_trials.py --run                # really runs `claude -p` (uses your Claude usage)
    python3 run_trials.py --run --set questions --conditions A,B --repeats 1   # small first try
    python3 run_trials.py --run --out runs/<dir>   # continue an interrupted run (finished trials are skipped)

Each trial gets a NEW temp folder. Skill conditions copy the pinned SKILL.md (fetch_skill.py) into
that folder as a project skill, send the activation command (e.g. `/caveman`) as turn 1, then the
question as turn 2 in the same session. Only turn 2 is the measurement; turn 1 is stored separately.
Before any measurement, each skill condition must pass a preflight: activate, then `/caveman status`
must report the expected mode. Otherwise the run is refused (exit 3).

Numbers come straight from `claude -p --output-format json` (`usage`, `total_cost_usd`, `duration_ms`).
`total_cost_usd` is the CLI's own estimate, not an invoice. Standard library only.
"""
import argparse
import concurrent.futures as cf
import datetime as dt
import json
import os
import random
import re
import shlex
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from pathlib import Path

import fetch_skill

HERE = Path(__file__).resolve().parent
SHORT = {"questions": "q", "tasks": "t"}


def load_json(p):
    return json.loads(Path(p).read_text(encoding="utf-8"))


def load_inputs(root=HERE):
    conds = load_json(root / "conditions.json")["conditions"]
    qs = load_json(root / "prompts" / "questions.json")["questions"]
    ts = load_json(root / "prompts" / "tasks.json")["tasks"]
    return conds, qs, ts


def build_plan(conds, qs, ts, sets=("questions", "tasks"), cond_ids=None, repeats=3, seed=20261031, items=None):
    cs = [c for c in conds if cond_ids is None or c["id"] in cond_ids]
    pool = ([("questions", q) for q in qs] if "questions" in sets else []) + \
           ([("tasks", t) for t in ts] if "tasks" in sets else [])
    if items:
        pool = [(s, it) for s, it in pool if it["id"] in items]
    plan = [{"trial_id": f"{SHORT[s]}_{it['id']}_{c['id']}_{r}", "set": s, "item": it["id"], "cond": c["id"], "rep": r}
            for s, it in pool for c in cs for r in range(1, repeats + 1)]
    random.Random(seed).shuffle(plan)  # interleave conditions so time-of-day drift hits all of them
    for k, p in enumerate(plan, 1):
        p["order"] = k
    return plan


def count_calls(plan, conds):
    by = {c["id"]: c for c in conds}
    act = sum(1 for p in plan if by[p["cond"]]["activate"])
    skills = sorted({by[p["cond"]]["id"] for p in plan if by[p["cond"]]["skill"]})
    return {"measured": len(plan), "activation": act, "preflight": 2 * len(skills),
            "total_cli_calls": len(plan) + act + 2 * len(skills), "skill_conditions": skills}


class Claude:
    def __init__(self, bin_cmd="claude", model=None, isolate=True, timeout=900):
        self.cmd = shlex.split(bin_cmd)
        self.model, self.isolate, self.timeout = model, isolate, timeout
        env = {k: os.environ[k] for k in ("HOME", "PATH", "USER") if k in os.environ}
        env.update({k: v for k, v in os.environ.items() if k.startswith("CTM_")})
        env.update(LANG="ko_KR.UTF-8", TERM="xterm", DISABLE_AUTOUPDATER="1")  # no CLI update in the middle of a run
        self.env = env

    def args(self, prompt, kind, resume=None):
        a = self.cmd + ["-p", prompt, "--output-format", "json"]
        if self.model:
            a += ["--model", self.model]
        if self.isolate:  # your user-level hooks, plugins and MCP servers stay out of the measurement
            a += ["--setting-sources", "project", "--strict-mcp-config"]
        if kind == "questions":
            a += ["--tools", ""]
        else:
            a += ["--permission-mode", "acceptEdits", "--allowedTools", "Bash"]
        if resume:
            a += ["--resume", resume]
        return a

    def call(self, cwd, prompt, kind, resume=None):
        t0 = time.time()
        try:
            p = subprocess.run(self.args(prompt, kind, resume), cwd=cwd, env=self.env, capture_output=True,
                               text=True, timeout=self.timeout)
            out, err, code = p.stdout, p.stderr, p.returncode
        except subprocess.TimeoutExpired as e:
            out, err, code = e.stdout or "", "timeout", -1
            out = out.decode() if isinstance(out, bytes) else out
        wall = round(time.time() - t0, 2)
        try:
            data = json.loads(out)
        except ValueError:
            data = {"is_error": True, "result": "", "_parse_error": True}
        return data, {"wall_s": wall, "exit_code": code, "stderr_tail": (err or "")[-400:]}


def usage_fields(d):
    u = d.get("usage") or {}
    inp = [u.get("input_tokens") or 0, u.get("cache_creation_input_tokens") or 0, u.get("cache_read_input_tokens") or 0]
    return {"output_tokens": u.get("output_tokens"),
            "thinking_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens"),
            "input_tokens": inp[0], "cache_creation_input_tokens": inp[1], "cache_read_input_tokens": inp[2],
            "input_total": sum(inp), "cost_usd": d.get("total_cost_usd"), "duration_ms": d.get("duration_ms"),
            "num_turns": d.get("num_turns"), "is_error": bool(d.get("is_error")),
            "models": sorted((d.get("modelUsage") or {}).keys())}


def scrub(text, roots):
    for r, rep in roots:
        if r:
            text = text.replace(str(r), rep)
    return text


class Runner:
    def __init__(self, claude, conds, qs, ts, out, lab=None, root=HERE, keep=False):
        self.claude, self.out, self.root, self.keep = claude, Path(out), Path(root), keep
        self.conds = {c["id"]: c for c in conds}
        self.items = {**{q["id"]: q for q in qs}, **{t["id"]: t for t in ts}}
        self.lab = Path(lab or tempfile.gettempdir()) / "ctm-lab"
        self.lab.mkdir(parents=True, exist_ok=True)
        (self.out / "raw").mkdir(parents=True, exist_ok=True)
        self.lock = threading.Lock()
        self.roots = [(self.lab, "<LAB>"), (Path.home(), "~")]

    def save_raw(self, name, data):
        txt = scrub(json.dumps(data, ensure_ascii=False, indent=1), self.roots)
        (self.out / "raw" / f"{name}.json").write_text(txt, encoding="utf-8")

    def make_folder(self, tag, cond, item_id=None, set_name=None):
        path = Path(tempfile.mkdtemp(prefix=f"{tag}_", dir=self.lab))
        if set_name == "tasks":
            shutil.copytree(self.root / "tasks" / item_id / "files", path, dirs_exist_ok=True)
        if cond["skill"]:
            dst = path / ".claude" / "skills" / cond["skill"] / "SKILL.md"
            dst.parent.mkdir(parents=True)
            shutil.copy(fetch_skill.cached_path(cond["skill"], self.root / ".skills_cache"), dst)
        return path

    def preflight(self, cond_ids):
        report, ok = [], True
        for cid in cond_ids:
            c = self.conds[cid]
            path = self.make_folder(f"preflight_{cid}", c)
            d1, m1 = self.claude.call(path, c["activate"], "questions")
            d2, m2 = self.claude.call(path, "/caveman status", "questions", resume=d1.get("session_id"))
            self.save_raw(f"preflight_{cid}_activate", d1)
            self.save_raw(f"preflight_{cid}_status", d2)
            status = d2.get("result") or ""
            passed = bool(re.search(c["status_expect"], status)) and not d1.get("is_error") and not d2.get("is_error")
            ok &= passed
            report.append({"cond": cid, "skill": c["skill"], "activate_reply": d1.get("result"), "status_reply": status,
                           "expect": c["status_expect"], "pass": passed})
            if not self.keep:
                shutil.rmtree(path, ignore_errors=True)
        (self.out / "preflight.json").write_text(json.dumps(report, ensure_ascii=False, indent=1), encoding="utf-8")
        return ok, report

    def trial(self, p):
        try:
            return self._trial(p)
        except Exception as e:  # noqa: BLE001 — one broken trial must not lose the whole run
            row = {**p, "is_error": True, "error": f"{type(e).__name__}: {e}", "output_tokens": None,
                   "input_total": None, "wall_s": None}
            with self.lock:
                with open(self.out / "results.jsonl", "a", encoding="utf-8") as f:
                    f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return row

    def _trial(self, p):
        c, it = self.conds[p["cond"]], self.items[p["item"]]
        path = self.make_folder(p["trial_id"], c, p["item"], p["set"])
        row = {**p, "started": dt.datetime.now().isoformat(timespec="seconds"), "folder": path.name}
        sid = None
        if c["activate"]:
            d1, m1 = self.claude.call(path, c["activate"], p["set"])
            self.save_raw(p["trial_id"] + "_activate", d1)
            sid = d1.get("session_id")
            row["activation"] = {**usage_fields(d1), "reply": d1.get("result"), **m1}
        prompt = c["prefix"] + it["prompt"]
        d2, m2 = self.claude.call(path, prompt, p["set"], resume=sid)
        self.save_raw(p["trial_id"], d2)
        row.update(usage_fields(d2))
        row.update(m2)
        row["prompt"] = prompt
        row["answer"] = scrub(d2.get("result") or "", self.roots)
        row["answer_chars"] = len(row["answer"])
        if p["set"] == "tasks":
            chk = subprocess.run([sys.executable, str(self.root / "tasks" / p["item"] / "check.py"), str(path)],
                                 capture_output=True, text=True)
            row["check_pass"] = chk.returncode == 0
            row["check_output"] = scrub(chk.stdout.strip(), self.roots)[-600:]
            keep_dir = self.out / "task_files" / p["trial_id"]
            shutil.copytree(path, keep_dir, ignore=shutil.ignore_patterns(".claude", "__pycache__"))
        if not self.keep:
            shutil.rmtree(path, ignore_errors=True)
        with self.lock:
            with open(self.out / "results.jsonl", "a", encoding="utf-8") as f:
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
        return row


def done_ids(out):
    f = Path(out) / "results.jsonl"
    if not f.exists():
        return set()
    return {json.loads(l)["trial_id"] for l in f.read_text(encoding="utf-8").splitlines()
            if l.strip() and not json.loads(l).get("is_error")}


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", action="store_true", help="really call claude (default is a dry run)")
    ap.add_argument("--set", default="questions,tasks", help="questions, tasks or both (comma)")
    ap.add_argument("--conditions", default="", help="e.g. A,B,C,D (default: all in conditions.json)")
    ap.add_argument("--items", default="", help="only these question/task ids (comma)")
    ap.add_argument("--repeats", type=int, default=3)
    ap.add_argument("--seed", type=int, default=20261031)
    ap.add_argument("--model", default=None, help="e.g. claude-opus-5-5 (default: the CLI's default model)")
    ap.add_argument("--workers", type=int, default=1)
    ap.add_argument("--out", default=None)
    ap.add_argument("--lab", default=None, help="where temp trial folders go (default: system temp)")
    ap.add_argument("--claude-bin", default="claude", help="pin a version: e.g. ~/.local/share/claude/versions/<ver>")
    ap.add_argument("--no-isolate", action="store_true", help="also load your user settings, plugins and MCP servers")
    ap.add_argument("--keep", action="store_true", help="keep trial folders")
    a = ap.parse_args(argv)
    conds, qs, ts = load_inputs()
    sets = tuple(s.strip() for s in a.set.split(",") if s.strip())
    cond_ids = [c.strip() for c in a.conditions.split(",") if c.strip()] or None
    items = [i.strip() for i in a.items.split(",") if i.strip()] or None
    plan = build_plan(conds, qs, ts, sets, cond_ids, a.repeats, a.seed, items)
    n = count_calls(plan, conds)
    print(f"plan: {n['measured']} measured trials + {n['activation']} activation turns + {n['preflight']} preflight calls"
          f" = {n['total_cli_calls']} `claude -p` calls · sets {','.join(sets)} · repeats {a.repeats}")
    if not a.run:
        for p in plan[:8]:
            print(f"  {p['order']:>3}. {p['trial_id']}")
        if len(plan) > 8:
            print(f"  … {len(plan) - 8} more")
        print("DRY RUN — nothing was called. Add --run to measure (it uses your Claude usage).")
        return 0
    by = {c["id"]: c for c in conds}
    missing = [s for s in {by[c]["skill"] for c in n["skill_conditions"]}
               if not fetch_skill.verify(s, cache=HERE / ".skills_cache")]
    if missing:
        print(f"REFUSED: skill file missing or sha256 differs: {missing} — run: python3 fetch_skill.py {' '.join(missing)}")
        return 2
    out = Path(a.out or HERE / "runs" / dt.datetime.now().strftime("%Y%m%d-%H%M%S"))
    out.mkdir(parents=True, exist_ok=True)
    claude = Claude(a.claude_bin, a.model, not a.no_isolate)
    ver = subprocess.run(shlex.split(a.claude_bin) + ["--version"], capture_output=True, text=True).stdout.strip()
    meta = {"started": dt.datetime.now().isoformat(timespec="seconds"), "claude_version": ver, "model_arg": a.model,
            "isolate": not a.no_isolate, "seed": a.seed, "repeats": a.repeats, "sets": sets, "calls": n,
            "skills": {s: fetch_skill.load_lock()[s] for s in {by[c]["skill"] for c in n["skill_conditions"]}}}
    (out / "plan.json").write_text(json.dumps({"meta": meta, "plan": plan}, ensure_ascii=False, indent=1), encoding="utf-8")
    runner = Runner(claude, conds, qs, ts, out, a.lab, keep=a.keep)
    if n["skill_conditions"]:
        ok, rep = runner.preflight(n["skill_conditions"])
        for r in rep:
            print(f"preflight {r['cond']} ({r['skill']}): {'PASS' if r['pass'] else 'FAIL'} — {r['status_reply']!r}")
        if not ok:
            print("REFUSED: a skill did not switch on — no measurement was run.")
            return 3
    done = done_ids(out)
    todo = [p for p in plan if p["trial_id"] not in done]
    print(f"running {len(todo)} trials ({len(done)} already done) → {out}")
    with cf.ThreadPoolExecutor(max_workers=max(1, a.workers)) as ex:
        for k, row in enumerate(ex.map(runner.trial, todo), 1):
            extra = f" check={'PASS' if row.get('check_pass') else 'FAIL'}" if row["set"] == "tasks" else ""
            print(f"[{k}/{len(todo)}] {row['trial_id']} out={row['output_tokens']} in={row['input_total']}"
                  f" {row['wall_s']}s{' ERROR' if row['is_error'] else ''}{extra}", flush=True)
    print(f"DONE → python3 report.py {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
