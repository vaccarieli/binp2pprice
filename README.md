# Binance P2P VES/USDT Price Tracker

Monitor Binance P2P prices for Venezuelan Bolívares (VES) with real-time Telegram alerts and BCV rate comparison.

## Features

✅ **Modern Telegram Alerts**
- Beautiful formatted messages with visual indicators
- Regular price updates every 15 seconds
- Sudden price change alerts (configurable threshold)
- Separate alerts for BUY and SELL with trader information
- Bilingual support (Spanish/English)

✅ **BCV Integration**
- Displays official Venezuelan exchange rate
- Shows P2P premium percentage vs BCV
- 1-hour caching to minimize API calls

✅ **Smart Alert System**
- Tracks sudden price changes independently for BUY and SELL
- Preserves opposite direction alerts (UP vs DOWN)
- Captures trader info at the moment of change
- No spam - intelligent baseline reset

✅ **Robust Monitoring**
- Automatic retries with backoff
- Rate limit handling
- Historical data tracking
- Graceful shutdown support

## Quick Start

### 1. Install Dependencies
```bash
pip install -r requirements.txt
```

### 2. Configure Telegram Bot

**Create Bot:**
1. Message [@BotFather](https://t.me/BotFather) on Telegram
2. Send `/newbot` and follow instructions
3. Save the bot token

**Get Chat ID:**
```bash
python get_telegram_chat_id.py
# Send a message to your bot, then check the output
```

### 3. Edit Configuration

Copy and edit `config.json`:
```json
{
  "asset": "USDT",
  "fiat": "VES",
  "check_interval": 15,
  "payment_methods": ["Pago Movil"],
  "min_amount": 60000,

  "telegram_enabled": true,
  "telegram_bot_token": "YOUR_BOT_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "telegram_regular_updates": true,
  "telegram_sudden_change_threshold": 5.0,
  "telegram_language": "es"
}
```

### 4. Run the Tracker
```bash
python price_tracker_prod.py
```

## Configuration Options

### Core Settings
- `check_interval`: Seconds between price checks (default: 15)
- `payment_methods`: Filter by payment methods (e.g., "Pago Movil")
- `min_amount`: Minimum transaction amount in VES

### Telegram Settings
- `telegram_enabled`: Enable/disable Telegram alerts
- `telegram_bot_token`: Your bot token from BotFather
- `telegram_chat_id`: Your chat/group ID
- `telegram_regular_updates`: Send periodic updates (true/false)
- `telegram_sudden_change_threshold`: % change to trigger alerts (default: 5.0)
- `telegram_language`: Message language - "es" (Spanish) or "en" (English)

### Alert Behavior
- **Regular Updates**: Price status every check interval (edited message)
- **Sudden Changes**: New alert when price moves ≥ threshold%
- **Smart Deletion**: Only deletes previous alert if same direction (UP/UP or DOWN/DOWN)
- **Trader Info**: Captures trader details at moment of price change

## Message Examples

### Regular Update (Spanish)
```
╔═══ 📊 Actualización de Precios P2P Binance ═══╗
║ VES/USDT  •  ⏰ 11 Ene 2026, 07:35:34 PM
╚══════════════════════════════════════╝

┌─ 🏛️ Tasa Oficial BCV ─┐
│ 330.38 VES
└────────────────────┘

┏━━ 💵 Mejor COMPRA ━━┓
┃ 522.50 VES  🟢 ↗️ 58.2% vs BCV
┃
┃ 👤 Trader_Name
┃ 📦 3457 órdenes  •  💰 186.82 USDT
┃ 💳 Banesco, Pago Movil
┗══════════════════════════════════════┛

┏━━ 💰 Mejor VENTA ━━┓
┃ 504.30 VES  🟢 ↗️ 52.6% vs BCV
┃
┃ 👤 Another_Trader
┃ 📦 1990 órdenes  •  💰 1598.43 USDT
┃ 💳 Pago Movil, Provincial
┗══════════════════════════════════════┛

╔═ 📈 Cambios de Precio ═╗
║
║ 15m
║  💵 🔴 ↘ -0.10%
║  💰 🔴 ↘ -0.06%
╚══════════════════════════════╝
```

### Sudden Change Alert
```
╔══════ ⚡ ¡ALERTA! ⚡ ══════╗
║ VES/USDT  •  ⏰ 11 Ene 2026, 07:42:15 PM
╚═════════════════════════════════════════════╝

┏━━━━ 💰 VENTA 🔴 ↘️ ━━━━┓
┃
┃ ❄️ Cambio: 12.01%
┃ 💱 578.50 → 509.00 VES
┃
┃ 👤 FlashTrader
┃ 📦 1234 órdenes
┃ 💰 45.00 USDT
┗══════════════════════════════════════┛
```

## Timezone

All timestamps are shown in Venezuela timezone (VET, UTC-4).

## Production Deployment

### Run in tmux (Recommended)
```bash
tmux new -s p2p_tracker
python price_tracker_prod.py
# Detach: Ctrl+B, then D
# Reattach: tmux attach -t p2p_tracker
```

## Logs

View real-time logs:
```bash
tail -f price_tracker.log
```

Check for errors:
```bash
grep ERROR price_tracker.log
```

## Files

- `price_tracker_prod.py` - Main application
- `config.json` - Your configuration
- `config.example.json` - Configuration template
- `requirements.txt` - Python dependencies
- `get_telegram_chat_id.py` - Helper to get Telegram chat ID
- `price_history_VES_USDT.json` - Historical price data (auto-generated)
- `price_tracker.log` - Application logs (auto-generated)

## Security

Protect your configuration:
```bash
chmod 600 config.json
```

Never commit `config.json` to git (already in `.gitignore`).

## Troubleshooting

### Telegram Not Working
1. Verify bot token and chat ID are correct
2. Ensure bot is added to your group (if using group chat)
3. Check bot has permission to send messages
4. If group was upgraded to supergroup, update chat ID (check logs for new ID)

### Rate Limiting
- Script automatically handles rate limits
- If issues persist, increase `check_interval` in config

### No Price Data
- Check internet connection
- Verify Binance P2P is accessible
- Review logs for API errors

## Support

- Check logs: `price_tracker.log`
- Review configuration: `config.json`
- Test Telegram bot separately using `get_telegram_chat_id.py`

## License

MIT - Use at your own risk. Not affiliated with Binance.

## Disclaimer

This software is for educational and informational purposes. Cryptocurrency trading involves risk. Always verify prices on official platforms before making decisions. Not financial advice.
