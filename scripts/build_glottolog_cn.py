#!/usr/bin/env python3
"""从 glottolog-cldf 生成中国相关条目表与“民族标注”派生映射。

用法: python3 scripts/build_glottolog_cn.py <glottolog-cldf/cldf 目录>
只读输入目录；输出写入本仓库 data/。
"""
import csv, re, sys, collections
from pathlib import Path

csv.field_size_limit(10**9)
ROOT = Path(__file__).resolve().parent.parent
G = Path(sys.argv[1])

langs = {r["ID"]: r for r in csv.DictReader(open(G / "languages.csv", encoding="utf-8"))}
cn = [k for k, r in langs.items() if "CN" in (r["Countries"] or "").split(";")]

cls, aes, aes_comment = {}, {}, {}
for r in csv.DictReader(open(G / "values.csv", encoding="utf-8")):
    lid = r["Language_ID"]
    if lid not in langs:
        continue
    if r["Parameter_ID"] == "classification":
        cls[lid] = r["Value"]
    elif r["Parameter_ID"] == "aes" and lid in set(cn):
        aes[lid] = (r["Code_ID"] or "").replace("aes-", "")
        aes_comment[lid] = r["Comment"] or ""

zh = collections.defaultdict(list)
cjk = re.compile(r"[一-鿿]")
cnset = set(cn)
for r in csv.DictReader(open(G / "names.csv", encoding="utf-8")):
    if r["Language_ID"] in cnset and cjk.search(r["Name"] or ""):
        if r["Name"] not in zh[r["Language_ID"]]:
            zh[r["Language_ID"]].append(r["Name"])

legal = list(csv.DictReader(open(ROOT / "data" / "legal_categories.csv", encoding="utf-8")))
alias = {r["label_alias"]: r["code"] for r in legal}
pat = re.compile(r"Language of recognized (?:indigenous )?nationalit(?:y|ies):\s*([^.]*)\.")

rows, derived = [], []
for k in sorted(cn):
    r = langs[k]
    codes = [c for c in (cls.get(k) or "").split("/") if c]
    names = [langs[c]["Name"] if c in langs else c for c in codes]
    m = pat.search(aes_comment.get(k, ""))
    label = m.group(1).strip() if m else ""
    code = alias.get(label, "")
    rows.append({
        "glottocode": k, "name": r["Name"], "level": r["Level"], "iso639_3": r["ISO639P3code"],
        "family": names[0] if names else "",
        "branch_l2": names[1] if len(names) > 1 else "",
        "classification_path": " / ".join(names),
        "latitude": r["Latitude"], "longitude": r["Longitude"], "countries": r["Countries"],
        "aes_status": aes.get(k, ""), "nationality_label_raw": label, "legal_code_from_label": code,
        "names_cjk": "；".join(zh.get(k, [])[:6]),
    })
    if code:
        derived.append({"legal_code": code, "glottocode": k, "name": r["Name"],
                        "family": names[0] if names else "(isolate/unclassified)",
                        "branch_l2": names[1] if len(names) > 1 else "",
                        "basis": "Glottolog AES 注释所引 Ethnologue 的 recognized nationality 标注"})

def dump(path, data):
    with open(path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(data[0].keys()))
        w.writeheader(); w.writerows(data)

dump(ROOT / "data" / "glottolog_cn.csv", rows)
dump(ROOT / "data" / "mapping_label_derived.csv", sorted(derived, key=lambda d: (d["legal_code"], d["glottocode"])))
print(f"glottolog_cn.csv: {len(rows)} 行; mapping_label_derived.csv: {len(derived)} 行; 有标注的法定类别 {len({d['legal_code'] for d in derived})} 个")
