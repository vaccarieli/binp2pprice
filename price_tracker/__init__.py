"""Binance P2P Price Tracker.

A professional, modular package for tracking Binance P2P prices with
real-time Telegram alerts and BCV rate comparison.
"""

__version__ = "2.0.0"

from price_tracker.infrastructure.config import Config
from price_tracker.services.tracker_service import TrackerService

__all__ = ["Config", "TrackerService"]
