"""BCV (Banco Central de Venezuela) exchange rate API client.

This module fetches the official Venezuelan exchange rate with caching
and multiple fallback endpoints.
"""

from datetime import datetime
from typing import Optional

from .base import BaseAPIClient


class BCVRateClient(BaseAPIClient):
    """Client for fetching BCV official exchange rates."""

    def __init__(
        self,
        max_retries: int = 3,
        request_timeout: int = 10,
        backoff_multiplier: float = 2.0,
        cache_duration: int = 3600  # 1 hour
    ):
        """Initialize BCV rate client.

        Args:
            max_retries: Maximum number of retries
            request_timeout: Request timeout in seconds
            backoff_multiplier: Multiplier for exponential backoff
            cache_duration: Cache duration in seconds (default 1 hour)
        """
        super().__init__(max_retries, request_timeout, backoff_multiplier)
        self.cache_duration = cache_duration
        self.cached_rate: Optional[float] = None
        self.cache_timestamp: Optional[datetime] = None

    def get_rate(self, force_refresh: bool = False) -> Optional[float]:
        """Fetch current BCV official exchange rate.

        Caches the rate to avoid excessive API calls. Tries multiple
        API endpoints as fallbacks.

        Args:
            force_refresh: If True, ignore cache and fetch fresh rate

        Returns:
            Exchange rate in VES per USD, or None if all endpoints fail
        """
        # Check cache first
        if not force_refresh and self.cached_rate and self.cache_timestamp:
            elapsed = (datetime.now() - self.cache_timestamp).total_seconds()
            if elapsed < self.cache_duration:
                self.logger.debug(
                    f"Using cached BCV rate: {self.cached_rate:.2f} "
                    f"(age: {elapsed:.0f}s)"
                )
                return self.cached_rate

        # Try multiple API endpoints
        endpoints = [
            {
                "url": "https://ve.dolarapi.com/v1/dolares/oficial",
                "parser": lambda d: float(d.get("promedio", 0))
            },
            {
                "url": "https://pydolarve.org/api/v1/dollar?monitor=bcv",
                "parser": lambda d: float(d["monitors"]["bcv"]["price"])
                if "monitors" in d else 0
            },
            {
                "url": "https://s3.amazonaws.com/dolartoday/data.json",
                "parser": lambda d: float(d["USD"]["promedio_real"])
                if "USD" in d and "promedio_real" in d["USD"] else 0
            }
        ]

        for endpoint in endpoints:
            try:
                self.logger.debug(f"Fetching BCV rate from: {endpoint['url']}")
                response = self.session.get(endpoint['url'], timeout=5)
                response.raise_for_status()
                data = response.json()

                # Parse response using endpoint-specific parser
                rate = endpoint['parser'](data)

                if rate and rate > 0:
                    self.cached_rate = rate
                    self.cache_timestamp = datetime.now()
                    self.logger.info(
                        f"BCV rate updated: {rate:.2f} VES "
                        f"(source: {endpoint['url']})"
                    )
                    return rate

            except Exception as e:
                self.logger.debug(
                    f"Failed to fetch BCV from {endpoint['url']}: {e}"
                )
                continue

        # If all endpoints fail, keep using cached rate if available
        if self.cached_rate:
            self.logger.warning(
                "Failed to fetch new BCV rate, using cached value"
            )
            return self.cached_rate

        self.logger.error("Failed to fetch BCV rate from all endpoints")
        return None
