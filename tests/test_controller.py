import unittest
from pumpkin.controller import Controller, State


class VisitTests(unittest.TestCase):
    def test_high_input_keeps_visit_alive_and_does_not_repeat(self):
        pumpkin = Controller()
        self.assertTrue(pumpkin.update(1, True))
        for now in (2, 30, 300):
            self.assertFalse(pumpkin.update(now, True))
        self.assertEqual(pumpkin.state, State.AWAKE)
        pumpkin.update(301, False)
        pumpkin.update(320.99, False)
        self.assertEqual(pumpkin.state, State.AWAKE)
        pumpkin.update(321, False)
        self.assertEqual(pumpkin.state, State.CLOSING)
        pumpkin.update(322, False)
        self.assertEqual(pumpkin.state, State.SLEEPING)
        self.assertTrue(pumpkin.update(323, True))

    def test_repeated_motion_resets_inactivity_without_new_joke(self):
        pumpkin = Controller()
        pumpkin.update(0, True)
        pumpkin.update(1, False)
        self.assertFalse(pumpkin.update(19, True))
        pumpkin.update(20, False)
        pumpkin.update(39, False)
        self.assertEqual(pumpkin.state, State.AWAKE)
        self.assertAlmostEqual(pumpkin.remaining(39), 1)

    def test_motion_reverses_closing_without_visual_jump(self):
        pumpkin = Controller(2)
        pumpkin.update(0, True)
        pumpkin.update(1, False)
        pumpkin.update(3, False)
        before = pumpkin.openness(3.3)
        self.assertTrue(pumpkin.update(3.3, True))
        self.assertAlmostEqual(before, pumpkin.openness(3.3))
        pumpkin.update(5, True)
        self.assertEqual(pumpkin.state, State.AWAKE)

    def test_startup_stays_asleep_without_motion(self):
        pumpkin = Controller()
        for now in (0, 20, 1000):
            self.assertFalse(pumpkin.update(now, False))
            self.assertEqual(pumpkin.openness(now), 0)


if __name__ == "__main__":
    unittest.main()
