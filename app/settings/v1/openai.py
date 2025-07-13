"""OpenAI configuration settings."""

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class OpenAISettings(BaseSettings):
    """OpenAI configuration settings."""

    # OpenAI Configuration
    OPENAI_API_KEY: str = Field(
        default="", description="OpenAI API key"
    )
    OPENAI_API_VERSION: str = Field(
        default="2024-02-01", description="OpenAI API version"
    )

    # Azure OpenAI Configuration
    AZURE_OPENAI_ENDPOINT: str = Field(
        default="", description="Azure OpenAI endpoint URL"
    )
    AZURE_OPENAI_API_KEY: str = Field(
        default="", description="Azure OpenAI API key"
    )
    AZURE_OPENAI_API_VERSION: str = Field(
        default="2024-02-01", description="Azure OpenAI API version"
    )

    # Models Configuration
    CHAT_MODEL: str = Field(
        default="gpt-4o-mini", description="Chat completion model name"
    )
    EMBEDDING_MODEL: str = Field(
        default="text-embedding-ada-002", description="Embedding model name"
    )
    COMPLETION_MODEL: str = Field(
        default="gpt-4o-mini", description="Text completion model name"
    )

    # Model Parameters
    MAX_TOKENS: int = Field(
        default=4000, description="Maximum tokens per request"
    )
    TEMPERATURE: float = Field(
        default=0.7, description="Model temperature (0.0 to 1.0)"
    )
    TOP_P: float = Field(
        default=1.0, description="Top-p sampling parameter"
    )
    FREQUENCY_PENALTY: float = Field(
        default=0.0, description="Frequency penalty parameter"
    )
    PRESENCE_PENALTY: float = Field(
        default=0.0, description="Presence penalty parameter"
    )

    # Embeddings Configuration
    EMBEDDING_DIMENSION: int = Field(
        default=1536, description="Embedding vector dimension"
    )
    K_EMBEDDINGS: int = Field(
        default=20, description="Number of similar embeddings to retrieve"
    )

    # Chat Configuration
    MAX_CONVERSATION_HISTORY: int = Field(
        default=10, description="Maximum conversation history length"
    )
    CONTEXT_WINDOW_SIZE: int = Field(
        default=32000, description="Context window size in tokens"
    )

    model_config = SettingsConfigDict(env_file="app/env/v1/openai.env") 