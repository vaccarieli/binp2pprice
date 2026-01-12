"""Binance P2P API client.

This module handles fetching P2P offers from Binance with proper
filtering, rate limiting, and error handling.
"""

import json
import time
from typing import List, Optional

import requests

from .base import BaseAPIClient


class BinanceP2PClient(BaseAPIClient):
    """Client for Binance P2P API."""

    API_URL = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"

    def __init__(
        self,
        asset: str = "USDT",
        fiat: str = "VES",
        max_retries: int = 3,
        request_timeout: int = 10,
        backoff_multiplier: float = 2.0
    ):
        """Initialize Binance P2P client.

        Args:
            asset: Crypto asset to trade (e.g., "USDT")
            fiat: Fiat currency (e.g., "VES")
            max_retries: Maximum number of retries
            request_timeout: Request timeout in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        super().__init__(max_retries, request_timeout, backoff_multiplier)
        self.asset = asset
        self.fiat = fiat

    def fetch_offers(
        self,
        trade_type: str,
        payment_methods: Optional[List[str]] = None,
        min_amount: float = 0.0
    ) -> Optional[dict]:
        """Fetch P2P offers from Binance.

        Uses API server-side filtering for payment methods and amount.
        Results are already sorted by best price (BUY=lowest, SELL=highest).

        Args:
            trade_type: "BUY" or "SELL"
            payment_methods: List of payment method names
            min_amount: Minimum transaction amount in fiat currency

        Returns:
            API response dict with offer data, or None if request fails
        """
        headers = {"Content-Type": "application/json"}

        # Convert payment methods to API format (remove spaces)
        # API expects "PagoMovil" not "Pago Movil"
        pay_types = []
        if payment_methods:
            for method in payment_methods:
                # Remove spaces and hyphens for API
                api_method = method.replace(" ", "").replace("-", "")
                pay_types.append(api_method)

        # Build request payload
        payload = {
            "fiat": self.fiat,
            "page": 1,
            "rows": 10,
            "tradeType": trade_type,
            "asset": self.asset,
            "countries": [],
            "proMerchantAds": False,
            "shieldMerchantAds": False,
            "filterType": "tradable",
            "periods": [],
            "additionalKycVerifyFilter": 0,
            "publisherType": "merchant",
            "payTypes": pay_types,
            "classifies": ["mass", "profession", "fiat_trade"],
            "tradedWith": False,
            "followed": False,
            "transAmount": min_amount
        }

        for attempt in range(self.max_retries):
            try:
                response = self.session.post(
                    self.API_URL,
                    json=payload,
                    headers=headers,
                    timeout=self.request_timeout
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    self._handle_rate_limit(
                        int(retry_after) if retry_after else None
                    )
                    continue

                # Handle IP ban
                if response.status_code == 418:
                    retry_after = response.headers.get('Retry-After', 300)
                    self.logger.error(
                        f"IP banned! Waiting {retry_after} seconds"
                    )
                    time.sleep(int(retry_after))
                    continue

                response.raise_for_status()

                data = response.json()

                # Validate response structure
                if not isinstance(data, dict) or 'data' not in data:
                    self.logger.error(
                        f"Invalid response structure for {trade_type}"
                    )
                    return None

                return data

            except requests.exceptions.Timeout:
                self.logger.warning(
                    f"Timeout fetching {trade_type} (attempt {attempt + 1})"
                )
                time.sleep(2 ** attempt)

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error for {trade_type}: {e}")
                time.sleep(2 ** attempt)

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {trade_type}: {e}")
                return None

            except Exception as e:
                self.logger.error(
                    f"Unexpected error for {trade_type}: {e}",
                    exc_info=True
                )
                return None

        self.logger.error(
            f"Failed to fetch {trade_type} after {self.max_retries} attempts"
        )
        return None
