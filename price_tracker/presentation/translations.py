"""Translation and localization support.

This module provides translations for Telegram messages and
handles timezone-aware timestamp formatting for Venezuela.
"""

from datetime import datetime
from zoneinfo import ZoneInfo


# Translation dictionary for Telegram messages
TRANSLATIONS = {
    "en": {
        "price_update": "Binance P2P Prices",
        "bcv_official_rate": "BCV Official",
        "best_buy": "Best BUY",
        "best_sell": "Best SELL",
        "buy": "BUY",
        "sell": "SELL",
        "vs_bcv": "vs BCV USD",
        "trader": "Trader",
        "available": "Available",
        "payment": "Payment",
        "orders": "orders",
        "spread": "Spread",
        "price_changes": "Price Changes",
        "no_offers": "No matching offers",
        "alert_title": "PRICE ALERT",
        "change": "Change",
        "up": "UP",
        "down": "DOWN",
    },
    "es": {
        "price_update": "Precios P2P Binance",
        "bcv_official_rate": "Tasa Oficial BCV",
        "best_buy": "Mejor COMPRA",
        "best_sell": "Mejor VENTA",
        "buy": "COMPRA",
        "sell": "VENTA",
        "vs_bcv": "vs BCV USD",
        "trader": "Comerciante",
        "available": "Disponible",
        "payment": "Pago",
        "orders": "órdenes",
        "spread": "Diferencial",
        "price_changes": "Cambios de Precio",
        "no_offers": "Sin ofertas",
        "alert_title": "ALERTA DE PRECIO",
        "change": "Cambio",
        "up": "SUBIÓ",
        "down": "BAJÓ",
    },
}


def get_translation(language: str, key: str) -> str:
    """Get translated string based on language."""
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, key)


def get_venezuela_time() -> datetime:
    """Get current time in Venezuela timezone (VET, UTC-4)."""
    return datetime.now(ZoneInfo("America/Caracas"))


def format_timestamp(language: str) -> str:
    """Format timestamp in Venezuela timezone."""
    vet_time = get_venezuela_time()

    if language == "es":
        months_es = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic",
        }
        # Full style that worked well before: "1 Ago 2026, 08:31:00 AM"
        return (
            f"{vet_time.day} {months_es[vet_time.month]} {vet_time.year}, "
            f"{vet_time.strftime('%I:%M:%S %p')}"
        )

    return vet_time.strftime("%b %d, %Y, %I:%M:%S %p")
