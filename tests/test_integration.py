"""
Tests de integración end-to-end para validar el flujo completo del sistema.
Estos tests validan que todos los componentes funcionen juntos correctamente.
"""

import pytest
import json
import time
import httpx
from typing import Dict, Any, List


class TestCompleteUserJourney:
    """Tests del recorrido completo del usuario a través del sistema."""

    @pytest.mark.slow
    @pytest.mark.integration
    def test_complete_user_journey_single_document(self, api_client, clean_database, sample_medical_pdf_file, test_user_data, wait_for_processing):
        """
        Test del recorrido completo de un usuario:
        1. Subir documento
        2. Esperar procesamiento
        3. Listar documentos
        4. Buscar por nombre de paciente
        5. Crear sesión de chat
        6. Hacer pregunta
        7. Obtener tokens
        8. Limpiar recursos
        """
        
        # 1. Subir documento
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {
                "user_id": test_user_data["user_id"],
                "description": "Documento médico de prueba completa",
                "tags": json.dumps(["integration", "test", "medical"])
            }
            
            upload_response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert upload_response.status_code == 201
            
            upload_result = upload_response.json()
            document_id = upload_result["document_id"]
            
            print(f"✓ Documento subido exitosamente: {document_id}")
        
        # 2. Esperar procesamiento completo
        processed_doc = wait_for_processing(api_client, document_id)
        assert processed_doc["processing_status"] == "completed"
        
        print(f"✓ Documento procesado exitosamente: {processed_doc['processing_status']}")
        
        # 3. Listar documentos del usuario
        list_response = api_client.get(f"/api/v1/documents/?user_id={test_user_data['user_id']}")
        assert list_response.status_code == 200
        
        documents = list_response.json()
        assert len(documents) == 1
        assert documents[0]["document_id"] == document_id
        
        print(f"✓ Documento listado correctamente: {len(documents)} documentos encontrados")
        
        # 4. Buscar por nombre de paciente
        patient_name = sample_medical_pdf_file["nombre_paciente"]
        search_response = api_client.get(f"/api/v1/search/patients?search_term={patient_name}")
        assert search_response.status_code == 200
        
        search_results = search_response.json()
        assert search_results["total_found"] > 0
        assert search_results["documents"][0]["document_id"] == document_id
        
        print(f"✓ Búsqueda fuzzy exitosa: {search_results['total_found']} resultados encontrados")
        
        # 5. Crear sesión de chat
        session_data = {
            "user_id": test_user_data["user_id"],
            "document_id": document_id,
            "session_name": "Sesión de prueba de integración"
        }
        
        session_response = api_client.post("/api/v1/chat/sessions", json=session_data)
        assert session_response.status_code == 201
        
        session_info = session_response.json()
        session_id = session_info["session_id"]
        
        print(f"✓ Sesión de chat creada: {session_id}")
        
        # 6. Hacer pregunta en chat
        question_data = {
            "session_id": session_id,
            "user_id": test_user_data["user_id"],
            "document_id": document_id,
            "question": "¿Cuál es el diagnóstico principal mencionado en este documento?"
        }
        
        # Usar streaming para la pregunta
        with httpx.stream("POST", f"{api_client.base_url}/api/v1/chat/ask", json=question_data) as response:
            assert response.status_code == 200
            
            events = []
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])
                        events.append(event_data)
                    except json.JSONDecodeError:
                        continue
            
            assert len(events) > 0
            event_types = [event.get("type") for event in events]
            assert "start" in event_types
            assert "end" in event_types
        
        print(f"✓ Pregunta procesada exitosamente: {len(events)} eventos recibidos")
        
        # Esperar a que se procese la interacción
        time.sleep(2)
        
        # 7. Verificar que la interacción se guardó
        interactions_response = api_client.get(f"/api/v1/chat/sessions/{session_id}/interactions?user_id={test_user_data['user_id']}")
        assert interactions_response.status_code == 200
        
        interactions = interactions_response.json()["interactions"]
        assert len(interactions) > 0
        assert interactions[0]["question"] == question_data["question"]
        
        print(f"✓ Interacción guardada correctamente: {len(interactions)} interacciones")
        
        # 8. Obtener tokens de Azure
        speech_token_response = api_client.get("/api/v1/tokens/speech")
        assert speech_token_response.status_code == 200
        
        storage_token_response = api_client.get("/api/v1/tokens/storage")
        assert storage_token_response.status_code == 200
        
        speech_token = speech_token_response.json()
        storage_token = storage_token_response.json()
        
        assert "access_token" in speech_token
        assert "sas_token" in storage_token
        
        print(f"✓ Tokens obtenidos exitosamente: Speech y Storage")
        
        # 9. Generar URL firmada para el blob
        blob_url_response = api_client.get(f"/api/v1/tokens/storage/blob/{upload_result['storage_info']['blob_name']}")
        assert blob_url_response.status_code == 200
        
        blob_url = blob_url_response.json()["blob_url"]
        assert blob_url.startswith("https://")
        
        print(f"✓ URL firmada generada para blob")
        
        # 10. Obtener estadísticas de chat
        stats_response = api_client.get(f"/api/v1/chat/stats?user_id={test_user_data['user_id']}")
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert stats["total_interactions"] > 0
        assert stats["unique_sessions"] > 0
        
        print(f"✓ Estadísticas obtenidas: {stats['total_interactions']} interacciones")
        
        # 11. Limpiar recursos
        # Eliminar sesión de chat
        delete_session_response = api_client.delete(f"/api/v1/chat/sessions/{session_id}?user_id={test_user_data['user_id']}")
        assert delete_session_response.status_code == 200
        assert delete_session_response.json()["deleted"] is True
        
        # Eliminar documento
        delete_doc_response = api_client.delete(f"/api/v1/documents/{document_id}")
        assert delete_doc_response.status_code == 200
        assert delete_doc_response.json()["success"] is True
        
        print(f"✓ Recursos limpiados exitosamente")
        
        # 12. Verificar limpieza
        final_list_response = api_client.get(f"/api/v1/documents/?user_id={test_user_data['user_id']}")
        assert final_list_response.status_code == 200
        assert len(final_list_response.json()) == 0
        
        print(f"✓ Verificación de limpieza exitosa")
        
        print("\n🎉 Recorrido completo del usuario completado exitosamente!")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_complete_user_journey_batch_upload(self, api_client, clean_database, sample_pdf_file, sample_medical_pdf_file, test_user_data, wait_for_processing):
        """
        Test del recorrido completo con batch upload:
        1. Subir múltiples documentos en lote
        2. Buscar por diferentes pacientes
        3. Crear múltiples sesiones de chat
        4. Obtener estadísticas consolidadas
        """
        
        # 1. Preparar archivos para batch upload
        files = []
        
        # Archivo 1: PDF médico
        with open(sample_medical_pdf_file["path"], "rb") as file1:
            files.append(("files", (sample_medical_pdf_file["filename"], file1.read(), "application/pdf")))
        
        # Archivo 2: PDF genérico
        with open(sample_pdf_file, "rb") as file2:
            files.append(("files", ("documento_generico.pdf", file2.read(), "application/pdf")))
        
        # Archivo 3: Otro PDF médico con diferente paciente
        medical_filename_2 = "4000567890_MARTINEZ PEREZ, JUAN_2024010100002_CONS.pdf"
        with open(sample_medical_pdf_file["path"], "rb") as file3:
            files.append(("files", (medical_filename_2, file3.read(), "application/pdf")))
        
        data = {
            "user_id": test_user_data["user_id"],
            "batch_description": "Lote de documentos para testing de integración",
            "batch_tags": json.dumps(["batch", "integration", "test"])
        }
        
        # 2. Subir lote
        batch_response = api_client.post("/api/v1/documents/upload/batch", files=files, data=data)
        assert batch_response.status_code == 201
        
        batch_result = batch_response.json()
        assert batch_result["total_files"] == 3
        assert batch_result["processed_count"] > 0
        
        batch_id = batch_result["batch_id"]
        successful_docs = batch_result["successful_documents"]
        
        print(f"✓ Lote subido exitosamente: {batch_result['processed_count']}/{batch_result['total_files']} documentos procesados")
        
        # 3. Esperar procesamiento de todos los documentos
        processed_documents = []
        for doc in successful_docs:
            processed_doc = wait_for_processing(api_client, doc["document_id"])
            processed_documents.append(processed_doc)
        
        completed_docs = [doc for doc in processed_documents if doc["processing_status"] == "completed"]
        
        print(f"✓ Documentos procesados: {len(completed_docs)} completados exitosamente")
        
        # 4. Listar documentos del lote
        batch_list_response = api_client.get(f"/api/v1/documents/?batch_id={batch_id}")
        assert batch_list_response.status_code == 200
        
        batch_documents = batch_list_response.json()
        assert len(batch_documents) > 0
        
        print(f"✓ Documentos del lote listados: {len(batch_documents)} documentos")
        
        # 5. Buscar por diferentes pacientes
        search_terms = [
            "GARCIA LOPEZ, MARIA",
            "MARTINEZ PEREZ, JUAN",
            "GARCIA"  # Búsqueda parcial
        ]
        
        search_results = []
        for term in search_terms:
            search_response = api_client.get(f"/api/v1/search/patients?search_term={term}")
            assert search_response.status_code == 200
            
            result = search_response.json()
            search_results.append(result)
        
        print(f"✓ Búsquedas completadas: {len(search_results)} términos buscados")
        
        # 6. Crear múltiples sesiones de chat
        sessions_created = []
        for doc in completed_docs[:2]:  # Crear sesiones para los primeros 2 documentos
            session_data = {
                "user_id": test_user_data["user_id"],
                "document_id": doc["document_id"],
                "session_name": f"Sesión para {doc.get('nombre_paciente', 'Documento')} - {doc['document_id'][:8]}"
            }
            
            session_response = api_client.post("/api/v1/chat/sessions", json=session_data)
            assert session_response.status_code == 201
            
            session_info = session_response.json()
            sessions_created.append(session_info)
        
        print(f"✓ Sesiones de chat creadas: {len(sessions_created)} sesiones")
        
        # 7. Hacer preguntas en diferentes sesiones
        questions = [
            "¿Cuál es el diagnóstico principal?",
            "¿Qué información médica relevante contiene este documento?",
            "¿Cuál es el estado del paciente?"
        ]
        
        interactions_created = 0
        for i, session in enumerate(sessions_created):
            question = questions[i % len(questions)]
            
            question_data = {
                "session_id": session["session_id"],
                "user_id": test_user_data["user_id"],
                "document_id": session["document_id"],
                "question": question
            }
            
            ask_response = api_client.post("/api/v1/chat/ask", json=question_data)
            assert ask_response.status_code == 200
            
            interactions_created += 1
        
        print(f"✓ Preguntas realizadas: {interactions_created} interacciones")
        
        # Esperar procesamiento de interacciones
        time.sleep(3)
        
        # 8. Obtener estadísticas consolidadas
        stats_response = api_client.get(f"/api/v1/chat/stats?user_id={test_user_data['user_id']}")
        assert stats_response.status_code == 200
        
        stats = stats_response.json()
        assert stats["total_interactions"] >= interactions_created
        assert stats["unique_sessions"] >= len(sessions_created)
        
        print(f"✓ Estadísticas consolidadas: {stats['total_interactions']} interacciones, {stats['unique_sessions']} sesiones")
        
        # 9. Limpiar recursos
        # Eliminar sesiones
        for session in sessions_created:
            delete_response = api_client.delete(f"/api/v1/chat/sessions/{session['session_id']}?user_id={test_user_data['user_id']}")
            assert delete_response.status_code == 200
        
        # Eliminar documentos
        for doc in completed_docs:
            delete_response = api_client.delete(f"/api/v1/documents/{doc['document_id']}")
            assert delete_response.status_code == 200
        
        print(f"✓ Recursos limpiados exitosamente")
        
        print("\n🎉 Recorrido completo con batch upload completado exitosamente!")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_multi_user_isolation_workflow(self, api_client, clean_database, sample_medical_pdf_file, test_user_data):
        """
        Test de aislamiento entre múltiples usuarios:
        1. Dos usuarios suben documentos
        2. Verificar aislamiento en listados
        3. Verificar aislamiento en búsquedas
        4. Verificar aislamiento en chat
        """
        
        user1_id = test_user_data["user_id"]
        user2_id = test_user_data["alternative_user_id"]
        
        # 1. Usuario 1 sube documento
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {"user_id": user1_id, "description": "Documento del usuario 1"}
            
            upload1_response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert upload1_response.status_code == 201
            
            doc1_id = upload1_response.json()["document_id"]
        
        # 2. Usuario 2 sube documento
        filename2 = "4000567890_MARTINEZ PEREZ, JUAN_2024010100002_CONS.pdf"
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (filename2, file, "application/pdf")}
            data = {"user_id": user2_id, "description": "Documento del usuario 2"}
            
            upload2_response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert upload2_response.status_code == 201
            
            doc2_id = upload2_response.json()["document_id"]
        
        print(f"✓ Documentos subidos por ambos usuarios")
        
        # 3. Verificar aislamiento en listados
        user1_docs = api_client.get(f"/api/v1/documents/?user_id={user1_id}").json()
        user2_docs = api_client.get(f"/api/v1/documents/?user_id={user2_id}").json()
        
        assert len(user1_docs) == 1
        assert len(user2_docs) == 1
        assert user1_docs[0]["document_id"] == doc1_id
        assert user2_docs[0]["document_id"] == doc2_id
        
        print(f"✓ Aislamiento en listados verificado")
        
        # 4. Verificar aislamiento en búsquedas
        search1 = api_client.get(f"/api/v1/search/patients?search_term=GARCIA&user_id={user1_id}").json()
        search2 = api_client.get(f"/api/v1/search/patients?search_term=GARCIA&user_id={user2_id}").json()
        
        assert search1["total_found"] > 0  # User1 debería encontrar su documento
        assert search2["total_found"] == 0  # User2 no debería encontrar nada
        
        print(f"✓ Aislamiento en búsquedas verificado")
        
        # 5. Crear sesiones para ambos usuarios
        session1_data = {
            "user_id": user1_id,
            "document_id": doc1_id,
            "session_name": "Sesión Usuario 1"
        }
        
        session2_data = {
            "user_id": user2_id,
            "document_id": doc2_id,
            "session_name": "Sesión Usuario 2"
        }
        
        session1_response = api_client.post("/api/v1/chat/sessions", json=session1_data)
        session2_response = api_client.post("/api/v1/chat/sessions", json=session2_data)
        
        assert session1_response.status_code == 201
        assert session2_response.status_code == 201
        
        session1_id = session1_response.json()["session_id"]
        session2_id = session2_response.json()["session_id"]
        
        print(f"✓ Sesiones creadas para ambos usuarios")
        
        # 6. Verificar aislamiento en sesiones
        user1_sessions = api_client.get(f"/api/v1/chat/sessions?user_id={user1_id}").json()
        user2_sessions = api_client.get(f"/api/v1/chat/sessions?user_id={user2_id}").json()
        
        assert len(user1_sessions["sessions"]) == 1
        assert len(user2_sessions["sessions"]) == 1
        assert user1_sessions["sessions"][0]["session_id"] == session1_id
        assert user2_sessions["sessions"][0]["session_id"] == session2_id
        
        print(f"✓ Aislamiento en sesiones verificado")
        
        # 7. Verificar que usuario no puede acceder a sesión de otro
        wrong_access_response = api_client.get(f"/api/v1/chat/sessions/{session1_id}?user_id={user2_id}")
        assert wrong_access_response.status_code == 400
        
        print(f"✓ Seguridad entre usuarios verificada")
        
        # 8. Limpiar recursos
        api_client.delete(f"/api/v1/chat/sessions/{session1_id}?user_id={user1_id}")
        api_client.delete(f"/api/v1/chat/sessions/{session2_id}?user_id={user2_id}")
        api_client.delete(f"/api/v1/documents/{doc1_id}")
        api_client.delete(f"/api/v1/documents/{doc2_id}")
        
        print(f"✓ Recursos limpiados exitosamente")
        
        print("\n🎉 Aislamiento multi-usuario verificado exitosamente!")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_error_recovery_workflow(self, api_client, clean_database, sample_pdf_file, test_user_data):
        """
        Test de recuperación de errores:
        1. Subir documento válido
        2. Intentar operaciones inválidas
        3. Verificar que el sistema se recupera correctamente
        """
        
        # 1. Subir documento válido
        with open(sample_pdf_file, "rb") as file:
            files = {"file": ("valid_document.pdf", file, "application/pdf")}
            data = {"user_id": test_user_data["user_id"]}
            
            upload_response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert upload_response.status_code == 201
            
            doc_id = upload_response.json()["document_id"]
        
        print(f"✓ Documento válido subido: {doc_id}")
        
        # 2. Intentar operaciones inválidas
        error_scenarios = []
        
        # Intentar acceder a documento inexistente
        response = api_client.get("/api/v1/documents/60f7b3b8e8f4c2a1b8d3e4f5")
        error_scenarios.append(("Document not found", response.status_code == 404))
        
        # Intentar crear sesión con documento inexistente
        response = api_client.post("/api/v1/chat/sessions", json={
            "user_id": test_user_data["user_id"],
            "document_id": "60f7b3b8e8f4c2a1b8d3e4f5"
        })
        error_scenarios.append(("Session with invalid doc", response.status_code == 400))
        
        # Intentar búsqueda con término vacío
        response = api_client.get("/api/v1/search/patients?search_term=")
        error_scenarios.append(("Empty search term", response.status_code == 422))
        
        # Intentar acceder a sesión inexistente
        response = api_client.get("/api/v1/chat/sessions/invalid-session?user_id=test")
        error_scenarios.append(("Invalid session access", response.status_code == 404))
        
        print(f"✓ Escenarios de error probados: {len(error_scenarios)} casos")
        
        # 3. Verificar que el sistema sigue funcionando normalmente
        # Listar documentos
        list_response = api_client.get(f"/api/v1/documents/?user_id={test_user_data['user_id']}")
        assert list_response.status_code == 200
        assert len(list_response.json()) == 1
        
        # Obtener información del documento
        info_response = api_client.get(f"/api/v1/documents/{doc_id}")
        assert info_response.status_code == 200
        
        # Crear sesión válida
        session_response = api_client.post("/api/v1/chat/sessions", json={
            "user_id": test_user_data["user_id"],
            "document_id": doc_id,
            "session_name": "Sesión post-errores"
        })
        assert session_response.status_code == 201
        
        session_id = session_response.json()["session_id"]
        
        # Verificar que los tokens siguen funcionando
        speech_response = api_client.get("/api/v1/tokens/speech")
        assert speech_response.status_code == 200
        
        storage_response = api_client.get("/api/v1/tokens/storage")
        assert storage_response.status_code == 200
        
        print(f"✓ Sistema funcionando normalmente después de errores")
        
        # 4. Limpiar
        api_client.delete(f"/api/v1/chat/sessions/{session_id}?user_id={test_user_data['user_id']}")
        api_client.delete(f"/api/v1/documents/{doc_id}")
        
        print(f"✓ Recursos limpiados exitosamente")
        
        # 5. Verificar que todos los errores se manejaron correctamente
        all_errors_handled = all(handled for _, handled in error_scenarios)
        assert all_errors_handled, f"Algunos errores no se manejaron correctamente: {error_scenarios}"
        
        print("\n🎉 Recuperación de errores verificada exitosamente!")

    @pytest.mark.slow
    @pytest.mark.integration
    def test_performance_workflow(self, api_client, clean_database, sample_medical_pdf_file, test_user_data):
        """
        Test de rendimiento básico:
        1. Medir tiempos de respuesta de endpoints críticos
        2. Verificar que no hay degradación significativa
        3. Validar cache de tokens
        """
        
        # 1. Medir tiempo de subida de documento
        start_time = time.time()
        
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {"user_id": test_user_data["user_id"]}
            
            upload_response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert upload_response.status_code == 201
            
            doc_id = upload_response.json()["document_id"]
        
        upload_time = time.time() - start_time
        
        print(f"✓ Tiempo de subida: {upload_time:.2f} segundos")
        
        # 2. Medir tiempo de listado
        start_time = time.time()
        
        for _ in range(5):
            list_response = api_client.get(f"/api/v1/documents/?user_id={test_user_data['user_id']}")
            assert list_response.status_code == 200
        
        list_time = (time.time() - start_time) / 5
        
        print(f"✓ Tiempo promedio de listado: {list_time:.3f} segundos")
        
        # 3. Medir tiempo de búsqueda
        start_time = time.time()
        
        for _ in range(5):
            search_response = api_client.get("/api/v1/search/patients?search_term=GARCIA")
            assert search_response.status_code == 200
        
        search_time = (time.time() - start_time) / 5
        
        print(f"✓ Tiempo promedio de búsqueda: {search_time:.3f} segundos")
        
        # 4. Medir tiempo de tokens (primera vez vs cache)
        start_time = time.time()
        
        speech_response1 = api_client.get("/api/v1/tokens/speech")
        assert speech_response1.status_code == 200
        
        first_token_time = time.time() - start_time
        
        start_time = time.time()
        
        speech_response2 = api_client.get("/api/v1/tokens/speech")
        assert speech_response2.status_code == 200
        
        cached_token_time = time.time() - start_time
        
        print(f"✓ Tiempo de token (primera vez): {first_token_time:.3f} segundos")
        print(f"✓ Tiempo de token (cache): {cached_token_time:.3f} segundos")
        
        # 5. Verificar que cache es significativamente más rápido
        assert cached_token_time < first_token_time / 2, "Cache no está funcionando eficientemente"
        
        # 6. Verificar límites de rendimiento razonables
        assert upload_time < 30, f"Subida muy lenta: {upload_time} segundos"
        assert list_time < 1, f"Listado muy lento: {list_time} segundos"
        assert search_time < 2, f"Búsqueda muy lenta: {search_time} segundos"
        assert first_token_time < 10, f"Generación de token muy lenta: {first_token_time} segundos"
        assert cached_token_time < 0.1, f"Cache de token muy lento: {cached_token_time} segundos"
        
        print(f"✓ Todos los límites de rendimiento cumplidos")
        
        # 7. Limpiar
        api_client.delete(f"/api/v1/documents/{doc_id}")
        
        print("\n🎉 Validación de rendimiento completada exitosamente!")


class TestSystemResilience:
    """Tests de resistencia del sistema."""

    @pytest.mark.integration
    def test_system_health_monitoring(self, api_client, server_health_check):
        """Test de monitoreo de salud del sistema."""
        
        # Verificar endpoints de salud
        health_response = api_client.get("/health")
        assert health_response.status_code == 200
        
        root_response = api_client.get("/")
        assert root_response.status_code == 200
        
        # Verificar información básica
        health_data = health_response.json()
        root_data = root_response.json()
        
        assert health_data["status"] == "healthy"
        assert root_data["status"] == "healthy"
        
        print("✓ Sistema reportando estado saludable")
        
        # Verificar que endpoints principales responden
        endpoints_to_check = [
            "/api/v1/documents/",
            "/api/v1/tokens/speech",
            "/api/v1/tokens/storage",
            "/api/v1/search/patients/suggestions?partial_term=test"
        ]
        
        for endpoint in endpoints_to_check:
            response = api_client.get(endpoint)
            assert response.status_code in [200, 422], f"Endpoint {endpoint} no responde correctamente"
        
        print(f"✓ Endpoints principales respondiendo: {len(endpoints_to_check)} verificados")

    @pytest.mark.integration
    def test_concurrent_operations(self, api_client, clean_database, sample_pdf_file, test_user_data):
        """Test de operaciones concurrentes."""
        
        # Simular múltiples operaciones simultáneas
        import threading
        import queue
        
        results = queue.Queue()
        
        def upload_document(thread_id):
            try:
                with open(sample_pdf_file, "rb") as file:
                    files = {"file": (f"concurrent_doc_{thread_id}.pdf", file, "application/pdf")}
                    data = {"user_id": f"{test_user_data['user_id']}_{thread_id}"}
                    
                    response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                    results.put(("upload", thread_id, response.status_code))
            except Exception as e:
                results.put(("upload", thread_id, f"Error: {e}"))
        
        def get_tokens(thread_id):
            try:
                speech_response = api_client.get("/api/v1/tokens/speech")
                storage_response = api_client.get("/api/v1/tokens/storage")
                results.put(("tokens", thread_id, speech_response.status_code, storage_response.status_code))
            except Exception as e:
                results.put(("tokens", thread_id, f"Error: {e}"))
        
        # Crear y lanzar threads
        threads = []
        
        # 3 threads para upload
        for i in range(3):
            thread = threading.Thread(target=upload_document, args=(i,))
            threads.append(thread)
            thread.start()
        
        # 2 threads para tokens
        for i in range(2):
            thread = threading.Thread(target=get_tokens, args=(i,))
            threads.append(thread)
            thread.start()
        
        # Esperar a que terminen todos
        for thread in threads:
            thread.join()
        
        # Verificar resultados
        upload_success = 0
        token_success = 0
        
        while not results.empty():
            result = results.get()
            
            if result[0] == "upload":
                if result[2] == 201:
                    upload_success += 1
                else:
                    print(f"Upload thread {result[1]} failed: {result[2]}")
            
            elif result[0] == "tokens":
                if len(result) == 4 and result[2] == 200 and result[3] == 200:
                    token_success += 1
                else:
                    print(f"Token thread {result[1]} failed: {result[2:]}")
        
        assert upload_success >= 2, f"Solo {upload_success}/3 uploads exitosos"
        assert token_success >= 1, f"Solo {token_success}/2 token requests exitosos"
        
        print(f"✓ Operaciones concurrentes: {upload_success} uploads, {token_success} tokens exitosos")

    @pytest.mark.integration
    def test_data_consistency(self, api_client, clean_database, sample_medical_pdf_file, test_user_data, wait_for_processing):
        """Test de consistencia de datos."""
        
        # Subir documento
        with open(sample_medical_pdf_file["path"], "rb") as file:
            files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
            data = {"user_id": test_user_data["user_id"]}
            
            upload_response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            assert upload_response.status_code == 201
            
            doc_id = upload_response.json()["document_id"]
        
        # Esperar procesamiento
        processed_doc = wait_for_processing(api_client, doc_id)
        
        # Verificar consistencia entre diferentes endpoints
        # 1. Información del documento
        doc_info = api_client.get(f"/api/v1/documents/{doc_id}").json()
        
        # 2. Documento en lista
        doc_list = api_client.get(f"/api/v1/documents/?user_id={test_user_data['user_id']}").json()
        doc_in_list = next((d for d in doc_list if d["document_id"] == doc_id), None)
        
        # 3. Documento en búsqueda
        patient_name = sample_medical_pdf_file["nombre_paciente"]
        search_results = api_client.get(f"/api/v1/search/patients?search_term={patient_name}").json()
        doc_in_search = next((d for d in search_results["documents"] if d["document_id"] == doc_id), None)
        
        # Verificar consistencia de datos críticos
        assert doc_info["document_id"] == doc_in_list["document_id"] == doc_in_search["document_id"]
        assert doc_info["filename"] == doc_in_list["filename"] == doc_in_search["filename"]
        assert doc_info["user_id"] == doc_in_list["user_id"] == doc_in_search["user_id"]
        assert doc_info["nombre_paciente"] == doc_in_search["nombre_paciente"]
        
        print("✓ Consistencia de datos verificada entre todos los endpoints")
        
        # Limpiar
        api_client.delete(f"/api/v1/documents/{doc_id}")
        
        print("\n🎉 Resistencia del sistema verificada exitosamente!") 