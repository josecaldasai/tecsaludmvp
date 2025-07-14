"""
Tests para verificar la autorización por user_id en todas las APIs de búsqueda.
Incluye tests para asegurar que los usuarios solo puedan ver sus propios documentos.
"""

import pytest
import json
import uuid
from typing import Dict, Any


class TestUserIdRequiredEndpoints:
    """Tests para verificar que user_id es obligatorio en todos los endpoints de búsqueda."""

    def test_list_documents_requires_user_id(self, api_client, clean_database):
        """Test que verifica que GET /documents/ requiere user_id."""
        response = api_client.get("/api/v1/documents/")
        
        # Debería retornar 400 (bad request) porque user_id es requerido
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "USER_ID_REQUIRED"
        assert "message" in error_data
        assert "user_id" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data

    def test_search_patients_requires_user_id(self, api_client, clean_database):
        """Test que verifica que GET /search/patients requiere user_id."""
        response = api_client.get("/api/v1/search/patients?search_term=MARIA")
        
        # Debería retornar 400 (bad request) porque user_id es requerido
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "USER_ID_REQUIRED"
        assert "message" in error_data
        assert "user_id" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data

    def test_search_suggestions_requires_user_id(self, api_client, clean_database):
        """Test que verifica que GET /search/patients/suggestions requiere user_id."""
        response = api_client.get("/api/v1/search/patients/suggestions?partial_term=MAR")
        
        # Debería retornar 400 (bad request) porque user_id es requerido
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "USER_ID_REQUIRED"
        assert "message" in error_data
        assert "user_id" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data

    def test_search_patient_documents_requires_user_id(self, api_client, clean_database):
        """Test que verifica que GET /search/patients/{patient_name}/documents requiere user_id."""
        response = api_client.get("/api/v1/search/patients/MARIA%20GARCIA/documents")
        
        # Debería retornar 400 (bad request) porque user_id es requerido
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "USER_ID_REQUIRED"
        assert "message" in error_data
        assert "user_id" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data


class TestUserIdDocumentIsolation:
    """Tests para verificar que los usuarios solo puedan ver sus propios documentos."""

    def test_list_documents_user_isolation(self, api_client, clean_database, sample_medical_pdf_file, wait_for_processing):
        """Test que verifica que los usuarios solo ven sus propios documentos en el listado."""
        user1_id = "user1_test"
        user2_id = "user2_test"
        
        # Subir documento para user1
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {
                "user_id": user1_id,
                "description": "Documento de user1"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc1 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc1["processing_status"] == "completed"
        
        # Subir documento para user2
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (f"user2_{sample_medical_pdf_file['filename']}", file, "application/pdf")}
            data = {
                "user_id": user2_id,
                "description": "Documento de user2"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc2 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc2["processing_status"] == "completed"
        
        # User1 debería ver solo su documento
        response = api_client.get(f"/api/v1/documents/?user_id={user1_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user1_id
        assert data["documents"][0]["description"] == "Documento de user1"
        
        # User2 debería ver solo su documento
        response = api_client.get(f"/api/v1/documents/?user_id={user2_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user2_id
        assert data["documents"][0]["description"] == "Documento de user2"

    def test_search_patients_user_isolation(self, api_client, clean_database, sample_medical_pdf_file, wait_for_processing):
        """Test que verifica que la búsqueda de pacientes solo retorna documentos del usuario."""
        user1_id = "user1_test"
        user2_id = "user2_test"
        
        # Subir documento para user1
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {
                "user_id": user1_id,
                "description": "Documento de user1"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc1 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc1["processing_status"] == "completed"
        
        # Subir documento para user2 con mismo nombre de paciente
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (f"user2_{sample_medical_pdf_file['filename']}", file, "application/pdf")}
            data = {
                "user_id": user2_id,
                "description": "Documento de user2"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc2 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc2["processing_status"] == "completed"
        
        # Buscar paciente como user1
        patient_name = sample_medical_pdf_file["nombre_paciente"]
        response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&user_id={user1_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user1_id
        
        # Buscar paciente como user2
        response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&user_id={user2_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user2_id

    def test_search_suggestions_user_isolation(self, api_client, clean_database, sample_medical_pdf_file, wait_for_processing):
        """Test que verifica que las sugerencias solo incluyen pacientes del usuario."""
        user1_id = "user1_test"
        user2_id = "user2_test"
        
        # Subir documento para user1
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {
                "user_id": user1_id,
                "description": "Documento de user1"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc1 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc1["processing_status"] == "completed"
        
        # Subir documento para user2
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (f"user2_{sample_medical_pdf_file['filename']}", file, "application/pdf")}
            data = {
                "user_id": user2_id,
                "description": "Documento de user2"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc2 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc2["processing_status"] == "completed"
        
        # Obtener sugerencias para user1
        partial_name = sample_medical_pdf_file["nombre_paciente"][:5]
        response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_name}&user_id={user1_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_suggestions"] >= 1
        assert len(data["suggestions"]) >= 1
        
        # Obtener sugerencias para user2
        response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_name}&user_id={user2_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_suggestions"] >= 1
        assert len(data["suggestions"]) >= 1

    def test_search_patient_documents_user_isolation(self, api_client, clean_database, sample_medical_pdf_file, wait_for_processing):
        """Test que verifica que la búsqueda por nombre de paciente solo retorna documentos del usuario."""
        user1_id = "user1_test"
        user2_id = "user2_test"
        
        # Subir documento para user1
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {
                "user_id": user1_id,
                "description": "Documento de user1"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc1 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc1["processing_status"] == "completed"
        
        # Subir documento para user2
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (f"user2_{sample_medical_pdf_file['filename']}", file, "application/pdf")}
            data = {
                "user_id": user2_id,
                "description": "Documento de user2"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc2 = wait_for_processing(api_client, response.json()["document_id"])
            assert doc2["processing_status"] == "completed"
        
        # Buscar documentos del paciente como user1
        patient_name = sample_medical_pdf_file["nombre_paciente"]
        response = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?user_id={user1_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user1_id
        
        # Buscar documentos del paciente como user2
        response = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?user_id={user2_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user2_id


class TestUserIdValidation:
    """Tests para verificar la validación de user_id en diferentes escenarios."""

    def test_list_documents_empty_user_id(self, api_client, clean_database):
        """Test que verifica que user_id vacío es rechazado."""
        response = api_client.get("/api/v1/documents/?user_id=")
        
        # Debería retornar 400 (bad request) porque user_id no puede estar vacío
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "INVALID_USER_ID"
        assert "message" in error_data
        assert "empty" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data

    def test_search_patients_empty_user_id(self, api_client, clean_database):
        """Test que verifica que user_id vacío es rechazado en búsqueda de pacientes."""
        response = api_client.get("/api/v1/search/patients?search_term=MARIA&user_id=")
        
        # Debería retornar 400 (bad request) porque user_id no puede estar vacío
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "INVALID_USER_ID"
        assert "message" in error_data
        assert "empty" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data

    def test_search_suggestions_empty_user_id(self, api_client, clean_database):
        """Test que verifica que user_id vacío es rechazado en sugerencias."""
        response = api_client.get("/api/v1/search/patients/suggestions?partial_term=MAR&user_id=")
        
        # Debería retornar 400 (bad request) porque user_id no puede estar vacío
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "INVALID_USER_ID"
        assert "message" in error_data
        assert "empty" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data

    def test_search_patient_documents_empty_user_id(self, api_client, clean_database):
        """Test que verifica que user_id vacío es rechazado en búsqueda de documentos por paciente."""
        response = api_client.get("/api/v1/search/patients/MARIA%20GARCIA/documents?user_id=")
        
        # Debería retornar 400 (bad request) porque user_id no puede estar vacío
        assert response.status_code == 400
        
        error_data = response.json()
        assert "error_code" in error_data
        assert error_data["error_code"] == "INVALID_USER_ID"
        assert "message" in error_data
        assert "empty" in error_data["message"].lower()
        assert "request_id" in error_data
        assert "suggestion" in error_data


class TestUserIdWorkflow:
    """Tests para verificar el flujo completo con user_id."""

    @pytest.mark.slow
    def test_complete_userid_workflow(self, api_client, clean_database, sample_medical_pdf_file, wait_for_processing):
        """Test que verifica el flujo completo de un usuario con sus documentos."""
        user_id = "test_user_workflow"
        
        # 1. Subir documento
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {
                "user_id": user_id,
                "description": "Documento de prueba para workflow"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response.status_code == 201
            
            # Esperar procesamiento
            doc = wait_for_processing(api_client, response.json()["document_id"])
            assert doc["processing_status"] == "completed"
        
        # 2. Listar documentos del usuario
        response = api_client.get(f"/api/v1/documents/?user_id={user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user_id
        
        # 3. Buscar paciente
        patient_name = sample_medical_pdf_file["nombre_paciente"]
        response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&user_id={user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user_id
        
        # 4. Obtener sugerencias
        partial_name = patient_name[:5]
        response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_name}&user_id={user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_suggestions"] >= 1
        assert len(data["suggestions"]) >= 1
        
        # 5. Buscar documentos por nombre de paciente
        response = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?user_id={user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 1
        assert len(data["documents"]) == 1
        assert data["documents"][0]["user_id"] == user_id
        
        # 6. Verificar que otro usuario no puede ver el documento
        other_user_id = "other_user"
        
        # Listar documentos como otro usuario
        response = api_client.get(f"/api/v1/documents/?user_id={other_user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 0
        assert len(data["documents"]) == 0
        
        # Buscar paciente como otro usuario
        response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&user_id={other_user_id}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["total_found"] == 0
        assert len(data["documents"]) == 0 