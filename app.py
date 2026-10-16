"""Run the driver drowsiness demo with a webcam or a video file."""

import argparse
import importlib
import logging
import math
import time
from pathlib import Path

import cv2

from src.alerts import AlertManager
from src.contracts import DrowsinessResult, FaceObservation
from src.overlay import draw_overlay


_LOG = logging.getLogger(__name__)
_DEFAULT_SOUND = Path(__file__).resolve().parent / "assets" / "alarm.wav"
_WINDOW = "Drowsiness alert - Q/Esc quit, R restart video"


def make_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--camera", type=int, default=0, metavar="INDEX", help="Webcam index (default: 0)")
    source.add_argument("--video", type=Path, metavar="PATH", help="Video file instead of webcam")
    parser.add_argument("--ear-threshold", type=float, default=0.22)
    parser.add_argument("--closed-seconds", type=float, default=2.0)
    parser.add_argument("--max-gap-seconds", type=float, default=0.5)
    parser.add_argument("--model", type=Path, help="Model file if required by FaceAnalyzer")
    parser.add_argument("--sound", type=Path, default=_DEFAULT_SOUND)
    parser.add_argument("--cooldown-seconds", type=float, default=3.0)
    return parser


def _load_backends():
    try:
        vision = importlib.import_module("src.vision")
        drowsiness = importlib.import_module("src.drowsiness")
        return vision.FaceAnalyzer, drowsiness.DrowsinessDetector
    except (ImportError, AttributeError) as exc:
        raise RuntimeError(
            "A/B backend unavailable or incompatible. Add src/vision.py and "
            "src/drowsiness.py with the signatures in src/contracts.py; "
            f"original error: {exc}"
        ) from exc


def _video_timestamp(capture: cv2.VideoCapture, frame_index: int, fps: float) -> float:
    if math.isfinite(fps) and fps > 0:
        return (frame_index - 1) / fps
    position_ms = capture.get(cv2.CAP_PROP_POS_MSEC)
    if math.isfinite(position_ms) and position_ms >= 0:
        return position_ms / 1000.0
    raise RuntimeError("Video has neither valid FPS nor valid content timestamp")


def run(args: argparse.Namespace) -> int:
    if args.camera is not None and args.camera < 0:
        raise ValueError("--camera must be a nonnegative index")
    if args.video is not None and not args.video.is_file():
        raise FileNotFoundError(f"Video file not found: {args.video}")
    if args.model is not None and not args.model.is_file():
        raise FileNotFoundError(f"Model file not found: {args.model}")
    for name in ("ear_threshold", "closed_seconds", "max_gap_seconds", "cooldown_seconds"):
        value = getattr(args, name)
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"--{name.replace('_', '-')} must be finite and nonnegative")
    if args.max_gap_seconds == 0:
        raise ValueError("--max-gap-seconds must be positive")

    FaceAnalyzer, DrowsinessDetector = _load_backends()
    capture = None
    analyzer = None
    alerts = None
    try:
        source = str(args.video) if args.video is not None else args.camera
        capture = cv2.VideoCapture(source)
        if not capture.isOpened():
            kind = "video" if args.video is not None else "camera"
            raise RuntimeError(f"Cannot open {kind}: {source}. Check path, device index and access permissions.")
        fps = capture.get(cv2.CAP_PROP_FPS) if args.video is not None else 0.0
        if args.video is not None and (not math.isfinite(fps) or fps <= 0):
            _LOG.warning("Video FPS invalid; using CAP_PROP_POS_MSEC content timestamps")
        elif args.video is not None and 1.0 / fps > args.max_gap_seconds:
            _LOG.warning(
                "Video frame interval %.3f s exceeds max_gap_seconds %.3f s; "
                "B will reset closed-eye sequences. Increase --max-gap-seconds if appropriate.",
                1.0 / fps, args.max_gap_seconds,
            )
        try:
            analyzer = FaceAnalyzer(model_path=str(args.model) if args.model is not None else None)
        except TypeError as exc:
            raise RuntimeError(
                "A interface mismatch: FaceAnalyzer must accept model_path. "
                f"Original error: {exc}"
            ) from exc
        try:
            detector = DrowsinessDetector(
                ear_threshold=args.ear_threshold,
                closed_seconds=args.closed_seconds,
                max_gap_seconds=args.max_gap_seconds,
            )
        except TypeError as exc:
            raise RuntimeError(
                "B interface mismatch: DrowsinessDetector must accept "
                "ear_threshold, closed_seconds, max_gap_seconds. "
                f"Original error: {exc}"
            ) from exc
        for owner, instance, names in (
            ("A", analyzer, ("analyze", "close")),
            ("B", detector, ("update", "reset")),
        ):
            for name in names:
                if not callable(getattr(instance, name, None)):
                    raise RuntimeError(f"{owner} interface mismatch: missing callable {name}()")
        alerts = AlertManager(str(args.sound), cooldown_seconds=args.cooldown_seconds)
        frame_index = 0
        previous_timestamp = None
        previous_wall = None
        processing_fps = 0.0

        while True:
            ok, frame = capture.read()
            if not ok:
                if args.video is None:
                    _LOG.warning("Camera stopped providing frames")
                else:
                    _LOG.info("Video ended after %d frames", frame_index)
                break
            frame_index += 1
            timestamp = (
                _video_timestamp(capture, frame_index, fps)
                if args.video is not None
                else time.monotonic()
            )
            if previous_timestamp is not None and timestamp <= previous_timestamp:
                detector.reset()
                _LOG.warning("Nonincreasing source timestamp; detector state reset")
                if args.video is not None and (not math.isfinite(fps) or fps <= 0):
                    raise RuntimeError("Video content timestamps are not increasing; cannot measure closed duration")
            previous_timestamp = timestamp

            observation = analyzer.analyze(frame, timestamp)
            if not isinstance(observation, FaceObservation):
                raise RuntimeError(
                    "A interface mismatch: analyze() must return src.contracts.FaceObservation"
                )
            result = detector.update(observation)
            if not isinstance(result, DrowsinessResult):
                raise RuntimeError(
                    "B interface mismatch: update() must return src.contracts.DrowsinessResult"
                )
            alerts.update(result, timestamp)
            display = draw_overlay(frame, observation, result)

            wall = time.monotonic()
            if previous_wall is not None and wall > previous_wall:
                instantaneous = 1.0 / (wall - previous_wall)
                processing_fps = instantaneous if processing_fps == 0 else 0.2 * instantaneous + 0.8 * processing_fps
            previous_wall = wall
            cv2.putText(display, f"Processing FPS: {processing_fps:.1f}",
                        (12, display.shape[0] - 14), cv2.FONT_HERSHEY_SIMPLEX,
                        0.55, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.imshow(_WINDOW, display)
            key = cv2.waitKey(1) & 0xFF
            if key in (ord("q"), 27):
                break
            if key == ord("r") and args.video is not None:
                if not capture.set(cv2.CAP_PROP_POS_FRAMES, 0):
                    _LOG.warning("Video backend cannot rewind this file")
                    continue
                detector.reset()
                alerts.update(DrowsinessResult("NO_FACE", 0.0, False), 0.0)
                frame_index = 0
                previous_timestamp = None
                previous_wall = None
                processing_fps = 0.0
                _LOG.info("Video restarted; detector state reset")
        return 0
    finally:
        for label, action in (
            ("audio", alerts.close if alerts is not None else None),
            ("vision", getattr(analyzer, "close", None) if analyzer is not None else None),
            ("capture", capture.release if capture is not None else None),
            ("windows", cv2.destroyAllWindows),
        ):
            if action is not None:
                try:
                    action()
                except Exception as exc:
                    _LOG.warning("Could not clean up %s: %s", label, exc)


def main() -> int:
    parser = make_parser()
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    try:
        return run(args)
    except (FileNotFoundError, ValueError, RuntimeError, cv2.error) as exc:
        parser.exit(1, f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
