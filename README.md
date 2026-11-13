# Renew_56｜民族分类研究项目：错位数据集

本仓库是“民族分类研究项目”的数据与脚本部分。项目控制台在 Notion，本仓库只放可重算的表格、脚本和指标。

## 范围声明

这里做的是**描述性的错位测量**：同一批人群按“法定民族类别”和按“语言变体”等不同标准切分之后，结果相差多远。
本仓库不提出任何合并、拆分或调整法定民族的建议，也不产出“新的民族名单”。表中的对应关系是研究记录，不是族属判定。

## 目录

| 路径 | 内容 | 来源 |
| --- | --- | --- |
| `data/legal_categories.csv` | 56 个法定类别、国标两位代码、罗马字母拼写、标注别名 | 项目存档附表（GB/T 3304 拼写未逐项对照国标原件） |
| `data/glottolog_cn.csv` | Glottolog 中国家字段含 CN 的全部条目：分类路径、坐标、濒危等级、民族标注、汉字名称 | glottolog-cldf，由脚本生成 |
| `data/mapping_label_derived.csv` | 法定类别 × Glottolog 条目，依据是 Glottolog 濒危注释中所引 Ethnologue 的“recognized nationality”标注 | 由脚本生成 |
| `data/mapping_legal_language.csv` | 试点（T13）人工映射：11 个法定类别 × 语言变体，含国内口径与 Glottolog 口径是否一致 | Notion“论断与关系边”库的 X- 行精简版 |
| `data/partitions/` | 预留：不同制度与学术口径下的分类表（T14 产出） | 待填 |
| `scripts/build_glottolog_cn.py` | 生成上面两张脚本表 | |
| `scripts/build_indicators.py` | 计算错位指标 | |
| `outputs/indicators.csv` | 每个法定类别的指标 | 由脚本生成 |

## 重算

```
git clone --depth 1 --filter=blob:none --sparse https://github.com/glottolog/glottolog-cldf
git -C glottolog-cldf sparse-checkout set cldf
python3 scripts/build_glottolog_cn.py glottolog-cldf/cldf
python3 scripts/build_indicators.py
```

当前数据取自 glottolog-cldf 标签 v5.4（提交 84977fc，2026-11-10）。

## 读表时必须知道的限制

1. **民族标注覆盖不全**。473 条条目中只有 141 条带可对应到 56 类的标注，覆盖 23 个法定类别；其余 33 类没有标注，不代表它们没有对应语言。
2. **标注是转引**。它是 Glottolog 濒危注释里引用的 Ethnologue 说法，不是 Glottolog 自己的判断，也不是中国官方口径。项目内证据等级暂记 D，待抽检裁定。
3. **标注可能有错**。例如 Chadong（chad1240，侗台语）在原数据中标为 “Hani”，需人工核对，指标中由此出现的“哈尼族跨语系”不可直接采信。
4. **国家字段沿用 Glottolog 的编码**。台湾的南岛语条目在 Glottolog 中标为 `CN;TW`，因此出现在本表中；这只是数据来源的编码方式。
5. **伪语系不计入跨语系**。Bookkeeping、Sign Language、Pidgin 等不参与语系计数。
6. **试点映射全部为 E 级**，细节与来源见 Notion 对应行；`nort3249`、`sout3221` 是 Glottolog 的簿记条目，不在中国条目表内。

## 首轮指标（仅基于标注派生映射）

- 有标注的法定类别：23 / 56
- 其中对应 2 个以上语言级条目：15 类（彝 30、苗 25、壮 16、汉 15、藏 9、瑶 7、哈尼 7 等）
- 标注显示跨语系：汉族（汉藏语与 2 条侗台语）、苗族（苗瑶语与 1 条侗台语）；哈尼族一例存疑，见限制 3

## 许可与署名

Glottolog 数据以 CC BY 4.0 发布，引用时请注明：Hammarström, Forkel, Haspelmath & Bank, *Glottolog*（所用版本见上）。本仓库的脚本与派生表格沿用同一署名要求。
