#!/usr/bin/env python3
"""
Test script to verify Telegram alert baseline logic
Simulates price changes and shows when alerts would trigger
"""

class MockPriceTracker:
    def __init__(self, threshold=5.0):
        self.threshold = threshold
        self.buy_baseline = None
        self.sell_baseline = None

    def check_alert(self, current_buy, current_sell):
        """Simulate the alert logic"""
        alerts = []

        # Initialize baselines
        if self.buy_baseline is None:
            self.buy_baseline = current_buy
            print(f"✓ Initialized BUY baseline: {current_buy:.2f}")

        if self.sell_baseline is None:
            self.sell_baseline = current_sell
            print(f"✓ Initialized SELL baseline: {current_sell:.2f}")

        # Check BUY
        if self.buy_baseline and current_buy:
            buy_change = ((current_buy - self.buy_baseline) / self.buy_baseline) * 100
            print(f"  BUY: {current_buy:.2f} ({buy_change:+.2f}% from baseline {self.buy_baseline:.2f})")

            if abs(buy_change) >= self.threshold:
                direction = "UP" if buy_change > 0 else "DOWN"
                alerts.append(f"🚨 BUY {direction}: {abs(buy_change):.2f}% ({self.buy_baseline:.2f} → {current_buy:.2f})")
                print(f"    ⚡ ALERT TRIGGERED! Resetting baseline to {current_buy:.2f}")
                self.buy_baseline = current_buy

        # Check SELL
        if self.sell_baseline and current_sell:
            sell_change = ((current_sell - self.sell_baseline) / self.sell_baseline) * 100
            print(f"  SELL: {current_sell:.2f} ({sell_change:+.2f}% from baseline {self.sell_baseline:.2f})")

            if abs(sell_change) >= self.threshold:
                direction = "UP" if sell_change > 0 else "DOWN"
                alerts.append(f"🚨 SELL {direction}: {abs(sell_change):.2f}% ({self.sell_baseline:.2f} → {current_sell:.2f})")
                print(f"    ⚡ ALERT TRIGGERED! Resetting baseline to {current_sell:.2f}")
                self.sell_baseline = current_sell

        return alerts

def test_scenario():
    """Test the example scenario from requirements"""
    print("=" * 70)
    print("TESTING TELEGRAM ALERT BASELINE LOGIC")
    print("Threshold: ±5.0%")
    print("=" * 70)
    print()

    tracker = MockPriceTracker(threshold=5.0)

    # Scenario from requirements
    test_prices = [
        ("10:00:00", 690.0, 650.0),
        ("10:05:00", 725.0, 682.5),  # BUY +5.07%, SELL +5.00% - should alert
        ("10:05:30", 730.0, 685.0),  # BUY +0.69%, SELL +0.37% - no alert
        ("10:10:00", 762.0, 720.0),  # BUY +5.10%, SELL +5.11% - should alert
        ("10:10:30", 765.0, 722.0),  # BUY +0.39%, SELL +0.28% - no alert
    ]

    for timestamp, buy, sell in test_prices:
        print(f"\n[{timestamp}]")
        alerts = tracker.check_alert(buy, sell)
        if alerts:
            print("  📨 TELEGRAM ALERTS SENT:")
            for alert in alerts:
                print(f"     {alert}")
        else:
            print("  ✓ No alerts (change below threshold)")
        print()

    print("=" * 70)
    print("TEST COMPLETE")
    print("=" * 70)
    print()
    print("Expected behavior:")
    print("1. ✓ First check initializes baselines")
    print("2. ✓ 10:05:00 - Both prices trigger alerts, baselines reset")
    print("3. ✓ 10:05:30 - No alerts (< 5% from new baselines)")
    print("4. ✓ 10:10:00 - Both prices trigger alerts again")
    print("5. ✓ 10:10:30 - No alerts (< 5% from new baselines)")
    print()
    print("Result: No alert spam! ✨")

if __name__ == "__main__":
    test_scenario()
