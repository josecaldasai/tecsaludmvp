"""Main FastAPI application for TecSalud Chatbot Document Processing API."""

import uvicorn
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.openapi.docs import get_swagger_ui_html
from fastapi.openapi.utils import get_openapi
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
    DatabaseException
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
    
    # Create database indexes if needed
    try:
        from app.core.v1.mongodb_manager import MongoDBManager
        mongodb_manager = MongoDBManager()
        
        # Create text search index
        mongodb_manager.create_index(
            collection_name=SETTINGS.GENERAL.MONGODB_COLLECTION_DOCUMENTS,
            index_spec=[("extracted_text", "text"), ("filename", "text")],
            name="text_search_index"
        )
        
        # Create user index
        mongodb_manager.create_index(
            collection_name=SETTINGS.GENERAL.MONGODB_COLLECTION_DOCUMENTS,
            index_spec="user_id",
            name="user_id_index"
        )
        
        # Create processing status index
        mongodb_manager.create_index(
            collection_name=SETTINGS.GENERAL.MONGODB_COLLECTION_DOCUMENTS,
            index_spec="processing_status",
            name="processing_status_index"
        )
        
        logger.info("Database indexes created successfully")
        
    except Exception as err:
        logger.warning(f"Failed to create database indexes: {err}")
    
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