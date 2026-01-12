"""Price history persistence.

This module handles saving and loading price history to/from JSON files.
"""

import json
import logging
import os
from collections import deque
from datetime import datetime
from typing import Tuple


class HistoryPersistence:
    """Handles saving and loading price history."""

    def __init__(self, asset: str, fiat: str):
        """Initialize history persistence.

        Args:
            asset: Crypto asset (e.g., "USDT")
            fiat: Fiat currency (e.g., "VES")
        """
        self.asset = asset
        self.fiat = fiat
        self.logger = logging.getLogger(__name__)
        self.filename = f"price_history_{fiat}_{asset}.json"

    def save_history(self, price_history: deque, config):
        """Save price history to file.

        Args:
            price_history: Deque of (timestamp, buy, sell) tuples
            config: Config object with settings
        """
        data = {
            "last_updated": datetime.now().isoformat(),
            "config": {
                "asset": self.asset,
                "fiat": self.fiat,
                "check_interval": config.check_interval,
                "alert_threshold": config.alert_threshold
            },
            "history": [
                {
                    "timestamp": ts.isoformat(),
                    "buy": buy,
                    "sell": sell
                }
                for ts, buy, sell in price_history
            ]
        }

        try:
            # Atomic write
            temp_filename = f"{self.filename}.tmp"
            with open(temp_filename, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_filename, self.filename)
            self.logger.info(
                f"Saved {len(price_history)} readings to {self.filename}"
            )

        except Exception as e:
            self.logger.error(f"Error saving history: {e}")

    def load_history(self, price_history: deque):
        """Load price history from file into provided deque.

        Only loads recent history (last 24 hours).

        Args:
            price_history: Deque to populate with loaded history
        """
        price_history.clear()  # Clear any existing data

        if not os.path.exists(self.filename):
            self.logger.info("No history file found, starting fresh")
            return

        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                data = json.load(f)

            loaded = 0
            for entry in data.get("history", []):
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    # Only load recent history (last 24 hours)
                    if (datetime.now() - ts).total_seconds() < 86400:
                        price_history.append((ts, entry["buy"], entry["sell"]))
                        loaded += 1
                except (ValueError, KeyError) as e:
                    self.logger.warning(
                        f"Skipping invalid history entry: {e}"
                    )
                    continue

            self.logger.info(
                f"Loaded {loaded} historical readings from last 24h"
            )

        except Exception as e:
            self.logger.error(f"Error loading history: {e}")
