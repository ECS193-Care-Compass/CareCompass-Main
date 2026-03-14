"""
Logging utility for CARE Bot
"""
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# Determine if running in Lambda
_IS_LAMBDA = bool(os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))

# Create logs directory (skip on Lambda, read-only filesystem)
if _IS_LAMBDA:
    LOGS_DIR = Path("/tmp/logs")
else:
    LOGS_DIR = Path(__file__).parent.parent.parent.parent / "logs"

LOGS_DIR.mkdir(exist_ok=True)


def get_logger(name: str, level: int = logging.INFO) -> logging.Logger:
    """
    Get or create a logger with console and file handlers

    Args:
        name: Logger name (typically __name__ from calling module)
        level: Logging level

    Returns:
        Configured logger instance
    """
    logger = logging.getLogger(name)

    # Only add handlers if logger doesn't have them already
    if not logger.handlers:
        logger.setLevel(level)

        # Console handler 
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(level)
        console_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        console_handler.setFormatter(console_formatter)
        logger.addHandler(console_handler)

        # File handler (skip on Lambda, CloudWatch handles logging)
        if not _IS_LAMBDA:
            log_file = LOGS_DIR / f"care_bot_{datetime.now().strftime('%Y%m%d')}.log"
            file_handler = logging.FileHandler(log_file)
            file_handler.setLevel(logging.DEBUG)
            file_formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(funcName)s:%(lineno)d - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            file_handler.setFormatter(file_formatter)
            logger.addHandler(file_handler)

    return logger


def log_interaction(logger: logging.Logger,
                   user_query: str,
                   response: str,
                   metadata: dict = None) -> None:
    """
    Log user interaction (privacy-preserving)

    Args:
        logger: Logger instance
        user_query: User's query (should be sanitized)
        response: Bot's response
        metadata: Additional metadata
    """
    logger.info(
        f"INTERACTION - Query length: {len(user_query)}, "
        f"Response length: {len(response)}, "
        f"Metadata: {metadata or {}}"
    )


