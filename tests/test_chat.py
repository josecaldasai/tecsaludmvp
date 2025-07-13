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
    """Tests para obtener interacciones de sesiones."""

    def test_get_session_interactions_empty(self, api_client, chat_session):
        """Test de obtención de interacciones cuando no hay ninguna."""
        session_id = chat_session["session_id"]
        user_id = chat_session["document"]["user_data"]["user_id"]
        
        response = api_client.get(f"/api/v1/chat/sessions/{session_id}/interactions?user_id={user_id}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "interactions" in result
        assert len(result["interactions"]) == 0
        assert result["total_found"] == 0

    @pytest.mark.slow
    def test_get_session_interactions_with_data(self, api_client, chat_session):
        """Test de obtención de interacciones después de hacer una pregunta."""
        session_id = chat_session["session_id"]
        user_id = chat_session["document"]["user_data"]["user_id"]
        document_id = chat_session["document"]["document_id"]
        
        # Hacer una pregunta primero para crear una interacción
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