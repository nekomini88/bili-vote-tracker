#!/usr/bin/env python3
"""Bili Vote Tracker — API 集成测试（对运行中的容器端到端）
运行: python3 tests/api_test.py  （unittest 内置，无需 pytest）
前置: docker compose up -d 已运行，容器监听 127.0.0.1:9008
"""
import os
import sys
import unittest
import urllib.request
import urllib.parse
import json

BASE = os.environ.get("BVT_BASE", "http://127.0.0.1:9008")


def get(path):
    with urllib.request.urlopen(BASE + path, timeout=15) as r:
        return r.status, json.loads(r.read().decode())


class ApiIntegrationTest(unittest.TestCase):

    def test_healthz(self):
        status, j = get("/healthz")
        self.assertEqual(status, 200)
        self.assertTrue(j.get("ok"))
        self.assertTrue(j.get("version"), "healthz 应返回 version 字段")

    def test_stats_version(self):
        _, j = get("/api/stats")
        self.assertIn("version", j, "stats 应暴露版本号")
        self.assertGreater(j.get("candidates", 0), 0, "应有候选人数据")

    def test_latest_returns_all_candidates(self):
        status, rows = get("/api/latest")
        self.assertEqual(status, 200)
        # 活动共有 46 位候选人（pn 分页拉全后落库）
        self.assertGreaterEqual(len(rows), 46, f"应返回全部 46 位候选人，实际 {len(rows)}")
        titles = {r["title"] for r in rows}
        # 关键候选应存在（含新增的后半段）
        for name in ["迪迦奥特曼", "赛罗奥特曼", "格丽乔奥特曼", "奥特之王", "纳伊斯奥特曼"]:
            self.assertIn(name, titles, f"缺少候选人 {name}")

    def test_latest_rows_shape(self):
        _, rows = get("/api/latest")
        for r in rows:
            self.assertIn("title", r)
            self.assertIn("votes", r)
            self.assertIn("captured_at", r)
            self.assertIn("item_id", r)
            self.assertIsInstance(r["votes"], (int, float))

    def test_diff_real_delta(self):
        # 老候选应有真实增量（可能有 0，但不能是 null）
        _, rows = get("/api/latest")
        diga = next((r for r in rows if r["title"] == "迪迦奥特曼"), None)
        self.assertIsNotNone(diga)
        status, d = get(f"/api/diff?title={urllib.parse.quote(diga['title'])}")
        self.assertEqual(status, 200)
        self.assertIn("intervals", d)
        self.assertGreaterEqual(len(d["intervals"]), 1)

    def test_history(self):
        _, rows = get("/api/latest")
        title = urllib.parse.quote(rows[0]["title"])
        status, hist = get(f"/api/history?title={title}")
        self.assertEqual(status, 200)
        self.assertGreater(len(hist), 0, "历史至少一条")


if __name__ == "__main__":
    unittest.main(verbosity=2)
