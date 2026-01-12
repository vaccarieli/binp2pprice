"""Configuration management.

This module handles application configuration with validation and
loading from JSON files or dictionaries.
"""

import json
import logging
import os
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List


@dataclass
class OfferFilters:
    """Filters for P2P offers."""
    asset: str = "USDT"
    fiat: str = "VES"
    payment_methods: List[str] = field(default_factory=list)
    exclude_methods: List[str] = field(default_factory=lambda: ["Recarga Pines"])
    min_amount: Decimal = field(default_factory=lambda: Decimal(0))


@dataclass
class TelegramConfig:
    """Telegram bot configuration."""
    enabled: bool = False
    bot_token: str = ""
    chat_id: str = ""
    regular_updates: bool = True
    sudden_change_threshold: float = 5.0
    language: str = "en"


@dataclass
class Config:
    """Main application configuration."""

    # Core settings
    check_interval: int = 30
    alert_threshold: float = 2.0

    # Filters
    filters: OfferFilters = field(default_factory=OfferFilters)

    # Telegram
    telegram: TelegramConfig = field(default_factory=TelegramConfig)

    # Performance tuning
    max_retries: int = 3
    request_timeout: int = 10
    max_history: int = 1000
    backoff_multiplier: float = 2.0

    # Logging
    log_file: str = "price_tracker.log"
    log_level: str = "INFO"

    def __post_init__(self):
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self):
        """Validate configuration values."""
        # Validate intervals
        if self.check_interval < 10:
            raise ValueError("check_interval must be at least 10 seconds")
        if self.check_interval > 3600:
            raise ValueError("check_interval must not exceed 3600 seconds")

        # Validate threshold
        if self.alert_threshold < 0 or self.alert_threshold > 100:
            raise ValueError("alert_threshold must be between 0 and 100")

        # Validate min_amount
        if self.filters.min_amount < 0:
            raise ValueError("min_amount must be non-negative")

        # Validate log file path (prevent path traversal)
        if self.log_file:
            log_path = os.path.abspath(self.log_file)
            if not log_path.startswith(os.path.abspath(os.getcwd())):
                logging.warning(f"Log file path outside working directory: {log_path}")

            # Check for suspicious patterns
            if ".." in self.log_file or self.log_file.startswith("/etc") or self.log_file.startswith("C:\\Windows"):
                raise ValueError("Invalid log file path")

        # Validate Telegram configuration
        if self.telegram.enabled:
            if not self.telegram.bot_token or not self.telegram.chat_id:
                raise ValueError("Telegram enabled but missing bot token or chat ID")
            if self.telegram.sudden_change_threshold < 0 or self.telegram.sudden_change_threshold > 100:
                raise ValueError("telegram_sudden_change_threshold must be between 0 and 100")
            if self.telegram.language not in ["en", "es"]:
                raise ValueError("telegram_language must be 'en' (English) or 'es' (Spanish)")

    @classmethod
    def from_dict(cls, data: dict) -> "Config":
        """Create Config from dictionary.

        Args:
            data: Configuration dictionary

        Returns:
            Config instance
        """
        # Extract filter settings
        filters_data = {
            "asset": data.get("asset", "USDT"),
            "fiat": data.get("fiat", "VES"),
            "payment_methods": data.get("payment_methods", []),
            "exclude_methods": data.get("exclude_methods", ["Recarga Pines"]),
            "min_amount": Decimal(str(data.get("min_amount", 0)))
        }
        filters = OfferFilters(**filters_data)

        # Extract Telegram settings
        telegram_data = {
            "enabled": data.get("telegram_enabled", False),
            "bot_token": data.get("telegram_bot_token", ""),
            "chat_id": data.get("telegram_chat_id", ""),
            "regular_updates": data.get("telegram_regular_updates", True),
            "sudden_change_threshold": data.get("telegram_sudden_change_threshold", 5.0),
            "language": data.get("telegram_language", "en")
        }
        telegram = TelegramConfig(**telegram_data)

        # Create main config
        return cls(
            check_interval=data.get("check_interval", 30),
            alert_threshold=data.get("alert_threshold", 2.0),
            filters=filters,
            telegram=telegram,
            max_retries=data.get("max_retries", 3),
            request_timeout=data.get("request_timeout", 10),
            max_history=data.get("max_history", 1000),
            backoff_multiplier=data.get("backoff_multiplier", 2.0),
            log_file=data.get("log_file", "price_tracker.log"),
            log_level=data.get("log_level", "INFO")
        )

    @classmethod
    def from_file(cls, filepath: str) -> "Config":
        """Load configuration from JSON file.

        Args:
            filepath: Path to JSON configuration file

        Returns:
            Config instance

        Raises:
            FileNotFoundError: If file doesn't exist
            json.JSONDecodeError: If file is not valid JSON
        """
        with open(filepath, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)
