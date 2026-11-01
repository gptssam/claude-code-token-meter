# 📏 Claude Code Token Meter — measure "saves N% tokens" claims with your own prompts

🌐 **Language**: [**English**](./README.md) | [**简体中文**](./README.zh-CN.md) | [**日本語**](./README.ja.md) | [**한국어**](./README.ko.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-17%2F17%20OK-brightgreen)](./tests/test_meter.py)
[![Dependencies](https://img.shields.io/badge/Dependencies-Python%203%20stdlib%20only-lightgrey)](./run_trials.py)

> **"Don't trust a viral number. Measure it."** Same prompt, only the condition changes, a new folder every time, and the answer is checked by a script — not by an AI judge.

This kit runs the same questions and coding tasks through `claude -p` under several conditions and counts tokens from the CLI's own `usage` field:

| Condition | What is different |
|---|---|
| **A** baseline | nothing |
| **B** concise | the prompt starts with `간결하게 답해.` ("Answer concisely.") |
| **C** `/caveman` | the [caveman](https://github.com/JuliusBrussee/caveman) skill, pinned commit, as a project skill |
| **D** `/ultracave` | the ultracave skill from the same commit |

Why **B** matters: a token-saving skill should beat a plain "answer concisely", not only the bare baseline. The caveman README itself names "be concise" as the real baseline.

> This kit is not affiliated with the caveman project. "Caveman" is its author's name; the skill files are **not** bundled here — `fetch_skill.py` downloads them from the pinned commit and checks their sha256.

---

## ⚡ Start (dry run first)

```bash
git clone https://github.com/gptssam/claude-code-token-meter.git
cd claude-code-token-meter
python3 tests/test_meter.py          # expected: Ran 17 tests … OK (never calls the real CLI)
python3 fetch_skill.py               # downloads caveman + ultracave SKILL.md from the pinned commit
python3 run_trials.py                # DRY RUN: prints the plan, calls nothing
```

The dry run prints something like:

```
plan: 156 measured trials + 78 activation turns + 4 preflight calls = 238 `claude -p` calls
```

Every call uses your Claude usage. Start small, then go big:

```bash
python3 run_trials.py --run --set questions --items q01 --repeats 1     # 4 trials + 2 activations + 4 preflight
python3 run_trials.py --run --model claude-opus-5-5 --workers 3          # the full plan
python3 report.py runs/<folder>                                         # report.md · report.html · summary.json
```

Tip: pin the CLI version for a long run so it cannot update itself halfway (`--claude-bin ~/.local/share/claude/versions/<ver>`). The runner also sets `DISABLE_AUTOUPDATER=1` for its calls.

## 🔬 What one trial does

1. Makes a **new temp folder**. Task trials copy `tasks/<id>/files/` into it.
2. Skill conditions copy the pinned `SKILL.md` to `.claude/skills/<name>/SKILL.md` (project skill only — nothing global).
3. Skill conditions send `/caveman` (or `/ultracave`) as turn 1, then the question as turn 2 in the same session. **Only turn 2 is measured.**
4. Questions run with tools off (`--tools ""`). Tasks run with `--permission-mode acceptEdits --allowedTools Bash`, then `tasks/<id>/check.py` decides PASS/FAIL.
5. User-level settings, plugins and MCP servers are left out (`--setting-sources project --strict-mcp-config`) so every condition starts the same. Use `--no-isolate` to measure with your own setup.

**Preflight**: before any measurement, each skill condition is switched on and asked `/caveman status`. If it does not report the expected mode, the run is refused (exit 3).

**Scoring** (`score.py`): every `required` group in `prompts/questions.json` must appear and no `forbidden` regex may match. Same text in → same score out. Write the criteria before you measure.

## 🧪 Our run (2026-10-31)

**Questions (10 × 3 runs per condition)**

| Condition | Median output tokens | vs A | vs B | Correct |
|---|---:|---:|---:|---:|
| A baseline | **1,100** (618–1,612) | — | — | 29/30 |
| B `간결하게 답해.` | **335** (191–551) | -69.5% | — | 30/30 |
| C `/caveman` | **571** (283–1,044) | -48.1% | +70.4% | 30/30 |
| D `/ultracave` | **499.5** (219–768) | -54.6% | +49.1% | 30/30 |

**Coding tasks (3 × 3 runs per condition)**

| Condition | Median output tokens | vs A | vs B | Correct |
|---|---:|---:|---:|---:|
| A baseline | **863** (782–1,566) | — | — | 9/9 |
| B `간결하게 답해.` | **677** (479–976) | -21.6% | — | 9/9 |
| C `/caveman` | **895** (672–1,121) | +3.7% | +32.2% | 9/9 |
| D `/ultracave` | **798** (620–1,088) | -7.5% | +17.9% | 9/9 |

Claude Code 2.1.314 · `claude-opus-5-5` · 156 measured trials · CLI cost estimate for the measured turns $8.06 (not an invoice). Summary and per-trial scores: [`results/2026-10-31/`](./results/2026-10-31/). "Correct" is the scorer's verdict after removing Markdown bold; a person read every miss — the one A miss (q03) is a correct answer that tripped a `forbidden` pattern, so all 156 answers were actually correct. The criteria were not changed after measuring.

## 🛠 Measure your own work

1. Replace `prompts/questions.json` with 5–10 questions you actually ask, each with two `required` word groups.
2. Optional: add a task folder `tasks/<id>/files/` + `tasks/<id>/check.py` (exit 0 = PASS) and list it in `prompts/tasks.json`.
3. Add or edit conditions in `conditions.json` (your own prompt prefix, another skill pinned in `skills.lock.json`).
4. Dry run → small run → full run → `report.py`.

## ⚠️ Limits

- Measures the **answer style** only. caveman 4.0 has other parts (reading less, automation, blocks, browser) that this kit does not measure.
- `cost` is the CLI's own estimate (`total_cost_usd`), not an invoice.
- Answer length varies run to run. Look at medians and ranges, and repeat at least 3 times.
- Word-group scoring catches missing key facts and a few known wrong claims. It is not a full review of the answer.

## 📄 License

MIT (this kit). Third-party skills keep their own licenses and trademarks — see the caveman repository's `LICENSE` and `TRADEMARKS.md`.
