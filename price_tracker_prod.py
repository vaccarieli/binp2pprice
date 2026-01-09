#!/usr/bin/env python3
"""
Binance P2P VES Price Tracker - Production Version
Monitors prices with robust error handling, logging, and alerting
"""

import requests
import json
import time
import logging
import argparse
import signal
import sys
import os
from datetime import datetime, timedelta
from collections import deque
from typing import Optional, Tuple, Dict, List
from dataclasses import dataclass
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from urllib.parse import urlparse
import re


# Configuration
@dataclass
class Config:
    """Application configuration"""
    asset: str = "USDT"
    fiat: str = "VES"
    check_interval: int = 30
    alert_threshold: float = 2.0
    payment_methods: List[str] = None
    exclude_methods: List[str] = None
    min_amount: float = 0.0  # Minimum transaction amount in fiat currency
    
    # Alerting
    email_enabled: bool = False
    email_smtp_host: str = ""
    email_smtp_port: int = 587
    email_from: str = ""
    email_to: str = ""
    email_password: str = ""
    
    webhook_enabled: bool = False
    webhook_url: str = ""
    
    # Limits
    max_retries: int = 3
    request_timeout: int = 10
    max_history: int = 1000
    backoff_multiplier: float = 2.0
    
    # Logging
    log_file: str = "price_tracker.log"
    log_level: str = "INFO"
    
    def __post_init__(self):
        if self.payment_methods is None:
            self.payment_methods = []
        if self.exclude_methods is None:
            self.exclude_methods = ["Recarga Pines"]

        # Validate configuration
        self._validate()

    def _validate(self):
        """Validate configuration values"""
        # Validate intervals
        if self.check_interval < 10:
            raise ValueError("check_interval must be at least 10 seconds")
        if self.check_interval > 3600:
            raise ValueError("check_interval must not exceed 3600 seconds")

        # Validate threshold
        if self.alert_threshold < 0 or self.alert_threshold > 100:
            raise ValueError("alert_threshold must be between 0 and 100")

        # Validate min_amount
        if self.min_amount < 0:
            raise ValueError("min_amount must be non-negative")

        # Validate log file path (prevent path traversal)
        if self.log_file:
            log_path = os.path.abspath(self.log_file)
            if not log_path.startswith(os.path.abspath(os.getcwd())):
                # Allow absolute paths but warn
                logging.warning(f"Log file path outside working directory: {log_path}")
            # Check for suspicious patterns
            if ".." in self.log_file or self.log_file.startswith("/etc") or self.log_file.startswith("C:\\Windows"):
                raise ValueError("Invalid log file path")

        # Validate webhook URL
        if self.webhook_enabled and self.webhook_url:
            try:
                parsed = urlparse(self.webhook_url)
                if parsed.scheme not in ["http", "https"]:
                    raise ValueError("Webhook URL must use HTTP or HTTPS")
                if not parsed.netloc:
                    raise ValueError("Webhook URL must have a valid hostname")
            except Exception as e:
                raise ValueError(f"Invalid webhook URL: {e}")

        # Validate email configuration
        if self.email_enabled:
            if not self.email_smtp_host or not self.email_from or not self.email_to:
                raise ValueError("Email enabled but missing required configuration")
            # Basic email validation
            email_pattern = re.compile(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$')
            if not email_pattern.match(self.email_from):
                raise ValueError(f"Invalid email_from address: {self.email_from}")
            if not email_pattern.match(self.email_to):
                raise ValueError(f"Invalid email_to address: {self.email_to}")


class AlertManager:
    """Handles different alert mechanisms"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
    
    def send_email(self, subject: str, body: str) -> bool:
        """Send email alert"""
        if not self.config.email_enabled:
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.config.email_from
            msg['To'] = self.config.email_to
            msg['Subject'] = subject
            
            msg.attach(MIMEText(body, 'plain'))
            
            with smtplib.SMTP(self.config.email_smtp_host, self.config.email_smtp_port) as server:
                server.starttls()
                server.login(self.config.email_from, self.config.email_password)
                server.send_message(msg)
            
            self.logger.info("Email alert sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False
    
    def send_webhook(self, data: dict) -> bool:
        """Send webhook alert (Slack/Discord/etc)"""
        if not self.config.webhook_enabled:
            return False
        
        try:
            response = requests.post(
                self.config.webhook_url,
                json=data,
                timeout=5
            )
            response.raise_for_status()
            self.logger.info("Webhook alert sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send webhook: {e}")
            return False
    
    def send_alert(self, alerts: List[str]):
        """Send alerts through all enabled channels"""
        if not alerts:
            return
        
        alert_text = "\n".join(alerts)
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Console
        self.logger.warning(f"ALERTS at {timestamp}:\n{alert_text}")
        
        # Email
        if self.config.email_enabled:
            subject = f"Binance P2P Alert - {self.config.fiat}/{self.config.asset}"
            body = f"Alert triggered at {timestamp}\n\n{alert_text}"
            self.send_email(subject, body)
        
        # Webhook
        if self.config.webhook_enabled:
            webhook_data = {
                "text": f"Binance P2P Alert",
                "timestamp": timestamp,
                "alerts": alerts
            }
            self.send_webhook(webhook_data)


class PriceTracker:
    """Main price tracking and monitoring class"""
    
    def __init__(self, config: Config):
        self.config = config
        self.logger = logging.getLogger(__name__)
        self.alert_manager = AlertManager(config)
        self.session = self._create_session()
        self.price_history = deque(maxlen=config.max_history)
        self.running = True
        self.consecutive_failures = 0
        self.last_429_time = None
        self.backoff_time = 0
        self.best_buy_offer = None  # Store best buy offer details
        self.best_sell_offer = None  # Store best sell offer details

        # Setup signal handlers
        signal.signal(signal.SIGINT, self._signal_handler)
        signal.signal(signal.SIGTERM, self._signal_handler)
    
    def _signal_handler(self, signum, frame):
        """Handle shutdown signals gracefully"""
        self.logger.info(f"Received signal {signum}, shutting down...")
        self.running = False
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.config.max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _handle_rate_limit(self, retry_after: Optional[int] = None):
        """Handle 429 rate limit response"""
        self.last_429_time = datetime.now()
        
        if retry_after:
            wait_time = retry_after
        else:
            # Exponential backoff
            self.backoff_time = max(60, self.backoff_time * self.config.backoff_multiplier)
            wait_time = int(self.backoff_time)
        
        self.logger.warning(f"Rate limit hit. Backing off for {wait_time} seconds")
        time.sleep(wait_time)
    
    def get_p2p_offers(self, trade_type: str) -> Optional[dict]:
        """
        Fetch P2P offers with error handling and rate limit respect

        Uses API server-side filtering for payment methods and amount
        Results are already sorted by best price (BUY=lowest, SELL=highest)
        Just fetch page 1 - the first result is the best offer!
        """
        url = "https://p2p.binance.com/bapi/c2c/v2/friendly/c2c/adv/search"
        headers = {"Content-Type": "application/json"}

        # Convert payment methods to API format (remove spaces)
        # API expects "PagoMovil" not "Pago Movil"
        pay_types = []
        if self.config.payment_methods:
            for method in self.config.payment_methods:
                # Remove spaces for API
                api_method = method.replace(" ", "").replace("-", "")
                pay_types.append(api_method)

        # Single request - API returns sorted results
        # DON'T use transAmount filter - it's too restrictive
        # Just filter by payment method and check amounts client-side

        payload = {
    "fiat":self.config.fiat,
    "page":1,
    "rows":10,
    "tradeType":trade_type,
    "asset":self.config.asset,
    "countries":[
    ],
    "proMerchantAds":False,
    "shieldMerchantAds":False,
    "filterType":"tradable",
    "periods":[
        
    ],
    "additionalKycVerifyFilter":0,
    "publisherType":"merchant",
    "payTypes":pay_types,
    "classifies":[
        "mass",
        "profession",
        "fiat_trade"
    ],
    "tradedWith":False,
    "followed":False,
    "transAmount":self.config.min_amount
    }
    

        for attempt in range(self.config.max_retries):
            try:
                response = self.session.post(
                    url,
                    json=payload,
                    headers=headers,
                    timeout=self.config.request_timeout
                )

                # Handle rate limiting
                if response.status_code == 429:
                    retry_after = response.headers.get('Retry-After')
                    self._handle_rate_limit(int(retry_after) if retry_after else None)
                    continue

                # Handle IP ban
                if response.status_code == 418:
                    retry_after = response.headers.get('Retry-After', 300)
                    self.logger.error(f"IP banned! Waiting {retry_after} seconds")
                    time.sleep(int(retry_after))
                    continue

                response.raise_for_status()

                data = response.json()

                # Validate response structure
                if not isinstance(data, dict) or 'data' not in data:
                    self.logger.error(f"Invalid response structure for {trade_type}")
                    return None

                return data

            except requests.exceptions.Timeout:
                self.logger.warning(f"Timeout fetching {trade_type} (attempt {attempt + 1})")
                time.sleep(2 ** attempt)

            except requests.exceptions.RequestException as e:
                self.logger.error(f"Request error for {trade_type}: {e}")
                time.sleep(2 ** attempt)

            except json.JSONDecodeError as e:
                self.logger.error(f"JSON decode error for {trade_type}: {e}")
                return None

            except Exception as e:
                self.logger.error(f"Unexpected error for {trade_type}: {e}", exc_info=True)
                return None

        self.consecutive_failures += 1
        self.logger.error(f"Failed to fetch {trade_type} after {self.config.max_retries} attempts")
        return None
    
    def filter_offers_by_payment_methods(self, offers: List[dict]) -> List[dict]:
        """Filter offers to only include those with desired payment methods"""
        if not self.config.payment_methods:
            return offers  # No filter, return all

        desired_normalized = [m.strip().lower() for m in self.config.payment_methods]
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

    def filter_offers_by_exclude(self, offers: List[dict]) -> List[dict]:
        """Filter out offers with excluded payment methods"""
        if not self.config.exclude_methods:
            return offers

        exclude_normalized = [m.strip().lower() for m in self.config.exclude_methods]
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

    def filter_offers_by_amount(self, offers: List[dict]) -> List[dict]:
        """Filter offers by minimum transaction amount in fiat currency"""
        if self.config.min_amount <= 0:
            return offers

        filtered = []

        for offer in offers:
            try:
                adv = offer.get("adv", {})
                price = float(adv.get("price", 0))

                if price <= 0:
                    continue

                # IMPORTANT: API returns minSingleTransAmount and maxSingleTransAmount
                # already in FIAT (VES), not crypto! No need to multiply by price.
                min_fiat = float(adv.get("minSingleTransAmount", 0))
                max_fiat = float(adv.get("dynamicMaxSingleTransAmount",
                                        adv.get("maxSingleTransAmount", 0)))

                if max_fiat <= 0:
                    continue

                # Check if our desired amount is within the offer's range
                # The offer must be able to handle our min_amount:
                #   - Offer's min must be <= our amount (we can trade this much)
                #   - Offer's max must be >= our amount (offer has enough liquidity)
                if min_fiat <= self.config.min_amount <= max_fiat:
                    filtered.append(offer)
                    self.logger.debug(
                        f"Included offer: {price:.2f} {self.config.fiat}, "
                        f"range: {min_fiat:,.0f} - {max_fiat:,.0f} {self.config.fiat}"
                    )
                else:
                    self.logger.debug(
                        f"Filtered out offer: {price:.2f} {self.config.fiat}, "
                        f"range: {min_fiat:,.0f} - {max_fiat:,.0f} {self.config.fiat} "
                        f"(need {self.config.min_amount:,.0f})"
                    )

            except Exception as e:
                self.logger.warning(f"Error filtering offer by amount: {e}")
                continue

        if filtered:
            self.logger.info(f"Amount filter: {len(filtered)} offers can handle {self.config.min_amount:,.0f} {self.config.fiat}")
        else:
            self.logger.warning(f"Amount filter: NO offers can handle {self.config.min_amount:,.0f} {self.config.fiat}")

        return filtered

    def filter_promoted_ads(self, offers: List[dict]) -> List[dict]:
        """Filter out promoted ads to get organic offers only"""
        filtered = [
            offer for offer in offers 
            if offer.get('privilegeType') is None
        ]
        
        if len(offers) != len(filtered):
            self.logger.debug(f"Filtered out {len(offers) - len(filtered)} promoted ads")
        
        return filtered
    
    def find_best_price(self, data, trade_type):
        if not data:
            return None
        
        if trade_type == "BUY":
            return min(data, key=lambda x: float(x['adv']['price']))
        else:  # SELL
            return max(data, key=lambda x: float(x['adv']['price']))



    def get_best_prices(self) -> Tuple[Optional[float], Optional[float]]:
        """Get best buy and sell prices with validation"""
        buy_data = self.get_p2p_offers("BUY")
        sell_data = self.get_p2p_offers("SELL")

        if not buy_data or not sell_data:
            return None, None
        
        try:
            # API filtered by payment methods only
            # Apply client-side filters: exclude promoted ads, exclude methods, and amount
            buy_offers = buy_data.get("data", [])
            
            # DEBUG: Log first 3 offers before filtering
            self.logger.info("=== BUY OFFERS BEFORE FILTERING ===")
            for i, offer in enumerate(buy_offers[:3]):
                price = offer.get('adv', {}).get('price')
                trader = offer.get('advertiser', {}).get('nickName')
                priv_type = offer.get('privilegeType')
                self.logger.info(f"  {i}: {trader} - {price} VES (privilegeType: {priv_type})")
            
            buy_offers = self.filter_promoted_ads(buy_offers)  # Remove promoted ads
            
            # DEBUG: Log first 3 offers after promoted ad filter
            self.logger.info("=== BUY OFFERS AFTER PROMOTED AD FILTER ===")
            for i, offer in enumerate(buy_offers[:3]):
                price = offer.get('adv', {}).get('price')
                trader = offer.get('advertiser', {}).get('nickName')
                self.logger.info(f"  {i}: {trader} - {price} VES")
            
            buy_offers = self.filter_offers_by_exclude(buy_offers)
            buy_offers = self.filter_offers_by_amount(buy_offers)

            sell_offers = sell_data.get("data", [])
            sell_offers = self.filter_promoted_ads(sell_offers)  # Remove promoted ads
            sell_offers = self.filter_offers_by_exclude(sell_offers)
            sell_offers = self.filter_offers_by_amount(sell_offers)

            self.logger.info(f"After filtering: {len(buy_offers)} BUY, {len(sell_offers)} SELL offers")

            # Allow showing results even if only one side has matches
            if not buy_offers and not sell_offers:
                self.logger.warning("No offers after filtering")
                self.logger.warning(f"Filtering: payment_methods={self.config.payment_methods}, "
                                  f"min_amount={self.config.min_amount} {self.config.fiat}")
                return None, None
            
            try:
                # Now safely get first offer - promoted ads are already filtered out
                self.best_buy_offer = self.find_best_price(buy_offers, "BUY") if buy_offers else None
                self.best_sell_offer = self.find_best_price(sell_offers, "SELL") if sell_offers else None

                best_buy = float(self.best_buy_offer.get("adv", {}).get("price", 0)) if self.best_buy_offer else None
                best_sell = float(self.best_sell_offer.get("adv", {}).get("price", 0)) if self.best_sell_offer else None
            except Exception as e:
                traceback = sys.exc_info()[2]
                print(f"Error extracting best prices: {e}")

            # Sanity check - only check values that exist
            if best_buy is not None and best_buy <= 0:
                self.logger.error(f"Invalid BUY price: {best_buy}")
                best_buy = None
                self.best_buy_offer = None

            if best_sell is not None and best_sell <= 0:
                self.logger.error(f"Invalid SELL price: {best_sell}")
                best_sell = None
                self.best_sell_offer = None

            # Check for suspicious spread only if both exist
            if best_buy and best_sell:
                if best_buy > best_sell * 2 or best_sell > best_buy * 2:
                    self.logger.warning(f"Suspicious price spread: buy={best_buy}, sell={best_sell}")

            # Log offer details for debugging
            if self.best_buy_offer:
                self.logger.debug(f"Best BUY: {best_buy} from {self.best_buy_offer.get('advertiser', {}).get('nickName', 'Unknown')}")
            if self.best_sell_offer:
                self.logger.debug(f"Best SELL: {best_sell} from {self.best_sell_offer.get('advertiser', {}).get('nickName', 'Unknown')}")

            return best_buy, best_sell
            
        except (ValueError, KeyError, TypeError) as e:
            self.logger.error(f"Error parsing prices: {e}")
            return None, None
    
    def record_price(self, buy_price: float, sell_price: float):
        """Record a price reading"""
        timestamp = datetime.now()
        self.price_history.append((timestamp, buy_price, sell_price))
        self.logger.debug(f"Recorded: buy={buy_price}, sell={sell_price}")
    
    def get_price_at_time(self, minutes_ago: int) -> Tuple[Optional[float], Optional[float]]:
        """Get price from N minutes ago"""
        if not self.price_history:
            return None, None
        
        target_time = datetime.now() - timedelta(minutes=minutes_ago)
        
        # Find closest price reading
        closest = min(
            self.price_history,
            key=lambda x: abs((x[0] - target_time).total_seconds())
        )
        
        # Only return if within 2 minutes of target
        if abs((closest[0] - target_time).total_seconds()) < 120:
            return closest[1], closest[2]
        
        return None, None
    
    def calculate_changes(self, current_buy: float, current_sell: float) -> Dict[str, dict]:
        """Calculate price changes over different time periods"""
        changes = {}
        
        for period, minutes in [("15m", 15), ("30m", 30), ("1h", 60)]:
            old_buy, old_sell = self.get_price_at_time(minutes)
            
            if old_buy and old_sell:
                buy_change = ((current_buy - old_buy) / old_buy) * 100
                sell_change = ((current_sell - old_sell) / old_sell) * 100
                
                changes[period] = {
                    "buy_change": buy_change,
                    "sell_change": sell_change,
                    "buy_old": old_buy,
                    "sell_old": old_sell
                }
        
        return changes
    
    def check_alert(self, changes: Dict[str, dict], threshold: float) -> List[str]:
        """Check if any changes exceed threshold"""
        alerts = []
        
        for period, data in changes.items():
            if abs(data['buy_change']) >= threshold:
                direction = "UP" if data['buy_change'] > 0 else "DOWN"
                alerts.append(
                    f"BUY price {direction} {abs(data['buy_change']):.2f}% in {period} "
                    f"({data['buy_old']:.2f} -> {data['buy_old'] * (1 + data['buy_change']/100):.2f})"
                )
            
            if abs(data['sell_change']) >= threshold:
                direction = "UP" if data['sell_change'] > 0 else "DOWN"
                alerts.append(
                    f"SELL price {direction} {abs(data['sell_change']):.2f}% in {period} "
                    f"({data['sell_old']:.2f} -> {data['sell_old'] * (1 + data['sell_change']/100):.2f})"
                )
        
        return alerts
    
    def display_status(self, buy_price: Optional[float], sell_price: Optional[float], changes: Dict[str, dict]):
        """Display current status"""
        try:
            os.system('cls' if os.name == 'nt' else 'clear')
        except:
            print("\n" * 50)  # Fallback

        print("=" * 70)
        print(f"Binance P2P {self.config.fiat}/{self.config.asset} Price Tracker")
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Status: {'RUNNING' if self.running else 'STOPPING'}")
        print("=" * 70)

        print(f"\nCurrent Prices:")

        # BUY offer details
        if buy_price is not None and self.best_buy_offer:
            buy_adv = self.best_buy_offer.get("adv", {})
            buy_advertiser = self.best_buy_offer.get("advertiser", {})
            buy_trader = buy_advertiser.get("nickName", "Unknown")
            buy_orders = buy_advertiser.get("monthOrderCount", 0)
            buy_available = float(buy_adv.get("surplusAmount", 0))
            buy_methods = ", ".join([
                m.get("tradeMethodName", "")
                for m in buy_adv.get("tradeMethods", [])
                if m.get("tradeMethodName")
            ])

            print(f"  Best BUY:  {buy_price:.2f} {self.config.fiat}/USDT")
            print(f"    Trader: {buy_trader} (Orders: {buy_orders})")
            print(f"    Available: {buy_available:.2f} USDT")
            print(f"    Payment: {buy_methods}")
        else:
            print(f"  Best BUY:  No offers matching filters")

        print()

        # SELL offer details
        if sell_price is not None and self.best_sell_offer:
            sell_adv = self.best_sell_offer.get("adv", {})
            sell_advertiser = self.best_sell_offer.get("advertiser", {})
            sell_trader = sell_advertiser.get("nickName", "Unknown")
            sell_orders = sell_advertiser.get("monthOrderCount", 0)
            sell_available = float(sell_adv.get("surplusAmount", 0))
            sell_methods = ", ".join([
                m.get("tradeMethodName", "")
                for m in sell_adv.get("tradeMethods", [])
                if m.get("tradeMethodName")
            ])

            print(f"  Best SELL: {sell_price:.2f} {self.config.fiat}/USDT")
            print(f"    Trader: {sell_trader} (Orders: {sell_orders})")
            print(f"    Available: {sell_available:.2f} USDT")
            print(f"    Payment: {sell_methods}")
        else:
            print(f"  Best SELL: No offers matching filters")

        print()

        # Only show spread if both prices exist
        if buy_price is not None and sell_price is not None:
            spread = buy_price - sell_price
            spread_pct = ((buy_price/sell_price - 1) * 100)
            print(f"  Spread: {spread:.2f} {self.config.fiat} ({spread_pct:.2f}%)")
        else:
            print(f"  Spread: N/A (need both BUY and SELL offers)")
        
        if changes:
            print(f"\nPrice Changes:")
            for period, data in sorted(changes.items()):
                print(f"\n  {period}:")
                print(f"    BUY:  {data['buy_change']:+.2f}% "
                      f"({data['buy_old']:.2f} -> {buy_price:.2f})")
                print(f"    SELL: {data['sell_change']:+.2f}% "
                      f"({data['sell_old']:.2f} -> {sell_price:.2f})")
        
        print(f"\nMonitoring:")
        print(f"  History: {len(self.price_history)} readings")
        print(f"  Failures: {self.consecutive_failures}")
        print(f"  Next check: {self.config.check_interval}s")
        print("=" * 70)
    
    def save_history(self):
        """Save price history to file"""
        filename = f"price_history_{self.config.fiat}_{self.config.asset}.json"
        
        data = {
            "last_updated": datetime.now().isoformat(),
            "config": {
                "asset": self.config.asset,
                "fiat": self.config.fiat,
                "check_interval": self.config.check_interval,
                "alert_threshold": self.config.alert_threshold
            },
            "history": [
                {
                    "timestamp": ts.isoformat(),
                    "buy": buy,
                    "sell": sell
                }
                for ts, buy, sell in self.price_history
            ]
        }
        
        try:
            # Atomic write
            temp_filename = f"{filename}.tmp"
            with open(temp_filename, 'w') as f:
                json.dump(data, f, indent=2)
            os.replace(temp_filename, filename)
            self.logger.info(f"Saved {len(self.price_history)} readings to {filename}")
            
        except Exception as e:
            self.logger.error(f"Error saving history: {e}")
    
    def load_history(self):
        """Load price history from file"""
        filename = f"price_history_{self.config.fiat}_{self.config.asset}.json"
        
        if not os.path.exists(filename):
            self.logger.info("No history file found, starting fresh")
            return
        
        try:
            with open(filename, 'r') as f:
                data = json.load(f)
            
            loaded = 0
            for entry in data.get("history", []):
                try:
                    ts = datetime.fromisoformat(entry["timestamp"])
                    # Only load recent history (last 24 hours)
                    if (datetime.now() - ts).total_seconds() < 86400:
                        self.price_history.append((ts, entry["buy"], entry["sell"]))
                        loaded += 1
                except (ValueError, KeyError) as e:
                    self.logger.warning(f"Skipping invalid history entry: {e}")
                    continue
            
            self.logger.info(f"Loaded {loaded} historical readings from last 24h")
            
        except Exception as e:
            self.logger.error(f"Error loading history: {e}")
    
    def run(self):
        """Run the tracker continuously"""
        self.logger.info("=" * 70)
        self.logger.info("Starting P2P Price Tracker")
        self.logger.info(f"Asset: {self.config.asset}")
        self.logger.info(f"Fiat: {self.config.fiat}")
        self.logger.info(f"Check interval: {self.config.check_interval}s")
        self.logger.info(f"Alert threshold: ±{self.config.alert_threshold}%")
        
        if self.config.payment_methods:
            self.logger.info(f"Payment methods: {', '.join(self.config.payment_methods)}")
        if self.config.exclude_methods:
            self.logger.info(f"Excluding: {', '.join(self.config.exclude_methods)}")
        
        self.logger.info("Email alerts: " + ("ENABLED" if self.config.email_enabled else "DISABLED"))
        self.logger.info("Webhook alerts: " + ("ENABLED" if self.config.webhook_enabled else "DISABLED"))
        self.logger.info("=" * 70)
        
        iteration = 0
        
        try:
            while self.running:
                iteration += 1
                self.logger.debug(f"Starting iteration {iteration}")
                
                # Get current prices
                buy_price, sell_price = self.get_best_prices()

                # Allow showing results if at least one price exists
                if buy_price is not None or sell_price is not None:
                    # Record price (only if both exist for historical tracking)
                    if buy_price is not None and sell_price is not None:
                        self.record_price(buy_price, sell_price)

                        # Calculate changes
                        changes = self.calculate_changes(buy_price, sell_price)

                        # Check for alerts
                        alerts = self.check_alert(changes, self.config.alert_threshold)
                        if alerts:
                            self.alert_manager.send_alert(alerts)
                    else:
                        changes = {}

                    # Display status
                    self.display_status(buy_price, sell_price, changes)

                    # Save history periodically (only if we have both prices)
                    if buy_price is not None and sell_price is not None and iteration % 10 == 0:
                        self.save_history()

                    # Reset consecutive failures
                    self.consecutive_failures = 0

                else:
                    # Display status even when no offers match
                    try:
                        os.system('cls' if os.name == 'nt' else 'clear')
                    except:
                        print("\n" * 50)

                    print("=" * 70)
                    print(f"Binance P2P {self.config.fiat}/{self.config.asset} Price Tracker")
                    print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                    print(f"Status: {'RUNNING' if self.running else 'STOPPING'}")
                    print("=" * 70)
                    print()
                    print("WARNING: NO OFFERS MATCH YOUR FILTERS")
                    print()
                    print("Current filters:")
                    if self.config.payment_methods:
                        print(f"  Payment methods: {', '.join(self.config.payment_methods)}")
                    if self.config.min_amount > 0:
                        print(f"  Minimum amount: {self.config.min_amount:,.0f} {self.config.fiat}")
                    if self.config.exclude_methods:
                        print(f"  Excluding: {', '.join(self.config.exclude_methods)}")
                    print()
                    print("Suggestions:")
                    if self.config.min_amount > 0:
                        print(f"  • Lower min_amount (currently {self.config.min_amount:,.0f} VES)")
                        print(f"  • Try: python price_tracker_prod.py -m 0")
                    if self.config.payment_methods:
                        print(f"  • Try different payment method")
                        print(f"  • Remove payment filter: python price_tracker_prod.py -p \"\"")
                    print()
                    print(f"Monitoring:")
                    print(f"  History: {len(self.price_history)} readings")
                    print(f"  Failures: {self.consecutive_failures}")
                    print(f"  Next check: {self.config.check_interval}s")
                    print("=" * 70)

                    self.logger.warning(f"Failed to fetch prices at {datetime.now()}")

                    # If too many failures, increase backoff
                    if self.consecutive_failures > 5:
                        extra_wait = min(300, self.consecutive_failures * 10)
                        self.logger.warning(f"Multiple failures, waiting extra {extra_wait}s")
                        time.sleep(extra_wait)
                
                # Wait before next check
                if self.running:
                    time.sleep(self.config.check_interval)
                
        except Exception as e:
            self.logger.error(f"Fatal error in main loop: {e}", exc_info=True)
            
        finally:
            self.logger.info("Shutting down tracker...")
            self.save_history()
            self.logger.info("Shutdown complete")


def setup_logging(config: Config):
    """Setup logging configuration"""
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))
    
    # File handler
    file_handler = logging.FileHandler(config.log_file)
    file_handler.setLevel(getattr(logging, config.log_level.upper()))
    file_handler.setFormatter(logging.Formatter(log_format))
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)
    
    # Suppress noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def load_config_file(filepath: str) -> dict:
    """Load configuration from JSON file"""
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        logging.warning(f"Config file {filepath} not found, using defaults")
        return {}
    except json.JSONDecodeError as e:
        logging.error(f"Invalid JSON in config file: {e}")
        return {}


def main():
    parser = argparse.ArgumentParser(
        description='Production P2P Price Tracker',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Auto-loads config.json if it exists
  python price_tracker_prod.py

  # Override payment method from config
  python price_tracker_prod.py -p "Banesco"

  # Without config file (all via CLI)
  python price_tracker_prod.py -p "PagoMovil" -i 60 -t 3.0

  # Use different config file
  python price_tracker_prod.py --config my_config.json

  # Override specific settings
  python price_tracker_prod.py -p "PagoMovil" -t 5.0
        """
    )
    
    parser.add_argument('--config', '-c', help='JSON config file path (default: config.json if exists)')
    parser.add_argument('--payment-methods', '-p', nargs='+', help='Payment methods to filter')
    parser.add_argument('--interval', '-i', type=int, help='Check interval in seconds')
    parser.add_argument('--threshold', '-t', type=float, help='Alert threshold percentage')
    parser.add_argument('--asset', help='Crypto asset (default: USDT)')
    parser.add_argument('--fiat', help='Fiat currency (default: VES)')
    parser.add_argument('--min-amount', '-m', type=float, help='Minimum transaction amount in fiat (e.g., 60000 for 60,000 VES)')

    # Email alerts
    parser.add_argument('--email-enabled', action='store_true', help='Enable email alerts')
    parser.add_argument('--email-smtp-host', help='SMTP server host')
    parser.add_argument('--email-smtp-port', type=int, help='SMTP server port')
    parser.add_argument('--email-from', help='From email address')
    parser.add_argument('--email-to', help='To email address')
    parser.add_argument('--email-password', help='Email password')
    
    # Webhook alerts
    parser.add_argument('--webhook-enabled', action='store_true', help='Enable webhook alerts')
    parser.add_argument('--webhook-url', help='Webhook URL')
    
    # Logging
    parser.add_argument('--log-file', help='Log file path')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Log level')
    
    args = parser.parse_args()

    # Load config: try specified file, then default config.json, then empty
    config_dict = {}
    if args.config:
        # User specified a config file
        config_dict = load_config_file(args.config)
    elif os.path.exists('config.json'):
        # Auto-load config.json if it exists
        config_dict = load_config_file('config.json')
        logging.info("Loaded default config.json")
    # else: no config file, will use CLI args or defaults
    
    # Override with CLI arguments
    if args.payment_methods:
        config_dict['payment_methods'] = args.payment_methods
    if args.interval:
        config_dict['check_interval'] = args.interval
    if args.threshold:
        config_dict['alert_threshold'] = args.threshold
    if args.asset:
        config_dict['asset'] = args.asset
    if args.fiat:
        config_dict['fiat'] = args.fiat
    if args.min_amount:
        config_dict['min_amount'] = args.min_amount

    # Email config
    if args.email_enabled:
        config_dict['email_enabled'] = True
    if args.email_smtp_host:
        config_dict['email_smtp_host'] = args.email_smtp_host
    if args.email_smtp_port:
        config_dict['email_smtp_port'] = args.email_smtp_port
    if args.email_from:
        config_dict['email_from'] = args.email_from
    if args.email_to:
        config_dict['email_to'] = args.email_to
    if args.email_password:
        config_dict['email_password'] = args.email_password
    
    # Webhook config
    if args.webhook_enabled:
        config_dict['webhook_enabled'] = True
    if args.webhook_url:
        config_dict['webhook_url'] = args.webhook_url
    
    # Logging config
    if args.log_file:
        config_dict['log_file'] = args.log_file
    if args.log_level:
        config_dict['log_level'] = args.log_level
    
    # Create config object
    config = Config(**config_dict)
    
    # Validate interval
    if config.check_interval < 10:
        print("ERROR: Interval must be at least 10 seconds to avoid rate limits")
        sys.exit(1)
    
    # Setup logging
    setup_logging(config)
    logger = logging.getLogger(__name__)
    
    # Validate email config
    if config.email_enabled:
        if not all([config.email_smtp_host, config.email_from, 
                   config.email_to, config.email_password]):
            logger.error("Email enabled but missing required config")
            sys.exit(1)
    
    # Create and run tracker
    tracker = PriceTracker(config)
    tracker.load_history()
    tracker.run()


if __name__ == "__main__":
    main()