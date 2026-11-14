#!/usr/bin/env python3
"""T19：输出计数表（不画图、不下结论）。
读 data/partitions/han_partitions.csv 与 data/events/gaitu_guiliu.csv，写 outputs/ 下两张计数表。
分类规则只按 trigger 列里的字面关键词归类，不做额外判断。"""
import csv, re, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rd = lambda p: list(csv.DictReader(open(ROOT / p, encoding="utf-8")))

# 1) 按口径的类别数
rows = rd("data/partitions/han_partitions.csv")
with open(ROOT / "outputs/partitions_counts.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["regime", "basis", "n_listed", "evidence_grade"])
    for r in rows:
        w.writerow([r["regime"], r["basis"], r["n_listed"], r["evidence_grade"]])

# 2) 按年代与触发因素的事件计数
def era(y):
    m = re.search(r"(1[0-9]{3})", y)
    yr = int(m.group(1)) if m else None
    if "雍正" in y or (yr and 1723 <= yr <= 1735):
        return "雍正朝（1723—1735）"
    if any(k in y for k in ("明", "嘉靖", "崇祯", "永乐")) or (yr and yr <= 1644):
        return "明代（至1644）"
    return "年代未标"

def trig(t):
    if t.startswith("不适用"):
        return "不适用（保留）"
    if "学者论点" in t:
        return "学者论点（非原档转述）"
    if "叛乱" in t:
        return "叛乱"
    if "承袭争端" in t:
        return "承袭争端"
    if "军事通道" in t:
        return "军事通道"
    if t.startswith("来源未述"):
        return "来源未述"
    return "来源明说的其他原因"

cnt = collections.Counter((era(r["year"]), trig(r["trigger"])) for r in rd("data/events/gaitu_guiliu.csv"))
with open(ROOT / "outputs/events_counts.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["era", "trigger_class", "n_events"])
    for (e, t), n in sorted(cnt.items()):
        w.writerow([e, t, n])
print("partitions rows:", len(rows), "| events:", sum(cnt.values()))
