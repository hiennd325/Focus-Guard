#!/usr/bin/env python3
import http.server
import json
import os
import sys
import threading
import time
from urllib.parse import parse_qs

HOSTS_FILE = os.environ.get("HOSTS_PATH", "/etc/hosts")
QUOTA_FILE = os.environ.get("QUOTA_PATH", os.path.join(os.path.dirname(__file__), "quota.json"))
DOMAINS = ["facebook.com", "www.facebook.com", "tiktok.com", "www.tiktok.com", "x.com", "youtube.com", "www.youtube.com"]

timer_end = 0
last_quota_mtime = 0
quota_state = {"date": "", "used": 0, "limit": 3600}  # limit mặc định 60 phút

def get_quota():
    global last_quota_mtime
    today = time.strftime("%Y-%m-%d")
    if os.path.exists(QUOTA_FILE):
        try:
            mtime = os.path.getmtime(QUOTA_FILE)
            if mtime > last_quota_mtime:
                with open(QUOTA_FILE) as f:
                    d = json.load(f)
                    quota_state["date"] = d.get("date", today)
                    quota_state["used"] = d.get("used", 0) if quota_state["date"] == today else 0
                    quota_state["limit"] = d.get("limit", 3600)
                    last_quota_mtime = mtime
        except Exception:
            pass
    if quota_state["date"] != today:
        quota_state["date"] = today
        quota_state["used"] = 0
        save_quota()
    return quota_state

def save_quota():
    global last_quota_mtime
    try:
        with open(QUOTA_FILE, "w") as f:
            json.dump(quota_state, f)
        last_quota_mtime = os.path.getmtime(QUOTA_FILE)
    except Exception:
        pass

def is_blocked():
    try:
        with open(HOSTS_FILE, "r") as f:
            content = f.read()
        return all(f"127.0.0.1 {d}" in content for d in DOMAINS)
    except Exception:
        return False

def set_block(block=True):
    global timer_end
    if block:
        timer_end = 0
    with open(HOSTS_FILE, "r") as f:
        lines = [line for line in f.readlines() if not any(d in line for d in DOMAINS)]
    if block:
        for d in DOMAINS:
            lines.append(f"127.0.0.1 {d}\n")
    with open(HOSTS_FILE, "w") as f:
        f.writelines(lines)

def start_timer(minutes):
    global timer_end
    q = get_quota()
    remain_quota = max(0, q["limit"] - q["used"])
    if remain_quota <= 0:
        set_block(True)
        return
    allowed_sec = min(minutes * 60, remain_quota)
    set_block(False)
    timer_end = time.time() + allowed_sec

# ponytail: monitor dùng thread vòng lặp 1s; nâng cấp eBPF/nftables cgroup nếu muốn đếm dung lượng mạng thay vì chỉ thời gian
def quota_monitor():
    last_save = time.time()
    while True:
        time.sleep(1)
        if not is_blocked():
            q = get_quota()
            q["used"] += 1
            if q["used"] >= q["limit"]:
                set_block(True)
            if time.time() - last_save >= 5 or q["used"] >= q["limit"]:
                save_quota()
                last_save = time.time()
        elif timer_end > 0 and time.time() >= timer_end:
            set_block(True)

HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Focus Guard | Giới Hạn Mạng Xã Hội</title>
<style>
:root {
  --bg: #0b0f19;
  --card: #131b2e;
  --card-border: #1e293b;
  --text: #f8fafc;
  --muted: #94a3b8;
  --emerald: #10b981;
  --emerald-bg: #064e3b33;
  --emerald-border: #059669;
  --rose: #f43f5e;
  --rose-bg: #88133733;
  --rose-border: #e11d48;
  --blue: #3b82f6;
  --blue-bg: #1e3a8a33;
}
* { box-sizing: border-box; margin: 0; padding: 0; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  background-color: var(--bg);
  color: var(--text);
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  padding: 24px 16px;
}
.container {
  width: 100%;
  max-width: 460px;
  background: var(--card);
  border: 1px solid var(--card-border);
  border-radius: 16px;
  padding: 28px 24px;
  box-shadow: 0 20px 40px rgba(0,0,0,0.45);
}
.header { text-align: center; margin-bottom: 24px; }
.header h1 { font-size: 22px; font-weight: 700; letter-spacing: -0.5px; }
.header p { color: var(--muted); font-size: 13px; margin-top: 4px; }

/* Status Banner */
.status-card {
  border-radius: 12px;
  padding: 18px;
  text-align: center;
  margin-bottom: 20px;
  border: 1px solid transparent;
  transition: all 0.2s ease;
}
.status-card.blocked {
  background: var(--emerald-bg);
  border-color: var(--emerald-border);
  color: #a7f3d0;
}
.status-card.unblocked {
  background: var(--rose-bg);
  border-color: var(--rose-border);
  color: #fecdd3;
}
.status-badge {
  display: inline-block;
  font-size: 11px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 1px;
  padding: 4px 10px;
  border-radius: 20px;
  margin-bottom: 8px;
  background: rgba(0,0,0,0.3);
}
.status-title { font-size: 20px; font-weight: 800; }
.status-desc { font-size: 13px; margin-top: 4px; opacity: 0.9; }
.timer-countdown { font-size: 28px; font-weight: 800; font-variant-numeric: tabular-nums; margin-top: 6px; }

/* Quota meter */
.quota-section {
  background: rgba(15, 23, 42, 0.6);
  border: 1px solid var(--card-border);
  border-radius: 12px;
  padding: 16px;
  margin-bottom: 22px;
}
.quota-header {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  margin-bottom: 8px;
}
.quota-header span:first-child { color: var(--muted); }
.quota-header span:last-child { font-weight: 600; }
.progress-bar-bg {
  width: 100%;
  height: 8px;
  background: #1e293b;
  border-radius: 4px;
  overflow: hidden;
}
.progress-bar-fill {
  height: 100%;
  background: linear-gradient(90deg, #3b82f6, #ec4899);
  border-radius: 4px;
  transition: width 0.3s ease;
}
.progress-bar-fill.danger { background: var(--rose); }
.quota-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: var(--muted);
  margin-top: 6px;
}

/* Actions */
.btn-primary-focus {
  width: 100%;
  padding: 14px;
  background: #059669;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 15px;
  font-weight: 700;
  cursor: pointer;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 8px;
  margin-bottom: 16px;
  transition: background 0.15s;
}
.btn-primary-focus:hover { background: #047857; }

.section-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: var(--muted);
  margin-bottom: 10px;
}
.break-buttons {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
  margin-bottom: 12px;
}
.btn-break {
  padding: 10px 6px;
  background: #1e293b;
  color: var(--text);
  border: 1px solid #334155;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.15s;
}
.btn-break:hover:not(:disabled) { background: #334155; border-color: #475569; }
.btn-break:disabled, .btn-secondary:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}
.btn-secondary {
  width: 100%;
  padding: 10px;
  background: transparent;
  color: var(--muted);
  border: 1px solid #334155;
  border-radius: 8px;
  font-size: 13px;
  cursor: pointer;
  margin-bottom: 20px;
  transition: color 0.15s, border-color 0.15s;
}
.btn-secondary:hover:not(:disabled) { color: var(--text); border-color: #64748b; }

/* Quota Setting Form */
.settings-box {
  border-top: 1px solid var(--card-border);
  padding-top: 16px;
  margin-top: 8px;
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.settings-box label { font-size: 13px; color: var(--muted); }
.settings-input-group { display: flex; gap: 6px; }
.settings-input-group input {
  width: 70px;
  background: #0f172a;
  border: 1px solid #334155;
  color: var(--text);
  border-radius: 6px;
  padding: 6px 8px;
  font-size: 13px;
  text-align: center;
}
.btn-save {
  padding: 6px 12px;
  background: #2563eb;
  color: #fff;
  border: none;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
}
.btn-save:hover { background: #1d4ed8; }

/* Tags */
.domains-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-top: 16px;
  justify-content: center;
}
.domain-tag {
  background: #0f172a;
  border: 1px solid #1e293b;
  color: #64748b;
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 4px;
}
</style>
</head>
<body>

<div class="container">
  <div class="header">
    <h1>Focus Guard</h1>
    <p>Kiểm soát mạng xã hội & Tối đa tập trung</p>
  </div>

  <div class="status-card __CLS__">
    <div class="status-badge">Trạng thái: __STATUS_LABEL__</div>
    <div class="status-title">__STATUS_TITLE__</div>
    <div class="status-desc" id="status-desc">__STATUS_DESC__</div>
    <div class="timer-countdown" id="timer-display" style="display: __SHOW_TIMER__;">__TIMER_STR__</div>
  </div>

  <div class="quota-section">
    <div class="quota-header">
      <span>Hạn mức hôm nay</span>
      <span>__USED__ / __LIMIT__ phút</span>
    </div>
    <div class="progress-bar-bg">
      <div class="progress-bar-fill __BAR_CLS__" style="width: __PERCENT__%;"></div>
    </div>
    <div class="quota-footer">
      <span>Đã dùng __PERCENT__%</span>
      <span>Còn lại __REMAIN__ phút</span>
    </div>
  </div>

  <form method="POST" action="/action">
    <button class="btn-primary-focus" name="act" value="block">
      Bật Tập Trung (Chặn ngay)
    </button>

    <div class="section-label">Giải lao có hẹn giờ</div>
    <div class="break-buttons">
      <button class="btn-break" name="act" value="timer_5" __DISABLED__>5 phút</button>
      <button class="btn-break" name="act" value="timer_15" __DISABLED__>15 phút</button>
      <button class="btn-break" name="act" value="timer_25" __DISABLED__>25 phút</button>
    </div>

    <button class="btn-secondary" name="act" value="unblock" __DISABLED__>
      Mở không hẹn giờ
    </button>

    <div class="settings-box">
      <label for="limit_min">Hạn mức ngày (phút):</label>
      <div class="settings-input-group">
        <input type="number" id="limit_min" name="limit_min" value="__LIMIT__" min="1" max="1440">
        <button class="btn-save" name="act" value="set_limit">Lưu</button>
      </div>
    </div>
  </form>

  <div class="domains-list">
    __DOMAINS_HTML__
  </div>
</div>

<script>
// Live JS countdown without full page refresh
let secondsLeft = __REM_SECONDS__;
const timerEl = document.getElementById("timer-display");
if (secondsLeft > 0 && timerEl) {
  const interval = setInterval(() => {
    secondsLeft--;
    if (secondsLeft <= 0) {
      clearInterval(interval);
      location.reload();
    } else {
      const m = Math.floor(secondsLeft / 60);
      const s = secondsLeft % 60;
      timerEl.textContent = (m < 10 ? '0' : '') + m + ':' + (s < 10 ? '0' : '') + s;
    }
  }, 1000);
}
</script>
</body>
</html>"""

class Handler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        blocked = is_blocked()
        q = get_quota()
        rem_sec = max(0, q["limit"] - q["used"])
        is_exhausted = rem_sec <= 0
        rem_timer = max(0, int(timer_end - time.time()))

        limit_min = max(1, q["limit"] // 60)
        used_min = q["used"] // 60
        remain_min = rem_sec // 60
        percent = min(100, int((q["used"] / q["limit"]) * 100)) if q["limit"] > 0 else 100

        if blocked:
            cls = "blocked"
            status_label = "ĐANG CHẶN"
            status_title = "Đang Tập Trung"
            status_desc = "Toàn bộ mạng xã hội đã bị chặn qua /etc/hosts."
            show_timer = "none"
            timer_str = "00:00"
        elif rem_timer > 0:
            cls = "unblocked"
            status_label = "MỞ TẠM THỜI"
            status_title = "Đang Giải Lao"
            status_desc = "Tự động kích hoạt lại chế độ tập trung khi hết giờ:"
            show_timer = "block"
            m = rem_timer // 60
            s = rem_timer % 60
            timer_str = f"{m:02d}:{s:02d}"
        else:
            cls = "unblocked"
            status_label = "ĐANG MỞ"
            status_title = "Mạng Xã Hội Đang Mở"
            status_desc = "Thời gian sử dụng đang được tính vào hạn mức ngày."
            show_timer = "none"
            timer_str = "00:00"

        if is_exhausted:
            status_label = "HẾT HẠN MỨC HÔM NAY"
            status_desc = "Bạn đã dùng hết hạn mức trong ngày. Hãy tập trung học tập!"

        bar_cls = "danger" if (percent >= 90 or is_exhausted) else ""
        domains_html = "".join(f'<span class="domain-tag">{d}</span>' for d in DOMAINS)

        body = (HTML.replace("__CLS__", cls)
                    .replace("__STATUS_LABEL__", status_label)
                    .replace("__STATUS_TITLE__", status_title)
                    .replace("__STATUS_DESC__", status_desc)
                    .replace("__SHOW_TIMER__", show_timer)
                    .replace("__TIMER_STR__", timer_str)
                    .replace("__REM_SECONDS__", str(rem_timer))
                    .replace("__USED__", str(used_min))
                    .replace("__LIMIT__", str(limit_min))
                    .replace("__REMAIN__", str(remain_min))
                    .replace("__PERCENT__", str(percent))
                    .replace("__BAR_CLS__", bar_cls)
                    .replace("__DISABLED__", "disabled" if is_exhausted else "")
                    .replace("__DOMAINS_HTML__", domains_html)
                    .encode("utf-8"))

        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        data = parse_qs(self.rfile.read(length).decode("utf-8"))
        act = data.get("act", [""])[0]
        q = get_quota()

        if act == "block":
            set_block(True)
        elif act == "unblock":
            if q["used"] < q["limit"]:
                set_block(False)
        elif act.startswith("timer_"):
            start_timer(int(act.split("_")[1]))
        elif act == "set_limit":
            try:
                new_limit = int(data.get("limit_min", [60])[0])
                q["limit"] = max(1, new_limit) * 60
                save_quota()
            except ValueError:
                pass

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()

if __name__ == "__main__":
    if "--test" in sys.argv:
        test_hosts = "/tmp/test_hosts"
        test_quota = "/tmp/test_quota.json"
        HOSTS_FILE = test_hosts
        QUOTA_FILE = test_quota
        with open(test_hosts, "w") as f:
            f.write("127.0.0.1 localhost\n")

        # 1. Quota initialization
        q = get_quota()
        assert q["used"] == 0
        q["limit"] = 10  # 10s limit
        save_quota()

        # 2. Check persistence
        with open(test_quota) as f:
            saved = json.load(f)
            assert saved["limit"] == 10

        # 3. Simulate usage and auto-block
        set_block(False)
        assert not is_blocked()
        q["used"] = 10
        if q["used"] >= q["limit"]:
            set_block(True)
        assert is_blocked()

        # Clean
        if os.path.exists(test_hosts): os.remove(test_hosts)
        if os.path.exists(test_quota): os.remove(test_quota)
        print("Self-check OK")
        sys.exit(0)

    get_quota()
    threading.Thread(target=quota_monitor, daemon=True).start()
    server = http.server.HTTPServer(("127.0.0.1", 8080), Handler)
    print("Mở browser: http://127.0.0.1:8080")
    server.serve_forever()
