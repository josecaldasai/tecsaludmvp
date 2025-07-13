"""Document processing API router."""

import json
import logging
from typing import List, Optional, Any
from fastapi import APIRouter, UploadFile, File, Form, HTTPException, Query, Depends


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
)
from app.core.v1.document_processor import DocumentProcessor
from app.core.v1.exceptions import (
    DocumentProcessorException
)
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


@router.get("/", response_model=List[DocumentInfoResponse])
async def list_documents(
    params: DocumentSearchParams = Depends(get_search_params)
):
    """
    List documents with optional filtering by user or batch.
    
    Args:
        params: Validated search parameters (user_id, batch_id, limit, skip)
    
    Returns:
        List[DocumentInfoResponse]: List of documents
    """
    try:
        logger.info(
            "Listing documents",
            user_id=params.user_id,
            batch_id=params.batch_id,
            limit=params.limit,
            skip=params.skip
        )
        
        # Build query
        query = {}
        if params.user_id:
            query["user_id"] = params.user_id
        if params.batch_id:
            query["batch_info.batch_id"] = params.batch_id
        
        # Execute search
        results = document_processor.search_documents(
            query=query,
            limit=params.limit,
            skip=params.skip
        )
        
        logger.info(
            "Documents listed successfully",
            total_found=results["total_found"],
            user_id=params.user_id,
            batch_id=params.batch_id
        )
        
        return results["documents"]
        
    except DocumentProcessorException as err:
        logger.error(f"Failed to list documents: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to list documents: {err}")
    except Exception as err:
        logger.error(f"Unexpected error listing documents: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/{document_id}", response_model=DocumentInfoResponse)
async def get_document_info(document_id: str):
    """
    Get information about a specific document.
    
    Args:
        document_id: Unique document identifier
    
    Returns:
        DocumentInfoResponse: Document information
    """
    try:
        logger.info(
            "Getting document info",
            document_id=document_id
        )
        
        document_info = document_processor.get_document_info(document_id)
        
        if not document_info:
            raise HTTPException(
                status_code=404,
                detail=f"Document with ID {document_id} not found"
            )
        
        logger.info(
            "Document info retrieved successfully",
            document_id=document_id
        )
        
        return DocumentInfoResponse(**document_info)
        
    except DocumentProcessorException as err:
        logger.error(f"Failed to get document info: {err}")
        raise HTTPException(status_code=500, detail=f"Failed to get document info: {err}")
    except Exception as err:
        logger.error(f"Unexpected error getting document info: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.delete("/{document_id}", response_model=DocumentDeleteResponse)
async def delete_document(document_id: str):
    """
    Delete a document completely.
    
    This removes the document from both MongoDB and Azure Storage.
    
    Args:
        document_id: Unique document identifier
    
    Returns:
        DocumentDeleteResponse: Deletion result
    """
    try:
        logger.info(
            "Starting document deletion",
            document_id=document_id
        )
        
        success = document_processor.delete_document(document_id)
        
        if success:
            message = "Document deleted successfully"
            logger.info(
                "Document deleted successfully",
                document_id=document_id
            )
        else:
            message = "Document not found"
            logger.warning(
                "Document not found for deletion",
                document_id=document_id
            )
        
        return DocumentDeleteResponse(
            document_id=document_id,
            success=success,
            message=message
        )
        
    except DocumentProcessorException as err:
        logger.error(f"Deletion failed: {err}")
        raise HTTPException(status_code=500, detail=f"Deletion failed: {err}")
    except Exception as err:
        logger.error(f"Unexpected error during deletion: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")
