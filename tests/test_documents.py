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

    @pytest.mark.slow
    def test_upload_document_success(self, api_client, clean_database, sample_medical_pdf_file, test_user_data, wait_for_processing):
        """Test de subida exitosa de documento individual."""
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {
                "user_id": test_user_data["user_id"],
                "description": test_user_data["description"],
                "tags": json.dumps(test_user_data["tags"])
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 201
            
            result = response.json()
            assert "document_id" in result
            assert "processing_id" in result
            assert "filename" in result
            assert result["filename"] == sample_medical_pdf_file["filename"]
            assert "storage_info" in result
            assert "processing_status" in result
            assert result["processing_status"] in ["processing", "completed"]
            
            # Verificar información médica extraída
            assert result.get("expediente") == sample_medical_pdf_file["expediente"]
            assert result.get("nombre_paciente") == sample_medical_pdf_file["nombre_paciente"]
            assert result.get("numero_episodio") == sample_medical_pdf_file["numero_episodio"]
            assert result.get("categoria") == sample_medical_pdf_file["categoria"]
            
            # Esperar a que termine el procesamiento
            processed_doc = wait_for_processing(api_client, result["document_id"])
            assert processed_doc["processing_status"] == "completed"

    def test_upload_document_minimal_data(self, api_client, clean_database, sample_pdf_file):
        """Test de subida de documento con datos mínimos (solo archivo)."""
        with open(sample_pdf_file, "rb") as file:
            files = {"file": ("test_document.pdf", file, "application/pdf")}
            
            response = api_client.post("/api/v1/documents/upload", files=files)
            
            assert response.status_code == 201
            
            result = response.json()
            assert "document_id" in result
            assert result["filename"] == "test_document.pdf"

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

    def test_upload_document_with_tags(self, api_client, clean_database, sample_pdf_file, test_user_data):
        """Test de subida con tags."""
        tags = ["tag1", "tag2", "medical", "test"]
        
        with open(sample_pdf_file, "rb") as file:
            files = {"file": ("test_with_tags.pdf", file, "application/pdf")}
            data = {
                "user_id": test_user_data["user_id"],
                "tags": json.dumps(tags)
            }
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 201

    @pytest.mark.edge_case
    def test_upload_document_large_description(self, api_client, clean_database, sample_pdf_file):
        """Test con descripción muy larga."""
        # Descripción de exactamente 1000 caracteres (límite)
        long_description = "x" * 1000
        
        with open(sample_pdf_file, "rb") as file:
            files = {"file": ("test_long_desc.pdf", file, "application/pdf")}
            data = {"description": long_description}
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 201

    @pytest.mark.edge_case
    def test_upload_document_too_long_description(self, api_client, clean_database, sample_pdf_file):
        """Test con descripción que excede el límite."""
        # Descripción de 1001 caracteres (excede límite)
        too_long_description = "x" * 1001
        
        with open(sample_pdf_file, "rb") as file:
            files = {"file": ("test_too_long.pdf", file, "application/pdf")}
            data = {"description": too_long_description}
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            assert response.status_code == 422  # Validation Error


class TestDocumentBatchUpload:
    """Tests para upload en lote de documentos."""

    @pytest.mark.slow
    def test_batch_upload_success(self, api_client, clean_database, sample_pdf_file, sample_medical_pdf_file, test_user_data):
        """Test de subida en lote exitosa."""
        files = []
        
        # Archivo 1
        with open(sample_pdf_file, "rb") as file1:
            files.append(("files", ("batch_doc1.pdf", file1.read(), "application/pdf")))
        
        # Archivo 2
        with open(sample_medical_pdf_file["path"], "rb") as file2:
            files.append(("files", (sample_medical_pdf_file["filename"], file2.read(), "application/pdf")))
        
        data = {
            "user_id": test_user_data["user_id"],
            "batch_description": "Test batch upload",
            "batch_tags": json.dumps(["batch", "test"])
        }
        
        response = api_client.post("/api/v1/documents/upload/batch", files=files, data=data)
        
        assert response.status_code == 201
        
        result = response.json()
        assert "batch_id" in result
        assert "total_files" in result
        assert result["total_files"] == 2
        assert "processed_count" in result
        assert "failed_count" in result
        assert "success_rate" in result
        assert "successful_documents" in result
        assert "failed_documents" in result

    def test_batch_upload_minimal(self, api_client, clean_database, sample_pdf_file):
        """Test de batch upload con datos mínimos."""
        files = []
        
        with open(sample_pdf_file, "rb") as file:
            files.append(("files", ("single_batch.pdf", file.read(), "application/pdf")))
        
        response = api_client.post("/api/v1/documents/upload/batch", files=files)
        
        assert response.status_code == 201
        
        result = response.json()
        assert result["total_files"] == 1

    @pytest.mark.edge_case
    def test_batch_upload_no_files(self, api_client, clean_database):
        """Test de error al no proporcionar archivos."""
        data = {"user_id": "test_user"}
        
        response = api_client.post("/api/v1/documents/upload/batch", data=data)
        
        assert response.status_code == 422  # Validation Error

    @pytest.mark.slow
    def test_batch_upload_mixed_success_failure(self, api_client, clean_database, sample_pdf_file):
        """Test de batch con algunos archivos válidos y otros inválidos."""
        files = []
        
        # Archivo válido
        with open(sample_pdf_file, "rb") as file1:
            files.append(("files", ("valid.pdf", file1.read(), "application/pdf")))
        
        # Archivo inválido (texto)
        files.append(("files", ("invalid.txt", b"Invalid content", "text/plain")))
        
        response = api_client.post("/api/v1/documents/upload/batch", files=files)
        
        assert response.status_code == 201
        
        result = response.json()
        assert result["total_files"] == 2
        assert result["processing_status"] in ["completed", "partial_success"]


class TestDocumentListing:
    """Tests para listado de documentos."""

    def test_list_documents_empty(self, api_client, clean_database):
        """Test de listado cuando no hay documentos."""
        response = api_client.get("/api/v1/documents/")
        
        assert response.status_code == 200
        
        documents = response.json()
        assert isinstance(documents, list)
        assert len(documents) == 0

    def test_list_documents_with_documents(self, api_client, uploaded_document):
        """Test de listado con documentos existentes."""
        response = api_client.get("/api/v1/documents/")
        
        assert response.status_code == 200
        
        documents = response.json()
        assert isinstance(documents, list)
        assert len(documents) == 1
        
        doc = documents[0]
        assert doc["document_id"] == uploaded_document["document_id"]
        assert "filename" in doc
        assert "processing_status" in doc
        assert "created_at" in doc

    def test_list_documents_filter_by_user(self, api_client, uploaded_document):
        """Test de filtrado por usuario."""
        user_id = uploaded_document["user_data"]["user_id"]
        
        response = api_client.get(f"/api/v1/documents/?user_id={user_id}")
        
        assert response.status_code == 200
        
        documents = response.json()
        assert len(documents) == 1
        assert documents[0]["user_id"] == user_id

    def test_list_documents_filter_nonexistent_user(self, api_client, uploaded_document):
        """Test de filtrado por usuario que no existe."""
        response = api_client.get("/api/v1/documents/?user_id=nonexistent_user")
        
        assert response.status_code == 200
        
        documents = response.json()
        assert len(documents) == 0

    def test_list_documents_with_limit(self, api_client, uploaded_document):
        """Test de limitación de resultados."""
        response = api_client.get("/api/v1/documents/?limit=5")
        
        assert response.status_code == 200
        
        documents = response.json()
        assert len(documents) <= 5

    @pytest.mark.edge_case
    def test_list_documents_invalid_limit(self, api_client, clean_database):
        """Test con límite inválido."""
        response = api_client.get("/api/v1/documents/?limit=101")  # Excede máximo
        
        assert response.status_code == 422  # Validation Error

    @pytest.mark.edge_case
    def test_list_documents_negative_skip(self, api_client, clean_database):
        """Test con skip negativo."""
        response = api_client.get("/api/v1/documents/?skip=-1")
        
        assert response.status_code == 422  # Validation Error


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

    @pytest.mark.edge_case
    def test_get_document_info_invalid_id(self, api_client, clean_database):
        """Test con ID de documento inválido."""
        invalid_id = "invalid_id_format"
        
        response = api_client.get(f"/api/v1/documents/{invalid_id}")
        
        # Puede ser 400 (Bad Request) o 500 (Internal Server Error) dependiendo de la validación
        assert response.status_code in [400, 500]


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
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["document_id"] == fake_id
        assert result["success"] is False
        assert "not found" in result["message"].lower()

    @pytest.mark.edge_case
    def test_delete_document_invalid_id(self, api_client, clean_database):
        """Test de eliminación con ID inválido."""
        invalid_id = "invalid_id_format"
        
        response = api_client.delete(f"/api/v1/documents/{invalid_id}")
        
        # Puede ser 400 (Bad Request) o 500 (Internal Server Error)
        assert response.status_code in [400, 500]

    def test_delete_document_twice(self, api_client, uploaded_document):
        """Test de eliminación del mismo documento dos veces."""
        document_id = uploaded_document["document_id"]
        
        # Primera eliminación
        response1 = api_client.delete(f"/api/v1/documents/{document_id}")
        assert response1.status_code == 200
        assert response1.json()["success"] is True
        
        # Segunda eliminación
        response2 = api_client.delete(f"/api/v1/documents/{document_id}")
        assert response2.status_code == 200
        assert response2.json()["success"] is False


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
        list_response = api_client.get("/api/v1/documents/")
        assert list_response.status_code == 200
        documents = list_response.json()
        assert len(documents) == 1
        assert documents[0]["document_id"] == document_id
        
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
        final_list_response = api_client.get("/api/v1/documents/")
        assert final_list_response.status_code == 200
        final_documents = final_list_response.json()
        assert len(final_documents) == 0

    @pytest.mark.slow
    def test_multiple_users_isolation(self, api_client, clean_database, sample_pdf_file, test_user_data):
        """Test de aislamiento entre usuarios diferentes."""
        user1_id = test_user_data["user_id"]
        user2_id = test_user_data["alternative_user_id"]
        
        # Upload documento para user1
        with open(sample_pdf_file, "rb") as file:
            files = {"file": ("user1_doc.pdf", file, "application/pdf")}
            data = {"user_id": user1_id}
            
            response1 = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response1.status_code == 201
        
        # Upload documento para user2
        with open(sample_pdf_file, "rb") as file:
            files = {"file": ("user2_doc.pdf", file, "application/pdf")}
            data = {"user_id": user2_id}
            
            response2 = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert response2.status_code == 201
        
        # Verificar aislamiento
        user1_docs = api_client.get(f"/api/v1/documents/?user_id={user1_id}").json()
        user2_docs = api_client.get(f"/api/v1/documents/?user_id={user2_id}").json()
        
        assert len(user1_docs) == 1
        assert len(user2_docs) == 1
        assert user1_docs[0]["user_id"] == user1_id
        assert user2_docs[0]["user_id"] == user2_id
        assert user1_docs[0]["document_id"] != user2_docs[0]["document_id"] 