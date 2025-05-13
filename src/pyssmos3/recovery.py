"""Recovery manager module for failure handling with automatic retries.

This module defines the `RecoveryManager` class, which monitors for failure
events in the background and triggers a user-defined recovery function. If the
recovery fails more than a specified number of times, it invokes a callback
to handle critical failure and stops the client gracefully.
"""

import logging
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)


class RecoveryManager:
    """
    Monitors failure events and performs automatic recovery with retries.

    The monitoring runs in a background daemon thread. When a failure event is
    triggered, the manager calls the specified recovery function. If the
    recovery function fails more than a configurable number of consecutive
    attempts, a critical failure callback is invoked and monitoring stops.

    Attributes:
        is_recovery_failed (bool): Indicates whether the recovery process has
            permanently failed after exceeding maximum retries.
    """

    def __init__(self, on_failed: Callable[[], None]) -> None:
        """
        Initializes the RecoveryManager.

        Args:
            on_failed (Callable[[], None]): Callback to invoke when recovery
                permanently fails after maximum retry attempts.
        """
        self.is_recovery_failed: bool = False
        self._callback_on_failed: Callable[[], None] = on_failed
        self._recovery_event: threading.Event = threading.Event()
        self._fail_count: int = 0
        self._stop_thread: bool = False
        self._thread: threading.Thread | None = None

    def start_monitoring(
        self, recovery_function: Callable[[], None], max_retries: int, interval: int
    ) -> None:
        """Starts a daemon thread to monitor and trigger recovery on failure events.

        Launches a background thread that waits for the internal recovery event to be set.
        When triggered, it attempts to call the provided recovery function. If recovery
        fails consecutively more than `max_try` times, the failure callback is invoked
        and monitoring stops.

        Args:
            recovery_function (Callable[[], None]): The recovery function to invoke upon failure.
            max_retries (int): Maximum number of allowed recovery attempts before critical failure.
            interval (int): Number of seconds to wait between recovery attempts.

        Raises:
            RuntimeError: If the recovery thread is already running.
        """

        def monitoring_loop() -> None:
            while not self._stop_thread:
                self._recovery_event.wait()
                self._recovery_event.clear()
                if self._stop_thread:
                    break
                if self._fail_count >= max_retries:
                    logger.error("Recovery failed more than %s times.", max_retries)
                    self.is_recovery_failed = True
                    self._callback_on_failed()
                    break
                self._fail_count += 1
                logger.info(
                    "Recovery after %s seconds. fail_count: %s",
                    interval,
                    self._fail_count,
                )
                time.sleep(interval)
                recovery_function()

        if self._thread and self._thread.is_alive():
            raise RuntimeError("Recovery thread already running.")
        self.is_recovery_failed = False
        self._stop_thread = False
        self._fail_count = 0
        self._thread = threading.Thread(target=monitoring_loop, daemon=True)
        self._thread.start()
        logger.debug("Recovery thread started.")

    def stop_monitoring(self) -> None:
        """Stops the recovery monitoring thread.

        Sets the stop flag and unblocks the waiting thread so it can terminate gracefully.

        Raises:
            RuntimeError: If recovery thread is not running.
        """
        if not (self._thread and self._thread.is_alive()):
            raise RuntimeError("Recovery thread is not running.")
        self._stop_thread = True
        self._recovery_event.set()
        self._thread.join()
        logger.debug("Recovery thread stopped.")

    def perform_recovery(self) -> None:
        """Triggers a recovery attempt.

        This method sets the internal event flag to initiate recovery
        in the background monitoring thread.
        """
        self._recovery_event.set()

    def is_running(self) -> bool:
        """Checks whether the recovery monitoring thread is currently active.

        Returns:
            bool: True if the thread is alive; False otherwise.
        """
        return bool(self._thread and self._thread.is_alive())

    def reset_fail_count(self) -> None:
        """Resets the internal counter for consecutive recovery failures.

        This should be called after a successful recovery to prevent unnecessary
        escalation on future failure events.
        """
        self._fail_count = 0
