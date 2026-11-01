# 📏 Claude Code トークンメーター — 「トークンN%削減」を自分の質問で測る

🌐 **Language**: [**English**](./README.md) | [**简体中文**](./README.zh-CN.md) | [**日本語**](./README.ja.md) | [**한국어**](./README.ko.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-17%2F17%20OK-brightgreen)](./tests/test_meter.py)
[![Dependencies](https://img.shields.io/badge/Dependencies-Python%203%20stdlib%20only-lightgrey)](./run_trials.py)

> **「バズった数字は信じずに、測りましょう。」** 同じ質問で条件だけを変え、毎回新しいフォルダで実行し、正誤はAIの採点ではなくスクリプトが判定します。

このキットは同じ質問とコーディング課題を `claude -p` で複数の条件で実行し、CLI自身の `usage` からトークンを数えます。

| 条件 | 違い |
|---|---|
| **A** ベースライン | 何もしない |
| **B** 簡潔に | プロンプトの先頭に `간결하게 답해.`(「簡潔に答えて。」) |
| **C** `/caveman` | [caveman](https://github.com/JuliusBrussee/caveman) スキル(コミット固定・プロジェクトスキル) |
| **D** `/ultracave` | 同じコミットの ultracave スキル |

**B が重要な理由**: トークン削減スキルは、何もしないベースラインだけでなく「簡潔に答えて」の一言にも勝つべきです。caveman の README 自身も「be concise が本当の基準」と書いています。

> このキットは caveman プロジェクトとは無関係です。「Caveman」は作者の名称です。スキルファイルは同梱して**いません**。`fetch_skill.py` が固定コミットからダウンロードし、sha256 を照合します。

---

## ⚡ はじめに(まず dry run)

```bash
git clone https://github.com/gptssam/claude-code-token-meter.git
cd claude-code-token-meter
python3 tests/test_meter.py          # 期待: Ran 17 tests … OK(実際の CLI は呼びません)
python3 fetch_skill.py               # 固定コミットから caveman / ultracave の SKILL.md を取得
python3 run_trials.py                # DRY RUN: 計画を表示するだけで何も呼びません
```

各呼び出しは Claude の利用量を使います。小さく試してから全体へ:

```bash
python3 run_trials.py --run --set questions --items q01 --repeats 1
python3 run_trials.py --run --model claude-opus-5-5 --workers 3
python3 report.py runs/<フォルダ>                                       # report.md · report.html · summary.json
```

長い計測では CLI のバージョンを固定してください(`--claude-bin ~/.local/share/claude/versions/<ver>`)。途中で自動更新されると、1回の計測にバージョンが混ざります。ランナーは各呼び出しに `DISABLE_AUTOUPDATER=1` も設定します。

## 🔬 1回の試行で行うこと

1. **新しい一時フォルダ**を作ります。課題では `tasks/<id>/files/` をコピーします。
2. スキル条件では固定した `SKILL.md` を `.claude/skills/<name>/SKILL.md` にだけコピーします(グローバルには何も入れません)。
3. スキル条件では1ターン目に `/caveman`(または `/ultracave`)、同じセッションの2ターン目に質問を送ります。**測るのは2ターン目だけです。**
4. 質問はツールなし(`--tools ""`)。課題は `--permission-mode acceptEdits --allowedTools Bash` で実行し、`tasks/<id>/check.py` が PASS/FAIL を判定します。
5. ユーザー設定・プラグイン・MCP サーバーは外します(`--setting-sources project --strict-mcp-config`)。自分の環境で測るなら `--no-isolate`。

**事前確認**: 計測前に各スキルを有効にして `/caveman status` を尋ねます。期待したモードが返らなければ計測を拒否します(終了コード 3)。

**採点**(`score.py`): `prompts/questions.json` の `required` の語グループがすべて現れ、`forbidden` の正規表現に一つも当たらなければ正解です。採点基準は計測の**前に**書きます。

## 🧪 私たちの計測(2026-10-31)

**質問(条件ごとに10問 × 3回)**

| 条件 | 出力トークン中央値 | A比 | B比 | 正解 |
|---|---:|---:|---:|---:|
| A baseline | **1,100** (618–1,612) | — | — | 29/30 |
| B `간결하게 답해.` | **335** (191–551) | -69.5% | — | 30/30 |
| C `/caveman` | **571** (283–1,044) | -48.1% | +70.4% | 30/30 |
| D `/ultracave` | **499.5** (219–768) | -54.6% | +49.1% | 30/30 |

**コーディング課題(条件ごとに3課題 × 3回)**

| 条件 | 出力トークン中央値 | A比 | B比 | 正解 |
|---|---:|---:|---:|---:|
| A baseline | **863** (782–1,566) | — | — | 9/9 |
| B `간결하게 답해.` | **677** (479–976) | -21.6% | — | 9/9 |
| C `/caveman` | **895** (672–1,121) | +3.7% | +32.2% | 9/9 |
| D `/ultracave` | **798** (620–1,088) | -7.5% | +17.9% | 9/9 |

Claude Code 2.1.314 · `claude-opus-5-5` · 計測 156 回 · 計測ターンの CLI 換算コスト合計 $8.06(請求額ではありません)。要約と試行ごとの採点: [`results/2026-10-31/`](./results/2026-10-31/)。「正解」は Markdown の太字記号を除いた後の採点結果です。誤判定はすべて人が読んで確認し、A の1件(q03)は正しい回答が禁止パターンに誤って当たったもので、156件すべてが実際には正解でした。採点基準は計測後に変更していません。

## ⚠️ 限界

- 測るのは**回答の文体**だけです。caveman 4.0 の他の部品はこのキットでは測りません。
- `cost` は CLI 自身の換算値(`total_cost_usd`)で、請求額ではありません。
- 回答の長さは毎回変わります。中央値と範囲を見て、最低3回は繰り返してください。

## 📄 ライセンス

MIT(このキット)。第三者のスキルはそれぞれのライセンスと商標方針に従います — caveman リポジトリの `LICENSE` と `TRADEMARKS.md` を参照してください。
