"""
Telegram message formatting for price updates and alerts.

This module handles all Telegram message formatting including:
- Regular price updates with BCV rates
- Sudden price change alerts
- Modern Unicode box-drawing characters for visual appeal
"""

from typing import Optional, Dict, Any
from price_tracker.presentation.translations import get_translation, format_timestamp


class TelegramFormatter:
    """Formats Telegram messages for price updates and alerts."""

    def __init__(self, config: Any):
        """
        Initialize the Telegram formatter.

        Args:
            config: Configuration object with fiat, asset, and language settings
        """
        self.config = config

    def format_regular_update(
        self,
        buy_price: Optional[float],
        sell_price: Optional[float],
        changes: Dict[str, dict],
        best_buy_offer: Optional[dict],
        best_sell_offer: Optional[dict],
        bcv_rate: Optional[float] = None
    ) -> str:
        """
        Format a regular price update message for Telegram.

        Args:
            buy_price: Current best buy price, or None if no offers
            sell_price: Current best sell price, or None if no offers
            changes: Dictionary of price changes over time periods (15m, 30m, 1h)
            best_buy_offer: Full offer details for best buy price
            best_sell_offer: Full offer details for best sell price
            bcv_rate: Optional BCV official exchange rate

        Returns:
            Formatted HTML message string for Telegram
        """
        # Get translations
        t_price_update = get_translation(self.config, "price_update")
        t_bcv_rate = get_translation(self.config, "bcv_official_rate")
        t_best_buy = get_translation(self.config, "best_buy")
        t_best_sell = get_translation(self.config, "best_sell")
        t_vs_bcv = get_translation(self.config, "vs_bcv")
        t_orders = get_translation(self.config, "orders")
        t_spread = get_translation(self.config, "spread")
        t_price_changes = get_translation(self.config, "price_changes")
        t_no_offers = get_translation(self.config, "no_offers")

        timestamp = format_timestamp(self.config)

        # Header with modern design
        msg = f"╔═══ 📊 <b>{t_price_update}</b> ═══╗\n"
        msg += f"║ <b>{self.config.fiat}/{self.config.asset}</b>  •  ⏰ {timestamp}\n"
        msg += f"╚{'═' * 38}╝\n\n"

        # BCV Official Rate with prominent display
        if bcv_rate:
            msg += f"┌─ 🏛️ <b>{t_bcv_rate}</b> ─┐\n"
            msg += f"│ <b>{bcv_rate:.2f} {self.config.fiat}</b>\n"
            msg += f"└{'─' * 20}┘\n\n"

        # BUY offer details with modern card layout
        if buy_price is not None and best_buy_offer:
            buy_adv = best_buy_offer.get("adv", {})
            buy_advertiser = best_buy_offer.get("advertiser", {})
            buy_trader = buy_advertiser.get("nickName", "Unknown")
            buy_orders = buy_advertiser.get("monthOrderCount", 0)
            buy_available = float(buy_adv.get("surplusAmount", 0))
            buy_methods = ", ".join([
                m.get("tradeMethodName", "")
                for m in buy_adv.get("tradeMethods", [])[:2]
                if m.get("tradeMethodName")
            ])

            msg += f"┏━━ 💵 <b>{t_best_buy}</b> ━━┓\n"
            msg += f"┃ <b>{buy_price:.2f}</b> {self.config.fiat}"

            # Add BCV difference
            if bcv_rate and bcv_rate > 0:
                buy_diff = ((buy_price - bcv_rate) / bcv_rate) * 100
                diff_emoji = "🟢" if buy_diff > 0 else "🔴"
                arrow = "↗️" if buy_diff > 0 else "↘️"
                msg += f"  {diff_emoji} <b>{arrow} {abs(buy_diff):.1f}%</b> {t_vs_bcv}"

            msg += f"\n┃\n"
            msg += f"┃ 👤 {buy_trader}\n"
            msg += f"┃ 📦 {buy_orders} {t_orders}  •  💰 {buy_available:.2f} USDT\n"
            msg += f"┃ 💳 {buy_methods}\n"
            msg += f"┗{'━' * 38}┛\n\n"
        else:
            msg += f"┏━━ 💵 <b>{t_best_buy}</b> ━━┓\n"
            msg += f"┃ {t_no_offers}\n"
            msg += f"┗{'━' * 38}┛\n\n"

        # SELL offer details with modern card layout
        if sell_price is not None and best_sell_offer:
            sell_adv = best_sell_offer.get("adv", {})
            sell_advertiser = best_sell_offer.get("advertiser", {})
            sell_trader = sell_advertiser.get("nickName", "Unknown")
            sell_orders = sell_advertiser.get("monthOrderCount", 0)
            sell_available = float(sell_adv.get("surplusAmount", 0))
            sell_methods = ", ".join([
                m.get("tradeMethodName", "")
                for m in sell_adv.get("tradeMethods", [])[:2]
                if m.get("tradeMethodName")
            ])

            msg += f"┏━━ 💰 <b>{t_best_sell}</b> ━━┓\n"
            msg += f"┃ <b>{sell_price:.2f}</b> {self.config.fiat}"

            # Add BCV difference
            if bcv_rate and bcv_rate > 0:
                sell_diff = ((sell_price - bcv_rate) / bcv_rate) * 100
                diff_emoji = "🟢" if sell_diff > 0 else "🔴"
                arrow = "↗️" if sell_diff > 0 else "↘️"
                msg += f"  {diff_emoji} <b>{arrow} {abs(sell_diff):.1f}%</b> {t_vs_bcv}"

            msg += f"\n┃\n"
            msg += f"┃ 👤 {sell_trader}\n"
            msg += f"┃ 📦 {sell_orders} {t_orders}  •  💰 {sell_available:.2f} USDT\n"
            msg += f"┃ 💳 {sell_methods}\n"
            msg += f"┗{'━' * 38}┛\n\n"
        else:
            msg += f"┏━━ 💰 <b>{t_best_sell}</b> ━━┓\n"
            msg += f"┃ {t_no_offers}\n"
            msg += f"┗{'━' * 38}┛\n\n"

        # Spread with modern formatting
        if buy_price is not None and sell_price is not None:
            spread = buy_price - sell_price
            spread_pct = ((buy_price/sell_price - 1) * 100)
            msg += f"╭─ 📊 <b>{t_spread}</b> ─╮\n"
            msg += f"│ <b>{spread:.2f}</b> {self.config.fiat}  •  <b>{spread_pct:.2f}%</b>\n"
            msg += f"╰{'─' * 25}╯\n\n"

        # Price changes with enhanced visuals
        if changes:
            msg += f"╔═ 📈 <b>{t_price_changes}</b> ═╗\n"
            for period in ["15m", "30m", "1h"]:
                if period in changes:
                    data = changes[period]

                    # Visual indicators for changes
                    if data['buy_change'] > 0:
                        buy_indicator = "🟢 ↗"
                        buy_sign = "+"
                    else:
                        buy_indicator = "🔴 ↘"
                        buy_sign = ""

                    if data['sell_change'] > 0:
                        sell_indicator = "🟢 ↗"
                        sell_sign = "+"
                    else:
                        sell_indicator = "🔴 ↘"
                        sell_sign = ""

                    msg += f"║\n"
                    msg += f"║ <b>{period}</b>\n"
                    msg += f"║  💵 {buy_indicator} <b>{buy_sign}{data['buy_change']:.2f}%</b>\n"
                    msg += f"║  💰 {sell_indicator} <b>{sell_sign}{data['sell_change']:.2f}%</b>\n"

            msg += f"╚{'═' * 30}╝"

        return msg

    def format_alert(
        self,
        alert_type: str,
        change_data: dict,
        timestamp: Optional[str] = None
    ) -> str:
        """
        Format a sudden price change alert message for Telegram.

        Args:
            alert_type: Either "BUY" or "SELL"
            change_data: Dictionary containing:
                - change: Percentage change (float)
                - old_price: Previous price (float)
                - new_price: Current price (float)
                - trader_info: Optional dict with trader, orders, available, payment_methods
            timestamp: Optional pre-formatted timestamp string (defaults to current time)

        Returns:
            Formatted HTML alert message string for Telegram
        """
        # Get translations
        t_alert_title = get_translation(self.config, "alert_title")
        t_change = get_translation(self.config, "change")
        t_buy = get_translation(self.config, "buy")
        t_sell = get_translation(self.config, "sell")
        t_orders = get_translation(self.config, "orders")

        if timestamp is None:
            timestamp = format_timestamp(self.config)

        # Modern alert header
        msg = f"╔══════ ⚡ <b>{t_alert_title}</b> ⚡ ══════╗\n"
        msg += f"║ <b>{self.config.fiat}/{self.config.asset}</b>  •  ⏰ {timestamp}\n"
        msg += f"╚{'═' * 45}╝\n\n"

        # Determine visual indicators
        if change_data['change'] > 0:
            trend_icon = "🟢 ↗️"
            change_color = "🔥"
        else:
            trend_icon = "🔴 ↘️"
            change_color = "❄️"

        # Use appropriate icon for BUY vs SELL
        if alert_type == "BUY":
            type_icon = "💵"
            type_label = t_buy
        else:
            type_icon = "💰"
            type_label = t_sell

        msg += f"┏━━━━ {type_icon} <b>{type_label}</b> {trend_icon} ━━━━┓\n"
        msg += f"┃\n"
        msg += f"┃ {change_color} <b>{t_change}:</b> <b>{abs(change_data['change']):.2f}%</b>\n"
        msg += f"┃ 💱 <b>{change_data['old_price']:.2f}</b> → <b>{change_data['new_price']:.2f}</b> {self.config.fiat}\n"

        # Add trader info if available
        if change_data.get('trader_info') and change_data['trader_info'].get('trader'):
            trader_info = change_data['trader_info']
            msg += f"┃\n"
            msg += f"┃ 👤 <b>{trader_info['trader']}</b>\n"
            msg += f"┃ 📦 {trader_info['orders']} {t_orders}\n"
            msg += f"┃ 💰 {trader_info['available']:.2f} {self.config.asset}\n"

        msg += f"┗{'━' * 38}┛\n"

        return msg

    def format_multi_alert(
        self,
        changes: list[dict],
        alert_type: str,
        timestamp: Optional[str] = None
    ) -> str:
        """
        Format multiple price change alerts into a single message.

        Args:
            changes: List of change_data dictionaries
            alert_type: Either "BUY" or "SELL"
            timestamp: Optional pre-formatted timestamp string

        Returns:
            Formatted HTML alert message string for Telegram
        """
        # Get translations
        t_alert_title = get_translation(self.config, "alert_title")
        t_change = get_translation(self.config, "change")
        t_buy = get_translation(self.config, "buy")
        t_sell = get_translation(self.config, "sell")
        t_orders = get_translation(self.config, "orders")

        if timestamp is None:
            timestamp = format_timestamp(self.config)

        # Modern alert header
        msg = f"╔══════ ⚡ <b>{t_alert_title}</b> ⚡ ══════╗\n"
        msg += f"║ <b>{self.config.fiat}/{self.config.asset}</b>  •  ⏰ {timestamp}\n"
        msg += f"╚{'═' * 45}╝\n\n"

        for change_data in changes:
            # Determine visual indicators
            if change_data['change'] > 0:
                trend_icon = "🟢 ↗️"
                change_color = "🔥"
            else:
                trend_icon = "🔴 ↘️"
                change_color = "❄️"

            # Use appropriate icon for BUY vs SELL
            if alert_type == "BUY":
                type_icon = "💵"
                type_label = t_buy
            else:
                type_icon = "💰"
                type_label = t_sell

            msg += f"┏━━━━ {type_icon} <b>{type_label}</b> {trend_icon} ━━━━┓\n"
            msg += f"┃\n"
            msg += f"┃ {change_color} <b>{t_change}:</b> <b>{abs(change_data['change']):.2f}%</b>\n"
            msg += f"┃ 💱 <b>{change_data['old_price']:.2f}</b> → <b>{change_data['new_price']:.2f}</b> {self.config.fiat}\n"

            # Add trader info if available
            if change_data.get('trader_info') and change_data['trader_info'].get('trader'):
                trader_info = change_data['trader_info']
                msg += f"┃\n"
                msg += f"┃ 👤 <b>{trader_info['trader']}</b>\n"
                msg += f"┃ 📦 {trader_info['orders']} {t_orders}\n"
                msg += f"┃ 💰 {trader_info['available']:.2f} {self.config.asset}\n"

            msg += f"┗{'━' * 38}┛\n"

        return msg
