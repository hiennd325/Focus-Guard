#!/usr/bin/env python3
import http.server
import json
import os
import sys
import threading

from focus_guard import blocker, config, monitor, quota
from focus_guard.web import FocusGuardHandler

def run_tests():
    test_quota = "/tmp/test_quota.json"
    config.QUOTA_FILE = test_quota

    state = {"rules": set(), "output_linked": False}
    class MockProcess:
        def __init__(self, stdout="", returncode=0):
            self.stdout = stdout
            self.returncode = returncode

    def mock_run(cmd, capture_output=True, text=True):
        import shlex
        args = cmd[len(shlex.split(config.IPTABLES_CMD)):]
        action = args[0]
        if action == "-N":
            return MockProcess()
        if action == "-C":
            return MockProcess(returncode=0 if state["output_linked"] else 1)
        if action == "-I":
            state["output_linked"] = True
            return MockProcess()
        if action == "-F":
            state["rules"].clear()
            return MockProcess()
        if action == "-A":
            state["rules"].add(tuple(args))
            return MockProcess()
        if action == "-S":
            out = "\n".join(f"-A {config.IPTABLES_CHAIN} " + " ".join(r[1:]) for r in state["rules"])
            return MockProcess(stdout=out)
        return MockProcess()

    import subprocess
    orig_run = subprocess.run
    subprocess.run = mock_run

    try:
        # 1. Quota initialization
        q = quota.get_quota()
        assert q["used"] == 0
        q["limit"] = 10
        quota.save_quota()

        # 2. Check persistence
        with open(test_quota) as f:
            saved = json.load(f)
            assert saved["limit"] == 10

        # 3. Simulate usage and auto-block
        blocker.set_block(False)
        assert not blocker.is_blocked()
        q["used"] = 10
        if q["used"] >= q["limit"]:
            blocker.set_block(True)
        assert blocker.is_blocked()

        # 4. Check heatmap logic
        hist = {"2026-10-09": 1200, "2026-10-10": 600}
        act_days, tot_mins, cells_html = quota.render_heatmap(hist, "2026-10-10")
        assert act_days == 2
        assert tot_mins == 30
        assert "hm-lvl-1" in cells_html
        assert "hm-lvl-2" in cells_html

        print("Self-check OK")
    finally:
        subprocess.run = orig_run
        if os.path.exists(test_quota):
            os.remove(test_quota)

def main():
    if "--test" in sys.argv:
        run_tests()
        sys.exit(0)

    quota.get_quota()
    threading.Thread(target=monitor.quota_monitor, daemon=True).start()
    server = http.server.HTTPServer(("127.0.0.1", 8080), FocusGuardHandler)
    print("Mở browser: http://127.0.0.1:8080")
    server.serve_forever()

if __name__ == "__main__":
    main()
