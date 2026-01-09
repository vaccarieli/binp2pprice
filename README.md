# Binance P2P Price Tracker - Production Ready ✅

A robust, enterprise-ready price monitoring system for Binance P2P cryptocurrency markets with real-time alerts and comprehensive deployment options.

## Production Features

✅ **Robust Error Handling**
- Automatic retries with exponential backoff
- 429/418 rate limit detection and handling
- Graceful shutdown (SIGINT/SIGTERM)
- Validates all API responses

✅ **Multiple Alert Channels**
- Console logging
- Email (SMTP)
- Webhooks (Slack/Discord/etc)

✅ **Production Monitoring**
- Structured logging to file and console
- Tracks consecutive failures
- Health status indicators
- Automatic history persistence

✅ **Safe Rate Limiting**
- Conservative 30s default interval
- Dynamic backoff on failures
- Respects Retry-After headers

## Documentation

- **[QUICK_START.md](QUICK_START.md)** - Get started in 5 minutes
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Complete production deployment guide
- **[PRODUCTION_CHECKLIST.md](PRODUCTION_CHECKLIST.md)** - Pre-deployment validation
- **[TESTING.md](TESTING.md)** - Test results and verification

## Quick Start

### Recommended: With Config File
```bash
# 1. Copy and edit config
cp config.example.json config.json
nano config.json

# 2. Run (automatically loads config.json)
python price_tracker_prod.py
```

### Alternative: CLI Only
```bash
# Without config file
python price_tracker_prod.py -p "PagoMovil" -i 30 -t 2.0
```

### Override Config Settings
```bash
# Uses config.json but overrides payment method
python price_tracker_prod.py -p "Banesco"
```

## Configuration

### Command Line Arguments
```
Required:
  -p, --payment-methods    Payment methods to filter (e.g., "PagoMovil")

Optional:
  -i, --interval          Check interval in seconds (default: 30, min: 10)
  -t, --threshold         Alert threshold % (default: 2.0)
  -m, --min-amount        Minimum transaction amount in fiat (e.g., 60000)
  --asset                 Crypto asset (default: USDT)
  --fiat                  Fiat currency (default: VES)
  -c, --config            Load from JSON config file
  
Email Alerts:
  --email-enabled         Enable email alerts
  --email-smtp-host       SMTP server (e.g., smtp.gmail.com)
  --email-smtp-port       SMTP port (default: 587)
  --email-from            Sender email
  --email-to              Recipient email
  --email-password        Email password (use app password for Gmail)

Webhook Alerts:
  --webhook-enabled       Enable webhook
  --webhook-url           Webhook URL

Logging:
  --log-file             Log file path (default: price_tracker.log)
  --log-level            DEBUG|INFO|WARNING|ERROR (default: INFO)
```

### Config File (JSON)
See `config.example.json` for all available options.

## Email Setup

### Gmail
1. Enable 2FA on your Google account
2. Generate App Password: https://myaccount.google.com/apppasswords
3. Use app password in config:
```json
{
  "email_enabled": true,
  "email_smtp_host": "smtp.gmail.com",
  "email_smtp_port": 587,
  "email_from": "your@gmail.com",
  "email_to": "alert@gmail.com",
  "email_password": "your_app_password"
}
```

### Other Providers
- **Outlook**: smtp-mail.outlook.com:587
- **Yahoo**: smtp.mail.yahoo.com:587
- **ProtonMail**: smtp.protonmail.com:587

## Webhook Setup

### Slack
1. Create Incoming Webhook: https://api.slack.com/messaging/webhooks
2. Add to config:
```json
{
  "webhook_enabled": true,
  "webhook_url": "https://hooks.slack.com/services/YOUR/WEBHOOK/URL"
}
```

### Discord
1. Server Settings → Integrations → Webhooks → New Webhook
2. Copy URL and add to config

## Rate Limits

**Recommended**: 30-60 seconds between requests
- No official limit documented for P2P endpoint
- Conservative approach avoids bans
- Script enforces 10s minimum

**Rate Limit Responses**:
- 429: Temporary rate limit → automatic backoff
- 418: IP ban → waits for Retry-After period

## Monitoring

### Log Files
```bash
# View logs in real-time
tail -f price_tracker.log

# Check for errors
grep ERROR price_tracker.log

# Check alerts
grep ALERT price_tracker.log
```

### History Files
Price history saved as: `price_history_VES_USDT.json`
- Auto-saves every 10 iterations
- Loads last 24h on startup
- Atomic writes prevent corruption

## Production Deployment

### As Background Service (Linux)

Create systemd service `/etc/systemd/system/p2p-tracker.service`:
```ini
[Unit]
Description=Binance P2P Price Tracker
After=network.target

[Service]
Type=simple
User=youruser
WorkingDirectory=/path/to/tracker
ExecStart=/usr/bin/python3 /path/to/price_tracker_prod.py --config config.json
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable p2p-tracker
sudo systemctl start p2p-tracker
sudo systemctl status p2p-tracker
```

### Docker (Optional)
```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY price_tracker_prod.py config.json ./

CMD ["python", "price_tracker_prod.py", "--config", "config.json"]
```

## Troubleshooting

### High Consecutive Failures
- Check internet connection
- Verify Binance P2P is accessible
- Increase interval if rate limited

### No Alerts Triggering
- Verify threshold is not too high
- Check that enough time has passed (need 15m+ history)
- Review alert configuration

### Email Not Sending
- Verify SMTP credentials
- Check firewall/antivirus blocking port 587
- Test with telnet: `telnet smtp.gmail.com 587`

### Rate Limited (429/418)
- Script handles automatically
- If persistent, increase interval
- Check for other scripts/services using same IP

## Performance

- **Memory**: ~50MB typical
- **CPU**: <1% average
- **Disk**: ~1MB history per 24h
- **Network**: ~1KB per request

## Security Notes

- Store credentials in config file with restricted permissions:
  ```bash
  chmod 600 config.json
  ```
- Use app passwords, not main passwords
- Don't commit config files to git
- Consider environment variables for sensitive data

## Project Structure

```
p2p_tracker/
├── price_tracker_prod.py      # Production-ready main script
├── price_tracker.py            # Simple version for testing
├── binance_p2p_ves.py         # One-time price checker
├── config.example.json         # Configuration template
├── requirements.txt            # Python dependencies
├── .gitignore                 # Git ignore rules
│
├── README.md                   # This file
├── QUICK_START.md             # 5-minute setup guide
├── DEPLOYMENT.md              # Full deployment guide
├── PRODUCTION_CHECKLIST.md    # Pre-deployment checklist
│
├── Dockerfile                 # Docker container
├── docker-compose.yml         # Docker Compose config
├── .dockerignore             # Docker ignore rules
└── p2p-tracker.service       # Systemd service file
```

## Security Features

✅ **Input Validation**
- Configuration parameter validation
- Path traversal protection
- Email format validation
- URL validation for webhooks
- Secure file permissions

✅ **Credential Protection**
- Gitignore prevents accidental commits
- Config file permission warnings
- App password support
- No secrets in logs

✅ **Production Hardening**
- Non-root user execution
- Resource limits (systemd/Docker)
- Automatic restart on failure
- Health monitoring
- Rate limit protection

## What Makes This Production-Ready?

1. **Comprehensive Error Handling**
   - Automatic retry with exponential backoff
   - Rate limit detection (429/418)
   - Network timeout handling
   - Graceful degradation

2. **Enterprise Deployment Options**
   - Systemd service (Linux)
   - Docker containerization
   - Windows Task Scheduler
   - Cloud VPS ready

3. **Monitoring & Observability**
   - Structured logging (file + console)
   - Health checks
   - Performance metrics
   - Alert tracking

4. **Reliability**
   - Atomic file writes
   - History persistence
   - Graceful shutdown (SIGINT/SIGTERM)
   - Service auto-restart

5. **Security**
   - Input validation
   - Secure defaults
   - Credential protection
   - Minimal privileges

## License

MIT - Use at your own risk. Not affiliated with Binance.

## Support & Contributing

- Report issues on GitHub
- Check logs first: `price_tracker.log`
- Review documentation before asking
- Security issues: Report privately

## Disclaimer

This software is for educational and informational purposes. Cryptocurrency trading involves risk. Always verify prices on official platforms before making decisions. Not financial advice.
# binp2pprice
