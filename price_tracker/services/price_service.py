"""
Price Service Module

Handles all price-related operations including fetching current prices,
managing price history, and calculating price changes.
"""

import logging
from datetime import datetime, timedelta
from collections import deque
from typing import Optional, Tuple, Dict, List

from price_tracker.api.binance import BinanceP2PClient
from price_tracker.api.bcv import BCVRateClient
from price_tracker.domain.filters import OfferFilter


class PriceService:
    """
    Service for managing price operations.

    This service handles:
    - Fetching current best buy/sell prices from Binance P2P
    - Fetching BCV official exchange rate
    - Maintaining price history for trend analysis
    - Calculating price changes over different time periods
    """

    def __init__(
        self,
        binance_client: BinanceP2PClient,
        bcv_client: BCVRateClient,
        offer_filter: OfferFilter,
        payment_methods: list,
        exclude_methods: list,
        min_amount: float,
        fiat: str,
        max_history: int = 1000
    ):
        """
        Initialize the price service.

        Args:
            binance_client: Client for interacting with Binance P2P API
            bcv_client: Client for fetching BCV official rates
            offer_filter: Filter for processing offers based on criteria
            payment_methods: List of payment methods to filter by
            exclude_methods: List of payment methods to exclude
            min_amount: Minimum transaction amount
            fiat: Fiat currency code
            max_history: Maximum number of price records to keep in history
        """
        self.binance_client = binance_client
        self.bcv_client = bcv_client
        self.offer_filter = offer_filter
        self.payment_methods = payment_methods
        self.exclude_methods = exclude_methods
        self.min_amount = min_amount
        self.fiat = fiat
        self.price_history = deque(maxlen=max_history)
        self.logger = logging.getLogger(__name__)

        # Store best offers for detailed information
        self.best_buy_offer: Optional[dict] = None
        self.best_sell_offer: Optional[dict] = None

    def get_current_prices(self) -> Tuple[Optional[float], Optional[float]]:
        """
        Get current best buy and sell prices from Binance P2P.

        Fetches offers from Binance P2P, applies filters, and returns
        the best available prices along with offer details.

        Returns:
            Tuple of (buy_price, sell_price). Either can be None if no
            matching offers are found.
        """
        # Fetch offers from API
        buy_data = self.binance_client.fetch_offers(
            "BUY",
            payment_methods=self.payment_methods,
            min_amount=self.min_amount
        )
        sell_data = self.binance_client.fetch_offers(
            "SELL",
            payment_methods=self.payment_methods,
            min_amount=self.min_amount
        )

        if not buy_data or not sell_data:
            return None, None

        try:
            # Extract offers from response
            buy_offers = buy_data.get("data", [])
            sell_offers = sell_data.get("data", [])

            # Apply filters
            buy_offers = self.offer_filter.filter_promoted(buy_offers)
            buy_offers = self.offer_filter.filter_by_exclude_methods(
                buy_offers, self.exclude_methods
            )
            buy_offers = self.offer_filter.filter_by_amount(
                buy_offers, self.min_amount, self.fiat
            )

            sell_offers = self.offer_filter.filter_promoted(sell_offers)
            sell_offers = self.offer_filter.filter_by_exclude_methods(
                sell_offers, self.exclude_methods
            )
            sell_offers = self.offer_filter.filter_by_amount(
                sell_offers, self.min_amount, self.fiat
            )

            self.logger.info(
                f"After filtering: {len(buy_offers)} BUY, "
                f"{len(sell_offers)} SELL offers"
            )

            # Check if we have any offers
            if not buy_offers and not sell_offers:
                self.logger.warning("No offers after filtering")
                return None, None

            # Find best prices
            self.best_buy_offer = self._find_best_price(buy_offers, "BUY") if buy_offers else None
            self.best_sell_offer = self._find_best_price(sell_offers, "SELL") if sell_offers else None

            # Extract price values
            best_buy = (
                float(self.best_buy_offer.get("adv", {}).get("price", 0))
                if self.best_buy_offer else None
            )
            best_sell = (
                float(self.best_sell_offer.get("adv", {}).get("price", 0))
                if self.best_sell_offer else None
            )

            # Validate prices
            if best_buy is not None and best_buy <= 0:
                self.logger.error(f"Invalid BUY price: {best_buy}")
                best_buy = None
                self.best_buy_offer = None

            if best_sell is not None and best_sell <= 0:
                self.logger.error(f"Invalid SELL price: {best_sell}")
                best_sell = None
                self.best_sell_offer = None

            # Check for suspicious spread
            if best_buy and best_sell:
                if best_buy > best_sell * 2 or best_sell > best_buy * 2:
                    self.logger.warning(
                        f"Suspicious price spread: buy={best_buy}, sell={best_sell}"
                    )

            # Log offer details
            if self.best_buy_offer:
                trader = self.best_buy_offer.get('advertiser', {}).get('nickName', 'Unknown')
                self.logger.debug(f"Best BUY: {best_buy} from {trader}")
            if self.best_sell_offer:
                trader = self.best_sell_offer.get('advertiser', {}).get('nickName', 'Unknown')
                self.logger.debug(f"Best SELL: {best_sell} from {trader}")

            return best_buy, best_sell

        except (ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error parsing prices: {e}")
            return None, None

    def _find_best_price(self, offers: List[dict], trade_type: str) -> Optional[dict]:
        """
        Find the best price offer from a list of offers.

        Args:
            offers: List of offer dictionaries
            trade_type: "BUY" or "SELL"

        Returns:
            The offer with the best price, or None if offers is empty
        """
        if not offers:
            return None

        if trade_type == "BUY":
            return min(offers, key=lambda x: float(x['adv']['price']))
        else:  # SELL
            return max(offers, key=lambda x: float(x['adv']['price']))

    def get_bcv_rate(self) -> Optional[float]:
        """
        Get the current BCV official exchange rate.

        Delegates to the BCV client which handles caching and
        fallback strategies.

        Returns:
            BCV rate in VES, or None if unavailable
        """
        return self.bcv_client.get_rate()

    def record_price(self, buy_price: float, sell_price: float) -> None:
        """
        Record a price reading to the history.

        Args:
            buy_price: Current best buy price
            sell_price: Current best sell price
        """
        timestamp = datetime.now()
        self.price_history.append((timestamp, buy_price, sell_price))
        self.logger.debug(f"Recorded: buy={buy_price}, sell={sell_price}")

    def get_price_at_time(self, minutes_ago: int) -> Tuple[Optional[float], Optional[float]]:
        """
        Get historical price from N minutes ago.

        Finds the closest price reading to the target time.
        Only returns if the reading is within 2 minutes of the target.

        Args:
            minutes_ago: How many minutes back to look

        Returns:
            Tuple of (buy_price, sell_price) or (None, None) if not available
        """
        if not self.price_history:
            return None, None

        target_time = datetime.now() - timedelta(minutes=minutes_ago)

        # Find closest price reading
        closest = min(
            self.price_history,
            key=lambda x: abs((x[0] - target_time).total_seconds())
        )

        # Only return if within 2 minutes of target
        if abs((closest[0] - target_time).total_seconds()) < 120:
            return closest[1], closest[2]

        return None, None

    def calculate_changes(
        self,
        current_buy: float,
        current_sell: float
    ) -> Dict[str, dict]:
        """
        Calculate price changes over different time periods.

        Compares current prices against historical prices at 15m, 30m, and 1h
        intervals to calculate percentage changes.

        Args:
            current_buy: Current best buy price
            current_sell: Current best sell price

        Returns:
            Dictionary with keys "15m", "30m", "1h" containing:
                - buy_change: Percentage change in buy price
                - sell_change: Percentage change in sell price
                - buy_old: Historical buy price
                - sell_old: Historical sell price
        """
        changes = {}

        for period, minutes in [("15m", 15), ("30m", 30), ("1h", 60)]:
            old_buy, old_sell = self.get_price_at_time(minutes)

            if old_buy and old_sell:
                buy_change = ((current_buy - old_buy) / old_buy) * 100
                sell_change = ((current_sell - old_sell) / old_sell) * 100

                changes[period] = {
                    "buy_change": buy_change,
                    "sell_change": sell_change,
                    "buy_old": old_buy,
                    "sell_old": old_sell
                }

        return changes

    def get_history_count(self) -> int:
        """
        Get the number of price records in history.

        Returns:
            Number of recorded price readings
        """
        return len(self.price_history)

    def get_best_offers(self) -> Tuple[Optional[dict], Optional[dict]]:
        """
        Get the most recent best buy and sell offers with full details.

        Returns:
            Tuple of (best_buy_offer, best_sell_offer)
        """
        return self.best_buy_offer, self.best_sell_offer
