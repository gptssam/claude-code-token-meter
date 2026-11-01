# 📏 Claude Code 토큰 측정기 — 「토큰 N% 절감」을 내 질문으로 직접 재 보기

🌐 **Language**: [**English**](./README.md) | [**简体中文**](./README.zh-CN.md) | [**日本語**](./README.ja.md) | [**한국어**](./README.ko.md)

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](./LICENSE)
[![Tests](https://img.shields.io/badge/Tests-17%2F17%20OK-brightgreen)](./tests/test_meter.py)
[![Dependencies](https://img.shields.io/badge/Dependencies-Python%203%20stdlib%20only-lightgrey)](./run_trials.py)

> **「바이럴 숫자는 믿지 말고 재 보세요.」** 같은 질문에 조건만 바꾸고, 회차마다 새 폴더에서, 정답은 AI 채점관이 아니라 스크립트가 판정합니다.

이 킷은 같은 질문과 코딩 과제를 `claude -p`로 여러 조건에서 돌리고, CLI가 직접 내놓는 `usage` 숫자로 토큰을 셉니다.

| 조건 | 무엇이 다른가 |
|---|---|
| **A** 기본 | 아무것도 없음 |
| **B** 두 단어 | 질문 앞에 `간결하게 답해.` 한 줄 |
| **C** `/caveman` | [caveman](https://github.com/JuliusBrussee/caveman) 스킬(커밋 고정 · 프로젝트 스킬) |
| **D** `/ultracave` | 같은 커밋의 ultracave 스킬 |

**B가 중요한 이유**: 토큰을 줄이는 스킬이라면 아무 지시 없는 기본(A)이 아니라 「간결하게 답해」 두 단어(B)보다 나아야 합니다. caveman README도 「be concise가 진짜 기준」이라고 스스로 적어 두었습니다.

> 이 킷은 caveman 프로젝트와 관계가 없습니다. 「Caveman」은 작성자의 이름입니다. 스킬 파일은 이 저장소에 **넣지 않았고**, `fetch_skill.py`가 고정 커밋에서 내려받은 뒤 sha256을 대조합니다.

---

## ⚡ 시작 (먼저 dry run)

```bash
git clone https://github.com/gptssam/claude-code-token-meter.git
cd claude-code-token-meter
python3 tests/test_meter.py          # 기대: Ran 17 tests … OK (실제 CLI를 부르지 않음)
python3 fetch_skill.py               # 고정 커밋에서 caveman · ultracave SKILL.md 받기
python3 run_trials.py                # DRY RUN: 계획만 보여 주고 아무것도 부르지 않음
```

dry run은 이렇게 보여 줍니다.

```
plan: 156 measured trials + 78 activation turns + 4 preflight calls = 238 `claude -p` calls
```

호출마다 내 Claude 사용량이 쓰입니다. 작게 먼저, 그다음 전체로:

```bash
python3 run_trials.py --run --set questions --items q01 --repeats 1     # 4회 + 켜기 2 + 사전 확인 4
python3 run_trials.py --run --model claude-opus-5-5 --workers 3          # 전체 계획
python3 report.py runs/<폴더>                                           # report.md · report.html · summary.json
```

긴 실측은 CLI 판을 고정하세요(`--claude-bin ~/.local/share/claude/versions/<판>`). 중간에 자동 업데이트되면 한 실측 안에 판이 섞입니다. 실행기는 호출마다 `DISABLE_AUTOUPDATER=1`도 넣습니다.

## 🔬 1회 실측이 하는 일

1. **새 임시 폴더**를 만듭니다. 작업 과제는 `tasks/<id>/files/`를 복사해 넣습니다.
2. 스킬 조건은 고정한 `SKILL.md`를 `.claude/skills/<이름>/SKILL.md`에만 복사합니다(프로젝트 스킬 — 전역 설치 없음).
3. 스킬 조건은 1턴에 `/caveman`(또는 `/ultracave`)을 보내고, 같은 세션 2턴에 질문을 보냅니다. **재는 것은 2턴뿐입니다.**
4. 질문은 도구를 끄고(`--tools ""`) 돌립니다. 작업 과제는 `--permission-mode acceptEdits --allowedTools Bash`로 돌린 뒤 `tasks/<id>/check.py`가 PASS/FAIL을 정합니다.
5. 사용자 전역 설정 · 플러그인 · MCP 서버는 빼고(`--setting-sources project --strict-mcp-config`) 모든 조건을 같은 출발선에서 시작합니다. 내 환경 그대로 재려면 `--no-isolate`.

**사전 확인**: 측정 전에 스킬 조건마다 스킬을 켜고 `/caveman status`를 묻습니다. 기대한 모드가 안 나오면 실측을 거부합니다(종료 코드 3).

**채점**(`score.py`): `prompts/questions.json`의 `required` 낱말 묶음이 모두 나오고 `forbidden` 정규식이 하나도 안 걸리면 정답입니다. 같은 글이면 언제나 같은 점수. 채점 기준은 재기 **전에** 적습니다.

## 🧪 우리 실측 (2026-10-31)

**질문 묶음 (조건마다 10문항 × 3회)**

| 조건 | 출력 토큰 중앙값 | A 대비 | B 대비 | 정답 |
|---|---:|---:|---:|---:|
| A baseline | **1,100** (618–1,612) | — | — | 29/30 |
| B `간결하게 답해.` | **335** (191–551) | -69.5% | — | 30/30 |
| C `/caveman` | **571** (283–1,044) | -48.1% | +70.4% | 30/30 |
| D `/ultracave` | **499.5** (219–768) | -54.6% | +49.1% | 30/30 |

**작업 과제 묶음 (조건마다 3과제 × 3회)**

| 조건 | 출력 토큰 중앙값 | A 대비 | B 대비 | 정답 |
|---|---:|---:|---:|---:|
| A baseline | **863** (782–1,566) | — | — | 9/9 |
| B `간결하게 답해.` | **677** (479–976) | -21.6% | — | 9/9 |
| C `/caveman` | **895** (672–1,121) | +3.7% | +32.2% | 9/9 |
| D `/ultracave` | **798** (620–1,088) | -7.5% | +17.9% | 9/9 |

Claude Code 2.1.314 · `claude-opus-5-5` · 실측 156회 · 잰 턴의 CLI 환산 비용 합계 $8.06(청구서 아님). 요약과 회차별 채점: [`results/2026-10-31/`](./results/2026-10-31/). 「정답」은 굵은 글씨 표시를 지운 뒤의 채점기 판정입니다. 틀린 판정은 사람이 모두 읽어 봤고, A의 1건(q03)은 맞는 답이 금지 패턴에 잘못 걸린 것이라 156개 답이 실제로는 모두 정답이었습니다. 채점 기준은 실측 뒤에 바꾸지 않았습니다.

## 🛠 내 일로 재 보기

1. `prompts/questions.json`을 내가 실제로 묻는 질문 5~10개로 바꾸고, 질문마다 꼭 나와야 할 낱말 묶음 2개를 적습니다.
2. 선택: 작업 과제 폴더 `tasks/<id>/files/` + `tasks/<id>/check.py`(종료 코드 0 = PASS)를 만들고 `prompts/tasks.json`에 한 줄 더합니다.
3. `conditions.json`에서 조건을 더하거나 고칩니다(내 지시 한 줄, `skills.lock.json`에 고정한 다른 스킬).
4. dry run → 작은 실측 → 전체 실측 → `report.py`.

## ⚠️ 한계

- **답 말투(Say less)**만 잽니다. caveman 4.0의 다른 부품(Read less · Auto · Blocks · 브라우저)은 이 킷이 재지 않습니다.
- `cost`는 CLI가 스스로 환산한 값(`total_cost_usd`)이고 청구서가 아닙니다.
- 답 길이는 회차마다 달라집니다. 중앙값과 범위를 보고, 최소 3회 반복하세요.
- 낱말 묶음 채점은 핵심 사실이 빠졌는지와 알려진 틀린 주장 몇 개만 잡습니다. 답 전체를 검토하는 것은 아닙니다.

## 📄 라이선스

MIT(이 킷). 다른 사람의 스킬은 각자의 라이선스와 상표 정책을 따릅니다 — caveman 저장소의 `LICENSE` · `TRADEMARKS.md`를 보세요.
