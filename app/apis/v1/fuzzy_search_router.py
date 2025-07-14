"""Fuzzy Search API router for patient document search."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime
from pydantic import ValidationError

from app.apis.v1.types_in import (
    FuzzySearchParams,
    SuggestionSearchParams,
    PatientDocumentSearchParams,
    validate_fuzzy_search_params,
    validate_suggestion_search_params,
    validate_patient_document_search_params
)
from app.apis.v1.types_out import (
    FuzzySearchResponse,
    SearchSuggestionsResponse,
    FuzzyDocumentMatch
)
from app.core.v1.fuzzy_search_manager import FuzzySearchManager
from app.core.v1.exceptions import (
    DatabaseException,
    UserIdRequiredException,
    InvalidUserIdException
)
from app.core.v1.log_manager import LogManager

# Initialize router
router = APIRouter()

# Initialize components
fuzzy_search_manager = FuzzySearchManager()
logger = LogManager(__name__)


def handle_userid_validation_error(error: ValidationError, request_id: str = None) -> HTTPException:
    """
    Handle user_id validation errors and convert them to custom exceptions.
    
    Args:
        error: ValidationError from Pydantic
        request_id: Optional request ID for tracking
        
    Returns:
        HTTPException with appropriate status code and custom error message
    """
    for error_detail in error.errors():
        if error_detail.get('loc') == ('user_id',) or 'user_id' in str(error_detail.get('loc', [])):
            error_type = error_detail.get('type', '')
            error_msg = error_detail.get('msg', '')
            
            if error_type == 'missing':
                logger.error(
                    "User ID is required but not provided",
                    request_id=request_id,
                    error_type=error_type,
                    error_msg=error_msg
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "USER_ID_REQUIRED",
                        "message": "User ID is required for this operation. Please provide a valid user_id parameter.",
                        "request_id": request_id,
                        "suggestion": "Add user_id parameter to your request (e.g., ?user_id=your_user_id)"
                    }
                )
            
            elif error_type == 'string_too_short' or 'empty' in error_msg.lower():
                logger.error(
                    "User ID is empty or too short",
                    request_id=request_id,
                    error_type=error_type,
                    error_msg=error_msg
                )
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error_code": "INVALID_USER_ID",
                        "message": "User ID cannot be empty. Please provide a valid user_id parameter.",
                        "request_id": request_id,
                        "suggestion": "Ensure user_id has at least 1 character (e.g., ?user_id=your_user_id)"
                    }
                )
    
    # If it's not a user_id error, re-raise the original ValidationError
    raise HTTPException(
        status_code=422,
        detail={
            "error_code": "VALIDATION_ERROR",
            "message": f"Request validation failed: {str(error)}",
            "request_id": request_id,
            "suggestion": "Please check your request parameters and try again"
        }
    )


def get_fuzzy_search_params(
    search_term: str = Query(..., description="Patient name or partial name to search for"),
    user_id: str = Query(..., min_length=1, description="Filter results by user ID (required)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity score threshold"),
    include_score: bool = Query(True, description="Include similarity score in results")
) -> FuzzySearchParams:
    """Get and validate fuzzy search parameters."""
    try:
        return validate_fuzzy_search_params(
            search_term=search_term,
            user_id=user_id,
            limit=limit,
            skip=skip,
            min_similarity=min_similarity,
            include_score=include_score
        )
    except ValidationError as e:
        handle_userid_validation_error(e, f"fuzzy_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    except ValueError as e:
        if "user_id" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_USER_ID",
                    "message": f"Invalid user_id: {str(e)}",
                    "request_id": f"fuzzy_search_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "suggestion": "Please provide a valid user_id parameter"
                }
            )
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")


def get_suggestion_search_params(
    partial_term: str = Query(..., description="Partial patient name for suggestions"),
    user_id: str = Query(..., min_length=1, description="Filter suggestions by user ID (required)"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions")
) -> SuggestionSearchParams:
    """Get and validate suggestion search parameters."""
    try:
        return validate_suggestion_search_params(
            partial_term=partial_term,
            user_id=user_id,
            limit=limit
        )
    except ValidationError as e:
        handle_userid_validation_error(e, f"suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    except ValueError as e:
        if "user_id" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_USER_ID",
                    "message": f"Invalid user_id: {str(e)}",
                    "request_id": f"suggestions_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "suggestion": "Please provide a valid user_id parameter"
                }
            )
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")


def get_patient_document_search_params(
    patient_name: str,
    user_id: str = Query(..., description="Filter results by user ID (required)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
) -> PatientDocumentSearchParams:
    """Get and validate patient document search parameters."""
    try:
        return validate_patient_document_search_params(
            patient_name=patient_name,
            user_id=user_id,
            limit=limit,
            skip=skip
        )
    except ValidationError as e:
        handle_userid_validation_error(e, f"patient_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
    except ValueError as e:
        if "user_id" in str(e).lower():
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_USER_ID",
                    "message": f"Invalid user_id: {str(e)}",
                    "request_id": f"patient_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "suggestion": "Please provide a valid user_id parameter"
                }
            )
        raise HTTPException(status_code=400, detail=f"Validation error: {str(e)}")


@router.get("/patients", response_model=FuzzySearchResponse)
async def search_patients_by_name(
    params: FuzzySearchParams = Depends(get_fuzzy_search_params)
):
    """
    Search for documents by patient name using fuzzy matching.
    
    This endpoint implements advanced fuzzy search algorithms to find patient documents
    based on partial or complete patient names. It supports:
    
    - Exact matches
    - Prefix matches (names starting with search term)
    - Substring matches (names containing search term)
    - Fuzzy similarity matching
    - MongoDB text search
    
    The user_id parameter is required to ensure users can only search within their own documents.
    
    Args:
        params: Fuzzy search parameters including search term, user_id (required), filters, and options
    
    Returns:
        FuzzySearchResponse: Matched documents with similarity scores and metadata
    
    Examples:
        - Search for "GARCIA" finds "GARCIA, MARIA" and "GARCIA LOPEZ, JUAN"
        - Search for "MAR" finds "MARIA", "MARTINEZ", "MARQUEZ"
        - Search for "PEDRO JAV" finds "PEDRO JAVIER"
    """
    try:
        logger.info(
            "Processing fuzzy patient search request",
            search_term=params.search_term,
            user_id=params.user_id,
            limit=params.limit,
            min_similarity=params.min_similarity
        )
        
        # Perform fuzzy search
        search_results = fuzzy_search_manager.search_patients_by_name(
            search_term=params.search_term,
            user_id=params.user_id,
            limit=params.limit,
            skip=params.skip,
            include_score=params.include_score
        )
        
        # Convert documents to response format
        fuzzy_documents = []
        for doc in search_results["documents"]:
            fuzzy_doc = FuzzyDocumentMatch(
                document_id=doc["_id"],
                processing_id=doc.get("processing_id", ""),
                filename=doc.get("filename", ""),
                content_type=doc.get("content_type", ""),
                file_size=doc.get("file_size", 0),
                user_id=doc.get("user_id"),
                storage_info=doc.get("storage_info", {}),
                extracted_text=doc.get("extracted_text", ""),
                processing_status=doc.get("processing_status", ""),
                batch_info=doc.get("batch_info"),
                description=doc.get("description"),
                tags=doc.get("tags", []),
                expediente=doc.get("expediente"),
                nombre_paciente=doc.get("nombre_paciente"),
                numero_episodio=doc.get("numero_episodio"),
                categoria=doc.get("categoria"),
                medical_info_valid=doc.get("medical_info_valid"),
                medical_info_error=doc.get("medical_info_error"),
                created_at=doc.get("created_at", datetime.now()),
                updated_at=doc.get("updated_at", datetime.now()),
                similarity_score=doc.get("similarity_score", 0.0),
                match_type=doc.get("match_type", "unknown")
            )
            fuzzy_documents.append(fuzzy_doc)
        
        # Create response
        response = FuzzySearchResponse(
            search_term=search_results["search_term"],
            normalized_term=search_results["normalized_term"],
            total_found=search_results["total_found"],
            documents=fuzzy_documents,
            limit=search_results["limit"],
            skip=search_results["skip"],
            search_strategies_used=search_results["search_strategies_used"],
            min_similarity_threshold=search_results["min_similarity_threshold"],
            search_timestamp=search_results["search_timestamp"]
        )
        
        logger.info(
            "Fuzzy search completed successfully",
            search_term=params.search_term,
            total_found=response.total_found,
            returned_count=len(response.documents)
        )
        
        return response
        
    except DatabaseException as err:
        logger.error(f"Database error in fuzzy search: {err}")
        raise HTTPException(status_code=500, detail=f"Search failed: {err}")
    except Exception as err:
        logger.error(f"Unexpected error in fuzzy search: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/patients/suggestions", response_model=SearchSuggestionsResponse)
async def get_patient_name_suggestions(
    params: SuggestionSearchParams = Depends(get_suggestion_search_params)
):
    """
    Get patient name suggestions for autocomplete functionality.
    
    This endpoint provides intelligent autocomplete suggestions for patient names
    based on a partial search term. It's optimized for fast real-time suggestions
    and implements smart fuzzy matching to handle typos and partial matches.
    
    The user_id parameter is required to ensure users can only get suggestions
    from their own documents.
    
    Args:
        params: Suggestion search parameters including partial_term, user_id (required), and limit
    
    Returns:
        SearchSuggestionsResponse: List of suggested patient names with metadata
    
    Examples:
        - "MAR" might suggest: ["MARÍA GONZÁLEZ", "MARIO RODRÍGUEZ", "MARTHA LÓPEZ"]
        - "GARC" might suggest: ["GARCÍA, JUAN", "GARCÍA LÓPEZ, MARÍA"]
    """
    try:
        logger.info(
            "Processing patient name suggestions request",
            partial_term=params.partial_term,
            user_id=params.user_id,
            limit=params.limit
        )
        
        # Get suggestions
        suggestions = fuzzy_search_manager.get_search_suggestions(
            partial_term=params.partial_term,
            user_id=params.user_id,
            limit=params.limit
        )
        
        # Create response
        response = SearchSuggestionsResponse(
            partial_term=params.partial_term,
            suggestions=suggestions,
            total_suggestions=len(suggestions),
            limit=params.limit
        )
        
        logger.info(
            "Patient name suggestions completed successfully",
            partial_term=params.partial_term,
            total_suggestions=response.total_suggestions
        )
        
        return response
        
    except DatabaseException as err:
        logger.error(f"Database error in suggestions: {err}")
        raise HTTPException(status_code=500, detail=f"Suggestions failed: {err}")
    except Exception as err:
        logger.error(f"Unexpected error in suggestions: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/patients/{patient_name}/documents", response_model=FuzzySearchResponse)
async def get_documents_by_patient_name(
    patient_name: str,
    user_id: str = Query(..., min_length=1, description="Filter results by user ID (required)"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Get all documents for a specific patient by exact name match.
    
    This endpoint finds all documents associated with a specific patient
    using exact name matching. It's useful when you know the exact patient name
    and want to retrieve all their documents.
    
    The user_id parameter is required to ensure users can only see documents
    from their own account.
    
    Args:
        patient_name: Exact patient name to search for
        user_id: User ID to filter results (required)
        limit: Maximum number of results
        skip: Number of results to skip
    
    Returns:
        FuzzySearchResponse: All documents for the specified patient
    """
    try:
        # Validate user_id if it's empty or None
        if not user_id or user_id.strip() == "":
            raise HTTPException(
                status_code=400,
                detail={
                    "error_code": "INVALID_USER_ID",
                    "message": "User ID cannot be empty. Please provide a valid user_id parameter.",
                    "request_id": f"patient_docs_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    "suggestion": "Ensure user_id has at least 1 character (e.g., ?user_id=your_user_id)"
                }
            )
        
        logger.info(
            "Processing exact patient name search",
            patient_name=patient_name,
            user_id=user_id,
            limit=limit,
            skip=skip
        )
        
        # Use fuzzy search with exact match (will get high similarity score)
        search_results = fuzzy_search_manager.search_patients_by_name(
            search_term=patient_name,
            user_id=user_id,
            limit=limit,
            skip=skip,
            include_score=True
        )
        
        # Filter for exact or very high similarity matches
        exact_matches = [
            doc for doc in search_results["documents"]
            if doc.get("similarity_score", 0.0) >= 0.9
        ]
        
        # Convert documents to response format
        fuzzy_documents = []
        for doc in exact_matches:
            fuzzy_doc = FuzzyDocumentMatch(
                document_id=doc["_id"],
                processing_id=doc.get("processing_id", ""),
                filename=doc.get("filename", ""),
                content_type=doc.get("content_type", ""),
                file_size=doc.get("file_size", 0),
                user_id=doc.get("user_id"),
                storage_info=doc.get("storage_info", {}),
                extracted_text=doc.get("extracted_text", ""),
                processing_status=doc.get("processing_status", ""),
                batch_info=doc.get("batch_info"),
                description=doc.get("description"),
                tags=doc.get("tags", []),
                expediente=doc.get("expediente"),
                nombre_paciente=doc.get("nombre_paciente"),
                numero_episodio=doc.get("numero_episodio"),
                categoria=doc.get("categoria"),
                medical_info_valid=doc.get("medical_info_valid"),
                medical_info_error=doc.get("medical_info_error"),
                created_at=doc.get("created_at", datetime.now()),
                updated_at=doc.get("updated_at", datetime.now()),
                similarity_score=doc.get("similarity_score", 0.0),
                match_type=doc.get("match_type", "unknown")
            )
            fuzzy_documents.append(fuzzy_doc)
        
        # Update search results with filtered documents
        search_results["documents"] = exact_matches
        search_results["total_found"] = len(exact_matches)
        
        # Create response
        response = FuzzySearchResponse(
            search_term=patient_name,
            normalized_term=search_results["normalized_term"],
            total_found=len(exact_matches),
            documents=fuzzy_documents,
            limit=limit,
            skip=skip,
            search_strategies_used=["exact_match"],
            min_similarity_threshold=0.9,
            search_timestamp=datetime.now().isoformat()
        )
        
        logger.info(
            "Exact patient name search completed successfully",
            patient_name=patient_name,
            total_found=response.total_found
        )
        
        return response
        
    except DatabaseException as err:
        logger.error(f"Database error in exact patient search: {err}")
        raise HTTPException(status_code=500, detail=f"Search failed: {err}")
    except Exception as err:
        logger.error(f"Unexpected error in exact patient search: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}") 