"""Input validation models for document processing API."""

import json
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field, validator, ValidationError
import uuid


class DocumentUploadData(BaseModel):
    """Validation model for document upload form data."""
    
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User ID who is uploading the document"
    )
    
    description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Document description"
    )
    
    tags: Optional[List[str]] = Field(
        default=None,
        description="Document tags"
    )
    
    @validator('tags', pre=True)
    def parse_tags(cls, v):
        """Parse tags from JSON string if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return None
            except (json.JSONDecodeError, TypeError):
                return None
        return v if isinstance(v, list) else None
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if v is not None and v.strip() == "":
            return None
        return v
    
    @validator('description')
    def validate_description(cls, v):
        """Validate description."""
        if v is not None and v.strip() == "":
            return None
        return v


class BatchUploadData(BaseModel):
    """Validation model for batch upload form data."""
    
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="User ID who is uploading the documents"
    )
    
    batch_description: Optional[str] = Field(
        default=None,
        max_length=1000,
        description="Common description for all documents"
    )
    
    batch_tags: Optional[List[str]] = Field(
        default=None,
        description="Common tags for all documents"
    )
    
    @validator('batch_tags', pre=True)
    def parse_batch_tags(cls, v):
        """Parse batch_tags from JSON string if needed."""
        if v is None:
            return None
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
                return None
            except (json.JSONDecodeError, TypeError):
                return None
        return v if isinstance(v, list) else None
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if v is not None and v.strip() == "":
            return None
        return v
    
    @validator('batch_description')
    def validate_batch_description(cls, v):
        """Validate batch_description."""
        if v is not None and v.strip() == "":
            return None
        return v


class DocumentSearchParams(BaseModel):
    """Validation model for document search parameters."""
    
    user_id: str = Field(
        max_length=100,
        description="Filter documents by user ID (required)"
    )
    
    batch_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter documents by batch ID"
    )
    
    limit: int = Field(
        default=10,
        ge=1,
        le=100,
        description="Maximum number of results"
    )
    
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if v is None or v.strip() == "":
            raise ValidationError("user_id is required and cannot be empty")
        return v
    
    @validator('batch_id')
    def validate_batch_id(cls, v):
        """Validate batch_id format - must be valid UUID when provided."""
        if v is not None:
            if v.strip() == "":
                return None
            try:
                # Validate UUID format
                uuid.UUID(v)
                return v
            except ValueError:
                raise ValidationError(f"batch_id must be a valid UUID format, got: '{v}'")
        return v


class ChatQuestionData(BaseModel):
    """Validation model for chat question."""
    
    session_id: str = Field(
        description="Session ID for the chat conversation"
    )
    
    user_id: str = Field(
        description="User ID making the question"
    )
    
    document_id: str = Field(
        description="Document ID to ask about"
    )
    
    question: str = Field(
        min_length=1,
        max_length=2000,
        description="User's question about the document"
    )
    
    @validator('session_id')
    def validate_session_id(cls, v):
        """Validate session_id format."""
        if not v or not v.strip():
            raise ValidationError("Session ID cannot be empty")
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if not v or not v.strip():
            raise ValidationError("User ID cannot be empty")
        return v.strip()
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Validate document_id format."""
        if not v or not v.strip():
            raise ValidationError("Document ID cannot be empty")
        return v.strip()
    
    @validator('question')
    def validate_question(cls, v):
        """Validate question content."""
        if not v or not v.strip():
            raise ValidationError("Question cannot be empty")
        return v.strip()


class CreateSessionData(BaseModel):
    """Validation model for creating a new chat session."""
    
    user_id: str = Field(
        description="User ID creating the session"
    )
    
    document_id: str = Field(
        description="Document ID for this session"
    )
    
    session_name: Optional[str] = Field(
        default=None,
        max_length=200,
        description="Optional custom name for the session"
    )
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if not v or not v.strip():
            raise ValidationError("User ID cannot be empty")
        return v.strip()
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Validate document_id format."""
        if not v or not v.strip():
            raise ValidationError("Document ID cannot be empty")
        return v.strip()
    
    @validator('session_name')
    def validate_session_name(cls, v):
        """Validate session_name."""
        if v is not None and v.strip() == "":
            return None
        return v


class SessionSearchParams(BaseModel):
    """Validation model for session search parameters."""
    
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter sessions by user ID"
    )
    
    document_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter sessions by document ID"
    )
    
    active_only: bool = Field(
        default=True,
        description="Only return active sessions"
    )
    
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results"
    )
    
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if v is not None and v.strip() == "":
            return None
        return v
    
    @validator('document_id')
    def validate_document_id(cls, v):
        """Validate document_id format."""
        if v is not None and v.strip() == "":
            return None
        return v


class InteractionSearchParams(BaseModel):
    """Validation model for interaction search parameters."""
    
    session_id: Optional[str] = Field(
        default=None,
        description="Filter by session ID"
    )
    
    user_id: Optional[str] = Field(
        default=None,
        description="Filter by user ID"
    )
    
    document_id: Optional[str] = Field(
        default=None,
        description="Filter by document ID"
    )
    
    search_query: Optional[str] = Field(
        default=None,
        max_length=500,
        description="Text search query"
    )
    
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results"
    )
    
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )
    
    ascending: bool = Field(
        default=True,
        description="Sort order by creation time"
    )


# Dependency functions for FastAPI
def validate_upload_data(
    user_id: Optional[str] = None,
    description: Optional[str] = None,
    tags: Optional[str] = None
) -> DocumentUploadData:
    """Validate and return upload data."""
    return DocumentUploadData(
        user_id=user_id,
        description=description,
        tags=tags
    )


def validate_batch_upload_data(
    user_id: Optional[str] = None,
    batch_description: Optional[str] = None,
    batch_tags: Optional[str] = None
) -> BatchUploadData:
    """Validate and return batch upload data."""
    return BatchUploadData(
        user_id=user_id,
        batch_description=batch_description,
        batch_tags=batch_tags
    )


def validate_search_params(
    user_id: str,
    batch_id: Optional[str] = None,
    limit: int = 10,
    skip: int = 0
) -> DocumentSearchParams:
    """Validate document search parameters."""
    return DocumentSearchParams(
        user_id=user_id,
        batch_id=batch_id,
        limit=limit,
        skip=skip
    )


def validate_session_search_params(
    user_id: Optional[str] = None,
    document_id: Optional[str] = None,
    active_only: bool = True,
    limit: int = 20,
    skip: int = 0
) -> SessionSearchParams:
    """Validate and return session search parameters."""
    return SessionSearchParams(
        user_id=user_id,
        document_id=document_id,
        active_only=active_only,
        limit=limit,
        skip=skip
    )


def validate_interaction_search_params(
    session_id: Optional[str] = None,
    user_id: Optional[str] = None,
    document_id: Optional[str] = None,
    search_query: Optional[str] = None,
    limit: int = 20,
    skip: int = 0,
    ascending: bool = True
) -> InteractionSearchParams:
    """Validate and return interaction search parameters."""
    return InteractionSearchParams(
        session_id=session_id,
        user_id=user_id,
        document_id=document_id,
        search_query=search_query,
        limit=limit,
        skip=skip,
        ascending=ascending
    )


class FuzzySearchParams(BaseModel):
    """Validation model for fuzzy search parameters."""
    
    search_term: str = Field(
        min_length=1,
        max_length=200,
        description="Patient name or partial name to search for"
    )
    
    user_id: str = Field(
        max_length=100,
        description="Filter results by user ID (required)"
    )
    
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results"
    )
    
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )
    
    min_similarity: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold"
    )
    
    include_score: bool = Field(
        default=True,
        description="Include similarity score in results"
    )
    
    @validator('search_term')
    def validate_search_term(cls, v):
        """Validate search term."""
        if not v or v.strip() == "":
            raise ValidationError("search_term cannot be empty")
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if v is None or v.strip() == "":
            raise ValidationError("user_id is required and cannot be empty")
        return v


class SuggestionSearchParams(BaseModel):
    """Validation model for search suggestion parameters."""
    
    partial_term: str = Field(
        min_length=1,
        max_length=100,
        description="Partial patient name for suggestions"
    )
    
    user_id: str = Field(
        max_length=100,
        description="Filter suggestions by user ID (required)"
    )
    
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of suggestions"
    )
    
    @validator('partial_term')
    def validate_partial_term(cls, v):
        """Validate partial term."""
        if not v or v.strip() == "":
            raise ValueError("partial_term cannot be empty")
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if v is None or v.strip() == "":
            raise ValueError("user_id is required and cannot be empty")
        return v


class PatientDocumentSearchParams(BaseModel):
    """Validation model for patient document search parameters."""
    
    patient_name: str = Field(
        min_length=1,
        max_length=200,
        description="Patient name to search for"
    )
    
    user_id: str = Field(
        max_length=100,
        description="Filter results by user ID (required)"
    )
    
    limit: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of results"
    )
    
    skip: int = Field(
        default=0,
        ge=0,
        description="Number of results to skip"
    )
    
    @validator('patient_name')
    def validate_patient_name(cls, v):
        """Validate patient name."""
        if not v or v.strip() == "":
            raise ValueError("patient_name cannot be empty")
        return v.strip()
    
    @validator('user_id')
    def validate_user_id(cls, v):
        """Validate user_id format."""
        if v is None or v.strip() == "":
            raise ValueError("user_id is required and cannot be empty")
        return v


def validate_fuzzy_search_params(
    search_term: str,
    user_id: str,
    limit: int = 20,
    skip: int = 0,
    min_similarity: float = 0.3,
    include_score: bool = True
) -> FuzzySearchParams:
    """Validate fuzzy search parameters."""
    return FuzzySearchParams(
        search_term=search_term,
        user_id=user_id,
        limit=limit,
        skip=skip,
        min_similarity=min_similarity,
        include_score=include_score
    )


def validate_suggestion_search_params(
    partial_term: str,
    user_id: str,
    limit: int = 10
) -> SuggestionSearchParams:
    """Validate search suggestion parameters."""
    return SuggestionSearchParams(
        partial_term=partial_term,
        user_id=user_id,
        limit=limit
    )


def validate_patient_document_search_params(
    patient_name: str,
    user_id: str,
    limit: int = 20,
    skip: int = 0
) -> PatientDocumentSearchParams:
    """Validate patient document search parameters."""
    return PatientDocumentSearchParams(
        patient_name=patient_name,
        user_id=user_id,
        limit=limit,
        skip=skip
    ) 