"""Persistence for Telegram runtime state.

Stores message IDs and alert baselines so restarts can resume editing
the same status message instead of creating duplicates.
"""

from __future__ import annotations

import json
import logging
import os
from dataclasses import asdict, dataclass
from datetime import datetime
from typing import Optional


DEFAULT_STATE_FILE = "telegram_state.json"


@dataclass
class TelegramState:
    """Serializable Telegram runtime state."""

    chat_id: str = ""
    status_message_id: Optional[int] = None
    buy_alert_message_id: Optional[int] = None
    sell_alert_message_id: Optional[int] = None
    buy_baseline: Optional[float] = None
    sell_baseline: Optional[float] = None
    last_updated: Optional[str] = None


class TelegramStateStore:
    """Load and save Telegram state to a local JSON file."""

    def __init__(self, filename: str = DEFAULT_STATE_FILE):
        self.filename = filename
        self.logger = logging.getLogger(__name__)

    def load(self, expected_chat_id: Optional[str] = None) -> TelegramState:
        """Load state from disk.

        If expected_chat_id is provided and differs from the stored chat_id,
        returns a fresh state (message IDs are chat-specific).
        """
        if not os.path.exists(self.filename):
            self.logger.info("No Telegram state file found; starting fresh")
            return TelegramState(chat_id=expected_chat_id or "")

        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                data = json.load(f)

            state = TelegramState(
                chat_id=str(data.get("chat_id") or ""),
                status_message_id=self._as_optional_int(data.get("status_message_id")),
                buy_alert_message_id=self._as_optional_int(
                    data.get("buy_alert_message_id")
                ),
                sell_alert_message_id=self._as_optional_int(
                    data.get("sell_alert_message_id")
                ),
                buy_baseline=self._as_optional_float(data.get("buy_baseline")),
                sell_baseline=self._as_optional_float(data.get("sell_baseline")),
                last_updated=data.get("last_updated"),
            )

            if expected_chat_id and state.chat_id and state.chat_id != str(expected_chat_id):
                self.logger.warning(
                    "Telegram chat_id changed (%s -> %s); discarding old message IDs",
                    state.chat_id,
                    expected_chat_id,
                )
                return TelegramState(chat_id=str(expected_chat_id))

            if expected_chat_id and not state.chat_id:
                state.chat_id = str(expected_chat_id)

            self.logger.info(
                "Loaded Telegram state: status_msg=%s buy_alert=%s sell_alert=%s "
                "buy_baseline=%s sell_baseline=%s",
                state.status_message_id,
                state.buy_alert_message_id,
                state.sell_alert_message_id,
                state.buy_baseline,
                state.sell_baseline,
            )
            return state

        except Exception as e:
            self.logger.error(f"Error loading Telegram state: {e}")
            return TelegramState(chat_id=expected_chat_id or "")

    def save(self, state: TelegramState) -> None:
        """Atomically persist Telegram state to disk."""
        state.last_updated = datetime.now().isoformat()
        data = asdict(state)

        try:
            temp_filename = f"{self.filename}.tmp"
            with open(temp_filename, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            os.replace(temp_filename, self.filename)
            self.logger.debug(
                "Saved Telegram state to %s (status_msg=%s)",
                self.filename,
                state.status_message_id,
            )
        except Exception as e:
            self.logger.error(f"Error saving Telegram state: {e}")

    @staticmethod
    def _as_optional_int(value) -> Optional[int]:
        if value is None or value == "":
            return None
        try:
            return int(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _as_optional_float(value) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None
