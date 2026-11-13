#!/usr/bin/env python3
"""计算错位指标（描述性）。用法: python3 scripts/build_indicators.py"""
import csv, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rd = lambda p: list(csv.DictReader(open(ROOT / p, encoding="utf-8")))
legal = rd("data/legal_categories.csv")
glot = {r["glottocode"]: r for r in rd("data/glottolog_cn.csv")}
derived = rd("data/mapping_label_derived.csv")
pilot = rd("data/mapping_legal_language.csv")

PSEUDO = {"Bookkeeping", "Unclassifiable", "Unattested", "Sign Language", "Mixed Language", "Pidgin", "Speech Register", "Artificial Language", "(isolate/unclassified)"}
by = collections.defaultdict(list)
for d in derived:
    by[d["legal_code"]].append(d)

pilot_codes = collections.defaultdict(set)
bad = []
for r in pilot:
    for lc in r["legal_code"].split(";"):
        for g in filter(None, r["glottocodes"].split(";")):
            pilot_codes[lc].add(g)
            if g not in glot:
                bad.append((r["row_id"], g))

out = []
for L in legal:
    c = L["code"]
    ds = by.get(c, [])
    langs_only = [d for d in ds if glot[d["glottocode"]]["level"] == "language" and d["family"] not in PSEUDO]
    pseudo_n = sum(1 for d in ds if d["family"] in PSEUDO)
    fams = sorted({d["family"] for d in langs_only})
    brs = sorted({(d["family"], d["branch_l2"]) for d in langs_only})
    out.append({
        "legal_code": c, "name_zh": L["name_zh"],
        "label_entries": len(ds), "label_languages": len(langs_only),
        "label_families": len(fams), "label_family_names": "；".join(fams),
        "label_branches_l2": len(brs), "label_pseudo_entries": pseudo_n,
        "pilot_glottocodes": len(pilot_codes.get(c, ())),
        "pilot_not_in_label": "；".join(sorted(pilot_codes.get(c, set()) - {d["glottocode"] for d in ds})),
    })
(ROOT / "outputs").mkdir(exist_ok=True)
with open(ROOT / "outputs" / "indicators.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

lab = [o for o in out if o["label_entries"]]
print("有标注的法定类别:", len(lab), "/ 56")
print("其中含 2 个以上语言级条目:", sum(o["label_languages"] >= 2 for o in lab))
print("其中跨 2 个以上语系:", sum(o["label_families"] >= 2 for o in lab), [o["name_zh"] for o in lab if o["label_families"] >= 2])
print("试点表中不在中国条目表里的 Glottocode:", bad)
for o in lab:
    if o["label_families"] >= 2:
        for d in by[o["legal_code"]]:
            if d["family"] not in PSEUDO:
                print("  ", o["name_zh"], d["family"], d["glottocode"], d["name"])
