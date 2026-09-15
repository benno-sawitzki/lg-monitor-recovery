"""Recover one identified LG after its controls disappear and return while macOS stays awake."""
import argparse
import fcntl
import json
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import signal
import subprocess
import sys
import threading
import time

BASE = Path(__file__).resolve().parent
TARGET = 'basic=7789:23305:YOUR_MONITOR_SERIAL'
READER = BASE / 'source/m1ddc'
STOP = threading.Event()


class RecoveryGate:
    def __init__(self):
        self.bad = self.good = 0
        self.armed = False
        self.previous_time = None

    def reset(self):
        self.bad = self.good = 0
        self.armed = False

    def update(self, state, now):
        if self.previous_time is not None and (now - self.previous_time > 10 or now < self.previous_time):
            self.reset()
        self.previous_time = now
        if (not state or state.get('online') is not True or state.get('asleep') is not False
                or state.get('external_count') != 1):
            self.reset()
            return False
        if state.get('power') not in (-1, 1, 2, 3, 4):
            self.reset()
            return False
        if state['power'] != 1:
            self.bad += 1
            self.good = 0
            self.armed = self.bad >= 2
            return False
        self.good += 1
        if self.armed and self.good >= 2:
            self.reset()
            return True
        if not self.armed:
            self.bad = 0
        return False


def probe():
    try:
        result = subprocess.run([str(READER), 'display', TARGET, 'probe', 'standby'],
                                capture_output=True, text=True, timeout=5)
        if result.returncode:
            return None
        state = json.loads(result.stdout.splitlines()[-1])
        return state if isinstance(state, dict) else None
    except (subprocess.TimeoutExpired, ValueError, IndexError):
        return None


def recover():
    # The wake child survives this helper exiting, so an interrupted reset still wakes the display.
    wake = subprocess.Popen([sys.executable, str(BASE / 'wake_display.py')],
                            start_new_session=True, stdin=subprocess.DEVNULL,
                            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    try:
        result = subprocess.run(['/usr/bin/pmset', 'displaysleepnow'],
                                capture_output=True, text=True, timeout=5)
        logging.info('display_output_restart exit=%s wake_pid=%s', result.returncode, wake.pid)
    except subprocess.TimeoutExpired:
        logging.error('display_output_restart timed out; independent wake remains scheduled')
    STOP.wait(6)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--probe', action='store_true')
    parser.add_argument('--recover-once', action='store_true')
    parser.add_argument('--parent-pid', type=int, default=0)
    args = parser.parse_args()
    if args.probe:
        print(json.dumps(probe()))
        return
    with (BASE / 'recovery.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        log_folder = Path.home() / 'Library/Logs/LGDisplayRecovery'
        log_folder.mkdir(parents=True, exist_ok=True)
        handler = RotatingFileHandler(log_folder / 'recovery.log', maxBytes=131072, backupCount=2)
        handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logging.basicConfig(level=logging.INFO, handlers=[handler])
        for sig in (signal.SIGTERM, signal.SIGINT):
            signal.signal(sig, lambda *_: STOP.set())
        if args.recover_once:
            check = probe()
            if check and check.get('online') is True and check.get('asleep') is False and check.get('external_count') == 1:
                recover()
            else:
                logging.info('manual_recovery_skipped target_not_available_or_asleep')
            return
        logging.info('started target=%s', TARGET)
        gate = RecoveryGate()
        previous = object()
        while not STOP.is_set():
            if args.parent_pid and os.getppid() != args.parent_pid:
                logging.info('menu_app_exited')
                break
            state = probe()
            if state != previous:
                logging.info('display_state %s', json.dumps(state, sort_keys=True))
                previous = state
            if gate.update(state, time.time()):
                # Recheck after the trigger so a concurrent unplug or normal sleep cancels the reset.
                check = probe()
                if (check and check.get('online') is True and check.get('asleep') is False
                        and check.get('power') == 1 and check.get('external_count') == 1):
                    logging.info('monitor_returned_after_control_outage')
                    recover()
                else:
                    logging.info('recovery_cancelled state_changed')
                gate.reset()
            # Poll faster only during an observed outage/reconnection, not in normal use.
            STOP.wait(0.15 if gate.bad or gate.armed else 1)
        logging.info('stopped')


if __name__ == '__main__':
    main()
