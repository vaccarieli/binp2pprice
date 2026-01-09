# Quick Start Guide

## Installation (5 minutes)

### Step 1: Install Dependencies

```bash
# Install Python dependencies
pip install -r requirements.txt
```

### Step 2: Create Configuration

```bash
# Copy example config
cp config.example.json config.json

# Edit configuration
nano config.json  # Linux/Mac
notepad config.json  # Windows
```

**Minimum required changes:**
- Set `payment_methods`: `["PagoMovil"]` or your preferred methods
- Set `check_interval`: `30` (seconds between checks, minimum 10)
- Set `alert_threshold`: `2.0` (percentage change to trigger alert)

### Step 3: Run the Tracker

```bash
# Automatically loads config.json
python price_tracker_prod.py

# Or without config file (using CLI flags)
python price_tracker_prod.py -p "PagoMovil" -i 30 -t 2.0
```

Press `Ctrl+C` to stop.

## Configuration Options

### Essential Settings

```json
{
  "asset": "USDT",
  "fiat": "VES",
  "check_interval": 30,
  "alert_threshold": 2.0,
  "payment_methods": ["PagoMovil"],
  "exclude_methods": ["Recarga Pines"],
  "min_amount": 0
}
```

**Note:** Set `min_amount` to filter by order size (e.g., `60000` for 60,000 VES minimum)

### Email Alerts (Optional)

```json
{
  "email_enabled": true,
  "email_smtp_host": "smtp.gmail.com",
  "email_smtp_port": 587,
  "email_from": "your_email@gmail.com",
  "email_to": "alert_email@gmail.com",
  "email_password": "your_app_password"
}
```

**Gmail Setup:**
1. Enable 2FA: https://myaccount.google.com/security
2. Create App Password: https://myaccount.google.com/apppasswords
3. Use app password in config (not your Gmail password)

### Webhook Alerts (Optional)

```json
{
  "webhook_enabled": true,
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

**Slack Setup:**
1. Go to https://api.slack.com/messaging/webhooks
2. Create Incoming Webhook
3. Copy URL to config

**Discord Setup:**
1. Server Settings → Integrations → Webhooks
2. Create webhook
3. Copy URL to config

## Common Commands

### Test Configuration

```bash
# Test with payment method filter
python price_tracker_prod.py -p "PagoMovil"

# Test with custom interval
python price_tracker_prod.py -p "PagoMovil" -i 60

# Test with lower threshold
python price_tracker_prod.py -p "PagoMovil" -t 1.0
```

### Monitor Logs

```bash
# View log file in real-time
tail -f price_tracker.log  # Linux/Mac
Get-Content price_tracker.log -Wait  # Windows PowerShell

# Search for errors
grep ERROR price_tracker.log  # Linux/Mac
Select-String -Pattern "ERROR" price_tracker.log  # Windows PowerShell

# Search for alerts
grep ALERT price_tracker.log  # Linux/Mac
Select-String -Pattern "ALERT" price_tracker.log  # Windows PowerShell
```

## Running in Background

### Linux/Mac

```bash
# Run in background
nohup python price_tracker_prod.py --config config.json > /dev/null 2>&1 &

# Check if running
ps aux | grep price_tracker

# Stop
pkill -f price_tracker_prod.py
```

### Windows

```powershell
# Run in background
Start-Process python -ArgumentList "price_tracker_prod.py --config config.json" -WindowStyle Hidden

# Check if running
Get-Process python

# Stop
Stop-Process -Name python
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'requests'"

```bash
pip install -r requirements.txt
```

### "ValueError: check_interval must be at least 10 seconds"

Edit config.json and set `check_interval` to 10 or higher.

### "Invalid email_from address"

Check that email addresses in config.json are properly formatted:
- Good: `user@example.com`
- Bad: `user@example`, `user.example.com`

### "Failed to send email"

1. Verify SMTP credentials
2. Use app password (not regular password) for Gmail
3. Check firewall isn't blocking port 587
4. Test SMTP connection:
   ```bash
   telnet smtp.gmail.com 587
   ```

### No alerts appearing

1. Check that threshold is not too high (try 1.0)
2. Wait at least 15 minutes to build price history
3. Verify payment methods are correct
4. Check log file for errors

### Rate limit errors (429/418)

1. Increase `check_interval` to 60 seconds or more
2. Script handles rate limits automatically
3. If persistent, wait several hours before retrying

## What to Expect

### First 15 minutes
- No alerts (building price history)
- Console shows current prices
- Log file being written

### After 15 minutes
- Price changes calculated for 15m period
- Alerts triggered if threshold exceeded

### After 30 minutes
- Price changes for 15m and 30m periods shown

### After 1 hour
- Full functionality with 15m, 30m, and 1h price changes

## Understanding the Output

```
======================================================================
Binance P2P VES/USDT Price Tracker
Time: 2026-01-08 14:30:00
Status: RUNNING
======================================================================

Current Prices:
  Best BUY:  68.50 VES
  Best SELL: 67.80 VES
  Spread: 0.70 VES (1.03%)

Price Changes:

  15m:
    BUY:  +2.50% (66.83 → 68.50)  ← 2.5% increase, alert triggered!
    SELL: +1.20% (66.99 → 67.80)

  30m:
    BUY:  +3.80% (65.99 → 68.50)  ← 3.8% increase, alert triggered!
    SELL: +2.10% (66.41 → 67.80)  ← 2.1% increase, alert triggered!

Monitoring:
  History: 45 readings
  Failures: 0
  Next check: 30s
======================================================================
```

**Interpretation:**
- BUY price: What you pay to buy USDT (you give VES, receive USDT)
- SELL price: What you get for selling USDT (you give USDT, receive VES)
- Spread: Difference between buy and sell (market maker profit)
- Changes: Percentage change from 15m, 30m, and 1h ago
- Alert threshold: 2.0% means alerts trigger for ±2% changes

## Next Steps

1. **Test Run**: Run for 1 hour to verify everything works
2. **Configure Alerts**: Set up email or webhook notifications
3. **Deploy**: Use systemd (Linux) or Task Scheduler (Windows) for automatic startup
4. **Monitor**: Check logs regularly for errors or alerts

See `DEPLOYMENT.md` for production deployment instructions.

## Support

- Check logs: `cat price_tracker.log`
- Verify config: `cat config.json`
- Test connection: `curl -s https://p2p.binance.com/`
- Read full docs: `README.md` and `DEPLOYMENT.md`
