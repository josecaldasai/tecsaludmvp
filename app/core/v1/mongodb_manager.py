"""MongoDB Manager for handling database operations."""

from typing import Dict, List, Optional, Any
from pymongo import MongoClient, ASCENDING
from pymongo.collection import Collection
from pymongo.database import Database
from pymongo.errors import PyMongoError, DuplicateKeyError
from bson import ObjectId
from datetime import datetime
import threading

from app.settings.v1.general import SETTINGS
from app.core.v1.exceptions import DatabaseException
from app.core.v1.log_manager import LogManager


class MongoDBManager:
    """
    MongoDB Manager for handling document operations.
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
        Initialize MongoDB manager (only once due to singleton pattern).
        """
        # Only initialize once
        if hasattr(self, '_initialized') and self._initialized:
            return
            
        # Initialize logger
        self.logger = LogManager(__name__)
        
        # Get collections
        self.documents_collection = SETTINGS.MONGODB_COLLECTION_DOCUMENTS
        
        # Initialize MongoDB client
        self.client: MongoClient = None
        self.database: Database = None
        self.documents_col: Collection = None
        
        # Connect to MongoDB
        self._connect()
        
        # Mark as initialized
        self._initialized = True
        
    def _connect(self):
        """
        Connect to MongoDB.
        """
        try:
            # Create MongoDB client
            self.client = MongoClient(SETTINGS.MONGODB_URL)
            
            # Get database
            self.database = self.client[SETTINGS.MONGODB_DATABASE]
            
            # Get collections
            self.documents_col = self.database[self.documents_collection]
            
            # Create indexes
            self._create_indexes()
            
            self.logger.info(
                "MongoDB connection established successfully",
                database=SETTINGS.MONGODB_DATABASE,
                documents_collection=self.documents_collection
            )
            
        except PyMongoError as err:
            self.logger.error(f"MongoDB connection failed: {err}")
            raise DatabaseException(f"MongoDB connection failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error during MongoDB connection: {err}")
            raise DatabaseException(f"Unexpected MongoDB connection error: {err}") from err
    
    def _create_indexes(self):
        """
        Create necessary indexes for better performance.
        """
        # Get existing indexes
        existing_indexes = set()
        try:
            indexes_info = self.documents_col.list_indexes()
            for index in indexes_info:
                existing_indexes.add(index["name"])
        except Exception as err:
            self.logger.warning(f"Failed to retrieve existing indexes: {err}")
        
        # Define indexes to create
        indexes_to_create = [
            ([("processing_id", ASCENDING)], {"unique": True, "name": "processing_id_unique"}),
            ([("created_at", ASCENDING)], {"name": "created_at_index"}),
            ([("user_id", ASCENDING)], {"name": "user_id_index"}),
            ([("processing_status", ASCENDING)], {"name": "processing_status_index"}),
            ([("batch_info.batch_id", ASCENDING)], {"sparse": True, "name": "batch_id_index"}),
            ([("filename", ASCENDING)], {"name": "filename_index"}),
            ([("tags", ASCENDING)], {"name": "tags_index"}),
            ([("expediente", ASCENDING)], {"sparse": True, "name": "expediente_index"}),
            ([("nombre_paciente", ASCENDING)], {"sparse": True, "name": "nombre_paciente_index"}),
            ([("numero_episodio", ASCENDING)], {"sparse": True, "name": "numero_episodio_index"}),
            ([("categoria", ASCENDING)], {"sparse": True, "name": "categoria_index"}),
            ([("medical_info_valid", ASCENDING)], {"sparse": True, "name": "medical_info_valid_index"}),
            # Usar el índice de texto principal para búsquedas fuzzy
            ([("extracted_text", "text"), ("filename", "text"), ("nombre_paciente", "text")], 
             {"sparse": True, "name": "text_search_index"})
        ]
        
        created_count = 0
        existing_count = 0
        
        for index_spec, options in indexes_to_create:
            index_name = options.get('name', 'unnamed')
            
            # Check if index already exists
            if index_name in existing_indexes:
                existing_count += 1
                self.logger.debug(f"Index already exists: {index_name}")
                continue
            
            try:
                self.documents_col.create_index(index_spec, **options)
                created_count += 1
                self.logger.debug(f"Created index: {index_name}")
                
            except PyMongoError as err:
                # Handle specific MongoDB errors
                if "already exists" in str(err).lower() or "duplicate" in str(err).lower():
                    existing_count += 1
                    self.logger.debug(f"Index already exists (duplicate key): {index_name}")
                elif "only one text index" in str(err).lower():
                    existing_count += 1
                    self.logger.debug(f"Text index already exists, skipping: {index_name}")
                else:
                    self.logger.warning(f"Failed to create index {index_name}: {err}")
            except Exception as err:
                self.logger.warning(f"Unexpected error creating index {index_name}: {err}")
        
        self.logger.info(f"MongoDB indexes processed successfully (created: {created_count}, existing: {existing_count}, total attempted: {len(indexes_to_create)})")

    def save_document(self, document: Dict[str, Any]) -> str:
        """Save document to MongoDB.
        
        Args:
            document (Dict[str, Any]): Document to save.
            
        Returns:
            str: Document ID.
            
        Raises:
            DatabaseException: If document save fails.
        """
        try:
            # Add timestamps
            document["created_at"] = datetime.now()
            document["updated_at"] = datetime.now()
            
            # Insert document
            result = self.documents_col.insert_one(document)
            document_id = str(result.inserted_id)
            
            self.logger.info(
                "Document saved successfully",
                document_id=document_id,
                collection=self.documents_collection
            )
            
            return document_id
            
        except DuplicateKeyError as err:
            self.logger.error(f"Document already exists: {err}")
            raise DatabaseException(f"Document already exists: {err}") from err
        except PyMongoError as err:
            self.logger.error(f"Failed to save document: {err}")
            raise DatabaseException(f"Document save failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error saving document: {err}")
            raise DatabaseException(f"Unexpected document save error: {err}") from err

    def save_documents_batch(self, documents: List[Dict[str, Any]]) -> List[str]:
        """
        Save multiple documents to MongoDB using bulk operations.
        
        Args:
            documents: List of documents to save
            
        Returns:
            List[str]: List of document IDs
            
        Raises:
            DatabaseException: If bulk save fails
        """
        try:
            if not documents:
                return []
                
            # Add timestamps to all documents
            current_time = datetime.now()
            for doc in documents:
                doc["created_at"] = current_time
                doc["updated_at"] = current_time
                
            # Use bulk insert for better performance
            result = self.documents_col.insert_many(documents, ordered=False)
            document_ids = [str(doc_id) for doc_id in result.inserted_ids]
            
            self.logger.info(
                "Documents saved successfully in batch",
                document_count=len(documents),
                collection=self.documents_collection,
                batch_size=len(documents)
            )
            
            return document_ids
            
        except DuplicateKeyError as err:
            self.logger.error(f"Some documents already exist: {err}")
            raise DatabaseException(f"Batch save failed - duplicates: {err}") from err
        except Exception as err:
            self.logger.error(f"Batch document save failed: {err}")
            raise DatabaseException(f"Batch document save failed: {err}") from err

    def get_document(self, document_id: str) -> Optional[Dict[str, Any]]:
        """Get document from MongoDB.
        
        Args:
            document_id (str): Document ID to retrieve.
            
        Returns:
            Optional[Dict[str, Any]]: Document or None if not found.
            
        Raises:
            DatabaseException: If document retrieval fails.
        """
        try:
            # Validate ObjectId
            try:
                object_id = ObjectId(document_id)
            except Exception:
                self.logger.warning(f"Invalid document ID format: {document_id}")
                return None
            
            # Find document
            document = self.documents_col.find_one({"_id": object_id})
            
            if document:
                # Convert ObjectId to string
                document["_id"] = str(document["_id"])
                
                self.logger.info(
                    "Document retrieved successfully",
                    document_id=document_id
                )
                
                return document
            else:
                self.logger.info(
                    "Document not found",
                    document_id=document_id
                )
                return None
            
        except PyMongoError as err:
            self.logger.error(f"Failed to retrieve document: {err}")
            raise DatabaseException(f"Document retrieval failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error retrieving document: {err}")
            raise DatabaseException(f"Unexpected document retrieval error: {err}") from err

    def update_document(self, document_id: str, update_data: Dict[str, Any]) -> bool:
        """Update document in MongoDB.
        
        Args:
            document_id (str): Document ID to update.
            update_data (Dict[str, Any]): Data to update.
            
        Returns:
            bool: True if updated successfully, False if not found.
            
        Raises:
            DatabaseException: If document update fails.
        """
        try:
            # Validate ObjectId
            try:
                object_id = ObjectId(document_id)
            except Exception:
                self.logger.warning(f"Invalid document ID format: {document_id}")
                return False
            
            # Add updated timestamp
            update_data["updated_at"] = datetime.now()
            
            # Update document
            result = self.documents_col.update_one(
                {"_id": object_id},
                {"$set": update_data}
            )
            
            if result.matched_count > 0:
                self.logger.info(
                    "Document updated successfully",
                    document_id=document_id,
                    modified_count=result.modified_count
                )
                return True
            else:
                self.logger.info(
                    "Document not found for update",
                    document_id=document_id
                )
                return False
                
        except PyMongoError as err:
            self.logger.error(f"Failed to update document: {err}")
            raise DatabaseException(f"Document update failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error updating document: {err}")
            raise DatabaseException(f"Unexpected document update error: {err}") from err

    def delete_document(self, document_id: str) -> bool:
        """Delete document from MongoDB.
        
        Args:
            document_id (str): Document ID to delete.
            
        Returns:
            bool: True if deleted successfully, False if not found.
            
        Raises:
            DatabaseException: If document deletion fails.
        """
        try:
            # Validate ObjectId
            try:
                object_id = ObjectId(document_id)
            except Exception:
                self.logger.warning(f"Invalid document ID format: {document_id}")
                return False
            
            # Delete document
            result = self.documents_col.delete_one({"_id": object_id})
            
            if result.deleted_count > 0:
                self.logger.info(
                    "Document deleted successfully",
                    document_id=document_id
                )
                return True
            else:
                self.logger.info(
                    "Document not found for deletion",
                    document_id=document_id
                )
                return False
                
        except PyMongoError as err:
            self.logger.error(f"Failed to delete document: {err}")
            raise DatabaseException(f"Document deletion failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error deleting document: {err}")
            raise DatabaseException(f"Unexpected document deletion error: {err}") from err

    def search_documents(
        self,
        query: Optional[Dict[str, Any]] = None,
        limit: int = 100,
        skip: int = 0,
        sort: Optional[List[tuple]] = None
    ) -> List[Dict[str, Any]]:
        """Search documents in MongoDB.
        
        Args:
            query (Optional[Dict[str, Any]]): MongoDB query filter.
            limit (int): Maximum number of results.
            skip (int): Number of results to skip.
            sort (Optional[List[tuple]]): Sort criteria.
            
        Returns:
            List[Dict[str, Any]]: List of matching documents.
            
        Raises:
            DatabaseException: If search fails.
        """
        try:
            # Default query
            if query is None:
                query = {}
            
            # Default sort
            if sort is None:
                sort = [("created_at", -1)]
            
            # Execute search
            cursor = self.documents_col.find(query).sort(sort).skip(skip).limit(limit)
            
            # Convert results
            documents = []
            for doc in cursor:
                doc["_id"] = str(doc["_id"])
                documents.append(doc)
            
            self.logger.info(
                "Document search completed",
                query=query,
                count=len(documents),
                limit=limit,
                skip=skip
            )
            
            return documents
            
        except PyMongoError as err:
            self.logger.error(f"Failed to search documents: {err}")
            raise DatabaseException(f"Document search failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error searching documents: {err}")
            raise DatabaseException(f"Unexpected document search error: {err}") from err

    def count_documents(self, query: Optional[Dict[str, Any]] = None) -> int:
        """Count documents in MongoDB that match the query.
        
        Args:
            query (Optional[Dict[str, Any]]): MongoDB query filter.
            
        Returns:
            int: Number of matching documents.
            
        Raises:
            DatabaseException: If count fails.
        """
        try:
            # Default query
            if query is None:
                query = {}
            
            # Execute count
            count = self.documents_col.count_documents(query)
            
            self.logger.info(
                "Document count completed",
                query=query,
                count=count
            )
            
            return count
            
        except PyMongoError as err:
            self.logger.error(f"Failed to count documents: {err}")
            raise DatabaseException(f"Document count failed: {err}") from err
        except Exception as err:
            self.logger.error(f"Unexpected error counting documents: {err}")
            raise DatabaseException(f"Unexpected document count error: {err}") from err

    def close(self):
        """
        Close MongoDB connection.
        """
        try:
            if self.client:
                self.client.close()
                self.logger.info("MongoDB connection closed successfully")
                
        except PyMongoError as err:
            self.logger.error(f"Failed to close MongoDB connection: {err}")
        except Exception as err:
            self.logger.error(f"Unexpected error closing MongoDB connection: {err}") 