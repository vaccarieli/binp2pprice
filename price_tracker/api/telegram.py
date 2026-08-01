"""Telegram Bot API client.

This module handles sending, editing, and deleting messages via Telegram Bot API.
"""

from typing import Optional, Tuple

import requests

from .base import BaseAPIClient


class TelegramClient(BaseAPIClient):
    """Client for Telegram Bot API operations."""

    def __init__(
        self,
        bot_token: str,
        chat_id: str,
        max_retries: int = 3,
        request_timeout: int = 10
    ):
        """Initialize Telegram client.

        Args:
            bot_token: Telegram bot token from BotFather
            chat_id: Chat ID to send messages to
            max_retries: Maximum number of retries
            request_timeout: Request timeout in seconds
        """
        super().__init__(max_retries, request_timeout)
        self.bot_token = bot_token
        self.chat_id = chat_id

    def send_message(self, text: str) -> Optional[int]:
        """Send a message to Telegram.

        Args:
            text: Message text (HTML format supported)

        Returns:
            Message ID if successful, None otherwise
        """
        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            response = self.session.post(url, json=payload, timeout=5)
            response.raise_for_status()
            result = response.json()
            message_id = result.get("result", {}).get("message_id")
            self.logger.info(
                f"Telegram message sent successfully (message_id: {message_id})"
            )
            return message_id

        except Exception as e:
            self.logger.error(f"Failed to send Telegram message: {e}")
            self._log_api_error(e)
            self.logger.debug(f"Message that failed: {text[:500]}")
            return None

    def edit_message(self, message_id: int, text: str) -> bool:
        """Edit an existing Telegram message.

        Args:
            message_id: ID of message to edit
            text: New message text (HTML format supported)

        Returns:
            True if successful (or content unchanged), False otherwise
        """
        success, _ = self.edit_message_detailed(message_id, text)
        return success

    def edit_message_detailed(
        self,
        message_id: int,
        text: str
    ) -> Tuple[bool, str]:
        """Edit a message and return (success, reason).

        reason is one of:
          - "ok": edited successfully
          - "not_modified": content identical (treat as success)
          - "missing": message_id empty
          - "not_found": message deleted / not found / can't edit
          - "error": other API/network error
        """
        if not message_id:
            return False, "missing"

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/editMessageText"
            payload = {
                "chat_id": self.chat_id,
                "message_id": message_id,
                "text": text,
                "parse_mode": "HTML",
                "disable_web_page_preview": True
            }
            response = self.session.post(url, json=payload, timeout=5)

            # Telegram returns 400 "message is not modified" when content is identical.
            # That is still a successful "keep editing this message" outcome.
            if response.status_code == 400:
                description = self._extract_error_description(response)
                if "message is not modified" in description.lower():
                    self.logger.debug(
                        f"Telegram message unchanged (message_id: {message_id})"
                    )
                    return True, "not_modified"
                if self._is_message_gone_error(description):
                    self.logger.warning(
                        f"Telegram message {message_id} no longer editable: {description}"
                    )
                    return False, "not_found"

            response.raise_for_status()
            self.logger.debug(
                f"Telegram message edited successfully (message_id: {message_id})"
            )
            return True, "ok"

        except requests.exceptions.HTTPError as e:
            description = ""
            if e.response is not None:
                description = self._extract_error_description(e.response)
            if self._is_message_gone_error(description):
                self.logger.warning(
                    f"Telegram message {message_id} gone/uneditable: {description}"
                )
                return False, "not_found"
            self.logger.error(f"Failed to edit Telegram message: {e}")
            self._log_api_error(e)
            self.logger.debug(f"Message that failed: {text[:500]}")
            return False, "error"

        except Exception as e:
            self.logger.error(f"Failed to edit Telegram message: {e}")
            self._log_api_error(e)
            self.logger.debug(f"Message that failed: {text[:500]}")
            return False, "error"

    def delete_message(self, message_id: int) -> bool:
        """Delete a Telegram message.

        Args:
            message_id: ID of message to delete

        Returns:
            True if successful, False otherwise
        """
        if not message_id:
            return False

        try:
            url = f"https://api.telegram.org/bot{self.bot_token}/deleteMessage"
            payload = {
                "chat_id": self.chat_id,
                "message_id": message_id
            }
            response = self.session.post(url, json=payload, timeout=5)
            response.raise_for_status()
            self.logger.debug(
                f"Telegram message deleted successfully (message_id: {message_id})"
            )
            return True

        except Exception as e:
            # Already-deleted messages are fine for our cleanup path.
            description = ""
            if hasattr(e, "response") and e.response is not None:
                description = self._extract_error_description(e.response)
            if self._is_message_gone_error(description):
                self.logger.debug(
                    f"Telegram message {message_id} already gone: {description}"
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
                    f"Telegram response text: "
                    f"{error.response.text if hasattr(error.response, 'text') else 'N/A'}"
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
            "chat not found",
            "bot was kicked",
            "bot is not a member",
            "have no rights to send a message",
            "not enough rights",
            "group chat was upgraded to a supergroup chat",
        )
        return any(marker in text for marker in markers)
