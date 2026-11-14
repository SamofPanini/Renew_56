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
| `data/mapping_legal_language.csv` | 人工映射，56 个法定类别 × 语言变体：试点 11 类（T13）加 T18 的 45 类。含国内口径与 Glottolog 口径是否一致、对齐依据、国内页面地址 | 试点行来自 Notion 的 X- 行；T18 行由 `scripts/build_t18_rows.py` 生成 |
| `data/aliases/legal_language_alias.csv` | 国内语言名—Glottolog 别名对照表（T21）：`row_id`、`domestic_name`、`glottocode`、`alias_basis`、`source_url`、`evidence_grade`、`note`。只覆盖 T18 中 `align_basis=none` 的行与 X-41-01 | 维基中文页（2026-11-14 抓取，原句摘在 `note`）与 `glottolog_cn.csv` 的 `names_cjk` |
| `data/partitions/han_partitions.csv` | 汉语方言人群在不同制度与学术口径下的分类表（14 行；`n_listed` 解析不出的留空；`status` 为 Notion“状态”原值） | Notion 论断库 HX- 行（T14，复检通过），T19 导出 |
| `data/events/gaitu_guiliu.csv`、`data/events/context_series.csv` | 改土归流事件表（20 行）与背景序列（5 行）；`trigger` 只记来源明说的触发因素；`status` 为 Notion“状态”原值（2026-11-14 读取，T21 补列；“待核”行下游使用时须回查） | Notion 论断库 G- 行（T16，抽检通过），T19 导出 |
| `scripts/build_glottolog_cn.py` | 生成上面两张脚本表 | |
| `scripts/t18_domestic_spec.py` | T18 国内口径规格表：45 类逐行的名称、两类官方页面的原文片段、互通性说法 | 人工摘录，读取日期 2026-11-14 |
| `scripts/build_t18_rows.py` | 按规格表与中国条目表生成 45 类的映射行 | |
| `scripts/build_t19_counts.py` | 输出口径类别数与事件按年代×触发因素的计数表（`outputs/partitions_counts.csv`、`outputs/events_counts.csv`） | |
| `scripts/build_indicators.py` | 计算错位指标（同时读标注派生映射与人工映射） | |
| `outputs/indicators.csv` | 每个法定类别的指标 | 由脚本生成 |

## 重算

```
git clone --depth 1 --filter=blob:none --sparse https://github.com/glottolog/glottolog-cldf
git -C glottolog-cldf sparse-checkout set cldf
python3 scripts/build_glottolog_cn.py glottolog-cldf/cldf
python3 scripts/build_t18_rows.py        # 需要 pip install opencc-python-reimplemented（繁转简）
python3 scripts/build_indicators.py
```

当前数据取自 glottolog-cldf 标签 v5.4（提交 84977fc，2026-11-10）。

## 读表时必须知道的限制

1. **民族标注覆盖不全**。473 条条目中只有 141 条带可对应到 56 类的标注，覆盖 23 个法定类别；其余 33 类没有标注，不代表它们没有对应语言。
2. **标注是转引**。它是 Glottolog 濒危注释里引用的 Ethnologue 说法，不是 Glottolog 自己的判断，也不是中国官方口径。项目内证据等级暂记 D，待抽检裁定。
3. **标注可能有错**。例如 Chadong（chad1240，侗台语，表内坐标在广西桂林一带）在原数据中标为 “Hani”，指标中由此出现的“哈尼族跨语系”不可直接采信。T18 用 1 次检索核对（2026-11-14）：检索摘录称茶洞语通行于广西桂林临桂茶洞一带，说话人在官方分类中归汉族（英文维基百科条目的说法，原页未打开，也未见中国官方来源，证据等级 E）；没有任何摘录把它与哈尼族联系起来。“Hani” 是否为 “Han” 的笔误属推测，未证实；本仓库不改动原标注，只在此注明。
4. **国家字段沿用 Glottolog 的编码**。台湾的南岛语条目在 Glottolog 中标为 `CN;TW`，因此出现在本表中；这只是数据来源的编码方式。
5. **伪语系不计入跨语系**。Bookkeeping、Sign Language、Pidgin 等不参与语系计数。
6. **试点映射（11 类）全部为 E 级**，细节与来源见 Notion 对应行；`nort3249`、`sout3221` 是 Glottolog 的簿记条目，不在中国条目表内。

## 人工映射的列与规则（T18）

`mapping_legal_language.csv` 的列：`row_id`（X-代码-序号；跨类共用行为 XS-序号）、`legal_code`、`variety_label`、`glottocodes`、`consistency`、`intelligibility_note`、`evidence_grade`，以及 T18 新增的 `domestic_source_url`、`align_basis`、`note`（试点行这三列留空）。

- **国内口径**每类读两页：国家民委该族“概况”页（neac.gov.cn）与国家语言资源监测与研究民族语言中心该族页面（nmlr.muc.edu.cn）。两页说法不一致时并存，不调和。汉族没有 nmlr 页；柯尔克孜族、达斡尔族的 neac 概况页正文没有写语言。
- **对齐依据**有四种：`name`（国内名称与条目表的 `names_cjk` 或 `name` 直接一致，只做繁体转简体的字形归一）、`label`（条目的 `legal_code_from_label` 等于本类代码）、`alias`（T21 别名表补上的对应，见下节）、`none`（未对应）。不按拼写相近、地理相邻或谱系相近对齐。
- **按名称对齐是字面对齐，不是语言学判定**。例如“塔吉克语”按名称曾对到 Glottolog 的 Tajik（taji1245），而国内页面说的两种方言是色勒库尔语与瓦罕语（同名异指，T21 起由别名表剔除）；“蒙古语”“苗语”“白语”“侗语”等在表内没有同名条目，T18 标为未对应，T21 用别名表补上了其中有来源的部分。未对应的多少首先反映两套名称体系的差别。
- **“汉语”不对齐**。回族、满族、锡伯族、瑶族、裕固族等行里的“汉语”在表内没有同名条目，标为未对应；汉族一行只记表内汉语支语言级条目数（29），不逐条对齐。
- **证据等级**：页面已打开并读到原句的行记 B（原文片段写在规格表里，可用 `build_t18_rows.py --pages` 对已下载的页面核对）；仅据标注的行记 D。
- **高山族**只记国内页面的表述与表内 `countries` 含 TW 的南岛语语言级条目数（22），不逐条对齐。

## 别名对照表（T21）

`data/aliases/legal_language_alias.csv` 一行 = 某个映射行（`row_id`）里的一个国内名称对到一个 Glottolog 条目。`build_t18_rows.py` 读这张表，把对应补进该行，`align_basis` 改为 `alias`。

- `alias_basis` 三种：`glottolog_cjk`（`glottolog_cn.csv` 的 `names_cjk` 含该国内名称，或仅差“语／话”后缀、仅多方位词，不抓取）；`iso_name`（Glottolog 或 ISO 639-3 页写出与国内名称对应的地名、方言名；本轮未用）；`source_states`（来源有一句话同时写出国内名称与该条目，原句已读，摘在 `note`）。
- 本轮 `source_states` 全部来自维基中文页，且都是**经 ISO 639-3 代码搭桥**：页面写“国内名称—代码”（如“doc – 北侗语”），代码在 `glottolog_cn.csv` 中唯一对应一个条目。证据等级一律 D。
- `note` 以“【不采用”开头的行表示同名异指或所指不同：不加入映射；若该条目原本按名称对到，则从该行剔除（taji1245 即此例）。
- 仍未对应的：`汉语` 各行（按既定规则不对齐）；阿拉伯语／波斯语（表内无条目）；巴那语（来源给出 Glottolog pana1310，但不在 `glottolog_cn.csv`）；载瓦语（本轮唯一一次抓取被环境拦截，未取得来源）；蒙古语的卫拉特、巴尔虎布利亚特方言（来源只写 mvf“部分”）；“怒语”合称；按设计不对齐的四行（X-03-05、X-06-03、X-22-01、X-23-01）。
- 限制：维基是后出转述，代码与名称的对应可能有误；Ethnologue／ISO 的语言切分本身与国内“方言”口径不同（如苗语三大方言对到 26 个条目），“国内合并而 Glottolog 分列”的条目数主要反映 ISO 的切分粒度。

## 56 类指标（人工映射 ∪ 标注，T18；T21 更新）

T21 别名表加入后（括号内为 T18 值）：已对齐语言级条目 2 个以上 28 类（23）；已对齐条目为 0 的 3 类：高山、土、基诺（7 类）；跨 2 个以上语系 7 类（5），新增蒙古族（卡卓语属汉藏语）、瑶族（拉珈语、布央语属侗台语，均有国内页面依据）；共用条目的类别对 3 对（不含语言转用）：怒族—独龙族、藏族—普米族（普米语，XS-02）、苗族—瑶族（金门方言 kimm1245：来源称海南说金门方言的人被识别为苗族）；语言转用另列 2 对（塔塔尔族用维吾尔语、哈萨克语），按 T11 裁决⑩不计为共用，见 `shift_shared_with` 列。新增列 `aligned_by_alias`；`name_aligned_*` 两列自 T21 起含别名对齐（即“有国内依据的对齐”）。下面是 T18 时的原记录。

`outputs/indicators.csv` 在原有 10 列之后新增：`domestic_varieties`（有国内依据的行数）、`domestic_unaligned`、`aligned_languages`（已对齐的表内语言级条目数，不计伪语系）、`aligned_by_name`、`aligned_by_label_only`、`aligned_families` 与名称、`name_aligned_families` 与名称（只看按名称或试点人工对齐的条目）、`shared_with`、`codes_not_in_table`。

- 国内口径行数 2 行以上：21 类；已对齐语言级条目 2 个以上：23 类；已对齐条目为 0：7 类（高山、土、普米、乌孜别克、德昂、京、基诺）。
- 已对齐条目跨 2 个以上语系：5 类。回族（回辉话属南岛语、康家语属蒙古语族）、裕固族（西部裕固语属突厥语、东部裕固语属蒙古语族）两类有国内页面依据；汉族、苗族、哈尼族三类只来自标注，其中哈尼族一例存疑（限制 3）。
- 共用条目的类别对：3 对。怒族—独龙族（独龙语，国内页面明述）；维吾尔族—塔塔尔族、哈萨克族—塔塔尔族（国家民委称维吾尔语、哈萨克语已成为塔塔尔族通用的语言文字）。另有两处国内页面明述、但表内没有同名条目的共用：壮族—布依族（XS-01）、藏族—普米族（XS-02）。
- 国内页面按语族或语支写明内部跨类、但按名称对不上的，指标里看不出来，须读 `note`：瑶族（瑶语支、苗语支、侗水语支、汉语方言四个支系）、景颇族（景颇语支与缅语支）、畲族（两页对“畲语”所指不一）、怒族（三种“怒语”互不能通话）。

## 首轮指标（仅基于标注派生映射）

- 有标注的法定类别：23 / 56
- 其中对应 2 个以上语言级条目：15 类（彝 30、苗 25、壮 16、汉 15、藏 9、瑶 7、哈尼 7 等）
- 标注显示跨语系：汉族（汉藏语与 2 条侗台语）、苗族（苗瑶语与 1 条侗台语）；哈尼族一例存疑，见限制 3

## 许可与署名

Glottolog 数据以 CC BY 4.0 发布，引用时请注明：Hammarström, Forkel, Haspelmath & Bank, *Glottolog*（所用版本见上）。本仓库的脚本与派生表格沿用同一署名要求。
