# How to Capture Binance P2P API Calls

## Method 1: Browser DevTools (Easiest)

1. Open Chrome/Edge/Firefox
2. Go to: https://p2p.binance.com/en/trade/sell/USDT?fiat=VES
3. Press **F12** to open Developer Tools
4. Click **Network** tab
5. Check **Preserve log**
6. Filter by typing: `search`
7. Set your filters in Binance (Pago Movil, amount, etc.)
8. Click on the `adv/search` request
9. Look at **Payload** or **Request** tab
10. Copy the exact JSON payload

You'll see something like:
```json
{
  "page": 1,
  "rows": 10,
  "payTypes": ["PagoMovil"],
  "countries": [],
  "publisherType": null,
  "asset": "USDT",
  "fiat": "VES",
  "tradeType": "SELL",
  ... (other fields)
}
```

## Method 2: Fiddler (For Desktop App)

If using the Binance desktop app:

1. Download Fiddler: https://www.telerik.com/download/fiddler
2. Install and run Fiddler
3. Enable HTTPS decryption:
   - Tools → Options → HTTPS
   - Check "Decrypt HTTPS traffic"
   - Install certificate when prompted
4. Open Binance desktop app
5. Apply your filters
6. In Fiddler, look for requests to `p2p.binance.com`
7. Click on request → Inspectors → Raw or JSON
8. See exact request payload

## Method 3: mitmproxy (Advanced)

```bash
# Install
pip install mitmproxy

# Run
mitmweb

# Configure Windows proxy to localhost:8080
# Install mitmproxy certificate
# Open Binance app
# View requests at http://localhost:8081
```

## What to Look For

Key fields that might be different:
- `countries`: []
- `publisherType`: null or "merchant"
- `proMerchantAds`: false
- `shieldMerchantAds`: false
- `filterType`: "all" or "tradable"
- `periods`: []
- `additionalKycVerifyFilter`: 0
- `classifies`: ["mass", "profession", "fiat_trade"]

## Quick Test

After capturing the payload, test it:

```bash
cd /c/Users/elios/OneDrive/Desktop/p2p_tracker

# Create test file with captured payload
cat > test_captured.json << 'EOF'
{
  "page": 1,
  "rows": 20,
  "payTypes": ["PagoMovil"],
  "asset": "USDT",
  "tradeType": "SELL",
  "fiat": "VES",
  "publisherType": null
  # ... add all other fields you captured
}
EOF

# Test it
python -c "
import requests, json
payload = json.load(open('test_captured.json'))
r = requests.post('https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search',
  json=payload, headers={'Content-Type':'application/json'})
print(r.json().get('data', [])[:3])
"
```
