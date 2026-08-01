"""
Alert Service Module

Handles alert generation and delivery for price changes.
Manages both sudden change alerts and regular status updates.
"""

import logging
from typing import Optional, Dict, List

from price_tracker.api.telegram import TelegramClient
from price_tracker.presentation.formatters import TelegramFormatter
from price_tracker.infrastructure.telegram_state import (
    TelegramState,
    TelegramStateStore,
)


class AlertService:
    """
    Service for managing price alerts and notifications.

    This service handles:
    - Detecting sudden price changes against baselines
    - Sending alert messages via Telegram
    - Sending regular status updates
    - Logging alerts to persistent storage
    - Persisting Telegram message IDs so restarts keep editing
      the same status message instead of creating duplicates
    """

    def __init__(
        self,
        telegram_client: Optional[TelegramClient],
        formatter: TelegramFormatter,
        sudden_change_threshold: float = 5.0,
        state_store: Optional[TelegramStateStore] = None,
    ):
        """
        Initialize the alert service.

        Args:
            telegram_client: Client for sending Telegram messages (None if disabled)
            formatter: Formatter for creating Telegram message text
            sudden_change_threshold: Percentage threshold for sudden change alerts
            state_store: Optional store for persisting Telegram message IDs/baselines
        """
        self.telegram_client = telegram_client
        self.formatter = formatter
        self.sudden_change_threshold = sudden_change_threshold
        self.logger = logging.getLogger(__name__)

        chat_id = ""
        if telegram_client is not None:
            chat_id = str(getattr(telegram_client, "chat_id", "") or "")

        self.state_store = state_store or TelegramStateStore()
        self.state: TelegramState = self.state_store.load(expected_chat_id=chat_id)
        if chat_id:
            self.state.chat_id = chat_id

        # Baseline tracking for sudden change detection (restored from disk)
        self.telegram_buy_baseline: Optional[float] = self.state.buy_baseline
        self.telegram_sell_baseline: Optional[float] = self.state.sell_baseline

        # Message ID tracking for editing/deleting messages (restored from disk)
        self.last_telegram_message_id: Optional[int] = self.state.status_message_id
        self.last_buy_alert_message_id: Optional[int] = self.state.buy_alert_message_id
        self.last_sell_alert_message_id: Optional[int] = self.state.sell_alert_message_id

        if self.last_telegram_message_id:
            self.logger.info(
                "Resuming Telegram status message id=%s (will edit if still exists)",
                self.last_telegram_message_id,
            )

        # Setup dedicated alerts logger
        self.alerts_logger = self._setup_alerts_logger()

    def _persist_state(self) -> None:
        """Write current in-memory Telegram state to disk."""
        self.state.status_message_id = self.last_telegram_message_id
        self.state.buy_alert_message_id = self.last_buy_alert_message_id
        self.state.sell_alert_message_id = self.last_sell_alert_message_id
        self.state.buy_baseline = self.telegram_buy_baseline
        self.state.sell_baseline = self.telegram_sell_baseline
        if self.telegram_client is not None:
            self.state.chat_id = str(self.telegram_client.chat_id)
        self.state_store.save(self.state)

    def _setup_alerts_logger(self) -> logging.Logger:
        """
        Setup dedicated logger for BUY/SELL alerts.

        Creates a separate log file (alerts_history.log) for tracking
        all price alerts with detailed information.

        Returns:
            Configured logger instance
        """
        alerts_logger = logging.getLogger('alerts')
        alerts_logger.setLevel(logging.INFO)

        # Create file handler for alerts
        alerts_file = 'alerts_history.log'
        file_handler = logging.FileHandler(alerts_file, encoding='utf-8')
        file_handler.setLevel(logging.INFO)

        # Professional format with all details
        formatter = logging.Formatter(
            '%(asctime)s | %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        file_handler.setFormatter(formatter)

        # Avoid duplicate handlers
        if not alerts_logger.handlers:
            alerts_logger.addHandler(file_handler)

        alerts_logger.propagate = False
        return alerts_logger

    def _log_alert(self, alert_type: str, change: dict) -> None:
        """
        Log detailed alert information for analysis.

        Writes comprehensive alert data to alerts_history.log including
        price changes, trader information, and timestamps.

        Args:
            alert_type: Type of alert ("BUY" or "SELL")
            change: Dictionary containing change details:
                - change: Percentage change
                - old_price: Previous price
                - new_price: Current price
                - trader_info: Optional trader details
        """
        direction = "UP ↗️" if change['change'] > 0 else "DOWN ↘️"

        # Build detailed log entry
        log_entry = f"{alert_type} ALERT | Direction: {direction} | "
        log_entry += f"Change: {change['change']:+.2f}% | "
        log_entry += f"Old Price: {change['old_price']:.2f} VES | "
        log_entry += f"New Price: {change['new_price']:.2f} VES | "
        log_entry += f"Difference: {change['new_price'] - change['old_price']:+.2f} VES"

        # Add trader information if available
        if change.get('trader_info') and change['trader_info'].get('trader'):
            trader = change['trader_info']
            log_entry += f" | Trader: {trader['trader']}"
            log_entry += f" | Orders: {trader['orders']}"
            log_entry += f" | Available: {trader['available']:.2f} USDT"

            if trader.get('payment_methods'):
                methods = ', '.join(trader['payment_methods'])
                log_entry += f" | Payment Methods: {methods}"

        self.alerts_logger.info(log_entry)

    def check_sudden_change(
        self,
        current_buy: float,
        current_sell: float,
        best_buy_offer: Optional[dict] = None,
        best_sell_offer: Optional[dict] = None
    ) -> None:
        """
        Check for sudden price changes and send alerts.

        Compares current prices against baseline prices. If the change exceeds
        the threshold, sends an alert and resets the baseline to prevent spam.

        Args:
            current_buy: Current best buy price
            current_sell: Current best sell price
            best_buy_offer: Full offer details for buy price
            best_sell_offer: Full offer details for sell price
        """
        sudden_changes = []
        baselines_changed = False

        # Initialize baselines if not set
        if self.telegram_buy_baseline is None:
            self.telegram_buy_baseline = current_buy
            baselines_changed = True
            self.logger.info(f"Initialized BUY baseline: {current_buy:.2f} VES")

        if self.telegram_sell_baseline is None:
            self.telegram_sell_baseline = current_sell
            baselines_changed = True
            self.logger.info(f"Initialized SELL baseline: {current_sell:.2f} VES")

        # Check BUY price change from baseline
        if self.telegram_buy_baseline and current_buy:
            buy_change = (
                (current_buy - self.telegram_buy_baseline) / self.telegram_buy_baseline
            ) * 100

            self.logger.debug(
                f"BUY: {current_buy:.2f} vs baseline {self.telegram_buy_baseline:.2f} "
                f"= {buy_change:+.2f}% (threshold: {self.sudden_change_threshold}%)"
            )

            if abs(buy_change) >= self.sudden_change_threshold:
                # Capture trader info at the moment of alert
                trader_info = {}
                if best_buy_offer:
                    buy_advertiser = best_buy_offer.get("advertiser", {})
                    buy_adv = best_buy_offer.get("adv", {})
                    trader_info = {
                        'trader': buy_advertiser.get("nickName", "Unknown"),
                        'orders': buy_advertiser.get("monthOrderCount", 0),
                        'available': float(buy_adv.get("surplusAmount", 0)),
                        'payment_methods': [
                            m.get("tradeMethodName", "")
                            for m in buy_adv.get("tradeMethods", [])
                            if m.get("tradeMethodName")
                        ]
                    }

                sudden_changes.append({
                    'type': 'BUY',
                    'change': buy_change,
                    'old_price': self.telegram_buy_baseline,
                    'new_price': current_buy,
                    'trader_info': trader_info
                })

                # Reset baseline immediately after detecting change
                self.logger.info(
                    f"BUY alert triggered: {buy_change:+.2f}% change. "
                    f"Resetting baseline from {self.telegram_buy_baseline:.2f} to {current_buy:.2f}"
                )
                self.telegram_buy_baseline = current_buy
                baselines_changed = True

        # Check SELL price change from baseline
        if self.telegram_sell_baseline and current_sell:
            sell_change = (
                (current_sell - self.telegram_sell_baseline) / self.telegram_sell_baseline
            ) * 100

            self.logger.debug(
                f"SELL: {current_sell:.2f} vs baseline {self.telegram_sell_baseline:.2f} "
                f"= {sell_change:+.2f}% (threshold: {self.sudden_change_threshold}%)"
            )

            if abs(sell_change) >= self.sudden_change_threshold:
                # Capture trader info at the moment of alert
                trader_info = {}
                if best_sell_offer:
                    sell_advertiser = best_sell_offer.get("advertiser", {})
                    sell_adv = best_sell_offer.get("adv", {})
                    trader_info = {
                        'trader': sell_advertiser.get("nickName", "Unknown"),
                        'orders': sell_advertiser.get("monthOrderCount", 0),
                        'available': float(sell_adv.get("surplusAmount", 0)),
                        'payment_methods': [
                            m.get("tradeMethodName", "")
                            for m in sell_adv.get("tradeMethods", [])
                            if m.get("tradeMethodName")
                        ]
                    }

                sudden_changes.append({
                    'type': 'SELL',
                    'change': sell_change,
                    'old_price': self.telegram_sell_baseline,
                    'new_price': current_sell,
                    'trader_info': trader_info
                })

                # Reset baseline immediately after detecting change
                self.logger.info(
                    f"SELL alert triggered: {sell_change:+.2f}% change. "
                    f"Resetting baseline from {self.telegram_sell_baseline:.2f} to {current_sell:.2f}"
                )
                self.telegram_sell_baseline = current_sell
                baselines_changed = True

        # Persist baseline updates even when no alert is sent (first init)
        if baselines_changed and not sudden_changes:
            self._persist_state()

        # Send alerts if any changes detected
        if sudden_changes:
            self.send_alerts(sudden_changes)

    def send_alerts(self, changes: List[dict]) -> None:
        """
        Send alert messages for sudden price changes.

        Groups changes by type (BUY/SELL) and sends separate alert messages.
        Deletes previous alert messages to keep chat clean.

        Args:
            changes: List of change dictionaries with details
        """
        # Group changes by type
        buy_changes = [c for c in changes if c['type'] == 'BUY']
        sell_changes = [c for c in changes if c['type'] == 'SELL']

        # Always log alerts locally, even if Telegram is disabled
        for change in buy_changes:
            self._log_alert("BUY", change)
        for change in sell_changes:
            self._log_alert("SELL", change)

        if self.telegram_client is None:
            self._persist_state()
            return

        # Send BUY alert if applicable
        if buy_changes:
            # Best-effort delete of previous BUY alert message
            if self.last_buy_alert_message_id:
                self.telegram_client.delete_message(self.last_buy_alert_message_id)
                self.logger.debug(
                    f"Deleted previous BUY alert message (ID: {self.last_buy_alert_message_id})"
                )
                self.last_buy_alert_message_id = None

            message = self.formatter.format_multi_alert(buy_changes, "BUY")
            message_id = self.telegram_client.send_message(message)

            if message_id:
                self.last_buy_alert_message_id = message_id
                self.logger.debug(f"Stored new BUY alert message (ID: {message_id})")

        # Send SELL alert if applicable
        if sell_changes:
            # Best-effort delete of previous SELL alert message
            if self.last_sell_alert_message_id:
                self.telegram_client.delete_message(self.last_sell_alert_message_id)
                self.logger.debug(
                    f"Deleted previous SELL alert message (ID: {self.last_sell_alert_message_id})"
                )
                self.last_sell_alert_message_id = None

            message = self.formatter.format_multi_alert(sell_changes, "SELL")
            message_id = self.telegram_client.send_message(message)

            if message_id:
                self.last_sell_alert_message_id = message_id
                self.logger.debug(f"Stored new SELL alert message (ID: {message_id})")

        # Persist baselines + alert message IDs after alert cycle
        self._persist_state()

    def send_regular_update(
        self,
        buy_price: Optional[float],
        sell_price: Optional[float],
        changes: Dict[str, dict],
        best_buy_offer: Optional[dict],
        best_sell_offer: Optional[dict],
        bcv_rate: Optional[float] = None,
        bcv_rates=None,
    ) -> Optional[int]:
        """
        Send or edit regular status update via Telegram.

        Creates a formatted status message with current prices, spreads,
        and price changes. Edits the previous message if it exists,
        otherwise sends a new message. If a previously known message was
        deleted (or process restarted with a stale ID), falls back to
        sending a fresh message and stores the new ID.

        Args:
            buy_price: Current best buy price
            sell_price: Current best sell price
            changes: Dictionary of price changes over time periods
            best_buy_offer: Full details of best buy offer
            best_sell_offer: Full details of best sell offer
            bcv_rate: Optional BCV official USD rate (legacy / premium %)
            bcv_rates: Optional BCVRates with USD/EUR/GBP

        Returns:
            Message ID of sent/edited message, or None if failed/disabled
        """
        if self.telegram_client is None:
            return None

        # Format the status message
        message = self.formatter.format_regular_update(
            buy_price=buy_price,
            sell_price=sell_price,
            changes=changes,
            best_buy_offer=best_buy_offer,
            best_sell_offer=best_sell_offer,
            bcv_rate=bcv_rate,
            bcv_rates=bcv_rates,
        )

        # Prefer editing the known status message (survives restarts via state file)
        if self.last_telegram_message_id:
            success, reason = self.telegram_client.edit_message_detailed(
                self.last_telegram_message_id,
                message
            )
            if success:
                # Keep ID persisted even if content was unchanged
                self._persist_state()
                return self.last_telegram_message_id

            self.logger.warning(
                "Could not edit status message id=%s (reason=%s); sending a new one",
                self.last_telegram_message_id,
                reason,
            )
            # Stale / deleted / uneditable → clear and recreate below
            self.last_telegram_message_id = None

        # No known message, or edit failed → create a new status message
        message_id = self.telegram_client.send_message(message)
        if message_id:
            self.last_telegram_message_id = message_id
            self._persist_state()
            self.logger.info(
                "Created new Telegram status message (message_id: %s)",
                message_id,
            )
        else:
            # Persist cleared ID if previous edit failed and send also failed
            self._persist_state()

        return message_id
