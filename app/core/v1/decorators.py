"""Decorators for application functionality."""

import time
import functools
from typing import Callable, Any, Optional
from datetime import datetime

from app.core.v1.log_manager import LogManager
from app.core.v1.exceptions import RuntimeException
from app.settings.v1.general import SETTINGS


def retry(
    max_retries: Optional[int] = None,
    delay: Optional[int] = None,
    exceptions: tuple = (Exception,)
):
    """Decorator for retry functionality.

    Args:
        max_retries (Optional[int]): Maximum number of retries.
        delay (Optional[int]): Delay between retries in seconds.
        exceptions (tuple): Tuple of exceptions to catch and retry.

    Returns:
        Callable: Decorated function.
    """
    if max_retries is None:
        max_retries = SETTINGS.NUMBER_OF_RETRIES
    if delay is None:
        delay = SETTINGS.SECONDS_BETWEEN_RETRIES

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = LogManager(func.__module__)
            
            for attempt in range(max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as err:
                    if attempt == max_retries:
                        logger.error(
                            f"Function {func.__name__} failed after {max_retries} retries",
                            error=str(err),
                            attempt=attempt + 1
                        )
                        raise RuntimeException(
                            f"Function {func.__name__} failed after {max_retries} retries: {err}"
                        ) from err
                    
                    logger.warning(
                        f"Function {func.__name__} failed, retrying...",
                        error=str(err),
                        attempt=attempt + 1,
                        max_retries=max_retries
                    )
                    time.sleep(delay)
            
        return wrapper
    return decorator


def log_execution_time(func: Callable) -> Callable:
    """Decorator to log function execution time.

    Args:
        func (Callable): Function to decorate.

    Returns:
        Callable: Decorated function.
    """
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        logger = LogManager(func.__module__)
        start_time = time.time()
        
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            logger.info(
                f"Function {func.__name__} executed successfully",
                execution_time=f"{execution_time:.3f}s",
                timestamp=datetime.now().isoformat()
            )
            
            return result
            
        except Exception as err:
            execution_time = time.time() - start_time
            
            logger.error(
                f"Function {func.__name__} failed",
                execution_time=f"{execution_time:.3f}s",
                error=str(err),
                timestamp=datetime.now().isoformat()
            )
            raise
    
    return wrapper


def validate_file_size(max_size: Optional[int] = None):
    """Decorator to validate file size.

    Args:
        max_size (Optional[int]): Maximum file size in bytes.

    Returns:
        Callable: Decorated function.
    """
    if max_size is None:
        max_size = SETTINGS.MAX_FILE_SIZE

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = LogManager(func.__module__)
            
            # Look for file-like objects in arguments
            for arg in args:
                if hasattr(arg, 'size') and arg.size > max_size:
                    logger.warning(
                        f"File size validation failed",
                        file_size=arg.size,
                        max_size=max_size,
                        function=func.__name__
                    )
                    raise RuntimeException(
                        f"File size {arg.size} exceeds maximum allowed size {max_size} bytes"
                    )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def validate_file_extension(allowed_extensions: Optional[list] = None):
    """Decorator to validate file extensions.

    Args:
        allowed_extensions (Optional[list]): List of allowed file extensions.

    Returns:
        Callable: Decorated function.
    """
    if allowed_extensions is None:
        allowed_extensions = SETTINGS.ALLOWED_FILE_EXTENSIONS

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            logger = LogManager(func.__module__)
            
            # Look for file-like objects in arguments
            for arg in args:
                if hasattr(arg, 'filename') and arg.filename:
                    file_extension = arg.filename.split('.')[-1].lower()
                    if file_extension not in allowed_extensions:
                        logger.warning(
                            f"File extension validation failed",
                            file_extension=file_extension,
                            allowed_extensions=allowed_extensions,
                            function=func.__name__
                        )
                        raise RuntimeException(
                            f"File extension '{file_extension}' not allowed. "
                            f"Allowed extensions: {allowed_extensions}"
                        )
            
            return func(*args, **kwargs)
        
        return wrapper
    return decorator


def async_retry(
    max_retries: Optional[int] = None,
    delay: Optional[int] = None,
    exceptions: tuple = (Exception,)
):
    """Decorator for async retry functionality.

    Args:
        max_retries (Optional[int]): Maximum number of retries.
        delay (Optional[int]): Delay between retries in seconds.
        exceptions (tuple): Tuple of exceptions to catch and retry.

    Returns:
        Callable: Decorated async function.
    """
    import asyncio
    
    if max_retries is None:
        max_retries = SETTINGS.NUMBER_OF_RETRIES
    if delay is None:
        delay = SETTINGS.SECONDS_BETWEEN_RETRIES

    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            logger = LogManager(func.__module__)
            
            for attempt in range(max_retries + 1):
                try:
                    return await func(*args, **kwargs)
                except exceptions as err:
                    if attempt == max_retries:
                        logger.error(
                            f"Async function {func.__name__} failed after {max_retries} retries",
                            error=str(err),
                            attempt=attempt + 1
                        )
                        raise RuntimeException(
                            f"Async function {func.__name__} failed after {max_retries} retries: {err}"
                        ) from err
                    
                    logger.warning(
                        f"Async function {func.__name__} failed, retrying...",
                        error=str(err),
                        attempt=attempt + 1,
                        max_retries=max_retries
                    )
                    await asyncio.sleep(delay)
            
        return wrapper
    return decorator 