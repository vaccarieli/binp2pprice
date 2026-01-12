#!/usr/bin/env python3
"""
Binance P2P Price Tracker - Entry point script

This is a wrapper script for backward compatibility.
The actual implementation is in the modular price_tracker package.

Usage:
    python3 price_tracker_prod.py
    python3 price_tracker_prod.py -c config.json
    python3 price_tracker_prod.py -p "Pago Movil" -i 30
"""

from price_tracker.cli import main

if __name__ == "__main__":
    main()
