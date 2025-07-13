"""Azure Speech Token Service for managing STT/TTS authentication tokens."""

import requests
from typing import Dict, Any
from datetime import datetime, timedelta

from app.settings.v1.azure import SETTINGS
from app.core.v1.exceptions import AppException
from app.core.v1.log_manager import LogManager


class AzureSpeechTokenService:
    """
    Service for obtaining Azure Speech Services authentication tokens.
    """
    
    def __init__(self):
        """Initialize Azure Speech Token Service."""
        self.logger = LogManager(__name__)
        
        # Get Azure Speech configuration
        self.speech_key = SETTINGS.AZURE_SPEECH_KEY
        self.speech_region = SETTINGS.AZURE_SPEECH_REGION
        
        # Build endpoint URL
        self.token_endpoint = f"https://{self.speech_region}.api.cognitive.microsoft.com/sts/v1.0/issueToken"
        
        # Token cache
        self._cached_token = None
        self._token_expires_at = None
        
        self.logger.info("Azure Speech Token Service initialized successfully")
    
    def get_token(self) -> str:
        """
        Get a valid Azure Speech Services authentication token.
        
        Returns:
            str: Valid authentication token
            
        Raises:
            AppException: If token generation fails
        """
        try:
            # Check if we have a cached token that's still valid
            if self._is_token_valid():
                self.logger.info("Using cached Azure Speech token")
                return self._cached_token
            
            # Generate new token
            self.logger.info("Generating new Azure Speech token")
            token = self._generate_new_token()
            
            # Cache the token (tokens are valid for 10 minutes)
            self._cached_token = token
            self._token_expires_at = datetime.now() + timedelta(minutes=9)  # Cache for 9 minutes for safety
            
            self.logger.info("Azure Speech token generated successfully")
            return token
            
        except Exception as err:
            self.logger.error(f"Failed to get Azure Speech token: {err}")
            raise AppException(f"Failed to get Azure Speech token: {err}") from err
    
    def _is_token_valid(self) -> bool:
        """
        Check if the cached token is still valid.
        
        Returns:
            bool: True if token is valid, False otherwise
        """
        if self._cached_token is None or self._token_expires_at is None:
            return False
        
        return datetime.now() < self._token_expires_at
    
    def _generate_new_token(self) -> str:
        """
        Generate a new Azure Speech Services token.
        
        Returns:
            str: New authentication token
            
        Raises:
            AppException: If token generation fails
        """
        try:
            headers = {
                "Ocp-Apim-Subscription-Key": self.speech_key,
                "Content-Type": "application/x-www-form-urlencoded",
                "Content-Length": "0"
            }
            
            self.logger.info(f"Requesting token from Azure Speech endpoint: {self.token_endpoint}")
            
            response = requests.post(
                self.token_endpoint,
                headers=headers,
                timeout=30
            )
            
            if response.status_code == 200:
                token = response.text
                self.logger.info("Azure Speech token generated successfully")
                return token
            else:
                error_msg = f"Azure Speech token request failed: {response.status_code} - {response.text}"
                self.logger.error(error_msg)
                raise AppException(error_msg)
                
        except requests.exceptions.RequestException as err:
            error_msg = f"Network error while requesting Azure Speech token: {err}"
            self.logger.error(error_msg)
            raise AppException(error_msg) from err
        except Exception as err:
            error_msg = f"Unexpected error generating Azure Speech token: {err}"
            self.logger.error(error_msg)
            raise AppException(error_msg) from err
    
    def invalidate_token(self):
        """Invalidate the cached token."""
        self._cached_token = None
        self._token_expires_at = None
        self.logger.info("Azure Speech token cache invalidated")
    
    def get_token_info(self) -> Dict[str, Any]:
        """
        Get information about the current token.
        
        Returns:
            Dict containing token information
        """
        return {
            "has_cached_token": self._cached_token is not None,
            "token_expires_at": self._token_expires_at.isoformat() if self._token_expires_at else None,
            "is_token_valid": self._is_token_valid(),
            "speech_region": self.speech_region,
            "token_endpoint": self.token_endpoint
        } 