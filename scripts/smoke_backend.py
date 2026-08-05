"""Quick stdin/stdout smoke test for backend/main.py"""
import json
import subprocess
import sys
import time

proc = subprocess.Popen(
    [sys.executable, "backend/main.py"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=subprocess.PIPE,
    text=True,
    cwd=r"d:\buff-timer-app",
    bufsize=1,
)

time.sleep(0.8)
proc.stdin.write(json.dumps({"type": "set_region", "x": 0, "y": 0, "width": 80, "height": 80}) + "\n")
proc.stdin.flush()

# wait for one JSON line (timeout)
deadline = time.time() + 5
line = None
while time.time() < deadline:
    # non-blocking-ish: poll with short select via readline timeout not available;
    # use communicate with timeout after a short sleep if needed
    if proc.poll() is not None:
        break
    # try reading with a short wait by peeking via threads is complex; sleep and read
    time.sleep(0.5)
    # Use a thread to read one line
    import threading
    holder = {"line": None}

    def reader():
        holder["line"] = proc.stdout.readline()

    t = threading.Thread(target=reader, daemon=True)
    t.start()
    t.join(3)
    if holder["line"]:
        line = holder["line"].strip()
        break

stderr_snip = ""
try:
    proc.kill()
except Exception:
    pass

# drain stderr briefly
try:
    import threading as th
    err_holder = {"data": ""}

    def err_reader():
        err_holder["data"] = proc.stderr.read()

    et = th.Thread(target=err_reader, daemon=True)
    et.start()
    et.join(1)
    stderr_snip = err_holder["data"][:500]
except Exception:
    pass

print("LINE:", line)
print("STDERR:", stderr_snip)
if line:
    data = json.loads(line)
    assert "buffs" in data
    print("SMOKE_OK")
else:
    print("SMOKE_FAIL_NO_OUTPUT")
    sys.exit(1)
