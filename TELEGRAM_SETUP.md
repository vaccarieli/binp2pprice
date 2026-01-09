# Telegram Alerts Setup Guide

This guide will help you set up Telegram alerts for your Binance P2P Price Tracker.

## Features

✅ **Regular Status Updates** (every 30 seconds)
- **BCV Official Rate** (Banco Central de Venezuela) at the top
- **Visual difference** showing P2P premium vs BCV rate
- Current BUY and SELL prices
- Trader information
- Available liquidity
- Price changes over 15m, 30m, 1h
- Spread information
- **Messages are edited in place** to keep your chat clean

✅ **Smart Sudden Change Alerts**
- Immediate alerts when price moves ±5% from baseline (customizable)
- **Baseline resets after each alert** to prevent spam
- Extra warning emoji (⚡) for changes >7.5%
- Separate threshold from regular alerts
- BUY and SELL tracked independently

## Quick Setup (5 minutes)

### Step 1: Create Your Telegram Bot

1. Open Telegram and search for [@BotFather](https://t.me/BotFather)
2. Send `/newbot` to BotFather
3. Choose a name for your bot (e.g., "P2P Price Alerts")
4. Choose a username (must end in 'bot', e.g., "my_p2p_alerts_bot")
5. **Save the bot token** - it looks like: `7413119427:AAECImETvOcwQEUTep776FXCdvYYIqukZ_s`

### Step 2: Get Your Chat ID

**Method 1: Using Helper Script (Recommended)**
```bash
# Run the helper script
python get_telegram_chat_id.py

# Send any message to your bot (open your bot in Telegram and click START)
# Then run the script again - it will show your chat ID
```

**Method 2: Manual**
```bash
# 1. Send a message to your bot in Telegram
# 2. Visit this URL in your browser (replace YOUR_BOT_TOKEN):
#    https://api.telegram.org/botYOUR_BOT_TOKEN/getUpdates
# 3. Look for "chat":{"id":123456789}
# 4. Copy the number (your chat ID)
```

### Step 3: Update config.json

Edit your `config.json` file:

```json
{
  "telegram_enabled": true,
  "telegram_bot_token": "7413119427:AAECImETvOcwQEUTep776FXCdvYYIqukZ_s",
  "telegram_chat_id": "123456789",
  "telegram_regular_updates": true,
  "telegram_sudden_change_threshold": 5.0
}
```

### Step 4: Test the Integration

```bash
# Run the tracker
source venv/bin/activate
python price_tracker_prod.py

# You should receive a Telegram message within 30 seconds!
```

## How Smart Alerts Work

The bot uses a **baseline reset system** to prevent alert spam:

### Example Flow:
```
10:00:00 - Price: 690 VES (baseline set)
10:05:00 - Price: 725 VES (+5.07% change)
         → 🚨 ALERT SENT
         → Baseline reset to 725 VES

10:05:30 - Price: 730 VES (+0.69% from 725)
         → No alert (below 5% threshold)

10:10:00 - Price: 762 VES (+5.10% from 725)
         → 🚨 ALERT SENT
         → Baseline reset to 762 VES
```

### Key Points:
- ✅ Alerts only trigger when crossing threshold from baseline
- ✅ Baseline resets immediately after alert
- ✅ Next alert requires another ±5% move from NEW baseline
- ✅ BUY and SELL prices track independently
- ✅ No cooldown period - event-driven only
- ✅ No spam even during volatile markets

## Configuration Options

### Basic Settings

| Option | Type | Default | Description |
|--------|------|---------|-------------|
| `telegram_enabled` | boolean | `false` | Enable/disable Telegram alerts |
| `telegram_bot_token` | string | `""` | Your bot token from BotFather |
| `telegram_chat_id` | string | `""` | Your chat ID |
| `telegram_regular_updates` | boolean | `true` | Send status updates every check interval |
| `telegram_sudden_change_threshold` | float | `5.0` | Percentage change to trigger sudden alerts |

### Example Configurations

**Only Sudden Change Alerts (No Regular Updates)**
```json
{
  "telegram_enabled": true,
  "telegram_bot_token": "YOUR_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "telegram_regular_updates": false,
  "telegram_sudden_change_threshold": 5.0
}
```

**High-Frequency Alerts (Very Sensitive)**
```json
{
  "telegram_enabled": true,
  "telegram_bot_token": "YOUR_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "telegram_regular_updates": true,
  "telegram_sudden_change_threshold": 2.0
}
```

**Conservative Alerts (Only Major Changes)**
```json
{
  "telegram_enabled": true,
  "telegram_bot_token": "YOUR_TOKEN",
  "telegram_chat_id": "YOUR_CHAT_ID",
  "telegram_regular_updates": false,
  "telegram_sudden_change_threshold": 10.0
}
```

## Message Examples

### Regular Status Update (Edited Every 30s)
```
📊 Binance P2P Price Update
VES/USDT
⏰ 2026-01-09 08:32:36
──────────────────────────────

🏛️ BCV Official Rate: 325.39 VES

💵 Best BUY: 662.40 VES 📈 +103.5% vs BCV
   Trader: Start_777 (7796 orders)
   Available: 257.55 USDT
   Payment: Pago Movil, Banesco

💰 Best SELL: 638.12 VES 📈 +96.1% vs BCV
   Trader: Nohito (1820 orders)
   Available: 2124.12 USDT
   Payment: Bank Transfer, Banesco

📈 Spread: 24.28 VES (3.81%)

Price Changes:

15m:
  📉 BUY: -0.96%
  📈 SELL: +0.63%

30m:
  📉 BUY: -3.85%
  📉 SELL: -3.46%

1h:
  📉 BUY: -6.55%
  📉 SELL: -7.63%
```

### Sudden Change Alert (New Message)
```
⚡ SUDDEN PRICE CHANGE ALERT!
VES/USDT
⏰ 2026-01-09 08:35:12
──────────────────────────────

⚡ BUY 📉 DOWN
   Change: 6.55%
   708.80 → 662.40 VES

⚠️ SELL 📉 DOWN
   Change: 7.63%
   690.85 → 638.12 VES
```

**Note:** After this alert, the baseline resets to 662.40 (BUY) and 638.12 (SELL). The next alert will only trigger if prices move another ±5% from these new baselines.

## Troubleshooting

### Not Receiving Messages

1. **Check bot token**:
   ```bash
   curl https://api.telegram.org/bot<YOUR_TOKEN>/getMe
   ```
   Should return bot information if token is valid

2. **Check chat ID**:
   - Make sure you sent at least one message to your bot
   - Run `python get_telegram_chat_id.py` again
   - Verify the chat ID is a number (not a string with quotes)

3. **Check logs**:
   ```bash
   grep -i telegram price_tracker.log
   ```
   Look for error messages

4. **Test sending a message manually**:
   ```bash
   curl -X POST "https://api.telegram.org/bot<YOUR_TOKEN>/sendMessage" \
        -d "chat_id=<YOUR_CHAT_ID>" \
        -d "text=Test message"
   ```

### Too Many Messages

If you're getting too many messages, adjust these settings:

**Option 1: Disable regular updates, keep only sudden changes**
```json
{
  "telegram_regular_updates": false,
  "telegram_sudden_change_threshold": 5.0
}
```

**Option 2: Increase check interval**
```json
{
  "check_interval": 60,
  "telegram_regular_updates": true
}
```

### Messages Not Formatted

Make sure HTML formatting is enabled in the bot settings. The script uses HTML parse mode for rich formatting.

## Privacy & Security

- Your bot token is sensitive - keep it secret
- Don't share your chat ID publicly
- Set proper file permissions:
  ```bash
  chmod 600 config.json
  ```
- Consider using environment variables for tokens
- Add config.json to .gitignore (already included)

## Rate Limits

Telegram Bot API has these limits:
- 30 messages per second to different chats
- 1 message per second to the same chat

With default settings (30s interval), you're well within limits:
- Regular updates: 2 messages per minute
- Sudden change alerts: Only when threshold is met

## Advanced Usage

### Multiple Receivers

To send alerts to multiple people/groups:
1. Add the bot to a group chat
2. Get the group chat ID (negative number)
3. Use the group chat ID in config

### Custom Emojis

You can customize the emojis in the code:
- Regular update: 📊 (line 247)
- Sudden change: ⚡ (line 804)
- Price up: 📈 (line 304)
- Price down: 📉 (line 304)
- Buy: 💵 (line 265)
- Sell: 💰 (line 285)

### Filtering Messages

You can add message filtering in Telegram:
1. Create a dedicated channel for alerts
2. Use Telegram's search/filter features
3. Pin important sudden change alerts

## FAQ

**Q: Can I use the same bot for multiple trackers?**
A: Yes, but you'll need different chat IDs or the messages will mix together.

**Q: Will I be notified at night?**
A: Yes, unless you mute the chat in Telegram or stop the tracker.

**Q: How much does this cost?**
A: Telegram bots are completely free!

**Q: Can I use this with a channel instead of a personal chat?**
A: Yes, add the bot as an admin to your channel and use the channel ID.

**Q: What if my bot stops responding?**
A: Check if the bot token is still valid. You may need to regenerate it via BotFather.

## Support

If you encounter issues:
1. Check the logs: `tail -f price_tracker.log`
2. Test with the helper script: `python get_telegram_chat_id.py`
3. Verify your configuration matches the examples above
4. Make sure the tracker is running: `ps aux | grep price_tracker`

## Updates

This feature was added on 2026-01-09. Future updates may include:
- Custom message templates
- Interactive buttons
- Group commands
- Multiple alert levels
- Schedule-based notifications
