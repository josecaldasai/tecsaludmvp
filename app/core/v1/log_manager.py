"""Log Manager for application logging."""

import logging
import sys
from typing import Optional
from datetime import datetime

from app.settings.v1.general import SETTINGS


class LogManager:
    """Log Manager class for handling application logs."""

    def __init__(self, name: str = __name__):
        """Initialize Log Manager.

        Args:
            name (str): Logger name.
        """
        self.logger = logging.getLogger(name)
        self.logger.setLevel(getattr(logging, SETTINGS.LOG_LEVEL.upper()))
        
        # Avoid duplicate handlers
        if not self.logger.handlers:
            self._setup_logger()

    def _setup_logger(self):
        """Set up logger configuration."""
        # Create console handler
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setLevel(getattr(logging, SETTINGS.LOG_LEVEL.upper()))

        # Create formatter
        formatter = logging.Formatter(
            fmt='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        
        console_handler.setFormatter(formatter)
        self.logger.addHandler(console_handler)

    def info(self, message: str, **kwargs):
        """Log info message.

        Args:
            message (str): Log message.
            **kwargs: Additional context information.
        """
        context = self._format_context(kwargs)
        self.logger.info(f"{message} {context}")

    def warning(self, message: str, **kwargs):
        """Log warning message.

        Args:
            message (str): Log message.
            **kwargs: Additional context information.
        """
        context = self._format_context(kwargs)
        self.logger.warning(f"{message} {context}")

    def error(self, message: str, **kwargs):
        """Log error message.

        Args:
            message (str): Log message.
            **kwargs: Additional context information.
        """
        context = self._format_context(kwargs)
        self.logger.error(f"{message} {context}")

    def debug(self, message: str, **kwargs):
        """Log debug message.

        Args:
            message (str): Log message.
            **kwargs: Additional context information.
        """
        context = self._format_context(kwargs)
        self.logger.debug(f"{message} {context}")

    def critical(self, message: str, **kwargs):
        """Log critical message.

        Args:
            message (str): Log message.
            **kwargs: Additional context information.
        """
        context = self._format_context(kwargs)
        self.logger.critical(f"{message} {context}")

    def _format_context(self, context: dict) -> str:
        """Format context information for logging.

        Args:
            context (dict): Context information.

        Returns:
            str: Formatted context string.
        """
        if not context:
            return ""
        
        formatted_items = []
        for key, value in context.items():
            if isinstance(value, str):
                formatted_items.append(f"{key}='{value}'")
            else:
                formatted_items.append(f"{key}={value}")
        
        return f"[{', '.join(formatted_items)}]"

    def log_request(self, method: str, path: str, user_id: Optional[str] = None):
        """Log HTTP request.

        Args:
            method (str): HTTP method.
            path (str): Request path.
            user_id (Optional[str]): User ID if authenticated.
        """
        self.info(
            f"HTTP Request: {method} {path}",
            user_id=user_id,
            timestamp=datetime.now().isoformat()
        )

    def log_response(self, method: str, path: str, status_code: int, duration: float):
        """Log HTTP response.

        Args:
            method (str): HTTP method.
            path (str): Request path.
            status_code (int): HTTP status code.
            duration (float): Request duration in seconds.
        """
        self.info(
            f"HTTP Response: {method} {path} - {status_code}",
            duration=f"{duration:.3f}s",
            timestamp=datetime.now().isoformat()
        ) 