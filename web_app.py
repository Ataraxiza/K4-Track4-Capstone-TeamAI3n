"""Local browser demo and recording UI. Bind only to this computer."""

from __future__ import annotations

import argparse
import logging
import math
import threading
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory

from src.contracts import DrowsinessResult, FaceObservation


ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
STATUSES = ("NORMAL", "EYES_CLOSED", "DROWSY", "NO_FACE")
DEFAULTS = {"ear_threshold": 0.22, "closed_seconds": 2.0, "max_gap_seconds": 0.5}


def _number(value: object, name: str, *, positive: bool = True) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not math.isfinite(number) or (number <= 0 if positive else number < 0):
        raise ValueError(f"{name} must be finite and {'positive' if positive else 'nonnegative'}")
    return number


def _payload(observation: FaceObservation, result: DrowsinessResult) -> dict:
    def safe_ear(value: float | None) -> float | None:
        return value if value is not None and math.isfinite(value) else None

    return {
        "timestamp": observation.timestamp,
        "face_detected": observation.face_detected,
        "ear_left": safe_ear(observation.ear_left),
        "ear_right": safe_ear(observation.ear_right),
        "left_eye_points": observation.left_eye_points,
        "right_eye_points": observation.right_eye_points,
        "status": result.status,
        "closed_duration": result.closed_duration,
        "should_alert": result.should_alert,
    }


class MockPipeline:
    def __init__(self) -> None:
        self.settings = DEFAULTS.copy()

    def configure(self, settings: dict) -> None:
        self.settings = settings

    def reset(self) -> None:
        pass

    def analyze(self, timestamp: float, status: str, _frame: bytes | None) -> tuple[FaceObservation, DrowsinessResult]:
        if status not in STATUSES:
            raise ValueError(f"Unknown mock status: {status}")
        ear = {"NORMAL": 0.31, "EYES_CLOSED": 0.15, "DROWSY": 0.14, "NO_FACE": None}[status]
        duration = {"NORMAL": 0.0, "EYES_CLOSED": 0.8, "DROWSY": 2.3, "NO_FACE": 0.0}[status]
        observation = FaceObservation(timestamp, status != "NO_FACE", ear, ear)
        result = DrowsinessResult(status, duration, status == "DROWSY")
        return observation, result

    def close(self) -> None:
        pass


def create_app(mode: str = "real") -> Flask:
    if mode == "real":
        from src.web_vision_adapter import RealPipeline

        pipeline = RealPipeline(DEFAULTS)
    elif mode == "mock":
        pipeline = MockPipeline()
    else:
        raise ValueError(f"Unknown mode: {mode}")
    lock = threading.Lock()
    app = Flask(__name__, static_folder=str(WEB), static_url_path="/static")
    app.config["pipeline"] = pipeline

    @app.get("/")
    def home():
        return send_from_directory(WEB, "index.html")

    @app.get("/api/health")
    def health():
        return jsonify({"mode": mode, "settings": pipeline.settings})

    @app.post("/api/config")
    def config():
        data = request.get_json(silent=True) or {}
        try:
            settings = {
                name: _number(data.get(name, DEFAULTS[name]), name)
                for name in DEFAULTS
            }
            with lock:
                pipeline.configure(settings)
        except (ValueError, TypeError) as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify({"settings": settings})

    @app.post("/api/reset")
    def reset():
        with lock:
            pipeline.reset()
        return jsonify({"ok": True})

    @app.post("/api/analyze")
    def analyze():
        try:
            timestamp = _number(request.form.get("timestamp"), "timestamp", positive=False)
            status = request.form.get("mock_status", "NORMAL")
            uploaded = request.files.get("frame")
            frame_bytes = uploaded.read(2_000_001) if uploaded else None
            if frame_bytes and len(frame_bytes) > 2_000_000:
                raise ValueError("JPEG frame exceeds 2 MB")
            with lock:
                observation, result = pipeline.analyze(timestamp, status, frame_bytes)
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(_payload(observation, result))

    return app


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--mode", choices=("real", "mock"), default="real")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("--port must be between 1 and 65535")
    try:
        app = create_app(args.mode)
    except (ImportError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Real detection unavailable: {exc}\nInstall MediaPipe or use --mode mock.\n")
    print(f"Local {args.mode} demo: http://127.0.0.1:{args.port}", flush=True)
    logging.getLogger("werkzeug").setLevel(logging.ERROR)
    try:
        app.run(host="127.0.0.1", port=args.port, debug=False, use_reloader=False, threaded=True)
    finally:
        app.config["pipeline"].close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
