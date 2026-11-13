import http.server
import time
from urllib.parse import parse_qs
from . import blocker
from . import config
from . import quota

_template_cache = None

def get_template():
    global _template_cache
    if _template_cache is None:
        with open(config.TEMPLATE_FILE, "r", encoding="utf-8") as f:
            _template_cache = f.read()
    return _template_cache

class FocusGuardHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/metrics":
            blocked_val = 1 if blocker.is_blocked() else 0
            q = quota.get_quota()
            metrics = (
                f"# HELP focus_guard_blocked Current block status (1=blocked, 0=unblocked)\n"
                f"# TYPE focus_guard_blocked gauge\n"
                f"focus_guard_blocked {blocked_val}\n"
                f"# HELP focus_guard_quota_used_seconds Total quota used today in seconds\n"
                f"# TYPE focus_guard_quota_used_seconds gauge\n"
                f"focus_guard_quota_used_seconds {q['used']}\n"
                f"# HELP focus_guard_quota_limit_seconds Daily quota limit in seconds\n"
                f"# TYPE focus_guard_quota_limit_seconds gauge\n"
                f"focus_guard_quota_limit_seconds {q['limit']}\n"
                f"# HELP focus_guard_monitored_domains_count Number of configured domains\n"
                f"# TYPE focus_guard_monitored_domains_count gauge\n"
                f"focus_guard_monitored_domains_count {len(config.DOMAINS)}\n"
            ).encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4; charset=utf-8")
            self.send_header("Content-Length", str(len(metrics)))
            self.end_headers()
            self.wfile.write(metrics)
            return

        blocked = blocker.is_blocked()
        q = quota.get_quota()
        rem_sec = max(0, q["limit"] - q["used"])
        is_exhausted = rem_sec <= 0
        rem_timer = max(0, int(blocker.timer_end - time.time()))

        limit_min = max(1, q["limit"] // 60)
        used_min = q["used"] // 60
        remain_min = rem_sec // 60
        percent = min(100, int((q["used"] / q["limit"]) * 100)) if q["limit"] > 0 else 100

        if blocked:
            cls = "blocked"
            status_title = "Đang chặn"
            show_timer = "none"
            timer_str = "00:00"
        elif rem_timer > 0:
            cls = "unblocked"
            status_title = "Giải lao"
            show_timer = "block"
            m = rem_timer // 60
            s = rem_timer % 60
            timer_str = f"{m:02d}:{s:02d}"
        else:
            cls = "unblocked"
            status_title = "Đang mở"
            show_timer = "none"
            timer_str = "00:00"

        if is_exhausted:
            cls = "blocked"
            status_title = "Hết hạn mức"

        bar_cls = "danger" if (percent >= 90 or is_exhausted) else ""
        domains_html = "".join(f'<span class="domain-tag">{d}</span>' for d in config.DOMAINS)
        active_days, total_mins, heatmap_cells = quota.render_heatmap(q.get("history", {}), q["date"])

        template = get_template()
        body = (template.replace("__CLS__", cls)
                        .replace("__STATUS_TITLE__", status_title)
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
                        .replace("__ACTIVE_DAYS__", str(active_days))
                        .replace("__TOTAL_MINS__", str(total_mins))
                        .replace("__HEATMAP_CELLS__", heatmap_cells)
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
        q = quota.get_quota()

        if act == "block":
            blocker.set_block(True)
        elif act == "unblock":
            if q["used"] < q["limit"]:
                blocker.set_block(False)
        elif act.startswith("timer_"):
            blocker.start_timer(int(act.split("_")[1]))
        elif act == "set_limit":
            try:
                new_limit = int(data.get("limit_min", [60])[0])
                q["limit"] = max(1, new_limit) * 60
                quota.save_quota()
            except ValueError:
                pass

        self.send_response(303)
        self.send_header("Location", "/")
        self.end_headers()
