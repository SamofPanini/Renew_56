"""T22 V-08 对照：用 2010 年普查五年迁移表（2005→2010）复跑 T20 引力模型。

一条命令重算：  python scripts/t22_gravity_2010.py
依赖：同 t20_gravity.py（pandas、numpy、statsmodels）
输入：
  data/raw/census2010_migration_5yr.csv   2010 年鉴长表 7-8（行=现住地，列=五年前常住地）
  其余（坐标、方言、相邻、经济大区）与 T20 共用同一批文件，不改动
  outputs/t20_results.csv                 T20 结果，用于并排对照
输出：
  outputs/t22_results.csv   列同 t20_results.csv，另加 year
  outputs/t22_vs_t20.csv    每个样本×模型：两年的系数、SE、离差下降比例并排
模型、样本、稳健性全部来自 t20_gravity.run_all，唯一变化是迁移年份。计划见 docs/t22_plan.md。
"""
from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent))
import t20_gravity as t20  # noqa: E402

ROOT = t20.ROOT
MIG_2010 = ROOT / "data/raw/census2010_migration_5yr.csv"


def main():
    out = t20.run_all(t20.load(MIG_2010))
    out.insert(0, "year", 2010)
    out.to_csv(ROOT / "outputs/t22_results.csv", index=False, float_format="%.6g", encoding="utf-8")

    prev = pd.read_csv(ROOT / "outputs/t20_results.csv", encoding="utf-8")
    keys = ["sample", "model"]
    cols = ["key_var", "coef", "robust_se", "deviance_reduction_pct", "loo_oos_reduction_pct", "n_pairs"]
    a = out[keys + cols].rename(columns={c: f"{c}_2010" for c in cols})
    b = prev[keys + cols].rename(columns={c: f"{c}_2020" for c in cols})
    cmp = a.merge(b, on=keys, how="outer", validate="one_to_one")
    assert (cmp["key_var_2010"].fillna("") == cmp["key_var_2020"].fillna("")).all()
    cmp = cmp.rename(columns={"key_var_2010": "key_var"}).drop(columns="key_var_2020")
    cmp["same_sign"] = [
        "" if pd.isna(x) or pd.isna(y) else ("是" if (x > 0) == (y > 0) else "否")
        for x, y in zip(cmp["coef_2010"], cmp["coef_2020"])
    ]
    order = keys + ["key_var", "n_pairs_2010", "n_pairs_2020",
                    "coef_2010", "robust_se_2010", "coef_2020", "robust_se_2020", "same_sign",
                    "deviance_reduction_pct_2010", "deviance_reduction_pct_2020",
                    "loo_oos_reduction_pct_2010", "loo_oos_reduction_pct_2020"]
    cmp = cmp[order]
    cmp.to_csv(ROOT / "outputs/t22_vs_t20.csv", index=False, float_format="%.6g", encoding="utf-8")
    pd.set_option("display.width", 250)
    print(cmp.to_string(index=False))


if __name__ == "__main__":
    main()
