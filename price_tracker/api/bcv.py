"""BCV (Banco Central de Venezuela) exchange rate API client.

Fetches official VES rates for whatever currencies the sources publish.
New currencies appear automatically in consumers — no per-currency
hardcoding in the display layer.

Primary source: ve.dolarapi.com
  - /v1/cotizaciones → all official quotes in one call
  - optional per-currency fallbacks for known endpoints

Fallback: BCV homepage scrape (any ISO currency codes found).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Iterable, List, Optional, Tuple

from .base import BaseAPIClient


# Preferred display order when present. Unknown codes sort after these.
CURRENCY_DISPLAY_ORDER: Tuple[str, ...] = (
    "USD", "EUR", "GBP", "CNY", "TRY", "RUB", "JPY", "CHF", "BRL", "COP",
)

# Emoji markers for known currencies (fallback: 💱)
CURRENCY_EMOJI: Dict[str, str] = {
    "USD": "💵",
    "EUR": "💶",
    "GBP": "💷",
    "CNY": "💴",
    "JPY": "💴",
    "TRY": "🇹🇷",
    "RUB": "🇷🇺",
    "CHF": "₣",
    "BRL": "🇧🇷",
    "COP": "🇨🇴",
}


def currency_emoji(code: str) -> str:
    """Return a display emoji for a currency code."""
    return CURRENCY_EMOJI.get((code or "").upper(), "💱")


def sort_currency_codes(codes: Iterable[str]) -> List[str]:
    """Stable, human-friendly currency ordering."""
    order = {c: i for i, c in enumerate(CURRENCY_DISPLAY_ORDER)}
    return sorted(
        {(c or "").upper() for c in codes if c},
        key=lambda c: (order.get(c, 1000), c),
    )


@dataclass
class BCVRates:
    """Official VES exchange rates for any set of foreign currencies.

    ``rates`` maps ISO code → VES per 1 unit of that currency.
    Adding a new key is enough for Telegram / consumers to pick it up.
    """

    rates: Dict[str, float] = field(default_factory=dict)
    source: str = ""
    timestamp: Optional[datetime] = None

    # --- dynamic accessors -------------------------------------------------

    def get(self, code: str) -> Optional[float]:
        """Return VES rate for currency code, or None."""
        value = self.rates.get((code or "").upper())
        if value is not None and value > 0:
            return value
        return None

    def set(self, code: str, value: Optional[float]) -> None:
        """Set or clear a currency rate."""
        code = (code or "").upper()
        if not code:
            return
        if value is None or value <= 0:
            self.rates.pop(code, None)
        else:
            self.rates[code] = float(value)

    def items(self) -> List[Tuple[str, float]]:
        """Ordered (code, rate) pairs for display."""
        return [
            (code, self.rates[code])
            for code in sort_currency_codes(self.rates.keys())
            if self.rates.get(code) and self.rates[code] > 0
        ]

    def codes(self) -> List[str]:
        return [code for code, _ in self.items()]

    @property
    def has_any(self) -> bool:
        return bool(self.items())

    @property
    def primary(self) -> Optional[float]:
        """Best single reference rate (prefer USD, else first ordered)."""
        usd = self.get("USD")
        if usd is not None:
            return usd
        items = self.items()
        return items[0][1] if items else None

    # Back-compat properties used by older call sites
    @property
    def usd(self) -> Optional[float]:
        return self.get("USD")

    @property
    def eur(self) -> Optional[float]:
        return self.get("EUR")

    def as_dict(self) -> Dict[str, float]:
        return dict(self.items())

    def merge_missing(self, other: Optional["BCVRates"]) -> "BCVRates":
        """Fill only currencies we don't already have from ``other``."""
        if not other:
            return self
        for code, value in other.rates.items():
            if self.get(code) is None and value and value > 0:
                self.set(code, value)
        if other.source and not self.source:
            self.source = other.source
        return self

    def summary(self) -> str:
        """Compact log string: USD=746.63 EUR=858.98"""
        parts = [f"{code}={rate:.4f}" for code, rate in self.items()]
        return " ".join(parts) if parts else "none"


class BCVRateClient(BaseAPIClient):
    """Client for fetching BCV official exchange rates (dynamic currencies)."""

    COTIZACIONES_URL = "https://ve.dolarapi.com/v1/cotizaciones"
    BCV_HOME_URL = "https://www.bcv.org.ve/"

    # Optional per-currency fallbacks if cotizaciones omits a code
    CURRENCY_FALLBACK_URLS: Dict[str, str] = {
        "USD": "https://ve.dolarapi.com/v1/dolares/oficial",
        "EUR": "https://ve.dolarapi.com/v1/euros/oficial",
    }

    def __init__(
        self,
        max_retries: int = 3,
        request_timeout: int = 10,
        backoff_multiplier: float = 2.0,
        cache_duration: int = 3600,  # 1 hour
    ):
        super().__init__(max_retries, request_timeout, backoff_multiplier)
        self.cache_duration = cache_duration
        self.cached_rates: Optional[BCVRates] = None
        self.cached_rate: Optional[float] = None  # legacy primary rate
        self.cache_timestamp: Optional[datetime] = None

    def get_rate(self, force_refresh: bool = False) -> Optional[float]:
        """Return primary official rate (USD preferred)."""
        return self.get_rates(force_refresh=force_refresh).primary

    def get_rates(self, force_refresh: bool = False) -> BCVRates:
        """Fetch all available official rates with caching."""
        if not force_refresh and self.cached_rates and self.cache_timestamp:
            elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
            if elapsed < self.cache_duration and self.cached_rates.has_any:
                self.logger.debug(
                    "Using cached BCV rates %s (age: %.0fs)",
                    self.cached_rates.summary(),
                    elapsed,
                )
                return self.cached_rates

        rates = BCVRates()

        # 1) Preferred: cotizaciones (dynamic list of official currencies)
        rates.merge_missing(self._fetch_cotizaciones())

        # 2) Per-currency fallbacks only for missing known endpoints
        for code, url in self.CURRENCY_FALLBACK_URLS.items():
            if rates.get(code) is None:
                value = self._fetch_promedio(url)
                if value:
                    rates.set(code, value)
                    rates.source = rates.source or url

        # 3) BCV homepage scrape for anything still missing / extra codes
        if not rates.has_any or any(
            rates.get(c) is None for c in self.CURRENCY_FALLBACK_URLS
        ):
            rates.merge_missing(self._fetch_bcv_homepage())

        if rates.has_any:
            rates.timestamp = datetime.now()
            self.cached_rates = rates
            self.cached_rate = rates.primary
            self.cache_timestamp = rates.timestamp
            self.logger.info(
                "BCV rates updated: %s (source: %s)",
                rates.summary(),
                rates.source or "mixed",
            )
            return rates

        if self.cached_rates and self.cached_rates.has_any:
            self.logger.warning("Failed to refresh BCV rates; using cached values")
            return self.cached_rates

        self.logger.error("Failed to fetch BCV rates from all sources")
        return rates

    def _fetch_cotizaciones(self) -> Optional[BCVRates]:
        try:
            self.logger.debug(
                "Fetching BCV cotizaciones from: %s", self.COTIZACIONES_URL
            )
            response = self.session.get(self.COTIZACIONES_URL, timeout=5)
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, list):
                return None

            rates = BCVRates(source=self.COTIZACIONES_URL)
            for item in data:
                if not isinstance(item, dict):
                    continue
                # Only official BCV-style quotes (skip paralelo / black market)
                fuente = str(item.get("fuente", "oficial")).lower()
                if fuente not in ("oficial", "bcv"):
                    continue
                currency = str(item.get("moneda", "")).upper().strip()
                if not currency or len(currency) < 3:
                    continue
                value = self._to_float(item.get("promedio"))
                if value:
                    rates.set(currency, value)

            return rates if rates.has_any else None
        except Exception as e:
            self.logger.debug(f"Failed cotizaciones fetch: {e}")
            return None

    def _fetch_promedio(self, url: str) -> Optional[float]:
        try:
            self.logger.debug(f"Fetching BCV rate from: {url}")
            response = self.session.get(url, timeout=5)
            response.raise_for_status()
            data = response.json()
            return self._to_float(data.get("promedio"))
        except Exception as e:
            self.logger.debug(f"Failed to fetch {url}: {e}")
            return None

    def _fetch_bcv_homepage(self) -> Optional[BCVRates]:
        """Parse any currency codes published on the official BCV site."""
        try:
            self.logger.debug(f"Fetching BCV homepage: {self.BCV_HOME_URL}")
            response = self.session.get(
                self.BCV_HOME_URL,
                timeout=15,
                verify=False,  # BCV cert chain is often incomplete
                headers={"User-Agent": "Mozilla/5.0 (compatible; PriceTracker/2.0)"},
            )
            response.raise_for_status()
            html = response.text

            rates = BCVRates(source=self.BCV_HOME_URL)
            for match in re.finditer(
                r"<span>\s*([A-Z]{3})\s*</span>[\s\S]{0,200}?"
                r"<strong[^>]*>\s*([\d\.,]+)",
                html,
            ):
                code = match.group(1).upper()
                value = self._parse_ve_number(match.group(2))
                if value:
                    rates.set(code, value)

            return rates if rates.has_any else None
        except Exception as e:
            self.logger.debug(f"Failed BCV homepage scrape: {e}")
            return None

    @staticmethod
    def _to_float(value) -> Optional[float]:
        if value is None or value == "":
            return None
        try:
            number = float(value)
            return number if number > 0 else None
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _parse_ve_number(text: str) -> Optional[float]:
        """Parse BCV numbers like '748,78640000' (comma decimal separator)."""
        if not text:
            return None
        cleaned = text.strip().replace(" ", "")
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            number = float(cleaned)
            return number if number > 0 else None
        except ValueError:
            return None
