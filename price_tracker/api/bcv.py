"""BCV (Banco Central de Venezuela) exchange rate API client.

Fetches official VES rates for major currencies with caching and fallbacks.

Primary source (same family as before): ve.dolarapi.com
  - /v1/cotizaciones → official USD + EUR in one call
  - /v1/dolares/oficial, /v1/euros/oficial → individual fallbacks

GBP (Libra esterlina) is NOT published by ve.dolarapi.com or currently on
the BCV homepage (USD/EUR/CNY/TRY/RUB only). When USD is available, GBP is
derived as: VES/GBP = VES/USD ÷ (GBP per USD from a public FX feed).
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

from .base import BaseAPIClient


@dataclass
class BCVRates:
    """Official (or derived) VES exchange rates keyed by foreign currency."""

    usd: Optional[float] = None  # VES per 1 USD
    eur: Optional[float] = None  # VES per 1 EUR
    gbp: Optional[float] = None  # VES per 1 GBP (may be derived)
    gbp_derived: bool = False
    source: str = ""
    timestamp: Optional[datetime] = None

    def as_dict(self) -> Dict[str, Optional[float]]:
        return {"USD": self.usd, "EUR": self.eur, "GBP": self.gbp}

    @property
    def has_any(self) -> bool:
        return any(v is not None and v > 0 for v in (self.usd, self.eur, self.gbp))


class BCVRateClient(BaseAPIClient):
    """Client for fetching BCV official exchange rates (USD / EUR / GBP)."""

    COTIZACIONES_URL = "https://ve.dolarapi.com/v1/cotizaciones"
    USD_OFICIAL_URL = "https://ve.dolarapi.com/v1/dolares/oficial"
    EUR_OFICIAL_URL = "https://ve.dolarapi.com/v1/euros/oficial"
    BCV_HOME_URL = "https://www.bcv.org.ve/"
    # Public FX feed used only to convert BCV USD → GBP when BCV has no GBP
    GBP_CROSS_URLS = (
        "https://api.frankfurter.app/latest?from=USD&to=GBP",
        "https://open.er-api.com/v6/latest/USD",
    )

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
        # Backward-compatible single-rate cache used by get_rate()
        self.cached_rate: Optional[float] = None
        self.cache_timestamp: Optional[datetime] = None

    def get_rate(self, force_refresh: bool = False) -> Optional[float]:
        """Return official VES per 1 USD (legacy helper for P2P vs BCV %)."""
        rates = self.get_rates(force_refresh=force_refresh)
        return rates.usd

    def get_rates(self, force_refresh: bool = False) -> BCVRates:
        """Fetch USD / EUR / GBP rates in VES with caching."""
        if not force_refresh and self.cached_rates and self.cache_timestamp:
            elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
            if elapsed < self.cache_duration and self.cached_rates.has_any:
                self.logger.debug(
                    "Using cached BCV rates USD=%s EUR=%s GBP=%s (age: %.0fs)",
                    self.cached_rates.usd,
                    self.cached_rates.eur,
                    self.cached_rates.gbp,
                    elapsed,
                )
                return self.cached_rates

        rates = BCVRates()

        # 1) Preferred: single cotizaciones payload (USD + EUR)
        rates = self._merge(rates, self._fetch_cotizaciones())

        # 2) Individual dolarapi endpoints for any missing pairs
        if rates.usd is None:
            rates.usd = self._fetch_promedio(self.USD_OFICIAL_URL)
            if rates.usd:
                rates.source = rates.source or self.USD_OFICIAL_URL
        if rates.eur is None:
            rates.eur = self._fetch_promedio(self.EUR_OFICIAL_URL)
            if rates.eur:
                rates.source = rates.source or self.EUR_OFICIAL_URL

        # 3) BCV website scrape fallback (USD / EUR; no GBP published today)
        if rates.usd is None or rates.eur is None:
            scraped = self._fetch_bcv_homepage()
            rates = self._merge(rates, scraped)

        # 4) GBP: not on dolarapi / not on BCV page → derive from USD × market cross
        if rates.gbp is None and rates.usd:
            gbp = self._derive_gbp_from_usd(rates.usd)
            if gbp:
                rates.gbp = gbp
                rates.gbp_derived = True

        if rates.has_any:
            rates.timestamp = datetime.now()
            self.cached_rates = rates
            self.cached_rate = rates.usd
            self.cache_timestamp = rates.timestamp
            self.logger.info(
                "BCV rates updated: USD=%s EUR=%s GBP=%s%s (source: %s)",
                f"{rates.usd:.4f}" if rates.usd else "n/a",
                f"{rates.eur:.4f}" if rates.eur else "n/a",
                f"{rates.gbp:.4f}" if rates.gbp else "n/a",
                " [GBP derived]" if rates.gbp_derived else "",
                rates.source or "mixed",
            )
            return rates

        if self.cached_rates and self.cached_rates.has_any:
            self.logger.warning("Failed to refresh BCV rates; using cached values")
            return self.cached_rates

        self.logger.error("Failed to fetch BCV rates from all sources")
        return rates

    def _merge(self, base: BCVRates, extra: Optional[BCVRates]) -> BCVRates:
        if not extra:
            return base
        if base.usd is None and extra.usd:
            base.usd = extra.usd
        if base.eur is None and extra.eur:
            base.eur = extra.eur
        if base.gbp is None and extra.gbp:
            base.gbp = extra.gbp
            base.gbp_derived = extra.gbp_derived
        if extra.source and not base.source:
            base.source = extra.source
        return base

    def _fetch_cotizaciones(self) -> Optional[BCVRates]:
        try:
            self.logger.debug(f"Fetching BCV cotizaciones from: {self.COTIZACIONES_URL}")
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
                currency = str(item.get("moneda", "")).upper()
                value = self._to_float(item.get("promedio"))
                if not value:
                    continue
                if currency == "USD":
                    rates.usd = value
                elif currency == "EUR":
                    rates.eur = value
                elif currency == "GBP":
                    rates.gbp = value
                    rates.gbp_derived = False

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
        """Parse USD/EUR (and GBP if ever present) from the official BCV site."""
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

            found: Dict[str, float] = {}
            for match in re.finditer(
                r"<span>\s*([A-Z]{3})\s*</span>[\s\S]{0,200}?"
                r"<strong[^>]*>\s*([\d\.,]+)",
                html,
            ):
                code = match.group(1).upper()
                value = self._parse_ve_number(match.group(2))
                if value and code in {"USD", "EUR", "GBP", "CNY", "TRY", "RUB"}:
                    found[code] = value

            if not found:
                return None

            rates = BCVRates(
                usd=found.get("USD"),
                eur=found.get("EUR"),
                gbp=found.get("GBP"),
                gbp_derived=False,
                source=self.BCV_HOME_URL,
            )
            return rates if rates.has_any else None
        except Exception as e:
            self.logger.debug(f"Failed BCV homepage scrape: {e}")
            return None

    def _derive_gbp_from_usd(self, usd_ves: float) -> Optional[float]:
        """Compute VES per GBP using BCV USD and a public USD→GBP cross rate."""
        gbp_per_usd = self._fetch_gbp_per_usd()
        if not gbp_per_usd or gbp_per_usd <= 0:
            return None
        # 1 USD = gbp_per_usd GBP  →  1 GBP = 1/gbp_per_usd USD
        # VES/GBP = (VES/USD) / (GBP/USD)
        return usd_ves / gbp_per_usd

    def _fetch_gbp_per_usd(self) -> Optional[float]:
        for url in self.GBP_CROSS_URLS:
            try:
                response = self.session.get(url, timeout=5)
                response.raise_for_status()
                data = response.json()
                if "rates" in data and "GBP" in data["rates"]:
                    value = float(data["rates"]["GBP"])
                    if value > 0:
                        self.logger.debug(
                            "GBP cross rate from %s: 1 USD = %.6f GBP", url, value
                        )
                        return value
            except Exception as e:
                self.logger.debug(f"Failed GBP cross fetch from {url}: {e}")
                continue
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
        # Venezuelan format on BCV: thousands may use '.' and decimals ','
        if "," in cleaned and "." in cleaned:
            cleaned = cleaned.replace(".", "").replace(",", ".")
        elif "," in cleaned:
            cleaned = cleaned.replace(",", ".")
        try:
            number = float(cleaned)
            return number if number > 0 else None
        except ValueError:
            return None
