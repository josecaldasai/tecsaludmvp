"""Azure configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AzureSettings(BaseSettings):
    """Azure configuration settings."""

    # Azure Storage Account
    AZURE_STORAGE_CONNECTION_STRING: str = Field(
        ..., description="Azure Storage Account connection string"
    )
    AZURE_STORAGE_CONTAINER_NAME: str = Field(
        default="documents", description="Azure Storage container name"
    )

    # Azure Document Intelligence
    AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT: str = Field(
        ..., description="Azure Document Intelligence endpoint URL"
    )
    AZURE_DOCUMENT_INTELLIGENCE_KEY: str = Field(
        ..., description="Azure Document Intelligence API key"
    )

    # Azure Active Directory (opcional para autenticación)
    AZURE_TENANT_ID: str = Field(
        default="", description="Azure Active Directory tenant ID"
    )
    AZURE_CLIENT_ID: str = Field(
        default="", description="Azure Active Directory client ID"
    )
    AZURE_CLIENT_SECRET: str = Field(
        default="", description="Azure Active Directory client secret"
    )

    model_config = SettingsConfigDict(env_file="app/env/v1/azure.env")


# Create settings instance
SETTINGS = AzureSettings() 