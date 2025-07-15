"""
Tests para la API de estadísticas de la plataforma TecSalud MVP.
Incluye tests robustos con setup/teardown de datos y validación de múltiples escenarios.
"""

import pytest
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List
from pymongo.database import Database


class TestStatisticsAPI:
    """Tests para la API de estadísticas de la plataforma."""

    @pytest.fixture
    def setup_test_data(self, clean_database):
        """
        Setup de datos de prueba para tests que lo necesiten.
        Carga datos realistas en las 4 colecciones principales.
        """
        self.db = clean_database
        
        # Fechas base para los datos de prueba
        now = datetime.utcnow()
        week_ago = now - timedelta(days=7)
        month_ago = now - timedelta(days=30)
        
        # 1. Datos de documentos (estructura real de MongoDB)
        self.test_documents = [
            {
                "processing_id": "proc_001",
                "filename": "emergency_report_001.pdf",
                "content_type": "application/pdf",
                "file_size": 1048576,  # Exactamente 1MB
                "user_id": "user_001",
                "storage_info": {
                    "blob_name": "emergency_report_001.pdf",
                    "blob_url": "https://storage.blob.core.windows.net/documents/emergency_report_001.pdf",
                    "container_name": "documents"
                },
                "extracted_text": "Reporte de emergencia - Paciente con síntomas cardíacos",
                "processing_status": "completed",
                "description": "Reporte de emergencia cardiovascular",
                "tags": ["emergencia", "cardiologia"],
                "expediente": "4000123456",
                "nombre_paciente": "GARCIA LOPEZ, MARIA",
                "numero_episodio": "2024010100001",
                "categoria": "EMER",
                "medical_info_valid": True,
                "medical_info_error": None,
                "created_at": now - timedelta(days=1),
                "updated_at": now - timedelta(days=1)
            },
            {
                "processing_id": "proc_002",
                "filename": "consultation_002.pdf",
                "content_type": "application/pdf", 
                "file_size": 524288,  # Exactamente 512KB
                "user_id": "user_001",
                "storage_info": {
                    "blob_name": "consultation_002.pdf",
                    "blob_url": "https://storage.blob.core.windows.net/documents/consultation_002.pdf",
                    "container_name": "documents"
                },
                "extracted_text": "Consulta neurológica - Evaluación de síntomas",
                "processing_status": "completed",
                "description": "Consulta neurológica de rutina",
                "tags": ["consulta", "neurologia"],
                "expediente": "4000234567",
                "nombre_paciente": "LOPEZ MARTINEZ, JUAN",
                "numero_episodio": "2024010100002",
                "categoria": "CONSUL",
                "medical_info_valid": True,
                "medical_info_error": None,
                "created_at": now - timedelta(days=8),  # Cambiado para estar claramente fuera del rango de 7 días
                "updated_at": now - timedelta(days=8)
            },
            {
                "processing_id": "proc_003",
                "filename": "lab_results_003.pdf",
                "content_type": "application/pdf",
                "file_size": 262144,  # Exactamente 256KB
                "user_id": "user_002",
                "storage_info": {
                    "blob_name": "lab_results_003.pdf", 
                    "blob_url": "https://storage.blob.core.windows.net/documents/lab_results_003.pdf",
                    "container_name": "documents"
                },
                "extracted_text": "Resultados de laboratorio - Análisis de sangre completo",
                "processing_status": "completed",
                "description": "Análisis de laboratorio completo",
                "tags": ["laboratorio", "sangre"],
                "expediente": "4000345678",
                "nombre_paciente": "RODRIGUEZ PEREZ, ANA",
                "numero_episodio": "2024010100003",
                "categoria": "LAB",
                "medical_info_valid": True,
                "medical_info_error": None,
                "created_at": month_ago,
                "updated_at": month_ago
            },
            {
                "processing_id": "proc_004",
                "filename": "trauma_report_004.pdf",
                "content_type": "application/pdf",
                "file_size": 2097152,  # Exactamente 2MB
                "user_id": "user_002",
                "storage_info": {
                    "blob_name": "trauma_report_004.pdf",
                    "blob_url": "https://storage.blob.core.windows.net/documents/trauma_report_004.pdf",
                    "container_name": "documents"
                },
                "extracted_text": "Reporte de trauma - Paciente con lesiones múltiples",
                "processing_status": "completed", 
                "description": "Reporte de trauma de urgencias",
                "tags": ["emergencia", "trauma"],
                "expediente": "4000456789",
                "nombre_paciente": "HERNANDEZ SILVA, CARLOS",
                "numero_episodio": "2024010100004",
                "categoria": "EMER",
                "medical_info_valid": True,
                "medical_info_error": None,
                "created_at": now - timedelta(hours=2),
                "updated_at": now - timedelta(hours=2)
            }
        ]
        
        # Insertar documentos y obtener los ObjectIds reales
        result = self.db["documents"].insert_many(self.test_documents)
        document_ids = result.inserted_ids
        
        # 2. Datos de sesiones de chat (estructura real de MongoDB)
        self.test_chat_sessions = [
            {
                "session_id": "session_001",
                "user_id": "user_001",
                "document_id": str(document_ids[0]),  # Usar ObjectId real del primer documento
                "session_name": "Chat con reporte de emergencia",
                "is_active": True,
                "created_at": now - timedelta(hours=3),
                "last_interaction_at": now - timedelta(hours=1),
                "interaction_count": 5,
                "metadata": {
                    "created_by": "user_001",
                    "last_updated_by": "user_001"
                }
            },
            {
                "session_id": "session_002",
                "user_id": "user_001", 
                "document_id": str(document_ids[1]),  # Usar ObjectId real del segundo documento
                "session_name": "Chat con consulta neurológica",
                "is_active": False,
                "created_at": now - timedelta(days=8, hours=1),  # Ajustado para coincidir con el documento
                "last_interaction_at": now - timedelta(days=8, hours=1),
                "interaction_count": 3,
                "metadata": {
                    "created_by": "user_001",
                    "last_updated_by": "user_001"
                }
            },
            {
                "session_id": "session_003",
                "user_id": "user_002",
                "document_id": str(document_ids[2]),  # Usar ObjectId real del tercer documento
                "session_name": "Chat con resultados de laboratorio",
                "is_active": False,
                "created_at": month_ago + timedelta(days=1),
                "last_interaction_at": month_ago + timedelta(days=1, hours=1),
                "interaction_count": 8,
                "metadata": {
                    "created_by": "user_002",
                    "last_updated_by": "user_002"
                }
            },
            {
                "session_id": "session_004",
                "user_id": "user_002",
                "document_id": str(document_ids[3]),  # Usar ObjectId real del cuarto documento
                "session_name": "Chat con reporte de trauma",
                "is_active": True,
                "created_at": now - timedelta(minutes=30),
                "last_interaction_at": now - timedelta(minutes=10),
                "interaction_count": 2,
                "metadata": {
                    "created_by": "user_002",
                    "last_updated_by": "user_002"
                }
            }
        ]
        
        # 3. Datos de interacciones de chat (estructura real de MongoDB)
        self.test_chat_interactions = [
            # Interacciones para session_001
            {
                "interaction_id": "int_001",
                "session_id": "session_001",
                "user_id": "user_001",
                "document_id": str(document_ids[0]),
                "question": "¿Cuál es el diagnóstico principal?",
                "response": "Según el documento, el diagnóstico es...",
                "created_at": now - timedelta(hours=3),
                "metadata": {
                    "question_length": 33,
                    "response_length": 45,
                    "created_by": "user_001"
                }
            },
            {
                "interaction_id": "int_002", 
                "session_id": "session_001",
                "user_id": "user_001",
                "document_id": str(document_ids[0]),
                "question": "¿Qué tratamiento se recomienda?",
                "response": "El tratamiento recomendado incluye...",
                "created_at": now - timedelta(hours=2, minutes=30),
                "metadata": {
                    "question_length": 35,
                    "response_length": 39,
                    "created_by": "user_001"
                }
            },
            # Interacciones para session_002
            {
                "interaction_id": "int_003",
                "session_id": "session_002",
                "user_id": "user_001", 
                "document_id": str(document_ids[1]),
                "question": "¿Hay complicaciones?",
                "response": "No se observan complicaciones...",
                "created_at": now - timedelta(days=8, hours=1, minutes=15),
                "metadata": {
                    "question_length": 21,
                    "response_length": 31,
                    "created_by": "user_001"
                }
            },
            # Interacciones para session_003
            {
                "interaction_id": "int_004",
                "session_id": "session_003",
                "user_id": "user_002",
                "document_id": str(document_ids[2]),
                "question": "¿Los resultados están normales?",
                "response": "Los valores de laboratorio muestran...",
                "created_at": month_ago + timedelta(days=1, minutes=5),
                "metadata": {
                    "question_length": 32,
                    "response_length": 37,
                    "created_by": "user_002"
                }
            },
            # Interacciones para session_004
            {
                "interaction_id": "int_005",
                "session_id": "session_004", 
                "user_id": "user_002",
                "document_id": str(document_ids[3]),
                "question": "¿Es grave la lesión?",
                "response": "La evaluación inicial indica...",
                "created_at": now - timedelta(minutes=25),
                "metadata": {
                    "question_length": 20,
                    "response_length": 33,
                    "created_by": "user_002"
                }
            }
        ]
        
        # 4. Datos de pills (estructura real de MongoDB)
        self.test_pills = [
            {
                "pill_id": "pill_001",
                "starter": "Consulta General",
                "text": "¿Podrías ayudarme con una consulta general?",
                "icon": "🩺",
                "category": "medico",
                "priority": 1,
                "is_active": True,
                "created_at": month_ago,
                "updated_at": month_ago
            },
            {
                "pill_id": "pill_002",
                "starter": "Análisis de Laboratorio", 
                "text": "¿Puedes analizar estos resultados de laboratorio?",
                "icon": "🧪",
                "category": "laboratorio",
                "priority": 2,
                "is_active": True,
                "created_at": week_ago,
                "updated_at": week_ago
            },
            {
                "pill_id": "pill_003",
                "starter": "Revisión de Emergencia",
                "text": "¿Qué indica este reporte de emergencia?",
                "icon": "🚨", 
                "category": "emergencia",
                "priority": 3,
                "is_active": False,  # Pill inactiva
                "created_at": month_ago - timedelta(days=5),
                "updated_at": week_ago
            }
        ]
        
        # Insertar datos restantes en MongoDB
        self.db["chat_sessions"].insert_many(self.test_chat_sessions)
        self.db["chat_interactions"].insert_many(self.test_chat_interactions)
        self.db["pills"].insert_many(self.test_pills)
        
        # Guardar fechas útiles para tests
        self.now = now
        self.week_ago = week_ago
        self.month_ago = month_ago

    def test_platform_overview_no_filters(self, api_client, setup_test_data):
        """Test del overview de plataforma sin filtros de fecha (todo el tiempo)."""
        response = api_client.get("/api/v1/statistics/platform/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validar estructura de respuesta
        assert "totals" in data
        assert "storage" in data  
        assert "period" in data
        
        # Validar totales (todos los datos cargados)
        totals = data["totals"]
        assert totals["documents"] == 4
        assert totals["sessions"] == 4
        assert totals["interactions"] == 5
        assert totals["active_pills"] == 2  # Solo 2 pills activas
        assert totals["unique_users"] == 2
        
        # Validar storage (usar cálculo aproximado)
        storage = data["storage"]
        assert storage["document_count"] == 4
        # Total: 1MB + 512KB + 256KB + 2MB = 3.75MB, pero usar tolerancia por redondeo
        expected_total_mb = (1048576 + 524288 + 262144 + 2097152) / (1024 * 1024)
        assert abs(storage["total_size_mb"] - expected_total_mb) < 0.1
        assert storage["avg_size_mb"] > 0
        assert storage["max_size_mb"] == 2097152 / (1024 * 1024)  # 2MB
        
        # Validar period (sin filtros)
        period = data["period"]
        assert period["filtered"] == False
        assert period["start_date"] is None
        assert period["end_date"] is None

    def test_platform_overview_with_date_filters(self, api_client, setup_test_data):
        """Test del overview con filtros de fecha específicos."""
        # Filtrar solo los últimos 7 días
        start_date = (self.now - timedelta(days=7)).strftime("%Y-%m-%d")
        end_date = self.now.strftime("%Y-%m-%d")
        
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Validar que solo incluye datos de los últimos 7 días
        totals = data["totals"]
        # Solo doc_001 (1 día atrás) y doc_004 (2 horas atrás) están en los últimos 7 días
        assert totals["documents"] == 2  
        assert totals["sessions"] == 2   # session_001 y session_004
        assert totals["interactions"] == 3  # 2 de session_001 + 1 de session_004
        
        # Validar period con filtros
        period = data["period"]
        assert period["filtered"] == True
        assert start_date in period["start_date"]
        assert end_date in period["end_date"]

    def test_platform_overview_with_datetime_filters(self, api_client, setup_test_data):
        """Test del overview con filtros de fecha y hora completos."""
        # Filtrar las últimas 24 horas usando formato datetime completo
        start_datetime = (self.now - timedelta(days=1)).strftime("%Y-%m-%dT%H:%M:%S")
        end_datetime = self.now.strftime("%Y-%m-%dT%H:%M:%S") 
        
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={start_datetime}&end_date={end_datetime}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Solo deberían incluirse doc_001 y doc_004 (últimas 24h)
        totals = data["totals"]
        assert totals["documents"] == 2
        assert totals["unique_users"] == 2  # user_001 y user_002

    def test_platform_overview_empty_date_range(self, api_client, setup_test_data):
        """Test con rango de fechas que no contiene datos."""
        # Fechas del futuro
        start_date = (self.now + timedelta(days=1)).strftime("%Y-%m-%d")
        end_date = (self.now + timedelta(days=2)).strftime("%Y-%m-%d")
        
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Todos los totales deberían ser 0
        totals = data["totals"]
        assert totals["documents"] == 0
        assert totals["sessions"] == 0
        assert totals["interactions"] == 0
        assert totals["unique_users"] == 0
        # Pills activas no dependen de fechas
        assert totals["active_pills"] == 2
        
        # Storage debería estar vacío
        storage = data["storage"]
        assert storage["document_count"] == 0
        assert storage["total_size_mb"] == 0
        assert storage["avg_size_mb"] == 0
        assert storage["max_size_mb"] == 0

    def test_platform_overview_invalid_date_format(self, api_client):
        """Test con formato de fecha inválido."""
        response = api_client.get(
            "/api/v1/statistics/platform/overview?start_date=invalid-date"
        )
        
        assert response.status_code == 400  # El API devuelve 400, no 422
        error_data = response.json()
        # El formato real usa 'error_message' en lugar de 'detail'
        assert "error_message" in error_data
        assert "Invalid start_date format" in error_data["error_message"]

    def test_platform_overview_invalid_date_range(self, api_client):
        """Test con rango de fechas inválido (start_date > end_date)."""
        start_date = self.now.strftime("%Y-%m-%d") if hasattr(self, 'now') else "2025-07-15"
        end_date = (self.now - timedelta(days=1)).strftime("%Y-%m-%d") if hasattr(self, 'now') else "2025-07-14"
        
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={start_date}&end_date={end_date}"
        )
        
        assert response.status_code == 400
        error_data = response.json()
        # El formato real usa 'error_message' en lugar de 'detail'
        assert "error_message" in error_data
        assert "start_date must be before or equal to end_date" in error_data["error_message"]

    def test_platform_overview_only_start_date(self, api_client, setup_test_data):
        """Test con solo start_date (sin end_date)."""
        start_date = (self.now - timedelta(days=7)).strftime("%Y-%m-%d")
        
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={start_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Debería incluir desde start_date hasta ahora
        period = data["period"]
        assert period["filtered"] == True
        assert start_date in period["start_date"]

    def test_platform_overview_only_end_date(self, api_client, setup_test_data):
        """Test con solo end_date (sin start_date)."""
        end_date = (self.now - timedelta(days=1)).strftime("%Y-%m-%d")
        
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?end_date={end_date}"
        )
        
        assert response.status_code == 200
        data = response.json()
        
        # Debería incluir desde el inicio hasta end_date
        period = data["period"]
        assert period["filtered"] == True
        assert end_date in period["end_date"]

    def test_platform_overview_response_structure(self, api_client, setup_test_data):
        """Test detallado de la estructura de respuesta."""
        response = api_client.get("/api/v1/statistics/platform/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # Validar estructura completa y tipos de datos
        assert isinstance(data, dict)
        
        # Sección totals
        totals = data["totals"]
        assert isinstance(totals["documents"], int)
        assert isinstance(totals["sessions"], int) 
        assert isinstance(totals["interactions"], int)
        assert isinstance(totals["active_pills"], int)
        assert isinstance(totals["unique_users"], int)
        assert all(v >= 0 for v in totals.values())  # No valores negativos
        
        # Sección storage (manejar valores None)
        storage = data["storage"]
        assert isinstance(storage["document_count"], int)
        assert isinstance(storage["total_size_mb"], (int, float))
        assert isinstance(storage["avg_size_mb"], (int, float))
        assert isinstance(storage["max_size_mb"], (int, float))
        # Verificar que no hay valores negativos, manejando None
        for key, value in storage.items():
            if value is not None:
                assert value >= 0, f"Storage field {key} should not be negative: {value}"
        
        # Sección period
        period = data["period"]
        assert isinstance(period["filtered"], bool)
        # start_date y end_date pueden ser None o string
        if period["start_date"] is not None:
            assert isinstance(period["start_date"], str)
        if period["end_date"] is not None:
            assert isinstance(period["end_date"], str)

    def test_platform_overview_with_empty_database(self, clean_database, api_client):
        """Test con base de datos completamente vacía (sin setup de datos)."""
        # Este test NO usa setup_test_data, por lo que no se cargan datos automáticamente
        
        response = api_client.get("/api/v1/statistics/platform/overview")
        
        assert response.status_code == 200
        data = response.json()
        
        # Todos los valores deberían ser 0
        totals = data["totals"]
        assert totals["documents"] == 0
        assert totals["sessions"] == 0
        assert totals["interactions"] == 0
        assert totals["active_pills"] == 0
        assert totals["unique_users"] == 0
        
        storage = data["storage"]
        assert storage["document_count"] == 0
        assert storage["total_size_mb"] == 0
        assert storage["avg_size_mb"] == 0
        assert storage["max_size_mb"] == 0

    def test_platform_overview_performance_with_large_dataset(self, clean_database, api_client):
        """Test de rendimiento con dataset más grande."""
        # Este test tampoco usa setup_test_data, maneja sus propios datos
        
        # Generar datos más grandes para probar performance
        large_documents = []
        large_sessions = []
        large_interactions = []
        
        base_time = datetime.utcnow() - timedelta(days=30)
        
        # Crear 50 documentos, 75 sesiones, 200 interacciones (reducido para velocidad)
        for i in range(50):
            doc = {
                "processing_id": f"large_proc_{i:03d}",
                "filename": f"document_{i:03d}.pdf",
                "content_type": "application/pdf",
                "file_size": 500000 + (i * 1000),  # Tamaños variables
                "user_id": f"large_user_{i % 10:02d}",  # 10 usuarios diferentes
                "storage_info": {
                    "blob_name": f"document_{i:03d}.pdf",
                    "blob_url": f"https://storage.blob.core.windows.net/documents/document_{i:03d}.pdf",
                    "container_name": "documents"
                },
                "extracted_text": f"Contenido del documento {i}",
                "processing_status": "completed",
                "description": f"Documento de prueba {i}",
                "tags": [f"tag_{i % 5}", f"category_{i % 3}"],
                "expediente": f"4000{i:06d}",
                "nombre_paciente": f"PACIENTE_{i:03d}, NOMBRE",
                "numero_episodio": f"202401{i:07d}",
                "categoria": ["EMER", "CONSUL", "LAB"][i % 3],
                "medical_info_valid": True,
                "medical_info_error": None,
                "created_at": base_time + timedelta(hours=i),
                "updated_at": base_time + timedelta(hours=i)
            }
            large_documents.append(doc)
        
        # Insertar documentos y obtener IDs
        doc_result = clean_database["documents"].insert_many(large_documents)
        doc_ids = [str(id) for id in doc_result.inserted_ids]
        
        # Crear sesiones e interacciones
        for i in range(min(50, len(doc_ids))):
            session_time = base_time + timedelta(hours=i, minutes=30)
            session = {
                "session_id": f"large_session_{i:03d}",
                "user_id": f"large_user_{i % 10:02d}",
                "document_id": doc_ids[i],
                "session_name": f"Chat con documento {i}",
                "is_active": i % 10 == 0,  # 10% sesiones activas
                "created_at": session_time,
                "last_interaction_at": session_time + timedelta(minutes=15),
                "interaction_count": 2 + (i % 3),
                "metadata": {
                    "created_by": f"large_user_{i % 10:02d}",
                    "last_updated_by": f"large_user_{i % 10:02d}"
                }
            }
            large_sessions.append(session)
            
            # 2-4 interacciones por sesión
            for j in range(2 + (i % 3)):
                interaction = {
                    "interaction_id": f"large_int_{i:03d}_{j}",
                    "session_id": f"large_session_{i:03d}",
                    "user_id": f"large_user_{i % 10:02d}",
                    "document_id": doc_ids[i],
                    "question": f"Pregunta {j+1} sobre documento {i}",
                    "response": f"Respuesta {j+1} para documento {i}",
                    "created_at": session_time + timedelta(minutes=j*2),
                    "metadata": {
                        "question_length": len(f"Pregunta {j+1} sobre documento {i}"),
                        "response_length": len(f"Respuesta {j+1} para documento {i}"),
                        "created_by": f"large_user_{i % 10:02d}"
                    }
                }
                large_interactions.append(interaction)
        
        # Insertar datos grandes
        clean_database["chat_sessions"].insert_many(large_sessions)
        clean_database["chat_interactions"].insert_many(large_interactions)
        
        # Hacer request y medir si responde en tiempo razonable
        import time
        start_time = time.time()
        
        response = api_client.get("/api/v1/statistics/platform/overview")
        
        end_time = time.time()
        response_time = end_time - start_time
        
        # Validaciones
        assert response.status_code == 200
        assert response_time < 5.0  # Debería responder en menos de 5 segundos
        
        data = response.json()
        assert data["totals"]["documents"] == 50
        assert data["totals"]["unique_users"] == 10
        assert data["storage"]["document_count"] == 50

    def test_platform_overview_date_filter_edge_cases(self, api_client, setup_test_data):
        """Test de casos edge con filtros de fecha."""
        # Test 1: Fecha de inicio igual a fecha de fin
        same_date = self.now.strftime("%Y-%m-%d")
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={same_date}&end_date={same_date}"
        )
        assert response.status_code == 200
        
        # Test 2: Filtros con microsegundos 
        start_precise = (self.now - timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%S.%f")
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={start_precise}"
        )
        assert response.status_code == 200
        
        # Test 3: Fechas muy antiguas
        old_date = "2020-01-01"
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?start_date={old_date}"
        )
        assert response.status_code == 200
        
        # Test 4: Fechas del futuro lejano
        future_date = "2030-12-31"
        response = api_client.get(
            f"/api/v1/statistics/platform/overview?end_date={future_date}"
        )
        assert response.status_code == 200

    def test_platform_overview_concurrent_requests(self, api_client, setup_test_data):
        """Test de requests concurrentes para verificar thread safety."""
        import threading
        import queue
        
        results = queue.Queue()
        
        def make_request():
            try:
                response = api_client.get("/api/v1/statistics/platform/overview")
                results.put(("success", response.status_code, response.json()))
            except Exception as e:
                results.put(("error", str(e), None))
        
        # Lanzar 5 requests concurrentes
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=make_request)
            threads.append(thread)
            thread.start()
        
        # Esperar a que terminen todos
        for thread in threads:
            thread.join()
        
        # Validar resultados
        success_count = 0
        while not results.empty():
            status, code, data = results.get()
            if status == "success":
                assert code == 200
                assert "totals" in data
                success_count += 1
        
        assert success_count == 5  # Todos los requests exitosos 