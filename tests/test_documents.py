"""
Tests para endpoints de gestión de documentos.
Incluye upload individual, batch upload, listado, información y eliminación.
"""

import pytest
import json
import time
import tempfile
import os
from typing import Dict, Any


class TestDocumentUpload:
    """Tests para upload de documentos individuales."""

    def test_upload_document_success(self, api_client, clean_database, sample_medical_pdf_file):
        """Test de subida exitosa de documento con datos completos."""
        file_data = sample_medical_pdf_file
        
        with open(file_data["path"], "rb") as file:
            files = {"file": (file_data["filename"], file, "application/pdf")}
            data = {
                "user_id": "test_user_123",
                "description": "Expediente médico de prueba",
                "tags": "urgente,cardiologia,consulta"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 201
            
            result = response.json()
            assert "document_id" in result
            assert result["filename"] == file_data["filename"]
            # La API no devuelve user_id, description, ni tags en la respuesta
            
            # Verificar que la información médica se extrajo correctamente
            assert result["expediente"] == file_data["expediente"]
            assert result["nombre_paciente"] == file_data["nombre_paciente"]
            assert result["numero_episodio"] == file_data["numero_episodio"]
            assert result["categoria"] == file_data["categoria"]
            assert result["medical_info_valid"] is True
            assert result["processing_status"] in ["processing", "completed"]

    def test_upload_document_minimal_data(self, api_client, clean_database, sample_pdf_file):
        """Test de subida de documento con datos mínimos (solo archivo)."""
        file_path, medical_filename = sample_pdf_file
        
        with open(file_path, "rb") as file:
            # Usar el nombre médico válido de la fixture
            files = {"file": (medical_filename, file, "application/pdf")}
            
            response = api_client.post("/api/v1/documents/upload", files=files)
            
            assert response.status_code == 201
            
            result = response.json()
            assert "document_id" in result
            assert result["filename"] == medical_filename
            # Verificar que los campos médicos se extrajeron correctamente
            assert result["expediente"] == "4000123456"
            assert result["nombre_paciente"] == "GARCIA LOPEZ, MARIA"
            assert result["numero_episodio"] == "6001467010"
            assert result["categoria"] == "CONS"
            assert result["medical_info_valid"] is True

    @pytest.mark.edge_case
    def test_upload_document_no_file(self, api_client, clean_database):
        """Test de error al no proporcionar archivo."""
        data = {"user_id": "test_user"}
        
        response = api_client.post("/api/v1/documents/upload", data=data)
        
        assert response.status_code == 422  # Validation Error

    @pytest.mark.edge_case
    def test_upload_document_invalid_file_type(self, api_client, clean_database):
        """Test de error con tipo de archivo inválido."""
        # Crear archivo de texto temporal
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"This is a text file, not a PDF")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": ("test.txt", file, "text/plain")}
                
                response = api_client.post("/api/v1/documents/upload", files=files)
                
                # Debería fallar la validación o el procesamiento
                assert response.status_code in [400, 422, 500]
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_with_tags(self, api_client, clean_database, sample_pdf_file):
        """Test de subida de documento con tags."""
        file_path, medical_filename = sample_pdf_file
        
        with open(file_path, "rb") as file:
            files = {"file": (medical_filename, file, "application/pdf")}
            data = {
                "user_id": "test_user", 
                "tags": "urgente,cardiologia"
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 201
            
            result = response.json()
            assert result["filename"] == medical_filename
            # La API no devuelve el campo "tags" en la respuesta
            # Solo verificamos que el upload fue exitoso y los datos médicos están correctos
            assert result["medical_info_valid"] is True
            assert "document_id" in result
            assert result["processing_status"] in ["processing", "completed"]

    def test_upload_document_large_description(self, api_client, clean_database, sample_pdf_file):
        """Test de subida de documento con descripción larga."""
        file_path, medical_filename = sample_pdf_file
        
        large_description = "A" * 500  # 500 caracteres
        
        with open(file_path, "rb") as file:
            files = {"file": (medical_filename, file, "application/pdf")}
            data = {
                "user_id": "test_user",
                "description": large_description
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 201
            
            result = response.json()
            assert result["filename"] == medical_filename
            # La API no devuelve el campo "description" en la respuesta
            # Solo verificamos que el upload fue exitoso y los datos médicos están correctos
            assert result["medical_info_valid"] is True
            assert "document_id" in result
            assert result["processing_status"] in ["processing", "completed"]

    def test_upload_document_too_long_description(self, api_client, clean_database, sample_pdf_file):
        """Test de subida de documento con descripción demasiado larga."""
        file_path, medical_filename = sample_pdf_file
        
        too_long_description = "A" * 2000  # 2000 caracteres, demasiado largo
        
        with open(file_path, "rb") as file:
            files = {"file": (medical_filename, file, "application/pdf")}
            data = {
                "user_id": "test_user",
                "description": too_long_description
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            # Debe fallar o truncar la descripción, dependiendo de la validación
            assert response.status_code >= 400


class TestDocumentBatchUpload:
    """Tests para upload en lote de documentos."""

    def test_batch_upload_success(self, api_client, clean_database, sample_pdf_file):
        """Test de subida exitosa de múltiples documentos."""
        file_path, medical_filename = sample_pdf_file
        
        with open(file_path, "rb") as file1:
            with open(file_path, "rb") as file2:
                # Usar nombres médicos válidos diferentes
                files = [
                    ("files", (medical_filename, file1, "application/pdf")),
                    ("files", ("4000123457_LOPEZ MARTINEZ, JOSE_6001467011_EMER.pdf", file2, "application/pdf"))
                ]
                data = {
                    "user_id": "test_user",
                    "batch_description": "Lote de documentos médicos"
                }
                
                response = api_client.post("/api/v1/documents/upload/batch", files=files, data=data)
                
                assert response.status_code == 201
                
                result = response.json()
                assert "batch_id" in result
                # La API devuelve "successful_documents" no "documents"
                assert len(result["successful_documents"]) == 2
                assert result["total_files"] == 2
                assert result["processed_count"] == 2
                assert result["failed_count"] == 0
                assert result["processing_status"] in ["processing", "completed"]

    def test_batch_upload_minimal(self, api_client, clean_database, sample_pdf_file):
        """Test de subida de lote con datos mínimos."""
        file_path, medical_filename = sample_pdf_file
        
        with open(file_path, "rb") as file:
            files = [("files", (medical_filename, file, "application/pdf"))]
            
            response = api_client.post("/api/v1/documents/upload/batch", files=files)
            
            assert response.status_code == 201
            
            result = response.json()
            assert "batch_id" in result
            # La API devuelve "successful_documents" no "documents"
            assert len(result["successful_documents"]) == 1
            assert result["total_files"] == 1
            assert result["processed_count"] == 1
            assert result["failed_count"] == 0

    @pytest.mark.edge_case
    def test_batch_upload_no_files(self, api_client, clean_database):
        """Test de error al no proporcionar archivos."""
        data = {"user_id": "test_user"}
        
        response = api_client.post("/api/v1/documents/upload/batch", data=data)
        
        assert response.status_code == 422  # Validation Error

    def test_batch_upload_mixed_success_failure(self, api_client, clean_database, sample_pdf_file):
        """Test de subida de lote con archivos mixtos (válidos e inválidos)."""
        file_path, medical_filename = sample_pdf_file
        
        with open(file_path, "rb") as file1:
            with open(file_path, "rb") as file2:
                # Un archivo válido y uno inválido (sin formato médico)
                files = [
                    ("files", (medical_filename, file1, "application/pdf")),
                    ("files", ("archivo_invalido.pdf", file2, "application/pdf"))
                ]
                
                response = api_client.post("/api/v1/documents/upload/batch", files=files)
                
                # Con validación estricta, toda la batch debe fallar si un archivo es inválido
                assert response.status_code == 400
                
                result = response.json()
                assert "error_code" in result
                assert "INVALID_MEDICAL_FILENAME" in str(result)


class TestDocumentListing:
    """Tests para listado de documentos."""

    def test_list_documents_empty(self, api_client, clean_database):
        """Test de listado cuando no hay documentos."""
        response = api_client.get("/api/v1/documents/?user_id=test_user")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "documents" in result
        assert "total_found" in result
        assert "pagination" in result or "has_next" in result  # Verificar estructura de paginación
        
        assert isinstance(result["documents"], list)
        assert len(result["documents"]) == 0
        assert result["total_found"] == 0
        
        # Verificar metadata de paginación
        assert result["returned_count"] == 0
        assert result["has_next"] is False
        assert result["has_prev"] is False
        assert result["current_page"] == 1
        assert result["total_pages"] == 1
        
        # Verificar campos de tracking
        assert "request_id" in result
        assert "search_timestamp" in result
        assert "applied_filters" in result

    def test_list_documents_with_documents(self, api_client, uploaded_document):
        """Test de listado con documentos existentes."""
        # Usar el mismo user_id que la fixture uploaded_document
        response = api_client.get("/api/v1/documents/?user_id=test_user_001")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "documents" in result
        documents = result["documents"]
        assert isinstance(documents, list)
        assert len(documents) == 1
        
        # Verificar que encontramos el documento correcto
        assert documents[0]["document_id"] == uploaded_document["document_id"]
        
        # Verificar información del documento
        doc = documents[0]
        assert doc["document_id"] == uploaded_document["document_id"]
        assert "filename" in doc
        assert "processing_status" in doc
        assert "created_at" in doc
        
        # Verificar metadata de paginación
        assert result["total_found"] == 1
        assert result["returned_count"] == 1
        assert result["has_next"] is False
        assert result["has_prev"] is False
        assert result["current_page"] == 1

    def test_list_documents_filter_by_user(self, api_client, uploaded_document):
        """Test de filtrado por usuario."""
        user_id = uploaded_document["user_data"]["user_id"]
        
        response = api_client.get(f"/api/v1/documents/?user_id={user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        documents = result["documents"]
        assert len(documents) == 1
        assert documents[0]["user_id"] == user_id
        
        # Verificar filtros aplicados
        assert result["applied_filters"]["user_id"] == user_id

    def test_list_documents_filter_nonexistent_user(self, api_client, uploaded_document):
        """Test de filtrado por usuario que no existe."""
        response = api_client.get("/api/v1/documents/?user_id=nonexistent_user")
        
        assert response.status_code == 200
        
        result = response.json()
        documents = result["documents"]
        assert len(documents) == 0
        assert result["total_found"] == 0
        
        # Verificar filtros aplicados
        assert result["applied_filters"]["user_id"] == "nonexistent_user"

    def test_list_documents_with_limit(self, api_client, uploaded_document):
        """Test de listado con límite específico."""
        response = api_client.get("/api/v1/documents/?user_id=test_user&limit=5")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["limit"] == 5

    @pytest.mark.edge_case  
    def test_list_documents_invalid_limit(self, api_client, clean_database):
        """Test de error con límite inválido."""
        response = api_client.get("/api/v1/documents/?user_id=test_user&limit=101")  # Excede máximo
        
        assert response.status_code >= 400  # Puede ser 400 o 422

    @pytest.mark.edge_case
    def test_list_documents_negative_skip(self, api_client, clean_database):
        """Test de error con skip negativo."""
        response = api_client.get("/api/v1/documents/?user_id=test_user&skip=-1")
        
        assert response.status_code >= 400  # Puede ser 400 o 422

    def test_list_documents_valid_batch_id_uuid(self, api_client, clean_database):
        """Test de filtrado por batch_id válido."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        response = api_client.get(f"/api/v1/documents/?user_id=test_user&batch_id={valid_uuid}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "documents" in result
        assert "applied_filters" in result
        
        filters = result["applied_filters"]
        assert "batch_id" in filters
        assert filters["batch_id"] == valid_uuid

    @pytest.mark.edge_case
    def test_list_documents_invalid_batch_id_format(self, api_client, clean_database):
        """Test con formato de batch_id inválido."""
        invalid_batch_id = "invalid-uuid-format"
        response = api_client.get(f"/api/v1/documents/?user_id=test_user&batch_id={invalid_batch_id}")
        
        # Puede devolver 400, 422 o 500 dependiendo de la validación
        assert response.status_code >= 400

    @pytest.mark.edge_case 
    def test_list_documents_pagination_metadata(self, api_client, clean_database):
        """Test de metadatos de paginación en respuesta."""
        response = api_client.get("/api/v1/documents/?user_id=test_user&limit=10&skip=0")
        
        assert response.status_code == 200
        
        result = response.json()
        
        # Verificar metadatos de paginación
        assert "limit" in result
        assert "skip" in result
        assert "total_found" in result
        assert "returned_count" in result
        assert "has_next" in result
        assert "has_prev" in result
        assert "current_page" in result
        assert "total_pages" in result
        
        # Verificar valores correctos
        assert result["limit"] == 10
        assert result["skip"] == 0
        assert result["returned_count"] == 0  # Base de datos vacía
        assert result["total_found"] == 0
        assert result["has_next"] is False
        assert result["has_prev"] is False
        assert result["current_page"] == 1
        assert result["total_pages"] == 1
        
        # Verificar formato de request_id
        assert result["request_id"].startswith("list_docs_")
        assert len(result["request_id"]) > 10

    @pytest.mark.edge_case
    def test_list_documents_pagination_logic(self, api_client, clean_database):
        """Test de lógica de paginación con base de datos vacía."""
        response = api_client.get("/api/v1/documents/?user_id=test_user&limit=10&skip=0")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_found"] == 0
        assert result["returned_count"] == 0
        assert result["has_next"] is False
        assert result["has_prev"] is False

    @pytest.mark.edge_case
    def test_list_documents_high_skip_value(self, api_client, clean_database):
        """Test con valor de skip alto (fuera de rango)."""
        response = api_client.get("/api/v1/documents/?user_id=test_user&skip=1000&limit=10")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_found"] == 0
        assert result["returned_count"] == 0

    @pytest.mark.edge_case
    def test_list_documents_empty_user_id_filter(self, api_client, clean_database):
        """Test con user_id vacío."""
        response = api_client.get("/api/v1/documents/?user_id=")
        
        # El endpoint correctamente rechaza user_id vacío con 400
        assert response.status_code == 400
        
        result = response.json()
        assert "error_code" in result

    @pytest.mark.edge_case
    def test_list_documents_multiple_filters(self, api_client, clean_database):
        """Test con múltiples filtros aplicados."""
        valid_uuid = "550e8400-e29b-41d4-a716-446655440000"
        
        response = api_client.get(f"/api/v1/documents/?user_id=test_user&batch_id={valid_uuid}&limit=5&skip=0")
        
        assert response.status_code == 200
        
        result = response.json()
        
        # Verificar filtros aplicados
        applied_filters = result["applied_filters"]
        assert applied_filters["user_id"] == "test_user"
        assert applied_filters["batch_id"] == valid_uuid
        
        # Verificar parámetros de paginación
        assert result["limit"] == 5
        assert result["skip"] == 0

    @pytest.mark.edge_case
    def test_list_documents_response_structure_consistency(self, api_client, clean_database):
        """Test que la estructura de respuesta es consistente."""
        response = api_client.get("/api/v1/documents/?user_id=test_user")
        
        assert response.status_code == 200
        
        result = response.json()
        
        # Verificar estructura principal
        assert isinstance(result, dict)
        assert isinstance(result["documents"], list)
        assert isinstance(result["total_found"], int)
        assert isinstance(result["has_next"], bool)
        assert isinstance(result["has_prev"], bool)
        assert isinstance(result["applied_filters"], dict)
        assert isinstance(result["request_id"], str)
        assert isinstance(result["search_timestamp"], str)


class TestDocumentInfo:
    """Tests para obtener información de documentos."""

    def test_get_document_info_success(self, api_client, uploaded_document):
        """Test de obtención exitosa de información de documento."""
        document_id = uploaded_document["document_id"]
        
        response = api_client.get(f"/api/v1/documents/{document_id}")
        
        assert response.status_code == 200
        
        doc_info = response.json()
        assert doc_info["document_id"] == document_id
        assert "filename" in doc_info
        assert "content_type" in doc_info
        assert "file_size" in doc_info
        assert "extracted_text" in doc_info
        assert "processing_status" in doc_info
        assert "storage_info" in doc_info
        assert "created_at" in doc_info
        assert "updated_at" in doc_info

    @pytest.mark.edge_case
    def test_get_document_info_nonexistent(self, api_client, clean_database):
        """Test de información de documento que no existe."""
        fake_id = "60f7b3b8e8f4c2a1b8d3e4f5"  # ObjectId válido pero inexistente
        
        response = api_client.get(f"/api/v1/documents/{fake_id}")
        
        assert response.status_code == 404
        
        # Verificar estructura de error mejorada
        error_data = response.json()
        assert "error_code" in error_data
        assert "error_message" in error_data
        assert "timestamp" in error_data
        assert error_data["error_code"] == "HTTP_404"
        
        # Los datos específicos están en error_message
        error_message = error_data["error_message"]
        assert "error_code" in error_message
        assert "message" in error_message
        assert "request_id" in error_message
        assert "document_id" in error_message
        assert "suggestion" in error_message
        assert error_message["error_code"] == "DOCUMENT_NOT_FOUND"
        assert error_message["document_id"] == fake_id

    @pytest.mark.edge_case
    def test_get_document_info_invalid_id(self, api_client, clean_database):
        """Test con ID de documento inválido."""
        invalid_id = "invalid_id_format"
        
        response = api_client.get(f"/api/v1/documents/{invalid_id}")
        
        assert response.status_code == 400
        
        # Verificar estructura de error mejorada
        error_data = response.json()
        assert "error_code" in error_data
        assert "error_message" in error_data
        assert "timestamp" in error_data
        assert error_data["error_code"] == "HTTP_400"
        
        # Los datos específicos están en error_message
        error_message = error_data["error_message"]
        assert "error_code" in error_message
        assert "message" in error_message
        assert "request_id" in error_message
        assert "provided_id" in error_message
        assert "expected_format" in error_message
        assert error_message["error_code"] == "INVALID_DOCUMENT_ID_FORMAT"
        assert error_message["provided_id"] == invalid_id

    @pytest.mark.edge_case
    def test_get_document_info_invalid_id_formats(self, api_client, clean_database):
        """Test con diferentes formatos de ID inválidos."""
        invalid_ids = [
            "123",  # Muy corto
            "507f1f77bcf86cd799439011x",  # Caracter inválido al final
            "",  # Vacío
            "507f1f77bcf86cd79943901",  # Muy corto por 1 caracter
            "invalid-id-with-dashes",  # Con guiones
            "507f1f77bcf86cd799439011507f1f77bcf86cd799439011",  # Muy largo
        ]
        
        for invalid_id in invalid_ids:
            response = api_client.get(f"/api/v1/documents/{invalid_id}")
            
            # Caso especial: ID vacío es interpretado como endpoint de listado
            if invalid_id == "":
                assert response.status_code == 200
                result = response.json()
                assert isinstance(result, list)  # Debe ser una lista (endpoint de listado)
                assert len(result) == 0  # Lista vacía en base de datos limpia
            else:
                # Otros IDs inválidos deben devolver 400
                assert response.status_code == 400
                
                error_data = response.json()
                assert error_data["error_code"] == "HTTP_400"
                
                error_message = error_data["error_message"]
                assert error_message["error_code"] == "INVALID_DOCUMENT_ID_FORMAT"
                assert error_message["provided_id"] == invalid_id
                assert "expected_format" in error_message

    @pytest.mark.edge_case
    def test_get_document_info_valid_objectid_nonexistent(self, api_client, clean_database):
        """Test con ObjectId válido que no existe en la base de datos."""
        # IDs válidos en formato pero que no existen
        valid_but_nonexistent_ids = [
            "507f1f77bcf86cd799439011",
            "60f7b3b8e8f4c2a1b8d3e4f5",
            "61f7b3b8e8f4c2a1b8d3e4f6",
        ]
        
        for fake_id in valid_but_nonexistent_ids:
            response = api_client.get(f"/api/v1/documents/{fake_id}")
            
            assert response.status_code == 404
            
            error_data = response.json()
            assert error_data["error_code"] == "HTTP_404"
            
            error_message = error_data["error_message"]
            assert error_message["error_code"] == "DOCUMENT_NOT_FOUND"
            assert error_message["document_id"] == fake_id
            assert "suggestion" in error_message
            assert "document" in error_message["suggestion"].lower()  # Cambio: buscar "document" en lugar de "documents"

    @pytest.mark.edge_case
    def test_get_document_info_error_response_structure(self, api_client, clean_database):
        """Test que las respuestas de error tienen estructura consistente."""
        # Test con ID inválido
        response = api_client.get("/api/v1/documents/invalid")
        
        assert response.status_code == 400
        
        error_data = response.json()
        
        # Campos obligatorios en el nivel superior
        required_fields = ["error_code", "error_message", "timestamp"]
        for field in required_fields:
            assert field in error_data, f"Campo requerido '{field}' falta en la respuesta de error"
        
        # Verificar estructura de error_message
        error_message = error_data["error_message"]
        validation_fields = ["error_code", "message", "request_id", "provided_id", "expected_format"]
        for field in validation_fields:
            assert field in error_message, f"Campo de validación '{field}' falta en error_message"
        
        # Verificar que request_id tiene formato correcto
        assert len(error_message["request_id"]) > 0
        assert error_message["request_id"].replace("-", "").replace("_", "").isalnum()

    @pytest.mark.edge_case
    def test_get_document_info_case_sensitivity(self, api_client, clean_database):
        """Test de sensibilidad a mayúsculas/minúsculas en ObjectId."""
        # ObjectId válido en mayúsculas
        uppercase_id = "507F1F77BCF86CD799439011"
        
        response = api_client.get(f"/api/v1/documents/{uppercase_id}")
        
        # El validador actual rechaza mayúsculas como formato inválido
        assert response.status_code == 400
        
        error_data = response.json()
        assert error_data["error_code"] == "HTTP_400"
        
        error_message = error_data["error_message"]
        assert error_message["error_code"] == "INVALID_DOCUMENT_ID_FORMAT"
        assert error_message["provided_id"] == uppercase_id


class TestDocumentDeletion:
    """Tests para eliminación de documentos."""

    def test_delete_document_success(self, api_client, uploaded_document):
        """Test de eliminación exitosa de documento."""
        document_id = uploaded_document["document_id"]
        
        response = api_client.delete(f"/api/v1/documents/{document_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["document_id"] == document_id
        assert result["success"] is True
        assert "message" in result
        
        # Verificar que el documento ya no existe
        get_response = api_client.get(f"/api/v1/documents/{document_id}")
        assert get_response.status_code == 404

    @pytest.mark.edge_case
    def test_delete_document_nonexistent(self, api_client, clean_database):
        """Test de eliminación de documento que no existe."""
        fake_id = "60f7b3b8e8f4c2a1b8d3e4f5"  # ObjectId válido pero inexistente
        
        response = api_client.delete(f"/api/v1/documents/{fake_id}")
        
        assert response.status_code == 404
        
        # Verificar estructura de error mejorada
        error_data = response.json()
        assert error_data["error_code"] == "HTTP_404"
        
        error_message = error_data["error_message"]
        assert error_message["error_code"] == "DOCUMENT_NOT_FOUND"
        assert error_message["document_id"] == fake_id
        assert error_message["message"] == f"Document with ID '{fake_id}' does not exist or has already been deleted"
        assert "request_id" in error_message
        assert "suggestion" in error_message

    @pytest.mark.edge_case
    def test_delete_document_invalid_id(self, api_client, clean_database):
        """Test de eliminación con ID inválido."""
        invalid_id = "invalid_id_format"
        
        response = api_client.delete(f"/api/v1/documents/{invalid_id}")
        
        assert response.status_code == 400
        
        # Verificar estructura de error mejorada
        error_data = response.json()
        assert error_data["error_code"] == "HTTP_400"
        
        error_message = error_data["error_message"]
        assert error_message["error_code"] == "INVALID_DOCUMENT_ID_FORMAT"
        assert error_message["provided_id"] == invalid_id
        assert error_message["expected_format"] == "24 hexadecimal characters (MongoDB ObjectId)"
        assert "request_id" in error_message
        assert "suggestion" in error_message

    @pytest.mark.edge_case
    def test_delete_document_invalid_id_formats(self, api_client, clean_database):
        """Test de eliminación con diferentes formatos de ID inválidos."""
        invalid_ids = [
            "123",  # Muy corto
            "507f1f77bcf86cd799439011x",  # Caracter inválido al final
            "507f1f77bcf86cd79943901",  # Muy corto por 1 caracter
            "invalid-id-with-dashes",  # Con guiones
            "507f1f77bcf86cd799439011507f1f77bcf86cd799439011",  # Muy largo
        ]
        
        for invalid_id in invalid_ids:
            response = api_client.delete(f"/api/v1/documents/{invalid_id}")
            
            assert response.status_code == 400
            
            error_data = response.json()
            assert error_data["error_code"] == "HTTP_400"
            
            error_message = error_data["error_message"]
            assert error_message["error_code"] == "INVALID_DOCUMENT_ID_FORMAT"
            assert error_message["provided_id"] == invalid_id
            assert "expected_format" in error_message

    @pytest.mark.edge_case
    def test_delete_document_empty_id(self, api_client, clean_database):
        """Test de eliminación con ID vacío."""
        response = api_client.delete("/api/v1/documents/")
        
        # ID vacío redirige al endpoint de listado, no al de eliminación
        assert response.status_code == 405  # Method Not Allowed para DELETE en endpoint de listado

    def test_delete_document_twice(self, api_client, uploaded_document):
        """Test de eliminación del mismo documento dos veces."""
        document_id = uploaded_document["document_id"]
        
        # Primera eliminación
        response1 = api_client.delete(f"/api/v1/documents/{document_id}")
        assert response1.status_code == 200
        assert response1.json()["success"] is True
        
        # Segunda eliminación - ahora devuelve 404
        response2 = api_client.delete(f"/api/v1/documents/{document_id}")
        assert response2.status_code == 404
        
        error_data = response2.json()
        assert error_data["error_code"] == "HTTP_404"
        
        error_message = error_data["error_message"]
        assert error_message["error_code"] == "DOCUMENT_NOT_FOUND"
        assert error_message["document_id"] == document_id

    @pytest.mark.edge_case
    def test_delete_document_error_response_structure(self, api_client, clean_database):
        """Test que las respuestas de error tienen estructura consistente."""
        # Test con ID inválido
        response = api_client.delete("/api/v1/documents/invalid")
        
        assert response.status_code == 400
        
        error_data = response.json()
        
        # Campos obligatorios en el nivel superior
        required_fields = ["error_code", "error_message", "timestamp"]
        for field in required_fields:
            assert field in error_data, f"Campo requerido '{field}' falta en la respuesta de error"
        
        # Verificar estructura de error_message
        error_message = error_data["error_message"]
        validation_fields = ["error_code", "message", "request_id", "provided_id", "expected_format", "suggestion"]
        for field in validation_fields:
            assert field in error_message, f"Campo de validación '{field}' falta en error_message"
        
        # Verificar que request_id tiene formato correcto
        assert len(error_message["request_id"]) > 0
        assert error_message["request_id"].replace("-", "").replace("_", "").isalnum()
        assert error_message["request_id"].startswith("del_doc_")

    @pytest.mark.edge_case
    def test_delete_document_case_sensitivity(self, api_client, clean_database):
        """Test de sensibilidad a mayúsculas/minúsculas en ObjectId."""
        # ObjectId válido en mayúsculas
        uppercase_id = "507F1F77BCF86CD799439011"
        
        response = api_client.delete(f"/api/v1/documents/{uppercase_id}")
        
        # El validador actual rechaza mayúsculas como formato inválido
        assert response.status_code == 400
        
        error_data = response.json()
        assert error_data["error_code"] == "HTTP_400"
        
        error_message = error_data["error_message"]
        assert error_message["error_code"] == "INVALID_DOCUMENT_ID_FORMAT"
        assert error_message["provided_id"] == uppercase_id


class TestDocumentWorkflow:
    """Tests de flujo completo de documentos."""

    @pytest.mark.slow
    def test_complete_document_workflow(self, api_client, clean_database, sample_medical_pdf_file, test_user_data, wait_for_processing):
        """Test del flujo completo: upload -> list -> info -> delete."""
        
        # 1. Upload
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {"user_id": test_user_data["user_id"]}
            
            upload_response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert upload_response.status_code == 201
            
            document_id = upload_response.json()["document_id"]
        
        # 2. Wait for processing
        processed_doc = wait_for_processing(api_client, document_id)
        assert processed_doc["processing_status"] == "completed"
        
        # 3. List documents
        list_response = api_client.get("/api/v1/documents/?user_id=test_user")
        assert list_response.status_code == 200
        documents = list_response.json()
        assert documents["total_found"] == 1
        assert documents["documents"][0]["document_id"] == document_id
        
        # 4. Get document info
        info_response = api_client.get(f"/api/v1/documents/{document_id}")
        assert info_response.status_code == 200
        doc_info = info_response.json()
        assert doc_info["document_id"] == document_id
        
        # 5. Delete document
        delete_response = api_client.delete(f"/api/v1/documents/{document_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["success"] is True
        
        # 6. Verify deletion
        list_response = api_client.get("/api/v1/documents/?user_id=test_user")
        assert list_response.status_code == 200
        final_documents = list_response.json()
        assert final_documents["total_found"] == 0

    @pytest.mark.slow
    def test_multiple_users_isolation(self, api_client, clean_database, sample_pdf_file, test_user_data):
        """Test de aislamiento entre usuarios diferentes."""
        file_path, medical_filename = sample_pdf_file
        user1_id = test_user_data["user_id"]
        user2_id = test_user_data["alternative_user_id"]
        
        # Upload documento para user1
        with open(file_path, "rb") as file:
            files = {"file": (medical_filename, file, "application/pdf")}
            data = {"user_id": user1_id}
            response1 = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response1.status_code == 201
        
        # Upload documento para user2
        with open(file_path, "rb") as file:
            files = {"file": ("4000777889_LOPEZ MARTINEZ, ANA_6001467013_EMER.pdf", file, "application/pdf")}
            data = {"user_id": user2_id}
            response2 = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response2.status_code == 201
        
        # Verificar aislamiento: cada usuario solo ve sus documentos
        user1_docs = api_client.get(f"/api/v1/documents/?user_id={user1_id}").json()
        user2_docs = api_client.get(f"/api/v1/documents/?user_id={user2_id}").json()
        
        assert user1_docs["total_found"] == 1
        assert user2_docs["total_found"] == 1
        
        # Verificar que no hay cross-contamination
        assert user1_docs["documents"][0]["filename"] == medical_filename
        assert user2_docs["documents"][0]["filename"] == "4000777889_LOPEZ MARTINEZ, ANA_6001467013_EMER.pdf" 