from dataclasses import dataclass
from typing import Literal

@dataclass(frozen=True)
class FaceObservation:
    timestamp: float
    face_detected: bool
    ear_left: float | None = None
    ear_right: float | None = None
    left_eye_points: tuple[tuple[int, int], ...] = ()
    right_eye_points: tuple[tuple[int, int], ...] = ()

@dataclass(frozen=True)
class DrowsinessResult:
    status: Literal["NORMAL", "EYES_CLOSED", "DROWSY", "NO_FACE"]
    closed_duration: float
    should_alert: bool

