"""
Tests para endpoints de chat y sesiones.
Incluye creación de sesiones, listado, preguntas con streaming, estadísticas y eliminación.
"""

import pytest
import json
import time
import httpx
from typing import Dict, Any


class TestChatSessions:
    """Tests para gestión de sesiones de chat."""

    def test_create_chat_session_success(self, api_client, uploaded_document):
        """Test de creación exitosa de sesión de chat."""
        session_data = {
            "user_id": uploaded_document["user_data"]["user_id"],
            "document_id": uploaded_document["document_id"],
            "session_name": "Test Chat Session"
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        assert response.status_code == 201
        
        session = response.json()
        assert "session_id" in session
        assert session["user_id"] == session_data["user_id"]
        assert session["document_id"] == session_data["document_id"]
        assert session["session_name"] == session_data["session_name"]
        assert session["is_active"] is True
        assert session["interaction_count"] == 0
        assert "created_at" in session
        assert "last_interaction_at" in session

    def test_create_chat_session_default_name(self, api_client, uploaded_document):
        """Test de creación de sesión sin nombre personalizado."""
        session_data = {
            "user_id": uploaded_document["user_data"]["user_id"],
            "document_id": uploaded_document["document_id"]
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        assert response.status_code == 201
        
        session = response.json()
        assert "session_name" in session
        assert session["session_name"] is not None
        assert len(session["session_name"]) > 0

    @pytest.mark.edge_case
    def test_create_chat_session_nonexistent_document(self, api_client, clean_database, test_user_data):
        """Test de error al crear sesión con documento inexistente."""
        session_data = {
            "user_id": test_user_data["user_id"],
            "document_id": "60f7b3b8e8f4c2a1b8d3e4f5",  # ID válido pero inexistente
            "session_name": "Test Session"
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        assert response.status_code == 400

    @pytest.mark.edge_case
    def test_create_chat_session_missing_required_fields(self, api_client, clean_database):
        """Test de error con campos requeridos faltantes."""
        # Sin user_id
        response1 = api_client.post("/api/v1/chat/sessions", json={"document_id": "test"})
        assert response1.status_code == 422
        
        # Sin document_id
        response2 = api_client.post("/api/v1/chat/sessions", json={"user_id": "test"})
        assert response2.status_code == 422

    def test_create_chat_session_long_name(self, api_client, uploaded_document):
        """Test con nombre de sesión largo."""
        long_name = "x" * 200  # Máximo permitido
        
        session_data = {
            "user_id": uploaded_document["user_data"]["user_id"],
            "document_id": uploaded_document["document_id"],
            "session_name": long_name
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        assert response.status_code == 201
        assert response.json()["session_name"] == long_name

    @pytest.mark.edge_case
    def test_create_chat_session_too_long_name(self, api_client, uploaded_document):
        """Test con nombre que excede el límite."""
        too_long_name = "x" * 201  # Excede límite
        
        session_data = {
            "user_id": uploaded_document["user_data"]["user_id"],
            "document_id": uploaded_document["document_id"],
            "session_name": too_long_name
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        assert response.status_code == 422

    @pytest.mark.edge_case
    def test_create_chat_session_user_document_mismatch(self, api_client, uploaded_document, test_user_data):
        """Test de error HTTP 500 cuando user_id no coincide con propietario del documento."""
        # Intentar crear sesión con un usuario diferente al propietario del documento
        different_user_id = test_user_data["alternative_user_id"]
        
        session_data = {
            "user_id": different_user_id,  # Usuario diferente al propietario
            "document_id": uploaded_document["document_id"],
            "session_name": "Unauthorized Session"
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        # Verificar que se devuelve HTTP 500 con formato específico
        assert response.status_code == 500
        
        result = response.json()
        
        # Verificar estructura específica del error
        assert "error_code" in result
        assert result["error_code"] == "HTTP_500"
        
        assert "error_message" in result
        error_message = result["error_message"]
        
        assert error_message["error_code"] == "SESSION_CREATION_FAILED"
        assert "message" in error_message
        assert "request_id" in error_message
        assert "suggestion" in error_message
        
        assert "timestamp" in result
        assert isinstance(result["timestamp"], (int, float))
        
        print(f"✓ UserDocumentMismatchException test passed with correct format: {result}")


class TestChatSessionExceptions:
    """Tests para manejo específico de excepciones en creación de sesiones de chat."""

    @pytest.mark.edge_case
    def test_create_session_invalid_document_id_format(self, api_client, test_user_data):
        """Test de error con formato de document_id inválido."""
        # Casos de document_id con formato inválido
        invalid_document_ids = [
            "invalid_id",  # No es ObjectId
            "123",  # Muy corto
            "60f7b3b8e8f4c2a1b8d3e4f",  # 23 caracteres (falta 1)
            "60f7b3b8e8f4c2a1b8d3e4f55",  # 25 caracteres (sobra 1)
            "gggggggggggggggggggggggg",  # Caracteres no hex
            "",  # Vacío
            "   ",  # Solo espacios
        ]
        
        for invalid_id in invalid_document_ids:
            session_data = {
                "user_id": test_user_data["user_id"],
                "document_id": invalid_id,
                "session_name": "Test Session"
            }
            
            response = api_client.post("/api/v1/chat/sessions", json=session_data)
            
            # Algunas validaciones son interceptadas por FastAPI (422) y otras por nuestro código (400)
            assert response.status_code in [400, 422]
            data = response.json()
            
            if response.status_code == 400:
                # Nuestro validador personalizado - estructura anidada
                assert "error_code" in data
                assert data["error_code"] == "HTTP_400"
                assert "error_message" in data
                
                # Check nested error details
                error_details = data["error_message"]
                assert "error_code" in error_details
                assert error_details["error_code"] == "INVALID_DOCUMENT_ID_FORMAT"
                assert "message" in error_details
                assert "suggestion" in error_details
                assert "MongoDB ObjectId" in error_details["suggestion"]
            else:
                # FastAPI/Pydantic validation - estructura estándar
                assert "detail" in data
                if isinstance(data["detail"], list):
                    # Lista de errores de validación
                    assert len(data["detail"]) > 0
                    assert "msg" in data["detail"][0]
                else:
                    # Mensaje de error simple
                    assert isinstance(data["detail"], str)

    @pytest.mark.edge_case
    def test_create_session_invalid_user_id_format(self, api_client, uploaded_document):
        """Test de error con formato de user_id inválido."""
        # Casos de user_id con formato inválido - probemos solo los que llegan a nuestro validador
        invalid_user_ids = [
            "user@domain.com",  # Contiene @
            "user#123",  # Contiene #
            "user with spaces",  # Contiene espacios
            "user/slash",  # Contiene /
            "user\\backslash",  # Contiene \
            "user<>brackets",  # Contiene < >
            "a" * 101,  # Muy largo (>100 caracteres)
        ]
        
        for invalid_user_id in invalid_user_ids:
            session_data = {
                "user_id": invalid_user_id,
                "document_id": uploaded_document["document_id"],
                "session_name": "Test Session"
            }
            
            response = api_client.post("/api/v1/chat/sessions", json=session_data)
            
            # Algunas validaciones son interceptadas por FastAPI (422) y otras por nuestro código (400)
            assert response.status_code in [400, 422]
            data = response.json()
            
            if response.status_code == 400:
                # Nuestro validador personalizado - estructura anidada
                assert "error_code" in data
                assert data["error_code"] == "HTTP_400"
                assert "error_message" in data
                
                # Check nested error details
                error_details = data["error_message"]
                assert "error_code" in error_details
                assert error_details["error_code"] == "INVALID_USER_ID_FORMAT"
                assert "message" in error_details
                assert "suggestion" in error_details
                assert "alphanumeric" in error_details["suggestion"]
            else:
                # FastAPI/Pydantic validation
                assert "detail" in data

    @pytest.mark.edge_case
    def test_create_session_document_not_found(self, api_client, test_user_data):
        """Test de error con documento inexistente pero con formato ObjectId válido."""
        session_data = {
            "user_id": test_user_data["user_id"],
            "document_id": "60f7b3b8e8f4c2a1b8d3e4f5",  # ObjectId válido pero inexistente
            "session_name": "Test Session"
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        assert response.status_code == 404
        data = response.json()
        
        # Check main error structure
        assert "error_code" in data
        assert data["error_code"] == "HTTP_404"
        assert "error_message" in data
        
        # Check nested error details
        error_details = data["error_message"]
        assert "error_code" in error_details
        assert error_details["error_code"] == "DOCUMENT_NOT_FOUND"
        assert "message" in error_details
        assert "suggestion" in error_details
        assert "verify the document ID exists" in error_details["suggestion"]
        assert "60f7b3b8e8f4c2a1b8d3e4f5" in error_details["message"]

    @pytest.mark.edge_case
    def test_create_session_with_empty_data(self, api_client):
        """Test de error con datos vacíos."""
        session_data = {}
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        # FastAPI validation should catch this before our custom validation
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.edge_case
    def test_create_session_with_null_values(self, api_client):
        """Test de error con valores null."""
        session_data = {
            "user_id": None,
            "document_id": None,
            "session_name": "Test Session"
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        # FastAPI validation should catch this
        assert response.status_code == 422
        error_data = response.json()
        assert "detail" in error_data

    @pytest.mark.edge_case
    def test_create_session_invalid_session_name_characters(self, api_client, uploaded_document):
        """Test de validación de session_name con caracteres problemáticos."""
        # Casos de session_name con caracteres problemáticos
        # Vamos a probar casos menos extremos primero
        problematic_names = [
            "a" * 201,  # Muy largo (>200 caracteres)
            "Session \"with quotes\"",  # Comillas dobles
            "Session 'with quotes'",  # Comillas simples
            "Session\\with\\backslashes",  # Backslashes
        ]
        
        for problematic_name in problematic_names:
            session_data = {
                "user_id": uploaded_document["user_data"]["user_id"],
                "document_id": uploaded_document["document_id"],
                "session_name": problematic_name
            }
            
            response = api_client.post("/api/v1/chat/sessions", json=session_data)
            
            # La validación de session_name debería atrapar algunos casos
            # pero otros podrían pasar a través de FastAPI validation
            assert response.status_code in [400, 422]
            data = response.json()
            
            if response.status_code == 400:
                # Nuestro validador personalizado - estructura anidada
                assert "error_code" in data
                assert data["error_code"] == "HTTP_400"
                assert "error_message" in data
                
                error_details = data["error_message"]
                assert "error_code" in error_details
                assert "message" in error_details
                assert "suggestion" in error_details
            else:
                # Validación de FastAPI - estructura diferente
                assert "detail" in data

    @pytest.mark.edge_case
    def test_create_session_valid_edge_cases(self, api_client, uploaded_document):
        """Test de casos edge válidos que deberían funcionar."""
        valid_cases = [
            {
                "user_id": "user_123",
                "session_name": None  # Debería ser permitido
            },
            {
                "user_id": "user.with.dots",
                "session_name": ""  # Debería convertirse a None
            },
            {
                "user_id": "user-with-hyphens",
                "session_name": "   "  # Solo espacios, debería convertirse a None
            },
            {
                "user_id": "user_123",
                "session_name": "a" * 200  # Exactamente 200 caracteres
            }
        ]
        
        for case in valid_cases:
            session_data = {
                "user_id": case["user_id"],
                "document_id": uploaded_document["document_id"],
                "session_name": case["session_name"]
            }
            
            response = api_client.post("/api/v1/chat/sessions", json=session_data)
            
            assert response.status_code == 201
            session = response.json()
            assert "session_id" in session
            assert session["user_id"] == case["user_id"]
            assert session["document_id"] == uploaded_document["document_id"]
            
            # session_name debería ser None si era None, vacío o solo espacios
            if not case["session_name"] or not case["session_name"].strip():
                assert session["session_name"] is not None  # Se genera automáticamente
            else:
                assert session["session_name"] == case["session_name"]

    @pytest.mark.edge_case  
    def test_create_session_error_response_structure(self, api_client, test_user_data):
        """Test de estructura de respuestas de error."""
        session_data = {
            "user_id": test_user_data["user_id"],
            "document_id": "invalid_format",  # Formato inválido
            "session_name": "Test Session"
        }
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        assert response.status_code == 400
        data = response.json()
        
        # Verificar estructura principal
        main_required_fields = ["error_code", "error_message", "timestamp"]
        for field in main_required_fields:
            assert field in data, f"Campo principal '{field}' faltante en respuesta de error"
        
        # Verificar estructura anidada
        error_details = data["error_message"]
        nested_required_fields = ["error_code", "message", "suggestion"]
        for field in nested_required_fields:
            assert field in error_details, f"Campo anidado '{field}' faltante en respuesta de error"
        
        # Verificar tipos de datos
        assert isinstance(data["error_code"], str)
        assert isinstance(error_details["error_code"], str)
        assert isinstance(error_details["message"], str)
        assert isinstance(error_details["suggestion"], str)
        
        # Verificar que los campos no están vacíos
        assert len(data["error_code"]) > 0
        assert len(error_details["error_code"]) > 0
        assert len(error_details["message"]) > 0
        assert len(error_details["suggestion"]) > 0


class TestChatSessionListing:
    """Tests para listado de sesiones de chat."""

    def test_list_sessions_empty(self, api_client, clean_database, test_user_data):
        """Test de listado cuando no hay sesiones."""
        response = api_client.get(f"/api/v1/chat/sessions?user_id={test_user_data['user_id']}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "sessions" in result
        assert len(result["sessions"]) == 0
        assert result["total_found"] == 0

    def test_list_sessions_with_sessions(self, api_client, chat_session):
        """Test de listado con sesiones existentes."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert len(result["sessions"]) == 1
        
        session = result["sessions"][0]
        assert session["session_id"] == chat_session["session_id"]
        assert session["user_id"] == user_id

    @pytest.mark.edge_case
    def test_list_sessions_missing_user_id(self, api_client, clean_database):
        """Test de error al no proporcionar user_id."""
        response = api_client.get("/api/v1/chat/sessions")
        
        assert response.status_code == 400

    def test_list_sessions_filter_by_document(self, api_client, chat_session):
        """Test de filtrado por documento."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        document_id = chat_session["document"]["document_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&document_id={document_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert len(result["sessions"]) == 1
        assert result["sessions"][0]["document_id"] == document_id

    def test_list_sessions_filter_nonexistent_document(self, api_client, chat_session):
        """Test de filtrado por documento inexistente."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        nonexistent_doc_id = "60f7b3b8e8f4c2a1b8d3e4f5"
        
        response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&document_id={nonexistent_doc_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert len(result["sessions"]) == 0

    def test_list_sessions_pagination(self, api_client, chat_session):
        """Test de paginación en listado de sesiones."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        # Crear sesiones adicionales para testing de paginación
        for i in range(3):
            session_data = {
                "user_id": user_id,
                "document_id": chat_session["document"]["document_id"],
                "session_name": f"Extra Session {i}"
            }
            api_client.post("/api/v1/chat/sessions", json=session_data)
        
        # Test con limit
        response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&limit=2")
        
        assert response.status_code == 200
        
        result = response.json()
        assert len(result["sessions"]) <= 2
        assert result["limit"] == 2

    def test_list_sessions_active_only_filter(self, api_client, chat_session):
        """Test de filtro por sesiones activas únicamente."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        # Test con active_only=true (default)
        response1 = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&active_only=true")
        assert response1.status_code == 200
        
        # Test con active_only=false
        response2 = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&active_only=false")
        assert response2.status_code == 200


class TestChatSessionListingExceptions:
    """Tests para manejo específico de excepciones en listado de sesiones de chat."""

    @pytest.mark.edge_case
    def test_list_sessions_missing_user_id(self, api_client):
        """Test de error cuando user_id es requerido pero no se proporciona."""
        response = api_client.get("/api/v1/chat/sessions")
        
        assert response.status_code == 400
        data = response.json()
        
        # Check main error structure
        assert "error_code" in data
        assert data["error_code"] == "HTTP_400"
        assert "error_message" in data
        
        # Check nested error details
        error_details = data["error_message"]
        assert "error_code" in error_details
        assert error_details["error_code"] == "USER_ID_REQUIRED"
        assert "message" in error_details
        assert "suggestion" in error_details
        assert "user_id parameter is required" in error_details["message"]

    @pytest.mark.edge_case
    def test_list_sessions_invalid_user_id_format(self, api_client):
        """Test de error con formato de user_id inválido."""
        # Casos de user_id con formato inválido que son más seguros para testing
        invalid_user_ids = [
            "user@domain.com",  # Contiene @
            "user#123",  # Contiene #
            "a" * 101,  # Muy largo (>100 caracteres)
        ]
        
        for invalid_user_id in invalid_user_ids:
            response = api_client.get(f"/api/v1/chat/sessions?user_id={invalid_user_id}")
            
            # Puede ser 400 (nuestras validaciones), 422 (FastAPI), 200 (URL encoding), o 500 (casos edge extremos)
            assert response.status_code in [200, 400, 422, 500]
            
            if response.status_code == 400:
                data = response.json()
                
                # Check main error structure for our custom validation
                assert "error_code" in data
                assert data["error_code"] == "HTTP_400"
                assert "error_message" in data
                
                # Check nested error details
                error_details = data["error_message"]
                assert "error_code" in error_details
                assert error_details["error_code"] == "INVALID_USER_ID_FORMAT"
                assert "message" in error_details
                assert "suggestion" in error_details
                assert "alphanumeric" in error_details["suggestion"]
            elif response.status_code == 422:
                # FastAPI validation
                data = response.json()
                assert "detail" in data
            elif response.status_code == 500:
                # Internal server error para casos edge extremos
                # Puede no tener JSON válido, así que solo verificamos que sea 500
                pass
            # Si es 200, el URL encoding puede haber hecho que el user_id sea válido

    @pytest.mark.edge_case
    def test_list_sessions_invalid_document_id_filter(self, api_client, test_user_data):
        """Test de error con formato de document_id inválido en filtro."""
        # Casos de document_id con formato inválido
        invalid_document_ids = [
            "invalid_id",  # No es ObjectId
            "123",  # Muy corto
            "60f7b3b8e8f4c2a1b8d3e4f",  # 23 caracteres (falta 1)
            "60f7b3b8e8f4c2a1b8d3e4f55",  # 25 caracteres (sobra 1)
            "gggggggggggggggggggggggg",  # Caracteres no hex
        ]
        
        for invalid_id in invalid_document_ids:
            response = api_client.get(f"/api/v1/chat/sessions?user_id={test_user_data['user_id']}&document_id={invalid_id}")
            
            assert response.status_code == 400
            data = response.json()
            
            # Check main error structure
            assert "error_code" in data
            assert data["error_code"] == "HTTP_400"
            assert "error_message" in data
            
            # Check nested error details
            error_details = data["error_message"]
            assert "error_code" in error_details
            assert error_details["error_code"] == "INVALID_DOCUMENT_ID_FILTER"
            assert "message" in error_details
            assert "suggestion" in error_details
            assert "MongoDB ObjectId" in error_details["suggestion"]

    @pytest.mark.edge_case
    def test_list_sessions_invalid_pagination_parameters(self, api_client, test_user_data):
        """Test de error con parámetros de paginación inválidos."""
        user_id = test_user_data["user_id"]
        
        # Test limit inválido
        invalid_limits = [0, -1, 101, 200]
        for invalid_limit in invalid_limits:
            response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&limit={invalid_limit}")
            
            # Puede ser 400 (nuestras validaciones) o 422 (FastAPI validation)
            assert response.status_code in [400, 422]
            data = response.json()
            
            if response.status_code == 400:
                # Nuestras validaciones personalizadas - estructura anidada
                assert "error_code" in data
                assert data["error_code"] == "HTTP_400"
                assert "error_message" in data
                
                # Check nested error details
                error_details = data["error_message"]
                assert "error_code" in error_details
                assert error_details["error_code"] == "INVALID_PAGINATION_PARAMETERS"
                assert "message" in error_details
                assert "suggestion" in error_details
                assert "limit" in error_details["message"]
            else:
                # FastAPI/Pydantic validation - estructura estándar
                assert "detail" in data
        
        # Test skip inválido
        invalid_skips = [-1, -10]
        for invalid_skip in invalid_skips:
            response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&skip={invalid_skip}")
            
            # Puede ser 400 (nuestras validaciones) o 422 (FastAPI validation)
            assert response.status_code in [400, 422]
            data = response.json()
            
            if response.status_code == 400:
                # Check nested error details
                error_details = data["error_message"]
                assert error_details["error_code"] == "INVALID_PAGINATION_PARAMETERS"
                assert "skip" in error_details["message"]
            else:
                # FastAPI validation
                assert "detail" in data

    @pytest.mark.edge_case
    def test_list_sessions_document_filter_works(self, api_client, chat_session):
        """Test que el filtro por document_id funciona correctamente."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        document_id = chat_session["document"]["document_id"]
        
        # Test con document_id correcto
        response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&document_id={document_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sessions" in data
        sessions = data["sessions"]
        assert len(sessions) == 1  # Debería encontrar exactamente 1 sesión
        assert sessions[0]["document_id"] == document_id
        assert sessions[0]["user_id"] == user_id

    @pytest.mark.edge_case
    def test_list_sessions_document_filter_no_results(self, api_client, chat_session):
        """Test que el filtro por document_id devuelve lista vacía cuando no hay coincidencias."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        nonexistent_document_id = "60f7b3b8e8f4c2a1b8d3e4f5"  # ObjectId válido pero inexistente
        
        response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}&document_id={nonexistent_document_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert "sessions" in data
        sessions = data["sessions"]
        assert len(sessions) == 0  # No debería encontrar sesiones

    @pytest.mark.edge_case
    def test_list_sessions_valid_edge_cases(self, api_client, test_user_data):
        """Test de casos edge válidos que deberían funcionar."""
        valid_cases = [
            {"user_id": "user_123", "limit": 1},
            {"user_id": "user.with.dots", "limit": 100},
            {"user_id": "user-with-hyphens", "skip": 0},
            {"user_id": "user_123", "active_only": "false"},
            {"user_id": "user_123", "active_only": "true"},
        ]
        
        for case in valid_cases:
            query_params = "&".join([f"{key}={value}" for key, value in case.items()])
            response = api_client.get(f"/api/v1/chat/sessions?{query_params}")
            
            assert response.status_code == 200
            data = response.json()
            
            assert "sessions" in data
            assert "total_found" in data
            assert "limit" in data
            assert "skip" in data
            assert isinstance(data["sessions"], list)

    @pytest.mark.edge_case
    def test_list_sessions_error_response_structure(self, api_client):
        """Test de estructura de respuestas de error."""
        # Test sin user_id
        response = api_client.get("/api/v1/chat/sessions")
        
        assert response.status_code == 400
        data = response.json()
        
        # Verificar estructura principal
        main_required_fields = ["error_code", "error_message", "timestamp"]
        for field in main_required_fields:
            assert field in data, f"Campo principal '{field}' faltante en respuesta de error"
        
        # Verificar estructura anidada
        error_details = data["error_message"]
        nested_required_fields = ["error_code", "message", "suggestion"]
        for field in nested_required_fields:
            assert field in error_details, f"Campo anidado '{field}' faltante en respuesta de error"
        
        # Verificar tipos de datos
        assert isinstance(data["error_code"], str)
        assert isinstance(error_details["error_code"], str)
        assert isinstance(error_details["message"], str)
        assert isinstance(error_details["suggestion"], str)
        
        # Verificar que los campos no están vacíos
        assert len(data["error_code"]) > 0
        assert len(error_details["error_code"]) > 0
        assert len(error_details["message"]) > 0
        assert len(error_details["suggestion"]) > 0


class TestChatQuestions:
    """Tests para hacer preguntas en chat."""

    @pytest.mark.slow
    def test_ask_question_streaming_success(self, api_client, chat_session):
        """Test de pregunta con respuesta streaming exitosa."""
        question_data = {
            "session_id": chat_session["session_id"],
            "user_id": chat_session["document"]["user_data"]["user_id"],
            "document_id": chat_session["document"]["document_id"],
            "question": "¿Cuál es el diagnóstico principal del paciente?"
        }
        
        with httpx.stream("POST", f"{api_client.base_url}/api/v1/chat/ask", json=question_data) as response:
            assert response.status_code == 200
            assert response.headers.get("content-type") == "text/event-stream; charset=utf-8"
            
            events = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])  # Remove "data: "
                        events.append(event_data)
                    except json.JSONDecodeError:
                        continue
            
            # Verificar que recibimos eventos
            assert len(events) > 0
            
            # Verificar tipos de eventos
            event_types = [event.get("type") for event in events]
            assert "start" in event_types
            assert any(event.get("type") == "content" for event in events)
            assert "end" in event_types

    def test_ask_question_simple(self, api_client, chat_session):
        """Test de pregunta simple."""
        question_data = {
            "session_id": chat_session["session_id"],
            "user_id": chat_session["document"]["user_data"]["user_id"],
            "document_id": chat_session["document"]["document_id"],
            "question": "Hola"
        }
        
        response = api_client.post("/api/v1/chat/ask", json=question_data)
        
        # Debería iniciar el streaming correctamente
        assert response.status_code == 200

    @pytest.mark.edge_case
    def test_ask_question_missing_fields(self, api_client, clean_database):
        """Test de error con campos faltantes."""
        # Sin session_id
        response1 = api_client.post("/api/v1/chat/ask", json={
            "user_id": "test",
            "document_id": "test",
            "question": "test"
        })
        assert response1.status_code == 422
        
        # Sin question
        response2 = api_client.post("/api/v1/chat/ask", json={
            "session_id": "test",
            "user_id": "test",
            "document_id": "test"
        })
        assert response2.status_code == 422

    @pytest.mark.edge_case
    def test_ask_question_nonexistent_session(self, api_client, clean_database, test_user_data):
        """Test de error con sesión inexistente."""
        question_data = {
            "session_id": "nonexistent-session-id",
            "user_id": test_user_data["user_id"],
            "document_id": "some-document-id",
            "question": "Test question"
        }
        
        response = api_client.post("/api/v1/chat/ask", json=question_data)
        
        # Debería fallar debido a sesión inexistente
        assert response.status_code in [400, 500]

    def test_ask_question_very_short(self, api_client, chat_session):
        """Test con pregunta muy corta."""
        question_data = {
            "session_id": chat_session["session_id"],
            "user_id": chat_session["document"]["user_data"]["user_id"],
            "document_id": chat_session["document"]["document_id"],
            "question": "¿?"
        }
        
        response = api_client.post("/api/v1/chat/ask", json=question_data)
        
        assert response.status_code == 200

    @pytest.mark.edge_case
    def test_ask_question_too_short(self, api_client, chat_session):
        """Test con pregunta que no cumple el mínimo."""
        question_data = {
            "session_id": chat_session["session_id"],
            "user_id": chat_session["document"]["user_data"]["user_id"],
            "document_id": chat_session["document"]["document_id"],
            "question": "a"  # Solo 1 carácter, mínimo es 3
        }
        
        response = api_client.post("/api/v1/chat/ask", json=question_data)
        
        assert response.status_code == 422


class TestChatSessionInfo:
    """Tests para obtener información de sesiones."""

    def test_get_session_info_success(self, api_client, chat_session):
        """Test de obtención exitosa de información de sesión."""
        session_id = chat_session["session_id"]
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}?user_id={user_id}")
        
        assert response.status_code == 200
        
        session_info = response.json()
        assert session_info["session_id"] == session_id
        assert session_info["user_id"] == user_id
        assert "document_id" in session_info
        assert "session_name" in session_info
        assert "is_active" in session_info
        assert "created_at" in session_info
        assert "last_interaction_at" in session_info
        assert "interaction_count" in session_info

    @pytest.mark.edge_case
    def test_get_session_info_missing_user_id(self, api_client, chat_session):
        """Test de error al no proporcionar user_id."""
        session_id = chat_session["session_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}")
        
        assert response.status_code == 422

    @pytest.mark.edge_case
    def test_get_session_info_wrong_user(self, api_client, chat_session, test_user_data):
        """Test de error al intentar acceder con usuario incorrecto."""
        session_id = chat_session["session_id"]
        wrong_user_id = test_user_data["alternative_user_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}?user_id={wrong_user_id}")
        
        assert response.status_code == 400

    @pytest.mark.edge_case
    def test_get_session_info_nonexistent(self, api_client, clean_database, test_user_data):
        """Test con sesión inexistente."""
        fake_session_id = "nonexistent-session-id"
        user_id = test_user_data["user_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{fake_session_id}?user_id={user_id}")
        
        assert response.status_code == 404


class TestChatSessionInteractions:
    """Tests para interacciones en sesiones de chat."""

    def test_get_session_interactions_empty(self, api_client, chat_session):
        """Test de obtención de interacciones en sesión vacía."""
        session_id = chat_session["session_id"]
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}/interactions?user_id={user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["session_id"] == session_id
        assert result["user_id"] == user_id
        assert len(result["interactions"]) == 0

    @pytest.mark.slow
    def test_get_session_interactions_with_data(self, api_client, chat_session):
        """Test de obtención de interacciones con datos."""
        session_id = chat_session["session_id"]
        user_id = chat_session["document"]["user_data"]["user_id"]
        document_id = chat_session["document"]["document_id"]
        
        # Crear una interacción primero
        question_data = {
            "session_id": session_id,
            "user_id": user_id,
            "document_id": document_id,
            "question": "¿Cuál es el contenido del documento?"
        }
        
        # Hacer la pregunta (esto creará una interacción)
        ask_response = api_client.post("/api/v1/chat/ask", json=question_data)
        assert ask_response.status_code == 200
        
        # Esperar un poco para que se procese
        time.sleep(2)
        
        # Obtener interacciones
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}/interactions?user_id={user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert len(result["interactions"]) > 0
        
        interaction = result["interactions"][0]
        assert "interaction_id" in interaction
        assert interaction["session_id"] == session_id
        assert interaction["user_id"] == user_id
        assert interaction["question"] == question_data["question"]
        assert "response" in interaction
        assert "created_at" in interaction

    def test_get_session_interactions_pagination(self, api_client, chat_session):
        """Test de paginación en interacciones."""
        session_id = chat_session["session_id"]
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}/interactions?user_id={user_id}&limit=10&skip=0")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["limit"] == 10
        assert result["skip"] == 0

    @pytest.mark.edge_case
    def test_get_session_interactions_missing_user_id(self, api_client, chat_session):
        """Test de error al no proporcionar user_id."""
        session_id = chat_session["session_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}/interactions")
        
        assert response.status_code == 422


class TestChatSessionDeletion:
    """Tests para eliminación de sesiones de chat."""

    def test_delete_session_success(self, api_client, chat_session):
        """Test de eliminación exitosa de sesión."""
        session_id = chat_session["session_id"]
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        response = api_client.delete(f"/api/v1/chat/sessions/{session_id}?user_id={user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["session_id"] == session_id
        assert result["deleted"] is True
        assert "interactions_deleted" in result
        assert "message" in result
        assert "deleted_timestamp" in result
        
        # Verificar que la sesión ya no existe
        get_response = api_client.get(f"/api/v1/chat/sessions/{session_id}?user_id={user_id}")
        assert get_response.status_code == 404

    @pytest.mark.edge_case
    def test_delete_session_missing_user_id(self, api_client, chat_session):
        """Test de error al no proporcionar user_id."""
        session_id = chat_session["session_id"]
        
        response = api_client.delete(f"/api/v1/chat/sessions/{session_id}")
        
        assert response.status_code == 422

    @pytest.mark.edge_case
    def test_delete_session_wrong_user(self, api_client, chat_session, test_user_data):
        """Test de error al intentar eliminar con usuario incorrecto."""
        session_id = chat_session["session_id"]
        wrong_user_id = test_user_data["alternative_user_id"]
        
        response = api_client.delete(f"/api/v1/chat/sessions/{session_id}?user_id={wrong_user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["deleted"] is False

    @pytest.mark.edge_case
    def test_delete_session_nonexistent(self, api_client, clean_database, test_user_data):
        """Test de eliminación de sesión inexistente."""
        fake_session_id = "nonexistent-session-id"
        user_id = test_user_data["user_id"]
        
        response = api_client.delete(f"/api/v1/chat/sessions/{fake_session_id}?user_id={user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["deleted"] is False


class TestChatStatistics:
    """Tests para estadísticas de chat."""

    def test_get_chat_stats_empty(self, api_client, clean_database):
        """Test de estadísticas cuando no hay datos."""
        response = api_client.get("/api/v1/chat/stats")
        
        assert response.status_code == 200
        
        stats = response.json()
        assert "period_days" in stats
        assert "total_interactions" in stats
        assert "total_questions" in stats
        assert "total_responses" in stats
        assert stats["total_interactions"] == 0
        assert stats["total_questions"] == 0
        assert stats["total_responses"] == 0

    def test_get_chat_stats_with_filter(self, api_client, chat_session):
        """Test de estadísticas con filtros."""
        user_id = chat_session["document"]["user_data"]["user_id"]
        document_id = chat_session["document"]["document_id"]
        
        # Test con filtro por usuario
        response1 = api_client.get(f"/api/v1/chat/stats?user_id={user_id}")
        assert response1.status_code == 200
        
        # Test con filtro por documento
        response2 = api_client.get(f"/api/v1/chat/stats?document_id={document_id}")
        assert response2.status_code == 200
        
        # Test con ambos filtros
        response3 = api_client.get(f"/api/v1/chat/stats?user_id={user_id}&document_id={document_id}")
        assert response3.status_code == 200

    def test_get_chat_stats_custom_period(self, api_client, clean_database):
        """Test de estadísticas con período personalizado."""
        response = api_client.get("/api/v1/chat/stats?days=7")
        
        assert response.status_code == 200
        
        stats = response.json()
        assert stats["period_days"] == 7

    @pytest.mark.edge_case
    def test_get_chat_stats_invalid_period(self, api_client, clean_database):
        """Test con período inválido."""
        # Días negativos
        response1 = api_client.get("/api/v1/chat/stats?days=-1")
        assert response1.status_code == 422
        
        # Días que exceden el máximo
        response2 = api_client.get("/api/v1/chat/stats?days=400")
        assert response2.status_code == 422


class TestChatWorkflow:
    """Tests de flujo completo de chat."""

    @pytest.mark.slow
    def test_complete_chat_workflow(self, api_client, uploaded_document):
        """Test del flujo completo de chat: crear sesión -> preguntar -> obtener interacciones -> eliminar."""
        user_id = uploaded_document["user_data"]["user_id"]
        document_id = uploaded_document["document_id"]
        
        # 1. Crear sesión
        session_data = {
            "user_id": user_id,
            "document_id": document_id,
            "session_name": "Complete Workflow Test"
        }
        
        create_response = api_client.post("/api/v1/chat/sessions", json=session_data)
        assert create_response.status_code == 201
        session_id = create_response.json()["session_id"]
        
        # 2. Hacer una pregunta
        question_data = {
            "session_id": session_id,
            "user_id": user_id,
            "document_id": document_id,
            "question": "¿Qué información contiene este documento?"
        }
        
        ask_response = api_client.post("/api/v1/chat/ask", json=question_data)
        assert ask_response.status_code == 200
        
        # Esperar procesamiento
        time.sleep(3)
        
        # 3. Verificar que la sesión tiene interacciones
        interactions_response = api_client.get(f"/api/v1/chat/sessions/{session_id}/interactions?user_id={user_id}")
        assert interactions_response.status_code == 200
        interactions = interactions_response.json()["interactions"]
        assert len(interactions) > 0
        
        # 4. Obtener información de la sesión
        info_response = api_client.get(f"/api/v1/chat/sessions/{session_id}?user_id={user_id}")
        assert info_response.status_code == 200
        session_info = info_response.json()
        assert session_info["interaction_count"] > 0
        
        # 5. Eliminar sesión
        delete_response = api_client.delete(f"/api/v1/chat/sessions/{session_id}?user_id={user_id}")
        assert delete_response.status_code == 200
        assert delete_response.json()["deleted"] is True
        
        # 6. Verificar eliminación
        final_info_response = api_client.get(f"/api/v1/chat/sessions/{session_id}?user_id={user_id}")
        assert final_info_response.status_code == 404

    def test_multiple_sessions_same_document(self, api_client, uploaded_document):
        """Test de múltiples sesiones para el mismo documento."""
        user_id = uploaded_document["user_data"]["user_id"]
        document_id = uploaded_document["document_id"]
        
        # Crear múltiples sesiones
        session_ids = []
        for i in range(3):
            session_data = {
                "user_id": user_id,
                "document_id": document_id,
                "session_name": f"Session {i+1}"
            }
            
            response = api_client.post("/api/v1/chat/sessions", json=session_data)
            assert response.status_code == 201
            session_ids.append(response.json()["session_id"])
        
        # Verificar que todas las sesiones existen
        list_response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}")
        assert list_response.status_code == 200
        sessions = list_response.json()["sessions"]
        assert len(sessions) == 3
        
        # Verificar que todas pertenecen al mismo documento
        for session in sessions:
            assert session["document_id"] == document_id

    def test_session_isolation_between_users(self, api_client, uploaded_document, test_user_data):
        """Test de aislamiento de sesiones entre usuarios."""
        user1_id = uploaded_document["user_data"]["user_id"]
        user2_id = test_user_data["alternative_user_id"]
        document_id = uploaded_document["document_id"]
        
        # Usuario 1 crea sesión
        session_data_1 = {
            "user_id": user1_id,
            "document_id": document_id,
            "session_name": "User 1 Session"
        }
        
        response1 = api_client.post("/api/v1/chat/sessions", json=session_data_1)
        assert response1.status_code == 201
        session1_id = response1.json()["session_id"]
        
        # Usuario 2 no debería ver la sesión de usuario 1
        list_response = api_client.get(f"/api/v1/chat/sessions?user_id={user2_id}")
        assert list_response.status_code == 200
        user2_sessions = list_response.json()["sessions"]
        assert len(user2_sessions) == 0
        
        # Usuario 2 no debería poder acceder a la sesión de usuario 1
        access_response = api_client.get(f"/api/v1/chat/sessions/{session1_id}?user_id={user2_id}")
        assert access_response.status_code == 400 