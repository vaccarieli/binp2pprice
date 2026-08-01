"""
Telegram message formatting for price updates and alerts.

Card-style layout (readable on mobile). BCV currencies are rendered
dynamically from BCVRates — any new currency from the API appears in:
  - official rates block
  - COMPRA / VENTA premium lines
  - sudden-change alerts
without hardcoding each code in the display layer.
"""

from __future__ import annotations

from html import escape
from typing import Any, Dict, List, Optional, Sequence, Tuple

from price_tracker.api.bcv import BCVRates, currency_emoji
from price_tracker.presentation.translations import get_translation, format_timestamp


class TelegramFormatter:
    """Formats Telegram messages for price updates and alerts."""

    def __init__(self, config: Any):
        self.config = config

    # ------------------------------------------------------------------
    # Public formatters
    # ------------------------------------------------------------------

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
        """Format the live status dashboard message."""
        lang = self.config.telegram.language
        fiat = self.config.filters.fiat
        asset = self.config.filters.asset
        timestamp = format_timestamp(lang)

        t_price_update = get_translation(lang, "price_update")
        t_bcv = get_translation(lang, "bcv_official_rate")
        t_buy = get_translation(lang, "best_buy")
        t_sell = get_translation(lang, "best_sell")
        t_orders = get_translation(lang, "orders")
        t_spread = get_translation(lang, "spread")
        t_changes = get_translation(lang, "price_changes")
        t_no_offers = get_translation(lang, "no_offers")

        rate_pairs = self._rate_pairs(bcv_rates, bcv_rate)

        # Header card
        msg = (
            f"╔══ 📊 <b>{escape(t_price_update)}</b> ══╗\n"
            f"║ <b>{escape(fiat)}/{escape(asset)}</b>\n"
            f"║ ⏰ {escape(timestamp)}\n"
            f"╚{'═' * 28}╝\n\n"
        )

        # BCV — one currency per line, driven by rate_pairs
        msg += self._format_bcv_block(fiat, rate_pairs, t_bcv)

        # COMPRA / VENTA cards with premium vs every BCV currency
        msg += self._format_offer_card(
            side="buy",
            title=t_buy,
            price=buy_price,
            offer=best_buy_offer,
            fiat=fiat,
            asset=asset,
            rate_pairs=rate_pairs,
            t_orders=t_orders,
            t_no_offers=t_no_offers,
        )
        msg += self._format_offer_card(
            side="sell",
            title=t_sell,
            price=sell_price,
            offer=best_sell_offer,
            fiat=fiat,
            asset=asset,
            rate_pairs=rate_pairs,
            t_orders=t_orders,
            t_no_offers=t_no_offers,
        )

        # Spread card
        if buy_price is not None and sell_price is not None and sell_price > 0:
            spread = buy_price - sell_price
            spread_pct = (buy_price / sell_price - 1.0) * 100.0
            msg += (
                f"╭─ 📏 <b>{escape(t_spread)}</b> ─╮\n"
                f"│ <code>{spread:.2f}</code> {escape(fiat)}\n"
                f"│ <b>{spread_pct:.2f}%</b>\n"
                f"╰{'─' * 22}╯\n\n"
            )

        # Changes — each period is its own short block
        if changes:
            msg += f"╔═ 📈 <b>{escape(t_changes)}</b> ═╗\n"
            for period in ("15m", "30m", "1h"):
                if period not in changes:
                    continue
                data = changes[period]
                msg += f"║\n"
                msg += f"║ <b>{period}</b>\n"
                msg += f"║  💵 {self._pct(data['buy_change'])}\n"
                msg += f"║  💰 {self._pct(data['sell_change'])}\n"
            msg += f"╚{'═' * 24}╝"

        return msg

    def format_alert(
        self,
        alert_type: str,
        change_data: dict,
        timestamp: Optional[str] = None,
        bcv_rates: Any = None,
    ) -> str:
        """Format a single sudden-change alert."""
        return self.format_multi_alert(
            [change_data], alert_type, timestamp, bcv_rates=bcv_rates
        )

    def format_multi_alert(
        self,
        changes: list[dict],
        alert_type: str,
        timestamp: Optional[str] = None,
        bcv_rates: Any = None,
    ) -> str:
        """Format COMPRA or VENTA alert(s) with card layout."""
        lang = self.config.telegram.language
        fiat = self.config.filters.fiat
        asset = self.config.filters.asset
        t_buy = get_translation(lang, "buy")
        t_sell = get_translation(lang, "sell")
        t_orders = get_translation(lang, "orders")
        t_alert = get_translation(lang, "alert_title")

        if timestamp is None:
            timestamp = format_timestamp(lang)

        side_label = t_buy if alert_type == "BUY" else t_sell
        side_icon = "💵" if alert_type == "BUY" else "💰"
        rate_pairs = self._rate_pairs(bcv_rates, None)

        msg = (
            f"╔══ ⚡ <b>{escape(t_alert)}</b> ⚡ ══╗\n"
            f"║ <b>{escape(fiat)}/{escape(asset)}</b>\n"
            f"║ ⏰ {escape(timestamp)}\n"
            f"╚{'═' * 30}╝\n\n"
        )

        for change_data in changes:
            pct = float(change_data.get("change", 0.0))
            old_price = float(change_data.get("old_price", 0.0))
            new_price = float(change_data.get("new_price", 0.0))
            delta = new_price - old_price
            delta_sign = "+" if delta >= 0 else ""
            heat = "🔥" if pct > 0 else "❄️"
            local_trend = "🟢 ↗️" if pct > 0 else "🔴 ↘️"
            local_sign = "+" if pct > 0 else ""

            msg += (
                f"┏━ {side_icon} <b>{escape(side_label)}</b> {local_trend} ━┓\n"
                f"┃\n"
                f"┃ {heat} <b>{local_sign}{pct:.2f}%</b>\n"
                f"┃ 💱 <code>{old_price:.2f}</code> → <code>{new_price:.2f}</code>\n"
                f"┃    {escape(fiat)}\n"
                f"┃ Δ <code>{delta_sign}{delta:.2f}</code> {escape(fiat)}\n"
            )

            # Premium vs every official BCV currency (auto)
            for code, ref in rate_pairs:
                msg += f"┃ {self._premium_line(new_price, ref, code)}\n"

            trader_info = change_data.get("trader_info") or {}
            if trader_info.get("trader"):
                trader = escape(str(trader_info["trader"]))
                orders = trader_info.get("orders", 0)
                available = float(trader_info.get("available", 0) or 0)
                methods = trader_info.get("payment_methods") or []
                methods_txt = ", ".join(
                    escape(str(m)) for m in methods[:3] if m
                )

                msg += (
                    f"┃\n"
                    f"┃ 👤 <b>{trader}</b>\n"
                    f"┃ 📦 {orders} {escape(t_orders)}\n"
                    f"┃ 💰 <code>{available:.2f}</code> {escape(asset)}\n"
                )
                if methods_txt:
                    msg += f"┃ 💳 {methods_txt}\n"

            msg += f"┗{'━' * 28}┛\n"

        return msg

    # ------------------------------------------------------------------
    # Helpers — currency-agnostic
    # ------------------------------------------------------------------

    @staticmethod
    def _rate_pairs(
        bcv_rates: Any,
        fallback_primary: Optional[float],
    ) -> List[Tuple[str, float]]:
        """Normalize any BCVRates-like object into ordered (code, rate) pairs."""
        pairs: List[Tuple[str, float]] = []

        if isinstance(bcv_rates, BCVRates):
            pairs = list(bcv_rates.items())
        elif bcv_rates is not None:
            # Duck-typing: object with items() or rates dict
            if hasattr(bcv_rates, "items") and callable(bcv_rates.items):
                try:
                    raw = list(bcv_rates.items())
                    if raw and isinstance(raw[0], tuple) and len(raw[0]) == 2:
                        pairs = [
                            (str(c).upper(), float(v))
                            for c, v in raw
                            if v is not None and float(v) > 0
                        ]
                except Exception:
                    pairs = []
            if not pairs and hasattr(bcv_rates, "rates"):
                rates_dict = getattr(bcv_rates, "rates") or {}
                pairs = [
                    (str(c).upper(), float(v))
                    for c, v in rates_dict.items()
                    if v is not None and float(v) > 0
                ]

        if not pairs and fallback_primary and fallback_primary > 0:
            pairs = [("USD", float(fallback_primary))]

        # De-dupe while preserving order
        seen = set()
        ordered: List[Tuple[str, float]] = []
        for code, rate in pairs:
            code = code.upper()
            if code in seen or rate <= 0:
                continue
            seen.add(code)
            ordered.append((code, rate))
        return ordered

    def _format_bcv_block(
        self,
        fiat: str,
        rate_pairs: Sequence[Tuple[str, float]],
        t_bcv: str,
    ) -> str:
        if not rate_pairs:
            return ""

        msg = f"┌─ 🏛️ <b>{escape(t_bcv)}</b> ─┐\n"
        for code, rate in rate_pairs:
            emoji = currency_emoji(code)
            msg += (
                f"│ {emoji} 1 {escape(code)} = "
                f"<code>{rate:.2f}</code> {escape(fiat)}\n"
            )
        msg += f"└{'─' * 24}┘\n\n"
        return msg

    def _format_offer_card(
        self,
        side: str,
        title: str,
        price: Optional[float],
        offer: Optional[dict],
        fiat: str,
        asset: str,
        rate_pairs: Sequence[Tuple[str, float]],
        t_orders: str,
        t_no_offers: str,
    ) -> str:
        icon = "💵" if side == "buy" else "💰"
        msg = f"┏━━ {icon} <b>{escape(title)}</b> ━━┓\n"

        if price is None or not offer:
            msg += f"┃ {escape(t_no_offers)}\n"
            msg += f"┗{'━' * 28}┛\n\n"
            return msg

        adv = offer.get("adv", {}) or {}
        advertiser = offer.get("advertiser", {}) or {}
        trader = escape(str(advertiser.get("nickName", "Unknown")))
        orders = advertiser.get("monthOrderCount", 0)
        available = float(adv.get("surplusAmount", 0) or 0)
        methods = ", ".join(
            escape(str(m.get("tradeMethodName", "")))
            for m in (adv.get("tradeMethods") or [])[:2]
            if m and m.get("tradeMethodName")
        )

        # Price on its own line
        msg += f"┃ <code>{price:.2f}</code> {escape(fiat)}\n"

        # Premium vs every official BCV currency (auto from rate_pairs)
        for code, ref in rate_pairs:
            msg += f"┃ {self._premium_line(price, ref, code)}\n"

        msg += (
            f"┃\n"
            f"┃ 👤 {trader}\n"
            f"┃ 📦 {orders} {escape(t_orders)}\n"
            f"┃ 💰 <code>{available:.2f}</code> {escape(asset)}\n"
        )
        if methods:
            msg += f"┃ 💳 {methods}\n"
        msg += f"┗{'━' * 28}┛\n\n"
        return msg

    @staticmethod
    def _premium_line(price: float, ref_rate: float, currency: str) -> str:
        """Format one premium line: 🟢 ↗️ 14.8% vs USD"""
        if not ref_rate or ref_rate <= 0:
            return f"⚪ n/a vs {escape(currency)}"
        diff = ((price - ref_rate) / ref_rate) * 100.0
        emoji = "🟢" if diff > 0 else "🔴"
        arrow = "↗️" if diff > 0 else "↘️"
        return (
            f"{emoji} {arrow} <b>{abs(diff):.1f}%</b> "
            f"vs {escape(currency)}"
        )

    @staticmethod
    def _pct(value: float) -> str:
        if value > 0:
            return f"🟢 ↗ <b>+{value:.2f}%</b>"
        if value < 0:
            return f"🔴 ↘ <b>{value:.2f}%</b>"
        return f"<b>{value:.2f}%</b>"
