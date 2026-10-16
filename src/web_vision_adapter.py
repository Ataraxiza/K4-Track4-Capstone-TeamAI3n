"""Bridge the A Face Mesh demo and B detector to the localhost C UI."""

from __future__ import annotations

import math
import hashlib
import importlib.metadata
import importlib.util
import os
from pathlib import Path
import shutil
import sys
import tempfile

import cv2
import numpy as np


def _load_mediapipe():
    """Work around MediaPipe's native resource lookup on non-ASCII Windows paths."""
    if "mediapipe" not in sys.modules and os.name == "nt":
        spec = importlib.util.find_spec("mediapipe")
        if spec is not None and spec.submodule_search_locations:
            package = Path(next(iter(spec.submodule_search_locations)))
            if not str(package).isascii():
                version = importlib.metadata.version("mediapipe")
                source_id = hashlib.sha256(str(package).encode("utf-8")).hexdigest()[:10]
                stage = Path(tempfile.gettempdir()) / f"ai3n-mediapipe-{version}-{source_id}"
                marker = stage / "ready.txt"
                if not marker.exists():
                    shutil.copytree(package, stage / "mediapipe", dirs_exist_ok=True)
                    marker.write_text(str(package), encoding="utf-8")
                sys.path.insert(0, str(stage))

    # MediaPipe's optional doc generator imports any global TensorFlow installation.
    # This machine's global TensorFlow/NumPy pair is incompatible; it is not needed.
    had_tensorflow = "tensorflow" in sys.modules
    original_tensorflow = sys.modules.get("tensorflow")
    sys.modules["tensorflow"] = None
    try:
        import mediapipe
    finally:
        if had_tensorflow:
            sys.modules["tensorflow"] = original_tensorflow
        else:
            sys.modules.pop("tensorflow", None)
    return mediapipe


mp = _load_mediapipe()

from drowsiness_detector import LEFT_EYE, RIGHT_EYE, eye_aspect_ratio, select_closest_face
from src.contracts import DrowsinessResult, FaceObservation
from src.drowsiness import DrowsinessDetector


class RealPipeline:
    def __init__(self, settings: dict[str, float]) -> None:
        if not hasattr(mp, "solutions"):
            raise RuntimeError("MediaPipe solutions.FaceMesh is unavailable in this installation")
        self.mesh = mp.solutions.face_mesh.FaceMesh(
            max_num_faces=5,
            refine_landmarks=True,
            min_detection_confidence=0.5,
            min_tracking_confidence=0.5,
        )
        self.configure(settings)

    def configure(self, settings: dict[str, float]) -> None:
        detector = DrowsinessDetector(**settings)
        self.settings = settings.copy()
        self.detector = detector

    def reset(self) -> None:
        self.detector.reset()

    def analyze(self, timestamp: float, _status: str, frame: bytes | None) -> tuple[FaceObservation, DrowsinessResult]:
        if not frame:
            raise ValueError("Missing JPEG frame")
        image = cv2.imdecode(np.frombuffer(frame, dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError("Invalid JPEG frame")
        height, width = image.shape[:2]
        rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        rgb.flags.writeable = False
        mesh_result = self.mesh.process(rgb)
        faces = [face.landmark for face in (mesh_result.multi_face_landmarks or [])]
        target = select_closest_face(faces)
        if target is None:
            observation = FaceObservation(timestamp, False)
        else:
            left = self._eye(target, LEFT_EYE, width, height)
            right = self._eye(target, RIGHT_EYE, width, height)
            try:
                # EAR needs pixel coordinates: normalized x/y distort a non-square frame.
                left_ear = eye_aspect_ratio(left)
                right_ear = eye_aspect_ratio(right)
            except ValueError:
                left_ear = right_ear = math.nan
            observation = FaceObservation(
                timestamp, True, left_ear, right_ear,
                tuple((round(x), round(y)) for x, y in left),
                tuple((round(x), round(y)) for x, y in right),
            )
        return observation, self.detector.update(observation)

    @staticmethod
    def _eye(landmarks: list, indices: tuple[int, ...], width: int, height: int) -> list[tuple[float, float]]:
        return [(landmarks[index].x * width, landmarks[index].y * height) for index in indices]

    def close(self) -> None:
        self.mesh.close()
