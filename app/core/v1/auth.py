"""Authentication handler for JWT tokens."""

import jwt
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from fastapi import HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.settings.v1.settings import SETTINGS
from app.core.v1.exceptions import UnauthorizedException
from app.core.v1.log_manager import LogManager


# Initialize security scheme
security = HTTPBearer()


class AuthManager:
    """Authentication manager for handling JWT tokens."""

    def __init__(self):
        """Initialize Authentication Manager."""
        self.logger = LogManager(__name__)
        self.secret_key = SETTINGS.GENERAL.JWT_SECRET_KEY
        self.algorithm = SETTINGS.GENERAL.JWT_ALGORITHM
        self.expiration_time = SETTINGS.GENERAL.JWT_EXPIRATION_TIME

    def create_access_token(self, data: Dict[str, Any]) -> str:
        """Create a new access token.

        Args:
            data (Dict[str, Any]): Token payload data.

        Returns:
            str: Generated JWT token.

        Raises:
            UnauthorizedException: If token creation fails.
        """
        try:
            to_encode = data.copy()
            expire = datetime.utcnow() + timedelta(seconds=self.expiration_time)
            to_encode.update({"exp": expire})
            
            encoded_jwt = jwt.encode(to_encode, self.secret_key, algorithm=self.algorithm)
            
            self.logger.info(
                "Access token created successfully",
                user_id=data.get("sub"),
                expires_at=expire.isoformat()
            )
            
            return encoded_jwt
            
        except Exception as err:
            self.logger.error(f"Token creation failed: {err}")
            raise UnauthorizedException(f"Token creation failed: {err}") from err

    def verify_token(self, token: str) -> Dict[str, Any]:
        """Verify and decode JWT token.

        Args:
            token (str): JWT token to verify.

        Returns:
            Dict[str, Any]: Decoded token payload.

        Raises:
            UnauthorizedException: If token verification fails.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=[self.algorithm])
            
            # Check if token is expired
            exp = payload.get("exp")
            if exp and datetime.utcnow().timestamp() > exp:
                raise UnauthorizedException("Token has expired")
            
            self.logger.debug(
                "Token verified successfully",
                user_id=payload.get("sub")
            )
            
            return payload
            
        except jwt.ExpiredSignatureError:
            self.logger.warning("Token has expired")
            raise UnauthorizedException("Token has expired")
        except jwt.InvalidTokenError as err:
            self.logger.warning(f"Invalid token: {err}")
            raise UnauthorizedException(f"Invalid token: {err}")
        except Exception as err:
            self.logger.error(f"Token verification failed: {err}")
            raise UnauthorizedException(f"Token verification failed: {err}") from err

    def get_current_user(self, token: str) -> Dict[str, Any]:
        """Get current user from token.

        Args:
            token (str): JWT token.

        Returns:
            Dict[str, Any]: User information.

        Raises:
            UnauthorizedException: If user extraction fails.
        """
        try:
            payload = self.verify_token(token)
            user_id = payload.get("sub")
            
            if user_id is None:
                raise UnauthorizedException("Could not validate credentials")
            
            return {
                "user_id": user_id,
                "username": payload.get("username"),
                "email": payload.get("email"),
                "roles": payload.get("roles", []),
                "exp": payload.get("exp")
            }
            
        except Exception as err:
            self.logger.error(f"User extraction failed: {err}")
            raise UnauthorizedException(f"Could not validate credentials: {err}") from err


# Initialize global auth manager
auth_manager = AuthManager()


def get_current_user_dependency(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, Any]:
    """FastAPI dependency for getting current user.

    Args:
        credentials (HTTPAuthorizationCredentials): HTTP authorization credentials.

    Returns:
        Dict[str, Any]: Current user information.

    Raises:
        HTTPException: If authentication fails.
    """
    try:
        return auth_manager.get_current_user(credentials.credentials)
    except UnauthorizedException as err:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(err),
            headers={"WWW-Authenticate": "Bearer"},
        ) from err


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[Dict[str, Any]]:
    """FastAPI dependency for optional authentication.

    Args:
        credentials (Optional[HTTPAuthorizationCredentials]): HTTP authorization credentials.

    Returns:
        Optional[Dict[str, Any]]: Current user information or None.
    """
    if credentials is None:
        return None
    
    try:
        return auth_manager.get_current_user(credentials.credentials)
    except UnauthorizedException:
        return None 