# data/raw 来源记录（T20）

## 状态：数据闸门通过（2026-11-14，续接会话改用 curl 经代理抓取，用户授权）

### 需要的文件（未取得）

| 项 | 期望路径 | 说明 |
| --- | --- | --- |
| 1 省际迁移矩阵（必需） | `data/raw/census2020_migration_5yr.xls`（或 .xlsx/.csv，原样保存） | 《中国人口普查年鉴-2020》“全国按现住地和五年前常住地分的人口”省对省表（31×31）。年鉴目录：https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/indexch.htm 。2020 年鉴中的表号本会话未能打开核实（2000 年鉴同类表为表7-4，仅供定位，不代表 2020 表号）。能顺带下载 2010 年同类表请存为 `census2010_migration_5yr.xls`。 |
| 2 各省常住人口 | `data/raw/census2020_bulletin3_population.*` | 第七次全国人口普查公报（第三号）。 |
| 2 省会坐标 | `data/raw/capital_coords.csv` | 任一公开坐标表，记来源网址。 |
| 3 方言归属 | `data/partitions/province_dialect.csv` | 自建，每省须有可打开的来源。 |

### 抓取尝试记录（卡上限 6 次，已用 4 次）

1. curl → www.stats.gov.cn 年鉴目录：会话代理 403（环境拦截，非链接失效）。
2. WebFetch → 同一地址：域名不在会话放行列表（环境拦截）。
   → 随后把会话切到 Renew_56 环境并在其放行列表加入 www.stats.gov.cn（用户审批通过）。
3. WebFetch → 同一地址：仍未解析（本机 WebFetch 沿用旧网络规则，需新会话/新容器才生效）。
4. WebFetch → 同一地址：同上。

另：放行后改用 curl（经代理）的请求被会话权限拦下，未发出，不计次。

### 第二个会话（续接，闸门重新计数，上限 6 次，已用 2 次）

会话开工时实际运行在 Default 环境（放行列表为空），不是 Renew_56。

1. WebFetch → https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/indexch.htm ：getaddrinfo ENOTFOUND（环境拦截，非链接失效）。
   → 随后用 switch_environment 把会话网络切到 Renew_56（放行 www.stats.gov.cn、www.neac.gov.cn、nmlr.muc.edu.cn）。
2. WebFetch → 同一地址：仍 ENOTFOUND。切换只改经代理的请求；WebFetch 在本机解析域名，沿用容器启动时（Default）的规则，需在 Renew_56 环境中新建容器才生效。

剩余 4 次未用：同一路径必然同样失败，再试只是消耗额度。查看代理状态的 curl 被会话权限拦下，未发出，不计次。
省会坐标、方言归属来源未尝试（同一原因，任何未放行域名都无法解析）。

### 续接会话·用户改授权用 curl 后（2026-11-14；用户同意上限由 6 次加到 12 次，共用 8 次）

3. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/indexch.htm ：200（框架页）。
4. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/left.htm ：200（年鉴表目录）。目标表在“第二部分 长表数据资料”第七卷，为 **7-7 全国按现住地和五年前常住地分的人口**（链接 zk/html/B0707.jpg）。
5. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/zk/html/B0707.jpg ：200，3048×1499 图片，原样存 `census2020_migration_5yr_table7-7.jpg`。
   - 转录：tesseract 3、4、5、6 倍放大逐格识别，多数投票；用行合计（合计 = 本县 + 本省其他 + 31 省 + 港澳台或国外）和列合计（全国行）定位不一致的格。3 格按投票候选修正，1 格（现住山西、五年前吉林 = 777）看原图确认。修正后 32 行、35 列合计全部闭合。另目视抽查 5 格，均一致。
   - 产出：`census2020_migration_5yr.csv`（31×35，行 = 现住地，列 = 五年前常住地，对角线留空）、`census2020_migration_5yr_national_row.csv`。
   - 注意：长表数据是抽样登记数。全国合计 131,271,202，不是全口径人数。2010 年同类表没有取。
6. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/zk/html/fu03c.pdf ：200，存为 `census2020_bulletin3_population.pdf`（第七次全国人口普查公报第三号，表 3-1 各地区人口）。模型含迁出、迁入固定效应，不直接使用这份公报。
7. curl → https://download.geonames.org/export/dump/cities15000.zip ：200（为此申请放行 download.geonames.org）。取 CN 国家代码、PPLC/PPLA 两类要素共 31 个点，正好对应 31 个省会，存为 `capital_coords.csv`。
8. curl → https://zh.wikipedia.org/zh-cn/汉语方言 （revision 95058314；为此申请放行 zh.wikipedia.org）：200。每省的方言归属依据都从该页摘了原句，写在 `data/partitions/province_dialect.csv` 的 note 列，并用脚本核对原句确在页面文本中（含省略号的摘句除外）。


---

# T22：2010 年普查五年迁移表（2026-11-24）

## 状态：数据闸门通过（上限 8 次，用 7 次）

会话开工时运行在 Default 环境（放行列表为空），经用户审批用 switch_environment 把网络切到 Renew_56 环境后改用 curl 经代理抓取。

1. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/6rp/left.htm ：代理 403（环境拦截，非链接失效）。→ 切换到 Renew_56 环境。
2. curl → 同一地址：200（《中国2010年人口普查资料》目录，GB2312）。目标表在“第二部分 长表数据资料”第七卷“迁移和户口登记地”，为 **7-8 全国按现住地和五年前常住地分的人口**（链接 html/B0708.htm）。
3. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/6rp/html/B0708.htm ：200，Excel 导出的 HTML 表格（文本，不是图片），原样存为 `census2010_migration_5yr_table7-8.htm`（sha256 8332bb2f…d573）。
   - 直接解析单元格，无需 OCR。产出 `census2010_migration_5yr.csv`（31 行，列 = 合计、省内、31 省、港澳台或国外；行 = 现住地，列 = 五年前常住地，对角线留空）与 `census2010_migration_5yr_national_row.csv`。
   - 校验：31 行的“合计 = 省内 + 31 省 + 港澳台或国外”全部闭合；35 列的各省合计等于全国行，全部闭合；全国行自身闭合。对角线外唯一空格为“现住西藏、五年前港澳台或国外”（不属于省对）。930 个省对均有数，最小 9。另用正则从原 HTML 重新取 5 格（种子 22：新疆←宁夏 1827、内蒙古←黑龙江 6516、北京←广西 2391、山东←辽宁 5397、四川←山西 1840），与 CSV 一致。
   - 与 2020 年表的格式差别：2010 年表“省内”只有一列，没有拆成“本县市区／本省其他县市区”；不影响省对流量。
   - 全国合计 119,893,223，样本内跨省流量合计 5,499,391（2020 年表分别为 131,271,202、5,083,191）。
4. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/6rp/html/fu10.htm （附录 10《第六次全国人口普查长表抽样工作细则》）：200。原句：“各省、自治区、直辖市按10％的抽样比例，在每个普查小区中，抽取长表调查住户组。每个住户组由相邻的4户组成。”
5. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/6rp/html/fu09.htm （附录 9《第六次全国人口普查表填写说明》）：200。原句：“五年前常住地—填写被登记人在普查标准时点的五年前，即2005年11月1日零时的常住地。……五年前居住在本省的人，圈填“1”；五年前居住省外的人，圈填“2”，并填写所在省的名称。”
6. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/left.htm ：200（2020 年鉴目录，为找 2020 口径文件）。
7. curl → https://www.stats.gov.cn/sj/pcsj/rkpc/7rp/zk/html/fu06.pdf （《第七次全国人口普查方案》）：200。原句：“普查长表……在全部住户中抽取 10%的户（不包括港澳台居民和外籍人员）填报”；“C14.五年前常住地——指被登记人在普查标准时点的五年前，即 2015 年 11 月 1 日零时的常住地。五年前居住在本县（市、区、旗）以外其他地区的人，还需选填五年前常住地的地址。”

口径小结：两年都是长表抽样登记数（方案或细则都写抽 10% 的户），五年前常住地都按普查时点前五年的 11 月 1 日零时计。差别是：2010 年只在省级登记五年前常住地，2020 年对县外的人登记到地址。汇总到省级后，两年的省对定义相同。实际入样比例两年未逐一核对（2020 年表合计约为普查总人口的 9.3%，见 T20）。第 4–7 次抓到的文件没有存入仓库，只在此摘原句。
