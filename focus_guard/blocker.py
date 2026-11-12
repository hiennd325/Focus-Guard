import shlex
import subprocess
import time

from . import config
from . import quota

timer_end = 0

def _run(args):
    cmd = shlex.split(config.IPTABLES_CMD) + args
    return subprocess.run(cmd, capture_output=True, text=True)

def _ensure_chain():
    _run(["-N", config.IPTABLES_CHAIN])
    if _run(["-C", "OUTPUT", "-j", config.IPTABLES_CHAIN]).returncode != 0:
        _run(["-I", "OUTPUT", "1", "-j", config.IPTABLES_CHAIN])

def is_blocked():
    res = _run(["-S", config.IPTABLES_CHAIN])
    return res.returncode == 0 and f"-A {config.IPTABLES_CHAIN}" in res.stdout

def set_block(block=True):
    global timer_end
    if block:
        timer_end = 0
    _ensure_chain()
    _run(["-F", config.IPTABLES_CHAIN])
    # ponytail: resolve domain to IP at rule insertion, upgrade to ipset if domain IPs change often
    if block:
        for d in config.DOMAINS:
            _run(["-A", config.IPTABLES_CHAIN, "-d", d, "-j", "REJECT"])

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
