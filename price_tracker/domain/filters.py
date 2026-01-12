"""Offer filtering logic.

This module provides filtering functions to process P2P offers
based on payment methods, amounts, and promotion status.
"""

import logging
from decimal import Decimal
from typing import List


class OfferFilter:
    """Filter P2P offers based on various criteria."""

    def __init__(self):
        """Initialize offer filter."""
        self.logger = logging.getLogger(__name__)

    def filter_by_payment_methods(
        self,
        offers: List[dict],
        payment_methods: List[str]
    ) -> List[dict]:
        """Filter offers to only include those with desired payment methods.

        Args:
            offers: List of raw offer dicts from API
            payment_methods: List of desired payment method names

        Returns:
            Filtered list of offers
        """
        if not payment_methods:
            return offers  # No filter, return all

        desired_normalized = [m.strip().lower() for m in payment_methods]
        filtered = []

        for offer in offers:
            try:
                trade_methods = offer.get("adv", {}).get("tradeMethods", [])
                methods = [
                    m.get("tradeMethodName", "")
                    for m in trade_methods
                    if m and m.get("tradeMethodName")
                ]
                methods_normalized = [m.strip().lower() for m in methods]

                # Include if offer has ANY of the desired payment methods
                has_desired = any(
                    method in methods_normalized
                    for method in desired_normalized
                )

                if has_desired:
                    filtered.append(offer)

            except Exception as e:
                self.logger.warning(f"Error filtering offer by payment: {e}")
                continue

        return filtered

    def filter_by_exclude_methods(
        self,
        offers: List[dict],
        exclude_methods: List[str]
    ) -> List[dict]:
        """Filter out offers with excluded payment methods.

        Args:
            offers: List of raw offer dicts from API
            exclude_methods: List of payment method names to exclude

        Returns:
            Filtered list of offers
        """
        if not exclude_methods:
            return offers

        exclude_normalized = [m.strip().lower() for m in exclude_methods]
        filtered = []

        for offer in offers:
            try:
                trade_methods = offer.get("adv", {}).get("tradeMethods", [])
                methods = [
                    m.get("tradeMethodName", "")
                    for m in trade_methods
                    if m and m.get("tradeMethodName")
                ]
                methods_normalized = [m.strip().lower() for m in methods]

                # Skip if any method is excluded
                has_excluded = any(
                    method in exclude_normalized
                    for method in methods_normalized
                )

                if not has_excluded:
                    filtered.append(offer)

            except Exception as e:
                self.logger.warning(f"Error filtering offer: {e}")
                continue

        return filtered

    def filter_by_amount(
        self,
        offers: List[dict],
        min_amount: Decimal,
        fiat: str
    ) -> List[dict]:
        """Filter offers by minimum transaction amount in fiat currency.

        Args:
            offers: List of raw offer dicts from API
            min_amount: Minimum amount in fiat currency
            fiat: Fiat currency code (e.g., "VES")

        Returns:
            Filtered list of offers
        """
        if min_amount <= 0:
            return offers

        filtered = []

        for offer in offers:
            try:
                adv = offer.get("adv", {})
                price = float(adv.get("price", 0))

                if price <= 0:
                    continue

                # API returns minSingleTransAmount and maxSingleTransAmount
                # already in FIAT (VES), not crypto! No need to multiply by price.
                min_fiat = float(adv.get("minSingleTransAmount", 0))
                max_fiat = float(adv.get(
                    "dynamicMaxSingleTransAmount",
                    adv.get("maxSingleTransAmount", 0)
                ))

                if max_fiat <= 0:
                    continue

                # Check if our desired amount is within the offer's range
                # The offer must be able to handle our min_amount:
                #   - Offer's min must be <= our amount (we can trade this much)
                #   - Offer's max must be >= our amount (offer has enough liquidity)
                if min_fiat <= float(min_amount) <= max_fiat:
                    filtered.append(offer)
                    self.logger.debug(
                        f"Included offer: {price:.2f} {fiat}, "
                        f"range: {min_fiat:,.0f} - {max_fiat:,.0f} {fiat}"
                    )
                else:
                    self.logger.debug(
                        f"Filtered out offer: {price:.2f} {fiat}, "
                        f"range: {min_fiat:,.0f} - {max_fiat:,.0f} {fiat} "
                        f"(need {min_amount:,.0f})"
                    )

            except Exception as e:
                self.logger.warning(f"Error filtering offer by amount: {e}")
                continue

        if filtered:
            self.logger.info(
                f"Amount filter: {len(filtered)} offers can handle "
                f"{min_amount:,.0f} {fiat}"
            )
        else:
            self.logger.warning(
                f"Amount filter: NO offers can handle {min_amount:,.0f} {fiat}"
            )

        return filtered

    def filter_promoted(self, offers: List[dict]) -> List[dict]:
        """Filter out promoted ads to get organic offers only.

        Args:
            offers: List of raw offer dicts from API

        Returns:
            Filtered list of offers without promoted ads
        """
        filtered = [
            offer for offer in offers
            if offer.get('privilegeType') is None
        ]

        if len(offers) != len(filtered):
            self.logger.debug(
                f"Filtered out {len(offers) - len(filtered)} promoted ads"
            )

        return filtered

    def find_best_offer(
        self,
        offers: List[dict],
        trade_type: str
    ) -> dict:
        """Find the best offer from a list.

        For BUY: lowest price
        For SELL: highest price

        Args:
            offers: List of raw offer dicts from API
            trade_type: "BUY" or "SELL"

        Returns:
            Best offer dict, or None if no offers
        """
        if not offers:
            return None

        # API already returns sorted results
        # BUY = lowest first, SELL = highest first
        # So just return the first offer
        return offers[0]
