"""Chat API router with streaming responses."""

import json
from typing import List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from fastapi.responses import StreamingResponse
from datetime import datetime

from app.apis.v1.types_in import (
    ChatQuestionData,
    CreateSessionData,
    SessionSearchParams,
    InteractionSearchParams,
    validate_session_search_params,
    validate_interaction_search_params
)
from app.apis.v1.types_out import (
    ChatSessionResponse,
    ChatInteractionResponse,
    ChatResponseStart,
    ChatStatsResponse,
    SessionListResponse,
    InteractionListResponse,
    SessionDeleteResponse
)
from app.core.v1.chat_processor import ChatProcessor
from app.core.v1.exceptions import (
    ChatException,
    InvalidDocumentIdFormatException,
    InvalidUserIdFormatException,
    DocumentNotFoundException,
    DocumentAccessDeniedException,
    DocumentNotReadyException,
    DocumentHasNoContentException,
    SessionLimitExceededException,
    SessionCreationFailedException,
    DatabaseConnectionException
)
from app.core.v1.log_manager import LogManager

# Initialize router
router = APIRouter()

# Initialize components
chat_processor = ChatProcessor()
logger = LogManager(__name__)


def get_session_search_params(
    user_id: Optional[str] = Query(None, description="Filter sessions by user ID"),
    document_id: Optional[str] = Query(None, description="Filter sessions by document ID"),
    active_only: bool = Query(True, description="Only return active sessions"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip")
) -> SessionSearchParams:
    return validate_session_search_params(user_id, document_id, active_only, limit, skip)


def get_interaction_search_params(
    session_id: Optional[str] = Query(None, description="Filter by session ID"),
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    search_query: Optional[str] = Query(None, description="Text search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum number of results"),
    skip: int = Query(0, ge=0, description="Number of results to skip"),
    ascending: bool = Query(True, description="Sort order by creation time")
) -> InteractionSearchParams:
    return validate_interaction_search_params(session_id, user_id, document_id, search_query, limit, skip, ascending)


@router.post("/sessions", response_model=ChatSessionResponse, status_code=201)
async def create_chat_session(data: CreateSessionData):
    """
    Create a new chat session for a document with comprehensive validation and error handling.
    
    This endpoint provides enhanced error handling for chat session creation,
    including specific validation for document IDs, user IDs, document status,
    and content availability.
    
    Args:
        data: Session creation data (user_id, document_id, session_name)
    
    Returns:
        ChatSessionResponse: Created session information
        
    Raises:
        400 Bad Request: Invalid input data (user_id or document_id format)
        403 Forbidden: User doesn't have access to document
        404 Not Found: Document not found
        409 Conflict: Document not ready, has no content, or user session limit exceeded
        503 Service Unavailable: Database connection issues
        500 Internal Server Error: Unexpected errors
    """
    try:
        logger.info(
            "Creating chat session",
            user_id=data.user_id,
            document_id=data.document_id,
            session_name=data.session_name
        )
        
        session = chat_processor.create_chat_session(
            user_id=data.user_id,
            document_id=data.document_id,
            session_name=data.session_name
        )
        
        # Convert to response format
        response = ChatSessionResponse(
            session_id=session["session_id"],
            user_id=session["user_id"],
            document_id=session["document_id"],
            session_name=session["session_name"],
            is_active=session["is_active"],
            created_at=session["created_at"].isoformat() if hasattr(session["created_at"], 'isoformat') else str(session["created_at"]),
            last_interaction_at=session["last_interaction_at"].isoformat() if hasattr(session["last_interaction_at"], 'isoformat') else str(session["last_interaction_at"]),
            interaction_count=session["interaction_count"]
        )
        
        logger.info(
            "Chat session created successfully",
            session_id=session["session_id"],
            request_id=session.get("request_id")
        )
        
        return response
        
    except InvalidUserIdFormatException as err:
        logger.error(f"Invalid user ID format: {err}")
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_USER_ID_FORMAT",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please provide a valid user ID with only alphanumeric characters, underscores, dots, and hyphens"
            }
        )
        
    except InvalidDocumentIdFormatException as err:
        logger.error(f"Invalid document ID format: {err}")
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "INVALID_DOCUMENT_ID_FORMAT",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please provide a valid document ID in MongoDB ObjectId format (24 hexadecimal characters)"
            }
        )
        
    except DocumentNotFoundException as err:
        logger.error(f"Document not found: {err}")
        raise HTTPException(
            status_code=404,
            detail={
                "error_code": "DOCUMENT_NOT_FOUND",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please verify the document ID exists and you have access to it"
            }
        )
        
    except DocumentAccessDeniedException as err:
        logger.error(f"Document access denied: {err}")
        raise HTTPException(
            status_code=403,
            detail={
                "error_code": "DOCUMENT_ACCESS_DENIED",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "You don't have permission to access this document for chat sessions"
            }
        )
        
    except DocumentNotReadyException as err:
        logger.error(f"Document not ready for chat: {err}")
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "DOCUMENT_NOT_READY",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please wait for document processing to complete or try with a different document"
            }
        )
        
    except DocumentHasNoContentException as err:
        logger.error(f"Document has no content: {err}")
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "DOCUMENT_NO_CONTENT",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Cannot create chat session for documents without extracted text content"
            }
        )
        
    except SessionLimitExceededException as err:
        logger.error(f"Session limit exceeded: {err}")
        raise HTTPException(
            status_code=409,
            detail={
                "error_code": "SESSION_LIMIT_EXCEEDED",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please close some existing sessions before creating new ones"
            }
        )
        
    except DatabaseConnectionException as err:
        logger.error(f"Database connection error: {err}")
        raise HTTPException(
            status_code=503,
            detail={
                "error_code": "DATABASE_SERVICE_UNAVAILABLE",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please try again in a few moments"
            }
        )
        
    except SessionCreationFailedException as err:
        logger.error(f"Session creation failed: {err}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "SESSION_CREATION_FAILED",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please try again or contact support if the issue persists"
            }
        )
        
    except ChatException as err:
        # Fallback for any other ChatException not specifically handled
        logger.error(f"Chat session creation failed: {err}")
        raise HTTPException(
            status_code=400,
            detail={
                "error_code": "CHAT_SESSION_ERROR",
                "message": str(err),
                "request_id": getattr(err, 'request_id', None),
                "suggestion": "Please verify your input and try again"
            }
        )
        
    except Exception as err:
        # Unexpected errors
        logger.error(f"Unexpected error creating session: {err}")
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": "INTERNAL_SERVER_ERROR",
                "message": "An unexpected error occurred during session creation",
                "request_id": None,
                "suggestion": "Please try again or contact support if the issue persists"
            }
        )


@router.get("/sessions", response_model=SessionListResponse)
async def list_chat_sessions(params: SessionSearchParams = Depends(get_session_search_params)):
    """
    List chat sessions with filtering options.
    
    Args:
        params: Search parameters (user_id, document_id, active_only, limit, skip)
    
    Returns:
        SessionListResponse: List of sessions
    """
    try:
        if not params.user_id:
            raise HTTPException(status_code=400, detail="user_id parameter is required")
        
        logger.info(
            "Listing chat sessions",
            user_id=params.user_id,
            document_id=params.document_id,
            active_only=params.active_only,
            limit=params.limit,
            skip=params.skip
        )
        
        sessions = chat_processor.get_user_sessions(
            user_id=params.user_id,
            active_only=params.active_only,
            limit=params.limit,
            skip=params.skip
        )
        
        # Convert to response format
        session_responses = []
        for session in sessions:
            session_responses.append(ChatSessionResponse(
                session_id=session["session_id"],
                user_id=session["user_id"],
                document_id=session["document_id"],
                session_name=session["session_name"],
                is_active=session["is_active"],
                created_at=session["created_at"].isoformat() if hasattr(session["created_at"], 'isoformat') else str(session["created_at"]),
                last_interaction_at=session["last_interaction_at"].isoformat() if hasattr(session["last_interaction_at"], 'isoformat') else str(session["last_interaction_at"]),
                interaction_count=session["interaction_count"]
            ))
        
        response = SessionListResponse(
            sessions=session_responses,
            total_found=len(session_responses),
            limit=params.limit,
            skip=params.skip
        )
        
        logger.info(f"Retrieved {len(sessions)} chat sessions")
        
        return response
        
    except ChatException as err:
        logger.error(f"Session listing failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error listing sessions: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.post("/ask")
async def ask_question(data: ChatQuestionData):
    """
    Ask a question about a document with streaming response.
    
    Args:
        data: Question data (session_id, user_id, document_id, question)
    
    Returns:
        StreamingResponse: Streaming chat response
    """
    try:
        logger.info(
            "Processing chat question",
            session_id=data.session_id,
            user_id=data.user_id,
            document_id=data.document_id,
            question_length=len(data.question)
        )
        
        async def generate_streaming_response():
            """Generate streaming response in SSE format."""
            try:
                interaction_id = None
                
                async for interaction_id, chunk, is_final in chat_processor.process_chat_question(
                    session_id=data.session_id,
                    user_id=data.user_id,
                    document_id=data.document_id,
                    question=data.question
                ):
                    if not is_final:
                        if chunk:  # Content chunk
                            # Send content chunk in SSE format
                            yield f"data: {json.dumps({'type': 'content', 'content': chunk, 'interaction_id': interaction_id})}\n\n"
                        elif not chunk and interaction_id:  # Start signal
                            # Send start signal
                            start_data = {
                                'type': 'start',
                                'interaction_id': interaction_id,
                                'session_id': data.session_id,
                                'question': data.question,
                                'started_at': datetime.now().isoformat()
                            }
                            yield f"data: {json.dumps(start_data)}\n\n"
                    else:
                        # Send completion signal
                        end_data = {
                            'type': 'end',
                            'interaction_id': interaction_id,
                            'completed_at': datetime.now().isoformat()
                        }
                        yield f"data: {json.dumps(end_data)}\n\n"
                        break
                        
            except ChatException as err:
                # Send error in SSE format
                error_data = {
                    'type': 'error',
                    'error': str(err),
                    'timestamp': datetime.now().isoformat()
                }
                yield f"data: {json.dumps(error_data)}\n\n"
            except Exception as err:
                # Send unexpected error in SSE format
                error_data = {
                    'type': 'error',
                    'error': f"Unexpected error: {str(err)}",
                    'timestamp': datetime.now().isoformat()
                }
                yield f"data: {json.dumps(error_data)}\n\n"
        
        return StreamingResponse(
            generate_streaming_response(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "Access-Control-Allow-Origin": "*",
                "Access-Control-Allow-Headers": "Cache-Control"
            }
        )
        
    except Exception as err:
        logger.error(f"Unexpected error in ask question: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/sessions/{session_id}", response_model=ChatSessionResponse)
async def get_session_info(
    session_id: str,
    user_id: str = Query(..., description="User ID requesting the session")
):
    """
    Get information about a specific chat session.
    
    Args:
        session_id: Session identifier
        user_id: User requesting the session
    
    Returns:
        ChatSessionResponse: Session information
    """
    try:
        logger.info(f"Getting session info: {session_id}")
        
        session = chat_processor.get_session_info(session_id, user_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        
        response = ChatSessionResponse(
            session_id=session["session_id"],
            user_id=session["user_id"],
            document_id=session["document_id"],
            session_name=session["session_name"],
            is_active=session["is_active"],
            created_at=session["created_at"].isoformat() if hasattr(session["created_at"], 'isoformat') else str(session["created_at"]),
            last_interaction_at=session["last_interaction_at"].isoformat() if hasattr(session["last_interaction_at"], 'isoformat') else str(session["last_interaction_at"]),
            interaction_count=session["interaction_count"]
        )
        
        logger.info(f"Session info retrieved: {session_id}")
        
        return response
        
    except ChatException as err:
        logger.error(f"Session info retrieval failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error getting session info: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/sessions/{session_id}/interactions", response_model=InteractionListResponse)
async def get_session_interactions(
    session_id: str,
    user_id: str = Query(..., description="User ID requesting the interactions"),
    limit: int = Query(50, ge=1, le=100, description="Maximum number of interactions"),
    skip: int = Query(0, ge=0, description="Number of interactions to skip")
):
    """
    Get chat interactions for a session.
    
    Args:
        session_id: Session identifier
        user_id: User requesting the interactions
        limit: Maximum number of interactions
        skip: Number of interactions to skip
    
    Returns:
        InteractionListResponse: List of interactions
    """
    try:
        logger.info(f"Getting interactions for session: {session_id}")
        
        interactions = chat_processor.get_session_interactions(
            session_id=session_id,
            user_id=user_id,
            limit=limit,
            skip=skip
        )
        
        # Convert to response format
        interaction_responses = []
        for interaction in interactions:
            interaction_responses.append(ChatInteractionResponse(
                interaction_id=interaction["interaction_id"],
                session_id=interaction["session_id"],
                user_id=interaction["user_id"],
                document_id=interaction["document_id"],
                question=interaction["question"],
                response=interaction["response"],
                created_at=interaction["created_at"].isoformat() if hasattr(interaction["created_at"], 'isoformat') else str(interaction["created_at"]),
                metadata=interaction.get("metadata")
            ))
        
        response = InteractionListResponse(
            interactions=interaction_responses,
            total_found=len(interaction_responses),
            limit=limit,
            skip=skip
        )
        
        logger.info(f"Retrieved {len(interactions)} interactions for session {session_id}")
        
        return response
        
    except ChatException as err:
        logger.error(f"Session interactions retrieval failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error getting session interactions: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.delete("/sessions/{session_id}", response_model=SessionDeleteResponse)
async def delete_chat_session(
    session_id: str,
    user_id: str = Query(..., description="User ID performing the deletion")
):
    """
    Delete a chat session and all its interactions.
    
    Args:
        session_id: Session identifier
        user_id: User performing the deletion
    
    Returns:
        SessionDeleteResponse: Deletion results
    """
    try:
        logger.info(f"Deleting session: {session_id}")
        
        result = chat_processor.delete_chat_session(session_id, user_id)
        
        response = SessionDeleteResponse(
            session_id=result["session_id"],
            deleted=result["deleted"],
            interactions_deleted=result["interactions_deleted"],
            message=result["message"],
            deleted_timestamp=result["deleted_timestamp"]
        )
        
        logger.info(f"Session deletion completed: {session_id}")
        
        return response
        
    except ChatException as err:
        logger.error(f"Session deletion failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error deleting session: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/stats", response_model=ChatStatsResponse)
async def get_chat_stats(
    user_id: Optional[str] = Query(None, description="Filter by user ID"),
    document_id: Optional[str] = Query(None, description="Filter by document ID"),
    days: int = Query(30, ge=1, le=365, description="Number of days to analyze")
):
    """
    Get chat statistics.
    
    Args:
        user_id: Optional user filter
        document_id: Optional document filter
        days: Number of days to analyze
    
    Returns:
        ChatStatsResponse: Chat statistics
    """
    try:
        logger.info(f"Getting chat stats for {days} days")
        
        stats = chat_processor.get_chat_stats(
            user_id=user_id,
            document_id=document_id,
            days=days
        )
        
        response = ChatStatsResponse(
            period_days=stats["period_days"],
            total_interactions=stats["total_interactions"],
            total_questions=stats["total_questions"],
            total_responses=stats["total_responses"],
            avg_question_length=stats["avg_question_length"],
            avg_response_length=stats["avg_response_length"],
            unique_sessions=stats["unique_sessions"],
            unique_documents=stats["unique_documents"],
            interactions_per_day=stats["interactions_per_day"]
        )
        
        logger.info("Chat stats retrieved successfully")
        
        return response
        
    except ChatException as err:
        logger.error(f"Chat stats retrieval failed: {err}")
        raise HTTPException(status_code=400, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error getting chat stats: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}") 