import os
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "crash_debug.log")

def log(msg):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        ts = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        f.write(f"[{ts}] {msg}\n")
