# How to Use the P2P Tracker

## Quick Start (3 Steps)

### Option A: With Config File (Recommended)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Create config file
cp config.example.json config.json
# Edit config.json with your settings

# 3. Run (automatically loads config.json)
python price_tracker_prod.py
```

### Option B: Without Config File (CLI Only)

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Run with command line flags
python price_tracker_prod.py -p "PagoMovil"

# 3. Stop with Ctrl+C when done
```

## What Happens When You Run It

### Console Output

```
======================================================================
Binance P2P VES/USDT Price Tracker
Time: 2026-01-08 17:30:15
Status: RUNNING
======================================================================

Current Prices:
  Best BUY:  68.50 VES
  Best SELL: 67.80 VES
  Spread: 0.70 VES (1.03%)

Price Changes:

  15m:
    BUY:  +2.50% (66.83 → 68.50)  ← Alert!
    SELL: +1.20% (66.99 → 67.80)

  30m:
    BUY:  +1.80% (67.29 → 68.50)
    SELL: +0.90% (67.19 → 67.80)

Monitoring:
  History: 45 readings
  Failures: 0
  Next check: 30s
======================================================================
```

**Understanding the Display:**
- **BUY Price** = What you PAY to buy USDT (you give VES, get USDT)
- **SELL Price** = What you GET for selling USDT (you give USDT, get VES)
- **Spread** = Difference between buy and sell
- **Changes** = Price movement over 15min, 30min, 1 hour
- **Alert** = Triggered when change exceeds your threshold (default 2%)

## Config File vs Command Line Flags

**How it works:**

1. **Script automatically loads `config.json`** if it exists (no need to specify!)
2. **CLI flags override** any settings from config.json
3. **If no config.json**, use CLI flags for everything

**Example:**
```json
// config.json (loaded automatically)
{
  "payment_methods": ["PagoMovil"],
  "check_interval": 60,
  "alert_threshold": 2.0
}
```

```bash
# Uses ALL settings from config.json
python price_tracker_prod.py

# Uses config.json BUT overrides payment method to Banesco
python price_tracker_prod.py -p "Banesco"

# Uses config.json BUT overrides threshold to 5%
python price_tracker_prod.py -t 5.0

# Ignores config.json completely (uses these CLI settings)
python price_tracker_prod.py -p "Mercantil" -i 30 -t 3.0 --fiat VES
```

**Best practices:**
- ✅ **Production:** Create config.json, run with no arguments
- ✅ **Testing variations:** Run with overrides: `python price_tracker_prod.py -p "Other"`
- ✅ **Quick one-off:** Use CLI flags only (no config.json needed)

## Usage Options

### 1. Simple Usage (Recommended for Testing)

```bash
# Monitor PagoMovil prices, check every 30 seconds, alert on 2% change
python price_tracker_prod.py -p "PagoMovil"
```

### 2. Custom Settings

```bash
# Check every 60 seconds, alert on 3% change
python price_tracker_prod.py -p "PagoMovil" -i 60 -t 3.0
```

### 3. Multiple Payment Methods

```bash
# Monitor multiple payment methods
python price_tracker_prod.py -p "PagoMovil" "Banesco" "Mercantil"
```

### 4. With Configuration File

```bash
# Use config.json for all settings
python price_tracker_prod.py --config config.json
```

## Common Use Cases

### Use Case 1: Quick Price Check
**Scenario:** Just want to see current prices

```bash
# Use the simple checker (one-time check)
python binance_p2p_ves.py -p "PagoMovil"
```

### Use Case 2: Monitor Prices While Working
**Scenario:** Keep tracker running in a terminal while you work

```bash
# Start tracker in a terminal window
python price_tracker_prod.py -p "PagoMovil" -i 30 -t 2.0

# Leave it running, check periodically
# Press Ctrl+C to stop
```

### Use Case 3: Get Alerts via Email
**Scenario:** Want email notifications when prices move

1. Edit `config.json`:
```json
{
  "payment_methods": ["PagoMovil"],
  "check_interval": 60,
  "alert_threshold": 2.0,

  "email_enabled": true,
  "email_smtp_host": "smtp.gmail.com",
  "email_smtp_port": 587,
  "email_from": "your@gmail.com",
  "email_to": "alerts@gmail.com",
  "email_password": "your_app_password"
}
```

2. Run:
```bash
python price_tracker_prod.py --config config.json
```

**Gmail Setup:**
- Go to: https://myaccount.google.com/apppasswords
- Generate app password
- Use that password in config

### Use Case 4: Send to Slack/Discord
**Scenario:** Want alerts in Slack or Discord

1. Get webhook URL:
   - **Slack:** https://api.slack.com/messaging/webhooks
   - **Discord:** Server Settings → Integrations → Webhooks

2. Edit `config.json`:
```json
{
  "payment_methods": ["PagoMovil"],
  "webhook_enabled": true,
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

3. Run:
```bash
python price_tracker_prod.py --config config.json
```

### Use Case 5: Run 24/7 on Server
**Scenario:** Want it running continuously on a VPS or server

**Windows (Task Scheduler):**
1. Open Task Scheduler
2. Create Task:
   - Trigger: At startup
   - Action: Run `python price_tracker_prod.py --config config.json`
   - Settings: Restart on failure

**Linux (systemd):**
```bash
# Copy files to /opt/p2p_tracker
sudo cp * /opt/p2p_tracker/

# Install service
sudo cp p2p-tracker.service /etc/systemd/system/
sudo systemctl enable p2p-tracker
sudo systemctl start p2p-tracker

# Check status
sudo systemctl status p2p-tracker

# View logs
sudo journalctl -u p2p-tracker -f
```

## Command Line Options

### Required
```bash
-p, --payment-methods    Payment method(s) to monitor
                        Example: -p "PagoMovil"
                        Example: -p "PagoMovil" "Banesco"
```

### Optional
```bash
-i, --interval          Seconds between checks (default: 30, min: 10)
                        Example: -i 60

-t, --threshold         Alert threshold % (default: 2.0)
                        Example: -t 3.0

-m, --min-amount        Minimum transaction amount in fiat (default: 0)
                        Example: -m 60000 (for 60,000 VES)
                        Filters offers that can't handle your order size

--asset                 Crypto asset (default: USDT)
--fiat                  Fiat currency (default: VES)

-c, --config            Use config file
                        Example: --config config.json
```

### Email Options
```bash
--email-enabled         Enable email alerts
--email-smtp-host       SMTP server (smtp.gmail.com)
--email-smtp-port       SMTP port (587)
--email-from            Your email
--email-to              Alert destination email
--email-password        App password
```

### Webhook Options
```bash
--webhook-enabled       Enable webhook
--webhook-url           Webhook URL
```

## Tips & Best Practices

### ✅ DO:
- Start with 30-60 second intervals
- Use 2-3% alert threshold initially
- Test with email/webhook before deploying
- Keep terminal open when testing
- Check logs regularly: `tail -f price_tracker.log`

### ❌ DON'T:
- Use intervals below 10 seconds (will be rejected)
- Run multiple instances with same config (redundant)
- Commit config.json to git (has credentials)
- Use your main email password (use app password)

## Monitoring

### View Logs
```bash
# Real-time log viewing
tail -f price_tracker.log           # Linux/Mac
Get-Content price_tracker.log -Wait # Windows PowerShell

# Search for alerts
grep ALERT price_tracker.log
```

### Check History
```bash
# View saved price history
cat price_history_VES_USDT.json
```

### Stop the Tracker
```bash
# Press Ctrl+C in the terminal
# Or if running as service:
sudo systemctl stop p2p-tracker  # Linux
# Stop in Task Scheduler           # Windows
```

## Troubleshooting

### "ModuleNotFoundError: No module named 'requests'"
**Solution:**
```bash
pip install -r requirements.txt
```

### "ValueError: check_interval must be at least 10 seconds"
**Solution:**
```bash
# Use 10 or higher
python price_tracker_prod.py -p "PagoMovil" -i 30
```

### No alerts appearing
**Possible causes:**
1. Threshold too high (try `-t 1.0`)
2. Not enough history yet (wait 15+ minutes)
3. Prices not moving much

**Solution:**
```bash
# Lower threshold to test
python price_tracker_prod.py -p "PagoMovil" -t 1.0
```

### Prices not fetching
**Check:**
1. Internet connection
2. Binance P2P accessible: https://p2p.binance.com
3. Payment method name correct (case sensitive)

## Examples

### Example 1: Conservative Monitoring
```bash
# Check every minute, only alert on large moves
python price_tracker_prod.py -p "PagoMovil" -i 60 -t 5.0
```

### Example 2: Aggressive Monitoring
```bash
# Check every 30 seconds, alert on small moves
python price_tracker_prod.py -p "PagoMovil" -i 30 -t 1.0
```

### Example 3: Filter by Minimum Amount
```bash
# Only show offers that can handle 60,000 VES or more
python price_tracker_prod.py -p "PagoMovil" -m 60000

# Useful when you need to trade specific amounts
# Filters out small offers that can't handle your order
```

### Example 4: Multiple Banks
```bash
# Monitor several payment methods
python price_tracker_prod.py -p "PagoMovil" "Banesco" "Mercantil" "Venezuela"
```

### Example 5: Different Currency Pair
```bash
# Monitor BTC/VES instead of USDT/VES
python price_tracker_prod.py -p "PagoMovil" --asset BTC --fiat VES
```

### Example 5: Testing
```bash
# Test for 5 minutes then stop
timeout 300 python price_tracker_prod.py -p "PagoMovil"  # Linux/Mac
```

## Getting Help

### In-app Help
```bash
python price_tracker_prod.py --help
```

### Check Logs
```bash
cat price_tracker.log | tail -50
```

### Test Scripts
```bash
# Test basic functionality
python test_run.py

# Test validation
python test_validation.py
```

### Documentation
- Quick setup: `QUICK_START.md`
- Full deployment: `DEPLOYMENT.md`
- Test results: `TESTING.md`
- Pre-deployment: `PRODUCTION_CHECKLIST.md`

## Next Steps

1. **Try it now:**
   ```bash
   python price_tracker_prod.py -p "PagoMovil"
   ```

2. **Watch for 15 minutes** to see price changes

3. **Add alerts:**
   - Configure email in `config.json`
   - Or set up webhook for Slack/Discord

4. **Deploy permanently:**
   - Windows: Use Task Scheduler
   - Linux: Use systemd service
   - Docker: Use docker-compose

## Summary

**Simplest usage:**
```bash
python price_tracker_prod.py -p "PagoMovil"
```

**Stop it:**
```
Press Ctrl+C
```

**That's it!** Everything else is optional configuration for alerts and automation.
