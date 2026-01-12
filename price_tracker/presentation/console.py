"""
Console display for price tracker status.

This module handles all terminal/console output including:
- Current price display with trader details
- Price change visualization
- Status information and monitoring metrics
- Cross-platform screen clearing
"""

import os
from datetime import datetime
from typing import Optional, Dict, Any


class ConsoleDisplay:
    """Handles console output for price tracker status."""

    def __init__(self, config: Any):
        """
        Initialize the console display.

        Args:
            config: Configuration object with fiat, asset, and other settings
        """
        self.config = config

    def _clear_screen(self) -> None:
        """Clear the console screen in a cross-platform way."""
        try:
            # Windows: cls, Unix/Linux/Mac: clear
            os.system('cls' if os.name == 'nt' else 'clear')
        except Exception:
            # Fallback: print newlines to push content up
            print("\n" * 50)

    def display_status(
        self,
        buy_price: Optional[float],
        sell_price: Optional[float],
        changes: Dict[str, dict],
        best_buy_offer: Optional[dict] = None,
        best_sell_offer: Optional[dict] = None,
        running: bool = True,
        price_history_count: int = 0,
        consecutive_failures: int = 0
    ) -> None:
        """
        Display current price tracker status to console.

        Args:
            buy_price: Current best buy price, or None if no offers
            sell_price: Current best sell price, or None if no offers
            changes: Dictionary of price changes over time periods (15m, 30m, 1h)
            best_buy_offer: Full offer details for best buy price
            best_sell_offer: Full offer details for best sell price
            running: Whether tracker is currently running
            price_history_count: Number of price readings in history
            consecutive_failures: Number of consecutive API failures
        """
        self._clear_screen()

        print("=" * 70)
        print(f"Binance P2P {self.config.fiat}/{self.config.asset} Price Tracker")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Status: {'RUNNING' if running else 'STOPPING'}")
        print("=" * 70)

        print(f"\nCurrent Prices:")

        # BUY offer details
        if buy_price is not None and best_buy_offer:
            buy_adv = best_buy_offer.get("adv", {})
            buy_advertiser = best_buy_offer.get("advertiser", {})
            buy_trader = buy_advertiser.get("nickName", "Unknown")
            buy_orders = buy_advertiser.get("monthOrderCount", 0)
            buy_available = float(buy_adv.get("surplusAmount", 0))
            buy_methods = ", ".join([
                m.get("tradeMethodName", "")
                for m in buy_adv.get("tradeMethods", [])
                if m.get("tradeMethodName")
            ])

            print(f"  Best BUY:  {buy_price:.2f} {self.config.fiat}/USDT")
            print(f"    Trader: {buy_trader} (Orders: {buy_orders})")
            print(f"    Available: {buy_available:.2f} USDT")
            print(f"    Payment: {buy_methods}")
        else:
            print(f"  Best BUY:  No offers matching filters")

        print()

        # SELL offer details
        if sell_price is not None and best_sell_offer:
            sell_adv = best_sell_offer.get("adv", {})
            sell_advertiser = best_sell_offer.get("advertiser", {})
            sell_trader = sell_advertiser.get("nickName", "Unknown")
            sell_orders = sell_advertiser.get("monthOrderCount", 0)
            sell_available = float(sell_adv.get("surplusAmount", 0))
            sell_methods = ", ".join([
                m.get("tradeMethodName", "")
                for m in sell_adv.get("tradeMethods", [])
                if m.get("tradeMethodName")
            ])

            print(f"  Best SELL: {sell_price:.2f} {self.config.fiat}/USDT")
            print(f"    Trader: {sell_trader} (Orders: {sell_orders})")
            print(f"    Available: {sell_available:.2f} USDT")
            print(f"    Payment: {sell_methods}")
        else:
            print(f"  Best SELL: No offers matching filters")

        print()

        # Only show spread if both prices exist
        if buy_price is not None and sell_price is not None:
            spread = buy_price - sell_price
            spread_pct = ((buy_price/sell_price - 1) * 100)
            print(f"  Spread: {spread:.2f} {self.config.fiat} ({spread_pct:.2f}%)")
        else:
            print(f"  Spread: N/A (need both BUY and SELL offers)")

        # Price changes over time
        if changes:
            print(f"\nPrice Changes:")
            for period, data in sorted(changes.items()):
                print(f"\n  {period}:")
                print(f"    BUY:  {data['buy_change']:+.2f}% "
                      f"({data['buy_old']:.2f} -> {buy_price:.2f})")
                print(f"    SELL: {data['sell_change']:+.2f}% "
                      f"({data['sell_old']:.2f} -> {sell_price:.2f})")

        # Monitoring information
        print(f"\nMonitoring:")
        print(f"  History: {price_history_count} readings")
        print(f"  Failures: {consecutive_failures}")
        print(f"  Next check: {self.config.check_interval}s")
        print("=" * 70)

    def display_no_offers_warning(
        self,
        running: bool = True,
        price_history_count: int = 0,
        consecutive_failures: int = 0
    ) -> None:
        """
        Display warning when no offers match the configured filters.

        Args:
            running: Whether tracker is currently running
            price_history_count: Number of price readings in history
            consecutive_failures: Number of consecutive API failures
        """
        self._clear_screen()

        print("=" * 70)
        print(f"Binance P2P {self.config.fiat}/{self.config.asset} Price Tracker")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Status: {'RUNNING' if running else 'STOPPING'}")
        print("=" * 70)
        print()
        print("WARNING: NO OFFERS MATCH YOUR FILTERS")
        print()
        print("Current filters:")

        if self.config.payment_methods:
            print(f"  Payment methods: {', '.join(self.config.payment_methods)}")

        if hasattr(self.config, 'min_amount') and self.config.min_amount > 0:
            print(f"  Minimum amount: {self.config.min_amount:,.0f} {self.config.fiat}")

        if hasattr(self.config, 'exclude_methods') and self.config.exclude_methods:
            print(f"  Excluding: {', '.join(self.config.exclude_methods)}")

        print()
        print("Suggestions:")

        if hasattr(self.config, 'min_amount') and self.config.min_amount > 0:
            print(f"  • Lower min_amount (currently {self.config.min_amount:,.0f} {self.config.fiat})")
            print(f"  • Try: python price_tracker_prod.py -m 0")

        if self.config.payment_methods:
            print(f"  • Try different payment method")
            print(f"  • Remove payment filter: python price_tracker_prod.py -p \"\"")

        print()
        print(f"Monitoring:")
        print(f"  History: {price_history_count} readings")
        print(f"  Failures: {consecutive_failures}")
        print(f"  Next check: {self.config.check_interval}s")
        print("=" * 70)
