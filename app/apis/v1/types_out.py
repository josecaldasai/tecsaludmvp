"""Output types for document processing API."""

from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
from datetime import datetime


class DocumentUploadResponse(BaseModel):
    """Response schema for document upload."""
    
    model_config = {"validate_assignment": True}
    
    document_id: str = Field(
        description="Unique document ID in the database"
    )
    
    processing_id: str = Field(
        description="Unique processing ID for tracking"
    )
    
    filename: str = Field(
        description="Original filename of the uploaded document"
    )
    
    storage_info: Dict[str, Any] = Field(
        description="Storage information including blob name and URL"
    )
    
    ocr_summary: Dict[str, Any] = Field(
        description="Summary of OCR processing results"
    )
    
    processing_status: str = Field(
        description="Current processing status"
    )
    
    processing_timestamp: str = Field(
        description="Timestamp when processing was completed"
    )
    
    # Información médica extraída del nombre del archivo (campos al primer nivel para búsquedas)
    expediente: Optional[str] = Field(
        default=None,
        description="Número de expediente del paciente"
    )
    
    nombre_paciente: Optional[str] = Field(
        default=None,
        description="Nombre completo del paciente"
    )
    
    numero_episodio: Optional[str] = Field(
        default=None,
        description="Número de episodio médico"
    )
    
    categoria: Optional[str] = Field(
        default=None,
        description="Categoría del documento médico (EMER, CONS, etc.)"
    )
    
    medical_info_valid: Optional[bool] = Field(
        default=None,
        description="Indica si la información médica fue parseada correctamente"
    )
    
    medical_info_error: Optional[str] = Field(
        default=None,
        description="Error en el parsing de información médica, si existe"
    )


class DocumentInfoResponse(BaseModel):
    """Response schema for document information."""
    
    document_id: str = Field(
        description="Unique document ID"
    )
    
    processing_id: str = Field(
        description="Processing ID for tracking"
    )
    
    filename: str = Field(
        description="Original filename"
    )
    
    content_type: str = Field(
        description="MIME type of the document"
    )
    
    file_size: int = Field(
        description="File size in bytes"
    )
    
    user_id: Optional[str] = Field(
        description="User ID who uploaded the document"
    )
    
    storage_info: Dict[str, Any] = Field(
        description="Storage information"
    )
    
    extracted_text: str = Field(
        description="Text extracted from the document"
    )
    
    processing_status: str = Field(
        description="Processing status"
    )
    
    batch_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Batch information if document was processed as part of a batch"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Document description"
    )
    
    tags: List[str] = Field(
        default=[],
        description="Document tags"
    )
    
    # Información médica extraída del nombre del archivo (campos al primer nivel para búsquedas)
    expediente: Optional[str] = Field(
        default=None,
        description="Número de expediente del paciente"
    )
    
    nombre_paciente: Optional[str] = Field(
        default=None,
        description="Nombre completo del paciente"
    )
    
    numero_episodio: Optional[str] = Field(
        default=None,
        description="Número de episodio médico"
    )
    
    categoria: Optional[str] = Field(
        default=None,
        description="Categoría del documento médico (EMER, CONS, etc.)"
    )
    
    medical_info_valid: Optional[bool] = Field(
        default=None,
        description="Indica si la información médica fue parseada correctamente"
    )
    
    medical_info_error: Optional[str] = Field(
        default=None,
        description="Error en el parsing de información médica, si existe"
    )
    
    created_at: datetime = Field(
        description="Creation timestamp"
    )
    
    updated_at: datetime = Field(
        description="Last update timestamp"
    )


class DocumentSearchResponse(BaseModel):
    """Response schema for document search with enhanced pagination metadata."""
    
    # Results
    documents: List[DocumentInfoResponse] = Field(
        description="List of matching documents"
    )
    
    # Pagination metadata
    total_found: int = Field(
        description="Total number of documents found"
    )
    
    limit: int = Field(
        description="Maximum number of results requested"
    )
    
    skip: int = Field(
        description="Number of results skipped"
    )
    
    returned_count: int = Field(
        description="Actual number of documents returned in this response"
    )
    
    has_next: bool = Field(
        description="Whether there are more results available"
    )
    
    has_prev: bool = Field(
        description="Whether there are previous results available"
    )
    
    current_page: int = Field(
        description="Current page number (1-based)"
    )
    
    total_pages: int = Field(
        description="Total number of pages available"
    )
    
    # Query context
    applied_filters: Dict[str, Any] = Field(
        description="Filters that were applied to the search"
    )
    
    request_id: str = Field(
        description="Unique request identifier for tracking"
    )
    
    search_timestamp: str = Field(
        description="Timestamp when the search was performed"
    )


class FuzzyDocumentMatch(BaseModel):
    """Document match with fuzzy search metadata."""
    
    # Document information (inherited from DocumentInfoResponse)
    document_id: str = Field(
        description="Unique document ID"
    )
    
    processing_id: str = Field(
        description="Processing ID for tracking"
    )
    
    filename: str = Field(
        description="Original filename"
    )
    
    content_type: str = Field(
        description="MIME type of the document"
    )
    
    file_size: int = Field(
        description="File size in bytes"
    )
    
    user_id: Optional[str] = Field(
        description="User ID who uploaded the document"
    )
    
    storage_info: Dict[str, Any] = Field(
        description="Storage information"
    )
    
    extracted_text: str = Field(
        description="Text extracted from the document"
    )
    
    processing_status: str = Field(
        description="Processing status"
    )
    
    batch_info: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Batch information if document was processed as part of a batch"
    )
    
    description: Optional[str] = Field(
        default=None,
        description="Document description"
    )
    
    tags: List[str] = Field(
        default=[],
        description="Document tags"
    )
    
    # Medical information
    expediente: Optional[str] = Field(
        default=None,
        description="Número de expediente del paciente"
    )
    
    nombre_paciente: Optional[str] = Field(
        default=None,
        description="Nombre completo del paciente"
    )
    
    numero_episodio: Optional[str] = Field(
        default=None,
        description="Número de episodio médico"
    )
    
    categoria: Optional[str] = Field(
        default=None,
        description="Categoría del documento médico (EMER, CONS, etc.)"
    )
    
    medical_info_valid: Optional[bool] = Field(
        default=None,
        description="Indica si la información médica fue parseada correctamente"
    )
    
    medical_info_error: Optional[str] = Field(
        default=None,
        description="Error en el parsing de información médica, si existe"
    )
    
    created_at: datetime = Field(
        description="Creation timestamp"
    )
    
    updated_at: datetime = Field(
        description="Last update timestamp"
    )
    
    # Fuzzy search specific fields
    similarity_score: float = Field(
        description="Similarity score between search term and patient name (0.0 to 1.0)"
    )
    
    match_type: str = Field(
        description="Type of match (exact, prefix, substring, fuzzy)"
    )


class FuzzySearchResponse(BaseModel):
    """Response schema for fuzzy patient search."""
    
    search_term: str = Field(
        description="Original search term"
    )
    
    normalized_term: str = Field(
        description="Normalized search term used for matching"
    )
    
    total_found: int = Field(
        description="Total number of documents found"
    )
    
    documents: List[FuzzyDocumentMatch] = Field(
        description="List of matching documents with similarity scores"
    )
    
    limit: int = Field(
        description="Maximum number of results requested"
    )
    
    skip: int = Field(
        description="Number of results skipped"
    )
    
    returned_count: int = Field(
        description="Actual number of documents returned in this response"
    )
    
    has_next: bool = Field(
        description="Whether there are more results available"
    )
    
    has_prev: bool = Field(
        description="Whether there are previous results available"
    )
    
    current_page: int = Field(
        description="Current page number (1-based)"
    )
    
    total_pages: int = Field(
        description="Total number of pages available"
    )
    
    search_strategies_used: List[str] = Field(
        description="List of search strategies used"
    )
    
    min_similarity_threshold: float = Field(
        description="Minimum similarity threshold applied"
    )
    
    search_timestamp: str = Field(
        description="Timestamp when the search was performed"
    )


class SearchSuggestionsResponse(BaseModel):
    """Response schema for search suggestions."""
    
    partial_term: str = Field(
        description="Partial search term provided"
    )
    
    suggestions: List[str] = Field(
        description="List of suggested patient names"
    )
    
    total_suggestions: int = Field(
        description="Total number of suggestions returned"
    )
    
    limit: int = Field(
        description="Maximum number of suggestions requested"
    )
    
    returned_count: int = Field(
        description="Actual number of suggestions returned in this response"
    )
    
    has_next: bool = Field(
        description="Whether there are more suggestions available"
    )
    
    has_prev: bool = Field(
        description="Whether there are previous suggestions available"
    )
    
    current_page: int = Field(
        description="Current page number (1-based)"
    )
    
    total_pages: int = Field(
        description="Total number of pages available"
    )
    
    search_timestamp: str = Field(
        description="Timestamp when the search was performed"
    )


class BatchUploadResponse(BaseModel):
    """Response schema for batch document upload."""
    
    batch_id: str = Field(
        description="Unique batch ID"
    )
    
    batch_timestamp: str = Field(
        description="Timestamp when batch processing started"
    )
    
    batch_description: Optional[str] = Field(
        description="Description of the batch"
    )
    
    user_id: Optional[str] = Field(
        description="User ID who uploaded the batch"
    )
    
    total_files: int = Field(
        description="Total number of files in the batch"
    )
    
    processed_count: int = Field(
        description="Number of successfully processed documents"
    )
    
    failed_count: int = Field(
        description="Number of failed documents"
    )
    
    success_rate: float = Field(
        description="Success rate as percentage (0-100)"
    )
    
    processing_status: str = Field(
        description="Overall batch processing status (completed, failed, partial_success)"
    )
    
    successful_documents: List[DocumentUploadResponse] = Field(
        description="List of successfully processed documents"
    )
    
    failed_documents: List[Dict[str, Any]] = Field(
        description="List of failed documents with error details"
    )
    
    processing_summary: Dict[str, Any] = Field(
        description="Processing summary with statistics"
    )


class DocumentDeleteResponse(BaseModel):
    """Response schema for document deletion."""
    
    document_id: str = Field(
        description="ID of the deleted document"
    )
    
    success: bool = Field(
        description="Whether deletion was successful"
    )
    
    message: str = Field(
        description="Deletion status message"
    )


class HealthCheckResponse(BaseModel):
    """Response schema for health check."""
    
    status: str = Field(
        description="Overall health status"
    )
    
    timestamp: str = Field(
        description="Timestamp of the health check"
    )
    
    components: Dict[str, str] = Field(
        description="Status of individual components"
    )


class ErrorResponse(BaseModel):
    """Response schema for error responses."""
    
    error: str = Field(
        description="Error type"
    )
    
    message: str = Field(
        description="Error message"
    )
    
    details: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional error details"
    )
    
    timestamp: str = Field(
        description="Error timestamp"
    )


class ChatSessionResponse(BaseModel):
    """Response schema for chat session."""
    
    model_config = {"validate_assignment": True}
    
    session_id: str = Field(
        description="Unique session identifier"
    )
    
    user_id: str = Field(
        description="User ID who owns the session"
    )
    
    document_id: str = Field(
        description="Document ID for this session"
    )
    
    session_name: str = Field(
        description="Name of the chat session"
    )
    
    is_active: bool = Field(
        description="Whether the session is active"
    )
    
    created_at: str = Field(
        description="Session creation timestamp"
    )
    
    last_interaction_at: str = Field(
        description="Last interaction timestamp"
    )
    
    interaction_count: int = Field(
        description="Number of interactions in this session"
    )


class ChatInteractionResponse(BaseModel):
    """Response schema for chat interaction."""
    
    model_config = {"validate_assignment": True}
    
    interaction_id: str = Field(
        description="Unique interaction identifier"
    )
    
    session_id: str = Field(
        description="Session identifier"
    )
    
    user_id: str = Field(
        description="User identifier"
    )
    
    document_id: str = Field(
        description="Document identifier"
    )
    
    question: str = Field(
        description="User's question"
    )
    
    response: str = Field(
        description="Assistant's response"
    )
    
    created_at: str = Field(
        description="Interaction timestamp"
    )
    
    metadata: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Additional interaction metadata"
    )


class ChatResponseStart(BaseModel):
    """Response schema for chat response start (streaming)."""
    
    model_config = {"validate_assignment": True}
    
    interaction_id: str = Field(
        description="Unique interaction identifier"
    )
    
    session_id: str = Field(
        description="Session identifier"
    )
    
    question: str = Field(
        description="User's question"
    )
    
    started_at: str = Field(
        description="Response start timestamp"
    )


class ChatStatsResponse(BaseModel):
    """Response schema for chat statistics."""
    
    model_config = {"validate_assignment": True}
    
    period_days: int = Field(
        description="Number of days analyzed"
    )
    
    total_interactions: int = Field(
        description="Total number of interactions"
    )
    
    total_questions: int = Field(
        description="Total number of questions"
    )
    
    total_responses: int = Field(
        description="Total number of responses"
    )
    
    avg_question_length: float = Field(
        description="Average question length in characters"
    )
    
    avg_response_length: float = Field(
        description="Average response length in characters"
    )
    
    unique_sessions: int = Field(
        description="Number of unique sessions"
    )
    
    unique_documents: int = Field(
        description="Number of unique documents"
    )
    
    interactions_per_day: float = Field(
        description="Average interactions per day"
    )


class SessionListResponse(BaseModel):
    """Response schema for session list with enhanced pagination metadata."""
    
    model_config = {"validate_assignment": True}
    
    # Results
    sessions: List[ChatSessionResponse] = Field(
        description="List of chat sessions"
    )
    
    # Pagination metadata
    total_found: int = Field(
        description="Total number of sessions found"
    )
    
    limit: int = Field(
        description="Limit applied to results"
    )
    
    skip: int = Field(
        description="Number of results skipped"
    )
    
    returned_count: int = Field(
        description="Actual number of sessions returned in this response"
    )
    
    has_next: bool = Field(
        description="Whether there are more results available"
    )
    
    has_prev: bool = Field(
        description="Whether there are previous results available"
    )
    
    current_page: int = Field(
        description="Current page number (1-based)"
    )
    
    total_pages: int = Field(
        description="Total number of pages available"
    )
    
    # Query context
    applied_filters: Dict[str, Any] = Field(
        description="Filters that were applied to the search"
    )
    
    request_id: Optional[str] = Field(
        default=None,
        description="Unique request identifier for tracking"
    )
    
    search_timestamp: str = Field(
        description="Timestamp when the search was performed"
    )


class InteractionListResponse(BaseModel):
    """Response schema for interaction list."""
    
    model_config = {"validate_assignment": True}
    
    interactions: List[ChatInteractionResponse] = Field(
        description="List of chat interactions"
    )
    
    total_found: int = Field(
        description="Total number of interactions found"
    )
    
    limit: int = Field(
        description="Limit applied to results"
    )
    
    skip: int = Field(
        description="Number of results skipped"
    )


class SessionDeleteResponse(BaseModel):
    """Response schema for session deletion."""
    
    model_config = {"validate_assignment": True}
    
    session_id: str = Field(
        description="ID of the deleted session"
    )
    
    deleted: bool = Field(
        description="Whether the session was successfully deleted"
    )
    
    interactions_deleted: int = Field(
        description="Number of interactions deleted with the session"
    )
    
    message: str = Field(
        description="Deletion result message"
    )
    
    deleted_timestamp: str = Field(
        description="Timestamp when the session was deleted"
    )


class AzureSpeechTokenResponse(BaseModel):
    """Response schema for Azure Speech token."""
    
    model_config = {"validate_assignment": True}
    
    access_token: str = Field(
        description="Azure Speech Services access token"
    )
    
    token_type: str = Field(
        description="Type of token (Bearer)"
    )
    
    expires_in: int = Field(
        description="Token expiration time in seconds"
    )
    
    region: str = Field(
        description="Azure Speech Services region"
    )
    
    issued_at: str = Field(
        description="Timestamp when token was issued"
    )


class AzureStorageTokenResponse(BaseModel):
    """Response schema for Azure Storage token."""
    
    model_config = {"validate_assignment": True}
    
    sas_token: str = Field(
        description="Azure Storage SAS token"
    )
    
    container_url: str = Field(
        description="Complete container URL with SAS token"
    )
    
    base_url: str = Field(
        description="Base URL for the storage account"
    )
    
    container_name: str = Field(
        description="Name of the storage container"
    )
    
    account_name: str = Field(
        description="Storage account name"
    )
    
    expires_at: str = Field(
        description="Token expiration timestamp (ISO format)"
    )
    
    permissions: str = Field(
        description="Token permissions (e.g., 'rl' for read and list)"
    )
    
    resource_type: str = Field(
        description="Resource type (container)"
    )
    
    issued_at: str = Field(
        description="Timestamp when token was issued"
    ) 


# ============================================================================
# PILLS RESPONSE MODELS
# ============================================================================

class PillResponse(BaseModel):
    """Response schema for a single pill template."""
    
    pill_id: str = Field(
        description="Unique pill identifier"
    )
    
    starter: str = Field(
        description="Text displayed on the starter button"
    )
    
    text: str = Field(
        description="Text that will be sent when the button is clicked"
    )
    
    icon: str = Field(
        description="Emoji icon displayed on the button"
    )
    
    category: str = Field(
        description="Category for organizing pills"
    )
    
    priority: int = Field(
        description="Priority order (1 is highest priority)"
    )
    
    is_active: bool = Field(
        description="Whether the pill is active"
    )
    
    created_at: str = Field(
        description="Creation timestamp (ISO format)"
    )
    
    updated_at: str = Field(
        description="Last update timestamp (ISO format)"
    )


class PillListResponse(BaseModel):
    """Response schema for pill list with pagination."""
    
    pills: List[PillResponse] = Field(
        description="List of pill templates"
    )
    
    pagination: Dict[str, Any] = Field(
        description="Pagination metadata"
    )
    
    total: int = Field(
        description="Total number of pills matching the query"
    )
    
    count: int = Field(
        description="Number of pills returned in this response"
    )
    
    limit: int = Field(
        description="Maximum number of results requested"
    )
    
    skip: int = Field(
        description="Number of results skipped"
    )
    
    has_next: bool = Field(
        description="Whether there are more results available"
    )
    
    has_prev: bool = Field(
        description="Whether there are previous results available"
    )


class PillDeleteResponse(BaseModel):
    """Response schema for pill deletion."""
    
    pill_id: str = Field(
        description="ID of the deleted pill"
    )
    
    success: bool = Field(
        description="Whether the deletion was successful"
    )
    
    message: str = Field(
        description="Descriptive message about the deletion result"
    )


class PillCategoriesResponse(BaseModel):
    """Response schema for available pill categories."""
    
    categories: List[str] = Field(
        description="List of valid category names"
    )
    
    count: int = Field(
        description="Number of available categories"
    ) 


# ============================================================================
# STATISTICS API RESPONSE TYPES
# ============================================================================

class PlatformOverviewStatsResponse(BaseModel):
    """Response schema for platform-wide statistics."""
    
    model_config = {"validate_assignment": True}
    
    totals: Dict[str, Any] = Field(
        description="Total counts across the platform"
    )
    
    storage: Dict[str, Any] = Field(
        description="Storage usage statistics"
    )
    
    period: Dict[str, Any] = Field(
        description="Time period information for filtering"
    ) 