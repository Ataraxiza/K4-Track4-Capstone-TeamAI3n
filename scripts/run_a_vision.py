"""Launch A's standalone demo with MediaPipe resources staged for this machine."""

from src import web_vision_adapter  # noqa: F401 - prepares MediaPipe import path
from drowsiness_detector import main


if __name__ == "__main__":
    raise SystemExit(main())
