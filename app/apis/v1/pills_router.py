"""Pills API router for managing pill templates (starter buttons)."""

import json
from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import JSONResponse
from datetime import datetime
from pydantic import ValidationError

from app.apis.v1.types_in import (
    PillCreateData,
    PillUpdateData,
    PillSearchParams,
    validate_pill_create_data,
    validate_pill_update_data,
    validate_pill_search_params
)
from app.apis.v1.types_out import (
    PillResponse,
    PillListResponse,
    PillDeleteResponse,
    PillCategoriesResponse
)
from app.core.v1.pills_manager import PillsManager
from app.core.v1.exceptions import (
    DatabaseException,
    ValidationException,
    PillNotFoundException,
    InvalidPillCategoryException,
    DuplicatePillPriorityException
)
from app.core.v1.log_manager import LogManager

# Initialize router
router = APIRouter()

# Initialize components
pills_manager = PillsManager()
logger = LogManager(__name__)


def get_pill_create_data(data: str) -> PillCreateData:
    """Parse and validate pill creation data from JSON string."""
    try:
        pill_data = json.loads(data) if isinstance(data, str) else data
        return validate_pill_create_data(pill_data)
    except (json.JSONDecodeError, ValidationError) as err:
        raise HTTPException(status_code=400, detail=f"Invalid pill data: {err}")


def get_pill_update_data(data: str) -> PillUpdateData:
    """Parse and validate pill update data from JSON string."""
    try:
        pill_data = json.loads(data) if isinstance(data, str) else data
        return validate_pill_update_data(pill_data)
    except (json.JSONDecodeError, ValidationError) as err:
        raise HTTPException(status_code=400, detail=f"Invalid pill update data: {err}")


def get_pill_search_params(
    category: Optional[str] = Query(None, description="Filter by category"),
    created_after: Optional[str] = Query(None, description="Filter by creation date (ISO format, after this date)"),
    created_before: Optional[str] = Query(None, description="Filter by creation date (ISO format, before this date)"),
    updated_after: Optional[str] = Query(None, description="Filter by update date (ISO format, after this date)"),
    updated_before: Optional[str] = Query(None, description="Filter by update date (ISO format, before this date)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination")
) -> PillSearchParams:
    """Get and validate pill search parameters."""
    try:
        return validate_pill_search_params(
            category=category,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            is_active=is_active,
            limit=limit,
            skip=skip
        )
    except ValidationError as err:
        raise HTTPException(status_code=400, detail=f"Invalid search parameters: {err}")


@router.post("/", response_model=PillResponse, status_code=201)
async def create_pill(pill_data: PillCreateData):
    """
    Create a new pill template.
    
    This endpoint creates a new pill template with starter text, content text,
    icon, category, and priority. The priority must be unique.
    
    Args:
        pill_data: Validated pill creation data
    
    Returns:
        PillResponse: Created pill information
        
    Raises:
        400 Bad Request: Invalid pill data or duplicate priority
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info(
            "Creating new pill",
            starter=pill_data.starter,
            category=pill_data.category,
            priority=pill_data.priority
        )
        
        # Create pill using manager
        result = pills_manager.create_pill({
            "starter": pill_data.starter,
            "text": pill_data.text,
            "icon": pill_data.icon,
            "category": pill_data.category,
            "priority": pill_data.priority
        })
        
        logger.info(
            "Pill created successfully",
            pill_id=result["pill_id"],
            starter=pill_data.starter,
            priority=pill_data.priority
        )
        
        return PillResponse(
            pill_id=result["pill_id"],
            starter=result["starter"],
            text=result["text"],
            icon=result["icon"],
            category=result["category"],
            priority=result["priority"],
            is_active=result["is_active"],
            created_at=result["created_at"].isoformat(),
            updated_at=result["updated_at"].isoformat()
        )
        
    except InvalidPillCategoryException as err:
        # Let specific pill exceptions bubble up to global handlers
        logger.info(f"🔍 DEBUG: Caught InvalidPillCategoryException: {err}")
        raise err
    except (DuplicatePillPriorityException, PillNotFoundException) as err:
        # Let other specific pill exceptions bubble up to global handlers  
        logger.info(f"🔍 DEBUG: Caught other specific pill exception: {type(err).__name__}: {err}")
        raise err
    except ValidationException as err:
        logger.warning(f"🔍 DEBUG: Caught ValidationException: {err}")
        logger.warning(f"Pill creation validation failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except DatabaseException as err:
        logger.error(f"🔍 DEBUG: Caught DatabaseException: {err}")
        logger.error(f"Pill creation database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"🔍 DEBUG: Caught generic Exception: {type(err).__name__}: {err}")
        logger.error(f"Unexpected error creating pill: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/", response_model=PillListResponse)
async def list_pills(params: PillSearchParams = Depends(get_pill_search_params)):
    """
    List pills with filtering and pagination.
    
    This endpoint provides comprehensive pill listing with filtering by category,
    date ranges, active status, and pagination support.
    
    Args:
        params: Validated search parameters
    
    Returns:
        PillListResponse: Paginated list of pills with metadata
        
    Raises:
        400 Bad Request: Invalid search parameters
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info(
            "Listing pills",
            category=params.category,
            is_active=params.is_active,
            limit=params.limit,
            skip=params.skip
        )
        
        # Parse date filters if provided
        date_filters = {}
        if params.created_after:
            try:
                date_filters["created_after"] = datetime.fromisoformat(params.created_after.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid created_after date format")
        
        if params.created_before:
            try:
                date_filters["created_before"] = datetime.fromisoformat(params.created_before.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid created_before date format")
        
        if params.updated_after:
            try:
                date_filters["updated_after"] = datetime.fromisoformat(params.updated_after.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid updated_after date format")
        
        if params.updated_before:
            try:
                date_filters["updated_before"] = datetime.fromisoformat(params.updated_before.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid updated_before date format")
        
        # Search pills using manager
        result = pills_manager.search_pills(
            category=params.category,
            is_active=params.is_active,
            limit=params.limit,
            skip=params.skip,
            **date_filters
        )
        
        # Format response
        pills_response = []
        for pill in result["pills"]:
            pills_response.append(PillResponse(
                pill_id=pill["pill_id"],
                starter=pill["starter"],
                text=pill["text"],
                icon=pill["icon"],
                category=pill["category"],
                priority=pill["priority"],
                is_active=pill["is_active"],
                created_at=pill["created_at"].isoformat(),
                updated_at=pill["updated_at"].isoformat()
            ))
        
        pagination = result["pagination"]
        
        logger.info(
            "Pills listed successfully",
            total_found=pagination["total"],
            returned_count=pagination["count"],
            limit=params.limit,
            skip=params.skip
        )
        
        return PillListResponse(
            pills=pills_response,
            pagination=pagination,
            total=pagination["total"],
            count=pagination["count"],
            limit=pagination["limit"],
            skip=pagination["skip"],
            has_next=pagination["has_next"],
            has_prev=pagination["has_prev"]
        )
        
    except ValidationException as err:
        logger.warning(f"Pills listing validation failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except DatabaseException as err:
        logger.error(f"Pills listing database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error listing pills: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/ordered", response_model=List[PillResponse])
async def get_pills_ordered(is_active: Optional[bool] = Query(True, description="Filter by active status")):
    """
    Get all pills ordered by priority.
    
    This is a convenience endpoint to get all pills in priority order,
    typically used for displaying in the UI.
    
    Args:
        is_active: Filter by active status (default: True)
    
    Returns:
        List[PillResponse]: List of pills ordered by priority
    """
    try:
        logger.info("Getting pills ordered by priority", is_active=is_active)
        
        pills = pills_manager.get_all_pills_ordered(is_active=is_active)
        
        pills_response = []
        for pill in pills:
            pills_response.append(PillResponse(
                pill_id=pill["pill_id"],
                starter=pill["starter"],
                text=pill["text"],
                icon=pill["icon"],
                category=pill["category"],
                priority=pill["priority"],
                is_active=pill["is_active"],
                created_at=pill["created_at"].isoformat(),
                updated_at=pill["updated_at"].isoformat()
            ))
        
        logger.info("Pills retrieved successfully", count=len(pills_response))
        
        return pills_response
        
    except DatabaseException as err:
        logger.error(f"Pills retrieval database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error retrieving pills: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/categories", response_model=PillCategoriesResponse)
async def get_valid_categories():
    """
    Get list of valid pill categories.
    
    Returns the list of valid categories that can be used when creating or updating pills.
    
    Returns:
        PillCategoriesResponse: List of valid categories
    """
    try:
        logger.info("Getting valid pill categories")
        
        categories = pills_manager.get_valid_categories()
        
        logger.info("Valid categories retrieved", count=len(categories))
        
        return PillCategoriesResponse(
            categories=categories,
            count=len(categories)
        )
        
    except Exception as err:
        logger.error(f"Unexpected error getting categories: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/{pill_id}", response_model=PillResponse)
async def get_pill(pill_id: str):
    """
    Get a specific pill by ID.
    
    Args:
        pill_id: Unique pill identifier
    
    Returns:
        PillResponse: Pill information
        
    Raises:
        404 Not Found: Pill not found
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info("Getting pill by ID", pill_id=pill_id)
        
        pill = pills_manager.get_pill(pill_id)
        
        if not pill:
            logger.info("Pill not found", pill_id=pill_id)
            raise HTTPException(status_code=404, detail="Pill not found")
        
        logger.info("Pill retrieved successfully", pill_id=pill_id)
        
        return PillResponse(
            pill_id=pill["pill_id"],
            starter=pill["starter"],
            text=pill["text"],
            icon=pill["icon"],
            category=pill["category"],
            priority=pill["priority"],
            is_active=pill["is_active"],
            created_at=pill["created_at"].isoformat(),
            updated_at=pill["updated_at"].isoformat()
        )
        
    except DatabaseException as err:
        logger.error(f"Pill retrieval database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error retrieving pill: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.put("/{pill_id}", response_model=PillResponse)
async def update_pill(pill_id: str, pill_data: PillUpdateData):
    """
    Update an existing pill.
    
    This endpoint allows updating any field of a pill. When updating priority,
    the new priority must be unique.
    
    Args:
        pill_id: Unique pill identifier
        pill_data: Validated pill update data
    
    Returns:
        PillResponse: Updated pill information
        
    Raises:
        400 Bad Request: Invalid update data or duplicate priority
        404 Not Found: Pill not found
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info("Updating pill", pill_id=pill_id)
        
        # Prepare update data (only include non-None fields)
        update_data = {}
        if pill_data.starter is not None:
            update_data["starter"] = pill_data.starter
        if pill_data.text is not None:
            update_data["text"] = pill_data.text
        if pill_data.icon is not None:
            update_data["icon"] = pill_data.icon
        if pill_data.category is not None:
            update_data["category"] = pill_data.category
        if pill_data.priority is not None:
            update_data["priority"] = pill_data.priority
        if pill_data.is_active is not None:
            update_data["is_active"] = pill_data.is_active
        
        if not update_data:
            raise HTTPException(status_code=400, detail="No update data provided")
        
        # Update pill using manager
        result = pills_manager.update_pill(pill_id, update_data)
        
        if not result:
            logger.info("Pill not found for update", pill_id=pill_id)
            raise HTTPException(status_code=404, detail="Pill not found")
        
        logger.info(
            "Pill updated successfully",
            pill_id=pill_id,
            updated_fields=list(update_data.keys())
        )
        
        return PillResponse(
            pill_id=result["pill_id"],
            starter=result["starter"],
            text=result["text"],
            icon=result["icon"],
            category=result["category"],
            priority=result["priority"],
            is_active=result["is_active"],
            created_at=result["created_at"].isoformat(),
            updated_at=result["updated_at"].isoformat()
        )
        
    except ValidationException as err:
        logger.warning(f"Pill update validation failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except DatabaseException as err:
        logger.error(f"Pill update database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error updating pill: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.delete("/{pill_id}", response_model=PillDeleteResponse)
async def delete_pill(pill_id: str):
    """
    Delete a pill.
    
    This permanently removes the pill from the database.
    
    Args:
        pill_id: Unique pill identifier
    
    Returns:
        PillDeleteResponse: Deletion result
        
    Raises:
        404 Not Found: Pill not found
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info("Deleting pill", pill_id=pill_id)
        
        success = pills_manager.delete_pill(pill_id)
        
        if success:
            logger.info("Pill deleted successfully", pill_id=pill_id)
            return PillDeleteResponse(
                pill_id=pill_id,
                success=True,
                message="Pill deleted successfully"
            )
        else:
            logger.info("Pill not found for deletion", pill_id=pill_id)
            raise HTTPException(status_code=404, detail="Pill not found")
        
    except DatabaseException as err:
        logger.error(f"Pill deletion database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error deleting pill: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}") 