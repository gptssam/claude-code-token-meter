#!/usr/bin/env python3
"""Deterministic tests for the token meter. Never calls the real Claude CLI (tests/fake_claude.py).

    python3 tests/test_meter.py
"""
import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import fetch_skill  # noqa: E402
import report  # noqa: E402
import run_trials  # noqa: E402
import score  # noqa: E402

FAKE = f"{sys.executable} {ROOT / 'tests' / 'fake_claude.py'}"


class TestScore(unittest.TestCase):
    def setUp(self):
        self.qs = score.load_questions()

    def test_ten_questions_with_two_groups(self):
        self.assertEqual(len(self.qs), 10)
        for q in self.qs.values():
            self.assertGreaterEqual(len(q["required"]), 2, q["id"])

    def test_pass_and_missing(self):
        self.assertTrue(score.score("리스트는 가변, 튜플은 불변.", self.qs["q01"])["pass"])
        r = score.score("튜플은 괄호를 씁니다.", self.qs["q01"])
        self.assertFalse(r["pass"])
        self.assertEqual(r["missing_groups"], [0, 1])

    def test_forbidden_claim(self):
        r = score.score("401 Unauthorized는 인증 실패, 403 Forbidden은 권한 부족.", self.qs["q03"])
        self.assertTrue(r["pass"], r)
        r = score.score("401은 권한이 없을 때, 403은 로그인이 안 됐을 때", self.qs["q03"])
        self.assertFalse(r["pass"])
        self.assertTrue(r["forbidden_hits"])

    def test_negation_is_not_a_false_claim(self):
        r = score.score("프로세스는 메모리를 공유하지 않고, 스레드는 힙을 공유합니다.", self.qs["q06"])
        self.assertTrue(r["pass"], r)

    def test_markdown_bold_does_not_split_words(self):
        t = "탐욕적은 가능한 한 **많이**, 게으른 `*?`는 가능한 한 **적게** 매칭"
        self.assertTrue(score.score(t, self.qs["q10"])["pass"])

    def test_case_insensitive_and_deterministic(self):
        t = "PUT replaces the whole resource; PATCH is a PARTIAL update."
        self.assertEqual(score.score(t, self.qs["q08"]), score.score(t, self.qs["q08"]))
        self.assertTrue(score.score(t, self.qs["q08"])["pass"])


class TestTaskChecks(unittest.TestCase):
    def test_reference_solution_passes_and_start_files_fail(self):
        for t in ("t1_average", "t2_slugify", "t3_csv_clean"):
            chk = ROOT / "tasks" / t / "check.py"
            ok = subprocess.run([sys.executable, chk, ROOT / "tests" / "solutions" / t], capture_output=True)
            bad = subprocess.run([sys.executable, chk, ROOT / "tasks" / t / "files"], capture_output=True)
            self.assertEqual(ok.returncode, 0, t)
            self.assertNotEqual(bad.returncode, 0, t)


class TestPlan(unittest.TestCase):
    def test_full_plan_is_156(self):
        conds, qs, ts = run_trials.load_inputs()
        plan = run_trials.build_plan(conds, qs, ts)
        self.assertEqual(len(plan), 156)
        self.assertEqual(len({p["trial_id"] for p in plan}), 156)
        n = run_trials.count_calls(plan, conds)
        self.assertEqual((n["activation"], n["preflight"]), (78, 4))

    def test_shuffle_is_seeded(self):
        conds, qs, ts = run_trials.load_inputs()
        a = [p["trial_id"] for p in run_trials.build_plan(conds, qs, ts, seed=1)]
        b = [p["trial_id"] for p in run_trials.build_plan(conds, qs, ts, seed=1)]
        self.assertEqual(a, b)

    def test_dry_run_calls_nothing(self):
        log = Path(tempfile.mkdtemp()) / "calls.jsonl"
        os.environ["CTM_FAKE_LOG"] = str(log)
        try:
            with contextlib.redirect_stdout(io.StringIO()) as buf:
                rc = run_trials.main(["--claude-bin", FAKE])
        finally:
            del os.environ["CTM_FAKE_LOG"]
        self.assertEqual(rc, 0)
        self.assertIn("DRY RUN", buf.getvalue())
        self.assertFalse(log.exists())


class TestSkillLock(unittest.TestCase):
    def test_sha_mismatch_is_refused(self):
        cache = Path(tempfile.mkdtemp())
        lock = {"x": {"repo": "o/r", "ref": "abc", "path": "SKILL.md", "sha256": "0" * 64}}

        class Resp(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        with self.assertRaises(SystemExit):
            fetch_skill.fetch("x", lock, cache, opener=lambda url: Resp(b"tampered"))
        self.assertFalse(fetch_skill.cached_path("x", cache).exists())

    def test_pinned_lock_has_full_commit_and_hash(self):
        for name, e in fetch_skill.load_lock().items():
            self.assertRegex(e["ref"], r"^[0-9a-f]{40}$", name)
            self.assertRegex(e["sha256"], r"^[0-9a-f]{64}$", name)


class TestFakeRun(unittest.TestCase):
    """Whole pipeline with the fake CLI: preflight → trials → report."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.root = self.tmp / "kit"
        shutil.copytree(ROOT, self.root, ignore=shutil.ignore_patterns("runs", "__pycache__", ".skills_cache"))
        for s, body in (("caveman", b"fake caveman rules"), ("ultracave", b"fake ultracave rules")):
            p = self.root / ".skills_cache" / s / "SKILL.md"
            p.parent.mkdir(parents=True)
            p.write_bytes(body)
        lock = json.loads((self.root / "skills.lock.json").read_text())
        for s, body in (("caveman", b"fake caveman rules"), ("ultracave", b"fake ultracave rules")):
            lock[s]["sha256"] = fetch_skill.sha256(body)
        (self.root / "skills.lock.json").write_text(json.dumps(lock))
        self.log = self.tmp / "calls.jsonl"

    def run_kit(self, *args, off=False):
        env = {**os.environ, "CTM_FAKE_LOG": str(self.log)}
        if off:
            env["CTM_FAKE_OFF"] = "1"
        return subprocess.run([sys.executable, self.root / "run_trials.py", "--run", "--claude-bin", FAKE,
                               "--lab", str(self.tmp / "lab"), *args], capture_output=True, text=True, env=env, cwd=self.root)

    def test_end_to_end(self):
        out = self.tmp / "run1"
        r = self.run_kit("--set", "questions", "--items", "q01", "--repeats", "2", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        rows = [json.loads(l) for l in (out / "results.jsonl").read_text().splitlines()]
        self.assertEqual(len(rows), 8)
        calls = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertEqual(len(calls), 4 + 8 + 4)  # preflight 2×2 · measured 8 · activation 4 (C, D × 2)
        measured = [c for c in calls if not c["prompt"].startswith("/")]
        self.assertTrue(all(("--tools" in c["args"]) for c in measured))
        for row in rows:  # skill only in C/D folders, prefix only in B
            want = {"A": [], "B": [], "C": ["caveman"], "D": ["ultracave"]}[row["cond"]]
            match = [c for c in measured if c["prompt"] == row["prompt"] and c["skills"] == want]
            self.assertTrue(match, row["trial_id"])
            self.assertEqual(row["prompt"].startswith("간결하게 답해."), row["cond"] == "B")
            self.assertEqual("activation" in row, row["cond"] in ("C", "D"))
        self.assertFalse(list((self.tmp / "lab" / "ctm-lab").glob("q_*")), "trial folders are removed")
        rr = subprocess.run([sys.executable, self.root / "report.py", out], capture_output=True, text=True)
        self.assertEqual(rr.returncode, 0, rr.stderr)
        summ = json.loads((out / "summary.json").read_text())["questions"]["conditions"]
        self.assertLess(summ["D"]["output_tokens"]["median"], summ["A"]["output_tokens"]["median"])
        self.assertEqual(summ["A"]["correct"], 2)
        page = (out / "report.html").read_text()
        self.assertNotIn("http", page)  # self-contained report, nothing loaded from the web

    def test_resume_skips_done(self):
        out = self.tmp / "run2"
        self.run_kit("--set", "questions", "--items", "q02", "--conditions", "A,B", "--repeats", "1", "--out", str(out))
        n1 = len(self.log.read_text().splitlines())
        r = self.run_kit("--set", "questions", "--items", "q02", "--conditions", "A,B", "--repeats", "1", "--out", str(out))
        self.assertIn("2 already done", r.stdout)
        self.assertEqual(len(self.log.read_text().splitlines()), n1)

    def test_preflight_failure_refuses_run(self):
        out = self.tmp / "run3"
        r = self.run_kit("--set", "questions", "--items", "q01", "--repeats", "1", "--out", str(out), off=True)
        self.assertEqual(r.returncode, 3, r.stdout)
        self.assertIn("REFUSED", r.stdout)
        self.assertFalse((out / "results.jsonl").exists())
        calls = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertTrue(all(c["prompt"].startswith("/") for c in calls), "no question was sent")

    def test_missing_skill_file_refuses_run(self):
        shutil.rmtree(self.root / ".skills_cache")
        r = self.run_kit("--set", "questions", "--items", "q01", "--repeats", "1", "--out", str(self.tmp / "run4"))
        self.assertEqual(r.returncode, 2)
        self.assertFalse(self.log.exists())

    def test_task_check_recorded(self):
        out = self.tmp / "run5"
        r = self.run_kit("--set", "tasks", "--items", "t1_average", "--conditions", "A", "--repeats", "1", "--out", str(out))
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        row = json.loads((out / "results.jsonl").read_text().splitlines()[0])
        self.assertFalse(row["check_pass"])  # the fake edits nothing, so the bug is still there
        self.assertTrue((out / "task_files" / row["trial_id"] / "calc.py").exists())
        calls = [json.loads(l) for l in self.log.read_text().splitlines()]
        self.assertIn("acceptEdits", calls[0]["args"])


if __name__ == "__main__":
    unittest.main(verbosity=1)
