"""Tokens API router for Azure Speech and Storage authentication."""

from fastapi import APIRouter, HTTPException
from datetime import datetime

from app.apis.v1.types_out import (
    AzureSpeechTokenResponse,
    AzureStorageTokenResponse
)
from app.core.v1.azure_speech_token_service import AzureSpeechTokenService
from app.core.v1.azure_storage_token_service import AzureStorageTokenService
from app.core.v1.exceptions import AppException
from app.core.v1.log_manager import LogManager

# Initialize router
router = APIRouter()

# Initialize services
speech_token_service = AzureSpeechTokenService()
storage_token_service = AzureStorageTokenService()
logger = LogManager(__name__)


@router.get("/speech", response_model=AzureSpeechTokenResponse)
async def get_speech_token():
    """
    Get Azure Speech Services authentication token.
    
    Returns:
        AzureSpeechTokenResponse: Token and metadata for Speech Services (STT/TTS)
    """
    try:
        logger.info("Requesting Azure Speech token")
        
        # Get token from service
        token = speech_token_service.get_token()
        
        # Build response
        response = AzureSpeechTokenResponse(
            access_token=token,
            token_type="Bearer",
            expires_in=600,  # 10 minutes
            region=speech_token_service.speech_region,
            issued_at=datetime.now().isoformat()
        )
        
        logger.info("Azure Speech token retrieved successfully")
        return response
        
    except AppException as err:
        logger.error(f"Azure Speech token request failed: {err}")
        raise HTTPException(status_code=500, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error getting Azure Speech token: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/storage", response_model=AzureStorageTokenResponse)
async def get_storage_token():
    """
    Get Azure Storage SAS token for blob container access.
    
    Returns:
        AzureStorageTokenResponse: SAS token and metadata for Storage access
    """
    try:
        logger.info("Requesting Azure Storage token")
        
        # Get token from service
        token_data = storage_token_service.get_token()
        
        # Build response
        response = AzureStorageTokenResponse(
            sas_token=token_data["sas_token"],
            container_url=token_data["container_url"],
            base_url=token_data["base_url"],
            container_name=token_data["container_name"],
            account_name=token_data["account_name"],
            expires_at=token_data["expires_at"],
            permissions=token_data["permissions"],
            resource_type=token_data["resource_type"],
            issued_at=datetime.now().isoformat()
        )
        
        logger.info("Azure Storage token retrieved successfully")
        return response
        
    except AppException as err:
        logger.error(f"Azure Storage token request failed: {err}")
        raise HTTPException(status_code=500, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error getting Azure Storage token: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/speech/info")
async def get_speech_token_info():
    """
    Get information about the current Azure Speech token.
    
    Returns:
        Dict: Token information and status
    """
    try:
        logger.info("Requesting Azure Speech token info")
        
        token_info = speech_token_service.get_token_info()
        
        logger.info("Azure Speech token info retrieved successfully")
        return token_info
        
    except Exception as err:
        logger.error(f"Error getting Azure Speech token info: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/storage/info")
async def get_storage_token_info():
    """
    Get information about the current Azure Storage token.
    
    Returns:
        Dict: Token information and status
    """
    try:
        logger.info("Requesting Azure Storage token info")
        
        token_info = storage_token_service.get_token_info()
        
        logger.info("Azure Storage token info retrieved successfully")
        return token_info
        
    except Exception as err:
        logger.error(f"Error getting Azure Storage token info: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.post("/speech/invalidate")
async def invalidate_speech_token():
    """
    Invalidate the cached Azure Speech token.
    
    Returns:
        Dict: Success message
    """
    try:
        logger.info("Invalidating Azure Speech token")
        
        speech_token_service.invalidate_token()
        
        logger.info("Azure Speech token invalidated successfully")
        return {"message": "Azure Speech token invalidated successfully"}
        
    except Exception as err:
        logger.error(f"Error invalidating Azure Speech token: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.post("/storage/invalidate")
async def invalidate_storage_token():
    """
    Invalidate the cached Azure Storage token.
    
    Returns:
        Dict: Success message
    """
    try:
        logger.info("Invalidating Azure Storage token")
        
        storage_token_service.invalidate_token()
        
        logger.info("Azure Storage token invalidated successfully")
        return {"message": "Azure Storage token invalidated successfully"}
        
    except Exception as err:
        logger.error(f"Error invalidating Azure Storage token: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}")


@router.get("/storage/blob/{blob_name}")
async def get_blob_url(blob_name: str):
    """
    Get a signed URL for a specific blob.
    
    Args:
        blob_name: Name of the blob
        
    Returns:
        Dict: Blob URL with SAS token
    """
    try:
        logger.info(f"Requesting blob URL for: {blob_name}")
        
        blob_url = storage_token_service.get_blob_url(blob_name)
        
        response = {
            "blob_name": blob_name,
            "blob_url": blob_url,
            "generated_at": datetime.now().isoformat()
        }
        
        logger.info(f"Blob URL generated successfully for: {blob_name}")
        return response
        
    except AppException as err:
        logger.error(f"Blob URL generation failed: {err}")
        raise HTTPException(status_code=500, detail=str(err))
    except Exception as err:
        logger.error(f"Unexpected error generating blob URL: {err}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {err}") 