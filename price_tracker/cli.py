"""Command-line interface for price tracker.

This module handles CLI argument parsing and application entry point.
"""

import argparse
import logging
import os
import sys

from price_tracker.infrastructure.config import Config
from price_tracker.infrastructure.logging import setup_logging
from price_tracker.services.tracker_service import TrackerService


def main():
    """Main entry point for price tracker."""
    parser = argparse.ArgumentParser(
        description='Binance P2P Price Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-loads config.json if it exists
  python -m price_tracker

  # Override payment method from config
  python -m price_tracker -p "Banesco"

  # Without config file (all via CLI)
  python -m price_tracker -p "PagoMovil" -i 60 -t 3.0

  # Use different config file
  python -m price_tracker --config my_config.json

  # Override specific settings
  python -m price_tracker -p "PagoMovil" -t 5.0
        """
    )

    parser.add_argument(
        '--config', '-c',
        help='JSON config file path (default: config.json if exists)'
    )
    parser.add_argument(
        '--payment-methods', '-p',
        nargs='+',
        help='Payment methods to filter'
    )
    parser.add_argument(
        '--interval', '-i',
        type=int,
        help='Check interval in seconds'
    )
    parser.add_argument(
        '--threshold', '-t',
        type=float,
        help='Alert threshold percentage'
    )
    parser.add_argument('--asset', help='Crypto asset (default: USDT)')
    parser.add_argument('--fiat', help='Fiat currency (default: VES)')
    parser.add_argument(
        '--min-amount', '-m',
        type=float,
        help='Minimum transaction amount in fiat (e.g., 60000 for 60,000 VES)'
    )

    # Logging
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        help='Log level'
    )

    args = parser.parse_args()

    # Load config: try specified file, then default config.json, then empty
    if args.config:
        # User specified a config file
        try:
            config = Config.from_file(args.config)
        except Exception as e:
            print(f"ERROR: Failed to load config file: {e}")
            sys.exit(1)
    elif os.path.exists('config.json'):
        # Auto-load config.json if it exists
        try:
            config = Config.from_file('config.json')
            logging.info("Loaded default config.json")
        except Exception as e:
            print(f"ERROR: Failed to load config.json: {e}")
            sys.exit(1)
    else:
        # No config file, create default config
        config = Config()

    # Override with CLI arguments
    if args.payment_methods:
        config.filters.payment_methods = args.payment_methods
    if args.interval:
        config.check_interval = args.interval
    if args.threshold:
        config.alert_threshold = args.threshold
    if args.asset:
        config.filters.asset = args.asset
    if args.fiat:
        config.filters.fiat = args.fiat
    if args.min_amount:
        from decimal import Decimal
        config.filters.min_amount = Decimal(str(args.min_amount))

    # Logging config
    if args.log_file:
        config.log_file = args.log_file
    if args.log_level:
        config.log_level = args.log_level

    # Validate interval
    if config.check_interval < 10:
        print("ERROR: Interval must be at least 10 seconds to avoid rate limits")
        sys.exit(1)

    # Setup logging
    setup_logging(config.log_file, config.log_level)
    logger = logging.getLogger(__name__)

    # Create dependencies
    from price_tracker.api.binance import BinanceP2PClient
    from price_tracker.api.bcv import BCVRateClient
    from price_tracker.api.telegram import TelegramClient
    from price_tracker.domain.filters import OfferFilter
    from price_tracker.presentation.formatters import TelegramFormatter
    from price_tracker.presentation.console import ConsoleDisplay
    from price_tracker.services.price_service import PriceService
    from price_tracker.services.alert_service import AlertService
    from price_tracker.infrastructure.persistence import HistoryPersistence
    from price_tracker.infrastructure.signals import SignalHandler

    # API clients
    binance_client = BinanceP2PClient(
        asset=config.filters.asset,
        fiat=config.filters.fiat,
        max_retries=config.max_retries,
        request_timeout=config.request_timeout,
        backoff_multiplier=config.backoff_multiplier
    )
    bcv_client = BCVRateClient(
        max_retries=config.max_retries,
        request_timeout=config.request_timeout,
        backoff_multiplier=config.backoff_multiplier
    )

    # Domain
    offer_filter = OfferFilter()

    # Services
    price_service = PriceService(
        binance_client=binance_client,
        bcv_client=bcv_client,
        offer_filter=offer_filter,
        config=config
    )

    # Telegram (only if enabled)
    if config.telegram.enabled:
        telegram_client = TelegramClient(
            bot_token=config.telegram.bot_token,
            chat_id=config.telegram.chat_id
        )
        telegram_formatter = TelegramFormatter()
        alert_service = AlertService(
            telegram_client=telegram_client,
            telegram_formatter=telegram_formatter,
            config=config
        )
    else:
        alert_service = AlertService(
            telegram_client=None,
            telegram_formatter=None,
            config=config
        )

    # Infrastructure
    persistence = HistoryPersistence(
        asset=config.filters.asset,
        fiat=config.filters.fiat
    )
    console = ConsoleDisplay(config)
    signal_handler = SignalHandler()

    # Create and run tracker
    tracker = TrackerService(
        config=config,
        price_service=price_service,
        alert_service=alert_service,
        persistence=persistence,
        console=console,
        signal_handler=signal_handler
    )
    tracker.start()


if __name__ == "__main__":
    main()
