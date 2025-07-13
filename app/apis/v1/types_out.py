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
    """Response schema for document search."""
    
    total_found: int = Field(
        description="Total number of documents found"
    )
    
    documents: List[DocumentInfoResponse] = Field(
        description="List of matching documents"
    )
    
    limit: int = Field(
        description="Maximum number of results requested"
    )
    
    skip: int = Field(
        description="Number of results skipped"
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