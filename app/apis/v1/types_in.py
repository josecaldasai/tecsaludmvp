"""Input validation models for document processing API."""

import json
from typing import Optional, List
from pydantic import BaseModel, Field, validator, root_validator


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
    
    user_id: Optional[str] = Field(
        default=None,
        max_length=100,
        description="Filter documents by user ID"
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
        if v is not None and v.strip() == "":
            return None
        return v
    
    @validator('batch_id')
    def validate_batch_id(cls, v):
        """Validate batch_id format."""
        if v is not None and v.strip() == "":
            return None
        return v


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
    user_id: Optional[str] = None,
    batch_id: Optional[str] = None,
    limit: int = 10,
    skip: int = 0
) -> DocumentSearchParams:
    """Validate and return search parameters."""
    return DocumentSearchParams(
        user_id=user_id,
        batch_id=batch_id,
        limit=limit,
        skip=skip
    ) 