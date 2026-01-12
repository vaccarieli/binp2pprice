"""Logging configuration.

This module sets up application logging with console and file handlers.
"""

import logging
import sys


def setup_logging(log_file: str, log_level: str = "INFO"):
    """Setup logging configuration.

    Args:
        log_file: Path to log file
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR)
    """
    log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(log_format))

    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(getattr(logging, log_level.upper()))
    file_handler.setFormatter(logging.Formatter(log_format))

    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(console_handler)
    root_logger.addHandler(file_handler)

    # Suppress noisy libraries
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('requests').setLevel(logging.WARNING)


def setup_alerts_logger() -> logging.Logger:
    """Setup dedicated logger for BUY/SELL alerts.

    Returns:
        Configured logger for alerts
    """
    alerts_logger = logging.getLogger('alerts')
    alerts_logger.setLevel(logging.INFO)

    # Create file handler for alerts
    alerts_file = 'alerts_history.log'
    file_handler = logging.FileHandler(alerts_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)

    # Professional format with all details
    formatter = logging.Formatter(
        '%(asctime)s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # Avoid duplicate handlers
    if not alerts_logger.handlers:
        alerts_logger.addHandler(file_handler)

    alerts_logger.propagate = False
    return alerts_logger
