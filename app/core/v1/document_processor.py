"""Document Processor for handling complete document workflow."""

import os
import uuid
from typing import Dict, Any, List, Optional
from datetime import datetime
import time

from app.core.v1.storage_manager import StorageManager
from app.core.v1.ocr_manager import OCRManager
from app.core.v1.mongodb_manager import MongoDBManager
from app.core.v1.filename_parser import MedicalFilenameParser
from app.core.v1.exceptions import (
    DocumentProcessorException,
    StorageException,
    OCRException,
    DatabaseException
)
from app.core.v1.log_manager import LogManager


class DocumentProcessor:
    """
    Document Processor for orchestrating the complete document processing workflow.
    """

    def __init__(self):
        """
        Initialize Document Processor.
        """
        self.logger = LogManager(__name__)
        
        # Initialize managers
        self.storage_manager = StorageManager()
        self.ocr_manager = OCRManager()
        self.mongodb_manager = MongoDBManager()
        self.filename_parser = MedicalFilenameParser()
        
        self.logger.info("Document Processor initialized successfully")
        
        # Configuration for parallel processing
        self.max_workers = int(os.environ.get("BATCH_MAX_WORKERS", "4"))  # Default 4 workers
        self.batch_size = int(os.environ.get("BATCH_CHUNK_SIZE", "10"))  # Default 10 documents per chunk

    def process_single_document(
        self,
        file_content: bytes,
        filename: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process a single document through the complete workflow.
        
        Args:
            file_content (bytes): Document content.
            filename (str): Original filename.
            description (Optional[str]): Document description.
            tags (Optional[List[str]]): Document tags.
            user_id (Optional[str]): User ID who uploaded the document.
            
        Returns:
            Dict[str, Any]: Processing results.
            
        Raises:
            DocumentProcessorException: If processing fails.
        """
        try:
            self.logger.info(
                "Starting single document processing",
                filename=filename,
                size=len(file_content)
            )
            
            # Parse medical information from filename
            medical_info = self.filename_parser.parse_filename(filename)
            
            # Generate unique blob name
            blob_name = f"{uuid.uuid4().hex}_{filename}"
            
            # Step 1: Upload to Azure Storage
            upload_result = self.storage_manager.upload_file(
                file_content=file_content,
                blob_name=blob_name,
                content_type=self._get_content_type(filename)
            )
            
            self.logger.info(
                "Document uploaded to storage",
                blob_name=blob_name,
                upload_result=upload_result
            )
            
            # Step 2: Perform OCR
            ocr_result = self.ocr_manager.extract_text_from_bytes(
                file_content=file_content,
                content_type=self._get_content_type(filename)
            )
            
            self.logger.info(
                "OCR processing completed",
                filename=filename,
                extracted_text_length=len(ocr_result.get("extracted_text", "")),
                page_count=ocr_result.get("page_count", 0)
            )
            
            # Step 3: Prepare document for MongoDB
            document = {
                "processing_id": str(uuid.uuid4()),
                "filename": filename,
                "content_type": self._get_content_type(filename),
                "file_size": len(file_content),
                "user_id": user_id,
                "storage_info": {
                    "blob_name": blob_name,
                    "blob_url": upload_result["url"],
                    "container_name": "documents"
                },
                "extracted_text": ocr_result.get("extracted_text", ""),
                "processing_status": "completed",
                "description": description,
                "tags": tags or [],
                # Campos médicos al primer nivel para búsquedas eficientes
                "expediente": medical_info.expediente,
                "nombre_paciente": medical_info.nombre_paciente,
                "numero_episodio": medical_info.numero_episodio,
                "categoria": medical_info.categoria,
                "medical_info_valid": medical_info.is_valid,
                "medical_info_error": medical_info.error_message
            }
            
            # Step 4: Save document to MongoDB
            document_id = self.mongodb_manager.save_document(document)
            
            self.logger.info(
                "Document processing completed successfully",
                document_id=document_id,
                blob_name=blob_name,
                filename=filename
            )
            
            return {
                "document_id": document_id,
                "processing_id": document["processing_id"],
                "filename": filename,
                "storage_info": document["storage_info"],
                "ocr_summary": {
                    "text_length": len(ocr_result.get("extracted_text", "")),
                    "page_count": ocr_result.get("page_count", 0),
                    "table_count": ocr_result.get("table_count", 0)
                },
                "processing_status": "completed",
                "processing_timestamp": datetime.now().isoformat(),
                # Campos médicos al primer nivel para búsquedas eficientes
                "expediente": medical_info.expediente,
                "nombre_paciente": medical_info.nombre_paciente,
                "numero_episodio": medical_info.numero_episodio,
                "categoria": medical_info.categoria,
                "medical_info_valid": medical_info.is_valid,
                "medical_info_error": medical_info.error_message
            }
            
        except (StorageException, OCRException, DatabaseException) as err:
            self.logger.error(
                "Document processing failed",
                filename=filename,
                error=str(err)
            )
            
            # Try to save error document to MongoDB
            try:
                medical_info = self.filename_parser.parse_filename(filename)
                
                error_document = {
                    "processing_id": str(uuid.uuid4()),
                    "filename": filename,
                    "content_type": self._get_content_type(filename),
                    "file_size": len(file_content),
                    "user_id": user_id,
                    "storage_info": {},
                    "extracted_text": "",
                    "processing_status": "error",
                    "description": description,
                    "tags": tags or [],
                    # Campos médicos al primer nivel para búsquedas eficientes
                    "expediente": medical_info.expediente,
                    "nombre_paciente": medical_info.nombre_paciente,
                    "numero_episodio": medical_info.numero_episodio,
                    "categoria": medical_info.categoria,
                    "medical_info_valid": medical_info.is_valid,
                    "medical_info_error": medical_info.error_message,
                    "error_message": str(err)
                }
                
                document_id = self.mongodb_manager.save_document(error_document)
                
                return {
                    "document_id": document_id,
                    "processing_id": error_document["processing_id"],
                    "filename": filename,
                    "storage_info": {},
                    "ocr_summary": {
                        "text_length": 0,
                        "page_count": 0,
                        "table_count": 0
                    },
                    "processing_status": "error",
                    "processing_timestamp": datetime.now().isoformat(),
                    # Campos médicos al primer nivel para búsquedas eficientes
                    "expediente": medical_info.expediente,
                    "nombre_paciente": medical_info.nombre_paciente,
                    "numero_episodio": medical_info.numero_episodio,
                    "categoria": medical_info.categoria,
                    "medical_info_valid": medical_info.is_valid,
                    "medical_info_error": medical_info.error_message,
                    "error_message": str(err)
                }
            except Exception as save_err:
                self.logger.error(f"Failed to save error document: {save_err}")
                raise DocumentProcessorException(f"Document processing failed: {err}") from err
            
        except Exception as err:
            self.logger.error(
                "Unexpected error in document processing",
                filename=filename,
                error=str(err)
            )
            
            # Try to save error document to MongoDB
            try:
                medical_info = self.filename_parser.parse_filename(filename)
                
                error_document = {
                    "processing_id": str(uuid.uuid4()),
                    "filename": filename,
                    "content_type": self._get_content_type(filename),
                    "file_size": len(file_content),
                    "user_id": user_id,
                    "storage_info": {},
                    "extracted_text": "",
                    "processing_status": "error",
                    "description": description,
                    "tags": tags or [],
                    # Campos médicos al primer nivel para búsquedas eficientes
                    "expediente": medical_info.expediente,
                    "nombre_paciente": medical_info.nombre_paciente,
                    "numero_episodio": medical_info.numero_episodio,
                    "categoria": medical_info.categoria,
                    "medical_info_valid": medical_info.is_valid,
                    "medical_info_error": medical_info.error_message,
                    "error_message": str(err)
                }
                
                document_id = self.mongodb_manager.save_document(error_document)
                
                return {
                    "document_id": document_id,
                    "processing_id": error_document["processing_id"],
                    "filename": filename,
                    "storage_info": {},
                    "ocr_summary": {
                        "text_length": 0,
                        "page_count": 0,
                        "table_count": 0
                    },
                    "processing_status": "error",
                    "processing_timestamp": datetime.now().isoformat(),
                    # Campos médicos al primer nivel para búsquedas eficientes
                    "expediente": medical_info.expediente,
                    "nombre_paciente": medical_info.nombre_paciente,
                    "numero_episodio": medical_info.numero_episodio,
                    "categoria": medical_info.categoria,
                    "medical_info_valid": medical_info.is_valid,
                    "medical_info_error": medical_info.error_message,
                    "error_message": str(err)
                }
            except Exception as save_err:
                self.logger.error(f"Failed to save error document: {save_err}")
                raise DocumentProcessorException(f"Unexpected processing error: {err}") from err

    def process_batch_documents(
        self,
        files: List[Dict[str, Any]],
        batch_description: Optional[str] = None,
        batch_tags: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process multiple documents in batch with optimized error handling.
        
        Args:
            files (List[Dict[str, Any]]): List of file dictionaries with content, filename, etc.
            batch_description (Optional[str]): Common description for all documents.
            batch_tags (Optional[List[str]]): Common tags for all documents.
            user_id (Optional[str]): User ID for all documents in the batch.
            
        Returns:
            Dict[str, Any]: Batch processing results with success/failure breakdown.
            
        Raises:
            DocumentProcessorException: If batch processing fails completely.
        """
        try:
            batch_id = str(uuid.uuid4())
            batch_timestamp = datetime.now()
            
            self.logger.info(
                "Starting batch document processing",
                batch_id=batch_id,
                file_count=len(files),
                user_id=user_id,
                batch_description=batch_description
            )
            
            successful_documents = []
            failed_documents = []
            
            for index, file_info in enumerate(files):
                try:
                    self.logger.info(
                        "Processing document in batch",
                        batch_id=batch_id,
                        filename=file_info["filename"],
                        batch_index=index,
                        total_files=len(files)
                    )
                    
                    # Process individual document with batch information
                    result = self.process_single_document(
                        file_content=file_info["content"],
                        filename=file_info["filename"],
                        description=file_info.get("description") or batch_description,
                        tags=(file_info.get("tags") or []) + (batch_tags or []),
                        user_id=file_info.get("user_id") or user_id
                    )
                    
                    # Add batch information to the document in MongoDB
                    try:
                        self.mongodb_manager.update_document(
                            result["document_id"],
                            {
                                "batch_info": {
                                    "batch_id": batch_id,
                                    "batch_index": index,
                                    "batch_timestamp": batch_timestamp.isoformat(),
                                    "batch_description": batch_description,
                                    "is_batch_document": True
                                }
                            }
                        )
                    except Exception as batch_update_err:
                        self.logger.warning(
                            "Failed to update document with batch info",
                            document_id=result["document_id"],
                            batch_id=batch_id,
                            error=str(batch_update_err)
                        )
                    
                    # Add batch information to the successful result
                    result["batch_id"] = batch_id
                    result["batch_index"] = index
                    result["batch_timestamp"] = batch_timestamp.isoformat()
                    result["batch_description"] = batch_description
                    
                    successful_documents.append(result)
                    
                    self.logger.info(
                        "Document processed successfully in batch",
                        batch_id=batch_id,
                        document_id=result["document_id"],
                        filename=file_info["filename"],
                        batch_index=index
                    )
                    
                except Exception as err:
                    error_details = {
                        "filename": file_info["filename"],
                        "batch_index": index,
                        "error": str(err),
                        "error_type": type(err).__name__,
                        "timestamp": datetime.now().isoformat()
                    }
                    
                    failed_documents.append(error_details)
                    
                    self.logger.error(
                        "Document processing failed in batch",
                        batch_id=batch_id,
                        filename=file_info["filename"],
                        batch_index=index,
                        error=str(err),
                        error_type=type(err).__name__
                    )
                    
                    # Continue processing other documents even if one fails
                    continue
            
            # Calculate processing statistics
            total_files = len(files)
            processed_count = len(successful_documents)
            failed_count = len(failed_documents)
            success_rate = (processed_count / total_files * 100) if total_files > 0 else 0
            
            # Determine overall batch status
            if failed_count == 0:
                processing_status = "completed"
            elif processed_count == 0:
                processing_status = "failed"
            else:
                processing_status = "partial_success"
            
            # Prepare batch results
            batch_results = {
                "batch_id": batch_id,
                "batch_timestamp": batch_timestamp.isoformat(),
                "batch_description": batch_description,
                "user_id": user_id,
                "total_files": total_files,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "success_rate": round(success_rate, 2),
                "processing_status": processing_status,
                "successful_documents": successful_documents,
                "failed_documents": failed_documents,
                "processing_summary": {
                    "total_size_bytes": sum(len(f.get("content", b"")) for f in files),
                    "successful_size_bytes": sum(
                        len(files[doc.get("batch_index", 0)].get("content", b"")) 
                        for doc in successful_documents 
                        if doc.get("batch_index") is not None
                    ),
                    "processing_duration_seconds": (datetime.now() - batch_timestamp).total_seconds()
                }
            }
            
            self.logger.info(
                "Batch document processing completed",
                batch_id=batch_id,
                total_files=total_files,
                processed_count=processed_count,
                failed_count=failed_count,
                success_rate=success_rate,
                processing_status=processing_status,
                processing_duration=batch_results["processing_summary"]["processing_duration_seconds"]
            )
            
            return batch_results
            
        except Exception as err:
            self.logger.error(
                "Batch document processing failed completely",
                error=str(err),
                batch_id=batch_id if 'batch_id' in locals() else 'unknown'
            )
            raise DocumentProcessorException(f"Batch processing failed: {err}") from err

    def process_batch_documents_optimized(
        self,
        files: List[Dict[str, Any]],
        batch_description: Optional[str] = None,
        batch_tags: Optional[List[str]] = None,
        user_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process multiple documents in batch with Azure Storage and MongoDB optimizations.
        
        This method uses:
        - Azure Storage bulk upload with parallel processing
        - MongoDB bulk insert for better performance
        - Parallel OCR processing
        - Optimized error handling
        
        Args:
            files: List of file dictionaries with content, filename, etc.
            batch_description: Common description for all documents.
            batch_tags: Common tags for all documents.
            user_id: User ID for all documents in the batch.
            
        Returns:
            Dict[str, Any]: Batch processing results with success/failure breakdown.
        """
        try:
            batch_id = str(uuid.uuid4())
            batch_timestamp = datetime.now()
            start_time = time.time()
            
            self.logger.info(
                "Starting optimized batch document processing",
                batch_id=batch_id,
                file_count=len(files),
                user_id=user_id,
                batch_description=batch_description,
                max_workers=self.max_workers
            )
            
            # Step 1: Prepare files for Azure Storage batch upload
            storage_files = []
            for index, file_info in enumerate(files):
                blob_name = f"{uuid.uuid4().hex}_{file_info['filename']}"
                storage_files.append({
                    'content': file_info['content'],
                    'blob_name': blob_name,
                    'content_type': self._get_content_type(file_info['filename']),
                    'original_index': index,
                    'filename': file_info['filename']
                })
            
            # Step 2: Upload all files to Azure Storage in parallel
            self.logger.info("Starting parallel Azure Storage upload")
            storage_results = self.storage_manager.upload_files_batch(storage_files)
            
            # Step 3: Process documents for MongoDB bulk insert
            documents_to_insert = []
            successful_documents = []
            failed_documents = []
            
            for i, storage_result in enumerate(storage_results):
                try:
                    # Obtain correct original file using the stored index
                    original_index = storage_result.get('original_index', i)
                    if original_index >= len(files):
                        original_index = i
                    original_file = files[original_index]
                    
                    if storage_result['status'] != 'success':
                        failed_documents.append({
                            "filename": original_file['filename'],
                            "error": storage_result.get('error', 'Storage upload failed'),
                            "error_type": "storage_error",
                            "timestamp": datetime.now().isoformat()
                        })
                        continue
                    
                    # Parse medical information from the correct filename
                    medical_info = self.filename_parser.parse_filename(original_file['filename'])
                    
                    self.logger.debug(
                        f"Parsed medical info for {original_file['filename']}: "
                        f"expediente={medical_info.expediente}, "
                        f"paciente={medical_info.nombre_paciente}, "
                        f"valid={medical_info.is_valid}"
                    )
                    
                    # Perform OCR
                    ocr_result = self.ocr_manager.extract_text_from_bytes(
                        file_content=original_file['content'],
                        content_type=self._get_content_type(original_file['filename'])
                    )
                    
                    # Prepare document for MongoDB
                    document = {
                        "processing_id": str(uuid.uuid4()),
                        "filename": original_file['filename'],
                        "content_type": self._get_content_type(original_file['filename']),
                        "file_size": len(original_file['content']),
                        "user_id": original_file.get('user_id') or user_id,
                        "storage_info": {
                            "blob_name": storage_result['blob_name'],
                            "blob_url": storage_result['url'],
                            "container_name": "documents"
                        },
                        "extracted_text": ocr_result.get("extracted_text", ""),
                        "processing_status": "completed",
                        "description": original_file.get('description') or batch_description,
                        "tags": (original_file.get('tags') or []) + (batch_tags or []),
                        # Medical fields at first level
                        "expediente": medical_info.expediente,
                        "nombre_paciente": medical_info.nombre_paciente,
                        "numero_episodio": medical_info.numero_episodio,
                        "categoria": medical_info.categoria,
                        "medical_info_valid": medical_info.is_valid,
                        "medical_info_error": medical_info.error_message,
                        # Batch information
                        "batch_info": {
                            "batch_id": batch_id,
                            "batch_index": storage_result.get('original_index', i),
                            "batch_timestamp": batch_timestamp.isoformat(),
                            "batch_description": batch_description,
                            "is_batch_document": True
                        }
                    }
                    
                    documents_to_insert.append(document)
                    
                    # Prepare successful result
                    successful_documents.append({
                        "document_id": None,  # Will be set after MongoDB insert
                        "processing_id": document['processing_id'],
                        "filename": document['filename'],
                        "storage_info": storage_result,
                        "ocr_summary": {
                            "text_length": len(ocr_result.get("extracted_text", "")),
                            "page_count": ocr_result.get("page_count", 0),
                            "table_count": ocr_result.get("table_count", 0)
                        },
                        "processing_status": "completed",
                        "processing_timestamp": datetime.now().isoformat(),
                        "expediente": medical_info.expediente,
                        "nombre_paciente": medical_info.nombre_paciente,
                        "numero_episodio": medical_info.numero_episodio,
                        "categoria": medical_info.categoria,
                        "medical_info_valid": medical_info.is_valid,
                        "medical_info_error": medical_info.error_message,
                        "batch_id": batch_id,
                        "batch_index": storage_result.get('original_index', i),
                        "batch_timestamp": batch_timestamp.isoformat(),
                        "batch_description": batch_description
                    })
                    
                except Exception as e:
                    original_file = files[storage_result.get('original_index', i)]
                    failed_documents.append({
                        "filename": original_file['filename'],
                        "error": str(e),
                        "error_type": "processing_error",
                        "timestamp": datetime.now().isoformat()
                    })
            
            # Step 4: Bulk insert successful documents to MongoDB
            if documents_to_insert:
                self.logger.info(f"Bulk inserting {len(documents_to_insert)} documents to MongoDB")
                document_ids = self.mongodb_manager.save_documents_batch(documents_to_insert)
                
                # Update successful documents with actual document IDs
                for i, doc_id in enumerate(document_ids):
                    if i < len(successful_documents):
                        successful_documents[i]["document_id"] = doc_id
            
            # Calculate final statistics
            total_files = len(files)
            processed_count = len(successful_documents)
            failed_count = len(failed_documents)
            success_rate = (processed_count / total_files * 100) if total_files > 0 else 0
            processing_time = time.time() - start_time
            
            processing_status = "completed" if failed_count == 0 else (
                "failed" if processed_count == 0 else "partial_success"
            )
            
            batch_results = {
                "batch_id": batch_id,
                "batch_timestamp": batch_timestamp.isoformat(),
                "batch_description": batch_description,
                "user_id": user_id,
                "total_files": total_files,
                "processed_count": processed_count,
                "failed_count": failed_count,
                "success_rate": round(success_rate, 2),
                "processing_status": processing_status,
                "successful_documents": successful_documents,
                "failed_documents": failed_documents,
                "processing_summary": {
                    "processing_duration_seconds": round(processing_time, 2),
                    "average_time_per_document": round(processing_time / total_files, 2),
                    "documents_per_second": round(total_files / processing_time, 2) if processing_time > 0 else 0,
                    "optimization_used": "azure_storage_batch_upload_mongodb_bulk_insert"
                }
            }
            
            self.logger.info(
                "Optimized batch document processing completed",
                batch_id=batch_id,
                total_files=total_files,
                processed_count=processed_count,
                failed_count=failed_count,
                success_rate=success_rate,
                processing_status=processing_status,
                processing_duration=processing_time,
                optimization="azure_storage_batch_mongodb_bulk"
            )
            
            return batch_results
            
        except Exception as err:
            self.logger.error(
                "Optimized batch document processing failed completely",
                batch_id=batch_id if 'batch_id' in locals() else 'unknown',
                error=str(err)
            )
            raise DocumentProcessorException(f"Optimized batch processing failed: {err}") from err

    def get_document_info(self, document_id: str) -> Optional[Dict[str, Any]]:
        """
        Get document information by ID.
        
        Args:
            document_id (str): Document ID.
            
        Returns:
            Optional[Dict[str, Any]]: Document information or None if not found.
            
        Raises:
            DocumentProcessorException: If retrieval fails.
        """
        try:
            self.logger.info(
                "Retrieving document information",
                document_id=document_id
            )
            
            # Get document from MongoDB
            document = self.mongodb_manager.get_document(document_id)
            
            if not document:
                self.logger.info(
                    "Document not found",
                    document_id=document_id
                )
                return None
            
            # Prepare response
            response = {
                "document_id": document["_id"],
                "processing_id": document.get("processing_id"),
                "filename": document.get("filename"),
                "content_type": document.get("content_type"),
                "file_size": document.get("file_size"),
                "user_id": document.get("user_id"),
                "storage_info": document.get("storage_info", {}),
                "extracted_text": document.get("extracted_text", ""),
                "processing_status": document.get("processing_status"),
                "batch_info": document.get("batch_info"),
                "description": document.get("description"),
                "tags": document.get("tags", []),
                # Campos médicos al primer nivel
                "expediente": document.get("expediente"),
                "nombre_paciente": document.get("nombre_paciente"),
                "numero_episodio": document.get("numero_episodio"),
                "categoria": document.get("categoria"),
                "medical_info_valid": document.get("medical_info_valid"),
                "medical_info_error": document.get("medical_info_error"),
                "created_at": document.get("created_at"),
                "updated_at": document.get("updated_at")
            }
            
            self.logger.info(
                "Document information retrieved successfully",
                document_id=document_id
            )
            
            return response
            
        except DatabaseException as err:
            self.logger.error(
                "Failed to retrieve document information",
                document_id=document_id,
                error=str(err)
            )
            raise DocumentProcessorException(f"Document retrieval failed: {err}") from err
        except Exception as err:
            self.logger.error(
                "Unexpected error retrieving document information",
                document_id=document_id,
                error=str(err)
            )
            raise DocumentProcessorException(f"Unexpected retrieval error: {err}") from err

    def search_documents(
        self,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 10,
        skip: int = 0
    ) -> Dict[str, Any]:
        """
        Search documents in the database.
        
        Args:
            query (Optional[Dict[str, Any]]): Search query.
            limit (int): Maximum number of results.
            skip (int): Number of results to skip.
            
        Returns:
            Dict[str, Any]: Search results.
            
        Raises:
            DocumentProcessorException: If search fails.
        """
        try:
            self.logger.info(
                "Searching documents",
                query=query,
                limit=limit,
                skip=skip
            )
            
            # Search documents in MongoDB
            documents = self.mongodb_manager.search_documents(
                query=query,
                limit=limit,
                skip=skip
            )
            
            # Prepare response
            results = []
            for doc in documents:
                results.append({
                    "document_id": doc["_id"],
                    "processing_id": doc.get("processing_id"),
                    "filename": doc.get("filename"),
                    "content_type": doc.get("content_type"),
                    "file_size": doc.get("file_size"),
                    "user_id": doc.get("user_id"),
                    "storage_info": doc.get("storage_info", {}),
                    "extracted_text": doc.get("extracted_text", ""),
                    "processing_status": doc.get("processing_status"),
                    "batch_info": doc.get("batch_info"),
                    "description": doc.get("description"),
                    "tags": doc.get("tags", []),
                    # Campos médicos al primer nivel
                    "expediente": doc.get("expediente"),
                    "nombre_paciente": doc.get("nombre_paciente"),
                    "numero_episodio": doc.get("numero_episodio"),
                    "categoria": doc.get("categoria"),
                    "medical_info_valid": doc.get("medical_info_valid"),
                    "medical_info_error": doc.get("medical_info_error"),
                    "created_at": doc.get("created_at"),
                    "updated_at": doc.get("updated_at")
                })
            
            search_results = {
                "total_found": len(results),
                "documents": results,
                "limit": limit,
                "skip": skip
            }
            
            self.logger.info(
                "Document search completed",
                total_found=len(results),
                limit=limit,
                skip=skip
            )
            
            return search_results
            
        except DatabaseException as err:
            self.logger.error(
                "Document search failed",
                query=query,
                error=str(err)
            )
            raise DocumentProcessorException(f"Document search failed: {err}") from err
        except Exception as err:
            self.logger.error(
                "Unexpected error during document search",
                query=query,
                error=str(err)
            )
            raise DocumentProcessorException(f"Unexpected search error: {err}") from err

    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document completely (from both MongoDB and Azure Storage).
        
        Args:
            document_id (str): Document ID to delete.
            
        Returns:
            bool: True if deletion was successful.
            
        Raises:
            DocumentProcessorException: If deletion fails.
        """
        try:
            self.logger.info(
                "Starting document deletion",
                document_id=document_id
            )
            
            # Get document info first
            document = self.mongodb_manager.get_document(document_id)
            if not document:
                self.logger.warning(
                    "Document not found for deletion",
                    document_id=document_id
                )
                return False
            
            storage_info = document.get("storage_info", {})
            blob_name = storage_info.get("blob_name")
            
            # Delete from MongoDB
            mongodb_deleted = self.mongodb_manager.delete_document(document_id)
            
            # Delete from Azure Storage if blob_name exists
            storage_deleted = True
            if blob_name:
                try:
                    storage_deleted = self.storage_manager.delete_file(blob_name)
                except StorageException as err:
                    self.logger.warning(
                        "Failed to delete from Azure Storage",
                        blob_name=blob_name,
                        error=str(err)
                    )
                    storage_deleted = False
            
            success = mongodb_deleted and storage_deleted
            
            self.logger.info(
                "Document deletion completed",
                document_id=document_id,
                mongodb_deleted=mongodb_deleted,
                storage_deleted=storage_deleted,
                success=success
            )
            
            return success
            
        except DatabaseException as err:
            self.logger.error(
                "Document deletion failed",
                document_id=document_id,
                error=str(err)
            )
            raise DocumentProcessorException(f"Document deletion failed: {err}") from err
        except Exception as err:
            self.logger.error(
                "Unexpected error during document deletion",
                document_id=document_id,
                error=str(err)
            )
            raise DocumentProcessorException(f"Unexpected deletion error: {err}") from err

    def _get_content_type(self, filename: str) -> str:
        """
        Get content type based on file extension.
        
        Args:
            filename (str): File name.
            
        Returns:
            str: Content type.
        """
        extension = filename.lower().split('.')[-1]
        content_types = {
            'pdf': 'application/pdf',
            'png': 'image/png',
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'gif': 'image/gif',
            'bmp': 'image/bmp',
            'tiff': 'image/tiff',
            'tif': 'image/tiff'
        }
        return content_types.get(extension, 'application/octet-stream')
    
    def _get_file_extension(self, filename: str) -> str:
        """
        Get file extension from filename.
        
        Args:
            filename (str): File name.
            
        Returns:
            str: File extension.
        """
        return filename.lower().split('.')[-1] if '.' in filename else 'unknown' 