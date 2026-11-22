"""C0 导出脚本的离线测试（不联网）。运行：python3 -m unittest discover -s tests -v"""
from __future__ import annotations

import csv
import io
import json
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import export_notion as ex  # noqa: E402

FIX = Path(__file__).resolve().parent / "fixtures"
TOKEN = "secret_TESTTOKEN_should_never_leak"


def load(name: str) -> dict:
    return json.loads((FIX / name).read_text(encoding="utf-8"))


class FlattenTest(unittest.TestCase):
    def setUp(self):
        self.a, self.b, self.c = load("page_a.json"), load("page_b.json"), load("page_c.json")

    def test_all_types_page_a(self):
        row = ex.flatten_page(self.a)
        expected = {
            "page_id": "22222222-2222-2222-2222-222222222222",
            "url": "https://www.notion.so/A-22222222222222222222222222222222",
            "created_time": "2026-11-01T08:00:00.000Z",
            "last_edited_time": "2026-11-20T09:30:00.000Z",
            "名称": "苗族（湘西）",
            "备注": "第一段，第二段",
            "数量": "12",
            "比例": "0.25",
            "证据等级": "E",
            "状态": "待核",
            "标签": "语言; 方言",
            "日期:start": "2026-11-14",
            "日期:end": "2026-11-15",
            "负责人": "Lucky",
            "已核": "true",
            "来源": "https://example.org/a",
            "邮箱": "a@example.org",
            "电话": "+86 10 0000",
            "附件": "https://example.org/a.pdf",
            "文字闸": "通过",
            "分数": "3",
            "是否完成": "false",
            "到期": "2026-12-01",
            "汇总数": "7",
            "汇总名": "甲; 乙",
            "编号": "N-42",
            "创建者": "11111111-1111-1111-1111-111111111111",
            "创建时间": "2026-11-01T08:00:00.000Z",
            "编辑时间": "2026-11-20T09:30:00.000Z",
            "编辑者": "11111111-1111-1111-1111-111111111111",
            "核验": "unverified",
            "按钮": "",
        }
        for k, v in expected.items():
            self.assertEqual(row[k], v, k)
        rel = row["关联"].split("; ")
        self.assertEqual(len(rel), 25)
        self.assertEqual(rel[0], "aaaaaaaa-0000-0000-0000-000000000001")
        self.assertNotIn("日期", row)  # date 只有拆开的两列

    def test_empty_values_page_b(self):
        row = ex.flatten_page(self.b)
        for k in ["备注", "数量", "证据等级", "标签", "日期:start", "日期:end", "负责人",
                  "来源", "附件", "文字闸", "汇总名"]:
            self.assertEqual(row[k], "", k)
        self.assertEqual(row["已核"], "false")
        self.assertEqual(row["编号"], "7")
        self.assertEqual(row["关联"], "aaaaaaaa-0000-0000-0000-000000000001")

    def test_csv_layout(self):
        text = ex.to_csv([self.a, self.c, self.b])
        self.assertNotIn("\r", text)
        rows = list(csv.DictReader(io.StringIO(text)))
        header = text.split("\n", 1)[0].split(",")
        self.assertEqual(header[:4], ex.META_COLUMNS)
        self.assertIn("文字闸", header)
        self.assertIn("日期:start", header)
        self.assertIn("日期:end", header)
        # 按 page id 排序
        self.assertEqual([r["page_id"] for r in rows],
                         sorted([self.a["id"], self.b["id"], self.c["id"]]))
        by_id = {r["page_id"]: r for r in rows}
        self.assertEqual(by_id[self.c["id"]]["文字闸"], "闸：缺来源")
        self.assertEqual(by_id[self.c["id"]]["日期:start"], "2026-11-14T10:00:00.000+08:00")

    def test_jsonl_sorted_raw(self):
        lines = ex.to_jsonl([self.a, self.c, self.b]).splitlines()
        objs = [json.loads(l) for l in lines]
        self.assertEqual([o["id"] for o in objs], sorted(o["id"] for o in objs))
        self.assertEqual(objs[-1], self.c)  # 原样保存

    def test_csv_columns_match_property_names(self):
        cols = ex.property_columns([self.a])
        names = ex.property_names([self.a])
        for n in names:
            if self.a["properties"][n]["type"] == "date":
                self.assertIn(f"{n}:start", cols)
            else:
                self.assertIn(n, cols)


class CompletionTest(unittest.TestCase):
    def test_relation_and_rich_text_completed(self):
        a, c = load("page_a.json"), load("page_c.json")
        responses = {
            ("rel1"): load("property_relation_rel1.json"),
            ("%3Dabc"): load("property_rich_text_abc.json"),
        }
        calls = []

        def fetch(page_id, prop_id):
            calls.append((page_id, prop_id))
            return responses[prop_id]["results"]

        self.assertEqual(ex.complete_page(a, fetch), ["关联"])
        self.assertEqual(len(a["properties"]["关联"]["relation"]), 26)
        self.assertFalse(a["properties"]["关联"]["has_more"])
        self.assertEqual(len(ex.flatten_page(a)["关联"].split("; ")), 26)

        self.assertEqual(ex.complete_page(c, fetch), ["备注"])
        self.assertEqual(ex.flatten_page(c)["备注"], "".join(f"{i}," for i in range(30)))
        self.assertEqual(calls, [(a["id"], "rel1"), (c["id"], "%3Dabc")])

    def test_untruncated_not_fetched(self):
        b = load("page_b.json")
        self.assertEqual(ex.complete_page(b, lambda *_: self.fail("不应请求")), [])


class WhitelistTest(unittest.TestCase):
    DS = "50f348e4-efb8-4b76-9c9b-ad82f7adc6c3"
    PG = "22222222-2222-2222-2222-222222222222"

    def test_allowed(self):
        ex.check_allowed("POST", f"/v1/data_sources/{self.DS}/query")
        ex.check_allowed("GET", f"/v1/pages/{self.PG}/properties/%3Dabc")
        ex.check_allowed("GET", f"/v1/pages/{self.PG}/properties/title")

    def test_rejected(self):
        bad = [
            ("PATCH", f"/v1/pages/{self.PG}"),
            ("POST", "/v1/pages"),
            ("DELETE", f"/v1/blocks/{self.PG}"),
            ("PATCH", f"/v1/data_sources/{self.DS}"),
            ("GET", f"/v1/data_sources/{self.DS}/query"),
            ("POST", f"/v1/pages/{self.PG}/properties/title"),
            ("GET", f"/v1/pages/{self.PG}"),
            ("POST", f"/v1/data_sources/{self.DS}/query/../../pages"),
            ("POST", "/v1/search"),
        ]
        for method, path in bad:
            with self.assertRaises(ex.ExportError, msg=f"{method} {path}"):
                ex.check_allowed(method, path)


class FakeResp:
    def __init__(self, status, body, headers=None):
        self.status_code, self._body, self.headers = status, body, headers or {}
        self.text = json.dumps(body)

    def json(self):
        return self._body


class FakeSession:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def request(self, method, url, **kw):
        self.calls.append((method, url, kw))
        return self.responses.pop(0)


class ClientTest(unittest.TestCase):
    DS = "50f348e4-efb8-4b76-9c9b-ad82f7adc6c3"

    def test_pagination_and_429(self):
        a, b = load("page_a.json"), load("page_b.json")
        sess = FakeSession([
            FakeResp(429, {"code": "rate_limited"}, {"Retry-After": "3"}),
            FakeResp(200, {"results": [a], "has_more": True, "next_cursor": "c1"}),
            FakeResp(200, {"results": [b], "has_more": False, "next_cursor": None}),
        ])
        slept = []
        client = ex.NotionClient(TOKEN, "2025-09-03", session=sess, sleep=slept.append)
        pages = client.query_data_source(self.DS)
        self.assertEqual([p["id"] for p in pages], [a["id"], b["id"]])
        self.assertEqual(slept, [3.0])
        self.assertEqual(sess.calls[2][2]["json"]["start_cursor"], "c1")
        self.assertEqual(sess.calls[0][2]["headers"]["Notion-Version"], "2025-09-03")
        self.assertTrue(all(c[0] == "POST" for c in sess.calls))

    def test_non_2xx_fails_without_leaking_token(self):
        sess = FakeSession([FakeResp(401, {"code": "unauthorized", "message": f"bad {TOKEN}"})])
        client = ex.NotionClient(TOKEN, "2025-09-03", session=sess, sleep=lambda s: None)
        with self.assertRaises(ex.ExportError) as cm:
            client.query_data_source(self.DS)
        self.assertIn("401", str(cm.exception))
        self.assertNotIn(TOKEN, str(cm.exception))


class ExportTest(unittest.TestCase):
    def test_zero_rows_keeps_old_files(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            (out / "N.csv").write_text("old\n", encoding="utf-8")
            a = load("page_a.json")
            sess = FakeSession([
                FakeResp(200, {"results": [a], "has_more": False}),
                FakeResp(200, load("property_relation_rel1.json")),
                FakeResp(200, {"results": [], "has_more": False}),
            ])
            client = ex.NotionClient(TOKEN, "2025-09-03", session=sess, sleep=lambda s: None)
            with self.assertRaises(ex.ExportError):
                ex.export(client, {"N": "50f348e4-efb8-4b76-9c9b-ad82f7adc6c3",
                                   "E": "a4d6ca00-3182-465e-8528-3c15f2c47d3d"}, out)
            self.assertEqual((out / "N.csv").read_text(encoding="utf-8"), "old\n")
            self.assertEqual(sorted(p.name for p in out.iterdir()), ["N.csv"])

    def test_success_writes_files_and_manifest(self):
        with tempfile.TemporaryDirectory() as d:
            out = Path(d)
            sess = FakeSession([
                FakeResp(200, {"results": [load("page_b.json")], "has_more": False}),
            ])
            client = ex.NotionClient(TOKEN, "2025-09-03", session=sess, sleep=lambda s: None)
            ex.export(client, {"N": "50f348e4-efb8-4b76-9c9b-ad82f7adc6c3"}, out)
            self.assertEqual(sorted(p.name for p in out.iterdir()),
                             ["N.csv", "N.jsonl", "manifest.json"])
            m = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
            self.assertEqual(m["sources"]["N"]["rows"], 1)
            self.assertIn("文字闸", m["sources"]["N"]["properties"])
            self.assertRegex(m["exported_at"], r"Z$")
            for p in out.iterdir():
                self.assertNotIn(TOKEN, p.read_text(encoding="utf-8"))
                self.assertNotIn(b"\r\n", p.read_bytes())

    def test_config_has_five_sources(self):
        version, sources = ex.load_config(ROOT / "config" / "notion_sources.json")
        self.assertEqual(version, "2025-09-03")
        self.assertEqual(sorted(sources), ["E", "I", "N", "T", "TICKETS"])


if __name__ == "__main__":
    unittest.main()
