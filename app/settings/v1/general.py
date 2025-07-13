"""General configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings


class GeneralSettings(BaseSettings):
    """General application settings."""
    
    # Application configuration
    APP_NAME: str = Field(
        default="Document Processing API",
        description="Application name"
    )
    
    APP_VERSION: str = Field(
        default="1.0.0",
        description="Application version"
    )
    
    DEBUG: bool = Field(
        default=False,
        description="Debug mode"
    )
    
    PRODUCTION: bool = Field(
        default=False,
        description="Production mode"
    )
    
    # MongoDB configuration
    MONGODB_URL: str = Field(
        default="mongodb://localhost:27017",
        description="MongoDB connection URL"
    )
    
    MONGODB_DATABASE: str = Field(
        default="tecsalud_chatbot",
        description="MongoDB database name"
    )
    
    MONGODB_COLLECTION_DOCUMENTS: str = Field(
        default="documents",
        description="MongoDB documents collection name"
    )
    
    # Logging configuration
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level"
    )
    
    LOG_FORMAT: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format"
    )
    
    # Request limits
    MAX_FILE_SIZE: int = Field(
        default=50 * 1024 * 1024,  # 50MB
        description="Maximum file size in bytes"
    )
    
    MAX_FILES_PER_BATCH: int = Field(
        default=10,
        description="Maximum number of files per batch upload"
    )
    
    # File validation
    ALLOWED_FILE_EXTENSIONS: list = Field(
        default=["pdf", "jpg", "jpeg", "png", "tiff", "tif", "bmp", "gif"],
        description="Allowed file extensions"
    )
    
    # Retry configuration
    NUMBER_OF_RETRIES: int = Field(
        default=3,
        description="Number of retry attempts"
    )
    
    SECONDS_BETWEEN_RETRIES: int = Field(
        default=5,
        description="Seconds between retry attempts"
    )
    
    # Processing configuration
    PROCESSING_TIMEOUT: int = Field(
        default=300,  # 5 minutes
        description="Processing timeout in seconds"
    )
    
    # CORS configuration
    CORS_ORIGINS: list = Field(
        default=["http://localhost:3000", "http://localhost:8080", "http://localhost:5173"],
        description="CORS allowed origins"
    )
    
    # JWT configuration
    JWT_SECRET_KEY: str = Field(
        default="tecsalud-development-secret-key-2024",
        description="JWT secret key"
    )
    
    JWT_ALGORITHM: str = Field(
        default="HS256",
        description="JWT algorithm"
    )
    
    JWT_EXPIRATION_TIME: int = Field(
        default=3600,  # 1 hour
        description="JWT expiration time in seconds"
    )
    
    class Config:
        env_file = "app/env/v1/general.env"
        case_sensitive = True


# Create settings instance
SETTINGS = GeneralSettings() 