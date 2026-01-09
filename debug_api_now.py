#!/usr/bin/env python3
"""
Debug what API returns right now vs what app shows
"""
import requests
import json

url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
headers = {"Content-Type": "application/json"}

print("=" * 80)
print("CHECKING WHAT API RETURNS RIGHT NOW")
print("Looking for 'Sushi' profile at 715.800 VES")
print("=" * 80)

# Test SELL with PagoMovil filter
payload = {
    "page": 1,
    "rows": 20,
    "payTypes": ["PagoMovil"],
    "transAmount": "60000",
    "asset": "USDT",
    "tradeType": "SELL",
    "fiat": "VES",
    "publisherType": None
}

print("\nRequest payload:")
print(json.dumps(payload, indent=2))
print()

try:
    response = requests.post(url, json=payload, headers=headers, timeout=10)
    data = response.json()
    offers = data.get("data", [])

    print(f"API returned {len(offers)} offers\n")

    # Look for Sushi
    found_sushi = False

    for i, offer in enumerate(offers, 1):
        adv = offer.get("adv", {})
        advertiser = offer.get("advertiser", {})

        trader = advertiser.get("nickName", "N/A")
        price = float(adv.get("price", 0))
        orders = advertiser.get("monthOrderCount", 0)
        all_time_orders = advertiser.get("orderCount", 0)
        methods = [m.get("tradeMethodName", "") for m in adv.get("tradeMethods", [])]
        min_ves = float(adv.get("minSingleTransAmount", 0))
        max_ves = float(adv.get("dynamicMaxSingleTransAmount", 0))

        print(f"{i}. {trader}")
        print(f"   Price: {price:.3f} VES/USDT")
        print(f"   Orders (month): {orders}, All-time: {all_time_orders}")
        print(f"   Range: {min_ves:,.0f} - {max_ves:,.0f} VES")
        print(f"   Payment: {', '.join(methods)}")

        if "sushi" in trader.lower():
            print(f"   >>> FOUND SUSHI! <<<")
            found_sushi = True

        print()

        # Stop after 10
        if i >= 10:
            break

    if not found_sushi:
        print("\n!!! SUSHI NOT FOUND IN FIRST 10 RESULTS !!!")
        print("Checking if Sushi is in all 20 results...")

        for offer in offers:
            advertiser = offer.get("advertiser", {})
            trader = advertiser.get("nickName", "")
            if "sushi" in trader.lower():
                price = float(offer.get("adv", {}).get("price", 0))
                print(f"\nFOUND: {trader} at {price:.3f} VES")
                found_sushi = True
                break

        if not found_sushi:
            print("\nSushi is NOT in the API results at all!")
            print("\nPossible reasons:")
            print("1. Sushi's offer doesn't have PagoMovil")
            print("2. Sushi's offer range doesn't include 60,000 VES")
            print("3. Different API endpoint or parameters needed")

except Exception as e:
    print(f"ERROR: {e}")
    import traceback
    traceback.print_exc()
