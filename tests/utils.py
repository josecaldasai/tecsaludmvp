"""
Utilidades auxiliares para los tests de TecSalud MVP.
"""

import json
import time
import tempfile
import os
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import httpx


class TestDataGenerator:
    """Generador de datos de prueba para tests."""
    
    @staticmethod
    def create_medical_filename(
        expediente: str = "4000123456",
        nombre_paciente: str = "GARCIA LOPEZ, MARIA",
        numero_episodio: str = "2024010100001",
        categoria: str = "EMER"
    ) -> str:
        """Crear nombre de archivo médico válido."""
        return f"{expediente}_{nombre_paciente}_{numero_episodio}_{categoria}.pdf"
    
    @staticmethod
    def create_test_users(count: int = 2) -> List[Dict[str, Any]]:
        """Crear datos de usuarios de prueba."""
        users = []
        for i in range(count):
            users.append({
                "user_id": f"test_user_{i+1:03d}",
                "description": f"Usuario de prueba {i+1}",
                "tags": ["test", "automation", f"user_{i+1}"]
            })
        return users
    
    @staticmethod
    def create_test_patients(count: int = 5) -> List[Dict[str, str]]:
        """Crear datos de pacientes de prueba."""
        patients = [
            {
                "expediente": "4000123456",
                "nombre_paciente": "GARCIA LOPEZ, MARIA",
                "numero_episodio": "2024010100001",
                "categoria": "EMER"
            },
            {
                "expediente": "4000234567",
                "nombre_paciente": "MARTINEZ PEREZ, JUAN",
                "numero_episodio": "2024010200001",
                "categoria": "CONS"
            },
            {
                "expediente": "4000345678",
                "nombre_paciente": "RODRIGUEZ SANCHEZ, ANA",
                "numero_episodio": "2024010300001",
                "categoria": "EMER"
            },
            {
                "expediente": "4000456789",
                "nombre_paciente": "LOPEZ HERNANDEZ, CARLOS",
                "numero_episodio": "2024010400001",
                "categoria": "CONS"
            },
            {
                "expediente": "4000567890",
                "nombre_paciente": "FERNANDEZ GOMEZ, LUCIA",
                "numero_episodio": "2024010500001",
                "categoria": "EMER"
            }
        ]
        return patients[:count]


class TestFileManager:
    """Gestor de archivos temporales para tests."""
    
    @staticmethod
    def create_temp_pdf(content: str = "Test PDF Document", filename: str = "test.pdf") -> str:
        """Crear archivo PDF temporal."""
        pdf_content = f"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length {len(content) + 20}
>>
stream
BT
/F1 12 Tf
100 700 Td
({content}) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000190 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
{285 + len(content)}
%%EOF""".encode()
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(pdf_content)
            return temp_file.name
    
    @staticmethod
    def create_temp_medical_pdf(patient_data: Dict[str, str]) -> str:
        """Crear archivo PDF médico temporal."""
        medical_content = f"""Expediente Medico
Paciente: {patient_data['nombre_paciente']}
Episodio: {patient_data['numero_episodio']}
Categoria: {patient_data['categoria']}
Expediente: {patient_data['expediente']}"""
        
        return TestFileManager.create_temp_pdf(medical_content)
    
    @staticmethod
    def cleanup_temp_files(file_paths: List[str]):
        """Limpiar archivos temporales."""
        for file_path in file_paths:
            try:
                os.unlink(file_path)
            except FileNotFoundError:
                pass


class TestAPIHelper:
    """Helper para operaciones comunes de API."""
    
    @staticmethod
    def wait_for_document_processing(
        api_client: httpx.Client,
        document_id: str,
        max_wait: int = 30,
        poll_interval: int = 1
    ) -> Dict[str, Any]:
        """Esperar a que se complete el procesamiento de un documento."""
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = api_client.get(f"/api/v1/documents/{document_id}")
            
            if response.status_code == 200:
                doc_info = response.json()
                if doc_info.get("processing_status") in ["completed", "failed"]:
                    return doc_info
            
            time.sleep(poll_interval)
        
        raise TimeoutError(f"Document processing did not complete within {max_wait} seconds")
    
    @staticmethod
    def upload_document(
        api_client: httpx.Client,
        file_path: str,
        filename: str,
        user_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None
    ) -> Dict[str, Any]:
        """Subir documento y retornar resultado."""
        with open(file_path, "rb") as file:
            files = {"file": (filename, file, "application/pdf")}
            data = {"user_id": user_id}
            
            if description:
                data["description"] = description
            
            if tags:
                data["tags"] = json.dumps(tags)
            
            response = api_client.post("/api/v1/documents/upload", files=files, data=data)
            
            if response.status_code != 201:
                raise Exception(f"Upload failed: {response.status_code} - {response.text}")
            
            return response.json()
    
    @staticmethod
    def upload_document_and_wait(
        api_client: httpx.Client,
        file_path: str,
        filename: str,
        user_id: str,
        description: Optional[str] = None,
        tags: Optional[List[str]] = None,
        max_wait: int = 30
    ) -> Dict[str, Any]:
        """Subir documento y esperar a que se procese."""
        upload_result = TestAPIHelper.upload_document(
            api_client, file_path, filename, user_id, description, tags
        )
        
        processed_doc = TestAPIHelper.wait_for_document_processing(
            api_client, upload_result["document_id"], max_wait
        )
        
        return {
            "upload_result": upload_result,
            "processed_doc": processed_doc,
            "document_id": upload_result["document_id"]
        }
    
    @staticmethod
    def create_chat_session(
        api_client: httpx.Client,
        user_id: str,
        document_id: str,
        session_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """Crear sesión de chat."""
        session_data = {
            "user_id": user_id,
            "document_id": document_id
        }
        
        if session_name:
            session_data["session_name"] = session_name
        
        response = api_client.post("/api/v1/chat/sessions", json=session_data)
        
        if response.status_code != 201:
            raise Exception(f"Session creation failed: {response.status_code} - {response.text}")
        
        return response.json()
    
    @staticmethod
    def ask_question_streaming(
        api_client: httpx.Client,
        session_id: str,
        user_id: str,
        document_id: str,
        question: str
    ) -> List[Dict[str, Any]]:
        """Hacer pregunta y obtener respuesta streaming."""
        question_data = {
            "session_id": session_id,
            "user_id": user_id,
            "document_id": document_id,
            "question": question
        }
        
        events = []
        
        with httpx.stream("POST", f"{api_client.base_url}/api/v1/chat/ask", json=question_data) as response:
            if response.status_code != 200:
                raise Exception(f"Question failed: {response.status_code} - {response.text}")
            
            for line in response.iter_lines():
                if line.startswith("data: "):
                    try:
                        event_data = json.loads(line[6:])
                        events.append(event_data)
                    except json.JSONDecodeError:
                        continue
        
        return events
    
    @staticmethod
    def cleanup_user_data(api_client: httpx.Client, user_id: str):
        """Limpiar todos los datos de un usuario."""
        try:
            # Obtener sesiones del usuario
            sessions_response = api_client.get(f"/api/v1/chat/sessions?user_id={user_id}")
            if sessions_response.status_code == 200:
                sessions = sessions_response.json().get("sessions", [])
                
                # Eliminar sesiones
                for session in sessions:
                    api_client.delete(f"/api/v1/chat/sessions/{session['session_id']}?user_id={user_id}")
            
            # Obtener documentos del usuario
            docs_response = api_client.get(f"/api/v1/documents/?user_id={user_id}")
            if docs_response.status_code == 200:
                documents = docs_response.json()
                
                # Eliminar documentos
                for doc in documents:
                    api_client.delete(f"/api/v1/documents/{doc['document_id']}")
        
        except Exception:
            # Ignorar errores en cleanup
            pass


class TestAssertions:
    """Assertions personalizadas para tests."""
    
    @staticmethod
    def assert_document_structure(doc: Dict[str, Any], expected_fields: Optional[List[str]] = None):
        """Verificar estructura de documento."""
        required_fields = expected_fields or [
            "document_id", "filename", "content_type", "file_size",
            "processing_status", "created_at", "updated_at"
        ]
        
        for field in required_fields:
            assert field in doc, f"Field '{field}' missing in document"
        
        assert isinstance(doc["document_id"], str)
        assert len(doc["document_id"]) > 0
        assert isinstance(doc["filename"], str)
        assert len(doc["filename"]) > 0
        assert doc["processing_status"] in ["processing", "completed", "failed"]
    
    @staticmethod
    def assert_session_structure(session: Dict[str, Any]):
        """Verificar estructura de sesión de chat."""
        required_fields = [
            "session_id", "user_id", "document_id", "session_name",
            "is_active", "created_at", "last_interaction_at", "interaction_count"
        ]
        
        for field in required_fields:
            assert field in session, f"Field '{field}' missing in session"
        
        assert isinstance(session["session_id"], str)
        assert isinstance(session["user_id"], str)
        assert isinstance(session["document_id"], str)
        assert isinstance(session["session_name"], str)
        assert isinstance(session["is_active"], bool)
        assert isinstance(session["interaction_count"], int)
    
    @staticmethod
    def assert_search_result_structure(result: Dict[str, Any]):
        """Verificar estructura de resultado de búsqueda."""
        required_fields = [
            "search_term", "total_found", "documents", "limit", "skip"
        ]
        
        for field in required_fields:
            assert field in result, f"Field '{field}' missing in search result"
        
        assert isinstance(result["total_found"], int)
        assert isinstance(result["documents"], list)
        assert isinstance(result["limit"], int)
        assert isinstance(result["skip"], int)
        assert result["total_found"] >= 0
    
    @staticmethod
    def assert_token_structure(token: Dict[str, Any], token_type: str):
        """Verificar estructura de token."""
        if token_type == "speech":
            required_fields = ["access_token", "token_type", "expires_in", "region", "issued_at"]
            assert token["token_type"] == "Bearer"
            assert token["expires_in"] == 600
        elif token_type == "storage":
            required_fields = [
                "sas_token", "container_url", "base_url", "container_name",
                "account_name", "expires_at", "permissions", "resource_type", "issued_at"
            ]
            assert token["permissions"] == "rl"
            assert token["resource_type"] == "container"
        else:
            raise ValueError(f"Unknown token type: {token_type}")
        
        for field in required_fields:
            assert field in token, f"Field '{field}' missing in {token_type} token"
        
        assert isinstance(token["issued_at"], str)
        assert len(token["issued_at"]) > 0


class TestMetrics:
    """Métricas y timing para tests."""
    
    def __init__(self):
        self.start_time = None
        self.metrics = {}
    
    def start_timer(self, operation: str):
        """Iniciar timer para operación."""
        self.start_time = time.time()
        self.metrics[operation] = {"start": self.start_time}
    
    def end_timer(self, operation: str):
        """Finalizar timer para operación."""
        if operation not in self.metrics:
            raise ValueError(f"Timer for operation '{operation}' not started")
        
        end_time = time.time()
        duration = end_time - self.metrics[operation]["start"]
        
        self.metrics[operation].update({
            "end": end_time,
            "duration": duration
        })
        
        return duration
    
    def get_duration(self, operation: str) -> float:
        """Obtener duración de operación."""
        if operation not in self.metrics or "duration" not in self.metrics[operation]:
            raise ValueError(f"No duration available for operation '{operation}'")
        
        return self.metrics[operation]["duration"]
    
    def assert_performance(self, operation: str, max_duration: float):
        """Verificar que operación completó dentro del tiempo límite."""
        duration = self.get_duration(operation)
        assert duration <= max_duration, f"Operation '{operation}' took {duration:.2f}s (max: {max_duration}s)"
    
    def get_summary(self) -> Dict[str, float]:
        """Obtener resumen de todas las métricas."""
        return {op: data.get("duration", 0) for op, data in self.metrics.items()}


class TestValidators:
    """Validadores de datos para tests."""
    
    @staticmethod
    def is_valid_iso_timestamp(timestamp: str) -> bool:
        """Verificar si es timestamp ISO válido."""
        try:
            datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
            return True
        except ValueError:
            return False
    
    @staticmethod
    def is_valid_object_id(obj_id: str) -> bool:
        """Verificar si es ObjectId de MongoDB válido."""
        import re
        return bool(re.match(r'^[0-9a-fA-F]{24}$', obj_id))
    
    @staticmethod
    def is_valid_medical_filename(filename: str) -> bool:
        """Verificar si es nombre de archivo médico válido."""
        # Formato: EXPEDIENTE_NOMBRE_PACIENTE_NUMERO_EPISODIO_CATEGORIA.pdf
        parts = filename.replace('.pdf', '').split('_')
        return len(parts) >= 4 and filename.endswith('.pdf')
    
    @staticmethod
    def is_valid_url(url: str) -> bool:
        """Verificar si es URL válida."""
        import re
        url_pattern = re.compile(
            r'^https?://'  # http:// or https://
            r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
            r'localhost|'  # localhost...
            r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
            r'(?::\d+)?'  # optional port
            r'(?:/?|[/?]\S+)$', re.IGNORECASE)
        return url_pattern.match(url) is not None
    
    @staticmethod
    def validate_patient_name(name: str) -> bool:
        """Validar formato de nombre de paciente."""
        # Formato esperado: APELLIDO, NOMBRE o APELLIDO1 APELLIDO2, NOMBRE1 NOMBRE2
        return ', ' in name and len(name.split(', ')) == 2 