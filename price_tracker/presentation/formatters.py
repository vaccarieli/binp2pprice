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
        bcv_rate: Optional[float] = None,
        bcv_rates: Any = None,
    ) -> str:
        """
        Format a regular price update message for Telegram.

        Args:
            buy_price: Current best buy price, or None if no offers
            sell_price: Current best sell price, or None if no offers
            changes: Dictionary of price changes over time periods (15m, 30m, 1h)
            best_buy_offer: Full offer details for best buy price
            best_sell_offer: Full offer details for best sell price
            bcv_rate: Optional BCV official USD rate (legacy)
            bcv_rates: Optional BCVRates with USD/EUR/GBP

        Returns:
            Formatted HTML message string for Telegram
        """
        # Get translations
        lang = self.config.telegram.language
        t_price_update = get_translation(lang, "price_update")
        t_bcv_rate = get_translation(lang, "bcv_official_rate")
        t_best_buy = get_translation(lang, "best_buy")
        t_best_sell = get_translation(lang, "best_sell")
        t_vs_bcv = get_translation(lang, "vs_bcv")
        t_orders = get_translation(lang, "orders")
        t_spread = get_translation(lang, "spread")
        t_price_changes = get_translation(lang, "price_changes")
        t_no_offers = get_translation(lang, "no_offers")
        t_gbp_note = get_translation(lang, "gbp_derived_note")

        timestamp = format_timestamp(lang)
        fiat = self.config.filters.fiat

        # Resolve USD rate used for P2P premium % (USDT ≈ USD)
        usd_rate = None
        if bcv_rates is not None and getattr(bcv_rates, "usd", None):
            usd_rate = bcv_rates.usd
        elif bcv_rate:
            usd_rate = bcv_rate

        # Header with modern design
        msg = f"╔═══ 📊 <b>{t_price_update}</b> ═══╗\n"
        msg += f"║ <b>{fiat}/{self.config.filters.asset}</b>  •  ⏰ {timestamp}\n"
        msg += f"╚{'═' * 38}╝\n\n"

        # BCV official rates — always label the foreign currency explicitly
        bcv_block = self._format_bcv_rates_block(
            t_bcv_rate=t_bcv_rate,
            fiat=fiat,
            bcv_rates=bcv_rates,
            fallback_usd=usd_rate,
            gbp_note=t_gbp_note,
        )
        if bcv_block:
            msg += bcv_block

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
            msg += f"┃ <b>{buy_price:.2f}</b> {fiat}"

            # P2P premium vs official BCV USD (USDT ≈ USD)
            if usd_rate and usd_rate > 0:
                buy_diff = ((buy_price - usd_rate) / usd_rate) * 100
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
            msg += f"┃ <b>{sell_price:.2f}</b> {fiat}"

            if usd_rate and usd_rate > 0:
                sell_diff = ((sell_price - usd_rate) / usd_rate) * 100
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
            msg += f"│ <b>{spread:.2f}</b> {fiat}  •  <b>{spread_pct:.2f}%</b>\n"
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

    def _format_bcv_rates_block(
        self,
        t_bcv_rate: str,
        fiat: str,
        bcv_rates: Any,
        fallback_usd: Optional[float],
        gbp_note: str,
    ) -> str:
        """Build the multi-currency BCV rates section with explicit pairs."""
        usd = getattr(bcv_rates, "usd", None) if bcv_rates is not None else None
        eur = getattr(bcv_rates, "eur", None) if bcv_rates is not None else None
        gbp = getattr(bcv_rates, "gbp", None) if bcv_rates is not None else None
        gbp_derived = bool(getattr(bcv_rates, "gbp_derived", False)) if bcv_rates else False

        if usd is None:
            usd = fallback_usd

        lines = []
        if usd:
            lines.append(f"│ 💵 <b>1 USD</b> = <b>{usd:.2f}</b> {fiat}")
        if eur:
            lines.append(f"│ 💶 <b>1 EUR</b> = <b>{eur:.2f}</b> {fiat}")
        if gbp:
            suffix = " *" if gbp_derived else ""
            lines.append(f"│ 💷 <b>1 GBP</b> = <b>{gbp:.2f}</b> {fiat}{suffix}")

        if not lines:
            return ""

        msg = f"┌─ 🏛️ <b>{t_bcv_rate}</b> ─┐\n"
        msg += "\n".join(lines) + "\n"
        if gbp and gbp_derived:
            msg += f"│ <i>* {gbp_note}</i>\n"
        msg += f"└{'─' * 28}┘\n\n"
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
        t_alert_title = get_translation(self.config.telegram.language, "alert_title")
        t_change = get_translation(self.config.telegram.language, "change")
        t_buy = get_translation(self.config.telegram.language, "buy")
        t_sell = get_translation(self.config.telegram.language, "sell")
        t_orders = get_translation(self.config.telegram.language, "orders")

        if timestamp is None:
            timestamp = format_timestamp(self.config.telegram.language)

        # Modern alert header
        msg = f"╔══════ ⚡ <b>{t_alert_title}</b> ⚡ ══════╗\n"
        msg += f"║ <b>{self.config.filters.fiat}/{self.config.filters.asset}</b>  •  ⏰ {timestamp}\n"
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
        msg += f"┃ 💱 <b>{change_data['old_price']:.2f}</b> → <b>{change_data['new_price']:.2f}</b> {self.config.filters.fiat}\n"

        # Add trader info if available
        if change_data.get('trader_info') and change_data['trader_info'].get('trader'):
            trader_info = change_data['trader_info']
            msg += f"┃\n"
            msg += f"┃ 👤 <b>{trader_info['trader']}</b>\n"
            msg += f"┃ 📦 {trader_info['orders']} {t_orders}\n"
            msg += f"┃ 💰 {trader_info['available']:.2f} {self.config.filters.asset}\n"

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
        t_alert_title = get_translation(self.config.telegram.language, "alert_title")
        t_change = get_translation(self.config.telegram.language, "change")
        t_buy = get_translation(self.config.telegram.language, "buy")
        t_sell = get_translation(self.config.telegram.language, "sell")
        t_orders = get_translation(self.config.telegram.language, "orders")

        if timestamp is None:
            timestamp = format_timestamp(self.config.telegram.language)

        # Modern alert header
        msg = f"╔══════ ⚡ <b>{t_alert_title}</b> ⚡ ══════╗\n"
        msg += f"║ <b>{self.config.filters.fiat}/{self.config.filters.asset}</b>  •  ⏰ {timestamp}\n"
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
            msg += f"┃ 💱 <b>{change_data['old_price']:.2f}</b> → <b>{change_data['new_price']:.2f}</b> {self.config.filters.fiat}\n"

            # Add trader info if available
            if change_data.get('trader_info') and change_data['trader_info'].get('trader'):
                trader_info = change_data['trader_info']
                msg += f"┃\n"
                msg += f"┃ 👤 <b>{trader_info['trader']}</b>\n"
                msg += f"┃ 📦 {trader_info['orders']} {t_orders}\n"
                msg += f"┃ 💰 {trader_info['available']:.2f} {self.config.filters.asset}\n"

            msg += f"┗{'━' * 38}┛\n"

        return msg
