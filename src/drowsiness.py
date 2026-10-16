"""
Module: src/drowsiness.py
Phụ trách: Người B (Module B - Drowsiness Detection Logic)
Theo hợp đồng và phân công trong Phan_cong_demo_canh_bao_buon_ngu.md
"""

from __future__ import annotations

import math
from typing import Literal

try:
    from src.contracts import DrowsinessResult, FaceObservation
except ImportError:
    from contracts import DrowsinessResult, FaceObservation


def _is_valid_ear(ear: float | None) -> bool:
    """Kiểm tra giá trị EAR có hợp lệ (không None, không NaN/Inf, không âm)."""
    if ear is None:
        return False
    if not isinstance(ear, (int, float)):
        return False
    if math.isnan(ear) or math.isinf(ear):
        return False
    if ear < 0.0:
        return False
    return True


class DrowsinessDetector:
    """
    Theo dõi trạng thái buồn ngủ của tài xế dựa trên thời gian thực truyền vào (timestamp).
    Tuyệt đối không đếm số frame, không dùng time.sleep(), hoàn toàn độc lập với UI và Camera.
    """

    def __init__(
        self,
        ear_threshold: float = 0.22,
        closed_seconds: float = 2.0,
        max_gap_seconds: float = 0.5,
    ) -> None:
        if not (0.0 < ear_threshold < 1.0):
            raise ValueError(f"ear_threshold phải nằm trong khoảng (0, 1), nhận: {ear_threshold}")
        if closed_seconds <= 0:
            raise ValueError(f"closed_seconds phải lớn hơn 0, nhận: {closed_seconds}")
        if max_gap_seconds <= 0:
            raise ValueError(f"max_gap_seconds phải lớn hơn 0, nhận: {max_gap_seconds}")

        self.ear_threshold = ear_threshold
        self.closed_seconds = closed_seconds
        self.max_gap_seconds = max_gap_seconds

        self.closed_start_time: float | None = None
        self.last_timestamp: float | None = None

    def reset(self) -> None:
        """Đặt lại toàn bộ trạng thái theo dõi thời gian và chuỗi nhắm mắt."""
        self.closed_start_time = None
        self.last_timestamp = None

    def update(self, observation: FaceObservation) -> DrowsinessResult:
        """
        Nhận FaceObservation và trả về DrowsinessResult.
        
        Quy tắc:
        - Không có mặt hoặc EAR không hợp lệ: trả NO_FACE, reset chuỗi nhắm.
        - Timestamp không tăng hoặc gián đoạn > max_gap_seconds: cắt chuỗi nhắm (reset start_time).
        - EAR trung bình < ear_threshold:
            + Chưa đủ closed_seconds: EYES_CLOSED, should_alert=False.
            + Đủ hoặc vượt closed_seconds: DROWSY, should_alert=True.
        - EAR trung bình >= ear_threshold:
            + Mở mắt: NORMAL, closed_duration=0, reset chuỗi nhắm.
        """
        # 1. Kiểm tra phát hiện khuôn mặt và tính hợp lệ của EAR
        if not observation.face_detected or not _is_valid_ear(observation.ear_left) or not _is_valid_ear(observation.ear_right):
            self.closed_start_time = None
            self.last_timestamp = observation.timestamp
            return DrowsinessResult(
                status="NO_FACE",
                closed_duration=0.0,
                should_alert=False,
            )

        ts = observation.timestamp

        # 2. Kiểm tra tính liên tục và hợp lệ của timestamp
        if self.last_timestamp is not None:
            # Timestamp không tăng (bị lùi hoặc đứng yên) hoặc gián đoạn quá lớn
            if ts <= self.last_timestamp or (ts - self.last_timestamp) > self.max_gap_seconds:
                self.closed_start_time = None

        self.last_timestamp = ts

        # 3. Tính EAR trung bình 2 mắt
        avg_ear = (observation.ear_left + observation.ear_right) / 2.0

        # 4. Xác định trạng thái nhắm / mở mắt
        if avg_ear < self.ear_threshold:
            # Mắt đang nhắm
            if self.closed_start_time is None:
                self.closed_start_time = ts

            closed_duration = max(0.0, ts - self.closed_start_time)

            if closed_duration >= self.closed_seconds:
                status: Literal["NORMAL", "EYES_CLOSED", "DROWSY", "NO_FACE"] = "DROWSY"
                should_alert = True
            else:
                status = "EYES_CLOSED"
                should_alert = False

            return DrowsinessResult(
                status=status,
                closed_duration=closed_duration,
                should_alert=should_alert,
            )
        else:
            # Mắt đang mở
            self.closed_start_time = None
            return DrowsinessResult(
                status="NORMAL",
                closed_duration=0.0,
                should_alert=False,
            )

