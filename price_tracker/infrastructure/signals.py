"""Signal handling for graceful shutdown.

This module provides signal handling to gracefully stop the tracker
on SIGINT (Ctrl+C) and SIGTERM.
"""

import logging
import signal
from typing import Callable, Optional


class SignalHandler:
    """Handles shutdown signals for graceful termination."""

    def __init__(self):
        """Initialize signal handler."""
        self.logger = logging.getLogger(__name__)
        self.shutdown_callback: Optional[Callable] = None

    def register(self, callback: Callable):
        """Register callback for shutdown signals.

        Args:
            callback: Function to call on shutdown signals
        """
        self.shutdown_callback = callback
        signal.signal(signal.SIGINT, self._handle_signal)
        signal.signal(signal.SIGTERM, self._handle_signal)

    def register_shutdown_callback(self, callback: Callable):
        """Register callback for shutdown signals (alias for register).

        Args:
            callback: Function to call on shutdown signals
        """
        self.register(callback)

    def _handle_signal(self, signum: int, frame):
        """Handle shutdown signal.

        Args:
            signum: Signal number
            frame: Current stack frame
        """
        self.logger.info(f"Received signal {signum}, shutting down...")
        if self.shutdown_callback:
            self.shutdown_callback()
