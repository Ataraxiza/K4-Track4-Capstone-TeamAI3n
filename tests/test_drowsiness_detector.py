import unittest

from drowsiness_detector import DrowsinessMonitor, eye_aspect_ratio


class EyeAspectRatioTests(unittest.TestCase):
    def test_calculates_eye_aspect_ratio(self):
        points = [(0.0, 1.0), (1.0, 0.0), (3.0, 0.0),
                  (4.0, 1.0), (3.0, 2.0), (1.0, 2.0)]

        self.assertAlmostEqual(eye_aspect_ratio(points), 0.5)

    def test_rejects_zero_width_eye(self):
        points = [(0.0, 0.0)] * 6

        with self.assertRaisesRegex(ValueError, "must not overlap"):
            eye_aspect_ratio(points)

    def test_rejects_wrong_number_of_points(self):
        with self.assertRaisesRegex(ValueError, "six"):
            eye_aspect_ratio([(0.0, 0.0)] * 5)


class DrowsinessMonitorTests(unittest.TestCase):
    def setUp(self):
        self.monitor = DrowsinessMonitor(ear_threshold=0.2, closed_seconds=1.0)

    def test_short_blink_does_not_trigger_alert(self):
        self.assertFalse(self.monitor.update(0.1, now=10.0))
        self.assertFalse(self.monitor.update(0.1, now=10.4))
        self.assertFalse(self.monitor.update(0.3, now=10.5))

    def test_prolonged_closure_triggers_alert(self):
        self.assertFalse(self.monitor.update(0.1, now=10.0))
        self.assertTrue(self.monitor.update(0.1, now=11.0))

    def test_open_eyes_recover_after_alert(self):
        self.monitor.update(0.1, now=10.0)
        self.assertTrue(self.monitor.update(0.1, now=11.0))

        self.assertFalse(self.monitor.update(0.3, now=11.1))

    def test_lost_face_resets_closure_timer(self):
        self.monitor.update(0.1, now=10.0)
        self.monitor.update(None, now=10.8)

        self.assertFalse(self.monitor.update(0.1, now=11.0))
        self.assertFalse(self.monitor.update(0.1, now=11.9))

    def test_rejects_invalid_configuration(self):
        with self.assertRaises(ValueError):
            DrowsinessMonitor(ear_threshold=1.0)
        with self.assertRaises(ValueError):
            DrowsinessMonitor(closed_seconds=0.0)


if __name__ == "__main__":
    unittest.main()