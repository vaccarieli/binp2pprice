#!/usr/bin/env python3
"""
Binance P2P VES Price Tracker
Monitors prices over time and sends alerts on significant changes
"""

import requests
import json
import time
import argparse
from datetime import datetime, timedelta
from collections import deque
import os

# Configuration
DEFAULT_CHECK_INTERVAL = 30  # seconds between checks
DEFAULT_ALERT_THRESHOLD = 2.0  # percentage change to trigger alert

class PriceTracker:
    def __init__(self, asset="USDT", fiat="VES", payment_methods=None, exclude_methods=None):
        self.asset = asset
        self.fiat = fiat
        self.payment_methods = payment_methods or []
        self.exclude_methods = exclude_methods or ["Recarga Pines"]
        
        # Store price history: (timestamp, buy_price, sell_price)
        self.price_history = deque(maxlen=1000)  # Keep last 1000 readings
        
    def get_p2p_offers(self, trade_type):
        """Fetch P2P offers from Binance"""
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        
        payload = {
            "page": 1,
            "rows": 10,
            "payTypes": self.payment_methods,
            "asset": self.asset,
            "tradeType": trade_type,
            "fiat": self.fiat,
            "publisherType": None
        }
        
        headers = {"Content-Type": "application/json"}
        
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=10)
            response.raise_for_status()
            return response.json()
        except Exception as e:
            print(f"Error fetching {trade_type} data: {e}")
            return None
    
    def filter_offers_by_exclude(self, offers):
        """Filter out offers with excluded payment methods"""
        if not self.exclude_methods:
            return offers
        
        exclude_normalized = [m.strip().lower() for m in self.exclude_methods]
        filtered = []
        
        for offer in offers:
            trade_methods = offer.get("adv", {}).get("tradeMethods", [])
            methods = [m.get("tradeMethodName", "") for m in trade_methods if m.get("tradeMethodName")]
            methods_normalized = [m.strip().lower() for m in methods]
            
            # Skip if any method is excluded
            has_excluded = any(method in exclude_normalized for method in methods_normalized)
            if not has_excluded:
                filtered.append(offer)
        
        return filtered
    
    def get_best_prices(self):
        """Get best buy and sell prices"""
        buy_data = self.get_p2p_offers("BUY")
        sell_data = self.get_p2p_offers("SELL")
        
        if not buy_data or not sell_data:
            return None, None
        
        buy_offers = self.filter_offers_by_exclude(buy_data.get("data", []))
        sell_offers = self.filter_offers_by_exclude(sell_data.get("data", []))
        
        if not buy_offers or not sell_offers:
            return None, None
        
        best_buy = float(buy_offers[0].get("adv", {}).get("price", 0))
        best_sell = float(sell_offers[0].get("adv", {}).get("price", 0))
        
        return best_buy, best_sell
    
    def record_price(self, buy_price, sell_price):
        """Record a price reading"""
        timestamp = datetime.now()
        self.price_history.append((timestamp, buy_price, sell_price))
    
    def get_price_at_time(self, minutes_ago):
        """Get price from N minutes ago"""
        if not self.price_history:
            return None, None
        
        target_time = datetime.now() - timedelta(minutes=minutes_ago)
        
        # Find closest price reading to target time
        closest = min(self.price_history, 
                     key=lambda x: abs((x[0] - target_time).total_seconds()))
        
        # Only return if within 2 minutes of target
        if abs((closest[0] - target_time).total_seconds()) < 120:
            return closest[1], closest[2]
        
        return None, None
    
    def calculate_changes(self, current_buy, current_sell):
        """Calculate price changes over different time periods"""
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
    
    def display_status(self, buy_price, sell_price, changes):
        """Display current status and changes"""
        os.system('cls' if os.name == 'nt' else 'clear')
        
        print("=" * 70)
        print(f"Binance P2P {self.fiat}/{self.asset} Price Tracker")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 70)
        print(f"\nCurrent Prices:")
        print(f"  Best BUY:  {buy_price:.2f} {self.fiat} (you buy {self.asset})")
        print(f"  Best SELL: {sell_price:.2f} {self.fiat} (you sell {self.asset})")
        print(f"  Spread: {buy_price - sell_price:.2f} {self.fiat} " +
              f"({((buy_price/sell_price - 1) * 100):.2f}%)")
        
        if changes:
            print(f"\nPrice Changes:")
            for period, data in sorted(changes.items()):
                print(f"\n  {period}:")
                print(f"    BUY:  {data['buy_change']:+.2f}% " +
                      f"({data['buy_old']:.2f} → {buy_price:.2f})")
                print(f"    SELL: {data['sell_change']:+.2f}% " +
                      f"({data['sell_old']:.2f} → {sell_price:.2f})")
        
        print(f"\nHistory: {len(self.price_history)} readings stored")
        print("=" * 70)
    
    def check_alert(self, changes, threshold):
        """Check if any changes exceed threshold"""
        alerts = []
        
        for period, data in changes.items():
            if abs(data['buy_change']) >= threshold:
                direction = "UP" if data['buy_change'] > 0 else "DOWN"
                alerts.append(
                    f"🚨 BUY price {direction} {abs(data['buy_change']):.2f}% in {period}"
                )
            
            if abs(data['sell_change']) >= threshold:
                direction = "UP" if data['sell_change'] > 0 else "DOWN"
                alerts.append(
                    f"🚨 SELL price {direction} {abs(data['sell_change']):.2f}% in {period}"
                )
        
        return alerts
    
    def run(self, check_interval=30, alert_threshold=2.0):
        """Run the tracker continuously"""
        print(f"Starting P2P Price Tracker...")
        print(f"Check interval: {check_interval} seconds")
        print(f"Alert threshold: ±{alert_threshold}%")
        if self.payment_methods:
            print(f"Payment methods: {', '.join(self.payment_methods)}")
        if self.exclude_methods:
            print(f"Excluding: {', '.join(self.exclude_methods)}")
        print("\nPress Ctrl+C to stop\n")
        
        iteration = 0
        
        try:
            while True:
                iteration += 1
                
                # Get current prices
                buy_price, sell_price = self.get_best_prices()
                
                if buy_price and sell_price:
                    # Record price
                    self.record_price(buy_price, sell_price)
                    
                    # Calculate changes
                    changes = self.calculate_changes(buy_price, sell_price)
                    
                    # Display status
                    self.display_status(buy_price, sell_price, changes)
                    
                    # Check for alerts
                    alerts = self.check_alert(changes, alert_threshold)
                    if alerts:
                        print("\n🔔 ALERTS:")
                        for alert in alerts:
                            print(f"  {alert}")
                        print()
                        # You can add email/SMS/sound alerts here
                    
                    # Save data periodically (every 10 readings)
                    if iteration % 10 == 0:
                        self.save_history()
                else:
                    print(f"Failed to fetch prices at {datetime.now()}")
                
                # Wait before next check
                time.sleep(check_interval)
                
        except KeyboardInterrupt:
            print("\n\nStopping tracker...")
            self.save_history()
            print("History saved. Goodbye!")
    
    def save_history(self):
        """Save price history to file"""
        filename = f"price_history_{self.fiat}_{self.asset}.json"
        
        data = {
            "last_updated": datetime.now().isoformat(),
            "history": [
                {
                    "timestamp": ts.isoformat(),
                    "buy": buy,
                    "sell": sell
                }
                for ts, buy, sell in self.price_history
            ]
        }
        
        try:
            with open(filename, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving history: {e}")
    
    def load_history(self):
        """Load price history from file"""
        filename = f"price_history_{self.fiat}_{self.asset}.json"
        
        if not os.path.exists(filename):
            return
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            for entry in data.get("history", []):
                ts = datetime.fromisoformat(entry["timestamp"])
                # Only load recent history (last 24 hours)
                if (datetime.now() - ts).total_seconds() < 86400:
                    self.price_history.append((ts, entry["buy"], entry["sell"]))
            
            print(f"Loaded {len(self.price_history)} historical readings")
        except Exception as e:
            print(f"Error loading history: {e}")


def main():
    parser = argparse.ArgumentParser(description='Track Binance P2P VES prices')
    parser.add_argument('--payment-methods', '-p', nargs='+',
                       help='Filter by payment methods')
    parser.add_argument('--interval', '-i', type=int, default=DEFAULT_CHECK_INTERVAL,
                       help=f'Check interval in seconds (default: {DEFAULT_CHECK_INTERVAL})')
    parser.add_argument('--threshold', '-t', type=float, default=DEFAULT_ALERT_THRESHOLD,
                       help=f'Alert threshold percentage (default: {DEFAULT_ALERT_THRESHOLD})')
    parser.add_argument('--asset', default='USDT',
                       help='Crypto asset (default: USDT)')
    parser.add_argument('--fiat', default='VES',
                       help='Fiat currency (default: VES)')
    
    args = parser.parse_args()
    
    # Validate interval
    if args.interval < 10:
        print("Warning: Interval less than 10 seconds may exceed rate limits!")
        print("Recommended: 30 seconds or more")
        response = input("Continue anyway? (y/n): ")
        if response.lower() != 'y':
            return
    
    tracker = PriceTracker(
        asset=args.asset,
        fiat=args.fiat,
        payment_methods=args.payment_methods
    )
    
    # Load previous history
    tracker.load_history()
    
    # Run tracker
    tracker.run(check_interval=args.interval, alert_threshold=args.threshold)


if __name__ == "__main__":
    main()
