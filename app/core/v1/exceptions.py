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


class ChatException(BaseException):
    """Chat and conversation related exception."""

    pass


# Specific Chat Session Creation Exceptions

class InvalidDocumentIdFormatException(ChatException):
    """Exception for invalid document ID format in chat sessions."""
    
    pass


class InvalidUserIdFormatException(ChatException):
    """Exception for invalid user ID format in chat sessions."""
    
    pass


class DocumentNotFoundException(ChatException):
    """Exception when document is not found for chat session."""
    
    pass


class DocumentAccessDeniedException(ChatException):
    """Exception when user doesn't have access to document."""
    
    pass


class DocumentNotReadyException(ChatException):
    """Exception when document is not ready for chat (still processing or failed)."""
    
    pass


class DocumentHasNoContentException(ChatException):
    """Exception when document has no extracted text content for chat."""
    
    pass


class SessionLimitExceededException(ChatException):
    """Exception when user exceeds maximum allowed sessions."""
    
    pass


class SessionCreationFailedException(ChatException):
    """Exception when session creation fails at database level."""
    
    pass


class DatabaseConnectionException(ChatException):
    """Exception for database connection issues during session operations."""
    
    pass


# Specific Chat Session Listing Exceptions

class UserIdRequiredException(ChatException):
    """Exception when user_id parameter is required but not provided."""
    
    pass


class InvalidUserIdException(ChatException):
    """Exception when user_id parameter is provided but invalid (empty, too short, etc.)."""
    
    pass


class InvalidPaginationParametersException(ChatException):
    """Exception for invalid pagination parameters (limit, skip)."""
    
    pass


class SessionListingFailedException(ChatException):
    """Exception when session listing fails due to internal errors."""
    
    pass


class InvalidDocumentIdFilterException(ChatException):
    """Exception for invalid document ID format in session filtering."""
    
    pass 


class UserDocumentMismatchException(ChatException):
    """Exception when user_id doesn't match document owner during session creation."""
    
    pass 


# Pills Management Exceptions

class PillNotFoundException(BaseException):
    """Exception when a pill is not found."""
    pass


class InvalidPillCategoryException(BaseException):
    """Exception for invalid pill category."""
    pass


class DuplicatePillPriorityException(BaseException):
    """Exception when trying to use a priority that already exists."""
    pass 


class InvalidUserIdException(AppException):
    """Exception raised for invalid user IDs."""
    pass


class MedicalFilenameException(AppException):
    """Exception raised for invalid medical filename format."""
    pass


class InvalidMedicalFilenameFormatException(MedicalFilenameException):
    """Exception raised when medical filename doesn't match expected format."""
    pass


class MedicalFilenameParsingException(MedicalFilenameException):
    """Exception raised when medical filename parsing fails."""
    pass


# Legacy exceptions for backward compatibility 