#!/usr/bin/env python3
"""T18：把人工映射从试点 11 类扩到 56 类（新增 45 类的行）。

用法:
  python3 scripts/build_t18_rows.py            # 重建 45 类的行，保留试点行不动
  python3 scripts/build_t18_rows.py --pages D  # 另外核对规格表里的原文片段确在已下载的页面中
                                               # （D 下文件名: neac_<缩写>.shtml、nmlr_<编号>.htm）

对齐只用三种依据（align_basis）：
  name   国内名称与 glottolog_cn.csv 的 names_cjk 或 name 列直接一致
         （仅做繁体转简体的字形归一；需要 opencc-python-reimplemented，缺失时只做原样比对）
  label  条目的 legal_code_from_label 等于本类代码
  none   未能对应
不按拼写相近、地理相邻或谱系相近对齐。
"""
import csv, html, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import t18_domestic_spec as spec

try:
    from opencc import OpenCC
    t2s = OpenCC("t2s").convert
except Exception:  # 没装 opencc 时退化为原样比对
    t2s = lambda s: s

PILOT = {"04", "07", "08", "09", "16", "18", "20", "24", "54", "55", "56"}
PSEUDO = {"Bookkeeping", "Unclassifiable", "Unattested", "Sign Language", "Mixed Language", "Pidgin",
          "Speech Register", "Artificial Language", "(isolate/unclassified)"}
NEAC = {"01": "hz", "02": "mgz", "03": "huiz", "04": "zz", "05": "wwez", "06": "mz", "07": "yz", "08": "zhz",
        "09": "byz", "10": "cxz", "11": "manz", "12": "dz", "13": "yaoz", "14": "bz", "15": "tjz", "16": "hnz",
        "17": "hskz", "18": "daiz", "19": "lz", "20": "ssz", "21": "wz", "22": "sz", "23": "gsz", "24": "lhz",
        "25": "shuiz", "26": "dxz", "27": "nxz", "28": "jpz", "29": "kekzz", "30": "tz", "31": "dwz", "32": "mlz",
        "33": "qz", "34": "blz", "35": "slz", "36": "mnz", "37": "glz", "38": "xbz", "39": "acz", "40": "pmz",
        "41": "tjkz", "42": "nz", "43": "wzbkz", "44": "elsz", "45": "ewkz", "46": "daz", "47": "baz",
        "48": "ygz", "49": "jz", "50": "ttez", "51": "dlz", "52": "elcz", "53": "hzz", "54": "mbz", "55": "lbz",
        "56": "jnz"}
neac_url = lambda c: f"https://www.neac.gov.cn/seac/ztzl/{NEAC[c]}/gk.shtml"
nmlr_id = lambda c: 2132 + 10 * (int(c) - 2)          # 蒙古族 2132 … 基诺族 2672；汉族无页
nmlr_url = lambda c: f"https://nmlr.muc.edu.cn/info/1119/{nmlr_id(c)}.htm"

rd = lambda p: list(csv.DictReader(open(ROOT / p, encoding="utf-8")))
glot = rd("data/glottolog_cn.csv")
G = {g["glottocode"]: g for g in glot}
legal = rd("data/legal_categories.csv")

# 名称索引：names_cjk 各项（原样与繁转简）＋ name 列
idx = {}
for g in glot:
    for n in filter(None, g["names_cjk"].split("；")):
        for k in {n, t2s(n)}:
            idx.setdefault(k, {}).setdefault(g["glottocode"], n)
    idx.setdefault(g["name"], {}).setdefault(g["glottocode"], g["name"])


def page_text(p):
    t = open(p, encoding="utf-8", errors="replace").read()
    t = re.sub(r"<script.*?</script>|<style.*?</style>", "", t, flags=re.S)
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", t)))


def verify(pages):
    bad = 0
    for c, rows in spec.R.items():
        tn = page_text(Path(pages) / f"neac_{NEAC[c]}.shtml")
        tm = page_text(Path(pages) / f"nmlr_{nmlr_id(c)}.htm") if c != "01" else ""
        for r in rows:
            for src, txt in (("neac", tn), ("nmlr", tm)):
                for frag in r[src]:
                    if re.sub(r"\s+", "", frag) not in txt:
                        bad += 1
                        print("页面中未找到片段:", c, src, frag)
    print("原文片段核对完成，未找到", bad, "处")


def lang_level(gc):
    return G[gc]["level"] == "language" and G[gc]["family"] not in PSEUDO


out = []
for L in legal:
    c = L["code"]
    if c in PILOT:
        continue
    seq = 0
    used = set()
    for r in spec.R[c]:
        seq += 1
        hits, how = [], []
        for n in r["names"]:
            for gc, orig in sorted(idx.get(n, {}).items()):
                if gc not in hits:
                    hits.append(gc)
                    lab = G[gc]["legal_code_from_label"]
                    tag = f"{n}={gc}（{G[gc]['name']}"
                    if orig != n:
                        tag += f"，表内写作{orig}"
                    if G[gc]["level"] != "language":
                        tag += f"，{G[gc]['level']}级"
                    if lab == c:
                        tag += "，同带本类标注"
                    elif lab:
                        tag += f"，标注为{lab}"
                    how.append(tag + "）")
        used.update(hits)
        n_lang = sum(lang_level(g) for g in hits)
        if not r["names"]:
            cons, basis = "不对齐（见备注）", "none"
        elif not hits:
            cons, basis = "未对应（表内无同名条目）", "none"
        elif n_lang == 1 and len(hits) == 1:
            cons, basis = "一致（按名称对到1条）", "name"
        elif n_lang == 0:
            cons, basis = "按名称对到非语言级节点", "name"
        else:
            cons, basis = f"国内合并而Glottolog分列（按名称对到{len(hits)}条）", "name"
        note = r["note"]
        if c == "01" and seq == 1:
            n_sin = sum(1 for g in glot if "Sinitic" in g["classification_path"] and g["level"] == "language")
            note += f"。表中 classification_path 含 Sinitic 的语言级条目共 {n_sin} 条（仅计数，不逐条对齐）"
        if c == "23":
            n_tw = sum(1 for g in glot if "TW" in g["countries"].split(";") and g["family"] == "Austronesian"
                       and g["level"] == "language")
            note += f"。表中 countries 含 TW 的南岛语语言级条目共 {n_tw} 条（来源编码为 CN;TW，仅计数）"
        if how:
            note += ("。" if note else "") + "名称对齐：" + "；".join(how)
        urls = ([neac_url(c)] if r["neac"] else []) + ([nmlr_url(c)] if r["nmlr"] else [])
        out.append(dict(row_id=f"X-{c}-{seq:02d}", legal_code=c, variety_label=r["label"],
                        glottocodes=";".join(hits), consistency=cons, intelligibility_note=r["intel"],
                        evidence_grade="B", domestic_source_url=";".join(urls), align_basis=basis, note=note))
    # 仅据标注的条目：按语系分行
    by_fam = {}
    for g in glot:
        if g["legal_code_from_label"] == c and g["glottocode"] not in used:
            by_fam.setdefault(g["family"], []).append(g["glottocode"])
    for fam in sorted(by_fam, key=lambda f: (-len(by_fam[f]), f)):
        seq += 1
        gcs = sorted(by_fam[fam])
        out.append(dict(row_id=f"X-{c}-{seq:02d}", legal_code=c,
                        variety_label=f"Glottolog 标注为本类的其他条目（{fam}，{len(gcs)}条）",
                        glottocodes=";".join(gcs), consistency="仅一方有（仅据标注）",
                        intelligibility_note="来源未述", evidence_grade="D", domestic_source_url="",
                        align_basis="label",
                        note="仅据标注：Glottolog 濒危注释转引 Ethnologue 的 recognized nationality；国内两页未以同名列出"))

# 跨类共用行（来源明述）
out.append(dict(row_id="XS-02", legal_code="04;40", variety_label="普米语（普米族与四川木里、盐源部分地区的藏族共用）",
                glottocodes="", consistency="国家民委普米族概况页明述藏族使用普米语；nmlr藏族页亦列普米语",
                intelligibility_note="来源明述", evidence_grade="B",
                domestic_source_url=neac_url("40") + ";" + nmlr_url("04"), align_basis="none",
                note="neac普米族页：“还有一种是藏族使用普米语，主要是四川木里、盐源县的部分地区”。表内无名为“普米语”的条目，未对应"))
out.append(dict(row_id="XS-03", legal_code="42;51", variety_label="独龙语／贡山怒语（怒族与独龙族共用近同变体）",
                glottocodes=";".join(sorted(idx.get("独龙语", {}))),
                consistency="国家民委怒族概况页明述“基本可以通话”；nmlr怒族页把独龙语列为怒族使用的语言",
                intelligibility_note="来源明述", evidence_grade="B",
                domestic_source_url=neac_url("42") + ";" + nmlr_url("42"), align_basis="name",
                note="neac怒族页：“贡山怒语与独龙语却比较接近，基本可以通话”。名称对齐：独龙语"))

cols = ["row_id", "legal_code", "variety_label", "glottocodes", "consistency", "intelligibility_note",
        "evidence_grade", "domestic_source_url", "align_basis", "note"]
path = ROOT / "data" / "mapping_legal_language.csv"
old = [r for r in rd("data/mapping_legal_language.csv")
       if set(r["legal_code"].split(";")) <= PILOT and r["row_id"] not in {o["row_id"] for o in out}]
with open(path, "w", encoding="utf-8", newline="") as f:
    w = csv.DictWriter(f, fieldnames=cols, lineterminator="\n")
    w.writeheader()
    for r in old + out:
        w.writerow({k: r.get(k, "") or "" for k in cols})

import collections
print("试点行保留", len(old), "；新增行", len(out), "；覆盖类数", len({o["legal_code"] for o in out if ";" not in o["legal_code"]}))
print("align_basis:", dict(collections.Counter(o["align_basis"] for o in out)))
if "--pages" in sys.argv:
    verify(sys.argv[sys.argv.index("--pages") + 1])
