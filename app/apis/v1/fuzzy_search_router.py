"""Fuzzy Search API router for patient document search."""

from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, Depends
from datetime import datetime

from app.apis.v1.types_in import (
    FuzzySearchParams,
    SuggestionSearchParams,
    validate_fuzzy_search_params,
    validate_suggestion_search_params
)
from app.apis.v1.types_out import (
    FuzzySearchResponse,
    SearchSuggestionsResponse,
    FuzzyDocumentMatch
)
from app.core.v1.fuzzy_search_manager import FuzzySearchManager
from app.core.v1.exceptions import DatabaseException
from app.core.v1.log_manager import LogManager

# Initialize router
router = APIRouter()

# Initialize components
fuzzy_search_manager = FuzzySearchManager()
logger = LogManager(__name__)


def get_fuzzy_search_params(
    search_term: str = Query(..., description="Patient name or partial name to search for"),
    user_id: Optional[str] = Query(None, description="Filter results by user ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    min_similarity: float = Query(0.3, ge=0.0, le=1.0, description="Minimum similarity score threshold"),
    include_score: bool = Query(True, description="Include similarity score in results")
) -> FuzzySearchParams:
    """Get and validate fuzzy search parameters."""
    return validate_fuzzy_search_params(
        search_term=search_term,
        user_id=user_id,
        limit=limit,
        skip=skip,
        min_similarity=min_similarity,
        include_score=include_score
    )


def get_suggestion_search_params(
    partial_term: str = Query(..., description="Partial patient name for suggestions"),
    user_id: Optional[str] = Query(None, description="Filter suggestions by user ID"),
    limit: int = Query(10, ge=1, le=50, description="Maximum number of suggestions")
) -> SuggestionSearchParams:
    """Get and validate suggestion search parameters."""
    return validate_suggestion_search_params(
        partial_term=partial_term,
        user_id=user_id,
        limit=limit
    )


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
    
    Args:
        params: Fuzzy search parameters including search term, filters, and options
    
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
    Get patient name suggestions based on partial input.
    
    This endpoint provides autocomplete suggestions for patient names based on
    partial input. It's designed to help users find the correct patient name
    by providing suggestions as they type.
    
    Args:
        params: Suggestion search parameters including partial term and filters
    
    Returns:
        SearchSuggestionsResponse: List of suggested patient names
    
    Examples:
        - Input "GAR" returns ["GARCIA, MARIA", "GARCIA LOPEZ, JUAN", "GARZA, PEDRO"]
        - Input "MAR" returns ["MARIA", "MARTINEZ", "MARQUEZ"]
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
    user_id: Optional[str] = Query(None, description="Filter results by user ID"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
):
    """
    Get all documents for a specific patient by exact name match.
    
    This endpoint finds all documents associated with a specific patient
    using exact name matching. It's useful when you know the exact patient name
    and want to retrieve all their documents.
    
    Args:
        patient_name: Exact patient name to search for
        user_id: Optional user filter
        limit: Maximum number of results
        skip: Number of results to skip
    
    Returns:
        FuzzySearchResponse: All documents for the specified patient
    """
    try:
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