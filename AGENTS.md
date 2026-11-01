# AGENTS.md — rules for AI agents working in this kit

This kit measures how many tokens an AI answer uses under different conditions. Agents (Claude Code, Codex, Gemini/Antigravity, Cursor) follow these rules here.

## 1. Measuring costs the user's usage
- `python3 run_trials.py` is a **dry run** by default. Show the user the plan line (`plan: N measured trials + … = M claude -p calls`) and ask before adding `--run`.
- Start small: `--set questions --items q01 --repeats 1`. Only run the full plan when the user says so.
- Never install third-party skills globally (`npx … -g`, global CLIs, editing `~/.claude`). Skills are fetched by `fetch_skill.py` from a pinned commit and copied into each temp trial folder as a project skill.

## 2. Fair comparison
- Same prompt for every condition. Only the condition changes (`conditions.json`).
- Compare a token-saving skill against **condition B (「간결하게 답해.」 / "Answer concisely.")**, not only against the baseline A.
- Write the scoring criteria (`prompts/questions.json` `required` / `forbidden`) and task checks (`tasks/<id>/check.py`) **before** measuring. Do not tune them after seeing answers; if the scorer is wrong, report it as a scorer error.
- If a preflight fails (`REFUSED`), do not work around it. Tell the user which skill did not switch on.

## 3. Reporting
- Report numbers exactly as `report.py` printed them (median, plus mean and range). State the run count.
- `cost` is the CLI's own estimate (`total_cost_usd`), not an invoice. Never promise savings in money.
- Say what was measured: output style only. Do not claim a whole tool was measured when only one skill was.
- Answer in the language the user wrote in.

## 4. Files
- Do not edit `skills.lock.json` hashes to make a mismatch pass.
- `runs/` and `.skills_cache/` are local results and caches (git-ignored).
- Tests: `python3 tests/test_meter.py` (never calls the real CLI).
