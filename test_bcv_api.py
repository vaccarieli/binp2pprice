#!/usr/bin/env python3
"""
Test script to verify BCV API integration
Tests multiple endpoints and shows the rate calculation
"""

import requests
import json

def test_bcv_endpoints():
    """Test all BCV API endpoints"""
    print("=" * 70)
    print("TESTING BCV API ENDPOINTS")
    print("=" * 70)
    print()

    endpoints = [
        {
            "name": "DolarAPI Venezuela",
            "url": "https://ve.dolarapi.com/v1/dolares/oficial",
            "parser": lambda data: float(data.get("promedio", 0)) if data.get("promedio") else None
        },
        {
            "name": "PyDolarVE",
            "url": "https://pydolarve.org/api/v1/dollar?monitor=bcv",
            "parser": lambda data: float(data["monitors"]["bcv"]["price"]) if "monitors" in data else None
        },
        {
            "name": "DolarToday S3",
            "url": "https://s3.amazonaws.com/dolartoday/data.json",
            "parser": lambda data: float(data["USD"]["promedio_real"]) if "USD" in data and "promedio_real" in data["USD"] else None
        }
    ]

    working_endpoints = []

    for endpoint in endpoints:
        print(f"Testing: {endpoint['name']}")
        print(f"URL: {endpoint['url']}")

        try:
            response = requests.get(endpoint['url'], timeout=5)
            response.raise_for_status()
            data = response.json()

            rate = endpoint['parser'](data)

            if rate and rate > 0:
                print(f"✅ SUCCESS - BCV Rate: {rate:.2f} VES")
                working_endpoints.append((endpoint['name'], rate))
            else:
                print(f"❌ FAILED - Could not parse rate from response")
                print(f"Response snippet: {str(data)[:200]}...")

        except requests.exceptions.RequestException as e:
            print(f"❌ FAILED - Network error: {e}")
        except json.JSONDecodeError as e:
            print(f"❌ FAILED - JSON parsing error: {e}")
        except Exception as e:
            print(f"❌ FAILED - Unexpected error: {e}")

        print()

    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)

    if working_endpoints:
        print(f"✅ Working endpoints: {len(working_endpoints)}/{len(endpoints)}")
        print()
        for name, rate in working_endpoints:
            print(f"  {name}: {rate:.2f} VES")
        print()

        # Test percentage calculation
        print("EXAMPLE CALCULATIONS:")
        bcv_rate = working_endpoints[0][1]
        test_prices = [
            ("P2P BUY", 685.0),
            ("P2P SELL", 653.0)
        ]

        for label, price in test_prices:
            diff = ((price - bcv_rate) / bcv_rate) * 100
            emoji = "📈" if diff > 0 else "📉"
            print(f"  {label}: {price:.2f} VES {emoji} {diff:+.1f}% vs BCV ({bcv_rate:.2f})")

    else:
        print("❌ No working endpoints found!")
        print()
        print("Possible issues:")
        print("  - APIs may be down or rate-limited")
        print("  - Network connectivity issues")
        print("  - API structure may have changed")
        print()
        print("The tracker will continue to work but won't show BCV rates")

    print("=" * 70)

if __name__ == "__main__":
    test_bcv_endpoints()
