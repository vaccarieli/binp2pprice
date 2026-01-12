"""Data models for price tracking.

This module contains type-safe dataclasses and enums that represent
the core business entities used throughout the application.
"""

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import List, Optional


class TradeType(Enum):
    """Type of trade offer."""
    BUY = "BUY"
    SELL = "SELL"


class AlertType(Enum):
    """Type of price alert."""
    BUY = "BUY"
    SELL = "SELL"


class Direction(Enum):
    """Direction of price movement."""
    UP = "UP"
    DOWN = "DOWN"


@dataclass
class TradeMethod:
    """Payment method information."""
    identifier: str
    trade_method_name: str

    @property
    def name(self) -> str:
        """Get the display name of the payment method."""
        return self.trade_method_name


@dataclass
class Trader:
    """Trader information."""
    nickname: str
    month_order_count: int
    month_finish_rate: float

    @property
    def completion_rate(self) -> float:
        """Get completion rate as percentage."""
        return self.month_finish_rate * 100 if self.month_finish_rate else 0


@dataclass
class Offer:
    """P2P offer details."""
    price: Decimal
    trade_type: TradeType
    trader: Trader
    available_amount: Decimal
    min_single_trans_amount: Decimal
    max_single_trans_amount: Decimal
    dynamic_max_single_trans_amount: Decimal
    trade_methods: List[TradeMethod]
    is_promoted: bool = False

    @property
    def payment_methods(self) -> List[str]:
        """Get list of payment method names."""
        return [method.name for method in self.trade_methods]

    @property
    def avg_payment_methods(self) -> str:
        """Get first 2 payment methods as comma-separated string."""
        methods = self.payment_methods[:2]
        return ", ".join(methods)


@dataclass
class Price:
    """Price snapshot at a specific time."""
    buy: Optional[Decimal]
    sell: Optional[Decimal]
    timestamp: datetime
    best_buy_offer: Optional[Offer] = None
    best_sell_offer: Optional[Offer] = None

    @property
    def spread(self) -> Optional[Decimal]:
        """Calculate spread between buy and sell prices."""
        if self.buy is not None and self.sell is not None:
            return abs(self.buy - self.sell)
        return None

    @property
    def spread_percentage(self) -> Optional[Decimal]:
        """Calculate spread as percentage of sell price."""
        if self.spread is not None and self.sell is not None and self.sell > 0:
            return (self.spread / self.sell) * Decimal(100)
        return None


@dataclass
class PriceChange:
    """Price change over a specific period."""
    period: str  # "15m", "30m", "1h"
    buy_change: Decimal
    sell_change: Decimal
    old_buy: Decimal
    old_sell: Decimal
    new_buy: Decimal
    new_sell: Decimal


@dataclass
class Alert:
    """Price alert information."""
    alert_type: AlertType
    direction: Direction
    change_percent: Decimal
    old_price: Decimal
    new_price: Decimal
    timestamp: datetime
    trader_info: Optional[dict] = None

    @property
    def price_difference(self) -> Decimal:
        """Calculate absolute price difference."""
        return abs(self.new_price - self.old_price)
