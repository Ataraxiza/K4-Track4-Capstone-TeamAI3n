"""Exercise the C browser bridge with A landmarks and the real B detector."""

import io
import sys
import types
import unittest
from unittest.mock import patch

import cv2
import numpy as np

from drowsiness_detector import LEFT_EYE, RIGHT_EYE
from web_app import create_app


class FakeMesh:
    def __init__(self):
        self.face_visible = True
        self.closed = True
        self.closed_resource = False

    def process(self, _rgb):
        if not self.face_visible:
            return types.SimpleNamespace(multi_face_landmarks=[])
        points = [types.SimpleNamespace(x=0.5, y=0.5) for _ in range(478)]
        for indices, shift in ((LEFT_EYE, 0), (RIGHT_EYE, 100)):
            vertical = 2 if self.closed else 10
            coords = ((100, 100), (110, 100 - vertical), (120, 100 - vertical),
                      (140, 100), (120, 100 + vertical), (110, 100 + vertical))
            for index, (x, y) in zip(indices, coords):
                points[index] = types.SimpleNamespace(x=(x + shift) / 480, y=y / 270)
        face = types.SimpleNamespace(landmark=points)
        return types.SimpleNamespace(multi_face_landmarks=[face])

    def close(self):
        self.closed_resource = True


class WebRealBridgeTests(unittest.TestCase):
    def setUp(self):
        self.mesh = FakeMesh()
        fake_mp = types.SimpleNamespace(solutions=types.SimpleNamespace(
            face_mesh=types.SimpleNamespace(FaceMesh=lambda **_kwargs: self.mesh)))
        self.patch = patch.dict(sys.modules, {"mediapipe": fake_mp})
        self.patch.start()
        # The module can be cached by another test; use the fake MediaPipe here.
        sys.modules.pop("src.web_vision_adapter", None)
        self.app = create_app("real")
        self.client = self.app.test_client()
        ok, jpeg = cv2.imencode(".jpg", np.zeros((270, 480, 3), dtype=np.uint8))
        self.assertTrue(ok)
        self.jpeg = jpeg.tobytes()

    def tearDown(self):
        self.app.config["pipeline"].close()
        self.assertTrue(self.mesh.closed_resource)
        sys.modules.pop("src.web_vision_adapter", None)
        self.patch.stop()

    def analyze(self, timestamp):
        return self.client.post("/api/analyze", data={
            "timestamp": str(timestamp), "frame": (io.BytesIO(self.jpeg), "frame.jpg")})

    def test_frames_reach_b_and_gap_resets(self):
        self.assertEqual(self.client.get("/api/health").json["mode"], "real")
        self.assertEqual(self.client.post("/api/config", json={
            "ear_threshold": 0.22, "closed_seconds": 0.4,
            "max_gap_seconds": 0.5}).status_code, 200)
        first = self.analyze(0).json
        self.assertEqual(first["status"], "EYES_CLOSED")
        self.assertEqual(len(first["left_eye_points"]), 6)
        self.assertAlmostEqual(first["ear_left"], 0.1)
        self.assertEqual(self.analyze(0.2).json["status"], "EYES_CLOSED")
        alert = self.analyze(0.4).json
        self.assertEqual(alert["status"], "DROWSY")
        self.assertTrue(alert["should_alert"])
        self.assertEqual(self.analyze(1.0).json["status"], "EYES_CLOSED")
        self.mesh.closed = False
        self.assertEqual(self.analyze(1.2).json["status"], "NORMAL")
        self.mesh.face_visible = False
        self.assertEqual(self.analyze(1.4).json["status"], "NO_FACE")

    def test_invalid_frame_is_rejected(self):
        self.assertEqual(self.client.post("/api/analyze", data={"timestamp": "0"}).status_code, 400)
        self.assertEqual(self.client.post("/api/analyze", data={
            "timestamp": "0", "frame": (io.BytesIO(b"bad"), "frame.jpg")}).status_code, 400)


if __name__ == "__main__":
    unittest.main()
