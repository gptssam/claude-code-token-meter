# GEMINI.md — Gemini / Antigravity entry point

Read [`AGENTS.md`](./AGENTS.md) in this folder first and follow it.

The runner drives the Claude Code CLI (`claude -p`). To measure another CLI, copy `run_trials.py`'s `Claude` class, change the command line, and map that CLI's usage fields in `usage_fields()`. Keep the dry-run default and the preflight.

```bash
python3 tests/test_meter.py
python3 run_trials.py           # dry run
```
