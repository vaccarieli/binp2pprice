"""Translation and localization support.

This module provides translations for Telegram messages and
handles timezone-aware timestamp formatting for Venezuela.
"""

from datetime import datetime
from zoneinfo import ZoneInfo


# Translation dictionary for Telegram messages
TRANSLATIONS = {
    "en": {
        "price_update": "Binance P2P Price Update",
        "bcv_official_rate": "BCV Official Rate",
        "best_buy": "Best BUY",
        "best_sell": "Best SELL",
        "buy": "BUY",
        "sell": "SELL",
        "vs_bcv": "vs BCV",
        "trader": "Trader",
        "available": "Available",
        "payment": "Payment",
        "orders": "orders",
        "spread": "Spread",
        "price_changes": "Price Changes",
        "no_offers": "No offers",
        "alert_title": "SUDDEN PRICE CHANGE ALERT!",
        "change": "Change",
        "up": "UP",
        "down": "DOWN",
    },
    "es": {
        "price_update": "Actualización de Precios P2P Binance",
        "bcv_official_rate": "Tasa Oficial BCV",
        "best_buy": "Mejor COMPRA",
        "best_sell": "Mejor VENTA",
        "buy": "COMPRA",
        "sell": "VENTA",
        "vs_bcv": "vs BCV",
        "trader": "Comerciante",
        "available": "Disponible",
        "payment": "Pago",
        "orders": "órdenes",
        "spread": "Diferencial",
        "price_changes": "Cambios de Precio",
        "no_offers": "Sin ofertas",
        "alert_title": "¡ALERTA DE CAMBIO REPENTINO DE PRECIO!",
        "change": "Cambio",
        "up": "SUBIÓ",
        "down": "BAJÓ",
    }
}


def get_translation(language: str, key: str) -> str:
    """Get translated string based on language.

    Args:
        language: Language code ("en" or "es")
        key: Translation key

    Returns:
        Translated string, or key if translation not found
    """
    return TRANSLATIONS.get(language, TRANSLATIONS["en"]).get(key, key)


def get_venezuela_time() -> datetime:
    """Get current time in Venezuela timezone (VET, UTC-4).

    Returns:
        Current datetime in Venezuela timezone
    """
    return datetime.now(ZoneInfo("America/Caracas"))


def format_timestamp(language: str) -> str:
    """Format timestamp according to language preference.

    Args:
        language: Language code ("en" or "es")

    Returns:
        Formatted timestamp string in Venezuela timezone
    """
    vet_time = get_venezuela_time()

    if language == "es":
        # Spanish format: "11 Ene 2026, 01:00:25 AM"
        months_es = {
            1: "Ene", 2: "Feb", 3: "Mar", 4: "Abr", 5: "May", 6: "Jun",
            7: "Jul", 8: "Ago", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dic"
        }
        day = vet_time.day
        month = months_es[vet_time.month]
        year = vet_time.year
        time_12h = vet_time.strftime("%I:%M:%S %p")
        return f"{day} {month} {year}, {time_12h}"
    else:
        # English format: "Jan 11, 2026, 01:00:25 AM"
        return vet_time.strftime("%b %d, %Y, %I:%M:%S %p")
