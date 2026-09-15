import datetime
import json
from pathlib import Path
import subprocess
import time

BASE = Path(__file__).resolve().parent
started = time.monotonic()
deadline = started + 2
confirmed_asleep = False
while time.monotonic() < deadline:
    try:
        result = subprocess.run(
            [str(BASE / 'source/m1ddc'), 'display', 'basic=7789:23305:YOUR_MONITOR_SERIAL', 'probe', 'standby'],
            capture_output=True, text=True, timeout=min(.5, max(.01, deadline-time.monotonic())))
        state = json.loads(result.stdout.splitlines()[-1])
        if isinstance(state, dict) and state.get('asleep') is True:
            confirmed_asleep = True
            # Allow the output to finish powering down before requesting wake.
            time.sleep(.5)
            break
    except (subprocess.TimeoutExpired, ValueError, IndexError, OSError):
        pass
    time.sleep(.05)

status = {'wake_requested_at': datetime.datetime.now().isoformat(),
          'sleep_confirmed': confirmed_asleep, 'delay_seconds': round(time.monotonic()-started, 3)}
try:
    temporary = BASE / 'wake-status.tmp'
    temporary.write_text(json.dumps(status) + '\n')
    temporary.replace(BASE / 'wake-status.json')
except OSError:
    pass
subprocess.run(['/usr/bin/caffeinate', '-u', '-d', '-t', '10'], timeout=15)
