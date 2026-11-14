# data/raw 来源记录（T20）

## 状态：数据闸门未通过（2026-11-14），等待用户提供原表

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
