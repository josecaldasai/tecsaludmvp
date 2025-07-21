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
    PillCategoriesResponse,
    PillPrioritiesResponse
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
        raise HTTPException(status_code=400, detail=f"Invalid pill data: {err}")


def get_pill_search_params(
    category: Optional[str] = None,
    created_after: Optional[str] = None,
    created_before: Optional[str] = None,
    updated_after: Optional[str] = None,
    updated_before: Optional[str] = None,
    is_active: Optional[bool] = None,
    limit: int = 100,
    skip: int = 0
) -> PillSearchParams:
    """Parse and validate pill search parameters."""
    try:
        return PillSearchParams(
            category=category,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            is_active=is_active,
            limit=limit,
            skip=skip
        )
    except Exception as err:
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
        logger.info(f"Invalid category error: {err}")
        raise err
    except (DuplicatePillPriorityException, PillNotFoundException) as err:
        # Let other specific pill exceptions bubble up to global handlers  
        logger.info(f"Caught specific pill exception: {type(err).__name__}: {err}")
        raise err
    except ValidationException as err:
        logger.warning(f"Pill creation validation failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except DatabaseException as err:
        logger.error(f"Pill creation database error: {err}")
        
        # Check if it's a duplicate key error and provide more helpful message
        error_message = str(err)
        if "duplicate key" in error_message.lower() or "e11000" in error_message.lower():
            logger.error(
                "Duplicate key error detected during pill creation",
                starter=pill_data.starter,
                category=pill_data.category,
                priority=pill_data.priority,
                error_details=error_message
            )
            raise HTTPException(
                status_code=409,  # Conflict instead of 500
                detail={
                    "error_code": "PILL_CREATION_CONFLICT",
                    "message": "Unable to create pill due to a database conflict. This may be due to concurrent requests or internal ID conflicts.",
                    "suggestion": "Please try again in a moment. If the problem persists, contact support.",
                    "retry_recommended": True,
                    "pill_data": {
                        "starter": pill_data.starter,
                        "category": pill_data.category,
                        "priority": pill_data.priority
                    }
                }
            )
        else:
            # Other database errors
            raise HTTPException(
                status_code=503,  # Service Unavailable
                detail={
                    "error_code": "DATABASE_SERVICE_ERROR", 
                    "message": "Database service is temporarily unavailable",
                    "suggestion": "Please try again in a few moments",
                    "retry_recommended": True
                }
            )
    except Exception as err:
        logger.error(f"Unexpected error creating pill: {err}")
        logger.error(f"Error type: {type(err).__name__}")
        logger.error(f"Error args: {err.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(
            status_code=500, 
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred while creating the pill",
                "suggestion": "Please try again or contact support if the issue persists",
                "retry_recommended": True
            }
        )


@router.get("/ordered", response_model=List[PillResponse])
async def get_pills_ordered(
    is_active: Optional[bool] = Query(True, description="Filter by active status")
):
    """
    Get all pills ordered by priority.
    
    Retrieves all pills ordered by priority (1 = highest priority).
    Useful for displaying pills in the correct order.
    
    Args:
        is_active: Filter by active status (default: True)
    
    Returns:
        List[PillResponse]: Pills ordered by priority
        
    Raises:
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info("Getting pills ordered by priority", is_active=is_active)
        
        pills = pills_manager.get_all_pills_ordered(is_active=is_active)
        
        # Convert to response format
        result = []
        for pill in pills:
            result.append(PillResponse(
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
        
        logger.info(
            "Pills ordered retrieved successfully",
            count=len(result),
            is_active_filter=is_active
        )
        
        return result
        
    except DatabaseException as err:
        logger.error(f"Pills ordered database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error getting pills ordered: {err}")
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


@router.get("/priorities", response_model=PillPrioritiesResponse)
async def get_pill_priorities():
    """
    Get available pill priority levels.
    
    Returns all available priority levels with their descriptions.
    
    Returns:
        PillPrioritiesResponse: Available priority levels and descriptions
    """
    try:
        logger.info("Getting available pill priorities")
        
        priorities = pills_manager.get_valid_priorities()
        descriptions = pills_manager.get_priority_descriptions()
        
        logger.info(
            "Pill priorities retrieved successfully",
            priorities_count=len(priorities)
        )
        
        return PillPrioritiesResponse(
            priorities=priorities,
            description=descriptions
        )
        
    except Exception as err:
        logger.error(f"Unexpected error getting pill priorities: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/categories", response_model=PillCategoriesResponse)
async def get_pill_categories():
    """
    Get available pill categories.
    
    Returns all available pill categories for organization.
    
    Returns:
        PillCategoriesResponse: Available categories
    """
    try:
        logger.info("Getting available pill categories")
        
        categories = pills_manager.get_valid_categories()
        
        logger.info(
            "Pill categories retrieved successfully",
            categories_count=len(categories)
        )
        
        return PillCategoriesResponse(
            categories=categories,
            count=len(categories)
        )
        
    except Exception as err:
        logger.error(f"Unexpected error getting pill categories: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/{pill_id}", response_model=PillResponse)
async def get_pill(pill_id: str):
    """
    Get a specific pill by ID.
    
    Retrieves detailed information about a specific pill template.
    
    Args:
        pill_id: Unique pill identifier
    
    Returns:
        PillResponse: Pill information
        
    Raises:
        404 Not Found: Pill not found
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info("Getting pill", pill_id=pill_id)
        
        pill = pills_manager.get_pill(pill_id)
        
        if pill:
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
        else:
            logger.info("Pill not found", pill_id=pill_id)
            raise HTTPException(status_code=404, detail="Pill not found")
        
    except DatabaseException as err:
        logger.error(f"Pill retrieval database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error getting pill: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.put("/{pill_id}", response_model=PillResponse)
async def update_pill(pill_id: str, pill_data: PillUpdateData):
    """
    Update a pill template.
    
    Updates an existing pill template with new information. Only provided
    fields will be updated.
    
    Args:
        pill_id: Unique pill identifier
        pill_data: Updated pill data
    
    Returns:
        PillResponse: Updated pill information
        
    Raises:
        400 Bad Request: Invalid pill data or duplicate priority
        404 Not Found: Pill not found
        500 Internal Server Error: Database operation failed
    """
    try:
        logger.info("Updating pill", pill_id=pill_id)
        
        # Filter out None values for partial updates
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
        
        result = pills_manager.update_pill(pill_id, update_data)
        
        if result:
            logger.info("Pill updated successfully", pill_id=pill_id)
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
        else:
            logger.info("Pill not found for update", pill_id=pill_id)
            raise HTTPException(status_code=404, detail="Pill not found")
        
    except ValidationException as err:
        logger.warning(f"Pill update validation failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except DatabaseException as err:
        logger.error(f"Pill update database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error updating pill: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/", response_model=PillListResponse)
async def list_pills(
    category: Optional[str] = Query(None, description="Filter by category"),
    created_after: Optional[str] = Query(None, description="Filter pills created after this date (ISO format)"),
    created_before: Optional[str] = Query(None, description="Filter pills created before this date (ISO format)"),
    updated_after: Optional[str] = Query(None, description="Filter pills updated after this date (ISO format)"),
    updated_before: Optional[str] = Query(None, description="Filter pills updated before this date (ISO format)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    limit: int = Query(100, ge=1, le=1000, description="Maximum number of results to return"),
    skip: int = Query(0, ge=0, description="Number of results to skip for pagination")
):
    """
    List pills with filtering and pagination.
    
    Retrieves a list of pill templates with optional filtering by category,
    date range, and active status. Results are paginated.
    
    Args:
        category: Filter by category name
        created_after: ISO timestamp to filter pills created after
        created_before: ISO timestamp to filter pills created before
        updated_after: ISO timestamp to filter pills updated after
        updated_before: ISO timestamp to filter pills updated before
        is_active: Filter by active status
        limit: Maximum number of results to return (1-1000)
        skip: Number of results to skip for pagination
    
    Returns:
        PillListResponse: List of pills with pagination metadata
        
    Raises:
        400 Bad Request: Invalid parameters
        500 Internal Server Error: Database operation failed
    """
    try:
        # Validate search parameters
        search_params = get_pill_search_params(
            category=category,
            created_after=created_after,
            created_before=created_before,
            updated_after=updated_after,
            updated_before=updated_before,
            is_active=is_active,
            limit=limit,
            skip=skip
        )
        
        logger.info(
            "Listing pills",
            category=category,
            is_active=is_active,
            limit=limit,
            skip=skip
        )
        
        # Search pills using manager
        # Convert string dates to datetime objects for the manager
        date_filters = {}
        if search_params.created_after:
            try:
                date_filters["created_after"] = datetime.fromisoformat(search_params.created_after.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid created_after date format")
        
        if search_params.created_before:
            try:
                date_filters["created_before"] = datetime.fromisoformat(search_params.created_before.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid created_before date format")
        
        if search_params.updated_after:
            try:
                date_filters["updated_after"] = datetime.fromisoformat(search_params.updated_after.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid updated_after date format")
        
        if search_params.updated_before:
            try:
                date_filters["updated_before"] = datetime.fromisoformat(search_params.updated_before.replace('Z', '+00:00'))
            except ValueError:
                raise HTTPException(status_code=400, detail="Invalid updated_before date format")
        
        result = pills_manager.search_pills(
            category=search_params.category,
            is_active=search_params.is_active,
            limit=search_params.limit,
            skip=search_params.skip,
            **date_filters
        )
        
        # Convert pills to response format
        pills = []
        for pill in result["pills"]:
            pills.append(PillResponse(
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
        
        logger.info(
            "Pills listed successfully",
            total_found=result["pagination"]["total"],
            returned_count=len(pills)
        )
        
        pagination = result["pagination"]
        return PillListResponse(
            pills=pills,
            pagination=pagination,
            total=pagination["total"],
            count=pagination["count"],
            limit=pagination["limit"],
            skip=pagination["skip"],
            has_next=pagination["has_next"],
            has_prev=pagination["has_prev"]
        )
        
    except InvalidPillCategoryException as err:
        # Let specific pill exceptions bubble up to global handlers
        logger.info(f"Invalid category error in list: {err}")
        raise err
    except ValidationException as err:
        logger.warning(f"Pill list validation failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except DatabaseException as err:
        logger.error(f"Pill list database error: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {err}")
    except Exception as err:
        logger.error(f"Unexpected error listing pills: {err}")
        logger.error(f"Error type: {type(err).__name__}")
        logger.error(f"Error args: {err.args}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}") 