from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import sqlite3
import json
import os
import re
from datetime import datetime, timezone, timedelta
import requests
from apscheduler.schedulers.background import BackgroundScheduler

DB_PATH = os.environ.get("DB_PATH", "/app/db/votes.db")
ADMIN_USER = os.environ.get("ADMIN_USER", "admin")
ADMIN_PASS = os.environ.get("ADMIN_PASS", "nekomini")
TARGET_URL = os.environ.get("TARGET_URL", "https://b23.tv/wDz5Xnc")
POLL_INTERVAL = int(os.environ.get("POLL_INTERVAL", "1"))
UTC8 = timezone(timedelta(hours=8))
Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)

CREATE_TABLE_SQL = "CREATE TABLE IF NOT EXISTS vote_records (id INTEGER PRIMARY KEY AUTOINCREMENT, captured_at DATETIME DEFAULT CURRENT_TIMESTAMP, title TEXT, votes INTEGER, item_id TEXT, is_my_vote INTEGER DEFAULT 0)"
CREATE_INDEX_SQL = "CREATE INDEX IF NOT EXISTS idx_vote_time ON vote_records(captured_at)"
CREATE_META_SQL = "CREATE TABLE IF NOT EXISTS meta (key TEXT PRIMARY KEY, value TEXT)"

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
        resp = requests.get(url, headers=HEADERS, timeout=20)
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
    try:
        r = requests.get(api, params={"vote_id": vote, "group_id": group, "activity_id": aid}, headers=HEADERS, timeout=15)
        print("[fetch] api status", r.status_code)
        if r.status_code != 200:
            return []
        payload = r.json()
        if payload.get("code") != 0:
            print("[fetch] api error", payload)
            return []
        items = payload.get("data", {}).get("items", [])
        out = []
        for it in items:
            info = it.get("item", {}) or {}
            out.append({
                "item_id": it.get("item_id"),
                "title": info.get("title") or "",
                "votes": it.get("vote"),
                "is_vote": int(it.get("is_vote") or 0),
                "user_vote": it.get("user_vote", 0),
            })
        if out:
            set_meta("activity_id", aid)
            set_meta("group_id", group)
            set_meta("vote_id", vote)
        # poll_and_save persists after fetch_votes returns
        return out
    except Exception as e:
        print("[fetch] exception:", e)
    return []

def poll_and_save():
    rows = fetch_votes(TARGET_URL)
    if not rows:
        print("[poll] no rows")
        return
    now = datetime.now(UTC8).isoformat()
    with sqlite3.connect(DB_PATH) as con:
        for row in rows:
            con.execute("INSERT OR IGNORE INTO vote_records(captured_at, title, votes, item_id, is_my_vote) VALUES(?,?,?,?,?)",
                (now, row["title"], row["votes"], row["item_id"], row["is_vote"]))
    print(f"[poll] saved {len(rows)} candidates at {now}")

def get_or_create_job():
    job_id = "bili_vote_job"
    scheduler = BackgroundScheduler()
    try:
        job = scheduler.get_job(job_id)
        if job:
            job.remove()
    except Exception:
        pass
    scheduler.add_job(poll_and_save, "interval", minutes=POLL_INTERVAL, next_run_time=datetime.now(UTC8), id=job_id)
    scheduler.start()
    return scheduler

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

@app.get("/api/config")
def config(username: str = Depends(admin_auth)):
    return {
        "target_url": TARGET_URL,
        "poll_interval": POLL_INTERVAL,
        "activity_id": get_meta("activity_id"),
        "group_id": get_meta("group_id"),
        "vote_id": get_meta("vote_id"),
    }

@app.post("/api/config")
def update_config(payload: dict, username: str = Depends(admin_auth)):
    global TARGET_URL, POLL_INTERVAL
    TARGET_URL = payload.get("target_url", TARGET_URL)
    POLL_INTERVAL = int(payload.get("poll_interval", POLL_INTERVAL))
    set_meta("target_url", TARGET_URL)
    set_meta("poll_interval", POLL_INTERVAL)
    get_or_create_job()
    return {"ok": True, "target_url": TARGET_URL, "poll_interval": POLL_INTERVAL}

@app.get("/api/records")
def list_records(limit: int = 200):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT id, captured_at, title, votes, item_id FROM vote_records ORDER BY captured_at DESC LIMIT ?", (limit,))
        rows = cur.fetchall()
    cols = ["id","captured_at","title","votes","item_id"]
    return [dict(zip(cols, r)) for r in rows]

@app.get("/api/latest")
def latest():
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT title, votes, captured_at, item_id, is_my_vote FROM vote_records ORDER BY captured_at DESC LIMIT 100")
        rows = cur.fetchall()
    out = {}
    for r in rows:
        title, votes, ts, item_id, is_my_vote = r
        if title not in out:
            out[title] = {"title": title, "votes": votes, "captured_at": ts, "item_id": item_id, "is_my_vote": is_my_vote}
    return list(out.values())

@app.get("/api/history")
def history(title: str, limit: int = 300):
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT captured_at, votes FROM vote_records WHERE title=? ORDER BY captured_at DESC LIMIT ?", (title, limit))
        rows = cur.fetchall()
    rows = rows[::-1]
    deduped = []
    seen = set()
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            deduped.append(r)
    return [{"captured_at": r[0], "votes": r[1]} for r in deduped]

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
    deduped = []
    seen = set()
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0])
            deduped.append(r)
    return [{"captured_at": r[0], "votes": r[1]} for r in deduped]

@app.get("/api/diff")
def diff(title: str):
    now = datetime.now(UTC8)
    intervals = {
        "1m": timedelta(minutes=1),
        "5m": timedelta(minutes=5),
        "30m": timedelta(minutes=30),
        "6h": timedelta(hours=6),
        "24h": timedelta(hours=24),
    }
    result = {"title": title, "current": None, "intervals": {}}
    with sqlite3.connect(DB_PATH) as con:
        cur = con.execute("SELECT captured_at, votes FROM vote_records WHERE title=? ORDER BY captured_at DESC LIMIT 1", (title,))
        row = cur.fetchone()
        if row:
            result["current"] = {"captured_at": row[0], "votes": row[1]}
        for key, delta in intervals.items():
            target = (now - delta).isoformat()
            cur = con.execute("SELECT captured_at, votes FROM vote_records WHERE title=? AND captured_at <= ? ORDER BY captured_at DESC LIMIT 1", (title, target))
            prev = cur.fetchone()
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
    return {"count": row[0], "max_votes": row[1], "min_votes": row[2], "avg_votes": round(row[3], 2) if row[3] else 0, "candidates": meta[0], "latest_capture": meta[1], "first_capture": meta[2]}

@app.get("/api/trigger")
def trigger_once(username: str = Depends(admin_auth)):
    poll_and_save()
    return {"ok": True}

@app.get("/healthz")
def healthz():
    return {"ok": True}

_CACHE_GEO = {"ts": 0, "data": {}}
_SUCCESS_RESPONSE = {"ok": True}

@app.get("/api/my-info")
def my_info(request: Request):
    ip = (request.headers.get("X-Forwarded-For") or "").split(",")[0].strip() or (request.client.host if request.client else "")
    ip = (ip or "").strip()
    now = int(time.time())
    data = dict(_CACHE_GEO["data"])
    if not ip:
        data.update({"ip": "", "country": "", "city": ""})
        return data
    if data.get("ip") != ip or now - _CACHE_GEO["ts"] > 60:
        try:
            r = requests.get(f"https://ipapi.co/{ip}/json/", timeout=5)
            if r.status_code == 200:
                j = r.json()
                data.update({
                    "ip": j.get("ip", ip),
                    "country": j.get("country_name", ""),
                    "city": j.get("city", ""),
                })
            else:
                data.update({"ip": ip, "country": "", "city": ""})
        except Exception:
            data.update({"ip": ip, "country": "", "city": ""})
        _CACHE_GEO["ts"] = now
        _CACHE_GEO["data"] = dict(data)
    return data

app.mount("/", StaticFiles(directory="/app/frontend", html=True), name="frontend")
