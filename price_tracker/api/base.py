"""Base API client with retry logic and rate limiting.

This module provides the base class for all API clients with common
functionality like session management, retry strategies, and rate limiting.
"""

import logging
import time
from datetime import datetime
from typing import Optional

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


class BaseAPIClient:
    """Base API client with retry and rate limit handling."""

    def __init__(
        self,
        max_retries: int = 3,
        request_timeout: int = 10,
        backoff_multiplier: float = 2.0
    ):
        """Initialize base API client.

        Args:
            max_retries: Maximum number of retries for failed requests
            request_timeout: Request timeout in seconds
            backoff_multiplier: Multiplier for exponential backoff
        """
        self.max_retries = max_retries
        self.request_timeout = request_timeout
        self.backoff_multiplier = backoff_multiplier
        self.logger = logging.getLogger(self.__class__.__name__)
        self.session = self._create_session()
        self.last_429_time: Optional[datetime] = None
        self.backoff_time = 0

    def _create_session(self) -> requests.Session:
        """Create requests session with retry logic.

        Returns:
            Configured requests Session
        """
        session = requests.Session()

        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[500, 502, 503, 504],
            allowed_methods=["GET", "POST"]
        )

        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        return session

    def _handle_rate_limit(self, retry_after: Optional[int] = None):
        """Handle 429 rate limit response.

        Args:
            retry_after: Seconds to wait before retrying (from Retry-After header)
        """
        self.last_429_time = datetime.now()

        if retry_after:
            wait_time = retry_after
        else:
            # Exponential backoff
            self.backoff_time = max(60, self.backoff_time * self.backoff_multiplier)
            wait_time = int(self.backoff_time)

        self.logger.warning(f"Rate limit hit. Backing off for {wait_time} seconds")
        time.sleep(wait_time)

    def request(
        self,
        method: str,
        url: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> requests.Response:
        """Make HTTP request with error handling.

        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL
            timeout: Request timeout (uses instance default if None)
            **kwargs: Additional arguments for requests

        Returns:
            Response object

        Raises:
            requests.exceptions.RequestException: For request errors
        """
        if timeout is None:
            timeout = self.request_timeout

        response = self.session.request(method, url, timeout=timeout, **kwargs)
        response.raise_for_status()
        return response
