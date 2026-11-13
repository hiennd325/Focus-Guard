import logging
import shlex
import socket
import subprocess
import time

from . import config
from . import quota

logger = logging.getLogger(config.SYSLOG_TAG)
timer_end = 0

def _run(args):
    cmd = shlex.split(config.IPTABLES_CMD) + args
    return subprocess.run(cmd, capture_output=True, text=True)

def _run_ipset(args):
    cmd = shlex.split(config.IPSET_CMD) + args
    return subprocess.run(cmd, capture_output=True, text=True)

def has_ipset():
    # ponytail: cache kết quả nếu không muốn gọi subprocess kiểm tra tool ipset mỗi lần block
    return _run_ipset(["-v"]).returncode == 0

def resolve_domains(domains):
    ips = set()
    for d in domains:
        try:
            for res in socket.getaddrinfo(d, None, socket.AF_INET):
                ips.add(res[4][0])
        except socket.gaierror:
            pass
    return sorted(ips)

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

    if not block:
        logger.info("Traffic unblocked")
        return

    ips = resolve_domains(config.DOMAINS)
    if has_ipset():
        _run_ipset(["create", config.IPSET_SET, "hash:ip", "-exist"])
        _run_ipset(["flush", config.IPSET_SET])
        for ip in ips:
            _run_ipset(["add", config.IPSET_SET, ip, "-exist"])
        _run(["-A", config.IPTABLES_CHAIN, "-m", "set", "--match-set", config.IPSET_SET, "dst", "-j", "REJECT"])
        logger.info("Traffic blocked via ipset (%d IPs)", len(ips))
    else:
        # Fallback to direct iptables rules
        targets = ips if ips else config.DOMAINS
        for t in targets:
            _run(["-A", config.IPTABLES_CHAIN, "-d", t, "-j", "REJECT"])
        logger.info("Traffic blocked via iptables rules (%d targets)", len(targets))

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
    logger.info("Timer started: %d seconds allowed", allowed_sec)
