# 📏 Claude Code Token 测量器 — 用自己的问题实测「节省 N% token」

🌐 **Language**: [**English**](./README.md) | [**简体中文**](./README.zh-CN.md) | [**日本語**](./README.ja.md) | [**한국어**](./README.ko.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-17%2F17%20OK-brightgreen)](./tests/test_meter.py)
[![Dependencies](https://img.shields.io/badge/Dependencies-Python%203%20stdlib%20only-lightgrey)](./run_trials.py)

> **「别轻信爆款数字，自己测一测。」** 同一个问题，只改变条件；每次都在新文件夹里运行；答案对错由脚本判定，而不是由 AI 打分。

本工具用 `claude -p` 在多种条件下运行相同的问题和编程任务，并直接读取 CLI 返回的 `usage` 统计 token。

| 条件 | 区别 |
|---|---|
| **A** 基线 | 什么都不加 |
| **B** 简洁 | 提示开头加一句 `간결하게 답해.`（「请简洁回答。」） |
| **C** `/caveman` | [caveman](https://github.com/JuliusBrussee/caveman) 技能（固定提交 · 项目级技能） |
| **D** `/ultracave` | 同一提交中的 ultracave 技能 |

**为什么 B 很重要**：节省 token 的技能不仅要胜过什么都不加的基线，还应胜过一句「请简洁回答」。caveman 的 README 自己也写着「be concise 才是真正的基准」。

> 本工具与 caveman 项目无关。「Caveman」是其作者的名称。本仓库**不包含**技能文件，`fetch_skill.py` 会从固定提交下载并校验 sha256。

---

## ⚡ 开始（先 dry run）

```bash
git clone https://github.com/gptssam/claude-code-token-meter.git
cd claude-code-token-meter
python3 tests/test_meter.py          # 预期：Ran 17 tests … OK（不会调用真实 CLI）
python3 fetch_skill.py               # 从固定提交下载 caveman / ultracave 的 SKILL.md
python3 run_trials.py                # DRY RUN：只显示计划，不调用任何东西
```

每次调用都会消耗你的 Claude 用量。先小规模试，再跑全部：

```bash
python3 run_trials.py --run --set questions --items q01 --repeats 1
python3 run_trials.py --run --model claude-opus-5-5 --workers 3
python3 report.py runs/<文件夹>                                         # report.md · report.html · summary.json
```

长时间测量时请固定 CLI 版本（`--claude-bin ~/.local/share/claude/versions/<ver>`），否则中途自动更新会让一次测量混入两个版本。运行器也会为每次调用设置 `DISABLE_AUTOUPDATER=1`。

## 🔬 每次试验做什么

1. 创建**新的临时文件夹**。任务会复制 `tasks/<id>/files/`。
2. 技能条件只把固定的 `SKILL.md` 复制到 `.claude/skills/<name>/SKILL.md`（不做任何全局安装）。
3. 技能条件第 1 轮发送 `/caveman`（或 `/ultracave`），同一会话第 2 轮发送问题。**只测量第 2 轮。**
4. 问题在关闭工具（`--tools ""`）下运行；任务用 `--permission-mode acceptEdits --allowedTools Bash` 运行，再由 `tasks/<id>/check.py` 判定 PASS/FAIL。
5. 排除用户级设置、插件和 MCP 服务器（`--setting-sources project --strict-mcp-config`）。若要按自己的环境测量，用 `--no-isolate`。

**预检**：测量前先启用每个技能并询问 `/caveman status`，若没有返回预期模式则拒绝测量（退出码 3）。

**评分**（`score.py`）：`prompts/questions.json` 中每个 `required` 词组都出现、且没有命中任何 `forbidden` 正则，即为正确。评分标准要在测量**之前**写好。

## 🧪 我们的测量（2026-10-31）

**问题（每个条件 10 题 × 3 次）**

| 条件 | 输出 token 中位数 | 对比 A | 对比 B | 正确 |
|---|---:|---:|---:|---:|
| A baseline | **1,100** (618–1,612) | — | — | 29/30 |
| B `간결하게 답해.` | **335** (191–551) | -69.5% | — | 30/30 |
| C `/caveman` | **571** (283–1,044) | -48.1% | +70.4% | 30/30 |
| D `/ultracave` | **499.5** (219–768) | -54.6% | +49.1% | 30/30 |

**编程任务（每个条件 3 题 × 3 次）**

| 条件 | 输出 token 中位数 | 对比 A | 对比 B | 正确 |
|---|---:|---:|---:|---:|
| A baseline | **863** (782–1,566) | — | — | 9/9 |
| B `간결하게 답해.` | **677** (479–976) | -21.6% | — | 9/9 |
| C `/caveman` | **895** (672–1,121) | +3.7% | +32.2% | 9/9 |
| D `/ultracave` | **798** (620–1,088) | -7.5% | +17.9% | 9/9 |

Claude Code 2.1.314 · `claude-opus-5-5` · 共测量 156 次 · 被测轮次的 CLI 估算费用合计 $8.06（不是账单）。汇总和每次试验的评分：[`results/2026-10-31/`](./results/2026-10-31/)。「正确」是去掉 Markdown 粗体符号后的评分结果。所有判错都经人工阅读：A 的 1 次（q03）是正确答案误触了禁止模式，因此 156 个回答实际上全部正确。测量之后没有修改评分标准。

## ⚠️ 局限

- 只测量**回答风格**。caveman 4.0 的其他部分本工具不测量。
- `cost` 是 CLI 自己的估算（`total_cost_usd`），不是账单。
- 回答长度每次不同。请看中位数和范围，并至少重复 3 次。

## 📄 许可证

MIT（本工具）。第三方技能遵循其各自的许可证和商标政策 — 请参阅 caveman 仓库的 `LICENSE` 和 `TRADEMARKS.md`。
