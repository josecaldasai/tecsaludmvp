"""Statistics Manager for handling user analytics and usage statistics."""

import threading
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pymongo import MongoClient, ASCENDING, DESCENDING
from pymongo.errors import PyMongoError
from bson import ObjectId

from app.settings.v1.general import SETTINGS
from app.core.v1.exceptions import DatabaseException
from app.core.v1.log_manager import LogManager


class StatisticsManager:
    """
    Statistics Manager for handling user analytics and platform usage statistics.
    Implements Singleton pattern to ensure only one instance exists.
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Create singleton instance with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """Initialize Statistics Manager (only once due to singleton pattern)."""
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.logger = LogManager(__name__)
        
        # MongoDB connection
        self.client = MongoClient(SETTINGS.MONGODB_URL)
        self.database = self.client[SETTINGS.MONGODB_DATABASE]
        
        # Collection references
        self.documents_collection = self.database["documents"]
        self.sessions_collection = self.database["chat_sessions"]
        self.interactions_collection = self.database["chat_interactions"]
        self.pills_collection = self.database["pills"]
        
        self.logger.info("Statistics Manager initialized successfully")
        
        # Mark as initialized
        self._initialized = True

    def get_platform_overview_stats(
        self, 
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Get platform-wide overview statistics (admin view).
        
        Args:
            start_date: Optional start date for filtering
            end_date: Optional end date for filtering
        
        Returns:
            Dictionary with platform statistics
        """
        try:
            # Build date filter query
            date_filter = {}
            if start_date or end_date:
                date_filter["created_at"] = {}
                if start_date:
                    date_filter["created_at"]["$gte"] = start_date
                if end_date:
                    date_filter["created_at"]["$lte"] = end_date
            
            # Total/filtered counts
            total_documents = self.documents_collection.count_documents(date_filter)
            total_sessions = self.sessions_collection.count_documents(date_filter)
            total_interactions = self.interactions_collection.count_documents(date_filter)
            total_pills = self.pills_collection.count_documents({"is_active": True})
            
            # Unique users (in filtered period if dates provided)
            if date_filter:
                unique_users_docs = len(self.documents_collection.distinct("user_id", date_filter))
                unique_users_sessions = len(self.sessions_collection.distinct("user_id", date_filter))
            else:
                unique_users_docs = len(self.documents_collection.distinct("user_id"))
                unique_users_sessions = len(self.sessions_collection.distinct("user_id"))
            
            # Storage usage (filtered by date if provided)
            storage_pipeline = [
                {"$match": date_filter} if date_filter else {"$match": {}},
                {
                    "$group": {
                        "_id": None,
                        "total_size": {"$sum": "$file_size"},
                        "avg_size": {"$avg": "$file_size"},
                        "max_size": {"$max": "$file_size"},
                        "document_count": {"$sum": 1}
                    }
                }
            ]
            
            # Remove empty match stage if no date filter
            if not date_filter:
                storage_pipeline = storage_pipeline[1:]
                
            storage_stats = list(self.documents_collection.aggregate(storage_pipeline))
            storage_info = storage_stats[0] if storage_stats else {
                "total_size": 0,
                "avg_size": 0,
                "max_size": 0,
                "document_count": 0
            }
            
            # Convert bytes to MB for readability
            storage_info["total_size_mb"] = round(storage_info["total_size"] / (1024 * 1024), 2) if storage_info["total_size"] > 0 else 0
            storage_info["avg_size_mb"] = round(storage_info["avg_size"] / (1024 * 1024), 2) if storage_info["avg_size"] > 0 else 0
            storage_info["max_size_mb"] = round(storage_info["max_size"] / (1024 * 1024), 2) if storage_info["max_size"] > 0 else 0
            
            # Prepare response
            stats = {
                "totals": {
                    "documents": total_documents,
                    "sessions": total_sessions,
                    "interactions": total_interactions,
                    "active_pills": total_pills,
                    "unique_users": max(unique_users_docs, unique_users_sessions)
                },
                "storage": storage_info,
                "period": {
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date": end_date.isoformat() if end_date else None,
                    "filtered": bool(start_date or end_date)
                }
            }
            
            filter_msg = f" (filtered from {start_date} to {end_date})" if (start_date or end_date) else ""
            self.logger.info(f"Platform overview stats retrieved successfully{filter_msg}")
            return stats
            
        except PyMongoError as err:
            self.logger.error(f"Failed to get platform stats: {err}")
            raise DatabaseException(f"Failed to get platform stats: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error getting platform stats: {err}")
            raise DatabaseException(f"Unexpected error getting platform stats: {err}") from err

    def close(self):
        """Close MongoDB connection."""
        try:
            if self.client:
                self.client.close()
                self.logger.info("Statistics Manager MongoDB connection closed successfully")
        except PyMongoError as err:
            self.logger.error(f"Failed to close Statistics Manager MongoDB connection: {err}")
        except Exception as err:
            self.logger.error(f"Unexpected error closing Statistics Manager MongoDB connection: {err}") 