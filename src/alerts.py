"""Nonblocking single-channel audio alert with a timestamp-based cooldown."""

import logging
import math
from pathlib import Path

from src.contracts import DrowsinessResult


_LOG = logging.getLogger(__name__)


class AlertManager:
    def __init__(self, sound_path: str, cooldown_seconds: float = 3.0):
        if not math.isfinite(cooldown_seconds) or cooldown_seconds < 0:
            raise ValueError("cooldown_seconds must be finite and nonnegative")
        self.cooldown_seconds = cooldown_seconds
        self._last_played: float | None = None
        self._last_timestamp: float | None = None
        self._pygame = None
        self._sound = None
        self._channel = None
        self._owns_mixer = False

        path = Path(sound_path)
        if not path.is_file():
            _LOG.warning("Audio disabled: sound file does not exist: %s", path)
            return
        try:
            import pygame

            self._pygame = pygame
            if not pygame.mixer.get_init():
                pygame.mixer.init()
                self._owns_mixer = True
            self._sound = pygame.mixer.Sound(str(path))
        except Exception as exc:  # Audio failure must never stop the visual demo.
            _LOG.warning("Audio disabled: %s", exc)
            self._sound = None
            if self._owns_mixer:
                self._pygame.mixer.quit()
                self._owns_mixer = False

    def update(self, result: DrowsinessResult, timestamp: float) -> None:
        """Schedule at most one sound, leaving frame processing free to continue."""
        if not math.isfinite(timestamp):
            _LOG.warning("Ignoring nonfinite alert timestamp: %s", timestamp)
            return
        if self._last_timestamp is not None and timestamp < self._last_timestamp:
            self._stop()
            self._last_played = None
        self._last_timestamp = timestamp

        if not result.should_alert:
            self._stop()
            return
        if self._sound is None:
            return
        if self._channel is not None:
            try:
                if self._channel.get_busy():
                    return
            except Exception as exc:
                _LOG.warning("Audio channel failed: %s; visual alert continues", exc)
                self._channel = None
                self._sound = None
                return
        if self._last_played is not None and timestamp - self._last_played < self.cooldown_seconds:
            return
        try:
            channel = self._sound.play()
            if channel is None:
                _LOG.warning("Audio unavailable: no playback channel; visual alert continues")
                return
            self._channel = channel
            self._last_played = timestamp
        except self._pygame.error as exc:
            _LOG.warning("Audio playback failed: %s; visual alert continues", exc)
            self._sound = None

    def _stop(self) -> None:
        if self._channel is not None:
            try:
                self._channel.stop()
            except Exception as exc:
                _LOG.warning("Could not stop audio channel: %s", exc)
            self._channel = None

    def close(self) -> None:
        self._stop()
        if self._owns_mixer and self._pygame is not None:
            try:
                self._pygame.mixer.quit()
            except Exception as exc:
                _LOG.warning("Could not close audio mixer: %s", exc)
            self._owns_mixer = False
