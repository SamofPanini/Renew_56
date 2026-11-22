#!/usr/bin/env python3
"""C0：把 Notion 上的数据源只读导出到 data/notion/。

用法：
    NOTION_TOKEN=... python3 scripts/export_notion.py [--config config/notion_sources.json] [--out data/notion]

- 数据源 ID 与 API 版本读自 config/notion_sources.json。
- 每个数据源输出 {name}.jsonl（API 原始 page 对象，按 page id 排序）与 {name}.csv（扁平化）。
- 另写 manifest.json（导出时刻 UTC、每库行数、属性列表、脚本 git commit）。
- 任一数据源行数为 0 或出现非 2xx 响应时以非零状态退出，且不覆盖 data/notion/ 下的旧文件。
- 只发两类请求（见 ALLOWED_REQUESTS 白名单）；任何写接口都会在发送前被拒绝。
- token 只放在请求头里，不打印、不写入任何文件。

依赖：Python 3.11+，requests。
"""
from __future__ import annotations

import argparse
import csv
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Iterable

import requests

API_BASE = "https://api.notion.com"
DEFAULT_NOTION_VERSION = "2025-09-03"
REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# 请求白名单：只允许这两类，其余一律拒绝（含一切 PATCH / DELETE / POST /pages 等写接口）。
# ---------------------------------------------------------------------------
_ID = r"[0-9a-fA-F-]{32,36}"
ALLOWED_REQUESTS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("POST", re.compile(rf"^/v1/data_sources/{_ID}/query$")),
    ("GET", re.compile(rf"^/v1/pages/{_ID}/properties/[^/?#]+$")),
)

META_COLUMNS = ["page_id", "url", "created_time", "last_edited_time"]
MULTI_SEP = "; "
# Notion 在 page 对象里对 relation/people/rich_text/title 等最多返回 25 项。
TRUNCATION_LIMIT = 25
MAX_429_RETRIES = 10


class ExportError(RuntimeError):
    pass


def check_allowed(method: str, path: str) -> None:
    method = method.upper()
    for m, pattern in ALLOWED_REQUESTS:
        if method == m and pattern.match(path):
            return
    raise ExportError(f"请求不在白名单内，已拒绝：{method} {path}")


class NotionClient:
    """只读客户端。所有请求都经 _request，先过白名单。"""

    def __init__(self, token: str, notion_version: str, session: requests.Session | None = None,
                 sleep: Callable[[float], None] = time.sleep):
        if not token:
            raise ExportError("环境变量 NOTION_TOKEN 为空")
        self._token = token
        self._version = notion_version
        self._session = session or requests.Session()
        self._sleep = sleep

    def _scrub(self, text: str) -> str:
        return text.replace(self._token, "***") if self._token else text

    def _request(self, method: str, path: str, *, json_body: dict | None = None,
                 params: dict | None = None) -> dict:
        check_allowed(method, path)
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Notion-Version": self._version,
            "Content-Type": "application/json",
        }
        for attempt in range(MAX_429_RETRIES + 1):
            resp = self._session.request(method, API_BASE + path, headers=headers,
                                         json=json_body, params=params, timeout=60)
            if resp.status_code == 429 and attempt < MAX_429_RETRIES:
                wait = _retry_after_seconds(resp.headers.get("Retry-After"))
                print(f"  429，{wait:.0f}s 后重试（{attempt + 1}/{MAX_429_RETRIES}）：{method} {path}",
                      file=sys.stderr)
                self._sleep(wait)
                continue
            if not 200 <= resp.status_code < 300:
                detail = ""
                try:
                    body = resp.json()
                    detail = f"{body.get('code', '')}: {body.get('message', '')}"
                except ValueError:
                    detail = resp.text[:300]
                raise ExportError(self._scrub(f"HTTP {resp.status_code} {method} {path} {detail}"))
            return resp.json()
        raise ExportError(f"429 重试 {MAX_429_RETRIES} 次仍失败：{method} {path}")

    def query_data_source(self, data_source_id: str) -> list[dict]:
        path = f"/v1/data_sources/{data_source_id}/query"
        pages: list[dict] = []
        cursor: str | None = None
        while True:
            body: dict[str, Any] = {"page_size": 100}
            if cursor:
                body["start_cursor"] = cursor
            data = self._request("POST", path, json_body=body)
            for item in data.get("results", []):
                if item.get("object") == "page" and not item.get("in_trash") and not item.get("archived"):
                    pages.append(item)
            if not data.get("has_more"):
                break
            cursor = data.get("next_cursor")
            if not cursor:
                raise ExportError(f"has_more 为真但没有 next_cursor：{path}")
        return pages

    def get_property_items(self, page_id: str, property_id: str) -> list[dict]:
        """GET /v1/pages/{id}/properties/{property_id}，分页取全量 property_item。"""
        path = f"/v1/pages/{page_id}/properties/{property_id}"
        items: list[dict] = []
        cursor: str | None = None
        while True:
            params: dict[str, Any] = {"page_size": 100}
            if cursor:
                params["start_cursor"] = cursor
            data = self._request("GET", path, params=params)
            if data.get("object") == "list":
                items.extend(data.get("results", []))
                if not data.get("has_more"):
                    break
                cursor = data.get("next_cursor")
                if not cursor:
                    break
            else:
                items.append(data)
                break
        return items


def _retry_after_seconds(value: str | None) -> float:
    try:
        return max(float(value), 0.0) if value is not None else 1.0
    except ValueError:
        return 1.0


# ---------------------------------------------------------------------------
# 截断补全
# ---------------------------------------------------------------------------
_PAGINATED_TYPES = ("relation", "rich_text", "title", "people")


def needs_completion(prop: dict) -> bool:
    ptype = prop.get("type")
    if ptype not in _PAGINATED_TYPES:
        return False
    if prop.get("has_more"):
        return True
    value = prop.get(ptype)
    return isinstance(value, list) and len(value) >= TRUNCATION_LIMIT


def complete_page(page: dict, fetch: Callable[[str, str], list[dict]]) -> list[str]:
    """就地补全被截断的属性；返回被补全的属性名列表。fetch(page_id, property_id)。"""
    completed: list[str] = []
    for name, prop in page.get("properties", {}).items():
        if not needs_completion(prop):
            continue
        ptype = prop["type"]
        items = fetch(page["id"], prop["id"])
        prop[ptype] = [it[ptype] for it in items if it.get("type") == ptype and ptype in it]
        if "has_more" in prop:
            prop["has_more"] = False
        completed.append(name)
    return completed


# ---------------------------------------------------------------------------
# 扁平化
# ---------------------------------------------------------------------------
def _plain(rich: list[dict] | None) -> str:
    return "".join(r.get("plain_text", "") for r in (rich or []))


def _user(u: dict | None) -> str:
    if not u:
        return ""
    return u.get("name") or u.get("id", "")


def _bool(v: Any) -> str:
    if v is None:
        return ""
    return "true" if v else "false"


def _num(v: Any) -> str:
    if v is None:
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v)


def _date_text(d: dict | None) -> str:
    if not d:
        return ""
    start, end = d.get("start") or "", d.get("end") or ""
    return f"{start}/{end}" if end else start


def _file_ref(f: dict) -> str:
    ftype = f.get("type")
    if ftype in ("file", "external") and isinstance(f.get(ftype), dict):
        return f[ftype].get("url", "") or f.get("name", "")
    return f.get("name", "")


def _scalar_value(obj: dict) -> str:
    """把带 type 字段的值（formula 结果、rollup 数组元素等）转成文本。"""
    t = obj.get("type")
    v = obj.get(t) if t else None
    if t in ("string", "url", "email", "phone_number"):
        return v or ""
    if t == "number":
        return _num(v)
    if t in ("boolean", "checkbox"):
        return _bool(v)
    if t == "date":
        return _date_text(v)
    if t in ("rich_text", "title"):
        return _plain(v)
    if t in ("select", "status"):
        return (v or {}).get("name", "")
    if t == "multi_select":
        return MULTI_SEP.join(o.get("name", "") for o in v or [])
    if t == "relation":
        return MULTI_SEP.join(r.get("id", "") for r in v or [])
    if t == "people":
        return MULTI_SEP.join(_user(u) for u in v or [])
    if t == "files":
        return MULTI_SEP.join(_file_ref(f) for f in v or [])
    if t == "formula":
        return _scalar_value(v or {})
    if t == "unique_id":
        if not v or v.get("number") is None:
            return ""
        return f"{v['prefix']}-{v['number']}" if v.get("prefix") else str(v["number"])
    if t in ("created_time", "last_edited_time"):
        return v or ""
    if t in ("created_by", "last_edited_by"):
        return _user(v)
    if t == "verification":
        return (v or {}).get("state", "")
    if t == "array":
        return MULTI_SEP.join(_scalar_value(x) for x in v or [])
    if v is None:
        return ""
    return json.dumps(v, ensure_ascii=False, sort_keys=True)


def flatten_property(name: str, prop: dict) -> dict[str, str]:
    """返回 {列名: 值}。date 拆成 名:start / 名:end，其余一列。"""
    ptype = prop.get("type")
    value = prop.get(ptype) if ptype else None
    if ptype == "date":
        value = value or {}
        return {f"{name}:start": value.get("start") or "", f"{name}:end": value.get("end") or ""}
    if ptype == "rollup":
        return {name: _scalar_value(value or {})}
    if ptype == "button":
        return {name: ""}
    return {name: _scalar_value(prop)}


def flatten_page(page: dict) -> dict[str, str]:
    row = {
        "page_id": page.get("id", ""),
        "url": page.get("url", ""),
        "created_time": page.get("created_time", ""),
        "last_edited_time": page.get("last_edited_time", ""),
    }
    for name, prop in page.get("properties", {}).items():
        row.update(flatten_property(name, prop))
    return row


def property_names(pages: Iterable[dict]) -> list[str]:
    names: set[str] = set()
    for p in pages:
        names.update(p.get("properties", {}).keys())
    return sorted(names)


def property_columns(pages: list[dict]) -> list[str]:
    """CSV 的属性列：按属性名排序；date 属性展开为两列。"""
    types: dict[str, str] = {}
    for p in pages:
        for name, prop in p.get("properties", {}).items():
            types.setdefault(name, prop.get("type", ""))
    cols: list[str] = []
    for name in sorted(types):
        if types[name] == "date":
            cols += [f"{name}:start", f"{name}:end"]
        else:
            cols.append(name)
    return cols


def to_csv(pages: list[dict]) -> str:
    cols = META_COLUMNS + [c for c in property_columns(pages) if c not in META_COLUMNS]
    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=cols, lineterminator="\n", extrasaction="ignore")
    writer.writeheader()
    for page in sort_pages(pages):
        row = flatten_page(page)
        writer.writerow({c: row.get(c, "") for c in cols})
    return buf.getvalue()


def to_jsonl(pages: list[dict]) -> str:
    return "".join(json.dumps(p, ensure_ascii=False, sort_keys=True) + "\n" for p in sort_pages(pages))


def sort_pages(pages: list[dict]) -> list[dict]:
    return sorted(pages, key=lambda p: p.get("id", ""))


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------
def load_config(path: Path) -> tuple[str, dict[str, str]]:
    cfg = json.loads(path.read_text(encoding="utf-8"))
    sources = cfg.get("sources") or {}
    if not sources:
        raise ExportError(f"{path} 里没有 sources")
    return cfg.get("notion_version", DEFAULT_NOTION_VERSION), sources


def git_commit() -> str:
    if os.environ.get("GITHUB_SHA"):
        return os.environ["GITHUB_SHA"]
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO_ROOT, check=True,
                              capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return ""


def _write(path: Path, text: str) -> None:
    with open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write(text)


def export(client: NotionClient, sources: dict[str, str], out_dir: Path) -> dict:
    staging = Path(tempfile.mkdtemp(prefix="notion_export_"))
    try:
        manifest: dict[str, Any] = {
            "exported_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "script_commit": git_commit(),
            "sources": {},
        }
        for name, ds_id in sources.items():
            print(f"[{name}] 查询数据源 {ds_id}", file=sys.stderr)
            pages = client.query_data_source(ds_id)
            if not pages:
                raise ExportError(f"[{name}] 行数为 0，中止，不覆盖旧文件")
            completed = 0
            for page in pages:
                completed += len(complete_page(page, client.get_property_items))
            _write(staging / f"{name}.jsonl", to_jsonl(pages))
            _write(staging / f"{name}.csv", to_csv(pages))
            manifest["sources"][name] = {
                "data_source_id": ds_id,
                "rows": len(pages),
                "properties": property_names(pages),
                "csv_columns": META_COLUMNS + property_columns(pages),
                "completed_properties": completed,
            }
            print(f"[{name}] {len(pages)} 行，补全截断属性 {completed} 处", file=sys.stderr)
        _write(staging / "manifest.json", json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")

        # 全部成功后才替换输出目录里的文件。
        out_dir.mkdir(parents=True, exist_ok=True)
        for f in staging.iterdir():
            shutil.copyfile(f, out_dir / f.name)
        return manifest
    finally:
        shutil.rmtree(staging, ignore_errors=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--config", type=Path, default=REPO_ROOT / "config" / "notion_sources.json")
    ap.add_argument("--out", type=Path, default=REPO_ROOT / "data" / "notion")
    args = ap.parse_args(argv)
    try:
        version, sources = load_config(args.config)
        client = NotionClient(os.environ.get("NOTION_TOKEN", ""), version)
        manifest = export(client, sources, args.out)
    except (ExportError, requests.RequestException) as e:
        token = os.environ.get("NOTION_TOKEN", "")
        msg = str(e).replace(token, "***") if token else str(e)
        print(f"导出失败：{msg}", file=sys.stderr)
        return 1
    rows = ", ".join(f"{k}={v['rows']}" for k, v in manifest["sources"].items())
    print(f"导出完成：{rows}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
