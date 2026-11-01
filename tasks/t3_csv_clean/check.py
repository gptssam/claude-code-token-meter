#!/usr/bin/env python3
"""t3 검사: sales_clean.csv = 중복 줄 하나만 · date 오름차순 · 머리줄 그대로 · 원본 바이트 그대로. 종료 코드 0 = PASS."""
import csv
import sys
from pathlib import Path

ORIGINAL = """date,item,amount
2026-03-05,notebook,12000
2026-01-20,pen,1500
2026-02-11,marker,3200
2026-01-20,pen,1500
2026-04-02,stapler,8900
2026-01-03,eraser,800
2026-02-11,marker,3200
2026-03-28,folder,2500
"""
WANT = [["date", "item", "amount"], ["2026-01-03", "eraser", "800"], ["2026-01-20", "pen", "1500"],
        ["2026-02-11", "marker", "3200"], ["2026-03-05", "notebook", "12000"], ["2026-03-28", "folder", "2500"],
        ["2026-04-02", "stapler", "8900"]]
work = Path(sys.argv[1])
bad = []
src = work / "data" / "sales.csv"
if not src.exists() or src.read_text(encoding="utf-8") != ORIGINAL:
    bad.append("original data/sales.csv changed or missing")
out = work / "data" / "sales_clean.csv"
if not out.exists():
    bad.append("data/sales_clean.csv missing")
else:
    rows = [r for r in csv.reader(out.read_text(encoding="utf-8-sig").splitlines()) if r]
    if rows != WANT:
        bad.append(f"rows differ: got {rows}")
print("PASS" if not bad else "FAIL\n" + "\n".join(bad))
sys.exit(1 if bad else 0)
