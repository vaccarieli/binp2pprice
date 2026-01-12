"""
Tracker Service Module

Main orchestration service that coordinates all components of the price tracker.
Manages the main tracking loop and handles graceful shutdown.
"""

import logging
import time
from typing import Optional
from datetime import datetime

from price_tracker.infrastructure.config import Config
from price_tracker.services.price_service import PriceService
from price_tracker.services.alert_service import AlertService
from price_tracker.infrastructure.persistence import HistoryPersistence
from price_tracker.presentation.console import ConsoleDisplay
from price_tracker.infrastructure.signals import SignalHandler


class TrackerService:
    """
    Main orchestration service for the price tracker.

    Coordinates all components and manages the main tracking loop:
    - Fetches prices at regular intervals
    - Calculates changes and triggers alerts
    - Updates console display
    - Persists history
    - Handles graceful shutdown
    """

    def __init__(
        self,
        config: Config,
        price_service: PriceService,
        alert_service: AlertService,
        persistence: HistoryPersistence,
        console: ConsoleDisplay,
        signal_handler: SignalHandler
    ):
        """
        Initialize the tracker service.

        Args:
            config: Application configuration
            price_service: Service for price operations
            alert_service: Service for alert management
            persistence: Service for history persistence
            console: Console display handler
            signal_handler: Signal handling for graceful shutdown
        """
        self.config = config
        self.price_service = price_service
        self.alert_service = alert_service
        self.persistence = persistence
        self.console = console
        self.signal_handler = signal_handler
        self.logger = logging.getLogger(__name__)

        # State tracking
        self.running = True
        self.consecutive_failures = 0
        self.iteration = 0

        # Register shutdown callback
        self.signal_handler.register_shutdown_callback(self.stop)

    def start(self) -> None:
        """
        Start the price tracker.

        Loads historical data and begins the main tracking loop.
        """
        self._log_startup_info()

        # Load historical data
        self.persistence.load_history(self.price_service.price_history)

        # Run main loop
        self.run()

    def stop(self) -> None:
        """
        Stop the tracker gracefully.

        Sets the running flag to false, which will cause the main loop
        to exit at the next iteration.
        """
        self.logger.info("Shutting down tracker...")
        self.running = False

    def run(self) -> None:
        """
        Main tracking loop.

        Continuously monitors prices, calculates changes, sends alerts,
        and updates displays until stopped.
        """
        try:
            while self.running:
                self.iteration += 1
                self.logger.debug(f"Starting iteration {self.iteration}")

                # Get current prices
                buy_price, sell_price = self.price_service.get_current_prices()

                # Process prices if at least one is available
                if buy_price is not None or sell_price is not None:
                    self._process_prices(buy_price, sell_price)
                else:
                    self._handle_no_offers()

                # Wait before next check
                if self.running:
                    time.sleep(self.config.check_interval)

        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}", exc_info=True)

        finally:
            self._shutdown()

    def _process_prices(
        self,
        buy_price: Optional[float],
        sell_price: Optional[float]
    ) -> None:
        """
        Process fetched prices and update all components.

        Args:
            buy_price: Current best buy price (can be None)
            sell_price: Current best sell price (can be None)
        """
        changes = {}

        # Only record and calculate changes if both prices exist
        if buy_price is not None and sell_price is not None:
            # Record to history
            self.price_service.record_price(buy_price, sell_price)

            # Calculate changes
            changes = self.price_service.calculate_changes(buy_price, sell_price)

            # Check for standard alerts (logged to console)
            alerts = self._check_alerts(changes)
            if alerts:
                self._log_alerts(alerts)

            # Check for sudden changes (Telegram alerts)
            best_buy_offer, best_sell_offer = self.price_service.get_best_offers()
            self.alert_service.check_sudden_change(
                buy_price,
                sell_price,
                best_buy_offer,
                best_sell_offer
            )

            # Get BCV rate
            bcv_rate = self.price_service.get_bcv_rate()

            # Send regular Telegram update
            self.alert_service.send_regular_update(
                buy_price,
                sell_price,
                changes,
                best_buy_offer,
                best_sell_offer,
                bcv_rate
            )

            # Save history periodically
            if self.iteration % 10 == 0:
                self.persistence.save_history(
                    self.price_service.price_history,
                    self.config
                )

            # Reset consecutive failures
            self.consecutive_failures = 0

        # Display status (works even if only one price exists)
        best_buy_offer, best_sell_offer = self.price_service.get_best_offers()
        self.console.display_status(
            buy_price=buy_price,
            sell_price=sell_price,
            changes=changes,
            best_buy_offer=best_buy_offer,
            best_sell_offer=best_sell_offer,
            price_history_count=self.price_service.get_history_count(),
            consecutive_failures=self.consecutive_failures,
            running=self.running
        )

    def _handle_no_offers(self) -> None:
        """
        Handle the case when no offers match filters.

        Displays a warning with filter information and suggestions.
        Increases backoff time if failures persist.
        """
        self.console.display_no_offers_warning(
            price_history_count=self.price_service.get_history_count(),
            consecutive_failures=self.consecutive_failures,
            running=self.running
        )

        self.logger.warning(f"Failed to fetch prices at {datetime.now()}")
        self.consecutive_failures += 1

        # If too many failures, increase backoff
        if self.consecutive_failures > 5:
            extra_wait = min(300, self.consecutive_failures * 10)
            self.logger.warning(f"Multiple failures, waiting extra {extra_wait}s")
            time.sleep(extra_wait)

    def _check_alerts(self, changes: dict) -> list:
        """
        Check if any changes exceed the alert threshold.

        Args:
            changes: Dictionary of price changes by time period

        Returns:
            List of alert strings
        """
        alerts = []
        threshold = self.config.alert_threshold

        for period, data in changes.items():
            if abs(data['buy_change']) >= threshold:
                direction = "UP" if data['buy_change'] > 0 else "DOWN"
                alerts.append(
                    f"BUY price {direction} {abs(data['buy_change']):.2f}% in {period} "
                    f"({data['buy_old']:.2f} -> "
                    f"{data['buy_old'] * (1 + data['buy_change']/100):.2f})"
                )

            if abs(data['sell_change']) >= threshold:
                direction = "UP" if data['sell_change'] > 0 else "DOWN"
                alerts.append(
                    f"SELL price {direction} {abs(data['sell_change']):.2f}% in {period} "
                    f"({data['sell_old']:.2f} -> "
                    f"{data['sell_old'] * (1 + data['sell_change']/100):.2f})"
                )

        return alerts

    def _log_alerts(self, alerts: list) -> None:
        """
        Log alerts to console.

        Args:
            alerts: List of alert strings
        """
        if not alerts:
            return

        alert_text = "\n".join(alerts)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        self.logger.warning(f"ALERTS at {timestamp}:\n{alert_text}")

    def _log_startup_info(self) -> None:
        """Log startup information."""
        self.logger.info("=" * 70)
        self.logger.info("Starting P2P Price Tracker")
        self.logger.info(f"Asset: {self.config.filters.asset}")
        self.logger.info(f"Fiat: {self.config.filters.fiat}")
        self.logger.info(f"Check interval: {self.config.check_interval}s")
        self.logger.info(f"Alert threshold: ±{self.config.alert_threshold}%")

        if self.config.filters.payment_methods:
            self.logger.info(f"Payment methods: {', '.join(self.config.filters.payment_methods)}")
        if self.config.filters.exclude_methods:
            self.logger.info(f"Excluding: {', '.join(self.config.filters.exclude_methods)}")

        if self.config.telegram.enabled:
            self.logger.info(
                f"Telegram alerts: ENABLED "
                f"(regular: {self.config.telegram.regular_updates}, "
                f"threshold: {self.config.telegram.sudden_change_threshold}%)"
            )
        else:
            self.logger.info("Telegram alerts: DISABLED")

        self.logger.info("=" * 70)

    def _shutdown(self) -> None:
        """Perform shutdown tasks."""
        self.logger.info("Shutting down tracker...")
        self.persistence.save_history(
            self.price_service.price_history,
            self.config
        )
        self.logger.info("Shutdown complete")
