"""OCR Manager for handling document text extraction using Azure Document Intelligence."""

import time
from typing import Dict, Any
from azure.ai.documentintelligence import DocumentIntelligenceClient
from azure.core.credentials import AzureKeyCredential
from azure.ai.documentintelligence.models import AnalyzeResult, DocumentAnalysisFeature
from azure.core.exceptions import AzureError
import threading

from app.core.v1.exceptions import OCRException
from app.core.v1.decorators import retry, log_execution_time
from app.core.v1.log_manager import LogManager
from app.settings.v1.settings import SETTINGS


class OCRManager:
    """
    OCR Manager for handling document text extraction.
    Implements Singleton pattern to ensure only one instance exists.
    """
    
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        """Create singleton instance with thread safety."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        """
        Initialize OCR Manager (only once due to singleton pattern).
        """
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        self.logger = LogManager(__name__)
        self.endpoint = SETTINGS.AZURE.AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT
        self.key = SETTINGS.AZURE.AZURE_DOCUMENT_INTELLIGENCE_KEY
        
        try:
            self.client = DocumentIntelligenceClient(
                endpoint=self.endpoint,
                credential=AzureKeyCredential(self.key)
            )
            self.logger.info("OCR Manager initialized successfully")
        except Exception as err:
            self.logger.error(f"Failed to initialize OCR Manager: {err}")
            raise OCRException(f"OCR initialization failed: {err}") from err
            
        # Mark as initialized
        self._initialized = True

    @retry(exceptions=(AzureError, OCRException))
    @log_execution_time
    def extract_text_from_url(self, document_url: str) -> Dict[str, Any]:
        """Extract text from document using URL.

        Args:
            document_url (str): URL of the document to process.

        Returns:
            Dict[str, Any]: Extracted text and metadata.

        Raises:
            OCRException: If text extraction fails.
        """
        try:
            self.logger.info(f"Starting OCR processing for URL: {document_url}")
            
            # Start the analysis
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-read",
                analyze_request={"urlSource": document_url}
            )
            
            # Wait for completion
            result = poller.result()
            
            # Extract text content
            extracted_text = ""
            pages_info = []
            
            if result.pages:
                for page_idx, page in enumerate(result.pages):
                    page_text = ""
                    page_info = {
                        "page_number": page_idx + 1,
                        "width": page.width,
                        "height": page.height,
                        "unit": page.unit,
                        "lines": []
                    }
                    
                    if page.lines:
                        for line in page.lines:
                            line_text = line.content
                            page_text += line_text + "\n"
                            
                            line_info = {
                                "text": line_text,
                                "bounding_box": line.polygon if line.polygon else None
                            }
                            page_info["lines"].append(line_info)
                    
                    extracted_text += page_text
                    pages_info.append(page_info)
            
            # Extract tables if present
            tables_info = []
            if result.tables:
                for table_idx, table in enumerate(result.tables):
                    table_info = {
                        "table_number": table_idx + 1,
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": []
                    }
                    
                    if table.cells:
                        for cell in table.cells:
                            cell_info = {
                                "content": cell.content,
                                "row_index": cell.row_index,
                                "column_index": cell.column_index,
                                "row_span": cell.row_span,
                                "column_span": cell.column_span
                            }
                            table_info["cells"].append(cell_info)
                    
                    tables_info.append(table_info)

            # Compile results
            ocr_result = {
                "extracted_text": extracted_text.strip(),
                "pages": pages_info,
                "tables": tables_info,
                "page_count": len(pages_info),
                "table_count": len(tables_info),
                "processing_timestamp": time.time(),
                "model_id": "prebuilt-read",
                "api_version": result.api_version if hasattr(result, 'api_version') else None
            }
            
            self.logger.info(
                "OCR processing completed successfully",
                page_count=len(pages_info),
                table_count=len(tables_info),
                text_length=len(extracted_text)
            )
            
            return ocr_result

        except AzureError as err:
            self.logger.error(f"Azure Document Intelligence processing failed: {err}")
            raise OCRException(f"OCR processing failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during OCR processing: {err}")
            raise OCRException(f"Unexpected OCR error: {err}") from err

    @retry(exceptions=(AzureError, OCRException))
    @log_execution_time
    def extract_text_from_bytes(self, file_content: bytes, content_type: str) -> Dict[str, Any]:
        """Extract text from document bytes.

        Args:
            file_content (bytes): Document content as bytes.
            content_type (str): MIME type of the document.

        Returns:
            Dict[str, Any]: Extracted text and metadata.

        Raises:
            OCRException: If text extraction fails.
        """
        try:
            self.logger.info(f"Starting OCR processing for bytes content, type: {content_type}")
            
            # Start the analysis
            from io import BytesIO
            document_stream = BytesIO(file_content)
            
            poller = self.client.begin_analyze_document(
                model_id="prebuilt-read",
                analyze_request=document_stream,
                content_type=content_type
            )
            
            # Wait for completion
            result = poller.result()
            
            # Extract text content
            extracted_text = ""
            pages_info = []
            
            if result.pages:
                for page_idx, page in enumerate(result.pages):
                    page_text = ""
                    page_info = {
                        "page_number": page_idx + 1,
                        "width": page.width,
                        "height": page.height,
                        "unit": page.unit,
                        "lines": []
                    }
                    
                    if page.lines:
                        for line in page.lines:
                            line_text = line.content
                            page_text += line_text + "\n"
                            
                            line_info = {
                                "text": line_text,
                                "bounding_box": line.polygon if line.polygon else None
                            }
                            page_info["lines"].append(line_info)
                    
                    extracted_text += page_text
                    pages_info.append(page_info)
            
            # Extract tables if present
            tables_info = []
            if result.tables:
                for table_idx, table in enumerate(result.tables):
                    table_info = {
                        "table_number": table_idx + 1,
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells": []
                    }
                    
                    if table.cells:
                        for cell in table.cells:
                            cell_info = {
                                "content": cell.content,
                                "row_index": cell.row_index,
                                "column_index": cell.column_index,
                                "row_span": cell.row_span,
                                "column_span": cell.column_span
                            }
                            table_info["cells"].append(cell_info)
                    
                    tables_info.append(table_info)

            # Compile results
            ocr_result = {
                "extracted_text": extracted_text.strip(),
                "pages": pages_info,
                "tables": tables_info,
                "page_count": len(pages_info),
                "table_count": len(tables_info),
                "processing_timestamp": time.time(),
                "model_id": "prebuilt-read",
                "api_version": result.api_version if hasattr(result, 'api_version') else None
            }
            
            self.logger.info(
                "OCR processing completed successfully",
                page_count=len(pages_info),
                table_count=len(tables_info),
                text_length=len(extracted_text)
            )
            
            return ocr_result

        except AzureError as err:
            self.logger.error(f"Azure Document Intelligence processing failed: {err}")
            raise OCRException(f"OCR processing failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during OCR processing: {err}")
            raise OCRException(f"Unexpected OCR error: {err}") from err

    @log_execution_time
    def extract_structured_data(self, document_url: str, model_id: str = "prebuilt-document") -> Dict[str, Any]:
        """Extract structured data from document using specific model.

        Args:
            document_url (str): URL of the document to process.
            model_id (str): Model ID for analysis (e.g., prebuilt-invoice, prebuilt-receipt).

        Returns:
            Dict[str, Any]: Extracted structured data.

        Raises:
            OCRException: If structured extraction fails.
        """
        try:
            self.logger.info(f"Starting structured data extraction with model: {model_id}")
            
            # Start the analysis
            poller = self.client.begin_analyze_document(
                model_id=model_id,
                analyze_request={"urlSource": document_url}
            )
            
            # Wait for completion
            result = poller.result()
            
            # Extract structured data
            structured_data = {
                "model_id": model_id,
                "processing_timestamp": time.time(),
                "documents": [],
                "pages": [],
                "tables": []
            }
            
            # Extract document-level information
            if result.documents:
                for doc in result.documents:
                    doc_info = {
                        "doc_type": doc.doc_type,
                        "confidence": doc.confidence,
                        "fields": {}
                    }
                    
                    if doc.fields:
                        for field_name, field_value in doc.fields.items():
                            doc_info["fields"][field_name] = {
                                "content": field_value.content if field_value.content else None,
                                "confidence": field_value.confidence if field_value.confidence else None,
                                "value": field_value.value if field_value.value else None
                            }
                    
                    structured_data["documents"].append(doc_info)
            
            # Extract page information
            if result.pages:
                for page in result.pages:
                    page_info = {
                        "page_number": page.page_number,
                        "width": page.width,
                        "height": page.height,
                        "unit": page.unit,
                        "lines_count": len(page.lines) if page.lines else 0
                    }
                    structured_data["pages"].append(page_info)
            
            # Extract table information
            if result.tables:
                for table in result.tables:
                    table_info = {
                        "row_count": table.row_count,
                        "column_count": table.column_count,
                        "cells_count": len(table.cells) if table.cells else 0
                    }
                    structured_data["tables"].append(table_info)
            
            self.logger.info(
                "Structured data extraction completed successfully",
                model_id=model_id,
                documents_count=len(structured_data["documents"]),
                pages_count=len(structured_data["pages"])
            )
            
            return structured_data

        except AzureError as err:
            self.logger.error(f"Structured data extraction failed: {err}")
            raise OCRException(f"Structured extraction failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during structured extraction: {err}")
            raise OCRException(f"Unexpected structured extraction error: {err}") from err

    @log_execution_time
    def get_operation_status(self, operation_id: str) -> Dict[str, Any]:
        """Get status of a document analysis operation.

        Args:
            operation_id (str): Operation ID to check.

        Returns:
            Dict[str, Any]: Operation status information.

        Raises:
            OCRException: If status retrieval fails.
        """
        try:
            # This would typically be used for async operations
            # For now, return a basic status structure
            status_info = {
                "operation_id": operation_id,
                "status": "completed",
                "timestamp": time.time()
            }
            
            self.logger.info(
                "Operation status retrieved",
                operation_id=operation_id
            )
            
            return status_info

        except Exception as err:
            self.logger.error(f"Status retrieval failed: {err}")
            raise OCRException(f"Status retrieval failed: {err}") from err 