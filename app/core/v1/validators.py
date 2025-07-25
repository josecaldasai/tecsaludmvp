"""Validation utilities for API endpoints."""

import re
from typing import Optional, Dict, Any
from bson import ObjectId
from bson.errors import InvalidId

from app.core.v1.exceptions import (
    ValidationException,
    InvalidDocumentIdFormatException,
    InvalidUserIdFormatException,
    UserIdRequiredException,
    InvalidPaginationParametersException,
    InvalidDocumentIdFilterException
)
from app.core.v1.log_manager import LogManager


class DocumentValidator:
    """Validator for document-related operations."""
    
    def __init__(self):
        self.logger = LogManager(__name__)
    
    @staticmethod
    def validate_document_id(document_id: str) -> str:
        """
        Validate document ID format (MongoDB ObjectId).
        
        Args:
            document_id: Document ID to validate
            
        Returns:
            str: Validated document ID
            
        Raises:
            ValidationException: If document ID format is invalid
        """
        if not document_id:
            raise ValidationException("Document ID cannot be empty")
        
        if not isinstance(document_id, str):
            raise ValidationException("Document ID must be a string")
        
        # Remove whitespace
        document_id = document_id.strip()
        
        if not document_id:
            raise ValidationException("Document ID cannot be empty or only whitespace")
        
        # Validate ObjectId format (24 hex characters)
        if not re.match(r'^[a-f0-9]{24}$', document_id):
            raise ValidationException(
                f"Invalid document ID format: '{document_id}'. "
                f"Expected 24 hexadecimal characters (MongoDB ObjectId)"
            )
        
        # Additional validation with bson ObjectId
        try:
            ObjectId(document_id)
        except InvalidId as err:
            raise ValidationException(
                f"Invalid document ID: '{document_id}'. {str(err)}"
            ) from err
        
        return document_id
    
    @staticmethod
    def validate_user_id(user_id: Optional[str]) -> Optional[str]:
        """
        Validate user ID format.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            Optional[str]: Validated user ID or None
            
        Raises:
            ValidationException: If user ID format is invalid
        """
        if user_id is None:
            return None
        
        if not isinstance(user_id, str):
            raise ValidationException("User ID must be a string")
        
        user_id = user_id.strip()
        
        if not user_id:
            return None
        
        # Validate length
        if len(user_id) > 100:
            raise ValidationException("User ID cannot exceed 100 characters")
        
        # Validate characters (alphanumeric, underscore, hyphen)
        if not re.match(r'^[a-zA-Z0-9_-]+$', user_id):
            raise ValidationException(
                "User ID can only contain alphanumeric characters, underscores, and hyphens"
            )
        
        return user_id


class SessionValidator:
    """Validator for session-related operations."""
    
    @staticmethod
    def validate_session_id(session_id: str) -> str:
        """
        Validate session ID format (UUID).
        
        Args:
            session_id: Session ID to validate
            
        Returns:
            str: Validated session ID
            
        Raises:
            ValidationException: If session ID format is invalid
        """
        if not session_id:
            raise ValidationException("Session ID cannot be empty")
        
        if not isinstance(session_id, str):
            raise ValidationException("Session ID must be a string")
        
        session_id = session_id.strip()
        
        if not session_id:
            raise ValidationException("Session ID cannot be empty or only whitespace")
        
        # Validate UUID format
        uuid_pattern = r'^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$'
        if not re.match(uuid_pattern, session_id):
            raise ValidationException(
                f"Invalid session ID format: '{session_id}'. "
                f"Expected UUID format (xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx)"
            )
        
        return session_id
    
    @staticmethod
    def validate_document_id_for_session(document_id: str) -> str:
        """
        Validate document ID format specifically for session creation.
        
        Args:
            document_id: Document ID to validate
            
        Returns:
            str: Validated document ID
            
        Raises:
            InvalidDocumentIdFormatException: If document ID format is invalid
        """
        if not document_id:
            raise InvalidDocumentIdFormatException("Document ID cannot be empty")
        
        if not isinstance(document_id, str):
            raise InvalidDocumentIdFormatException("Document ID must be a string")
        
        # Remove whitespace
        document_id = document_id.strip()
        
        if not document_id:
            raise InvalidDocumentIdFormatException("Document ID cannot be empty or only whitespace")
        
        # Validate ObjectId format (24 hex characters)
        if not re.match(r'^[a-f0-9]{24}$', document_id):
            raise InvalidDocumentIdFormatException(
                f"Invalid document ID format: '{document_id}'. "
                f"Expected 24 hexadecimal characters (MongoDB ObjectId)"
            )
        
        # Try to create ObjectId to ensure it's valid
        try:
            ObjectId(document_id)
        except InvalidId:
            raise InvalidDocumentIdFormatException(
                f"Invalid document ID: '{document_id}' is not a valid MongoDB ObjectId"
            )
        
        return document_id
    
    @staticmethod
    def validate_user_id_for_session(user_id: str) -> str:
        """
        Validate user ID format specifically for session creation.
        
        Args:
            user_id: User ID to validate
            
        Returns:
            str: Validated user ID
            
        Raises:
            InvalidUserIdFormatException: If user ID format is invalid
        """
        if not user_id:
            raise InvalidUserIdFormatException("User ID cannot be empty")
        
        if not isinstance(user_id, str):
            raise InvalidUserIdFormatException("User ID must be a string")
        
        user_id = user_id.strip()
        
        if not user_id:
            raise InvalidUserIdFormatException("User ID cannot be empty or only whitespace")
        
        # Basic format validation (no special characters that could cause issues)
        if not re.match(r'^[a-zA-Z0-9_.-]+$', user_id):
            raise InvalidUserIdFormatException(
                f"Invalid user ID format: '{user_id}'. "
                f"Only alphanumeric characters, underscores, dots, and hyphens are allowed"
            )
        
        if len(user_id) > 100:
            raise InvalidUserIdFormatException(
                f"User ID too long: '{user_id}'. Maximum length is 100 characters"
            )
        
        return user_id
    
    @staticmethod
    def validate_session_name(session_name: Optional[str]) -> Optional[str]:
        """
        Validate session name format and content.
        
        Args:
            session_name: Session name to validate (can be None)
            
        Returns:
            Optional[str]: Validated session name or None
            
        Raises:
            ValidationException: If session name format is invalid
        """
        if session_name is None:
            return None
        
        if not isinstance(session_name, str):
            raise ValidationException("Session name must be a string")
        
        session_name = session_name.strip()
        
        # If empty after strip, return None
        if not session_name:
            return None
        
        if len(session_name) > 200:
            raise ValidationException(
                f"Session name too long: '{session_name}'. Maximum length is 200 characters"
            )
        
        # Check for potentially problematic characters
        if re.search(r'[<>"\'\\\x00-\x1f]', session_name):
            raise ValidationException(
                f"Session name contains invalid characters: '{session_name}'. "
                f"Avoid using HTML/XML characters and control characters"
            )
        
        return session_name
    
    @staticmethod
    def validate_session_creation_data(user_id: str, document_id: str, session_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Validate all data required for session creation.
        
        Args:
            user_id: User ID creating the session
            document_id: Document ID for the session
            session_name: Optional session name
            
        Returns:
            Dict with validated data
            
        Raises:
            InvalidUserIdFormatException: If user ID is invalid
            InvalidDocumentIdFormatException: If document ID is invalid
            ValidationException: If session name is invalid
        """
        validated_user_id = SessionValidator.validate_user_id_for_session(user_id)
        validated_document_id = SessionValidator.validate_document_id_for_session(document_id)
        validated_session_name = SessionValidator.validate_session_name(session_name)
        
        return {
            "user_id": validated_user_id,
            "document_id": validated_document_id,
            "session_name": validated_session_name
        }
    
    @staticmethod
    def validate_user_id_required(user_id: Optional[str]) -> str:
        """
        Validate that user_id is provided and has correct format for session listing.
        
        Args:
            user_id: User ID to validate (may be None)
            
        Returns:
            str: Validated user ID
            
        Raises:
            UserIdRequiredException: If user_id is None or empty
            InvalidUserIdFormatException: If user_id format is invalid
        """
        if user_id is None:
            raise UserIdRequiredException("user_id parameter is required for session listing")
        
        if not isinstance(user_id, str):
            raise InvalidUserIdFormatException("user_id must be a string")
        
        user_id = user_id.strip()
        
        if not user_id:
            raise UserIdRequiredException("user_id cannot be empty or only whitespace")
        
        # Basic format validation (no special characters that could cause issues)
        if not re.match(r'^[a-zA-Z0-9_.-]+$', user_id):
            raise InvalidUserIdFormatException(
                f"Invalid user_id format: '{user_id}'. "
                f"Only alphanumeric characters, underscores, dots, and hyphens are allowed"
            )
        
        if len(user_id) > 100:
            raise InvalidUserIdFormatException(
                f"user_id too long: '{user_id}'. Maximum length is 100 characters"
            )
        
        return user_id
    
    @staticmethod
    def validate_document_id_filter(document_id: Optional[str]) -> Optional[str]:
        """
        Validate document_id format for session filtering (optional parameter).
        
        Args:
            document_id: Document ID to validate (may be None)
            
        Returns:
            Optional[str]: Validated document ID or None
            
        Raises:
            InvalidDocumentIdFilterException: If document_id format is invalid
        """
        if document_id is None:
            return None
        
        if not isinstance(document_id, str):
            raise InvalidDocumentIdFilterException("document_id must be a string")
        
        # Remove whitespace
        document_id = document_id.strip()
        
        if not document_id:
            return None  # Empty string is treated as None
        
        # Validate ObjectId format (24 hex characters)
        if not re.match(r'^[a-f0-9]{24}$', document_id):
            raise InvalidDocumentIdFilterException(
                f"Invalid document_id format: '{document_id}'. "
                f"Expected 24 hexadecimal characters (MongoDB ObjectId)"
            )
        
        # Try to create ObjectId to ensure it's valid
        try:
            ObjectId(document_id)
        except InvalidId:
            raise InvalidDocumentIdFilterException(
                f"Invalid document_id: '{document_id}' is not a valid MongoDB ObjectId"
            )
        
        return document_id
    
    @staticmethod
    def validate_pagination_parameters(limit: int, skip: int) -> Dict[str, int]:
        """
        Validate pagination parameters for session listing.
        
        Args:
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            Dict with validated pagination parameters
            
        Raises:
            InvalidPaginationParametersException: If parameters are invalid
        """
        if not isinstance(limit, int) or limit < 1:
            raise InvalidPaginationParametersException(
                f"Invalid limit: {limit}. Must be a positive integer"
            )
        
        if limit > 100:
            raise InvalidPaginationParametersException(
                f"Invalid limit: {limit}. Maximum allowed is 100"
            )
        
        if not isinstance(skip, int) or skip < 0:
            raise InvalidPaginationParametersException(
                f"Invalid skip: {skip}. Must be a non-negative integer"
            )
        
        return {
            "limit": limit,
            "skip": skip
        }
    
    @staticmethod
    def validate_session_listing_parameters(
        user_id: Optional[str], 
        document_id: Optional[str], 
        active_only: bool,
        limit: int,
        skip: int
    ) -> Dict[str, Any]:
        """
        Validate all parameters for session listing.
        
        Args:
            user_id: User ID (required)
            document_id: Document ID for filtering (optional)
            active_only: Whether to return only active sessions
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            Dict with validated parameters
            
        Raises:
            UserIdRequiredException: If user_id is missing
            InvalidUserIdFormatException: If user_id format is invalid
            InvalidDocumentIdFilterException: If document_id format is invalid
            InvalidPaginationParametersException: If pagination parameters are invalid
        """
        validated_user_id = SessionValidator.validate_user_id_required(user_id)
        validated_document_id = SessionValidator.validate_document_id_filter(document_id)
        validated_pagination = SessionValidator.validate_pagination_parameters(limit, skip)
        
        return {
            "user_id": validated_user_id,
            "document_id": validated_document_id,
            "active_only": active_only,
            "limit": validated_pagination["limit"],
            "skip": validated_pagination["skip"]
        } 