import json
from pathlib import Path
import runpy
import subprocess
import tempfile
import unittest
from unittest.mock import patch


class WakeTests(unittest.TestCase):
    def exercise(self, responds):
        elapsed = [0.0]
        wakes = []

        def sleep(seconds):
            elapsed[0] += seconds

        def run(command, **kwargs):
            if command[0] == '/usr/bin/caffeinate':
                wakes.append((elapsed[0], command))
                return subprocess.CompletedProcess(command, 0)
            if responds:
                return subprocess.CompletedProcess(command, 0, '{"asleep":true}\n', '')
            elapsed[0] += kwargs['timeout']
            raise subprocess.TimeoutExpired(command, kwargs['timeout'])

        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'wake_display.py'
            script.write_text(Path(__file__).with_name('wake_display.py').read_text())
            with patch('time.monotonic', side_effect=lambda: elapsed[0]), \
                    patch('time.sleep', side_effect=sleep), patch('subprocess.run', side_effect=run):
                runpy.run_path(str(script))
            status = json.loads((Path(directory) / 'wake-status.json').read_text())
        return wakes, status

    def test_confirmed_sleep_wakes_early_and_holds_display_awake(self):
        wakes, status = self.exercise(True)
        self.assertEqual(len(wakes), 1)
        self.assertEqual(wakes[0][0], .5)
        self.assertEqual(wakes[0][1], ['/usr/bin/caffeinate', '-u', '-d', '-t', '10'])
        self.assertTrue(status['sleep_confirmed'])

    def test_unresponsive_reader_still_requests_wake_within_bounded_time(self):
        wakes, status = self.exercise(False)
        self.assertEqual(len(wakes), 1)
        self.assertGreaterEqual(wakes[0][0], 2)
        self.assertLessEqual(wakes[0][0], 2.1)
        self.assertFalse(status['sleep_confirmed'])


if __name__ == '__main__':
    unittest.main()
