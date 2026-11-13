import logging
import time
from . import blocker
from . import config
from . import quota

logger = logging.getLogger(config.SYSLOG_TAG)

# ponytail: monitor dùng thread vòng lặp 1s; nâng cấp eBPF/nftables cgroup nếu muốn đếm dung lượng mạng thay vì chỉ thời gian
def quota_monitor():
    last_save = time.time()
    while True:
        time.sleep(1)
        if not blocker.is_blocked():
            q = quota.get_quota()
            q["used"] += 1
            if q["used"] >= q["limit"]:
                logger.warning("Daily quota reached: %d/%d sec. Auto-blocking.", q["used"], q["limit"])
                blocker.set_block(True)
            if time.time() - last_save >= 5 or q["used"] >= q["limit"]:
                quota.save_quota()
                last_save = time.time()
        elif blocker.timer_end > 0 and time.time() >= blocker.timer_end:
            logger.info("Timer expired. Re-blocking.")
            blocker.set_block(True)
