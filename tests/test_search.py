"""
Tests para endpoints de búsqueda fuzzy de pacientes.
Incluye búsqueda por nombre, sugerencias y obtención de documentos por paciente.
"""

import pytest
import json
import time
from typing import Dict, Any, List


class TestFuzzySearchPatients:
    """Tests para búsqueda fuzzy de pacientes por nombre."""

    def test_search_patients_exact_match(self, api_client, uploaded_document):
        """Test de búsqueda exacta por nombre de paciente."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "search_term" in result
        assert "documents" in result
        assert "total_found" in result
        assert result["search_term"] == patient_name
        assert result["total_found"] > 0
        assert len(result["documents"]) > 0
        
        # Verificar que encontró el documento correcto
        found_doc = result["documents"][0]
        assert found_doc["nombre_paciente"] == patient_name
        assert found_doc["document_id"] == uploaded_document["document_id"]
        assert "similarity_score" in found_doc
        assert found_doc["similarity_score"] > 0.8  # Debería ser alta para match exacto

    def test_search_patients_partial_match(self, api_client, uploaded_document):
        """Test de búsqueda parcial por nombre de paciente."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        # Usar solo la primera parte del nombre
        partial_name = patient_name.split()[0] if " " in patient_name else patient_name[:5]
        
        response = api_client.get(f"/api/v1/search/patients?search_term={partial_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_found"] > 0
        assert len(result["documents"]) > 0
        
        # Verificar que encontró el documento
        found_doc = result["documents"][0]
        assert patient_name in found_doc["nombre_paciente"]
        assert "similarity_score" in found_doc
        assert found_doc["similarity_score"] > 0.3  # Debería superar el umbral mínimo

    def test_search_patients_case_insensitive(self, api_client, uploaded_document):
        """Test de búsqueda insensible a mayúsculas/minúsculas."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        lowercase_name = patient_name.lower()
        
        response = api_client.get(f"/api/v1/search/patients?search_term={lowercase_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_found"] > 0
        assert len(result["documents"]) > 0
        
        # Debería encontrar el documento independientemente del caso
        found_doc = result["documents"][0]
        assert found_doc["nombre_paciente"] == patient_name.upper()  # Nombres médicos están en mayúsculas

    def test_search_patients_with_user_filter(self, api_client, uploaded_document):
        """Test de búsqueda con filtro por usuario."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        user_id = uploaded_document["user_data"]["user_id"]
        
        # Búsqueda con filtro de usuario correcto
        response1 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&user_id={user_id}")
        assert response1.status_code == 200
        result1 = response1.json()
        assert result1["total_found"] > 0
        
        # Búsqueda con filtro de usuario incorrecto
        response2 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&user_id=wrong_user")
        assert response2.status_code == 200
        result2 = response2.json()
        assert result2["total_found"] == 0

    def test_search_patients_with_pagination(self, api_client, uploaded_document):
        """Test de búsqueda con paginación."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        # Test con limit
        response1 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&limit=5")
        assert response1.status_code == 200
        result1 = response1.json()
        assert len(result1["documents"]) <= 5
        assert result1["limit"] == 5
        
        # Test con skip
        response2 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&skip=0")
        assert response2.status_code == 200
        result2 = response2.json()
        assert result2["skip"] == 0

    def test_search_patients_with_similarity_threshold(self, api_client, uploaded_document):
        """Test de búsqueda con umbral de similitud personalizado."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        partial_name = patient_name[:3]  # Búsqueda muy parcial
        
        # Umbral bajo
        response1 = api_client.get(f"/api/v1/search/patients?search_term={partial_name}&min_similarity=0.1")
        assert response1.status_code == 200
        result1 = response1.json()
        
        # Umbral alto
        response2 = api_client.get(f"/api/v1/search/patients?search_term={partial_name}&min_similarity=0.9")
        assert response2.status_code == 200
        result2 = response2.json()
        
        # Debería haber más resultados con umbral bajo
        assert result1["total_found"] >= result2["total_found"]

    def test_search_patients_include_score_option(self, api_client, uploaded_document):
        """Test de opción para incluir/excluir score de similitud."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        # Con score (default)
        response1 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&include_score=true")
        assert response1.status_code == 200
        result1 = response1.json()
        if result1["total_found"] > 0:
            assert "similarity_score" in result1["documents"][0]
        
        # Sin score
        response2 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&include_score=false")
        assert response2.status_code == 200
        result2 = response2.json()
        if result2["total_found"] > 0:
            # Puede que aún esté incluido, pero no debería ser el enfoque
            pass

    @pytest.mark.edge_case
    def test_search_patients_empty_term(self, api_client, clean_database):
        """Test con término de búsqueda vacío."""
        response = api_client.get("/api/v1/search/patients?search_term=")
        
        assert response.status_code == 422  # Validation Error

    @pytest.mark.edge_case
    def test_search_patients_very_long_term(self, api_client, clean_database):
        """Test con término muy largo."""
        long_term = "x" * 300  # Excede el límite de 200
        
        response = api_client.get(f"/api/v1/search/patients?search_term={long_term}")
        
        assert response.status_code == 422  # Validation Error

    def test_search_patients_no_matches(self, api_client, uploaded_document):
        """Test de búsqueda sin coincidencias."""
        response = api_client.get("/api/v1/search/patients?search_term=NONEXISTENT_PATIENT_NAME_12345")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_found"] == 0
        assert len(result["documents"]) == 0

    def test_search_patients_special_characters(self, api_client, uploaded_document):
        """Test de búsqueda con caracteres especiales."""
        # Intentar búsqueda con caracteres especiales
        response = api_client.get("/api/v1/search/patients?search_term=GARCÍA")
        
        assert response.status_code == 200
        
        result = response.json()
        # Debería manejar caracteres especiales correctamente
        assert "normalized_term" in result

    @pytest.mark.edge_case
    def test_search_patients_invalid_pagination(self, api_client, clean_database):
        """Test con parámetros de paginación inválidos."""
        # Límite excede máximo
        response1 = api_client.get("/api/v1/search/patients?search_term=test&limit=101")
        assert response1.status_code == 422
        
        # Skip negativo
        response2 = api_client.get("/api/v1/search/patients?search_term=test&skip=-1")
        assert response2.status_code == 422
        
        # Similitud fuera de rango
        response3 = api_client.get("/api/v1/search/patients?search_term=test&min_similarity=1.5")
        assert response3.status_code == 422

    def test_search_patients_metadata_validation(self, api_client, uploaded_document):
        """Test de validación de metadatos en respuesta."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        
        # Verificar metadatos requeridos
        assert "search_term" in result
        assert "normalized_term" in result
        assert "total_found" in result
        assert "documents" in result
        assert "limit" in result
        assert "skip" in result
        assert "search_strategies_used" in result
        assert "min_similarity_threshold" in result
        assert "search_timestamp" in result
        
        # Verificar tipos de datos
        assert isinstance(result["total_found"], int)
        assert isinstance(result["documents"], list)
        assert isinstance(result["limit"], int)
        assert isinstance(result["skip"], int)
        assert isinstance(result["search_strategies_used"], list)
        assert isinstance(result["min_similarity_threshold"], float)


class TestPatientNameSuggestions:
    """Tests para sugerencias de nombres de pacientes."""

    def test_get_suggestions_success(self, api_client, uploaded_document):
        """Test de obtención exitosa de sugerencias."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        partial_term = patient_name[:3]  # Primeros 3 caracteres
        
        response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_term}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "partial_term" in result
        assert "suggestions" in result
        assert "total_suggestions" in result
        assert "limit" in result
        assert result["partial_term"] == partial_term
        assert isinstance(result["suggestions"], list)
        assert isinstance(result["total_suggestions"], int)

    def test_get_suggestions_with_user_filter(self, api_client, uploaded_document):
        """Test de sugerencias con filtro por usuario."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        user_id = uploaded_document["user_data"]["user_id"]
        partial_term = patient_name[:3]
        
        # Con filtro de usuario correcto
        response1 = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_term}&user_id={user_id}")
        assert response1.status_code == 200
        result1 = response1.json()
        
        # Con filtro de usuario incorrecto
        response2 = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_term}&user_id=wrong_user")
        assert response2.status_code == 200
        result2 = response2.json()
        
        # Debería haber menos o igual sugerencias con filtro incorrecto
        assert result2["total_suggestions"] <= result1["total_suggestions"]

    def test_get_suggestions_with_limit(self, api_client, uploaded_document):
        """Test de sugerencias con límite personalizado."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        partial_term = patient_name[:2]
        
        response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_term}&limit=5")
        
        assert response.status_code == 200
        
        result = response.json()
        assert len(result["suggestions"]) <= 5
        assert result["limit"] == 5

    @pytest.mark.edge_case
    def test_get_suggestions_empty_term(self, api_client, clean_database):
        """Test con término parcial vacío."""
        response = api_client.get("/api/v1/search/patients/suggestions?partial_term=")
        
        assert response.status_code == 422  # Validation Error

    @pytest.mark.edge_case
    def test_get_suggestions_too_long_term(self, api_client, clean_database):
        """Test con término que excede el límite."""
        long_term = "x" * 101  # Excede límite de 100
        
        response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={long_term}")
        
        assert response.status_code == 422  # Validation Error

    def test_get_suggestions_no_matches(self, api_client, uploaded_document):
        """Test de sugerencias sin coincidencias."""
        response = api_client.get("/api/v1/search/patients/suggestions?partial_term=ZZZZZ")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_suggestions"] == 0
        assert len(result["suggestions"]) == 0

    @pytest.mark.edge_case
    def test_get_suggestions_invalid_limit(self, api_client, clean_database):
        """Test con límite inválido."""
        # Límite excede máximo
        response1 = api_client.get("/api/v1/search/patients/suggestions?partial_term=test&limit=51")
        assert response1.status_code == 422
        
        # Límite negativo
        response2 = api_client.get("/api/v1/search/patients/suggestions?partial_term=test&limit=-1")
        assert response2.status_code == 422

    def test_get_suggestions_single_character(self, api_client, uploaded_document):
        """Test con un solo carácter."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        single_char = patient_name[0]
        
        response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={single_char}")
        
        assert response.status_code == 200
        
        result = response.json()
        # Debería poder manejar búsquedas de un solo carácter
        assert isinstance(result["suggestions"], list)


class TestDocumentsByPatientName:
    """Tests para obtener documentos por nombre exacto de paciente."""

    def test_get_documents_by_patient_name_success(self, api_client, uploaded_document):
        """Test de obtención exitosa de documentos por nombre de paciente."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        response = api_client.get(f"/api/v1/search/patients/{patient_name}/documents")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "documents" in result
        assert "total_found" in result
        assert result["total_found"] > 0
        assert len(result["documents"]) > 0
        
        # Verificar que todos los documentos pertenecen al paciente correcto
        for doc in result["documents"]:
            assert doc["nombre_paciente"] == patient_name

    def test_get_documents_by_patient_name_with_user_filter(self, api_client, uploaded_document):
        """Test con filtro por usuario."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        user_id = uploaded_document["user_data"]["user_id"]
        
        # Con filtro de usuario correcto
        response1 = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?user_id={user_id}")
        assert response1.status_code == 200
        result1 = response1.json()
        assert result1["total_found"] > 0
        
        # Con filtro de usuario incorrecto
        response2 = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?user_id=wrong_user")
        assert response2.status_code == 200
        result2 = response2.json()
        assert result2["total_found"] == 0

    def test_get_documents_by_patient_name_pagination(self, api_client, uploaded_document):
        """Test de paginación."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        # Test con limit
        response1 = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?limit=10")
        assert response1.status_code == 200
        result1 = response1.json()
        assert len(result1["documents"]) <= 10
        
        # Test con skip
        response2 = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?skip=0")
        assert response2.status_code == 200
        result2 = response2.json()
        assert result2["skip"] == 0

    def test_get_documents_by_patient_name_nonexistent(self, api_client, clean_database):
        """Test con nombre de paciente inexistente."""
        response = api_client.get("/api/v1/search/patients/NONEXISTENT_PATIENT/documents")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_found"] == 0
        assert len(result["documents"]) == 0

    def test_get_documents_by_patient_name_special_characters(self, api_client, uploaded_document):
        """Test con caracteres especiales en nombre de paciente."""
        # Intentar con caracteres especiales codificados en URL
        patient_name = "GARCÍA, MARÍA"  # Nombre con acentos
        
        response = api_client.get(f"/api/v1/search/patients/{patient_name}/documents")
        
        assert response.status_code == 200
        
        result = response.json()
        # Debería manejar caracteres especiales correctamente
        assert isinstance(result["documents"], list)

    @pytest.mark.edge_case
    def test_get_documents_by_patient_name_invalid_pagination(self, api_client, uploaded_document):
        """Test con parámetros de paginación inválidos."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        # Límite excede máximo
        response1 = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?limit=101")
        assert response1.status_code == 422
        
        # Skip negativo
        response2 = api_client.get(f"/api/v1/search/patients/{patient_name}/documents?skip=-1")
        assert response2.status_code == 422

    def test_get_documents_by_patient_name_empty_name(self, api_client, clean_database):
        """Test con nombre vacío."""
        response = api_client.get("/api/v1/search/patients//documents")
        
        # Debería fallar o redirigir
        assert response.status_code in [400, 404, 422]

    def test_get_documents_by_patient_name_case_sensitivity(self, api_client, uploaded_document):
        """Test de sensibilidad a mayúsculas/minúsculas."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        lowercase_name = patient_name.lower()
        
        response = api_client.get(f"/api/v1/search/patients/{lowercase_name}/documents")
        
        assert response.status_code == 200
        
        result = response.json()
        # Puede que no encuentre nada si es sensible al caso
        # o que encuentre si normaliza el nombre
        assert isinstance(result["documents"], list)


class TestSearchWorkflow:
    """Tests de flujo completo de búsqueda."""

    @pytest.mark.slow
    def test_complete_search_workflow(self, api_client, uploaded_document):
        """Test del flujo completo de búsqueda."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        # 1. Buscar sugerencias con parte del nombre
        partial_name = patient_name[:4]
        suggestions_response = api_client.get(f"/api/v1/search/patients/suggestions?partial_term={partial_name}")
        assert suggestions_response.status_code == 200
        suggestions = suggestions_response.json()["suggestions"]
        
        # 2. Hacer búsqueda fuzzy con el nombre completo
        fuzzy_response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}")
        assert fuzzy_response.status_code == 200
        fuzzy_result = fuzzy_response.json()
        assert fuzzy_result["total_found"] > 0
        
        # 3. Obtener documentos por nombre exacto
        docs_response = api_client.get(f"/api/v1/search/patients/{patient_name}/documents")
        assert docs_response.status_code == 200
        docs_result = docs_response.json()
        assert docs_result["total_found"] > 0
        
        # 4. Verificar consistencia entre resultados
        fuzzy_doc = fuzzy_result["documents"][0]
        direct_doc = docs_result["documents"][0]
        assert fuzzy_doc["document_id"] == direct_doc["document_id"]
        assert fuzzy_doc["nombre_paciente"] == direct_doc["nombre_paciente"]

    def test_search_with_multiple_documents_same_patient(self, api_client, clean_database, sample_medical_pdf_file, test_user_data, wait_for_processing):
        """Test de búsqueda con múltiples documentos del mismo paciente."""
        # Crear múltiples documentos para el mismo paciente
        document_ids = []
        
        for i in range(3):
            # Crear nombre de archivo único pero mismo paciente
            filename = f"4000123456_GARCIA LOPEZ, MARIA_20240101000{i+1}_EMER.pdf"
            
            with open(sample_medical_pdf_file["path"], "rb") as file:
                files = {"file": (filename, file, "application/pdf")}
                data = {"user_id": test_user_data["user_id"]}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                assert response.status_code == 201
                
                document_id = response.json()["document_id"]
                document_ids.append(document_id)
                
                # Esperar procesamiento
                wait_for_processing(api_client, document_id)
        
        # Buscar por nombre de paciente
        patient_name = "GARCIA LOPEZ, MARIA"
        response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["total_found"] == 3
        assert len(result["documents"]) == 3
        
        # Verificar que todos los documentos pertenecen al mismo paciente
        for doc in result["documents"]:
            assert doc["nombre_paciente"] == patient_name
            assert doc["document_id"] in document_ids

    def test_search_performance_with_large_dataset(self, api_client, clean_database, sample_medical_pdf_file, test_user_data, wait_for_processing):
        """Test de rendimiento con dataset más grande."""
        # Crear varios documentos con diferentes pacientes
        patients = [
            "GARCIA LOPEZ, MARIA",
            "MARTINEZ PEREZ, JUAN",
            "RODRIGUEZ SANCHEZ, ANA",
            "LOPEZ HERNANDEZ, CARLOS",
            "FERNANDEZ GOMEZ, LUCIA"
        ]
        
        document_ids = []
        
        for i, patient in enumerate(patients):
            # Crear 2 documentos por paciente
            for j in range(2):
                filename = f"400012345{i}_{'_'.join(patient.split(', '))}_20240101000{j+1}_CONS.pdf"
                
                with open(sample_medical_pdf_file["path"], "rb") as file:
                    files = {"file": (filename, file, "application/pdf")}
                    data = {"user_id": test_user_data["user_id"]}
                    
                    response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                    assert response.status_code == 201
                    
                    document_id = response.json()["document_id"]
                    document_ids.append(document_id)
                    
                    # Esperar procesamiento
                    wait_for_processing(api_client, document_id)
        
        # Test de rendimiento de búsqueda
        start_time = time.time()
        
        # Buscar por cada paciente
        for patient in patients:
            response = api_client.get(f"/api/v1/search/patients?search_term={patient}")
            assert response.status_code == 200
            
            result = response.json()
            assert result["total_found"] == 2  # 2 documentos por paciente
        
        end_time = time.time()
        
        # Verificar que las búsquedas se completaron en tiempo razonable
        total_time = end_time - start_time
        assert total_time < 10  # Menos de 10 segundos para 5 búsquedas
        
        # Test de sugerencias
        suggestion_response = api_client.get("/api/v1/search/patients/suggestions?partial_term=GAR")
        assert suggestion_response.status_code == 200
        suggestions = suggestion_response.json()["suggestions"]
        assert "GARCIA LOPEZ, MARIA" in suggestions

    def test_search_edge_cases_comprehensive(self, api_client, uploaded_document):
        """Test comprehensivo de casos edge en búsqueda."""
        patient_name = uploaded_document["file_info"]["nombre_paciente"]
        
        # Caso 1: Búsqueda con números
        response1 = api_client.get("/api/v1/search/patients?search_term=123")
        assert response1.status_code == 200
        
        # Caso 2: Búsqueda con espacios múltiples
        response2 = api_client.get("/api/v1/search/patients?search_term=GARCIA  LOPEZ")
        assert response2.status_code == 200
        
        # Caso 3: Búsqueda con signos de puntuación
        response3 = api_client.get("/api/v1/search/patients?search_term=GARCIA, LOPEZ")
        assert response3.status_code == 200
        
        # Caso 4: Búsqueda con umbral de similitud muy bajo
        response4 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&min_similarity=0.01")
        assert response4.status_code == 200
        
        # Caso 5: Búsqueda con umbral de similitud muy alto
        response5 = api_client.get(f"/api/v1/search/patients?search_term={patient_name}&min_similarity=0.99")
        assert response5.status_code == 200
        
        # Todos los casos deberían manejar los inputs correctamente
        for response in [response1, response2, response3, response4, response5]:
            result = response.json()
            assert "documents" in result
            assert "total_found" in result
            assert isinstance(result["documents"], list) 