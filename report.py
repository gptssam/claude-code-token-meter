#!/usr/bin/env python3
"""Summarise a run: tokens and correctness per condition → summary.json · report.md · report.html.

    python3 report.py runs/<dir>

Questions are scored with score.py (deterministic). Tasks use the PASS/FAIL that run_trials.py
stored from tasks/<id>/check.py. Medians are the headline (answer length varies run to run);
mean, min and max are shown next to them. If a trial id appears twice, the last row counts.
"""
import html
import json
import statistics as st
import sys
from pathlib import Path

import score

HERE = Path(__file__).resolve().parent


def load_rows(run_dir):
    rows = {}
    for line in (Path(run_dir) / "results.jsonl").read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["trial_id"]] = r
    return list(rows.values())


def add_scores(rows, qs):
    for r in rows:
        if r["set"] == "questions" and not r.get("is_error"):
            s = score.score(r.get("answer", ""), qs[r["item"]])
            r["correct"], r["score_detail"] = s["pass"], s
        elif r["set"] == "tasks" and not r.get("is_error"):
            r["correct"] = bool(r.get("check_pass"))
    return rows


def stats(vals):
    v = [x for x in vals if x is not None]
    if not v:
        return None
    return {"n": len(v), "median": st.median(v), "mean": round(st.mean(v), 1), "min": min(v), "max": max(v)}


def pct(a, b):
    return None if not a or b is None else round((b - a) / a * 100, 1)


def summarise(rows, conds):
    out = {}
    for s in ("questions", "tasks"):
        sub = [r for r in rows if r["set"] == s]
        if not sub:
            continue
        per = {}
        for c in conds:
            rs = [r for r in sub if r["cond"] == c["id"]]
            ok = [r for r in rs if not r.get("is_error")]
            if not rs:
                continue
            per[c["id"]] = {
                "label": c["label"], "runs": len(rs), "errors": len(rs) - len(ok),
                "output_tokens": stats([r["output_tokens"] for r in ok]),
                "thinking_tokens": stats([r.get("thinking_tokens") for r in ok]),
                "answer_chars": stats([r.get("answer_chars") for r in ok]),
                "input_total": stats([r["input_total"] for r in ok]),
                "duration_s": stats([(r.get("duration_ms") or 0) / 1000 for r in ok]),
                "cost_usd_sum": round(sum(r.get("cost_usd") or 0 for r in ok), 4),
                "activation_cost_usd_sum": round(sum((r.get("activation") or {}).get("cost_usd") or 0 for r in ok), 4),
                "correct": sum(1 for r in ok if r.get("correct")), "scored": len(ok),
            }
        base = {k: (v["output_tokens"] or {}).get("median") for k, v in per.items()}
        for k, v in per.items():
            m = (v["output_tokens"] or {}).get("median")
            v["median_out_vs_A_pct"] = pct(base.get("A"), m) if k != "A" else None
            v["median_out_vs_B_pct"] = pct(base.get("B"), m) if k not in ("A", "B") else None
        items = sorted({r["item"] for r in sub})
        per_item = {i: {c["id"]: (stats([r["output_tokens"] for r in sub if r["item"] == i and r["cond"] == c["id"]
                                         and not r.get("is_error")]) or {}).get("median") for c in conds} for i in items}
        out[s] = {"conditions": per, "per_item_median_output": per_item}
    return out


def fmt(x):
    if x is None:
        return "—"
    if isinstance(x, float) and not x.is_integer():
        return f"{x:,.1f}"
    return f"{int(x):,}"


def signed(x):
    return "—" if x is None else f"{x:+.1f}%"


def to_markdown(summ, meta):
    L = [f"# Token meter report", "", f"- Claude Code: `{meta.get('claude_version', '?')}` · model arg: `{meta.get('model_arg')}` "
         f"· isolate: {meta.get('isolate')} · repeats: {meta.get('repeats')} · started {meta.get('started')}",
         "- `cost` = the CLI's own estimate (`total_cost_usd`), not an invoice.", ""]
    for s, block in summ.items():
        L += [f"## {s}", "", "| cond | runs | median output tokens (mean · min–max) | vs A | vs B | median chars | median input | correct | cost (measured turn) |",
              "|---|---:|---|---:|---:|---:|---:|---:|---:|"]
        for cid, v in block["conditions"].items():
            o = v["output_tokens"] or {}
            L.append(f"| {cid} {v['label']} | {v['runs']}{' (' + str(v['errors']) + ' err)' if v['errors'] else ''} | "
                     f"**{fmt(o.get('median'))}** ({fmt(o.get('mean'))} · {fmt(o.get('min'))}–{fmt(o.get('max'))}) | "
                     f"{signed(v['median_out_vs_A_pct'])} | {signed(v['median_out_vs_B_pct'])} | "
                     f"{fmt((v['answer_chars'] or {}).get('median'))} | {fmt((v['input_total'] or {}).get('median'))} | "
                     f"{v['correct']}/{v['scored']} | ${v['cost_usd_sum']:.2f} |")
        cids = list(block["conditions"])
        L += ["", "Median output tokens per item:", "", "| item | " + " | ".join(cids) + " |", "|---|" + "---:|" * len(cids)]
        for i, row in block["per_item_median_output"].items():
            L.append(f"| {i} | " + " | ".join(fmt(row.get(c)) for c in cids) + " |")
        L.append("")
    return "\n".join(L)


CSS = """body{font-family:-apple-system,'Apple SD Gothic Neo',sans-serif;max-width:1100px;margin:32px auto;padding:0 16px;
color:#0f172a;background:#fff}table{border-collapse:collapse;width:100%;margin:12px 0 28px}th,td{border:1px solid #e2e8f0;
padding:6px 10px;text-align:right}th{background:#eef2ff}td:first-child,th:first-child{text-align:left}.bar{height:12px;
background:#4f46e5;border-radius:3px}"""


def to_html(summ, meta):
    h = [f"<!doctype html><meta charset='utf-8'><title>Token meter report</title><style>{CSS}</style>",
         "<h1>Token meter report</h1>",
         f"<p>Claude Code <code>{html.escape(str(meta.get('claude_version')))}</code> · model arg "
         f"<code>{html.escape(str(meta.get('model_arg')))}</code> · repeats {meta.get('repeats')} · "
         f"started {html.escape(str(meta.get('started')))}. Cost = CLI estimate, not an invoice.</p>"]
    for s, block in summ.items():
        top = max([(v["output_tokens"] or {}).get("median") or 0 for v in block["conditions"].values()] + [1])
        h += [f"<h2>{s}</h2><table><tr><th>condition</th><th>runs</th><th>median output tokens</th><th></th>"
              "<th>vs A</th><th>vs B</th><th>median input</th><th>correct</th></tr>"]
        for cid, v in block["conditions"].items():
            m = (v["output_tokens"] or {}).get("median") or 0
            h.append(f"<tr><td>{cid} {html.escape(v['label'])}</td><td>{v['runs']}</td><td>{fmt(m)}</td>"
                     f"<td style='width:30%'><div class='bar' style='width:{m / top * 100:.0f}%'></div></td>"
                     f"<td>{signed(v['median_out_vs_A_pct'])}</td><td>{signed(v['median_out_vs_B_pct'])}</td>"
                     f"<td>{fmt((v['input_total'] or {}).get('median'))}</td><td>{v['correct']}/{v['scored']}</td></tr>")
        h.append("</table>")
    return "\n".join(h) + "\n"


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    run = Path(argv[0])
    conds = json.loads((HERE / "conditions.json").read_text(encoding="utf-8"))["conditions"]
    rows = add_scores(load_rows(run), score.load_questions())
    meta = json.loads((run / "plan.json").read_text(encoding="utf-8"))["meta"] if (run / "plan.json").exists() else {}
    summ = summarise(rows, conds)
    (run / "summary.json").write_text(json.dumps(summ, ensure_ascii=False, indent=1), encoding="utf-8")
    (run / "scored.jsonl").write_text("".join(json.dumps({k: r.get(k) for k in (
        "trial_id", "set", "item", "cond", "rep", "output_tokens", "answer_chars", "correct", "score_detail")},
        ensure_ascii=False) + "\n" for r in sorted(rows, key=lambda r: r["trial_id"])), encoding="utf-8")
    md = to_markdown(summ, meta)
    (run / "report.md").write_text(md, encoding="utf-8")
    (run / "report.html").write_text(to_html(summ, meta), encoding="utf-8")
    print(md)
    print(f"\n→ {run / 'report.html'}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
