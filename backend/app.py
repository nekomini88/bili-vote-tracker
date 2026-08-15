from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sqlite3
import json
import os
import re
from datetime import datetime, timezone, timedelta
import time
import requests
import sys
from apscheduler.schedulers.background import BackgroundScheduler

DB_PATH = os.environ.get("DB_PATH", "/app/db/votes.db")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "nekomini")
TARGET_URL = os.environ.get("TARGET_URL", "https://b23.tv/wDz5Xnc")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "1"))
UTC8 = timezone(timedelta(hours=8))
APP_VERSION = Path("/app/VERSION").read_text().strip() if Path("/app/VERSION").exists() else "0.0.0"
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

# --- 常量 ---
DISCOVER_TIMEOUT = 20          # discover_vote_ids 请求超时
FETCH_TIMEOUT = 15             # fetch_votes 分页请求超时
GEO_TIMEOUT = 5                # ipapi.co 查询超时
PAGE_SIZE = 20                 # 排名接口每页条数
MAX_FETCH_PAGES = 50           # fetch_votes 分页安全上限
GEO_CACHE_TTL = 60             # IP 地理信息缓存秒数
GEO_CACHE_MAX = 256            # 地理缓存条目上限
DEFAULT_RECORDS_LIMIT = 200
DEFAULT_HISTORY_LIMIT = 300
DIFF_INTERVALS = {
    "1m": timedelta(minutes=1),
    "5m": timedelta(minutes=5),
    "30m": timedelta(minutes=30),
    "6h": timedelta(hours=6),
    "24h": timedelta(hours=24),
}
RECORD_COLS = ["id", "captured_at", "title", "votes", "item_id"]
LATEST_COLS = ["title", "votes", "captured_at", "item_id", "is_my_vote"]

CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS vote_records (id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at DATETIME DEFAULT CURRENT_TIMESTAMP, title TEXT, votes INTEGER, item_id TEXT, is_my_vote INTEGER DEFAULT 0)"
CREATE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_vote_time ON vote_records(captured_at)"
CREATE_META_SQL = "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"
INSERT_RECORD_SQL = "INSERT OR IGNORE INTO vote_records(captured_at, title, votes, item_id, is_my_vote) VALUES(?,?,?,?,?)"

def init_db():
    with sqlite3.connect(DB_PATH) as con:
        con.execute(CREATE_TABLE_SQL)
        con.execute(CREATE_INDEX_SQL)
        con.execute(CREATE_META_SQL)

def set_meta(key, value):
    with sqlite3.connect(DB_PATH) as con:
        con.execute("INSERT OR REPLACE INTO meta(key, value) VALUES(?,?)", (key, str(value)))

def get_meta(key, default=None):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT value FROM meta WHERE key=?", (key,))
        row = cur.fetchone()
        return row[0] if row else default

init_db()
app = FastAPI(title="Bili Vote Tracker")
HEADERS = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36","Referer":"https://www.bilibili.com/"}

def discover_vote_ids(url: str):
    try:
        resp = requests.get(url, headers=HEADERS, timeout=DISCOVER_TIMEOUT)
        text = resp.text
        m = re.search(r'"trackValue"\s*:\s*"([^"]+)"', text)
        track = m.group(1) if m else get_meta("group_id")
        m = re.search(r'"voteValue"\s*:\s*"([^"]+)"', text)
        vote = m.group(1) if m else get_meta("vote_id")
        aid = get_meta("activity_id")
        if aid and track and vote:
            return aid, track, vote
        ids = re.findall(r'\b\d{2}ERA\d+wlogh[vw]\w+\b', text)
        tracks = [x for x in ids if 'loghvt' in x]
        votes = [x for x in ids if 'loghvx' in x or 'loghvz' in x]
        aid = get_meta("activity_id") or (ids[0] if ids else None)
        track = track or (tracks[0] if tracks else None)
        vote = vote or (votes[0] if votes else None)
        return aid, track, vote
    except Exception as e:
        print("[discover] failed:", e)
    return None, None, None

def fetch_votes(url: str):
    aid = get_meta("activity_id")
    group = get_meta("group_id")
    vote = get_meta("vote_id")
    if not all([aid, group, vote]):
        aid, group, vote = discover_vote_ids(url)
    if not all([aid, group, vote]):
        print("[fetch] missing vote ids")
        return []
    api = "https://api.bilibili.com/x/activity_components/vote_new/rank"
    out = []
    seen_ids = set()
    try:
        pn = 1
        total = None
        while True:
            r = requests.get(api, params={"vote_id": vote, "group_id": group, "activity_id": aid, "pn": pn, "page_size": PAGE_SIZE}, headers=HEADERS, timeout=FETCH_TIMEOUT)
            if r.status_code != 200:
                print("[fetch] api status", r.status_code)
                break
            payload = r.json()
            if payload.get("code") != 0:
                print("[fetch] api error", payload)
                break
            data = payload.get("data") or {}
            items = data.get("items", [])
            if not items:
                break
            page_info = data.get("page") or {}
            total = page_info.get("total", total)
            for it in items:
                iid = it.get("item_id")
                if iid is not None:
                    if iid in seen_ids:
                        continue
                    seen_ids.add(iid)
                info = it.get("item", {}) or {}
                out.append({
                    "item_id": iid,
                    "title": info.get("title") or "",
                    "votes": it.get("vote"),
                    "is_vote": int(it.get("is_vote") or 0),
                    "user_vote": it.get("user_vote", 0),
                })
            print(f"[fetch] pn={pn} accumulated={len(out)}/{total or '?'}")
            if total is not None and len(out) >= total:
                break
            if len(items) < PAGE_SIZE:
                break
            pn += 1
            if pn > MAX_FETCH_PAGES:  # 安全上限
                break
        if out:
            set_meta("activity_id", aid)
            set_meta("group_id", group)
            set_meta("vote_id", vote)
        # poll_and_save persists after fetch_votes returns
        return out
    except Exception as e:
        print("[fetch] exception:", e)
    return []

def _save_records(rows, now):
    """将抓取结果批量写入 vote_records（INSERT OR IGNORE 去重）。"""
    with sqlite3.connect(DB_PATH) as con:
        for row in rows:
            con.execute(INSERT_RECORD_SQL, (now, row["title"], row["votes"], row["item_id"], row["is_vote"]))

def poll_and_save():
    rows = fetch_votes(TARGET_URL)
    if not rows:
        print("[poll] no rows")
        return
    now = datetime.now(UTC8).isoformat()
    _save_records(rows, now)
    print(f"[poll] saved {len(rows)} candidates at {now}")

_scheduler = None

def get_or_create_job():
    """单例 scheduler：只在首次创建，后续仅重建 job，避免重复轮询。"""
    global _scheduler
    if _scheduler is None:
        _scheduler = BackgroundScheduler()
        _scheduler.start()
    try:
        job = _scheduler.get_job("bili_vote_job")
        if job:
            job.remove()
    except Exception:
        pass
    _scheduler.add_job(poll_and_save, "interval", minutes=POLL_INTERVAL, next_run_time=datetime.now(UTC8), id="bili_vote_job")
    return _scheduler

scheduler = get_or_create_job()

from fastapi import Depends, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials
security = HTTPBasic()

def admin_auth(credentials: HTTPBasicCredentials = Depends(security)):
    if not (credentials.username == ADMIN_USER and credentials.password == ADMIN_PASS):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized", headers={"WWW-Authenticate": "Basic"})
    return credentials.username

@app.get("/api/public-config")
def public_config():
    return {"poll_interval": POLL_INTERVAL, "target_url": TARGET_URL}

def _config_payload():
    """/api/config 返回体：当前配置 + meta 中缓存的投票 ID。"""
    return {
        "target_url": TARGET_URL,
        "poll_interval": POLL_INTERVAL,
        "activity_id": get_meta("activity_id"),
        "group_id": get_meta("group_id"),
        "vote_id": get_meta("vote_id"),
    }

@app.get("/api/config")
def config(username: str = Depends(admin_auth)):
    return _config_payload()

def _apply_config(payload):
    """应用配置更新并持久化到 meta，返回 (target_url, poll_interval)。"""
    global TARGET_URL, POLL_INTERVAL
    TARGET_URL = payload.get("target_url", TARGET_URL)
    POLL_INTERVAL = int(payload.get("poll_interval", POLL_INTERVAL))
    set_meta("target_url", TARGET_URL)
    set_meta("poll_interval", POLL_INTERVAL)

@app.post("/api/config")
def update_config(payload: dict, username: str = Depends(admin_auth)):
    _apply_config(payload)
    get_or_create_job()
    return {"ok": True, "target_url": TARGET_URL, "poll_interval": POLL_INTERVAL}

def _rows_to_dicts(rows, cols):
    """SQLite 行列表 -> 列名映射的 dict 列表。"""
    return [dict(zip(cols, r)) for r in rows]

@app.get("/api/records")
def list_records(limit: int = DEFAULT_RECORDS_LIMIT):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id, captured_at, title, votes, item_id FROM vote_records ORDER BY captured_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
    return _rows_to_dicts(rows, RECORD_COLS)

@app.get("/api/latest")
def latest():
    """每个候选人取最近一条记录，保证所有候选人都返回。"""
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(
            "SELECT title, votes, captured_at, item_id, is_my_vote "
            "FROM vote_records r "
            "WHERE captured_at = (SELECT MAX(captured_at) FROM vote_records r2 WHERE r2.title = r.title) "
            "ORDER BY title"
        )
        rows = cur.fetchall()
    return _rows_to_dicts(rows, LATEST_COLS)

def _series_to_json(rows_asc):
    """升序 (captured_at, votes) 行 -> 按时间戳去重后的 JSON 列表（每个时间戳保留第一条）。"""
    deduped = []
    seen = set()
    for r in rows_asc:
        if r[0] not in seen:
            seen.add(r[0])
            deduped.append(r)
    return [{"captured_at": r[0], "votes": r[1]} for r in deduped]

@app.get("/api/history")
def history(title: str, limit: int = DEFAULT_HISTORY_LIMIT):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT captured_at, votes FROM vote_records WHERE title=? ORDER BY captured_at DESC LIMIT ?", (title, limit))
        rows = cur.fetchall()
    return _series_to_json(rows[::-1])

@app.get("/api/range")
def range(title: str, start: str = '', end: str = ''):
    sql = "SELECT captured_at, votes FROM vote_records WHERE title=?"
    args = [title]
    if start:
        sql += " AND captured_at >= ?"
        args.append(start)
    if end:
        sql += " AND captured_at <= ?"
        args.append(end)
    sql += " ORDER BY captured_at ASC"
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute(sql, args)
        rows = cur.fetchall()
    return _series_to_json(rows)

def _last_series_point(title, before=None):
    """title 最近一条 (captured_at, votes)；before 给出时取该时刻之前最近一条。"""
    sql = "SELECT captured_at, votes FROM vote_records WHERE title=?"
    args = [title]
    if before is not None:
        sql += " AND captured_at <= ?"
        args.append(before)
    sql += " ORDER BY captured_at DESC LIMIT 1"
    with sqlite3.connect(DB_PATH) as con:
        return con.execute(sql, args).fetchone()

@app.get("/api/diff")
def diff(title: str):
    now = datetime.now(UTC8)
    result = {"title": title, "current": None, "intervals": {}}
    row = _last_series_point(title)
    if row:
        result["current"] = {"captured_at": row[0], "votes": row[1]}
    for key, delta in DIFF_INTERVALS.items():
        target = (now - delta).isoformat()
        prev = _last_series_point(title, before=target)
        if prev and row:
            result["intervals"][key] = {
                "captured_at": prev[0],
                "votes": prev[1],
                "delta": row[1] - prev[1],
            }
    return result

@app.get("/api/stats")
def stats():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT COUNT(*), COALESCE(MAX(votes),0), COALESCE(MIN(votes),0), COALESCE(AVG(votes),0) FROM vote_records")
        row = cur.fetchone()
        cur = con.execute("SELECT COUNT(DISTINCT title), MAX(captured_at), MIN(captured_at) FROM vote_records")
        meta = cur.fetchone()
    return {"count": row[0], "max_votes": row[1], "min_votes": row[2], "avg_votes": round(row[3], 2) if row[3] else 0, "candidates": meta[0], "latest_capture": meta[1], "first_capture": meta[2], "version": APP_VERSION}

@app.get("/api/trigger")
def trigger_once(username: str = Depends(admin_auth)):
    poll_and_save()
    return {"ok": True}

@app.get("/healthz")
def healthz():
    return {"ok": True, "version": APP_VERSION}

_GEO_CACHE = {}  # ip -> {"ts": int, "data": dict}

def _client_ip(request):
    """从 X-Forwarded-For 或直连地址解析客户端 IP。"""
    forwarded = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip()
    host = request.client.host if request.client else ""
    return forwarded or host.strip()

def _fetch_geo(ip):
    """调用 ipapi.co 查询 IP 归属地；失败时返回空字段。"""
    data = {"ip": ip, "country": "", "city": ""}
    try:
        r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=GEO_TIMEOUT)
        if r.status_code == 200:
            j = r.json()
            data.update({
                "ip": j.get("ip", ip),
                "country": j.get("country_name", ""),
                "city": j.get("city", ""),
            })
    except Exception as e:
        # geo 查询失败 → 返回空字段 (记录原因便于排障)
        print(f"⚠️ geo 查询失败 {ip}: {e}", file=sys.stderr)
    return data

def _geo_lookup(ip, now):
    """带 TTL 缓存的地理查询；缓存超限时整体清空。"""
    entry = _GEO_CACHE.get(ip)
    if entry and now - entry["ts"] <= GEO_CACHE_TTL:
        return dict(entry["data"])
    data = _fetch_geo(ip)
    _GEO_CACHE[ip] = {"ts": now, "data": dict(data)}
    if len(_GEO_CACHE) > GEO_CACHE_MAX:
        _GEO_CACHE.clear()
    return data

@app.get("/api/my-info")
def my_info(request: Request):
    ip = _client_ip(request)
    if not ip:
        return {"ip": "", "country": "", "city": ""}
    return _geo_lookup(ip, int(time.time()))

app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")


@app.middleware("http")
async def no_cache(request, call_next):
    """禁用浏览器缓存，确保用户始终拿到最新前端（避免 logic.js 等修复后 304 复用旧页）"""
    response = await call_next(request)
    path = request.url.path
    if path.endswith(".html") or path == "/":
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
        response.headers["Pragma"] = "no-cache"
        response.headers["Expires"] = "0"
    else:
        # 静态资源（js/css/png）允许短缓存 + 必须 revalidate
        response.headers.setdefault("Cache-Control", "no-cache")
    return response
