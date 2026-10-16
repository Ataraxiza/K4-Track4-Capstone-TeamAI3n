import unittest
from types import SimpleNamespace

from drowsiness_detector import (
    DrowsinessMonitor,
    eye_aspect_ratio,
    select_closest_face,
)


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


class FaceSelectionTests(unittest.TestCase):
    @staticmethod
    def make_face(left, top, right, bottom):
        return [
            SimpleNamespace(x=left, y=top),
            SimpleNamespace(x=right, y=bottom),
        ]

    def test_selects_largest_face_as_closest(self):
        farther_face = self.make_face(0.1, 0.1, 0.3, 0.4)
        closer_face = self.make_face(0.5, 0.2, 0.9, 0.8)

        self.assertIs(select_closest_face([farther_face, closer_face]), closer_face)

    def test_returns_none_when_no_faces_are_detected(self):
        self.assertIsNone(select_closest_face([]))


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