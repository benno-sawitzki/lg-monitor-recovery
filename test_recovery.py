import unittest
from recovery import RecoveryGate


def state(power=1, **changes):
    return dict(power=power, online=True, asleep=False, external_count=1) | changes


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

    def test_sleep_disconnect_and_other_displays_cancel_pending_recovery(self):
        for interruption in [None, state(online=False), state(asleep=True), state(external_count=2), {}]:
            with self.subTest(interruption=interruption):
                gate = RecoveryGate()
                for i in range(3):
                    self.assertFalse(gate.update(state(-1), i))
                self.assertFalse(gate.update(interruption, 3))
                self.assertFalse(gate.update(state(), 4))
                self.assertFalse(gate.update(state(), 5))

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


if __name__ == '__main__':
    unittest.main()
