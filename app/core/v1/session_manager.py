"""Session Manager for handling chat sessions."""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
import threading


from app.core.v1.exceptions import DatabaseException, ChatException
from app.core.v1.log_manager import LogManager
from app.settings.v1.general import SETTINGS
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection


class SessionManager:
    """
    Session Manager for handling chat sessions in MongoDB.
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
        """Initialize Session Manager (only once due to singleton pattern)."""
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.logger = LogManager(__name__)
        
        # MongoDB connection
        self.client = MongoClient(SETTINGS.MONGODB_URL)
        self.database = self.client[SETTINGS.MONGODB_DATABASE]
        
        # Collection names
        self.sessions_collection_name = "chat_sessions"
        self.sessions_collection = self.database[self.sessions_collection_name]
        
        # Ensure indexes exist
        self._create_indexes()
        
        self.logger.info("Session Manager initialized successfully")
        
        # Mark as initialized
        self._initialized = True
    
    def _create_indexes(self):
        """Create necessary indexes for sessions collection."""
        # Get existing indexes
        existing_indexes = set()
        try:
            indexes_info = self.sessions_collection.list_indexes()
            for index in indexes_info:
                existing_indexes.add(index["name"])
        except Exception as err:
            self.logger.warning(f"Failed to retrieve existing session indexes: {err}")
        
        # Define indexes to create
        indexes_to_create = [
            ([("session_id", 1)], {"unique": True, "name": "session_id_unique"}),
            ([("user_id", 1)], {"name": "user_id_index"}),
            ([("document_id", 1)], {"name": "document_id_index"}),
            ([("created_at", 1)], {"name": "created_at_index"}),
            ([("last_interaction_at", 1)], {"name": "last_interaction_at_index"}),
            ([("is_active", 1)], {"name": "is_active_index"}),
            ([("user_id", 1), ("document_id", 1)], {"name": "user_document_index"}),
            ([("user_id", 1), ("is_active", 1)], {"name": "user_active_sessions_index"})
        ]
        
        created_count = 0
        existing_count = 0
        
        for index_spec, options in indexes_to_create:
            index_name = options.get('name', 'unnamed')
            
            # Check if index already exists
            if index_name in existing_indexes:
                existing_count += 1
                self.logger.debug(f"Session index already exists: {index_name}")
                continue
            
            try:
                self.sessions_collection.create_index(index_spec, **options)
                created_count += 1
                self.logger.debug(f"Created session index: {index_name}")
                
            except Exception as e:
                if "already exists" not in str(e):
                    self.logger.warning(f"Failed to create session index {index_name}: {e}")
                else:
                    existing_count += 1
                    self.logger.debug(f"Session index already exists (duplicate): {index_name}")
        
        self.logger.info(f"Session indexes processed successfully (created: {created_count}, existing: {existing_count}, total attempted: {len(indexes_to_create)})")
    
    def create_session(
        self,
        user_id: str,
        document_id: str,
        session_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new chat session.
        
        Args:
            user_id: ID of the user creating the session
            document_id: ID of the document for this session
            session_name: Optional custom name for the session
            
        Returns:
            Created session document
        """
        try:
            session_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            session_doc = {
                "session_id": session_id,
                "user_id": user_id,
                "document_id": document_id,
                "session_name": session_name or f"Chat con documento {document_id[:8]}",
                "is_active": True,
                "created_at": timestamp,
                "last_interaction_at": timestamp,
                "interaction_count": 0,
                "metadata": {
                    "created_by": user_id,
                    "last_updated_by": user_id
                }
            }
            
            # Insert session
            result = self.sessions_collection.insert_one(session_doc)
            result_id = str(result.inserted_id)
            
            session_doc["_id"] = result_id
            
            self.logger.info(
                "Chat session created",
                session_id=session_id,
                user_id=user_id,
                document_id=document_id
            )
            
            return session_doc
            
        except Exception as err:
            self.logger.error(f"Failed to create session: {err}")
            raise ChatException(f"Failed to create chat session: {err}") from err
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session by session_id.
        
        Args:
            session_id: Session identifier
            
        Returns:
            Session document or None if not found
        """
        try:
            session = self.sessions_collection.find_one({"session_id": session_id})
            
            if session:
                self.logger.info(f"Session retrieved: {session_id}")
            else:
                self.logger.warning(f"Session not found: {session_id}")
            
            return session
            
        except Exception as err:
            self.logger.error(f"Failed to get session {session_id}: {err}")
            raise ChatException(f"Failed to retrieve session: {err}") from err
    
    def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get sessions for a user.
        
        Args:
            user_id: User identifier
            active_only: Only return active sessions
            limit: Maximum number of sessions to return
            skip: Number of sessions to skip
            
        Returns:
            List of session documents
        """
        try:
            query = {"user_id": user_id}
            if active_only:
                query["is_active"] = True
            
            sessions = list(self.sessions_collection.find(query)
                            .sort("last_interaction_at", -1)
                            .skip(skip)
                            .limit(limit))
            
            self.logger.info(
                f"Retrieved {len(sessions)} sessions for user {user_id}"
            )
            
            return sessions
            
        except Exception as err:
            self.logger.error(f"Failed to get sessions for user {user_id}: {err}")
            raise ChatException(f"Failed to retrieve user sessions: {err}") from err

    def count_user_sessions(
        self,
        user_id: str,
        document_id: Optional[str] = None,
        active_only: bool = True
    ) -> int:
        """
        Count total sessions for a user with optional filtering.
        
        Args:
            user_id: User identifier
            document_id: Optional document filter
            active_only: Only count active sessions
            
        Returns:
            Total count of matching sessions
        """
        try:
            query = {"user_id": user_id}
            
            if active_only:
                query["is_active"] = True
                
            if document_id:
                query["document_id"] = document_id
            
            total_count = self.sessions_collection.count_documents(query)
            
            self.logger.info(
                f"Counted {total_count} sessions for user {user_id}",
                document_id=document_id,
                active_only=active_only
            )
            
            return total_count
            
        except Exception as err:
            self.logger.error(f"Failed to count sessions for user {user_id}: {err}")
            raise ChatException(f"Failed to count user sessions: {err}") from err

    def search_user_sessions(
        self,
        user_id: str,
        document_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 20,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Search sessions for a user with proper pagination (similar to DocumentProcessor).
        
        Args:
            user_id: User identifier
            document_id: Optional document filter
            active_only: Only return active sessions
            limit: Maximum number of sessions to return
            skip: Number of sessions to skip
            
        Returns:
            Dict containing sessions and pagination metadata
        """
        try:
            # Build query with all filters
            query = {"user_id": user_id}
            
            if active_only:
                query["is_active"] = True
                
            if document_id:
                query["document_id"] = document_id
            
            # Get total count of matching sessions (without limit/skip)
            total_found = self.sessions_collection.count_documents(query)
            
            # Get sessions with pagination
            sessions = list(self.sessions_collection.find(query)
                          .sort("last_interaction_at", -1)
                          .skip(skip)
                          .limit(limit))
            
            self.logger.info(
                f"Retrieved {len(sessions)} of {total_found} sessions for user {user_id}",
                document_id=document_id,
                active_only=active_only,
                limit=limit,
                skip=skip
            )
            
            return {
                "sessions": sessions,
                "total_found": total_found,
                "limit": limit,
                "skip": skip
            }
            
        except Exception as err:
            self.logger.error(f"Failed to search sessions for user {user_id}: {err}")
            raise ChatException(f"Failed to search user sessions: {err}") from err
    
    def get_document_sessions(
        self,
        document_id: str,
        user_id: Optional[str] = None,
        active_only: bool = True,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get sessions for a specific document.
        
        Args:
            document_id: Document identifier
            user_id: Optional user filter
            active_only: Only return active sessions
            limit: Maximum number of sessions to return
            
        Returns:
            List of session documents
        """
        try:
            query = {"document_id": document_id}
            if user_id:
                query["user_id"] = user_id
            if active_only:
                query["is_active"] = True
            
            sessions = list(self.sessions_collection.find(query)
                            .sort("last_interaction_at", -1)
                            .limit(limit))
            
            self.logger.info(
                f"Retrieved {len(sessions)} sessions for document {document_id}"
            )
            
            return sessions
            
        except Exception as err:
            self.logger.error(f"Failed to get sessions for document {document_id}: {err}")
            raise ChatException(f"Failed to retrieve document sessions: {err}") from err
    
    def update_session_interaction(self, session_id: str) -> bool:
        """
        Update session's last interaction timestamp and increment count.
        
        Args:
            session_id: Session identifier
            
        Returns:
            True if updated successfully
        """
        try:
            result = self.sessions_collection.update_one(
                {"session_id": session_id},
                {
                    "$set": {"last_interaction_at": datetime.now()},
                    "$inc": {"interaction_count": 1}
                }
            )
            
            if result.modified_count > 0:
                self.logger.info(f"Session interaction updated: {session_id}")
                return True
            else:
                self.logger.warning(f"Failed to update session interaction: {session_id}")
                return False
                
        except Exception as err:
            self.logger.error(f"Failed to update session interaction {session_id}: {err}")
            raise ChatException(f"Failed to update session interaction: {err}") from err
    
    def deactivate_session(self, session_id: str, user_id: str) -> bool:
        """
        Deactivate a session.
        
        Args:
            session_id: Session identifier
            user_id: User performing the action
            
        Returns:
            True if deactivated successfully
        """
        try:
            result = self.sessions_collection.update_one(
                {"session_id": session_id, "user_id": user_id},
                {
                    "$set": {
                        "is_active": False,
                        "deactivated_at": datetime.now(),
                        "metadata.last_updated_by": user_id
                    }
                }
            )
            
            if result.modified_count > 0:
                self.logger.info(f"Session deactivated: {session_id}")
                return True
            else:
                self.logger.warning(f"Failed to deactivate session: {session_id}")
                return False
                
        except Exception as err:
            self.logger.error(f"Failed to deactivate session {session_id}: {err}")
            raise ChatException(f"Failed to deactivate session: {err}") from err
    
    def delete_session(self, session_id: str, user_id: str) -> bool:
        """
        Delete a session permanently.
        
        Args:
            session_id: Session identifier
            user_id: User performing the action
            
        Returns:
            True if deleted successfully
        """
        try:
            # First check if user owns the session
            session = self.get_session(session_id)
            if not session:
                return False
            
            if session.get("user_id") != user_id:
                raise ChatException("User does not have permission to delete this session")
            
            # Delete session
            result = self.sessions_collection.delete_one(
                {"session_id": session_id, "user_id": user_id}
            )
            
            if result.deleted_count > 0:
                self.logger.info(f"Session deleted: {session_id}")
                return True
            else:
                self.logger.warning(f"Failed to delete session: {session_id}")
                return False
                
        except Exception as err:
            self.logger.error(f"Failed to delete session {session_id}: {err}")
            raise ChatException(f"Failed to delete session: {err}") from err
    
    def cleanup_old_sessions(self, days_old: int = 30) -> int:
        """
        Cleanup old inactive sessions.
        
        Args:
            days_old: Number of days to consider old
            
        Returns:
            Number of sessions cleaned up
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            query = {
                "is_active": False,
                "last_interaction_at": {"$lt": cutoff_date}
            }
            
            result = self.sessions_collection.delete_many(query)
            
            count = result.deleted_count
            self.logger.info(f"Cleaned up {count} old sessions")
            
            return count
            
        except Exception as err:
            self.logger.error(f"Failed to cleanup old sessions: {err}")
            raise ChatException(f"Failed to cleanup old sessions: {err}") from err 