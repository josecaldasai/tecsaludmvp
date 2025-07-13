"""Main settings configuration."""

from .azure import AzureSettings
from .general import GeneralSettings
from .openai import OpenAISettings


class Settings:
    """Main settings class that combines all configuration settings."""

    def __init__(self):
        """Initialize all configuration settings."""
        self.GENERAL = GeneralSettings()
        self.AZURE = AzureSettings()
        self.OPENAI = OpenAISettings()

    def __repr__(self) -> str:
        """Return string representation of settings.

        Returns:
            str: String representation of settings.
        """
        return f"Settings(GENERAL={self.GENERAL}, AZURE={self.AZURE}, OPENAI={self.OPENAI})"


# Global settings instance
SETTINGS = Settings() 