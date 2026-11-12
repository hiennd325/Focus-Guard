import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IPTABLES_CMD = os.environ.get("IPTABLES_CMD", "sudo iptables")
IPTABLES_CHAIN = os.environ.get("IPTABLES_CHAIN", "FOCUS_GUARD")
QUOTA_FILE = os.environ.get("QUOTA_PATH", os.path.join(BASE_DIR, "quota.json"))
TEMPLATE_FILE = os.path.join(BASE_DIR, "templates", "index.html")

DOMAINS = [
    "facebook.com",
    "www.facebook.com",
    "tiktok.com",
    "www.tiktok.com",
    "x.com",
]
