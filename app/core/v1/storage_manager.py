"""Azure Storage Manager for handling file uploads and downloads."""

import os
import uuid
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta

from azure.storage.blob import BlobServiceClient, BlobClient, ContainerClient, ContentSettings
from azure.storage.blob import generate_blob_sas, BlobSasPermissions
from azure.core.exceptions import AzureError, ResourceNotFoundError
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

from app.settings.v1.azure import SETTINGS
from app.core.v1.exceptions import StorageException
from app.core.v1.log_manager import LogManager


class StorageManager:
    """
    Azure Storage Manager for handling file operations.
    """

    def __init__(self):
        """
        Initialize Storage Manager.
        """
        self.logger = LogManager(__name__)
        
        # Azure Storage configuration
        self.connection_string = SETTINGS.AZURE_STORAGE_CONNECTION_STRING
        self.container_name = SETTINGS.AZURE_STORAGE_CONTAINER_NAME
        
        # Initialize Azure Storage client with optimized settings
        self.blob_service_client = BlobServiceClient.from_connection_string(
            self.connection_string,
            connection_timeout=300,  # 5 minutes timeout
            read_timeout=300,
            max_single_put_size=4 * 1024 * 1024,  # 4MB for single upload
            max_block_size=4 * 1024 * 1024,  # 4MB block size
            max_page_size=4 * 1024 * 1024,  # 4MB page size
        )
        
        # Ensure container exists
        self._ensure_container_exists()
        
        # Configuration for parallel processing
        self.max_workers = int(os.environ.get("AZURE_STORAGE_MAX_WORKERS", "8"))  # Default 8 workers
        self.chunk_size = int(os.environ.get("AZURE_STORAGE_CHUNK_SIZE", "4194304"))  # 4MB chunks
        
        self.logger.info("Storage Manager initialized successfully with parallel processing")

    def _ensure_container_exists(self):
        """
        Ensure that the storage container exists.
        """
        try:
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            # Create container if it doesn't exist
            container_client.create_container()
            
            self.logger.info(
                "Container created or already exists",
                container_name=self.container_name
            )
            
        except Exception as err:
            if "ContainerAlreadyExists" not in str(err):
                self.logger.error(f"Failed to create container: {err}")
                raise StorageException(f"Container creation failed: {err}") from err

    def upload_file(
        self,
        file_content: bytes,
        blob_name: str,
        content_type: str = "application/octet-stream"
    ) -> Dict[str, Any]:
        """
        Upload file to Azure Storage.
        
        Args:
            file_content (bytes): File content as bytes.
            blob_name (str): Name for the blob.
            content_type (str): Content type of the file.
            
        Returns:
            Dict[str, Any]: Upload result with blob info.
            
        Raises:
            StorageException: If upload fails.
        """
        try:
            self.logger.info(
                "Starting file upload",
                blob_name=blob_name,
                content_type=content_type,
                file_size=len(file_content)
            )
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Upload file with optimized settings
            blob_client.upload_blob(
                data=file_content,
                blob_type="BlockBlob",
                content_settings=ContentSettings(content_type=content_type),
                overwrite=True,
                # Azure Storage optimization parameters
                max_concurrency=self.max_workers,  # Parallel upload
                timeout=300,  # 5 minutes timeout
                validate_content=False  # Skip MD5 validation for speed
            )
            
            # Get blob URL
            blob_url = blob_client.url
            
            self.logger.info(
                "File uploaded successfully",
                blob_name=blob_name,
                blob_url=blob_url,
                file_size=len(file_content)
            )
            
            return {
                "blob_name": blob_name,
                "url": blob_url,
                "file_size": len(file_content),
                "content_type": content_type
            }
            
        except AzureError as err:
            self.logger.error(f"Azure Storage upload failed: {err}")
            raise StorageException(f"Upload failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during upload: {err}")
            raise StorageException(f"Unexpected upload error: {err}") from err

    def upload_files_batch(
        self,
        files: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Upload multiple files in parallel using Azure Storage optimizations.
        
        Args:
            files: List of file dictionaries with 'content', 'blob_name', 'content_type'
            progress_callback: Optional callback function for progress updates
            
        Returns:
            List[Dict[str, Any]]: List of upload results
        """
        try:
            start_time = time.time()
            
            self.logger.info(
                "Starting batch file upload",
                file_count=len(files),
                max_workers=self.max_workers
            )
            
            upload_results = []
            
            def upload_single_file(file_info):
                """Helper function to upload a single file"""
                try:
                    result = self.upload_file(
                        file_content=file_info['content'],
                        blob_name=file_info['blob_name'],
                        content_type=file_info.get('content_type', 'application/octet-stream')
                    )
                    result['status'] = 'success'
                    # Preserve original_index for mapping back to files
                    result['original_index'] = file_info.get('original_index', 0)
                    result['filename'] = file_info.get('filename', 'unknown')
                    return result
                except Exception as e:
                    return {
                        'blob_name': file_info['blob_name'],
                        'status': 'error',
                        'error': str(e),
                        'file_size': len(file_info['content']),
                        # Preserve original_index even in errors
                        'original_index': file_info.get('original_index', 0),
                        'filename': file_info.get('filename', 'unknown')
                    }
            
            # Use ThreadPoolExecutor for parallel uploads
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Submit all upload tasks
                future_to_file = {
                    executor.submit(upload_single_file, file_info): file_info
                    for file_info in files
                }
                
                # Process completed uploads
                completed_count = 0
                for future in as_completed(future_to_file):
                    try:
                        result = future.result()
                        upload_results.append(result)
                        completed_count += 1
                        
                        # Call progress callback if provided
                        if progress_callback:
                            progress_callback(completed_count, len(files))
                            
                    except Exception as e:
                        file_info = future_to_file[future]
                        upload_results.append({
                            'blob_name': file_info['blob_name'],
                            'status': 'error',
                            'error': str(e),
                            'file_size': len(file_info['content'])
                        })
                        completed_count += 1
            
            # Calculate statistics
            successful_uploads = [r for r in upload_results if r['status'] == 'success']
            failed_uploads = [r for r in upload_results if r['status'] == 'error']
            
            total_time = time.time() - start_time
            
            self.logger.info(
                "Batch upload completed",
                total_files=len(files),
                successful_uploads=len(successful_uploads),
                failed_uploads=len(failed_uploads),
                total_time_seconds=round(total_time, 2),
                average_time_per_file=round(total_time / len(files), 2)
            )
            
            return upload_results
            
        except Exception as err:
            self.logger.error(f"Batch upload failed: {err}")
            raise StorageException(f"Batch upload failed: {err}") from err

    def download_file(self, blob_name: str) -> Dict[str, Any]:
        """
        Download file from Azure Storage.
        
        Args:
            blob_name (str): Name of the blob to download.
            
        Returns:
            Dict[str, Any]: File information including content.
            
        Raises:
            StorageException: If download fails.
        """
        try:
            self.logger.info(
                "Starting file download",
                blob_name=blob_name
            )
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Download blob
            blob_data = blob_client.download_blob()
            file_content = blob_data.readall()
            
            # Get blob properties
            blob_properties = blob_client.get_blob_properties()
            
            self.logger.info(
                "File downloaded successfully",
                blob_name=blob_name,
                file_size=len(file_content)
            )
            
            return {
                "blob_name": blob_name,
                "content": file_content,
                "content_type": blob_properties.content_settings.content_type,
                "file_size": len(file_content),
                "last_modified": blob_properties.last_modified,
                "etag": blob_properties.etag
            }
            
        except ResourceNotFoundError as err:
            self.logger.warning(f"Blob not found: {blob_name}")
            raise StorageException(f"File not found: {blob_name}") from err
        except AzureError as err:
            self.logger.error(f"Azure Storage download failed: {err}")
            raise StorageException(f"Download failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during download: {err}")
            raise StorageException(f"Unexpected download error: {err}") from err

    def delete_file(self, blob_name: str) -> bool:
        """
        Delete file from Azure Storage.
        
        Args:
            blob_name (str): Name of the blob to delete.
            
        Returns:
            bool: True if deletion was successful.
            
        Raises:
            StorageException: If deletion fails.
        """
        try:
            self.logger.info(
                "Starting file deletion",
                blob_name=blob_name
            )
            
            # Get blob client
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            # Delete blob
            blob_client.delete_blob()
            
            self.logger.info(
                "File deleted successfully",
                blob_name=blob_name
            )
            
            return True
            
        except ResourceNotFoundError as err:
            self.logger.warning(f"Blob not found for deletion: {blob_name}")
            return False
        except AzureError as err:
            self.logger.error(f"Azure Storage deletion failed: {err}")
            raise StorageException(f"Deletion failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during deletion: {err}")
            raise StorageException(f"Unexpected deletion error: {err}") from err

    def list_files(self, prefix: str = None, limit: int = 100) -> List[Dict[str, Any]]:
        """
        List files in Azure Storage container.
        
        Args:
            prefix (str, optional): Prefix to filter blobs.
            limit (int): Maximum number of files to return.
            
        Returns:
            List[Dict[str, Any]]: List of file information.
            
        Raises:
            StorageException: If listing fails.
        """
        try:
            self.logger.info(
                "Starting file listing",
                prefix=prefix,
                limit=limit
            )
            
            # Get container client
            container_client = self.blob_service_client.get_container_client(
                self.container_name
            )
            
            # List blobs
            blobs = container_client.list_blobs(name_starts_with=prefix)
            
            files = []
            count = 0
            
            for blob in blobs:
                if count >= limit:
                    break
                    
                files.append({
                    "blob_name": blob.name,
                    "file_size": blob.size,
                    "content_type": blob.content_settings.content_type if blob.content_settings else None,
                    "last_modified": blob.last_modified,
                    "etag": blob.etag
                })
                
                count += 1
            
            self.logger.info(
                "File listing completed",
                file_count=len(files),
                prefix=prefix
            )
            
            return files
            
        except AzureError as err:
            self.logger.error(f"Azure Storage listing failed: {err}")
            raise StorageException(f"File listing failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during listing: {err}")
            raise StorageException(f"Unexpected listing error: {err}") from err

    def generate_sas_url(
        self,
        blob_name: str,
        expiry_hours: int = 24,
        permissions: str = "r"
    ) -> str:
        """
        Generate SAS URL for a blob.
        
        Args:
            blob_name (str): Name of the blob.
            expiry_hours (int): Hours until expiry.
            permissions (str): Permissions (r=read, w=write, d=delete).
            
        Returns:
            str: SAS URL.
            
        Raises:
            StorageException: If SAS generation fails.
        """
        try:
            self.logger.info(
                "Generating SAS URL",
                blob_name=blob_name,
                expiry_hours=expiry_hours,
                permissions=permissions
            )
            
            # Generate SAS token
            sas_token = generate_blob_sas(
                account_name=self.blob_service_client.account_name,
                container_name=self.container_name,
                blob_name=blob_name,
                account_key=self.blob_service_client.credential.account_key,
                permission=BlobSasPermissions(read="r" in permissions),
                expiry=datetime.utcnow() + timedelta(hours=expiry_hours)
            )
            
            # Generate full URL
            blob_client = self.blob_service_client.get_blob_client(
                container=self.container_name,
                blob=blob_name
            )
            
            sas_url = f"{blob_client.url}?{sas_token}"
            
            self.logger.info(
                "SAS URL generated successfully",
                blob_name=blob_name,
                expiry_hours=expiry_hours
            )
            
            return sas_url
            
        except AzureError as err:
            self.logger.error(f"Azure Storage SAS generation failed: {err}")
            raise StorageException(f"SAS generation failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during SAS generation: {err}")
            raise StorageException(f"Unexpected SAS generation error: {err}") from err 