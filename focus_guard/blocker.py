import time
from . import config
from . import quota

timer_end = 0

def is_blocked(hosts_file=None):
    path = hosts_file or config.HOSTS_FILE
    try:
        with open(path, "r") as f:
            content = f.read()
        return all(f"127.0.0.1 {d}" in content for d in config.DOMAINS)
    except Exception:
        return False

def set_block(block=True, hosts_file=None):
    global timer_end
    if block:
        timer_end = 0
    path = hosts_file or config.HOSTS_FILE
    try:
        with open(path, "r") as f:
            lines = [line for line in f.readlines() if not any(d in line for d in config.DOMAINS)]
    except FileNotFoundError:
        lines = []
    if block:
        for d in config.DOMAINS:
            lines.append(f"127.0.0.1 {d}\n")
    with open(path, "w") as f:
        f.writelines(lines)

def start_timer(minutes):
    global timer_end
    q = quota.get_quota()
    remain_quota = max(0, q["limit"] - q["used"])
    if remain_quota <= 0:
        set_block(True)
        return
    allowed_sec = min(minutes * 60, remain_quota)
    set_block(False)
    timer_end = time.time() + allowed_sec
