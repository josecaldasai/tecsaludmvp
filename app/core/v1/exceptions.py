"""Custom Exceptions for application."""


class BaseException(Exception):
    """Custom Base Exception."""

    def __init__(self, message: str):
        """Instance Custom Base Exception.

        Args:
            message (str): Message detail exception.
        """
        self.message = message
        super().__init__(self.message)


class AppException(BaseException):
    """Expected App Exception."""

    pass


class UnauthorizedException(BaseException):
    """Expected Unauthorized Exception."""

    pass


class UnexpectedException(BaseException):
    """Unexpected Exception."""

    pass


class RuntimeException(BaseException):
    """RuntimeException Exception."""

    pass


class StorageException(BaseException):
    """Storage related exception."""

    pass


class OCRException(BaseException):
    """OCR processing related exception."""

    pass


class DatabaseException(BaseException):
    """Database related exception."""

    pass


class DocumentProcessorException(BaseException):
    """Document processor related exception."""

    pass


class ValidationException(BaseException):
    """Validation related exception."""

    pass


class FileUploadException(BaseException):
    """File upload related exception."""

    pass 