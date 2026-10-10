import os

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOSTS_FILE = os.environ.get("HOSTS_PATH", "/etc/hosts")
QUOTA_FILE = os.environ.get("QUOTA_PATH", os.path.join(BASE_DIR, "quota.json"))
TEMPLATE_FILE = os.path.join(BASE_DIR, "templates", "index.html")

DOMAINS = [
    "facebook.com",
    "www.facebook.com",
    "tiktok.com",
    "www.tiktok.com",
    "x.com",
    "youtube.com",
    "www.youtube.com",
]
