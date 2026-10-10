import datetime
import json
import os
import time
from . import config

last_quota_mtime = 0
quota_state = {"date": "", "used": 0, "limit": 3600, "history": {}}

def get_quota(quota_file=None):
    global last_quota_mtime
    path = quota_file or config.QUOTA_FILE
    today = time.strftime("%Y-%m-%d")
    if os.path.exists(path):
        try:
            mtime = os.path.getmtime(path)
            if mtime > last_quota_mtime:
                with open(path) as f:
                    d = json.load(f)
                    quota_state["date"] = d.get("date", today)
                    quota_state["used"] = d.get("used", 0) if quota_state["date"] == today else 0
                    quota_state["limit"] = d.get("limit", 3600)
                    quota_state["history"] = d.get("history", {})
                    last_quota_mtime = mtime
        except Exception:
            pass
    if quota_state["date"] != today:
        quota_state["date"] = today
        quota_state["used"] = 0
        save_quota(path)
    if "history" not in quota_state:
        quota_state["history"] = {}
    quota_state["history"][today] = quota_state["used"]
    return quota_state

def save_quota(quota_file=None):
    global last_quota_mtime
    path = quota_file or config.QUOTA_FILE
    try:
        today = quota_state.get("date", time.strftime("%Y-%m-%d"))
        if "history" not in quota_state:
            quota_state["history"] = {}
        quota_state["history"][today] = quota_state["used"]
        with open(path, "w") as f:
            json.dump(quota_state, f)
        last_quota_mtime = os.path.getmtime(path)
    except Exception:
        pass

def render_heatmap(history, today_str):
    try:
        today = datetime.date.fromisoformat(today_str)
    except Exception:
        today = datetime.date.today()
    start = today - datetime.timedelta(days=19 * 7 + today.weekday())
    end = today + datetime.timedelta(days=6 - today.weekday())

    active_days = 0
    total_sec = 0
    cells = []
    curr = start
    while curr <= end:
        ds = curr.isoformat()
        if curr > today:
            cells.append('<div class="hm-cell hm-future"></div>')
        else:
            sec = history.get(ds, 0)
            m = sec // 60
            if sec > 0:
                active_days += 1
                total_sec += sec
            lvl = 0 if m == 0 else (1 if m < 15 else (2 if m < 45 else 3))
            cells.append(f'<div class="hm-cell hm-lvl-{lvl}" title="{ds}: {m} phút"></div>')
        curr += datetime.timedelta(days=1)
    return active_days, total_sec // 60, "".join(cells)
