"""Chat Processor for orchestrating complete chat workflow."""

import uuid
from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from datetime import datetime

from app.core.v1.chat_manager import ChatManager
from app.core.v1.session_manager import SessionManager
from app.core.v1.interaction_manager import InteractionManager
from app.core.v1.document_processor import DocumentProcessor
from app.core.v1.exceptions import (
    ChatException,
)
from app.core.v1.log_manager import LogManager


class ChatProcessor:
    """
    Chat Processor for orchestrating the complete chat workflow.
    """
    
    def __init__(self):
        """Initialize Chat Processor."""
        self.logger = LogManager(__name__)
        
        # Initialize managers
        self.chat_manager = ChatManager()
        self.session_manager = SessionManager()
        self.interaction_manager = InteractionManager()
        self.document_processor = DocumentProcessor()
        
        self.logger.info("Chat Processor initialized successfully")
    
    def create_chat_session(
        self,
        user_id: str,
        document_id: str,
        session_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a new chat session.
        
        Args:
            user_id: User creating the session
            document_id: Document for this session
            session_name: Optional custom session name
            
        Returns:
            Created session data
        """
        try:
            # Verify document exists
            document = self.document_processor.get_document_info(document_id)
            if not document:
                raise ChatException(f"Document not found: {document_id}")
            
            # Create session
            session = self.session_manager.create_session(
                user_id=user_id,
                document_id=document_id,
                session_name=session_name
            )
            
            self.logger.info(
                "Chat session created successfully",
                session_id=session["session_id"],
                user_id=user_id,
                document_id=document_id
            )
            
            return session
            
        except Exception as err:
            self.logger.error(f"Failed to create chat session: {err}")
            raise ChatException(f"Failed to create chat session: {err}") from err
    
    async def process_chat_question(
        self,
        session_id: str,
        user_id: str,
        document_id: str,
        question: str
    ) -> AsyncGenerator[Tuple[str, str, bool], None]:
        """
        Process chat question with streaming response.
        
        Args:
            session_id: Session identifier
            user_id: User asking the question
            document_id: Document to ask about
            question: User's question
            
        Yields:
            Tuple[str, str, bool]: (interaction_id, chunk_content, is_final)
        """
        interaction_id = None
        full_response = ""
        
        try:
            # Validate session exists and belongs to user
            session = self.session_manager.get_session(session_id)
            if not session:
                raise ChatException(f"Session not found: {session_id}")
            
            if session.get("user_id") != user_id:
                raise ChatException("User does not have access to this session")
            
            if session.get("document_id") != document_id:
                raise ChatException("Document ID does not match session")
            
            # Get document information
            document = self.document_processor.get_document_info(document_id)
            if not document:
                raise ChatException(f"Document not found: {document_id}")
            
            # Validate document has extracted text
            document_content = document.get("extracted_text", "")
            if not document_content.strip():
                raise ChatException("Document has no extracted text content")
            
            # Get conversation history (using configured limit)
            conversation_history = self.interaction_manager.get_session_conversation_history(
                session_id=session_id,
                limit=self.chat_manager.max_conversation_history  # Use configured limit
            )
            
            # Prepare medical information
            medical_info = {
                "expediente": document.get("expediente"),
                "nombre_paciente": document.get("nombre_paciente"),
                "numero_episodio": document.get("numero_episodio"),
                "categoria": document.get("categoria")
            }
            
            # Validate chat input
            self.chat_manager.validate_chat_input(question, document_content)
            
            # Generate interaction ID
            interaction_id = str(uuid.uuid4())
            
            # Yield start signal with interaction ID
            yield interaction_id, "", False
            
            self.logger.info(
                "Starting chat response stream",
                interaction_id=interaction_id,
                session_id=session_id,
                question_length=len(question)
            )
            
            # Stream response from chat manager
            async for chunk, is_final in self.chat_manager.stream_chat_response(
                user_question=question,
                document_content=document_content,
                medical_info=medical_info,
                conversation_history=conversation_history
            ):
                if not is_final and chunk:
                    full_response += chunk
                    yield interaction_id, chunk, False
                elif is_final:
                    # Save interaction to database
                    try:
                        self.interaction_manager.save_interaction(
                            session_id=session_id,
                            user_id=user_id,
                            document_id=document_id,
                            question=question,
                            response=full_response,
                            metadata={
                                "interaction_id": interaction_id,
                                "medical_info": medical_info,
                                "conversation_context_length": len(conversation_history)
                            }
                        )
                        
                        # Update session interaction timestamp
                        self.session_manager.update_session_interaction(session_id)
                        
                        self.logger.info(
                            "Chat interaction completed and saved",
                            interaction_id=interaction_id,
                            session_id=session_id,
                            response_length=len(full_response)
                        )
                        
                    except Exception as save_err:
                        self.logger.error(f"Failed to save interaction: {save_err}")
                        # Don't raise here, response was successful
                    
                    # Yield final signal
                    yield interaction_id, "", True
                    break
            
        except Exception as err:
            self.logger.error(
                f"Failed to process chat question: {err}",
                interaction_id=interaction_id,
                session_id=session_id
            )
            
            # Try to save error interaction
            if interaction_id:
                try:
                    self.interaction_manager.save_interaction(
                        session_id=session_id,
                        user_id=user_id,
                        document_id=document_id,
                        question=question,
                        response=f"Error: {str(err)}",
                        metadata={
                            "interaction_id": interaction_id,
                            "error": True,
                            "error_message": str(err)
                        }
                    )
                except:
                    pass  # Don't fail on error saving
            
            raise ChatException(f"Failed to process chat question: {err}") from err
    
    def get_session_info(self, session_id: str, user_id: str) -> Optional[Dict[str, Any]]:
        """
        Get session information.
        
        Args:
            session_id: Session identifier
            user_id: User requesting the session
            
        Returns:
            Session information or None
        """
        try:
            session = self.session_manager.get_session(session_id)
            if not session:
                return None
            
            # Check user access
            if session.get("user_id") != user_id:
                raise ChatException("User does not have access to this session")
            
            return session
            
        except Exception as err:
            self.logger.error(f"Failed to get session info: {err}")
            raise ChatException(f"Failed to get session info: {err}") from err
    
    def get_user_sessions(
        self,
        user_id: str,
        active_only: bool = True,
        limit: int = 20,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get user's chat sessions.
        
        Args:
            user_id: User identifier
            active_only: Only return active sessions
            limit: Maximum number of sessions
            skip: Number of sessions to skip
            
        Returns:
            List of sessions
        """
        try:
            sessions = self.session_manager.get_user_sessions(
                user_id=user_id,
                active_only=active_only,
                limit=limit,
                skip=skip
            )
            
            self.logger.info(f"Retrieved {len(sessions)} sessions for user {user_id}")
            
            return sessions
            
        except Exception as err:
            self.logger.error(f"Failed to get user sessions: {err}")
            raise ChatException(f"Failed to get user sessions: {err}") from err
    
    def get_session_interactions(
        self,
        session_id: str,
        user_id: str,
        limit: int = 50,
        skip: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Get session's chat interactions.
        
        Args:
            session_id: Session identifier
            user_id: User requesting the interactions
            limit: Maximum number of interactions
            skip: Number of interactions to skip
            
        Returns:
            List of interactions
        """
        try:
            # Verify user has access to session
            session = self.get_session_info(session_id, user_id)
            if not session:
                raise ChatException("Session not found or access denied")
            
            interactions = self.interaction_manager.get_session_interactions(
                session_id=session_id,
                limit=limit,
                skip=skip,
                ascending=True  # Chronological order
            )
            
            self.logger.info(f"Retrieved {len(interactions)} interactions for session {session_id}")
            
            return interactions
            
        except Exception as err:
            self.logger.error(f"Failed to get session interactions: {err}")
            raise ChatException(f"Failed to get session interactions: {err}") from err
    
    def delete_chat_session(self, session_id: str, user_id: str) -> Dict[str, Any]:
        """
        Delete a chat session and its interactions.
        
        Args:
            session_id: Session identifier
            user_id: User performing the deletion
            
        Returns:
            Deletion results
        """
        try:
            # Delete interactions first
            interactions_deleted = self.interaction_manager.delete_session_interactions(
                session_id=session_id,
                user_id=user_id
            )
            
            # Delete session
            session_deleted = self.session_manager.delete_session(
                session_id=session_id,
                user_id=user_id
            )
            
            if session_deleted:
                self.logger.info(
                    f"Session deleted successfully",
                    session_id=session_id,
                    interactions_deleted=interactions_deleted
                )
                
                return {
                    "session_id": session_id,
                    "deleted": True,
                    "interactions_deleted": interactions_deleted,
                    "message": "Session and interactions deleted successfully",
                    "deleted_timestamp": datetime.now().isoformat()
                }
            else:
                return {
                    "session_id": session_id,
                    "deleted": False,
                    "interactions_deleted": 0,
                    "message": "Session not found or access denied",
                    "deleted_timestamp": datetime.now().isoformat()
                }
            
        except Exception as err:
            self.logger.error(f"Failed to delete session: {err}")
            raise ChatException(f"Failed to delete session: {err}") from err
    
    def get_chat_stats(
        self,
        user_id: Optional[str] = None,
        document_id: Optional[str] = None,
        days: int = 30
    ) -> Dict[str, Any]:
        """
        Get chat statistics.
        
        Args:
            user_id: Optional user filter
            document_id: Optional document filter
            days: Number of days to analyze
            
        Returns:
            Chat statistics
        """
        try:
            stats = self.interaction_manager.get_interaction_stats(
                user_id=user_id,
                document_id=document_id,
                days=days
            )
            
            self.logger.info(f"Generated chat stats for {days} days")
            
            return stats
            
        except Exception as err:
            self.logger.error(f"Failed to get chat stats: {err}")
            raise ChatException(f"Failed to get chat stats: {err}") from err 