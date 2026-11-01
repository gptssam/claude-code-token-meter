# CLAUDE.md — Claude Code entry point

Read [`AGENTS.md`](./AGENTS.md) in this folder first and follow it.

Claude Code specifics:
- `run_trials.py` calls `claude -p … --output-format json` and reads `usage` from the result. Each trial runs in a new temp folder.
- Skill conditions send `/caveman` (or `/ultracave`) as turn 1 and the question as turn 2 (`--resume`). Only turn 2 is measured.
- By default user-level settings, plugins and MCP servers are left out (`--setting-sources project --strict-mcp-config`) so every condition starts the same. `--no-isolate` measures with your own setup.

```bash
python3 tests/test_meter.py     # expected: Ran 17 tests … OK
python3 run_trials.py           # dry run: shows the plan, calls nothing
```
