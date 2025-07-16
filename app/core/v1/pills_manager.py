"""Pills Manager for handling pill templates (starter buttons)."""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import threading

from app.core.v1.exceptions import (
    DatabaseException, 
    ValidationException,
    PillNotFoundException,
    InvalidPillCategoryException,
    DuplicatePillPriorityException
)
from app.core.v1.log_manager import LogManager
from app.settings.v1.general import SETTINGS
from pymongo import MongoClient, ASCENDING


class PillsManager:
    """
    Pills Manager for handling pill templates (starter buttons) in MongoDB.
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
        """Initialize Pills Manager (only once due to singleton pattern)."""
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.logger = LogManager(__name__)
        
        # MongoDB connection
        self.client = MongoClient(SETTINGS.MONGODB_URL)
        self.database = self.client[SETTINGS.MONGODB_DATABASE]
        
        # Collection names
        self.pills_collection_name = "pills"
        self.pills_collection = self.database[self.pills_collection_name]
        
        # Valid categories (restrictive list)
        self.valid_categories = [
            "general",
            "medico",
            "emergencia", 
            "consulta",
            "laboratorio",
            "radiologia",
            "farmacia",
            "administrativo"
        ]
        
        # Valid priority levels (categorical)
        self.valid_priorities = ["alta", "media", "baja"]
        
        # Ensure indexes exist
        self._create_indexes()
        
        self.logger.info("Pills Manager initialized successfully")
        
        # Mark as initialized
        self._initialized = True

    def _create_indexes(self):
        """Create necessary indexes for pills collection."""
        # Get existing indexes
        existing_indexes = set()
        try:
            indexes_info = self.pills_collection.list_indexes()
            for index in indexes_info:
                existing_indexes.add(index["name"])
        except Exception as err:
            self.logger.warning(f"Failed to retrieve existing pills indexes: {err}")
        
        # Define indexes to create (removing unique priority index)
        indexes_to_create = [
            ([("pill_id", ASCENDING)], {"unique": True, "name": "pill_id_unique"}),
            ([("priority", ASCENDING)], {"name": "priority_index"}),  # Removed unique constraint
            ([("category", ASCENDING)], {"name": "category_index"}),
            ([("created_at", ASCENDING)], {"name": "created_at_index"}),
            ([("updated_at", ASCENDING)], {"name": "updated_at_index"}),
            ([("priority", ASCENDING), ("category", ASCENDING)], {"name": "priority_category_index"}),
            ([("starter", "text"), ("text", "text")], {"sparse": True, "name": "pills_text_search"})
        ]
        
        created_count = 0
        existing_count = 0
        
        for index_spec, index_options in indexes_to_create:
            index_name = index_options["name"]
            
            if index_name not in existing_indexes:
                try:
                    self.pills_collection.create_index(index_spec, **index_options)
                    created_count += 1
                except Exception as err:
                    self.logger.warning(f"Failed to create index '{index_name}': {err}")
            else:
                existing_count += 1
        
        # Try to drop the old unique priority index if it exists
        try:
            if "priority_unique" in existing_indexes:
                self.pills_collection.drop_index("priority_unique")
                self.logger.info("Dropped old unique priority index")
        except Exception as err:
            self.logger.warning(f"Failed to drop old priority index: {err}")
        
        self.logger.info(
            f"Pills indexes processed successfully (created: {created_count}, existing: {existing_count}, total attempted: {len(indexes_to_create)})"
        )

    def create_pill(self, pill_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new pill template.
        
        Args:
            pill_data: Dictionary containing pill information
            
        Returns:
            Created pill document
            
        Raises:
            ValidationException: If validation fails
            DatabaseException: If database operation fails
        """
        try:
            pill_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            # Validate required fields
            required_fields = ["starter", "text", "icon", "category", "priority"]
            for field in required_fields:
                if field not in pill_data or not pill_data[field]:
                    raise ValidationException(f"Missing required field: {field}")
            
            # Validate category
            if pill_data["category"] not in self.valid_categories:
                raise InvalidPillCategoryException(
                    f"Invalid category '{pill_data['category']}'. "
                    f"Valid categories: {', '.join(self.valid_categories)}"
                )
            
            # Validate priority (categorical)
            priority = pill_data["priority"]
            if not isinstance(priority, str) or priority.lower() not in self.valid_priorities:
                raise ValidationException(
                    f"Invalid priority '{priority}'. Valid priorities: {', '.join(self.valid_priorities)}"
                )
            
            pill_doc = {
                "pill_id": pill_id,
                "starter": pill_data["starter"].strip(),
                "text": pill_data["text"].strip(),
                "icon": pill_data["icon"].strip(),
                "category": pill_data["category"].strip().lower(),
                "priority": priority.lower(),
                "created_at": timestamp,
                "updated_at": timestamp,
                "is_active": True
            }
            
            # Insert pill
            result = self.pills_collection.insert_one(pill_doc)
            result_id = str(result.inserted_id)
            
            pill_doc["_id"] = result_id
            
            self.logger.info(
                "Pill created successfully",
                pill_id=pill_id,
                starter=pill_data["starter"],
                category=pill_data["category"],
                priority=priority
            )
            
            return pill_doc
            
        except (InvalidPillCategoryException, DuplicatePillPriorityException):
            # Let specific pill exceptions bubble up
            raise
        except ValidationException:
            raise
        except DuplicateKeyError as err:
            raise DatabaseException(f"Duplicate pill data: {err}") from err
        except PyMongoError as err:
            self.logger.error(f"Failed to create pill: {err}")
            raise DatabaseException(f"Failed to create pill: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error creating pill: {err}")
            raise DatabaseException(f"Unexpected error creating pill: {err}") from err

    def get_pill(self, pill_id: str) -> Optional[Dict[str, Any]]:
        """
        Get a specific pill by ID.
        
        Args:
            pill_id: Pill ID to retrieve
            
        Returns:
            Pill document or None if not found
        """
        try:
            pill = self.pills_collection.find_one({"pill_id": pill_id})
            
            if pill:
                pill["_id"] = str(pill["_id"])
                self.logger.info("Pill retrieved successfully", pill_id=pill_id)
                return pill
            else:
                self.logger.info("Pill not found", pill_id=pill_id)
                return None
                
        except PyMongoError as err:
            self.logger.error(f"Failed to retrieve pill: {err}")
            raise DatabaseException(f"Failed to retrieve pill: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error retrieving pill: {err}")
            raise DatabaseException(f"Unexpected error retrieving pill: {err}") from err

    def update_pill(self, pill_id: str, update_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Update an existing pill.
        
        Args:
            pill_id: Pill ID to update
            update_data: Dictionary containing fields to update
            
        Returns:
            Updated pill document or None if not found
            
        Raises:
            ValidationException: If validation fails
            DatabaseException: If database operation fails
        """
        try:
            # Get existing pill first
            existing_pill = self.pills_collection.find_one({"pill_id": pill_id})
            if not existing_pill:
                return None
            
            # Validate category if provided
            if "category" in update_data and update_data["category"] not in self.valid_categories:
                raise ValidationException(
                    f"Invalid category '{update_data['category']}'. "
                    f"Valid categories: {', '.join(self.valid_categories)}"
                )
            
            # Validate priority if provided (categorical)
            if "priority" in update_data:
                new_priority = update_data["priority"]
                if not isinstance(new_priority, str) or new_priority.lower() not in self.valid_priorities:
                    raise ValidationException(
                        f"Invalid priority '{new_priority}'. Valid priorities: {', '.join(self.valid_priorities)}"
                    )
            
            # Prepare update data
            update_fields = {}
            allowed_fields = ["starter", "text", "icon", "category", "priority", "is_active"]
            
            for field in allowed_fields:
                if field in update_data:
                    if field in ["starter", "text", "icon"]:
                        update_fields[field] = str(update_data[field]).strip()
                    elif field == "category":
                        update_fields[field] = str(update_data[field]).strip().lower()
                    elif field == "priority":
                        update_fields[field] = str(update_data[field]).strip().lower()
                    else:
                        update_fields[field] = update_data[field]
            
            update_fields["updated_at"] = datetime.now()
            
            # Update pill
            result = self.pills_collection.update_one(
                {"pill_id": pill_id},
                {"$set": update_fields}
            )
            
            if result.modified_count > 0:
                # Get updated pill
                updated_pill = self.pills_collection.find_one({"pill_id": pill_id})
                updated_pill["_id"] = str(updated_pill["_id"])
                
                self.logger.info(
                    "Pill updated successfully",
                    pill_id=pill_id,
                    modified_fields=list(update_fields.keys())
                )
                
                return updated_pill
            else:
                # No changes made, return existing pill
                existing_pill["_id"] = str(existing_pill["_id"])
                return existing_pill
                
        except ValidationException:
            raise
        except DuplicateKeyError as err:
            raise DatabaseException(f"Duplicate pill data: {err}") from err
        except PyMongoError as err:
            self.logger.error(f"Failed to update pill: {err}")
            raise DatabaseException(f"Failed to update pill: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error updating pill: {err}")
            raise DatabaseException(f"Unexpected error updating pill: {err}") from err

    def delete_pill(self, pill_id: str) -> bool:
        """
        Delete a pill.
        
        Args:
            pill_id: Pill ID to delete
            
        Returns:
            True if deleted successfully, False if not found
        """
        try:
            result = self.pills_collection.delete_one({"pill_id": pill_id})
            
            if result.deleted_count > 0:
                self.logger.info("Pill deleted successfully", pill_id=pill_id)
                return True
            else:
                self.logger.info("Pill not found for deletion", pill_id=pill_id)
                return False
                
        except PyMongoError as err:
            self.logger.error(f"Failed to delete pill: {err}")
            raise DatabaseException(f"Failed to delete pill: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error deleting pill: {err}")
            raise DatabaseException(f"Unexpected error deleting pill: {err}") from err

    def search_pills(
        self,
        category: Optional[str] = None,
        created_after: Optional[datetime] = None,
        created_before: Optional[datetime] = None,
        updated_after: Optional[datetime] = None,
        updated_before: Optional[datetime] = None,
        is_active: Optional[bool] = None,
        limit: int = 100,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Search pills with filtering and pagination.
        
        Args:
            category: Filter by category
            created_after: Filter by creation date (after)
            created_before: Filter by creation date (before)
            updated_after: Filter by update date (after)
            updated_before: Filter by update date (before)
            is_active: Filter by active status
            limit: Maximum number of results
            skip: Number of results to skip
            
        Returns:
            Dictionary with results and pagination metadata
        """
        try:
            # Build query
            query = {}
            
            if category is not None:
                if category not in self.valid_categories:
                    raise ValidationException(
                        f"Invalid category '{category}'. "
                        f"Valid categories: {', '.join(self.valid_categories)}"
                    )
                query["category"] = category.lower()
            
            if is_active is not None:
                query["is_active"] = is_active
            
            # Date filters
            date_query = {}
            if created_after or created_before:
                if created_after:
                    date_query["$gte"] = created_after
                if created_before:
                    date_query["$lte"] = created_before
                query["created_at"] = date_query
            
            if updated_after or updated_before:
                update_date_query = {}
                if updated_after:
                    update_date_query["$gte"] = updated_after
                if updated_before:
                    update_date_query["$lte"] = updated_before
                query["updated_at"] = update_date_query
            
            # Get total count
            total_count = self.pills_collection.count_documents(query)
            
            # Execute search with pagination and proper priority ordering
            # For categorical priorities, we need custom ordering: alta > media > baja
            pills_cursor = self.pills_collection.find(query).skip(skip).limit(limit)
            
            # Convert results and sort by priority order
            pills = []
            for pill in pills_cursor:
                pill["_id"] = str(pill["_id"])
                pills.append(pill)
            
            # Sort by priority (alta first, then media, then baja)
            priority_order = {"alta": 1, "media": 2, "baja": 3}
            pills.sort(key=lambda x: (
                priority_order.get(x.get("priority", "baja"), 3), 
                x.get("created_at", datetime(1970, 1, 1))
            ))

            # Calculate pagination metadata
            has_next = (skip + limit) < total_count
            has_prev = skip > 0
            
            result = {
                "pills": pills,
                "pagination": {
                    "total": total_count,
                    "count": len(pills),
                    "limit": limit,
                    "skip": skip,
                    "has_next": has_next,
                    "has_prev": has_prev
                }
            }
            
            self.logger.info(
                "Pills search completed",
                query=query,
                total_found=total_count,
                returned_count=len(pills),
                limit=limit,
                skip=skip
            )
            
            return result
            
        except ValidationException:
            raise
        except PyMongoError as err:
            self.logger.error(f"Failed to search pills: {err}")
            raise DatabaseException(f"Failed to search pills: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error searching pills: {err}")
            raise DatabaseException(f"Unexpected error searching pills: {err}") from err

    def get_all_pills_ordered(self, is_active: Optional[bool] = True) -> List[Dict[str, Any]]:
        """
        Get all pills ordered by priority.
        
        Args:
            is_active: Filter by active status (default: True)
            
        Returns:
            List of pills ordered by priority (alta, media, baja)
        """
        try:
            query = {}
            if is_active is not None:
                query["is_active"] = is_active
                
            cursor = self.pills_collection.find(query)
            
            pills = []
            for pill in cursor:
                pill["_id"] = str(pill["_id"])
                pills.append(pill)
            
            # Sort by priority (alta first, then media, then baja) and creation time
            priority_order = {"alta": 1, "media": 2, "baja": 3}
            pills.sort(key=lambda x: (
                priority_order.get(x.get("priority", "baja"), 3), 
                x.get("created_at", datetime(1970, 1, 1))
            ))
            
            self.logger.info(
                "All pills retrieved",
                count=len(pills),
                is_active_filter=is_active
            )
            
            return pills
            
        except PyMongoError as err:
            self.logger.error(f"Failed to get all pills: {err}")
            raise DatabaseException(f"Failed to get all pills: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error getting all pills: {err}")
            raise DatabaseException(f"Unexpected error getting all pills: {err}") from err

    def get_valid_categories(self) -> List[str]:
        """
        Get list of valid categories.
        
        Returns:
            List of valid category names
        """
        return self.valid_categories.copy()

    def get_valid_priorities(self) -> List[str]:
        """
        Get list of valid priority levels.
        
        Returns:
            List of valid priority levels
        """
        return self.valid_priorities.copy()

    def get_priority_descriptions(self) -> Dict[str, str]:
        """
        Get descriptions for each priority level.
        
        Returns:
            Dictionary mapping priority levels to their descriptions
        """
        return {
            "alta": "Prioridad alta - Se muestran primero",
            "media": "Prioridad media - Se muestran en posición intermedia", 
            "baja": "Prioridad baja - Se muestran al final"
        }

    def close(self):
        """Close MongoDB connection."""
        try:
            if self.client:
                self.client.close()
                self.logger.info("Pills Manager MongoDB connection closed successfully")
        except PyMongoError as err:
            self.logger.error(f"Failed to close Pills Manager MongoDB connection: {err}")
        except Exception as err:
            self.logger.error(f"Unexpected error closing Pills Manager MongoDB connection: {err}") 