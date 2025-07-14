"""Validation utilities for API endpoints."""

import re
from typing import Optional
from bson import ObjectId
from bson.errors import InvalidId

from app.core.v1.exceptions import ValidationException
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