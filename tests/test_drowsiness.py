"""
Module: tests/test_drowsiness.py
Kiểm thử tự động cho module B (DrowsinessDetector)
Chạy bằng lệnh: python -m unittest discover -s tests -v
"""

import math
import unittest

from src.contracts import FaceObservation
from src.drowsiness import DrowsinessDetector


def make_obs(
    timestamp: float,
    face_detected: bool = True,
    ear_left: float | None = 0.30,
    ear_right: float | None = 0.30,
) -> FaceObservation:
    """Hàm tiện ích tạo FaceObservation giả lập với timestamp xác định (không dùng sleep)."""
    return FaceObservation(
        timestamp=timestamp,
        face_detected=face_detected,
        ear_left=ear_left,
        ear_right=ear_right,
    )


class TestDrowsinessDetector(unittest.TestCase):
    def setUp(self):
        # Mặc định: ngưỡng EAR 0.22, nhắm liên tục 2.0 giây thì DROWSY, gián đoạn tối đa 0.5 giây
        self.detector = DrowsinessDetector(
            ear_threshold=0.22,
            closed_seconds=2.0,
            max_gap_seconds=0.5,
        )

    def test_configuration_validation(self):
        """Kiểm tra validation tham số đầu vào của DrowsinessDetector."""
        with self.assertRaises(ValueError):
            DrowsinessDetector(ear_threshold=0.0)
        with self.assertRaises(ValueError):
            DrowsinessDetector(ear_threshold=1.0)
        with self.assertRaises(ValueError):
            DrowsinessDetector(closed_seconds=0.0)
        with self.assertRaises(ValueError):
            DrowsinessDetector(max_gap_seconds=0.0)

    def test_normal_open_eyes(self):
        """Mắt mở bình thường trả về NORMAL, closed_duration=0, should_alert=False."""
        obs = make_obs(timestamp=1.0, ear_left=0.30, ear_right=0.30)
        result = self.detector.update(obs)

        self.assertEqual(result.status, "NORMAL")
        self.assertEqual(result.closed_duration, 0.0)
        self.assertFalse(result.should_alert)

    def test_short_blink_does_not_alert(self):
        """Chớp mắt ngắn trả về EYES_CLOSED nhưng không kích hoạt should_alert, sau đó mở mắt về NORMAL."""
        # Frame 1: bắt đầu chớp mắt (t = 10.0)
        res1 = self.detector.update(make_obs(timestamp=10.0, ear_left=0.15, ear_right=0.15))
        self.assertEqual(res1.status, "EYES_CLOSED")
        self.assertAlmostEqual(res1.closed_duration, 0.0)
        self.assertFalse(res1.should_alert)

        # Frame 2: chớp tiếp sau 0.15s (t = 10.15)
        res2 = self.detector.update(make_obs(timestamp=10.15, ear_left=0.14, ear_right=0.16))
        self.assertEqual(res2.status, "EYES_CLOSED")
        self.assertAlmostEqual(res2.closed_duration, 0.15)
        self.assertFalse(res2.should_alert)

        # Frame 3: mắt mở lại (t = 10.3)
        res3 = self.detector.update(make_obs(timestamp=10.3, ear_left=0.28, ear_right=0.28))
        self.assertEqual(res3.status, "NORMAL")
        self.assertEqual(res3.closed_duration, 0.0)
        self.assertFalse(res3.should_alert)

    def test_prolonged_closure_triggers_drowsy(self):
        """Nhắm mắt liên tục đạt hoặc vượt closed_seconds (2.0s) chuyển sang DROWSY và should_alert=True."""
        # Mô phỏng camera 10 FPS (mỗi frame cách nhau 0.1s <= max_gap_seconds=0.5s)
        # Bắt đầu nhắm từ t = 0.0 đến t = 2.5
        results = []
        for i in range(26):
            t = round(i * 0.1, 1)
            res = self.detector.update(make_obs(timestamp=t, ear_left=0.18, ear_right=0.18))
            results.append((t, res))

        # Tại t = 1.0 (nhắm được 1.0 giây) -> EYES_CLOSED, closed_duration = 1.0
        _, res_1s = results[10]
        self.assertEqual(res_1s.status, "EYES_CLOSED")
        self.assertAlmostEqual(res_1s.closed_duration, 1.0)
        self.assertFalse(res_1s.should_alert)

        # Tại t = 1.9 (nhắm được 1.9 giây) -> vẫn EYES_CLOSED
        _, res_1_9s = results[19]
        self.assertEqual(res_1_9s.status, "EYES_CLOSED")
        self.assertFalse(res_1_9s.should_alert)

        # Tại t = 2.0 (đúng 2.0 giây) -> kích hoạt DROWSY và should_alert=True
        _, res_2s = results[20]
        self.assertEqual(res_2s.status, "DROWSY")
        self.assertAlmostEqual(res_2s.closed_duration, 2.0)
        self.assertTrue(res_2s.should_alert)

        # Tại t = 2.5 -> tiếp tục duy trì DROWSY và should_alert=True
        _, res_2_5s = results[25]
        self.assertEqual(res_2_5s.status, "DROWSY")
        self.assertAlmostEqual(res_2_5s.closed_duration, 2.5)
        self.assertTrue(res_2_5s.should_alert)

    def test_recovery_to_normal_after_drowsy(self):
        """Sau khi bị cảnh báo DROWSY, tài xế mở mắt ra lập tức trở về NORMAL và reset bộ đếm."""
        # Nhắm mắt 2.2 giây (bước nhảy 0.2s <= 0.5s)
        for i in range(12):
            t = round(i * 0.2, 1)
            res = self.detector.update(make_obs(timestamp=t, ear_left=0.15, ear_right=0.15))

        # Kiểm tra trạng thái đang là DROWSY
        self.assertEqual(res.status, "DROWSY")
        self.assertTrue(res.should_alert)

        # Mở mắt tại t = 2.4s (EAR = 0.30 >= threshold 0.22)
        res_open = self.detector.update(make_obs(timestamp=2.4, ear_left=0.30, ear_right=0.30))
        self.assertEqual(res_open.status, "NORMAL")
        self.assertEqual(res_open.closed_duration, 0.0)
        self.assertFalse(res_open.should_alert)

    def test_lost_face_resets_closure_chain(self):
        """Mất mặt (face_detected=False) trả về NO_FACE và reset chuỗi nhắm, không cộng dồn thời gian."""
        # Nhắm 1.0 giây (bước 0.2s)
        for i in range(6):
            t = round(i * 0.2, 1)
            self.detector.update(make_obs(timestamp=t, ear_left=0.15, ear_right=0.15))

        # t = 1.2: quay mặt đi, không nhận diện được mặt
        res_lost = self.detector.update(make_obs(timestamp=1.2, face_detected=False))
        self.assertEqual(res_lost.status, "NO_FACE")
        self.assertEqual(res_lost.closed_duration, 0.0)
        self.assertFalse(res_lost.should_alert)

        # t = 1.4: thấy lại mặt nhưng mắt nhắm -> phải tính lại từ đầu, không cộng dồn 1.0s trước
        res_restart = self.detector.update(make_obs(timestamp=1.4, ear_left=0.15, ear_right=0.15))
        self.assertEqual(res_restart.status, "EYES_CLOSED")
        self.assertAlmostEqual(res_restart.closed_duration, 0.0)
        self.assertFalse(res_restart.should_alert)

    def test_invalid_or_missing_ear_treated_as_no_face(self):
        """Một trong hai EAR là None, NaN, Inf hoặc số âm được xem là NO_FACE và reset bộ đếm."""
        # 1. EAR là None
        res_none = self.detector.update(make_obs(timestamp=1.0, ear_left=0.25, ear_right=None))
        self.assertEqual(res_none.status, "NO_FACE")
        self.assertEqual(res_none.closed_duration, 0.0)

        # 2. EAR là NaN
        res_nan = self.detector.update(make_obs(timestamp=1.1, ear_left=float("nan"), ear_right=0.25))
        self.assertEqual(res_nan.status, "NO_FACE")

        # 3. EAR là Inf
        res_inf = self.detector.update(make_obs(timestamp=1.2, ear_left=float("inf"), ear_right=0.25))
        self.assertEqual(res_inf.status, "NO_FACE")

        # 4. EAR là số âm
        res_neg = self.detector.update(make_obs(timestamp=1.3, ear_left=-0.05, ear_right=0.25))
        self.assertEqual(res_neg.status, "NO_FACE")

    def test_timestamp_anomalies_and_gap_handling(self):
        """Timestamp bị lùi hoặc khoảng gián đoạn vượt max_gap_seconds phải cắt chuỗi nhắm."""
        # Chuỗi 1: nhắm mắt
        self.detector.update(make_obs(timestamp=10.0, ear_left=0.15, ear_right=0.15))
        self.detector.update(make_obs(timestamp=10.3, ear_left=0.15, ear_right=0.15))

        # Khoảng cách lớn: gián đoạn 0.6 giây (> max_gap_seconds 0.5s)
        res_gap = self.detector.update(make_obs(timestamp=10.9, ear_left=0.15, ear_right=0.15))
        self.assertEqual(res_gap.status, "EYES_CLOSED")
        # Chuỗi bị cắt và tính lại mốc mới từ 10.9
        self.assertAlmostEqual(res_gap.closed_duration, 0.0)

        # Timestamp bị lùi (ví dụ do video tua lại: 10.9 -> 5.0)
        res_rewind = self.detector.update(make_obs(timestamp=5.0, ear_left=0.15, ear_right=0.15))
        self.assertEqual(res_rewind.status, "EYES_CLOSED")
        self.assertAlmostEqual(res_rewind.closed_duration, 0.0)

    def test_manual_reset(self):
        """Hàm reset() chủ động xóa sạch mốc thời gian."""
        self.detector.update(make_obs(timestamp=1.0, ear_left=0.15, ear_right=0.15))
        self.detector.reset()
        self.assertIsNone(self.detector.closed_start_time)
        self.assertIsNone(self.detector.last_timestamp)


if __name__ == "__main__":
    unittest.main()

