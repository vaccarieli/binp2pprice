"""Telegram Bot API client.

This module handles sending, editing, and deleting messages via Telegram Bot API.

Edit failures are classified carefully so callers do not create duplicate
messages on transient network timeouts.
"""

from __future__ import annotations

import time
from typing import Optional, Tuple

import requests

from .base import BaseAPIClient


class TelegramClient(BaseAPIClient):
    """Client for Telegram Bot API operations."""

    # Reasons returned by edit_message_detailed / edit_with_retries
    REASON_OK = "ok"
    REASON_NOT_MODIFIED = "not_modified"
    REASON_MISSING = "missing"
    REASON_NOT_FOUND = "not_found"      # message truly gone → safe to recreate
    REASON_TRANSIENT = "transient"      # timeout/network/5xx → keep old ID, do NOT recreate
    REASON_ERROR = "error"              # other permanent-ish API error

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        max_retries: int = 3,
        request_timeout: int = 15,
    ):
        super().__init__(max_retries, request_timeout)
        self.bot_token = bot_token
        self.chat_id = chat_id
        self._http_timeout = max(10, int(request_timeout or 15))

    def send_message(self, text: str) -> Optional[int]:
        """Send a message to Telegram. Returns message_id or None."""
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            response = self.session.post(
                url, json=payload, timeout=self._http_timeout
            )
            response.raise_for_status()
            result = response.json()
            message_id = result.get("result", {}).get("message_id")
            self.logger.info(
                "Telegram message sent successfully (message_id: %s)", message_id
            )
            return message_id

        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            self._log_api_error(e)
            self.logger.debug(f"Message that failed: {text[:500]}")
            return None

    def edit_message(self, message_id: int, text: str) -> bool:
        """Edit an existing Telegram message. True if success/unchanged."""
        success, _ = self.edit_message_detailed(message_id, text)
        return success

    def edit_message_detailed(
        self,
        message_id: int,
        text: str,
    ) -> Tuple[bool, str]:
        """Edit a message and return (success, reason).

        reason is one of:
          - ok / not_modified: success (keep editing this id)
          - missing: no message_id
          - not_found: message deleted / uneditable (safe to create a new one)
          - transient: timeout/network/5xx (MUST keep old id; do not create new)
          - error: other API failure (prefer keep old id; do not create new)
        """
        if not message_id:
            return False, self.REASON_MISSING

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
            payload = {
                "chat_id": self.chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            }
            response = self.session.post(
                url, json=payload, timeout=self._http_timeout
            )

            if response.status_code == 400:
                description = self._extract_error_description(response)
                lower = description.lower()
                if "message is not modified" in lower:
                    self.logger.debug(
                        "Telegram message unchanged (message_id: %s)", message_id
                    )
                    return True, self.REASON_NOT_MODIFIED
                if self._is_message_gone_error(description):
                    self.logger.warning(
                        "Telegram message %s no longer editable: %s",
                        message_id,
                        description,
                    )
                    return False, self.REASON_NOT_FOUND
                # Other 400s (e.g. parse errors) — do not recreate
                self.logger.error(
                    "Telegram edit rejected (message_id=%s): %s",
                    message_id,
                    description,
                )
                return False, self.REASON_ERROR

            if response.status_code in (429, 500, 502, 503, 504):
                self.logger.warning(
                    "Telegram edit transient HTTP %s (message_id=%s)",
                    response.status_code,
                    message_id,
                )
                return False, self.REASON_TRANSIENT

            response.raise_for_status()
            self.logger.debug(
                "Telegram message edited successfully (message_id: %s)", message_id
            )
            return True, self.REASON_OK

        except (
            requests.exceptions.Timeout,
            requests.exceptions.ConnectionError,
            requests.exceptions.ChunkedEncodingError,
        ) as e:
            self.logger.warning(
                "Telegram edit transient network error (message_id=%s): %s",
                message_id,
                e,
            )
            return False, self.REASON_TRANSIENT

        except requests.exceptions.HTTPError as e:
            description = ""
            status = e.response.status_code if e.response is not None else None
            if e.response is not None:
                description = self._extract_error_description(e.response)
            if self._is_message_gone_error(description):
                self.logger.warning(
                    "Telegram message %s gone/uneditable: %s",
                    message_id,
                    description,
                )
                return False, self.REASON_NOT_FOUND
            if status in (429, 500, 502, 503, 504):
                self.logger.warning(
                    "Telegram edit transient HTTP %s (message_id=%s)",
                    status,
                    message_id,
                )
                return False, self.REASON_TRANSIENT
            self.logger.error(f"Failed to edit Telegram message: {e}")
            self._log_api_error(e)
            return False, self.REASON_ERROR

        except Exception as e:
            # Unknown — treat as transient to avoid duplicate spam
            self.logger.error(f"Failed to edit Telegram message: {e}")
            self._log_api_error(e)
            return False, self.REASON_TRANSIENT

    def edit_with_retries(
        self,
        message_id: int,
        text: str,
        max_attempts: int = 3,
        base_delay: float = 1.0,
    ) -> Tuple[bool, str]:
        """Edit with retries on transient failures only.

        Returns (success, final_reason). Never returns success=False with
        reason=transient after exhausting retries without also logging it —
        caller must NOT create a new message unless reason is not_found/missing.
        """
        last_reason = self.REASON_ERROR
        for attempt in range(1, max_attempts + 1):
            success, reason = self.edit_message_detailed(message_id, text)
            if success:
                return True, reason
            last_reason = reason
            if reason != self.REASON_TRANSIENT:
                return False, reason
            if attempt < max_attempts:
                delay = base_delay * attempt
                self.logger.warning(
                    "Retrying Telegram edit id=%s in %.1fs (attempt %s/%s)",
                    message_id,
                    delay,
                    attempt,
                    max_attempts,
                )
                time.sleep(delay)
        return False, last_reason

    def delete_message(self, message_id: int) -> bool:
        """Delete a Telegram message. True if deleted or already gone."""
        if not message_id:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/deleteMessage"
            payload = {
                "chat_id": self.chat_id,
                "message_id": message_id,
            }
            response = self.session.post(
                url, json=payload, timeout=self._http_timeout
            )
            response.raise_for_status()
            self.logger.debug(
                "Telegram message deleted successfully (message_id: %s)", message_id
            )
            return True

        except Exception as e:
            description = ""
            if hasattr(e, "response") and e.response is not None:
                description = self._extract_error_description(e.response)
            if self._is_message_gone_error(description):
                self.logger.debug(
                    "Telegram message %s already gone: %s", message_id, description
                )
                return True
            self.logger.error(f"Failed to delete Telegram message: {e}")
            return False

    def _log_api_error(self, error: Exception) -> None:
        if hasattr(error, "response") and error.response is not None:
            try:
                error_detail = error.response.json()
                self.logger.error(f"Telegram API error details: {error_detail}")
            except Exception:
                self.logger.error(
                    "Telegram response text: %s",
                    error.response.text if hasattr(error.response, "text") else "N/A",
                )

    @staticmethod
    def _extract_error_description(response) -> str:
        try:
            data = response.json()
            return str(data.get("description", "") or "")
        except Exception:
            try:
                return str(response.text or "")
            except Exception:
                return ""

    @staticmethod
    def _is_message_gone_error(description: str) -> bool:
        """Detect errors that mean the target message can no longer be used."""
        if not description:
            return False
        text = description.lower()
        markers = (
            "message to edit not found",
            "message to delete not found",
            "message can't be edited",
            "message can't be deleted",
            "message identifier is not specified",
            "message_id_invalid",
            "message to edit not found",
            "chat not found",
            "bot was kicked",
            "bot is not a member",
            "have no rights to send a message",
            "not enough rights",
            "group chat was upgraded to a supergroup chat",
        )
        return any(marker in text for marker in markers)
