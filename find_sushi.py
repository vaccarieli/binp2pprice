#!/usr/bin/env python3
"""
Find Sushi profile - try without amount filter
"""
import requests

url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
headers = {"Content-Type": "application/json"}

print("=" * 80)
print("SEARCHING FOR SUSHI - WITHOUT AMOUNT FILTER")
print("=" * 80)

# WITHOUT transAmount filter
payload = {
    "page": 1,
    "rows": 20,
    "payTypes": ["PagoMovil"],
    # NO transAmount!
    "asset": "USDT",
    "tradeType": "SELL",
    "fiat": "VES",
    "publisherType": None
}

print("\nWithout amount filter:")
try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    data = response.json()
    offers = data.get("data", [])

    for i, offer in enumerate(offers[:5], 1):
        adv = offer.get("adv", {})
        advertiser = offer.get("advertiser", {})
        trader = advertiser.get("nickName", "N/A")
        price = float(adv.get("price", 0))
        orders = advertiser.get("monthOrderCount", 0)

        print(f"{i}. {trader}: {price:.3f} VES (Orders: {orders})")

        if "sushi" in trader.lower():
            print(f"   >>> FOUND SUSHI! <<<")

    # Check all 20
    for offer in offers:
        trader = offer.get("advertiser", {}).get("nickName", "")
        if "sushi" in trader.lower():
            price = float(offer.get("adv", {}).get("price", 0))
            orders = offer.get("advertiser", {}).get("monthOrderCount", 0)
            all_orders = offer.get("advertiser", {}).get("orderCount", 0)
            min_ves = float(offer.get("adv", {}).get("minSingleTransAmount", 0))
            max_ves = float(offer.get("adv", {}).get("dynamicMaxSingleTransAmount", 0))

            print(f"\n*** FOUND SUSHI! ***")
            print(f"Trader: {trader}")
            print(f"Price: {price:.3f} VES/USDT")
            print(f"Orders (month): {orders}")
            print(f"Orders (all-time): {all_orders}")
            print(f"Range: {min_ves:,.0f} - {max_ves:,.0f} VES")
            break
    else:
        print("\nSushi still not found!")

except Exception as e:
    print(f"ERROR: {e}")

# Also try BUY side
print("\n" + "=" * 80)
print("ALSO CHECKING BUY SIDE")
print("=" * 80)

payload["tradeType"] = "BUY"

try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    data = response.json()
    offers = data.get("data", [])

    for offer in offers:
        trader = offer.get("advertiser", {}).get("nickName", "")
        if "sushi" in trader.lower():
            price = float(offer.get("adv", {}).get("price", 0))
            print(f"\nFound Sushi on BUY side: {price:.3f} VES")
            break
    else:
        print("Sushi not on BUY side either")

except Exception as e:
    print(f"ERROR: {e}")
