"""
Alert Service Module

Handles alert generation and delivery for price changes.
Manages both sudden change alerts and regular status updates.
"""

import logging
from typing import Optional, Dict, List
from datetime import datetime

from price_tracker.api.telegram import TelegramClient
from price_tracker.presentation.formatters import TelegramFormatter


class AlertService:
    """
    Service for managing price alerts and notifications.

    This service handles:
    - Detecting sudden price changes against baselines
    - Sending alert messages via Telegram
    - Sending regular status updates
    - Logging alerts to persistent storage
    """

    def __init__(
        self,
        telegram_client: TelegramClient,
        formatter: TelegramFormatter,
        sudden_change_threshold: float = 5.0
    ):
        """
        Initialize the alert service.

        Args:
            telegram_client: Client for sending Telegram messages
            formatter: Formatter for creating Telegram message text
            sudden_change_threshold: Percentage threshold for sudden change alerts
        """
        self.telegram_client = telegram_client
        self.formatter = formatter
        self.sudden_change_threshold = sudden_change_threshold
        self.logger = logging.getLogger(__name__)

        # Baseline tracking for sudden change detection
        self.telegram_buy_baseline: Optional[float] = None
        self.telegram_sell_baseline: Optional[float] = None

        # Message ID tracking for editing/deleting messages
        self.last_telegram_message_id: Optional[int] = None
        self.last_buy_alert_message_id: Optional[int] = None
        self.last_sell_alert_message_id: Optional[int] = None

        # Setup dedicated alerts logger
        self.alerts_logger = self._setup_alerts_logger()

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

        # Initialize baselines if not set
        if self.telegram_buy_baseline is None:
            self.telegram_buy_baseline = current_buy
            self.logger.info(f"Initialized BUY baseline: {current_buy:.2f} VES")

        if self.telegram_sell_baseline is None:
            self.telegram_sell_baseline = current_sell
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

        # Send BUY alert if applicable
        if buy_changes:
            # Delete previous BUY alert message
            if self.last_buy_alert_message_id:
                self.telegram_client.delete_message(self.last_buy_alert_message_id)
                self.logger.debug(
                    f"Deleted previous BUY alert message (ID: {self.last_buy_alert_message_id})"
                )

            # Format and send new BUY alert
            for change in buy_changes:
                self._log_alert("BUY", change)

            message = self.formatter.format_multi_alert(buy_changes, "BUY")
            message_id = self.telegram_client.send_message(message)

            if message_id:
                self.last_buy_alert_message_id = message_id
                self.logger.debug(f"Stored new BUY alert message (ID: {message_id})")

        # Send SELL alert if applicable
        if sell_changes:
            # Delete previous SELL alert message
            if self.last_sell_alert_message_id:
                self.telegram_client.delete_message(self.last_sell_alert_message_id)
                self.logger.debug(
                    f"Deleted previous SELL alert message (ID: {self.last_sell_alert_message_id})"
                )

            # Format and send new SELL alert
            for change in sell_changes:
                self._log_alert("SELL", change)

            message = self.formatter.format_multi_alert(sell_changes, "SELL")
            message_id = self.telegram_client.send_message(message)

            if message_id:
                self.last_sell_alert_message_id = message_id
                self.logger.debug(f"Stored new SELL alert message (ID: {message_id})")

    def send_regular_update(
        self,
        buy_price: Optional[float],
        sell_price: Optional[float],
        changes: Dict[str, dict],
        best_buy_offer: Optional[dict],
        best_sell_offer: Optional[dict],
        bcv_rate: Optional[float] = None
    ) -> Optional[int]:
        """
        Send or edit regular status update via Telegram.

        Creates a formatted status message with current prices, spreads,
        and price changes. Edits the previous message if it exists,
        otherwise sends a new message.

        Args:
            buy_price: Current best buy price
            sell_price: Current best sell price
            changes: Dictionary of price changes over time periods
            best_buy_offer: Full details of best buy offer
            best_sell_offer: Full details of best sell offer
            bcv_rate: Optional BCV official rate

        Returns:
            Message ID of sent/edited message, or None if failed
        """
        # Format the status message
        message = self.formatter.format_regular_update(
            buy_price=buy_price,
            sell_price=sell_price,
            changes=changes,
            best_buy_offer=best_buy_offer,
            best_sell_offer=best_sell_offer,
            bcv_rate=bcv_rate
        )

        # Edit existing message or send new one
        if self.last_telegram_message_id:
            success = self.telegram_client.edit_message(
                self.last_telegram_message_id,
                message
            )
            return self.last_telegram_message_id if success else None
        else:
            message_id = self.telegram_client.send_message(message)
            if message_id:
                self.last_telegram_message_id = message_id
            return message_id
