import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPTABLES_CMD = os.environ.get("IPTABLES_CMD", "sudo iptables")
IPTABLES_CHAIN = os.environ.get("IPTABLES_CHAIN", "FOCUS_GUARD")
IPSET_CMD = os.environ.get("IPSET_CMD", "sudo ipset")
IPSET_SET = os.environ.get("IPSET_SET", "focus_guard_blocked")
SYSLOG_TAG = "focus-guard"
QUOTA_FILE = os.environ.get("QUOTA_PATH", os.path.join(BASE_DIR, "quota.json"))
TEMPLATE_FILE = os.path.join(BASE_DIR, "templates", "index.html")

DOMAINS = [
    "facebook.com",
    "www.facebook.com",
    "tiktok.com",
    "www.tiktok.com",
    "x.com",
]
