"""T20 “划分的收益”建模试点：方言区对省际迁移的解释力（V-08）。

一条命令重算：  python scripts/t20_gravity.py
依赖：pandas、numpy、statsmodels（pip install -r requirements.txt）
输入：
  data/raw/census2020_migration_5yr.csv   长表 7-7 转录（行=现住地，列=五年前常住地）
  data/raw/capital_coords.csv             省会坐标（GeoNames）
  data/partitions/province_dialect.csv    各省主导方言区
  data/partitions/province_adjacency.csv  陆地相邻（含广东—海南，隔海）
  data/partitions/province_econ_region.csv 统计局四大区域
输出：
  outputs/t20_results.csv（每模型一行）
计划见 docs/t20_plan.md；与计划的偏离写在 docs/t20_report.md。
"""
from pathlib import Path
import math
import warnings

import numpy as np
import pandas as pd
import statsmodels.api as sm

warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]
SEED = 20201101  # 计划要求固定种子；留一划分本身是确定的，此处只为可复现记录
np.random.seed(SEED)


def load():
    mig = pd.read_csv(ROOT / "data/raw/census2020_migration_5yr.csv", encoding="utf-8")
    provs = list(mig["现住地"])
    assert len(provs) == 31
    coords = pd.read_csv(ROOT / "data/raw/capital_coords.csv").set_index("province")
    dia = pd.read_csv(ROOT / "data/partitions/province_dialect.csv", keep_default_na=False).set_index("province")
    adj = pd.read_csv(ROOT / "data/partitions/province_adjacency.csv")
    adjset = {frozenset(p) for p in adj[["a", "b"]].itertuples(index=False)}
    econ = pd.read_csv(ROOT / "data/partitions/province_econ_region.csv").set_index("province")["econ_region"]

    rows = []
    for _, r in mig.iterrows():
        dest = r["现住地"]
        for orig in provs:
            if orig == dest:
                continue
            flow = int(r[orig])
            la1, lo1 = coords.loc[orig, ["lat", "lon"]]
            la2, lo2 = coords.loc[dest, ["lat", "lon"]]
            d = hav(la1, lo1, la2, lo2)
            g1, g2 = dia.loc[orig, "dialect_group"], dia.loc[dest, "dialect_group"]
            rows.append(dict(
                orig=orig, dest=dest, flow=flow, logdist=math.log(d),
                adjacent=int(frozenset((orig, dest)) in adjset),
                same_econ=int(econ[orig] == econ[dest]),
                same_dialect=int(g1 != "" and g1 == g2),
                same_mandarin_status=int(g1 != "" and g2 != "" and ((g1 == "官话") == (g2 == "官话"))),
                mixed_any=int(dia.loc[orig, "mixed"] == "是" or dia.loc[dest, "mixed"] == "是"),
            ))
    df = pd.DataFrame(rows)
    assert len(df) == 930
    return df


def hav(la1, lo1, la2, lo2, R=6371.0):
    p1, p2 = math.radians(la1), math.radians(la2)
    dp, dl = p2 - p1, math.radians(lo2 - lo1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * R * math.asin(math.sqrt(a))


def design(df, extra):
    X = pd.get_dummies(df[["orig", "dest"]], drop_first=True, dtype=float)
    X = pd.concat([X, df[["logdist"] + extra].astype(float)], axis=1)
    return sm.add_constant(X)


def fit(df, extra):
    m = sm.GLM(df["flow"].astype(float), design(df, extra), family=sm.families.Poisson())
    return m.fit(cov_type="HC1", maxiter=200)


def poisson_dev(y, mu):
    y = np.asarray(y, float); mu = np.asarray(mu, float)
    t = np.where(y > 0, y * np.log(np.where(y > 0, y, 1) / mu), 0.0)
    return float(2 * np.sum(t - (y - mu)))


def loo_origin(df, extra):
    """留一迁出省：去掉迁出省 i 的全部省对拟合，再预测 i 的省对。
    i 的迁出固定效应无法从其余样本估出，按 PPML 一阶条件取值，使 i 的预测迁出总量等于实际总量；
    因此样本外离差衡量的是模型把 i 的迁出量分配到各迁入省的准确度。"""
    total = 0.0
    for o in sorted(df["orig"].unique()):
        tr, te = df[df["orig"] != o], df[df["orig"] == o]
        res = fit(tr, extra)
        Xte = design(df, extra).loc[te.index, res.params.index]
        eta = Xte.values @ res.params.values  # 迁出省 o 的哑变量列不在训练参数中，相当于取 0
        mu = np.exp(eta)
        mu *= te["flow"].sum() / mu.sum()
        total += poisson_dev(te["flow"], mu)
    return total


MODELS = [
    ("M0", [], None),
    ("M1", ["adjacent"], "adjacent"),
    ("M2", ["same_econ"], "same_econ"),
    ("M3", ["same_dialect"], "same_dialect"),
    ("M4", ["same_mandarin_status"], "same_mandarin_status"),
    ("M5", ["adjacent", "same_econ", "same_dialect"], "same_dialect"),
]


def run(df, label, models, base_dev=None):
    out = []
    if base_dev is None:
        r0 = fit(df, [])
        base_dev = (r0.deviance, loo_origin(df, []))
    for name, extra, key in models:
        r = fit(df, extra)
        oos = loo_origin(df, extra)
        row = dict(sample=label, model=name, n_pairs=len(df), n_provinces=df["orig"].nunique(),
                   regressors="logdist" + "".join("+" + e for e in extra),
                   key_var=key or "", coef=np.nan, robust_se=np.nan, z=np.nan,
                   logdist_coef=r.params["logdist"],
                   deviance=r.deviance, m0_deviance=base_dev[0],
                   deviance_reduction_pct=100 * (base_dev[0] - r.deviance) / base_dev[0],
                   loo_oos_deviance=oos, m0_loo_oos_deviance=base_dev[1],
                   loo_oos_reduction_pct=100 * (base_dev[1] - oos) / base_dev[1])
        if key:
            row.update(coef=r.params[key], robust_se=r.bse[key], z=r.tvalues[key])
        out.append(row)
        if extra == ["adjacent", "same_econ", "same_dialect"]:
            for k in ("adjacent", "same_econ"):
                row[f"{k}_coef_in_M5"] = r.params[k]
    return out


def main():
    df = load()
    res = run(df, "全样本", MODELS)
    # 稳健性 1：去掉 mixed=是 的省份（作迁出或迁入均去掉），重估 M3、M5
    keep = load_unmixed(df)
    res += run(keep, "去掉mixed=是的省份", [m for m in MODELS if m[0] in ("M0", "M3", "M5")])
    # 稳健性 2：去掉北京、上海、广东作为迁入地的省对，重估 M5
    sub = df[~df["dest"].isin(["北京", "上海", "广东"])].copy()
    res += run(sub, "去掉迁入地京沪粤", [m for m in MODELS if m[0] in ("M0", "M5")])
    out = pd.DataFrame(res)
    (ROOT / "outputs").mkdir(exist_ok=True)
    out.to_csv(ROOT / "outputs/t20_results.csv", index=False, float_format="%.6g", encoding="utf-8")
    pd.set_option("display.width", 250)
    print(out[["sample", "model", "n_pairs", "key_var", "coef", "robust_se", "deviance_reduction_pct", "loo_oos_reduction_pct"]].to_string(index=False))


def load_unmixed(df):
    dia = pd.read_csv(ROOT / "data/partitions/province_dialect.csv", keep_default_na=False)
    mixed = set(dia.loc[dia["mixed"] == "是", "province"])
    return df[~df["orig"].isin(mixed) & ~df["dest"].isin(mixed)].copy()


if __name__ == "__main__":
    main()
