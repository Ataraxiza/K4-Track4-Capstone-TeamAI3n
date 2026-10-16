"""Preview all application states without the vision or detector modules."""

import argparse
from pathlib import Path

import cv2
import numpy as np

from src.contracts import DrowsinessResult, FaceObservation
from src.overlay import draw_overlay


def sample_frames() -> list[tuple[str, np.ndarray]]:
    """Build one annotated BGR frame per contract status."""
    samples = (
        ("NORMAL", 0.30, 0.31, 0.0, False),
        ("EYES_CLOSED", 0.15, 0.16, 0.8, False),
        ("DROWSY", 0.14, 0.15, 2.3, True),
        ("NO_FACE", None, None, 0.0, False),
    )
    frames = []
    for status, left, right, duration, alert in samples:
        frame = np.full((480, 640, 3), (45, 50, 60), dtype=np.uint8)
        visible = status != "NO_FACE"
        points = ((240, 260), (255, 254), (270, 260)) if visible else ()
        observation = FaceObservation(
            timestamp=float(len(frames)),
            face_detected=visible,
            ear_left=left,
            ear_right=right,
            left_eye_points=points,
        )
        result = DrowsinessResult(status=status, closed_duration=duration, should_alert=alert)
        frames.append((status, draw_overlay(frame, observation, result)))
    return frames


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, help="Save PNG previews without a display")
    args = parser.parse_args()
    frames = sample_frames()
    if args.output_dir:
        args.output_dir.mkdir(parents=True, exist_ok=True)
        for status, frame in frames:
            destination = args.output_dir / f"{status.lower()}.png"
            if not cv2.imwrite(str(destination), frame):
                parser.error(f"Cannot save {destination}")
            print(destination)
        return 0

    try:
        for status, frame in frames:
            cv2.imshow("Drowsiness UI mock - Q or Esc to exit", frame)
            print(status)
            if cv2.waitKey(1500) & 0xFF in (ord("q"), 27):
                break
    finally:
        cv2.destroyAllWindows()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
