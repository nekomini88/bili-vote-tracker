# -*- coding: utf-8 -*-
"""行为一致性冒烟测试: 用临时 DB + TestClient 验证重构后所有 API 返回结构不变。"""
import os, sys, tempfile, sqlite3

# 临时 DB, 在 import app 前设置
fd, db = tempfile.mkstemp(suffix=".db")
os.close(fd)
os.environ["DB_PATH"] = db
os.environ["TARGET_URL"] = "https://example.test/"

sys.path.insert(0, "/root/bili-vote-tracker/backend")
import starlette.staticfiles as _ssf
class _FakeStaticFiles:
    def __init__(self, *a, **k): pass
_ssf.StaticFiles = _FakeStaticFiles
import fastapi.staticfiles as _fsf
_fsf.StaticFiles = _FakeStaticFiles

import app as bvt
from fastapi.testclient import TestClient
bvt._scheduler.shutdown(wait=False)  # 阻止后台轮询干扰冒烟测试

# 种子数据: A 有 4 条 (含同时间戳重复 + 24h 前旧记录), B 有 1 条
with sqlite3.connect(db) as con:
    con.execute("INSERT INTO vote_records(captured_at, title, votes, item_id, is_my_vote) VALUES (?,?,?,?,?)",
                ("2026-08-10T10:00:00+08:00", "A", 50, "id-a", 1))   # 24h 之前, 供 diff 24h 间隔
    con.execute("INSERT INTO vote_records(captured_at, title, votes, item_id, is_my_vote) VALUES (?,?,?,?,?)",
                ("2026-08-15T10:00:00+08:00", "A", 100, "id-a", 1))
    con.execute("INSERT INTO vote_records(captured_at, title, votes, item_id, is_my_vote) VALUES (?,?,?,?,?)",
                ("2026-08-15T10:00:00+08:00", "A", 999, "id-a2", 0))  # 同时间戳重复 -> 去重应保留第一条
    con.execute("INSERT INTO vote_records(captured_at, title, votes, item_id, is_my_vote) VALUES (?,?,?,?,?)",
                ("2026-08-15T11:00:00+08:00", "A", 120, "id-a", 1))
    con.execute("INSERT INTO vote_records(captured_at, title, votes, item_id, is_my_vote) VALUES (?,?,?,?,?)",
                ("2026-08-15T09:00:00+08:00", "B", 50, "id-b", 0))
# 事务已提交, 再单独写 meta, 避免连接锁冲突
bvt.set_meta("activity_id", "act1")
bvt.set_meta("group_id", "grp1")
bvt.set_meta("vote_id", "v1")

c = TestClient(bvt.app)
checks = []

def chk(name, cond, extra=""):
    checks.append((name, cond, extra))
    print(("PASS" if cond else "FAIL"), name, extra)

# public-config
r = c.get("/api/public-config"); j = r.json()
chk("public-config 200", r.status_code == 200)
chk("public-config keys", set(j) == {"poll_interval", "target_url"}, str(j))

# config (auth)
r = c.get("/api/config", auth=("admin", "nekomini")); j = r.json()
chk("config 200", r.status_code == 200)
chk("config keys", set(j) == {"target_url", "poll_interval", "activity_id", "group_id", "vote_id"}, str(j))
r = c.get("/api/config", auth=("admin", "wrong"))
chk("config 401 on bad auth", r.status_code == 401)

# update_config
r = c.post("/api/config", json={"poll_interval": 5}, auth=("admin", "nekomini")); j = r.json()
chk("update_config keys", set(j) == {"ok", "target_url", "poll_interval"}, str(j))
chk("update_config value", j["poll_interval"] == 5)

# records
r = c.get("/api/records"); j = r.json()
chk("records 200 + count", r.status_code == 200 and len(j) == 5, f"len={len(j)}")
chk("records keys", all(set(x) == {"id", "captured_at", "title", "votes", "item_id"} for x in j))

# latest: 每候选人最近一条
r = c.get("/api/latest"); j = r.json()
chk("latest 2 candidates", len(j) == 2, str(j))
a = next(x for x in j if x["title"] == "A")
chk("latest A newest (11:00,120)", a["captured_at"] == "2026-08-15T11:00:00+08:00" and a["votes"] == 120, str(a))
chk("latest keys", set(a) == {"title", "votes", "captured_at", "item_id", "is_my_vote"})

# history: DESC 取回 -> 反转 -> 按时间戳去重
r = c.get("/api/history", params={"title": "A"}); j = r.json()
chk("history dedup to 3", len(j) == 3, str(j))
chk("history asc order", [x["captured_at"] for x in j] == ["2026-08-10T10:00:00+08:00", "2026-08-15T10:00:00+08:00", "2026-08-15T11:00:00+08:00"])
chk("history dedup keeps first", j[1]["votes"] == 100, str(j))

# range: 升序 + 去重
r = c.get("/api/range", params={"title": "A"}); j = r.json()
chk("range dedup to 3", len(j) == 3, str(j))
chk("range keeps first at dup ts", j[1]["votes"] == 100, str(j))

# diff: 24h 间隔应命中 08-10 旧记录
r = c.get("/api/diff", params={"title": "A"}); j = r.json()
chk("diff keys", set(j) == {"title", "current", "intervals"}, str(j))
chk("diff current", j["current"] == {"captured_at": "2026-08-15T11:00:00+08:00", "votes": 120}, str(j))
chk("diff interval keys", set(j["intervals"]) == {"1m", "5m", "30m", "6h", "24h"}, str(j))
chk("diff 24h delta", j["intervals"]["24h"]["delta"] == 70, str(j["intervals"]["24h"]))
chk("diff interval value shape", set(j["intervals"]["24h"]) == {"captured_at", "votes", "delta"})

# diff 无历史记录的 title: intervals 为空 dict (原逻辑只在有 prev 时加 key)
r = c.get("/api/diff", params={"title": "NOPE"}); j = r.json()
chk("diff no-history", j["current"] is None and j["intervals"] == {}, str(j))

# stats
r = c.get("/api/stats"); j = r.json()
chk("stats keys", set(j) == {"count", "max_votes", "min_votes", "avg_votes", "candidates", "latest_capture", "first_capture", "version"}, str(j))
chk("stats values", j["count"] == 5 and j["candidates"] == 2 and j["max_votes"] == 999 and j["min_votes"] == 50 and j["avg_votes"] == 263.8, str(j))

# trigger + healthz
chk("trigger 401 no auth", c.get("/api/trigger").status_code == 401)
chk("trigger 200 auth", c.get("/api/trigger", auth=("admin", "nekomini")).status_code == 200)
r = c.get("/healthz"); chk("healthz", r.status_code == 200 and set(r.json()) == {"ok", "version"})

# my-info 无 IP 情况 (X-Forwarded-For 空)
r = c.get("/api/my-info", headers={"X-Forwarded-For": " "})
chk("my-info fallback shape", set(r.json()) <= {"ip", "country", "city"}, str(r.json()))

# 常量行为核对
chk("PAGE_SIZE", bvt.PAGE_SIZE == 20)
chk("MAX_FETCH_PAGES", bvt.MAX_FETCH_PAGES == 50)
chk("DIFF_INTERVALS keys", list(bvt.DIFF_INTERVALS) == ["1m", "5m", "30m", "6h", "24h"])

failed = [c for c in checks if not c[1]]
print(f"\n== {len(checks) - len(failed)}/{len(checks)} passed ==")
os.unlink(db)
sys.exit(1 if failed else 0)
