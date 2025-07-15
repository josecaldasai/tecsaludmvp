"""Statistics API Router for platform analytics and insights."""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
from datetime import datetime

from app.apis.v1.types_out import PlatformOverviewStatsResponse
from app.core.v1.statistics_manager import StatisticsManager
from app.core.v1.exceptions import DatabaseException
from app.core.v1.log_manager import LogManager

# Initialize router and logger
router = APIRouter()
logger = LogManager(__name__)

# Initialize Statistics Manager
statistics_manager = StatisticsManager()


@router.get(
    "/platform/overview",
    response_model=PlatformOverviewStatsResponse,
    summary="Get Platform Overview Statistics",
    description="Get platform-wide statistics for administrative dashboards with optional date filtering."
)
async def get_platform_overview_stats(
    start_date: Optional[str] = Query(default=None, description="Start date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)"),
    end_date: Optional[str] = Query(default=None, description="End date (ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS)")
) -> PlatformOverviewStatsResponse:
    """
    Get platform-wide overview statistics.
    
    - **start_date**: Optional start date for filtering (ISO format)
    - **end_date**: Optional end date for filtering (ISO format)
    
    Returns platform statistics including:
    - Total documents, sessions, interactions (in period if filtered)
    - Unique users count (in period if filtered)
    - Storage usage (in period if filtered)
    - Period information
    
    Examples:
    - No filter: `/platform/overview` - All time stats
    - Date only: `/platform/overview?start_date=2024-01-01&end_date=2024-01-31`
    - DateTime: `/platform/overview?start_date=2024-01-01T00:00:00&end_date=2024-01-31T23:59:59`
    """
    try:
        logger.info(f"Getting platform overview statistics with date filter: {start_date} to {end_date}")
        
        # Parse and validate dates
        parsed_start_date = None
        parsed_end_date = None
        
        if start_date:
            try:
                if 'T' in start_date:
                    parsed_start_date = datetime.fromisoformat(start_date.replace('Z', '+00:00'))
                else:
                    parsed_start_date = datetime.fromisoformat(start_date + 'T00:00:00')
            except ValueError:
                raise ValueError("Invalid start_date format. Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
        
        if end_date:
            try:
                if 'T' in end_date:
                    parsed_end_date = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                else:
                    parsed_end_date = datetime.fromisoformat(end_date + 'T23:59:59')
            except ValueError:
                raise ValueError("Invalid end_date format. Use ISO format: YYYY-MM-DD or YYYY-MM-DDTHH:MM:SS")
        
        # Validate date range
        if parsed_start_date and parsed_end_date and parsed_start_date > parsed_end_date:
            raise ValueError("start_date must be before or equal to end_date")
        
        # Get statistics
        stats = statistics_manager.get_platform_overview_stats(
            start_date=parsed_start_date,
            end_date=parsed_end_date
        )
        
        logger.info("Platform overview statistics retrieved successfully")
        return PlatformOverviewStatsResponse(**stats)
        
    except DatabaseException as err:
        logger.error(f"Database error getting platform stats: {err}")
        raise HTTPException(status_code=500, detail=f"Database error: {str(err)}")
    except ValueError as err:
        logger.error(f"Validation error in platform stats: {err}")
        raise HTTPException(status_code=400, detail=f"Invalid parameters: {str(err)}")
    except Exception as err:
        logger.error(f"Unexpected error getting platform stats: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(err)}") 