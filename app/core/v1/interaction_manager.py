"""Interaction Manager for handling chat interactions (questions and responses)."""

import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta

from app.core.v1.exceptions import ChatException
from app.core.v1.log_manager import LogManager
from app.settings.v1.general import SETTINGS
from pymongo import MongoClient


class InteractionManager:
    """
    Interaction Manager for handling chat interactions in MongoDB.
    """
    
    def __init__(self):
        """Initialize Interaction Manager."""
        self.logger = LogManager(__name__)
        
        # MongoDB connection
        self.client = MongoClient(SETTINGS.MONGODB_URL)
        self.database = self.client[SETTINGS.MONGODB_DATABASE]
        
        # Collection names
        self.interactions_collection_name = "chat_interactions"
        self.interactions_collection = self.database[self.interactions_collection_name]
        
        # Ensure indexes exist
        self._create_indexes()
        
        self.logger.info("Interaction Manager initialized successfully")
    
    def _create_indexes(self):
        """Create necessary indexes for interactions collection."""
        try:
            # Create indexes for interactions collection
            indexes_to_create = [
                ([("interaction_id", 1)], {"unique": True, "name": "interaction_id_unique"}),
                ([("session_id", 1)], {"name": "session_id_index"}),
                ([("user_id", 1)], {"name": "user_id_index"}),
                ([("document_id", 1)], {"name": "document_id_index"}),
                ([("created_at", 1)], {"name": "created_at_index"}),
                ([("session_id", 1), ("created_at", 1)], {"name": "session_chronological_index"}),
                ([("user_id", 1), ("created_at", 1)], {"name": "user_chronological_index"}),
                ([("question", "text"), ("response", "text")], {"name": "interaction_text_search"})
            ]
            
            created_count = 0
            for index_spec, options in indexes_to_create:
                try:
                    self.interactions_collection.create_index(
                        index_spec,
                        **options
                    )
                    created_count += 1
                except Exception as e:
                    if "already exists" not in str(e) and "only one text index" not in str(e):
                        self.logger.warning(f"Failed to create index {options.get('name', 'unknown')}: {e}")
            
            self.logger.info(f"Interaction indexes processed successfully (created: {created_count})")
            
        except Exception as err:
            self.logger.error(f"Failed to create interaction indexes: {err}")
    
    def save_interaction(
        self,
        session_id: str,
        user_id: str,
        document_id: str,
        question: str,
        response: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Save a chat interaction (question + response).
        
        Args:
            session_id: Session identifier
            user_id: User identifier
            document_id: Document identifier
            question: User's question
            response: Assistant's response
            metadata: Optional metadata about the interaction
            
        Returns:
            Saved interaction document
        """
        try:
            interaction_id = str(uuid.uuid4())
            timestamp = datetime.now()
            
            interaction_doc = {
                "interaction_id": interaction_id,
                "session_id": session_id,
                "user_id": user_id,
                "document_id": document_id,
                "question": question,
                "response": response,
                "created_at": timestamp,
                "metadata": metadata or {}
            }
            
            # Add additional metadata
            interaction_doc["metadata"].update({
                "question_length": len(question),
                "response_length": len(response),
                "created_by": user_id
            })
            
            # Insert interaction
            result = self.interactions_collection.insert_one(interaction_doc)
            result_id = str(result.inserted_id)
            
            interaction_doc["_id"] = result_id
            
            self.logger.info(
                "Chat interaction saved",
                interaction_id=interaction_id,
                session_id=session_id,
                question_length=len(question),
                response_length=len(response)
            )
            
            return interaction_doc
            
        except Exception as err:
            self.logger.error(f"Failed to save interaction: {err}")
            raise ChatException(f"Failed to save chat interaction: {err}") from err
    
    def get_interaction(self, interaction_id: str) -> Optional[Dict[str, Any]]:
        """
        Get interaction by interaction_id.
        
        Args:
            interaction_id: Interaction identifier
            
        Returns:
            Interaction document or None if not found
        """
        try:
            interaction = self.mongodb_manager.get_document(
                query={"interaction_id": interaction_id},
                collection_name=self.interactions_collection
            )
            
            if interaction:
                self.logger.info(f"Interaction retrieved: {interaction_id}")
            else:
                self.logger.warning(f"Interaction not found: {interaction_id}")
            
            return interaction
            
        except Exception as err:
            self.logger.error(f"Failed to get interaction {interaction_id}: {err}")
            raise ChatException(f"Failed to retrieve interaction: {err}") from err
    
    def get_session_interactions(
        self,
        session_id: str,
        limit: int = 50,
        skip: int = 0,
        ascending: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Get interactions for a session.
        
        Args:
            session_id: Session identifier
            limit: Maximum number of interactions to return
            skip: Number of interactions to skip
            ascending: Sort order by creation time
            
        Returns:
            List of interaction documents
        """
        try:
            query = {"session_id": session_id}
            sort_order = 1 if ascending else -1
            
            interactions = list(self.interactions_collection.find(query)
                                .sort("created_at", sort_order)
                                .skip(skip)
                                .limit(limit))
            
            self.logger.info(
                f"Retrieved {len(interactions)} interactions for session {session_id}"
            )
            
            return interactions
            
        except Exception as err:
            self.logger.error(f"Failed to get interactions for session {session_id}: {err}")
            raise ChatException(f"Failed to retrieve session interactions: {err}") from err
    
    def get_session_conversation_history(
        self,
        session_id: str,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get conversation history for a session (for context in new responses).
        
        Args:
            session_id: Session identifier
            limit: Maximum number of interactions to return
            
        Returns:
            List of interactions with question/response pairs
        """
        try:
            interactions = self.get_session_interactions(
                session_id=session_id,
                limit=limit,
                ascending=True  # Chronological order
            )
            
            # Format for chat context
            conversation_history = []
            for interaction in interactions:
                conversation_history.append({
                    "question": interaction.get("question", ""),
                    "response": interaction.get("response", ""),
                    "timestamp": interaction.get("created_at")
                })
            
            self.logger.info(
                f"Retrieved conversation history with {len(conversation_history)} interactions for session {session_id}"
            )
            
            return conversation_history
            
        except Exception as err:
            self.logger.error(f"Failed to get conversation history for session {session_id}: {err}")
            raise ChatException(f"Failed to retrieve conversation history: {err}") from err
    
    def get_user_interactions(
        self,
        user_id: str,
        limit: int = 100,
        skip: int = 0,
        document_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get interactions for a user.
        
        Args:
            user_id: User identifier
            limit: Maximum number of interactions to return
            skip: Number of interactions to skip
            document_id: Optional document filter
            
        Returns:
            List of interaction documents
        """
        try:
            query = {"user_id": user_id}
            if document_id:
                query["document_id"] = document_id
            
            interactions = self.mongodb_manager.search_documents(
                query=query,
                limit=limit,
                skip=skip,
                sort=[("created_at", -1)],  # Most recent first
                collection_name=self.interactions_collection
            )
            
            self.logger.info(
                f"Retrieved {len(interactions)} interactions for user {user_id}"
            )
            
            return interactions
            
        except Exception as err:
            self.logger.error(f"Failed to get interactions for user {user_id}: {err}")
            raise ChatException(f"Failed to retrieve user interactions: {err}") from err
    
    def get_document_interactions(
        self,
        document_id: str,
        limit: int = 100,
        skip: int = 0,
        user_id: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Get interactions for a document.
        
        Args:
            document_id: Document identifier
            limit: Maximum number of interactions to return
            skip: Number of interactions to skip
            user_id: Optional user filter
            
        Returns:
            List of interaction documents
        """
        try:
            query = {"document_id": document_id}
            if user_id:
                query["user_id"] = user_id
            
            interactions = self.mongodb_manager.search_documents(
                query=query,
                limit=limit,
                skip=skip,
                sort=[("created_at", -1)],  # Most recent first
                collection_name=self.interactions_collection
            )
            
            self.logger.info(
                f"Retrieved {len(interactions)} interactions for document {document_id}"
            )
            
            return interactions
            
        except Exception as err:
            self.logger.error(f"Failed to get interactions for document {document_id}: {err}")
            raise ChatException(f"Failed to retrieve document interactions: {err}") from err
    
    def search_interactions(
        self,
        search_query: str,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        session_id: Optional[str] = None,
        limit: int = 20
    ) -> List[Dict[str, Any]]:
        """
        Search interactions by text content.
        
        Args:
            search_query: Text to search for
            user_id: Optional user filter
            document_id: Optional document filter
            session_id: Optional session filter
            limit: Maximum number of results
            
        Returns:
            List of matching interaction documents
        """
        try:
            query = {"$text": {"$search": search_query}}
            
            # Add filters
            if user_id:
                query["user_id"] = user_id
            if document_id:
                query["document_id"] = document_id
            if session_id:
                query["session_id"] = session_id
            
            interactions = self.mongodb_manager.search_documents(
                query=query,
                limit=limit,
                sort=[("score", {"$meta": "textScore"})],  # Sort by relevance
                collection_name=self.interactions_collection
            )
            
            self.logger.info(
                f"Found {len(interactions)} interactions matching search: {search_query}"
            )
            
            return interactions
            
        except Exception as err:
            self.logger.error(f"Failed to search interactions: {err}")
            raise ChatException(f"Failed to search interactions: {err}") from err
    
    def delete_session_interactions(self, session_id: str, user_id: str) -> int:
        """
        Delete all interactions for a session.
        
        Args:
            session_id: Session identifier
            user_id: User performing the action
            
        Returns:
            Number of interactions deleted
        """
        try:
            query = {
                "session_id": session_id,
                "user_id": user_id
            }
            
            result = self.mongodb_manager.delete_documents(
                query=query,
                collection_name=self.interactions_collection
            )
            
            count = result.get("deleted_count", 0)
            self.logger.info(f"Deleted {count} interactions for session {session_id}")
            
            return count
            
        except Exception as err:
            self.logger.error(f"Failed to delete interactions for session {session_id}: {err}")
            raise ChatException(f"Failed to delete session interactions: {err}") from err
    
    def cleanup_old_interactions(self, days_old: int = 90) -> int:
        """
        Cleanup old interactions.
        
        Args:
            days_old: Number of days to consider old
            
        Returns:
            Number of interactions cleaned up
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days_old)
            
            query = {
                "created_at": {"$lt": cutoff_date}
            }
            
            result = self.mongodb_manager.delete_documents(
                query=query,
                collection_name=self.interactions_collection
            )
            
            count = result.get("deleted_count", 0)
            self.logger.info(f"Cleaned up {count} old interactions")
            
            return count
            
        except Exception as err:
            self.logger.error(f"Failed to cleanup old interactions: {err}")
            raise ChatException(f"Failed to cleanup old interactions: {err}") from err
    
    def get_interaction_stats(
        self,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        session_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get interaction statistics.
        
        Args:
            user_id: Optional user filter
            document_id: Optional document filter
            session_id: Optional session filter
            days: Number of days to analyze
            
        Returns:
            Dictionary with statistics
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=days)
            query = {"created_at": {"$gte": cutoff_date}}
            
            # Add filters
            if user_id:
                query["user_id"] = user_id
            if document_id:
                query["document_id"] = document_id
            if session_id:
                query["session_id"] = session_id
            
            # Get interactions
            interactions = self.mongodb_manager.search_documents(
                query=query,
                limit=10000,  # Large limit for stats
                collection_name=self.interactions_collection
            )
            
            # Calculate statistics
            total_interactions = len(interactions)
            total_questions = sum(1 for i in interactions if i.get("question"))
            total_responses = sum(1 for i in interactions if i.get("response"))
            avg_question_length = sum(len(i.get("question", "")) for i in interactions) / max(total_interactions, 1)
            avg_response_length = sum(len(i.get("response", "")) for i in interactions) / max(total_interactions, 1)
            
            # Unique sessions and documents
            unique_sessions = len(set(i.get("session_id") for i in interactions if i.get("session_id")))
            unique_documents = len(set(i.get("document_id") for i in interactions if i.get("document_id")))
            
            stats = {
                "period_days": days,
                "total_interactions": total_interactions,
                "total_questions": total_questions,
                "total_responses": total_responses,
                "avg_question_length": round(avg_question_length, 2),
                "avg_response_length": round(avg_response_length, 2),
                "unique_sessions": unique_sessions,
                "unique_documents": unique_documents,
                "interactions_per_day": round(total_interactions / max(days, 1), 2)
            }
            
            self.logger.info(f"Generated interaction statistics: {stats}")
            
            return stats
            
        except Exception as err:
            self.logger.error(f"Failed to get interaction stats: {err}")
            raise ChatException(f"Failed to get interaction statistics: {err}") from err 