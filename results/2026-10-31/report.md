# Token meter report

- Claude Code: `2.1.314 (Claude Code)` · model arg: `claude-opus-5-5` · isolate: True · repeats: 3 · started 2026-10-31T08:05:17
- `cost` = the CLI's own estimate (`total_cost_usd`), not an invoice.

## questions

| cond | runs | median output tokens (mean · min–max) | vs A | vs B | median chars | median input | correct | cost (measured turn) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| A No instruction | 30 | **1,100** (1,072.9 · 618–1,612) | — | — | 1,353.5 | 2,840 | 29/30 | $1.17 |
| B "간결하게 답해." (Answer concisely.) | 30 | **335** (339.9 · 191–551) | -69.5% | — | 428.5 | 2,849 | 30/30 | $0.74 |
| C /caveman skill (project skill) | 30 | **571** (584.8 · 283–1,044) | -48.1% | +70.4% | 659 | 4,612.5 | 30/30 | $1.40 |
| D /ultracave skill (project skill) | 30 | **499.5** (486 · 219–768) | -54.6% | +49.1% | 610.5 | 3,753 | 30/30 | $1.14 |

Median output tokens per item:

| item | A | B | C | D |
|---|---:|---:|---:|---:|
| q01 | 1,184 | 389 | 832 | 545 |
| q02 | 1,246 | 309 | 595 | 494 |
| q03 | 692 | 207 | 304 | 302 |
| q04 | 1,104 | 341 | 488 | 497 |
| q05 | 727 | 281 | 351 | 261 |
| q06 | 917 | 425 | 545 | 663 |
| q07 | 1,051 | 237 | 566 | 457 |
| q08 | 1,081 | 419 | 748 | 592 |
| q09 | 1,543 | 446 | 848 | 567 |
| q10 | 1,131 | 335 | 605 | 551 |

## tasks

| cond | runs | median output tokens (mean · min–max) | vs A | vs B | median chars | median input | correct | cost (measured turn) |
|---|---:|---|---:|---:|---:|---:|---:|---:|
| A No instruction | 9 | **863** (1,029.1 · 782–1,566) | — | — | 447 | 70,691 | 9/9 | $0.79 |
| B "간결하게 답해." (Answer concisely.) | 9 | **677** (714.7 · 479–976) | -21.6% | — | 277 | 53,360 | 9/9 | $0.71 |
| C /caveman skill (project skill) | 9 | **895** (897.4 · 672–1,121) | +3.7% | +32.2% | 435 | 77,939 | 9/9 | $1.08 |
| D /ultracave skill (project skill) | 9 | **798** (824.7 · 620–1,088) | -7.5% | +17.9% | 269 | 74,607 | 9/9 | $1.02 |

Median output tokens per item:

| item | A | B | C | D |
|---|---:|---:|---:|---:|
| t1_average | 855 | 677 | 695 | 752 |
| t2_slugify | 1,397 | 910 | 1,103 | 883 |
| t3_csv_clean | 787 | 563 | 895 | 747 |
