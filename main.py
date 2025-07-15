"""Main FastAPI application for TecSalud Chatbot Document Processing API."""

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
from fastapi.exceptions import RequestValidationError
from contextlib import asynccontextmanager
import time
from typing import Dict, Any

from app import TITLE, DESCRIPTION, VERSION, CONTACT, TAGS_METADATA
from app.apis.v1.router import router as documents_router
from app.core.v1.log_manager import LogManager
from app.core.v1.exceptions import (
    AppException,
    UnauthorizedException,
    ValidationException,
    StorageException,
    OCRException,
    DatabaseException,
    ChatException,
    UserIdRequiredException,
    InvalidUserIdException
)
from app.settings.v1.settings import SETTINGS


# Initialize logger
logger = LogManager(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting TecSalud Chatbot Document Processing API")
    logger.info(f"Environment: {'Production' if SETTINGS.GENERAL.PRODUCTION else 'Development'}")
    logger.info(f"Version: {VERSION}")
    
    # Validate database connection
    try:
        from app.core.v1.mongodb_manager import MongoDBManager
        mongodb_manager = MongoDBManager()
        
        # The MongoDBManager automatically creates indexes during initialization
        # We just need to verify the connection is working
        test_count = mongodb_manager.count_documents({})
        logger.info(f"Database connection validated successfully. Document count: {test_count}")
        
    except Exception as err:
        logger.error(f"Database connection validation failed: {err}")
        # Don't raise exception to allow startup to continue
        # The individual managers will handle their own connection errors
    
    yield
    
    # Shutdown
    logger.info("Shutting down TecSalud Chatbot Document Processing API")


# Create FastAPI application
app = FastAPI(
    title=TITLE,
    description=DESCRIPTION,
    version=VERSION,
    contact=CONTACT,
    openapi_tags=TAGS_METADATA,
    lifespan=lifespan,
    docs_url="/docs" if not SETTINGS.GENERAL.PRODUCTION else None,
    redoc_url="/redoc" if not SETTINGS.GENERAL.PRODUCTION else None
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=SETTINGS.GENERAL.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)


# Custom exception handlers
@app.exception_handler(AppException)
async def app_exception_handler(request: Request, exc: AppException):
    """Handle application exceptions."""
    logger.error(f"Application exception: {exc.message}")
    return JSONResponse(
        status_code=500,
        content={
            "error_code": "APPLICATION_ERROR",
            "error_message": exc.message,
            "timestamp": time.time()
        }
    )


@app.exception_handler(UnauthorizedException)
async def unauthorized_exception_handler(request: Request, exc: UnauthorizedException):
    """Handle unauthorized exceptions."""
    logger.warning(f"Unauthorized access attempt: {exc.message}")
    return JSONResponse(
        status_code=401,
        content={
            "error_code": "UNAUTHORIZED",
            "error_message": exc.message,
            "timestamp": time.time()
        }
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    """Handle validation exceptions."""
    logger.warning(f"Validation error: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error_code": "VALIDATION_ERROR",
            "error_message": exc.message,
            "timestamp": time.time()
        }
    )


@app.exception_handler(StorageException)
async def storage_exception_handler(request: Request, exc: StorageException):
    """Handle storage exceptions."""
    logger.error(f"Storage error: {exc.message}")
    return JSONResponse(
        status_code=503,
        content={
            "error_code": "STORAGE_ERROR",
            "error_message": "Storage service temporarily unavailable",
            "timestamp": time.time()
        }
    )


@app.exception_handler(OCRException)
async def ocr_exception_handler(request: Request, exc: OCRException):
    """Handle OCR processing exceptions."""
    logger.error(f"OCR processing error: {exc.message}")
    return JSONResponse(
        status_code=503,
        content={
            "error_code": "OCR_ERROR",
            "error_message": "OCR service temporarily unavailable",
            "timestamp": time.time()
        }
    )


@app.exception_handler(DatabaseException)
async def database_exception_handler(request: Request, exc: DatabaseException):
    """Handle database exceptions."""
    logger.error(f"Database error: {exc.message}")
    return JSONResponse(
        status_code=503,
        content={
            "error_code": "DATABASE_ERROR",
            "error_message": "Database service temporarily unavailable",
            "timestamp": time.time()
        }
    )


@app.exception_handler(ChatException)
async def chat_exception_handler(request: Request, exc: ChatException):
    """Handle chat exceptions."""
    logger.error(f"Chat exception: {exc.message}")
    return JSONResponse(
        status_code=400,
        content={
            "error_code": "CHAT_ERROR",
            "error_message": exc.message,
            "timestamp": time.time()
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions."""
    logger.warning(f"HTTP exception: {exc.status_code} - {exc.detail}")
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error_code": f"HTTP_{exc.status_code}",
            "error_message": exc.detail,
            "timestamp": time.time()
        }
    )


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle RequestValidationError exceptions with custom user_id error handling."""
    request_id = f"validation_error_{int(time.time())}"
    
    logger.warning(
        "Request validation error occurred",
        path=request.url.path,
        method=request.method,
        errors=exc.errors(),
        request_id=request_id
    )
    
    # Check if it's a user_id validation error
    for error in exc.errors():
        loc = error.get('loc', [])
        error_type = error.get('type', '')
        error_msg = error.get('msg', '')
        
        # Check if error is related to user_id
        if 'user_id' in loc or (len(loc) > 1 and loc[1] == 'user_id'):
            if error_type == 'missing':
                logger.error(
                    "User ID is required but not provided",
                    path=request.url.path,
                    request_id=request_id,
                    error_type=error_type
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error_code": "USER_ID_REQUIRED",
                        "message": "User ID is required for this operation. Please provide a valid user_id parameter.",
                        "request_id": request_id,
                        "suggestion": "Add user_id parameter to your request (e.g., ?user_id=your_user_id)",
                        "timestamp": time.time()
                    }
                )
            
            elif error_type == 'string_too_short' or 'empty' in error_msg.lower():
                logger.error(
                    "User ID is empty or too short",
                    path=request.url.path,
                    request_id=request_id,
                    error_type=error_type
                )
                return JSONResponse(
                    status_code=400,
                    content={
                        "error_code": "INVALID_USER_ID",
                        "message": "User ID cannot be empty. Please provide a valid user_id parameter.",
                        "request_id": request_id,
                        "suggestion": "Ensure user_id has at least 1 character (e.g., ?user_id=your_user_id)",
                        "timestamp": time.time()
                    }
                )
    
    # Default validation error handling
    return JSONResponse(
        status_code=422,
        content={
            "error_code": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
            "request_id": request_id,
            "suggestion": "Please check your request parameters and try again",
            "timestamp": time.time()
        }
    )


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all HTTP requests."""
    start_time = time.time()
    
    # Log request
    logger.log_request(
        method=request.method,
        path=request.url.path,
        user_id=None  # Could be extracted from token if needed
    )
    
    # Process request
    response = await call_next(request)
    
    # Log response
    process_time = time.time() - start_time
    logger.log_response(
        method=request.method,
        path=request.url.path,
        status_code=response.status_code,
        duration=process_time
    )
    
    return response


# Include routers
app.include_router(documents_router, prefix="/api/v1/documents", tags=["documents"])

# Import and include chat router
from app.apis.v1.chat_router import router as chat_router
app.include_router(chat_router, prefix="/api/v1/chat", tags=["chat"])

# Import and include fuzzy search router
from app.apis.v1.fuzzy_search_router import router as fuzzy_search_router
app.include_router(fuzzy_search_router, prefix="/api/v1/search", tags=["fuzzy-search"])

# Import and include tokens router
from app.apis.v1.tokens_router import router as tokens_router
app.include_router(tokens_router, prefix="/api/v1/tokens", tags=["tokens"])

# Import and include pills router
from app.apis.v1.pills_router import router as pills_router
app.include_router(pills_router, prefix="/api/v1/pills", tags=["pills"])


# Root endpoint
@app.get("/", tags=["health"])
async def root():
    """Root endpoint with basic API information."""
    return {
        "message": "TecSalud Chatbot Document Processing API",
        "version": VERSION,
        "status": "healthy",
        "timestamp": time.time(),
        "docs_url": "/docs" if not SETTINGS.GENERAL.PRODUCTION else None,
        "api_version": "v1"
    }


# Health check endpoint
@app.get("/health", tags=["health"])
async def health_check():
    """Basic health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": VERSION,
        "environment": "production" if SETTINGS.GENERAL.PRODUCTION else "development"
    }


# Custom OpenAPI schema
def custom_openapi():
    """Generate custom OpenAPI schema."""
    if app.openapi_schema:
        return app.openapi_schema
    
    openapi_schema = get_openapi(
        title=TITLE,
        version=VERSION,
        description=DESCRIPTION,
        routes=app.routes,
        tags=TAGS_METADATA
    )
    
    # Add custom security schemes
    openapi_schema["components"]["securitySchemes"] = {
        "bearerAuth": {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "JWT"
        }
    }
    
    # Add security to all endpoints
    for path in openapi_schema["paths"]:
        for method in openapi_schema["paths"][path]:
            if method != "options":
                openapi_schema["paths"][path][method]["security"] = [
                    {"bearerAuth": []}
                ]
    
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = custom_openapi


# Custom docs endpoint (if not in production)
if not SETTINGS.GENERAL.PRODUCTION:
    @app.get("/docs", include_in_schema=False)
    async def custom_swagger_ui_html():
        """Custom Swagger UI with additional configuration."""
        return get_swagger_ui_html(
            openapi_url=app.openapi_url,
            title=f"{TITLE} - Swagger UI",
            swagger_js_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui-bundle.js",
            swagger_css_url="https://cdn.jsdelivr.net/npm/swagger-ui-dist@4.15.5/swagger-ui.css",
        )


# Run the application
if __name__ == "__main__":
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=not SETTINGS.GENERAL.PRODUCTION,
        log_level=SETTINGS.GENERAL.LOG_LEVEL.lower(),
        access_log=True
    ) 