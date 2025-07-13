"""Azure Storage Token Service for managing Blob Storage authentication tokens."""

import re
from typing import Dict, Any
from datetime import datetime, timedelta
from urllib.parse import quote
import hmac
import hashlib
import base64

from app.settings.v1.azure import SETTINGS
from app.core.v1.exceptions import AppException
from app.core.v1.log_manager import LogManager


class AzureStorageTokenService:
    """
    Service for obtaining Azure Storage authentication tokens (SAS tokens).
    """
    
    def __init__(self):
        """Initialize Azure Storage Token Service."""
        self.logger = LogManager(__name__)
        
        # Get Azure Storage configuration
        self.connection_string = SETTINGS.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = SETTINGS.AZURE_STORAGE_CONTAINER_NAME
        
        # Parse connection string
        self._parse_connection_string()
        
        # Token cache
        self._cached_token = None
        self._token_expires_at = None
        
        self.logger.info("Azure Storage Token Service initialized successfully")
    
    def _parse_connection_string(self):
        """Parse the Azure Storage connection string to extract account name and key."""
        try:
            # Extract account name
            account_name_match = re.search(r'AccountName=([^;]+)', self.connection_string)
            if not account_name_match:
                raise AppException("Account name not found in connection string")
            self.account_name = account_name_match.group(1)
            
            # Extract account key
            account_key_match = re.search(r'AccountKey=([^;]+)', self.connection_string)
            if not account_key_match:
                raise AppException("Account key not found in connection string")
            self.account_key = account_key_match.group(1)
            
            # Extract endpoint suffix
            endpoint_suffix_match = re.search(r'EndpointSuffix=([^;]+)', self.connection_string)
            self.endpoint_suffix = endpoint_suffix_match.group(1) if endpoint_suffix_match else "core.windows.net"
            
            # Build base URL
            self.base_url = f"https://{self.account_name}.blob.{self.endpoint_suffix}"
            
            self.logger.info(f"Parsed Azure Storage config: account={self.account_name}, container={self.container_name}")
            
        except Exception as err:
            self.logger.error(f"Failed to parse Azure Storage connection string: {err}")
            raise AppException(f"Failed to parse Azure Storage connection string: {err}") from err
    
    def get_token(self) -> Dict[str, Any]:
        """
        Get a valid Azure Storage SAS token for the container.
        
        Returns:
            Dict containing SAS token and related information
            
        Raises:
            AppException: If token generation fails
        """
        try:
            # Check if we have a cached token that's still valid
            if self._is_token_valid():
                self.logger.info("Using cached Azure Storage token")
                return self._cached_token
            
            # Generate new SAS token
            self.logger.info("Generating new Azure Storage SAS token")
            token_data = self._generate_new_token()
            
            # Cache the token (tokens are valid for 1 hour)
            self._cached_token = token_data
            self._token_expires_at = datetime.now() + timedelta(minutes=55)  # Cache for 55 minutes for safety
            
            self.logger.info("Azure Storage SAS token generated successfully")
            return token_data
            
        except Exception as err:
            self.logger.error(f"Failed to get Azure Storage token: {err}")
            raise AppException(f"Failed to get Azure Storage token: {err}") from err
    
    def _is_token_valid(self) -> bool:
        """
        Check if the cached token is still valid.
        
        Returns:
            bool: True if token is valid, False otherwise
        """
        if self._cached_token is None or self._token_expires_at is None:
            return False
        
        return datetime.now() < self._token_expires_at
    
    def _generate_new_token(self) -> Dict[str, Any]:
        """
        Generate a new Azure Storage SAS token.
        
        Returns:
            Dict containing SAS token and related information
            
        Raises:
            AppException: If token generation fails
        """
        try:
            # Set expiration time (1 hour from now)
            expiry_time = datetime.utcnow() + timedelta(hours=1)
            expiry_str = expiry_time.strftime('%Y-%m-%dT%H:%M:%SZ')
            
            # Define resource (container)
            resource = 'c'  # Container
            
            # Define permissions (read and list)
            permissions = 'rl'  # Read and List permissions
            
            # Define service version
            service_version = '2021-06-08'
            
            # Build the string to sign
            string_to_sign = f"{permissions}\n\n{expiry_str}\n/{self.account_name}/{self.container_name}\n\n\n\n{service_version}\n\n\n\n\n"
            
            # Generate signature
            signature = self._generate_signature(string_to_sign)
            
            # Build SAS token
            sas_token = f"sv={service_version}&sr={resource}&sp={permissions}&se={quote(expiry_str)}&sig={quote(signature)}"
            
            # Build container URL with SAS token
            container_url = f"{self.base_url}/{self.container_name}?{sas_token}"
            
            token_data = {
                "sas_token": sas_token,
                "container_url": container_url,
                "base_url": self.base_url,
                "container_name": self.container_name,
                "account_name": self.account_name,
                "expires_at": expiry_str,
                "permissions": permissions,
                "resource_type": "container"
            }
            
            self.logger.info("Azure Storage SAS token generated successfully")
            return token_data
            
        except Exception as err:
            error_msg = f"Unexpected error generating Azure Storage SAS token: {err}"
            self.logger.error(error_msg)
            raise AppException(error_msg) from err
    
    def _generate_signature(self, string_to_sign: str) -> str:
        """
        Generate HMAC-SHA256 signature for the SAS token.
        
        Args:
            string_to_sign: The string to sign
            
        Returns:
            Base64-encoded signature
        """
        key = base64.b64decode(self.account_key)
        signature = hmac.new(key, string_to_sign.encode('utf-8'), hashlib.sha256).digest()
        return base64.b64encode(signature).decode('utf-8')
    
    def invalidate_token(self):
        """Invalidate the cached token."""
        self._cached_token = None
        self._token_expires_at = None
        self.logger.info("Azure Storage token cache invalidated")
    
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
            "account_name": self.account_name,
            "container_name": self.container_name,
            "base_url": self.base_url
        }
    
    def get_blob_url(self, blob_name: str) -> str:
        """
        Get URL for a specific blob with SAS token.
        
        Args:
            blob_name: Name of the blob
            
        Returns:
            Complete URL with SAS token
        """
        token_data = self.get_token()
        return f"{self.base_url}/{self.container_name}/{blob_name}?{token_data['sas_token']}" 