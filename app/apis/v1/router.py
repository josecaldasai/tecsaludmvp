"""Document processing API router."""

import json
import logging
from typing import List, Optional, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends
from datetime import datetime

from app.apis.v1.types_in import (
    DocumentUploadData,
    BatchUploadData,
    DocumentSearchParams,
    validate_upload_data,
    validate_batch_upload_data,
    validate_search_params
)
from app.apis.v1.types_out import (
    DocumentUploadResponse,
    DocumentInfoResponse,
    BatchUploadResponse,
    DocumentDeleteResponse,
    DocumentSearchResponse,
)
from app.core.v1.document_processor import DocumentProcessor
from app.core.v1.exceptions import (
    DocumentProcessorException,
    DatabaseException,
    ValidationException
)
from app.core.v1.validators import DocumentValidator
from app.core.v1.log_manager import LogManager

# Initialize router
router = APIRouter()

# Initialize components
document_processor = DocumentProcessor()
logger = LogManager(__name__)


def get_upload_data(
    user_id: Optional[str] = Form(None, description="User ID who is uploading the document"),
    description: Optional[str] = Form(None, description="Document description"),
    tags: Optional[str] = Form(None, description="Document tags as JSON array")
) -> DocumentUploadData:
    return validate_upload_data(user_id, description, tags)


@router.post("/upload", response_model=DocumentUploadResponse, status_code=201)
async def upload_document(
    file: UploadFile = File(..., description="Document file to upload"),
    data: DocumentUploadData = Depends(get_upload_data)
):
    """
    Upload a single document for processing.
    
    This endpoint accepts a file upload and processes it through the complete workflow:
    1. Upload to Azure Storage
    2. Perform OCR using Azure Document Intelligence
    3. Store extracted text and information in MongoDB
    
    Args:
        file: Document file to upload
        data: Validated upload data (user_id, description, tags)
    
    Returns:
        DocumentUploadResponse: Processing results
    """
    try:
        logger.info(
            "Starting document upload",
            filename=file.filename,
            content_type=file.content_type,
            user_id=data.user_id
        )
        
        # Read file content
        file_content = await file.read()
        
        # Process document (tags are already parsed by the validator)
        result = document_processor.process_single_document(
            file_content=file_content,
            filename=file.filename,
            description=data.description,
            tags=data.tags,
            user_id=data.user_id
        )
        
        logger.info(
            "Document upload completed successfully",
            document_id=result["document_id"],
            filename=file.filename,
            user_id=data.user_id
        )
        
        return DocumentUploadResponse(**result)
        
    except DocumentProcessorException as err:
        logger.error(f"Document processing failed: {err}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {err}")
    except Exception as err:
        logger.error(f"Unexpected error during upload: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


def get_batch_upload_data(
    user_id: Optional[str] = Form(None, description="User ID who is uploading the documents"),
    batch_description: Optional[str] = Form(None, description="Common description for all documents"),
    batch_tags: Optional[str] = Form(None, description="Common tags as JSON array")
) -> BatchUploadData:
    return validate_batch_upload_data(user_id, batch_description, batch_tags)


@router.post("/upload/batch", response_model=BatchUploadResponse, status_code=201)
async def upload_documents_batch(
    files: List[UploadFile] = File(..., description="List of files to upload"),
    data: BatchUploadData = Depends(get_batch_upload_data)
):
    """
    Upload multiple documents for batch processing.
    
    This endpoint processes multiple files in a batch operation with optimized error handling.
    Each file goes through the same processing workflow as single upload but errors are handled individually.
    
    Args:
        files: List of document files to upload
        data: Validated batch upload data (user_id, batch_description, batch_tags)
    
    Returns:
        BatchUploadResponse: Batch processing results with success/failure breakdown
    """
    try:
        logger.info(
            "Starting batch document upload",
            file_count=len(files),
            user_id=data.user_id,
            batch_description=data.batch_description
        )
        
        # Prepare files for batch processing
        files_to_process = []
        for index, file in enumerate(files):
            try:
                file_content = await file.read()
                files_to_process.append({
                    "content": file_content,
                    "filename": file.filename,
                    "description": data.batch_description,
                    "tags": data.batch_tags or [],
                    "user_id": data.user_id,
                    "batch_index": index
                })
            except Exception as err:
                logger.error(
                    "Failed to read file content",
                    filename=file.filename,
                    error=str(err)
                )
                # Continue with other files even if one fails to read
                continue
        
        # Process batch
        result = document_processor.process_batch_documents_optimized(
            files=files_to_process,
            batch_description=data.batch_description,
            batch_tags=data.batch_tags,
            user_id=data.user_id
        )
        
        logger.info(
            "Batch upload completed",
            batch_id=result["batch_id"],
            processed_count=result["processed_count"],
            failed_count=result["failed_count"],
            user_id=data.user_id
        )
        
        return BatchUploadResponse(**result)
        
    except DocumentProcessorException as err:
        logger.error(f"Batch processing failed: {err}")
        raise HTTPException(status_code=500, detail=f"Batch processing failed: {err}")
    except Exception as err:
        logger.error(f"Unexpected error during batch upload: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")



def get_search_params(
    user_id: Optional[str] = Query(None, description="Filter documents by user ID"),
    batch_id: Optional[str] = Query(None, description="Filter documents by batch ID"),
    limit: int = Query(10, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
) -> DocumentSearchParams:
    return validate_search_params(user_id, batch_id, limit, skip)


@router.get("/", response_model=DocumentSearchResponse)
async def list_documents(
    params: DocumentSearchParams = Depends(get_search_params)
):
    """
    List documents with optional filtering by user or batch.
    
    This endpoint provides comprehensive document listing with enhanced pagination,
    filtering capabilities, and specific error handling.
    
    Args:
        params: Validated search parameters (user_id, batch_id, limit, skip)
    
    Returns:
        DocumentSearchResponse: Paginated list of documents with metadata
        
    Raises:
        400 Bad Request: Invalid search parameters (e.g., invalid UUID for batch_id)
        503 Service Unavailable: Database connection issues
    """
    # Generate request ID for tracking
    request_id = f"list_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{params.limit}_{params.skip}"
    search_timestamp = datetime.now().isoformat()
    
    try:
        logger.info(
            "Starting document listing",
            request_id=request_id,
            user_id=params.user_id,
            batch_id=params.batch_id,
            limit=params.limit,
            skip=params.skip
        )
        
        # Build query filters
        query = {}
        applied_filters = {}
        
        if params.user_id:
            query["user_id"] = params.user_id
            applied_filters["user_id"] = params.user_id
            
        if params.batch_id:
            query["batch_info.batch_id"] = params.batch_id
            applied_filters["batch_id"] = params.batch_id
        
        # Log applied filters
        logger.info(
            "Applying search filters",
            request_id=request_id,
            applied_filters=applied_filters,
            total_filters=len(applied_filters)
        )
        
        # Execute search with error handling
        try:
            results = document_processor.search_documents(
                query=query,
                limit=params.limit,
                skip=params.skip
            )
            
        except DatabaseException as err:
            # Database connectivity or query issues
            logger.error(
                "Database error during document listing",
                request_id=request_id,
                applied_filters=applied_filters,
                error=str(err)
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "DATABASE_SERVICE_UNAVAILABLE",
                    "message": "Database service is temporarily unavailable",
                    "request_id": request_id,
                    "suggestion": "Please try again in a few moments"
                }
            )
            
        except DocumentProcessorException as err:
            # Document processing specific error
            logger.error(
                "Document processor error during listing",
                request_id=request_id,
                applied_filters=applied_filters,
                error=str(err)
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error_code": "DOCUMENT_PROCESSING_ERROR",
                    "message": f"Failed to process document search: {str(err)}",
                    "request_id": request_id,
                    "suggestion": "Please try again or contact support if the issue persists"
                }
            )
        
        # Calculate pagination metadata
        total_found = results["total_found"]
        returned_count = len(results["documents"])
        current_page = (params.skip // params.limit) + 1
        total_pages = (total_found + params.limit - 1) // params.limit if total_found > 0 else 1
        has_next = (params.skip + params.limit) < total_found
        has_prev = params.skip > 0
        
        logger.info(
            "Document listing completed successfully",
            request_id=request_id,
            total_found=total_found,
            returned_count=returned_count,
            current_page=current_page,
            total_pages=total_pages,
            has_next=has_next,
            has_prev=has_prev,
            applied_filters=applied_filters
        )
        
        # Build comprehensive response
        return DocumentSearchResponse(
            documents=results["documents"],
            total_found=total_found,
            limit=params.limit,
            skip=params.skip,
            returned_count=returned_count,
            has_next=has_next,
            has_prev=has_prev,
            current_page=current_page,
            total_pages=total_pages,
            applied_filters=applied_filters,
            request_id=request_id,
            search_timestamp=search_timestamp
        )
        
    except HTTPException:
        # Re-raise HTTP exceptions (already handled above)
        raise
    except Exception as err:
        # Unexpected error - log and return generic error
        logger.error(
            "Unexpected error during document listing",
            request_id=request_id,
            user_id=params.user_id,
            batch_id=params.batch_id,
            error=str(err)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during document listing",
                "request_id": request_id,
                "suggestion": "Please try again or contact support if the issue persists"
            }
        )


@router.get("/{document_id}", response_model=DocumentInfoResponse)
async def get_document_info(document_id: str):
    """
    Get information about a specific document.
    
    This endpoint retrieves detailed information about a document by its ID.
    It includes comprehensive validation and specific error handling.
    
    Args:
        document_id: Unique document identifier (MongoDB ObjectId format)
    
    Returns:
        DocumentInfoResponse: Complete document information
        
    Raises:
        400 Bad Request: Invalid document ID format
        404 Not Found: Document not found
        503 Service Unavailable: Database connection issues
    """
    # Generate request ID for tracking
    request_id = f"get_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{document_id[:8]}"
    
    try:
        logger.info(
            "Starting document info retrieval",
            request_id=request_id,
            document_id=document_id
        )
        
        # Step 1: Validate document ID format
        try:
            validated_document_id = DocumentValidator.validate_document_id(document_id)
        except ValidationException as err:
            logger.warning(
                "Invalid document ID format provided",
                request_id=request_id,
                document_id=document_id,
                error=str(err)
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_DOCUMENT_ID_FORMAT",
                    "message": str(err),
                    "request_id": request_id,
                    "provided_id": document_id,
                    "expected_format": "24 hexadecimal characters (MongoDB ObjectId)"
                }
            )
        
        # Step 2: Retrieve document from database
        try:
            document_info = document_processor.get_document_info(validated_document_id)
            
            logger.info(
                "Document info retrieved successfully",
                request_id=request_id,
                document_id=validated_document_id,
                filename=document_info.get("filename"),
                processing_status=document_info.get("processing_status")
            )
            
            return DocumentInfoResponse(**document_info)
            
        except DocumentProcessorException as err:
            # Document not found (most common case)
            logger.info(
                "Document not found",
                request_id=request_id,
                document_id=validated_document_id,
                error=str(err)
            )
            raise HTTPException(
                status_code=404,
                detail={
                    "error_code": "DOCUMENT_NOT_FOUND",
                    "message": f"Document with ID '{validated_document_id}' does not exist",
                    "request_id": request_id,
                    "document_id": validated_document_id,
                    "suggestion": "Verify the document ID and ensure the document has not been deleted"
                }
            )
            
        except DatabaseException as err:
            # Database connectivity or query issues
            logger.error(
                "Database error during document retrieval",
                request_id=request_id,
                document_id=validated_document_id,
                error=str(err)
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "DATABASE_SERVICE_UNAVAILABLE",
                    "message": "Database service is temporarily unavailable",
                    "request_id": request_id,
                    "suggestion": "Please try again in a few moments"
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions (already handled above)
        raise
        
    except Exception as err:
        # Unexpected errors
        logger.error(
            "Unexpected error during document retrieval",
            request_id=request_id,
            document_id=document_id,
            error=str(err),
            error_type=type(err).__name__
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred",
                "request_id": request_id,
                "suggestion": "Please contact support if this error persists"
            }
        )


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(document_id: str):
    """
    Delete a document completely.
    
    This removes the document from both MongoDB and Azure Storage.
    It includes comprehensive validation and specific error handling.
    
    Args:
        document_id: Unique document identifier (MongoDB ObjectId format)
    
    Returns:
        DocumentDeleteResponse: Deletion result
        
    Raises:
        400 Bad Request: Invalid document ID format
        404 Not Found: Document not found
        503 Service Unavailable: Database connection issues
    """
    # Generate request ID for tracking
    request_id = f"del_doc_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{document_id[:8]}"
    
    try:
        logger.info(
            "Starting document deletion",
            request_id=request_id,
            document_id=document_id
        )
        
        # Step 1: Validate document ID format
        try:
            validated_document_id = DocumentValidator.validate_document_id(document_id)
        except ValidationException as err:
            logger.warning(
                "Invalid document ID format provided for deletion",
                request_id=request_id,
                document_id=document_id,
                error=str(err)
            )
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_DOCUMENT_ID_FORMAT",
                    "message": str(err),
                    "request_id": request_id,
                    "provided_id": document_id,
                    "expected_format": "24 hexadecimal characters (MongoDB ObjectId)",
                    "suggestion": "Ensure you're using a valid MongoDB ObjectId format"
                }
            )
        
        # Step 2: Delete document
        try:
            success = document_processor.delete_document(validated_document_id)
            
            if success:
                logger.info(
                    "Document deleted successfully",
                    request_id=request_id,
                    document_id=validated_document_id
                )
                
                return DocumentDeleteResponse(
                    document_id=validated_document_id,
                    success=True,
                    message="Document deleted successfully"
                )
            else:
                # Document not found - return 404 instead of success=false
                logger.info(
                    "Document not found for deletion",
                    request_id=request_id,
                    document_id=validated_document_id
                )
                raise HTTPException(
                    status_code=404,
                    detail={
                        "error_code": "DOCUMENT_NOT_FOUND",
                        "message": f"Document with ID '{validated_document_id}' does not exist or has already been deleted",
                        "request_id": request_id,
                        "document_id": validated_document_id,
                        "suggestion": "Verify the document ID and ensure the document exists"
                    }
                )
                
        except DocumentProcessorException as err:
            # Document-specific processing error
            logger.error(
                "Document processing error during deletion",
                request_id=request_id,
                document_id=validated_document_id,
                error=str(err)
            )
            raise HTTPException(
                status_code=500,
                detail={
                    "error_code": "DOCUMENT_PROCESSING_ERROR",
                    "message": f"Failed to process document deletion: {str(err)}",
                    "request_id": request_id,
                    "suggestion": "Please try again in a few moments"
                }
            )
            
        except DatabaseException as err:
            # Database connectivity or query issues
            logger.error(
                "Database error during document deletion",
                request_id=request_id,
                document_id=validated_document_id,
                error=str(err)
            )
            raise HTTPException(
                status_code=503,
                detail={
                    "error_code": "DATABASE_SERVICE_UNAVAILABLE",
                    "message": "Database service is temporarily unavailable",
                    "request_id": request_id,
                    "suggestion": "Please try again in a few moments"
                }
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions (already handled above)
        raise
    except Exception as err:
        # Unexpected error - log and return generic error
        logger.error(
            "Unexpected error during document deletion",
            request_id=request_id,
            document_id=document_id,
            error=str(err)
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during document deletion",
                "request_id": request_id,
                "suggestion": "Please try again or contact support if the issue persists"
            }
        )
