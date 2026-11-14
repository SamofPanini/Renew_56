#!/usr/bin/env python3
"""计算错位指标（描述性）。用法: python3 scripts/build_indicators.py

同时读两张映射表：
  data/mapping_label_derived.csv   标注派生映射（脚本生成）
  data/mapping_legal_language.csv  人工映射（试点 11 类 + T18 的 45 类）
前 10 列（label_* 与 pilot_*）沿用 T17 的定义不变；其后各列为 T18 新增；
aligned_by_alias 与 shift_shared_with 为 T21 新增。

T11 裁决⑩：语言转用（某类现用另一类的语言，如塔塔尔族通用维吾尔语、哈萨克语）
不计为类别间共用变体。SHIFT_ROWS 中的行仍计入本类已对齐条目，但共用关系另列在
shift_shared_with，不进 shared_with。
"""
import csv, collections
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
rd = lambda p: list(csv.DictReader(open(ROOT / p, encoding="utf-8")))
legal = rd("data/legal_categories.csv")
glot = {r["glottocode"]: r for r in rd("data/glottolog_cn.csv")}
derived = rd("data/mapping_label_derived.csv")
manual = rd("data/mapping_legal_language.csv")
name_of = {L["code"]: L["name_zh"] for L in legal}

PSEUDO = {"Bookkeeping", "Unclassifiable", "Unattested", "Sign Language", "Mixed Language", "Pidgin", "Speech Register", "Artificial Language", "(isolate/unclassified)"}
by = collections.defaultdict(list)
for d in derived:
    by[d["legal_code"]].append(d)

SHIFT_ROWS = {"X-50-02"}   # neac：维吾尔、哈萨克两族语言文字“已成为塔塔尔族人的通用的语言文字”
is_lang = lambda g: g in glot and glot[g]["level"] == "language" and glot[g]["family"] not in PSEUDO

manual_codes = collections.defaultdict(set)      # 人工表里出现的全部 Glottocode
by_name = collections.defaultdict(set)           # align_basis = name
by_label_row = collections.defaultdict(set)      # align_basis = label
by_alias = collections.defaultdict(set)          # align_basis = alias（T21 别名表）
shift_codes = collections.defaultdict(set)       # 语言转用行的条目
nonshift_codes = collections.defaultdict(set)    # 非转用行（含标注）的条目
unbased = collections.defaultdict(set)           # 试点行（无 align_basis）
domestic_rows = collections.Counter()            # 国内口径变体数 = 有国内依据的行数
unaligned_rows = collections.Counter()
bad = []
for r in manual:
    shared_row = r["row_id"].startswith("XS-")
    gcs = [g for g in r["glottocodes"].split(";") if g]
    basis = (r.get("align_basis") or "").strip()
    for lc in r["legal_code"].split(";"):
        for g in gcs:
            manual_codes[lc].add(g)
            {"name": by_name, "label": by_label_row, "alias": by_alias}.get(basis, unbased)[lc].add(g)
            (shift_codes if r["row_id"] in SHIFT_ROWS else nonshift_codes)[lc].add(g)
            if g not in glot:
                bad.append((r["row_id"], g))
        if shared_row or basis == "label" or "系属措辞" in r["variety_label"]:
            continue
        domestic_rows[lc] += 1
        if not gcs:
            unaligned_rows[lc] += 1

# 每类的“已对齐条目”= 人工表条目 ∪ 标注派生条目（限表内、语言级、非伪语系）
aligned = {}
for L in legal:
    c = L["code"]
    aligned[c] = {g for g in manual_codes[c] | {d["glottocode"] for d in by.get(c, [])} if is_lang(g)}
    nonshift_codes[c] |= {d["glottocode"] for d in by.get(c, [])}
# 某条目在本类“只经语言转用行而来”时，不算本类自有，共用关系另列
shift_only = {c: {g for g in aligned[c] if g in shift_codes[c] and g not in nonshift_codes[c]} for c in aligned}
owners = collections.defaultdict(set)
for c, gs in aligned.items():
    for g in gs - shift_only[c]:
        owners[g].add(c)

out = []
for L in legal:
    c = L["code"]
    ds = by.get(c, [])
    langs_only = [d for d in ds if glot[d["glottocode"]]["level"] == "language" and d["family"] not in PSEUDO]
    pseudo_n = sum(1 for d in ds if d["family"] in PSEUDO)
    fams = sorted({d["family"] for d in langs_only})
    brs = sorted({(d["family"], d["branch_l2"]) for d in langs_only})
    al = aligned[c]
    al_fams = sorted({glot[g]["family"] for g in al})
    name_fams = sorted({glot[g]["family"] for g in by_name[c] | unbased[c] | by_alias[c] if is_lang(g)})  # T21 起含别名
    shared = collections.defaultdict(list)
    for g in sorted(al - shift_only[c]):
        for o in sorted(owners[g] - {c}):
            shared[o].append(g)
    shift = collections.defaultdict(list)       # 本类经转用而用的条目 → 原属类；或他类经转用用本类条目
    for g in sorted(al):
        for o in sorted(owners[g] - {c}) if g in shift_only[c] else sorted(o for o in aligned if g in shift_only[o] and o != c):
            shift[o].append(g)
    out.append({
        "legal_code": c, "name_zh": L["name_zh"],
        "label_entries": len(ds), "label_languages": len(langs_only),
        "label_families": len(fams), "label_family_names": "；".join(fams),
        "label_branches_l2": len(brs), "label_pseudo_entries": pseudo_n,
        "pilot_glottocodes": len(manual_codes.get(c, ())),
        "pilot_not_in_label": "；".join(sorted(manual_codes.get(c, set()) - {d["glottocode"] for d in ds})),
        # —— T18 新增 ——
        "domestic_varieties": domestic_rows[c],
        "domestic_unaligned": unaligned_rows[c],
        "aligned_languages": len(al),
        "aligned_by_name": sum(1 for g in al if g in by_name[c] or g in unbased[c]),
        "aligned_by_label_only": sum(1 for g in al if g not in by_name[c] | unbased[c] | by_alias[c]),
        "aligned_families": len(al_fams), "aligned_family_names": "；".join(al_fams),
        "name_aligned_families": len(name_fams), "name_aligned_family_names": "；".join(name_fams),
        "shared_with": "；".join(f"{o}{name_of[o]}（{'、'.join(gs)}）" for o, gs in sorted(shared.items())),
        "codes_not_in_table": "；".join(sorted(g for g in manual_codes[c] if g not in glot)),
        # —— T21 新增 ——
        "aligned_by_alias": sum(1 for g in al if g in by_alias[c] and g not in by_name[c] | unbased[c]),
        "shift_shared_with": "；".join(f"{o}{name_of[o]}（{'、'.join(gs)}）" for o, gs in sorted(shift.items())),
    })
(ROOT / "outputs").mkdir(exist_ok=True)
with open(ROOT / "outputs" / "indicators.csv", "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=list(out[0].keys())); w.writeheader(); w.writerows(out)

lab = [o for o in out if o["label_entries"]]
print("有标注的法定类别:", len(lab), "/ 56")
print("其中含 2 个以上语言级条目:", sum(o["label_languages"] >= 2 for o in lab))
print("其中跨 2 个以上语系:", sum(o["label_families"] >= 2 for o in lab), [o["name_zh"] for o in lab if o["label_families"] >= 2])
print("人工表中不在中国条目表里的 Glottocode:", bad)
print("—— 人工映射 ∪ 标注（56 类）——")
print("国内口径行数 ≥2 的类:", sum(o["domestic_varieties"] >= 2 for o in out))
print("已对齐语言级条目 ≥2 的类:", sum(o["aligned_languages"] >= 2 for o in out))
print("已对齐条目为 0 的类:", [o["name_zh"] for o in out if o["aligned_languages"] == 0])
x = [o for o in out if o["aligned_families"] >= 2]
print("已对齐条目跨 2 个以上语系:", len(x))
for o in x:
    print("  ", o["legal_code"], o["name_zh"], o["aligned_family_names"], "｜有国内依据（名称/别名/试点）:", o["name_aligned_family_names"] or "—")
pairs = sorted({tuple(sorted((c, o))) for c, gs in aligned.items() for g in gs - shift_only[c] for o in owners[g] - {c}})
print("共用条目的类别对（不含语言转用）:", len(pairs))
for a, b in pairs:
    print("  ", a + name_of[a], "—", b + name_of[b], "：", "、".join(sorted(aligned[a] & aligned[b])))
spairs = sorted({(c, o) for c in aligned for g in shift_only[c] for o in owners[g] - {c}})
print("语言转用（另列，不计共用）:", len(spairs))
for a, b in spairs:
    print("  ", a + name_of[a], "用", b + name_of[b], "的", "、".join(sorted(shift_only[a] & aligned[b])))
print("align_basis 取值:", dict(collections.Counter((r.get("align_basis") or "（试点行，空）") for r in manual)))
