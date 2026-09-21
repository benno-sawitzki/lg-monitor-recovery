import unittest
import tempfile
from pathlib import Path
from unittest.mock import patch
import recovery
from recovery import RecoveryGate


def state(power=1, **changes):
    return dict(power=power, online=True, asleep=False, external_count=1, display_id=3) | changes


class RecoveryTests(unittest.TestCase):
    def test_sustained_outage_then_two_good_reads_triggers_once(self):
        gate = RecoveryGate()
        values = [state(), state(-1), state(-1), state(-1), state(), state(), state()]
        self.assertEqual([gate.update(v, i) for i, v in enumerate(values)],
                         [False, False, False, False, False, True, False])

    def test_intermittent_errors_do_not_trigger(self):
        gate = RecoveryGate()
        for i in range(100):
            self.assertFalse(gate.update(state(-1 if i % 2 else 1), i))

    def test_sleep_disconnect_and_invalid_counts_cancel_pending_recovery(self):
        for interruption in [None, state(online=False), state(asleep=True), {},
                             *[state(external_count=n) for n in (0, -1, None, '2', True)]]:
            with self.subTest(interruption=interruption):
                gate = RecoveryGate()
                for i in range(3):
                    self.assertFalse(gate.update(state(-1), i))
                self.assertFalse(gate.update(interruption, 3))
                self.assertFalse(gate.update(state(), 4))
                self.assertFalse(gate.update(state(), 5))

    def test_multiple_displays_allow_repeated_target_power_cycles(self):
        for count in (2, 3):
            with self.subTest(count=count):
                gate = RecoveryGate()
                for start in (0, 6):
                    values = [state(p, external_count=count) for p in (1, -1, -1, 1, 1, 1)]
                    self.assertEqual([gate.update(s, start+i) for i, s in enumerate(values)],
                                     [False, False, False, False, True, False])

    def test_display_count_or_target_id_change_cancels_outage(self):
        for changes in ({'external_count': 3}, {'external_count': 1}, {'display_id': 7}):
            with self.subTest(changes=changes):
                gate = RecoveryGate()
                gate.update(state(-1, external_count=2), 0)
                gate.update(state(-1, external_count=2), 1)
                new_state = state(external_count=2) | changes
                self.assertFalse(gate.update(new_state, 2))
                self.assertFalse(gate.update(new_state, 3))
                # A fresh cycle on the new arrangement still recovers.
                gate.update(new_state | {'power': -1}, 4)
                gate.update(new_state | {'power': -1}, 5)
                self.assertFalse(gate.update(new_state, 6))
                self.assertTrue(gate.update(new_state, 7))

    def test_normal_sleep_with_two_displays_cancels_outage(self):
        gate = RecoveryGate()
        values = [state(p, external_count=2) for p in (-1, -1)]
        values += [dict(power=-1, online=True, asleep=True)]
        values += [state(external_count=2)] * 3
        self.assertFalse(any(gate.update(s, i) for i, s in enumerate(values)))

    def test_suspended_process_and_clock_change_clear_pending_recovery(self):
        for next_time in [100, -10]:
            gate = RecoveryGate()
            for i in range(3):
                gate.update(state(-1), i)
            self.assertFalse(gate.update(state(), next_time))
            self.assertFalse(gate.update(state(), next_time + 1))

    def test_each_distinct_cycle_recovers_even_within_one_minute(self):
        gate = RecoveryGate()
        def cycle(t):
            outcomes = [gate.update(s, t+i) for i, s in enumerate(
                [state(-1), state(-1), state(-1), state(), state()])]
            return outcomes[-1]
        self.assertTrue(cycle(0))
        self.assertTrue(cycle(10))
        for t in [20, 30, 40, 50, 60]:
            self.assertTrue(cycle(t))

    def test_short_power_cycle_is_detected(self):
        gate = RecoveryGate()
        self.assertFalse(gate.update(state(-1), 0))
        self.assertFalse(gate.update(state(-1), 1.2))
        self.assertFalse(gate.update(state(), 2.4))
        self.assertTrue(gate.update(state(), 3.6))
        for i in range(4, 100):
            self.assertFalse(gate.update(state(), i))


class RecoveryCommandTests(unittest.TestCase):
    def run_main(self, args, probes, stop=None):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(recovery, 'BASE', Path(directory)), \
                patch.object(recovery.Path, 'home', return_value=Path(directory)), \
                patch.object(recovery, 'probe', side_effect=probes), \
                patch.object(recovery, 'recover') as recover, \
                patch.object(recovery, 'STOP') as stopped, \
                patch.object(recovery.signal, 'signal'), \
                patch.object(recovery.logging, 'basicConfig'), \
                patch.object(recovery, 'RotatingFileHandler'), \
                patch('sys.argv', ['recovery.py', *args]):
            stopped.is_set.side_effect = stop
            recovery.main()
            return recover.call_count

    def test_manual_recovery_with_two_displays(self):
        self.assertEqual(self.run_main(['--recover-once'], [state(external_count=2)]), 1)

    def test_manual_recovery_skips_sleeping_or_disconnected_target(self):
        for value in (None, state(asleep=True, external_count=2), state(online=False)):
            self.assertEqual(self.run_main(['--recover-once'], [value]), 0)

    def test_automatic_recovery_rechecks_two_display_setup(self):
        samples = [state(p, external_count=2) for p in (-1, -1, 1, 1)]
        self.assertEqual(self.run_main([], samples + [samples[-1]], [False]*4 + [True]), 1)

    def test_recheck_cancels_concurrent_sleep_unplug_or_topology_change(self):
        samples = [state(p, external_count=2) for p in (-1, -1, 1, 1)]
        for changed in (None, state(asleep=True, external_count=2), state(external_count=3),
                        state(external_count=2, display_id=7), state(-1, external_count=2)):
            self.assertEqual(self.run_main([], samples + [changed], [False]*4 + [True]), 0)


if __name__ == '__main__':
    unittest.main()
