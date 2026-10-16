"""Live webcam demo for detecting prolonged eye closure with MediaPipe Face Mesh."""

from __future__ import annotations

import argparse
import math
import sys
import time
from collections.abc import Sequence

Point = tuple[float, float]

LEFT_EYE = (362, 385, 387, 263, 373, 380)
RIGHT_EYE = (33, 160, 158, 133, 153, 144)


def eye_aspect_ratio(points: Sequence[Point]) -> float:
    """Calculate EAR from two upper/lower pairs and the two eye corners."""
    if len(points) != 6:
        raise ValueError("EAR requires exactly six eye landmark points")

    vertical_a = math.dist(points[1], points[5])
    vertical_b = math.dist(points[2], points[4])
    horizontal = math.dist(points[0], points[3])
    if horizontal == 0:
        raise ValueError("Eye corner points must not overlap")

    return (vertical_a + vertical_b) / (2.0 * horizontal)


class DrowsinessMonitor:
    """Track prolonged eye closure using elapsed time rather than frame count."""

    def __init__(
        self,
        ear_threshold: float = 0.21,
        closed_seconds: float = 1.5,
        recovery_margin: float = 0.04,
    ) -> None:
        if not 0.0 < ear_threshold < 1.0:
            raise ValueError("EAR threshold must be between 0 and 1")
        if closed_seconds <= 0:
            raise ValueError("Closed duration must be greater than zero")
        if recovery_margin < 0:
            raise ValueError("Recovery margin cannot be negative")

        self.ear_threshold = ear_threshold
        self.open_threshold = ear_threshold + recovery_margin
        self.closed_seconds = closed_seconds
        self.closed_since: float | None = None
        self.is_drowsy = False

    def reset(self) -> None:
        self.closed_since = None
        self.is_drowsy = False

    def elapsed_closed(self, now: float | None = None) -> float:
        if self.closed_since is None:
            return 0.0
        current_time = time.monotonic() if now is None else now
        return max(0.0, current_time - self.closed_since)

    def update(self, ear: float | None, now: float | None = None) -> bool:
        current_time = time.monotonic() if now is None else now

        if ear is None:
            self.reset()
            return self.is_drowsy

        if self.is_drowsy:
            if ear >= self.open_threshold:
                self.reset()
            return self.is_drowsy

        if self.closed_since is None:
            if ear <= self.ear_threshold:
                self.closed_since = current_time
            return False

        if ear >= self.open_threshold:
            self.closed_since = None
            return False

        self.is_drowsy = self.elapsed_closed(current_time) >= self.closed_seconds
        return self.is_drowsy


def _parse_source(value: str) -> int | str:
    try:
        return int(value)
    except ValueError:
        return value


def _eye_points(face_landmarks: Sequence[object], indices: Sequence[int]) -> list[Point]:
    return [(face_landmarks[index].x, face_landmarks[index].y) for index in indices]


def _play_alert() -> None:
    try:
        import winsound

        winsound.Beep(880, 250)
    except ImportError:
        print("\a", end="", flush=True)
    except RuntimeError:
        pass


def run_demo(
    source: int | str,
    ear_threshold: float,
    closed_seconds: float,
    sound_enabled: bool,
) -> int:
    try:
        import cv2
        import mediapipe as mp
    except ImportError as error:
        print(
            "Missing demo dependency. Install packages with: "
            "python -m pip install -r requirements.txt",
            file=sys.stderr,
        )
        print(error, file=sys.stderr)
        return 1

    capture = cv2.VideoCapture(source)
    if not capture.isOpened():
        print(f"Could not open camera or video source: {source}", file=sys.stderr)
        capture.release()
        return 1

    monitor = DrowsinessMonitor(ear_threshold, closed_seconds)
    alert_count = 0
    was_drowsy = False
    previous_frame_time = time.monotonic()

    try:
        with mp.solutions.face_mesh.FaceMesh(
            max_num_faces=1,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        ) as face_mesh:
            while True:
                success, frame = capture.read()
                if not success:
                    break

                if isinstance(source, int):
                    frame = cv2.flip(frame, 1)

                now = time.monotonic()
                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                result = face_mesh.process(rgb_frame)
                ear: float | None = None

                if result.multi_face_landmarks:
                    landmarks = result.multi_face_landmarks[0].landmark
                    left_ear = eye_aspect_ratio(_eye_points(landmarks, LEFT_EYE))
                    right_ear = eye_aspect_ratio(_eye_points(landmarks, RIGHT_EYE))
                    ear = (left_ear + right_ear) / 2.0

                    for indices in (LEFT_EYE, RIGHT_EYE):
                        for index in indices:
                            point = landmarks[index]
                            x = int(point.x * frame.shape[1])
                            y = int(point.y * frame.shape[0])
                            cv2.circle(frame, (x, y), 2, (80, 210, 240), -1)

                is_drowsy = monitor.update(ear, now)
                if is_drowsy and not was_drowsy:
                    alert_count += 1
                    if sound_enabled:
                        _play_alert()
                was_drowsy = is_drowsy

                frame_interval = max(now - previous_frame_time, 1e-6)
                previous_frame_time = now
                fps = 1.0 / frame_interval

                if ear is None:
                    status = "NO FACE DETECTED"
                    status_color = (0, 190, 255)
                elif is_drowsy:
                    status = "DROWSINESS ALERT"
                    status_color = (40, 40, 235)
                elif monitor.closed_since is not None:
                    status = "EYES CLOSED - MONITORING"
                    status_color = (0, 190, 255)
                else:
                    status = "NORMAL - EYES OPEN"
                    status_color = (70, 190, 100)

                cv2.rectangle(frame, (0, 0), (frame.shape[1], 112), (20, 28, 36), -1)
                cv2.putText(frame, status, (18, 32), cv2.FONT_HERSHEY_SIMPLEX, 0.75,
                            status_color, 2, cv2.LINE_AA)
                ear_text = "--" if ear is None else f"{ear:.3f}"
                cv2.putText(frame, f"EAR {ear_text}  |  threshold {ear_threshold:.2f}",
                            (18, 65), cv2.FONT_HERSHEY_SIMPLEX, 0.55, (235, 240, 245),
                            1, cv2.LINE_AA)
                cv2.putText(frame,
                            f"Closed {monitor.elapsed_closed(now):.1f}/{closed_seconds:.1f}s"
                            f"  |  Alerts {alert_count}  |  {fps:.1f} FPS",
                            (18, 94), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 210, 220),
                            1, cv2.LINE_AA)
                cv2.imshow("Driver Drowsiness Demo - Q or Esc to quit, R to reset", frame)

                key = cv2.waitKey(1) & 0xFF
                if key in (ord("q"), 27):
                    break
                if key == ord("r"):
                    monitor.reset()
                    was_drowsy = False
    finally:
        capture.release()
        cv2.destroyAllWindows()

    return 0


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Detect prolonged eye closure from a webcam or video file."
    )
    parser.add_argument(
        "--source",
        default="0",
        help="Camera index (default: 0) or path to a video file.",
    )
    parser.add_argument(
        "--ear-threshold",
        type=float,
        default=0.21,
        help="EAR value at or below which eye closure is measured (default: 0.21).",
    )
    parser.add_argument(
        "--closed-seconds",
        type=float,
        default=1.5,
        help="Continuous closure duration before alerting (default: 1.5).",
    )
    parser.add_argument("--no-sound", action="store_true", help="Disable the beep alert.")
    args = parser.parse_args()

    try:
        return run_demo(
            _parse_source(args.source),
            args.ear_threshold,
            args.closed_seconds,
            not args.no_sound,
        )
    except ValueError as error:
        parser.error(str(error))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())