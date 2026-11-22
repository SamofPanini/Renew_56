# 任务

## C0：Notion 数据源导出

**用途**：让 GitHub Actions 每日（或手动）把 Notion 上的五个数据源只读导出到本仓库，供 C1 等任务直接读文件，不必在任务 session 里访问 Notion。

**脚本与配置**

- `scripts/export_notion.py`：Python 3.11，只依赖 `requests`；Notion API 版本 `2025-09-03`；对每个数据源调 `POST /v1/data_sources/{id}/query` 分页取全量（回收站以外的全部行），relation 超过 25 项、rich_text/title/people 可能被截断时用 `GET /v1/pages/{id}/properties/{property_id}` 补全。代码内白名单只放行这两类请求，任何写接口在发送前即被拒绝；token 不进日志。
- `config/notion_sources.json`：数据源名称与 ID（N、E、I、T、TICKETS）。增删数据源只改这里。
- `.github/workflows/export-notion.yml`：`workflow_dispatch` + 每日 UTC 19:17；有变化时以 github-actions bot 提交到分支 `data/notion-export` 并开或更新 PR，不直接推 main。只有 `manifest.json` 变化（导出时刻）不算变化。
- 测试：`python3 -m unittest discover -s tests -v`（离线，用 `tests/fixtures/` 里手造的 page JSON）。

**输出路径**（`data/notion/`，UTF-8，LF）

| 文件 | 内容 |
| --- | --- |
| `{name}.jsonl` | API 原始 page 对象，一行一个，按 page id 排序；被截断的属性已就地补全 |
| `{name}.csv` | 扁平化表。前四列 `page_id`、`url`、`created_time`、`last_edited_time`，其后为属性列（按属性名排序），列名与 Notion 属性名一致 |
| `manifest.json` | `exported_at`（UTC）、`script_commit`，每库 `rows`、`properties`、`csv_columns`、`completed_properties` |

CSV 取值规则：rich_text/title 取 `plain_text` 拼接；select/status 取 name；multi_select、relation（page id）、people、files 用 `; ` 连接；date 拆成 `属性名:start` 与 `属性名:end`；formula 写计算结果（如 `文字闸`）；checkbox 写 `true`/`false`；rollup 写数值或数组元素拼接；unique_id 写 `前缀-编号`。

任一数据源行数为 0 或出现非 2xx 响应时，脚本以非零状态退出，`data/notion/` 下的旧文件不被覆盖；429 按 `Retry-After` 重试。

**用户需先做的三步**

1. 在 Notion 建一个内部集成（Settings → Connections → Develop or manage integrations），只勾“Read content”；把五个数据源所在的数据库都分享给（Connect to）这个集成。
2. 在 GitHub 仓库 Settings → Secrets and variables → Actions 新建 secret `NOTION_TOKEN`，值为该集成的 Internal Integration Secret。
3. 在 GitHub 仓库 Settings → Actions → General → Workflow permissions 勾选 “Allow GitHub Actions to create and approve pull requests”（否则工作流能推分支但开不了 PR）。

之后在 Actions 页选 “Export Notion (C0)” → Run workflow 手动触发一次。

## C1

**输入**：`data/notion/N.csv`、`data/notion/E.csv`（由 C0 导出；列名以 C0 脚本输出为准，见 `data/notion/manifest.json` 的 `csv_columns`）。不在任务 session 里直接访问 Notion。
