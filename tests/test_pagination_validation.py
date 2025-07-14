"""
Test para validar la funcionalidad de paginación en todas las APIs de búsqueda.

Este test verifica que:
1. Todos los endpoints de búsqueda incluyen metadatos de paginación completos
2. Los cálculos de paginación son correctos
3. La navegación entre páginas funciona correctamente
4. Los campos de paginación están correctamente formateados
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime
from unittest.mock import MagicMock, patch

from main import app
from app.core.v1.document_processor import DocumentProcessor
from app.core.v1.fuzzy_search_manager import FuzzySearchManager

client = TestClient(app)


class TestPaginationValidation:
    """Test suite for pagination validation across all search endpoints."""

    def test_documents_endpoint_pagination_metadata(self):
        """Test que el endpoint de documentos incluye todos los metadatos de paginación."""
        with patch.object(DocumentProcessor, '__init__', return_value=None), \
             patch.object(DocumentProcessor, 'search_documents') as mock_search:
            
            # Mock de respuesta con documentos
            mock_search.return_value = {
                "documents": [
                    {
                        "document_id": f"doc_{i}",
                        "processing_id": f"proc_{i}",
                        "filename": f"file_{i}.pdf",
                        "content_type": "application/pdf",
                        "file_size": 1024 * i,
                        "user_id": "user123",
                        "storage_info": {},
                        "extracted_text": f"Text content {i}",
                        "processing_status": "completed",
                        "batch_info": None,
                        "description": f"Document {i}",
                        "tags": [],
                        "expediente": f"EXP{i:03d}",
                        "nombre_paciente": f"Patient {i}",
                        "numero_episodio": f"EP{i:03d}",
                        "categoria": "CONS",
                        "medical_info_valid": True,
                        "medical_info_error": None,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                    for i in range(1, 6)  # 5 documentos
                ],
                "total_found": 50  # Total 50 documentos
            }
            
            # Petición con paginación
            response = client.get("/api/v1/documents/?user_id=user123&limit=5&skip=10")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verificar que incluye todos los metadatos de paginación
            assert "total_found" in data
            assert "limit" in data
            assert "skip" in data
            assert "returned_count" in data
            assert "has_next" in data
            assert "has_prev" in data
            assert "current_page" in data
            assert "total_pages" in data
            assert "applied_filters" in data
            assert "request_id" in data
            assert "search_timestamp" in data
            
            # Verificar cálculos de paginación
            assert data["total_found"] == 50
            assert data["limit"] == 5
            assert data["skip"] == 10
            assert data["returned_count"] == 5
            assert data["has_next"] is True  # (10 + 5) < 50
            assert data["has_prev"] is True  # 10 > 0
            assert data["current_page"] == 3  # (10 // 5) + 1
            assert data["total_pages"] == 10  # (50 + 5 - 1) // 5

    def test_fuzzy_search_endpoint_pagination_metadata(self):
        """Test que el endpoint de búsqueda fuzzy incluye todos los metadatos de paginación."""
        with patch.object(FuzzySearchManager, '__init__', return_value=None), \
             patch.object(FuzzySearchManager, 'search_patients_by_name') as mock_search:
            
            # Mock de respuesta con documentos
            mock_search.return_value = {
                "search_term": "maria",
                "normalized_term": "maria",
                "documents": [
                    {
                        "_id": f"doc_{i}",
                        "processing_id": f"proc_{i}",
                        "filename": f"file_{i}.pdf",
                        "content_type": "application/pdf",
                        "file_size": 1024 * i,
                        "user_id": "user123",
                        "storage_info": {},
                        "extracted_text": f"Text content {i}",
                        "processing_status": "completed",
                        "batch_info": None,
                        "description": f"Document {i}",
                        "tags": [],
                        "expediente": f"EXP{i:03d}",
                        "nombre_paciente": f"María Patient {i}",
                        "numero_episodio": f"EP{i:03d}",
                        "categoria": "CONS",
                        "medical_info_valid": True,
                        "medical_info_error": None,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                        "similarity_score": 0.9 - (i * 0.1),
                        "match_type": "fuzzy"
                    }
                    for i in range(1, 4)  # 3 documentos
                ],
                "total_found": 15,
                "search_strategies_used": ["fuzzy", "exact"],
                "min_similarity_threshold": 0.3,
                "search_timestamp": datetime.now().isoformat()
            }
            
            # Petición con paginación
            response = client.get("/api/v1/search/patients?search_term=maria&user_id=user123&limit=3&skip=6")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verificar que incluye todos los metadatos de paginación
            assert "search_term" in data
            assert "normalized_term" in data
            assert "total_found" in data
            assert "limit" in data
            assert "skip" in data
            assert "returned_count" in data
            assert "has_next" in data
            assert "has_prev" in data
            assert "current_page" in data
            assert "total_pages" in data
            assert "search_strategies_used" in data
            assert "min_similarity_threshold" in data
            assert "search_timestamp" in data
            
            # Verificar cálculos de paginación
            assert data["total_found"] == 15
            assert data["limit"] == 3
            assert data["skip"] == 6
            assert data["returned_count"] == 3
            assert data["has_next"] is True  # (6 + 3) < 15
            assert data["has_prev"] is True  # 6 > 0
            assert data["current_page"] == 3  # (6 // 3) + 1
            assert data["total_pages"] == 5  # (15 + 3 - 1) // 3

    def test_patient_documents_endpoint_pagination_metadata(self):
        """Test que el endpoint de documentos por paciente incluye todos los metadatos de paginación."""
        with patch.object(FuzzySearchManager, '__init__', return_value=None), \
             patch.object(FuzzySearchManager, 'search_patients_by_name') as mock_search:
            
            # Mock de respuesta con documentos
            mock_search.return_value = {
                "search_term": "MARÍA GONZÁLEZ",
                "normalized_term": "maria gonzalez",
                "documents": [
                    {
                        "_id": f"doc_{i}",
                        "processing_id": f"proc_{i}",
                        "filename": f"file_{i}.pdf",
                        "content_type": "application/pdf",
                        "file_size": 1024 * i,
                        "user_id": "user123",
                        "storage_info": {},
                        "extracted_text": f"Text content {i}",
                        "processing_status": "completed",
                        "batch_info": None,
                        "description": f"Document {i}",
                        "tags": [],
                        "expediente": f"EXP{i:03d}",
                        "nombre_paciente": "MARÍA GONZÁLEZ",
                        "numero_episodio": f"EP{i:03d}",
                        "categoria": "CONS",
                        "medical_info_valid": True,
                        "medical_info_error": None,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now(),
                        "similarity_score": 1.0,
                        "match_type": "exact"
                    }
                    for i in range(1, 3)  # 2 documentos
                ],
                "total_found": 8,
                "search_strategies_used": ["exact"],
                "min_similarity_threshold": 0.9,
                "search_timestamp": datetime.now().isoformat()
            }
            
            # Petición con paginación
            response = client.get("/api/v1/search/patients/MARÍA GONZÁLEZ/documents?user_id=user123&limit=2&skip=4")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verificar que incluye todos los metadatos de paginación
            assert "search_term" in data
            assert "normalized_term" in data
            assert "total_found" in data
            assert "limit" in data
            assert "skip" in data
            assert "returned_count" in data
            assert "has_next" in data
            assert "has_prev" in data
            assert "current_page" in data
            assert "total_pages" in data
            assert "search_strategies_used" in data
            assert "min_similarity_threshold" in data
            assert "search_timestamp" in data
            
            # Verificar cálculos de paginación
            assert data["total_found"] == 8
            assert data["limit"] == 2
            assert data["skip"] == 4
            assert data["returned_count"] == 2
            assert data["has_next"] is True  # (4 + 2) < 8
            assert data["has_prev"] is True  # 4 > 0
            assert data["current_page"] == 3  # (4 // 2) + 1
            assert data["total_pages"] == 4  # (8 + 2 - 1) // 2

    def test_suggestions_endpoint_pagination_metadata(self):
        """Test que el endpoint de sugerencias incluye todos los metadatos de paginación."""
        with patch.object(FuzzySearchManager, '__init__', return_value=None), \
             patch.object(FuzzySearchManager, 'get_search_suggestions') as mock_suggestions:
            
            # Mock de respuesta con sugerencias
            mock_suggestions.return_value = [
                "MARÍA GONZÁLEZ",
                "MARIO GARCÍA",
                "MARTHA LÓPEZ",
                "MARCOS RODRÍGUEZ"
            ]
            
            # Petición de sugerencias
            response = client.get("/api/v1/search/patients/suggestions?partial_term=MAR&user_id=user123&limit=10")
            
            assert response.status_code == 200
            data = response.json()
            
            # Verificar que incluye todos los metadatos de paginación
            assert "partial_term" in data
            assert "suggestions" in data
            assert "total_suggestions" in data
            assert "limit" in data
            assert "returned_count" in data
            assert "has_next" in data
            assert "has_prev" in data
            assert "current_page" in data
            assert "total_pages" in data
            assert "search_timestamp" in data
            
            # Verificar cálculos de paginación para sugerencias
            assert data["partial_term"] == "MAR"
            assert data["total_suggestions"] == 4
            assert data["limit"] == 10
            assert data["returned_count"] == 4
            assert data["has_next"] is False  # No hay más sugerencias
            assert data["has_prev"] is False  # No hay páginas anteriores
            assert data["current_page"] == 1
            assert data["total_pages"] == 1

    def test_pagination_edge_cases(self):
        """Test casos extremos de paginación."""
        with patch.object(DocumentProcessor, '__init__', return_value=None), \
             patch.object(DocumentProcessor, 'search_documents') as mock_search:
            
            # Caso 1: Sin documentos
            mock_search.return_value = {
                "documents": [],
                "total_found": 0
            }
            
            response = client.get("/api/v1/documents/?user_id=user123&limit=10&skip=0")
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_found"] == 0
            assert data["returned_count"] == 0
            assert data["has_next"] is False
            assert data["has_prev"] is False
            assert data["current_page"] == 1
            assert data["total_pages"] == 1
            
            # Caso 2: Exactamente una página
            mock_search.return_value = {
                "documents": [
                    {
                        "document_id": "doc_1",
                        "processing_id": "proc_1",
                        "filename": "file_1.pdf",
                        "content_type": "application/pdf",
                        "file_size": 1024,
                        "user_id": "user123",
                        "storage_info": {},
                        "extracted_text": "Text content",
                        "processing_status": "completed",
                        "batch_info": None,
                        "description": "Document",
                        "tags": [],
                        "expediente": "EXP001",
                        "nombre_paciente": "Patient 1",
                        "numero_episodio": "EP001",
                        "categoria": "CONS",
                        "medical_info_valid": True,
                        "medical_info_error": None,
                        "created_at": datetime.now(),
                        "updated_at": datetime.now()
                    }
                ],
                "total_found": 1
            }
            
            response = client.get("/api/v1/documents/?user_id=user123&limit=10&skip=0")
            assert response.status_code == 200
            data = response.json()
            
            assert data["total_found"] == 1
            assert data["returned_count"] == 1
            assert data["has_next"] is False
            assert data["has_prev"] is False
            assert data["current_page"] == 1
            assert data["total_pages"] == 1

    def test_pagination_consistency_across_endpoints(self):
        """Test que la paginación es consistente entre todos los endpoints."""
        # Parámetros de paginación estándar
        test_params = [
            {"limit": 5, "skip": 0, "expected_page": 1},
            {"limit": 5, "skip": 5, "expected_page": 2},
            {"limit": 5, "skip": 10, "expected_page": 3}
        ]
        
        for params in test_params:
            with patch.object(DocumentProcessor, '__init__', return_value=None), \
                 patch.object(DocumentProcessor, 'search_documents') as mock_search_docs, \
                 patch.object(FuzzySearchManager, '__init__', return_value=None), \
                 patch.object(FuzzySearchManager, 'search_patients_by_name') as mock_search_patients:
                
                # Mock para endpoint de documentos
                mock_search_docs.return_value = {
                    "documents": [{"document_id": f"doc_{i}"} for i in range(params["limit"])],
                    "total_found": 100
                }
                
                # Mock para endpoint de búsqueda fuzzy
                mock_search_patients.return_value = {
                    "search_term": "test",
                    "normalized_term": "test",
                    "documents": [{"_id": f"doc_{i}"} for i in range(params["limit"])],
                    "total_found": 100,
                    "search_strategies_used": ["fuzzy"],
                    "min_similarity_threshold": 0.3,
                    "search_timestamp": datetime.now().isoformat()
                }
                
                # Test endpoint de documentos
                response = client.get(f"/api/v1/documents/?user_id=user123&limit={params['limit']}&skip={params['skip']}")
                assert response.status_code == 200
                data = response.json()
                assert data["current_page"] == params["expected_page"]
                assert data["limit"] == params["limit"]
                assert data["skip"] == params["skip"]
                
                # Test endpoint de búsqueda fuzzy
                response = client.get(f"/api/v1/search/patients?search_term=test&user_id=user123&limit={params['limit']}&skip={params['skip']}")
                assert response.status_code == 200
                data = response.json()
                assert data["current_page"] == params["expected_page"]
                assert data["limit"] == params["limit"]
                assert data["skip"] == params["skip"]

    def test_pagination_format_validation(self):
        """Test que los campos de paginación tienen el formato correcto."""
        with patch.object(DocumentProcessor, '__init__', return_value=None), \
             patch.object(DocumentProcessor, 'search_documents') as mock_search:
            
            mock_search.return_value = {
                "documents": [{"document_id": "doc_1"}],
                "total_found": 1
            }
            
            response = client.get("/api/v1/documents/?user_id=user123&limit=10&skip=0")
            assert response.status_code == 200
            data = response.json()
            
            # Verificar tipos de datos
            assert isinstance(data["total_found"], int)
            assert isinstance(data["limit"], int)
            assert isinstance(data["skip"], int)
            assert isinstance(data["returned_count"], int)
            assert isinstance(data["has_next"], bool)
            assert isinstance(data["has_prev"], bool)
            assert isinstance(data["current_page"], int)
            assert isinstance(data["total_pages"], int)
            assert isinstance(data["search_timestamp"], str)
            assert isinstance(data["request_id"], str)
            assert isinstance(data["applied_filters"], dict)
            
            # Verificar valores positivos
            assert data["total_found"] >= 0
            assert data["limit"] > 0
            assert data["skip"] >= 0
            assert data["returned_count"] >= 0
            assert data["current_page"] > 0
            assert data["total_pages"] > 0
            
            # Verificar formato de timestamp
            try:
                datetime.fromisoformat(data["search_timestamp"].replace("Z", "+00:00"))
            except ValueError:
                pytest.fail("search_timestamp no tiene formato ISO válido") 