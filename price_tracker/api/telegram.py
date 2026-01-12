"""Telegram Bot API client.

This module handles sending, editing, and deleting messages via Telegram Bot API.
"""

from typing import Optional

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
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    self.logger.error(f"Telegram API error details: {error_detail}")
                except:
                    self.logger.error(
                        f"Telegram response text: "
                        f"{e.response.text if hasattr(e.response, 'text') else 'N/A'}"
                    )
            self.logger.debug(f"Message that failed: {text[:500]}")
            return None

    def edit_message(self, message_id: int, text: str) -> bool:
        """Edit an existing Telegram message.

        Args:
            message_id: ID of message to edit
            text: New message text (HTML format supported)

        Returns:
            True if successful, False otherwise
        """
        if not message_id:
            return False

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
            response.raise_for_status()
            self.logger.debug(
                f"Telegram message edited successfully (message_id: {message_id})"
            )
            return True

        except Exception as e:
            self.logger.error(f"Failed to edit Telegram message: {e}")
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                    self.logger.error(f"Telegram API error details: {error_detail}")
                except:
                    self.logger.error(
                        f"Telegram response text: "
                        f"{e.response.text if hasattr(e.response, 'text') else 'N/A'}"
                    )
            self.logger.debug(f"Message that failed: {text[:500]}")
            return False

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
            self.logger.error(f"Failed to delete Telegram message: {e}")
            return False
