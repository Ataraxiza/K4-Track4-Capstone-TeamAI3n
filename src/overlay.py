"""Draw status and eye observations on an OpenCV BGR frame."""

import math

import cv2
import numpy as np

from src.contracts import DrowsinessResult, FaceObservation


_STATUS_COLORS = {
    "NORMAL": (52, 190, 64),
    "EYES_CLOSED": (0, 190, 255),
    "DROWSY": (40, 40, 230),
    "NO_FACE": (160, 160, 160),
}


def _ear_text(value: float | None) -> str:
    if value is None or not math.isfinite(value) or value < 0:
        return "N/A"
    return f"{value:.3f}"


def draw_overlay(
    frame: np.ndarray, observation: FaceObservation, result: DrowsinessResult
) -> np.ndarray:
    """Return a copy with status, EAR, duration, and available eye landmarks."""
    output = frame.copy()
    height, width = output.shape[:2]
    color = _STATUS_COLORS[result.status]

    cv2.rectangle(output, (0, 0), (width - 1, min(height - 1, 114)), (20, 20, 20), -1)
    cv2.rectangle(output, (0, 0), (width - 1, min(height - 1, 114)), color, 2)
    lines = (
        (f"STATUS: {result.status}", 29, 0.72, color),
        (f"EAR L: {_ear_text(observation.ear_left)}  R: {_ear_text(observation.ear_right)}", 61, 0.58, (240, 240, 240)),
        (f"EYES CLOSED: {result.closed_duration:.2f} s", 91, 0.58, (240, 240, 240)),
    )
    for label, y, scale, text_color in lines:
        if y < height:
            cv2.putText(output, label, (12, y), cv2.FONT_HERSHEY_SIMPLEX, scale, text_color, 2, cv2.LINE_AA)

    for points in (observation.left_eye_points, observation.right_eye_points):
        for x, y in points:
            if 0 <= x < width and 0 <= y < height:
                cv2.circle(output, (x, y), 3, color, -1, cv2.LINE_AA)
    return output
