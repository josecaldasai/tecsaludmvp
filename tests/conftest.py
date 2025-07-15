"""
Configuración de pytest y fixtures para tests de TecSalud MVP.
"""

import pytest
import asyncio
import httpx
import os
import time
import tempfile
from typing import Generator, Dict, Any, List
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
import requests


# Configuración base
BASE_URL = "http://localhost:8000"
TEST_TIMEOUT = 30


@pytest.fixture(scope="session")
def event_loop():
    """Crear event loop para toda la sesión de tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
def api_client():
    """Cliente HTTP para hacer requests a la API."""
    return httpx.Client(base_url=BASE_URL, timeout=TEST_TIMEOUT)


@pytest.fixture(scope="session")
def async_api_client():
    """Cliente HTTP asíncrono para hacer requests a la API."""
    return httpx.AsyncClient(base_url=BASE_URL, timeout=TEST_TIMEOUT)


@pytest.fixture(scope="session")
def mongodb_client():
    """Cliente de MongoDB para operaciones de base de datos."""
    client = MongoClient("mongodb://localhost:27017")
    yield client
    client.close()


@pytest.fixture(scope="session")
def mongodb_database(mongodb_client):
    """Base de datos de MongoDB para tests."""
    return mongodb_client["tecsalud_chatbot"]


@pytest.fixture(scope="function")
def clean_database(mongodb_database):
    """
    Limpiar la base de datos antes de cada test.
    Esto asegura que cada test empiece con una base de datos limpia.
    """
    # Limpiar todas las colecciones
    collections_to_clean = [
        "documents",
        "chat_sessions", 
        "chat_interactions",
        "pills"
    ]
    
    for collection_name in collections_to_clean:
        try:
            mongodb_database[collection_name].delete_many({})
        except Exception as e:
            # Ignorar errores si la colección no existe
            pass
    
    yield mongodb_database
    
    # Limpiar después del test también
    for collection_name in collections_to_clean:
        try:
            mongodb_database[collection_name].delete_many({})
        except Exception as e:
            pass


@pytest.fixture
def sample_pdf_file():
    """
    Crear un archivo PDF de prueba temporal.
    """
    # Crear contenido PDF básico
    pdf_content = b"""%PDF-1.4
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
/Length 44
>>
stream
BT
/F1 12 Tf
100 700 Td
(Test PDF Document) Tj
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
285
%%EOF"""
    
    # Crear archivo temporal
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(pdf_content)
        temp_file_path = temp_file.name
    
    yield temp_file_path
    
    # Limpiar archivo temporal
    try:
        os.unlink(temp_file_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def sample_medical_pdf_file():
    """
    Crear un archivo PDF con nombre médico válido para pruebas.
    """
    # Crear contenido PDF médico simulado
    pdf_content = b"""%PDF-1.4
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
/Length 100
>>
stream
BT
/F1 12 Tf
100 700 Td
(Expediente Medico) Tj
0 -20 Td
(Paciente: GARCIA LOPEZ, MARIA) Tj
0 -20 Td
(Episodio: 2024010100001) Tj
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
341
%%EOF"""
    
    # Crear archivo temporal con nombre médico
    filename = "4000123456_GARCIA LOPEZ, MARIA_2024010100001_EMER.pdf"
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
        temp_file.write(pdf_content)
        temp_file_path = temp_file.name
    
    yield {
        "path": temp_file_path,
        "filename": filename,
        "expediente": "4000123456",
        "nombre_paciente": "GARCIA LOPEZ, MARIA",
        "numero_episodio": "2024010100001",
        "categoria": "EMER"
    }
    
    # Limpiar archivo temporal
    try:
        os.unlink(temp_file_path)
    except FileNotFoundError:
        pass


@pytest.fixture
def test_user_data():
    """Datos de usuario de prueba consistentes."""
    return {
        "user_id": "test_user_001",
        "alternative_user_id": "test_user_002",
        "description": "Documento de prueba para testing",
        "tags": ["test", "automation", "pytest"]
    }


@pytest.fixture
def wait_for_processing():
    """
    Helper para esperar a que se complete el procesamiento de documentos.
    """
    def _wait_for_processing(api_client, document_id: str, max_wait: int = 30) -> Dict[str, Any]:
        """
        Esperar a que se complete el procesamiento de un documento.
        
        Args:
            api_client: Cliente HTTP
            document_id: ID del documento
            max_wait: Tiempo máximo de espera en segundos
            
        Returns:
            Información del documento procesado
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            response = api_client.get(f"/api/v1/documents/{document_id}")
            
            if response.status_code == 200:
                doc_info = response.json()
                if doc_info.get("processing_status") in ["completed", "failed"]:
                    return doc_info
            
            time.sleep(1)
        
        raise TimeoutError(f"Document processing did not complete within {max_wait} seconds")
    
    return _wait_for_processing


@pytest.fixture
def server_health_check(api_client):
    """
    Verificar que el servidor esté ejecutándose antes de los tests.
    """
    try:
        response = api_client.get("/health")
        if response.status_code != 200:
            pytest.skip("Server is not running or not healthy")
    except Exception as e:
        pytest.skip(f"Cannot connect to server: {e}")
    
    return True


@pytest.fixture
def uploaded_document(api_client, clean_database, sample_medical_pdf_file, test_user_data, wait_for_processing):
    """
    Fixture que sube un documento y espera a que se procese completamente.
    Útil para tests que necesitan un documento ya procesado.
    """
    # Subir documento
    with open(sample_medical_pdf_file["path"], "rb") as file:
        files = {"file": (sample_medical_pdf_file["filename"], file, "application/pdf")}
        data = {
            "user_id": test_user_data["user_id"],
            "description": test_user_data["description"],
            "tags": str(test_user_data["tags"])
        }
        
        response = api_client.post("/api/v1/documents/upload", files=files, data=data)
        assert response.status_code == 201
        
        upload_result = response.json()
        document_id = upload_result["document_id"]
    
    # Esperar a que se complete el procesamiento
    processed_doc = wait_for_processing(api_client, document_id)
    
    yield {
        "document_id": document_id,
        "upload_result": upload_result,
        "processed_info": processed_doc,
        "file_info": sample_medical_pdf_file,
        "user_data": test_user_data
    }


@pytest.fixture
def chat_session(api_client, uploaded_document):
    """
    Fixture que crea una sesión de chat con un documento ya procesado.
    """
    # Crear sesión de chat
    session_data = {
        "user_id": uploaded_document["user_data"]["user_id"],
        "document_id": uploaded_document["document_id"],
        "session_name": "Test Chat Session"
    }
    
    response = api_client.post("/api/v1/chat/sessions", json=session_data)
    assert response.status_code == 201
    
    session_info = response.json()
    
    yield {
        "session_id": session_info["session_id"],
        "session_info": session_info,
        "document": uploaded_document
    }


@pytest.fixture(scope="function")
def token_cache_cleanup():
    """
    Limpiar cache de tokens antes y después de cada test.
    """
    # Limpiar antes del test
    try:
        requests.post(f"{BASE_URL}/api/v1/tokens/speech/invalidate")
        requests.post(f"{BASE_URL}/api/v1/tokens/storage/invalidate")
    except:
        pass
    
    yield
    
    # Limpiar después del test
    try:
        requests.post(f"{BASE_URL}/api/v1/tokens/speech/invalidate")
        requests.post(f"{BASE_URL}/api/v1/tokens/storage/invalidate")
    except:
        pass


# Configuración de pytest
def pytest_configure(config):
    """Configuración global de pytest."""
    config.addinivalue_line(
        "markers", "slow: marca tests que son lentos de ejecutar"
    )
    config.addinivalue_line(
        "markers", "integration: marca tests de integración"
    )
    config.addinivalue_line(
        "markers", "unit: marca tests unitarios"
    )
    config.addinivalue_line(
        "markers", "api: marca tests de API"
    )


def pytest_collection_modifyitems(config, items):
    """Modificar items de test para agregar marcadores automáticamente."""
    for item in items:
        # Marcar tests que usan fixtures que requieren server como integration
        if any(fixture in item.fixturenames for fixture in ["api_client", "server_health_check"]):
            item.add_marker(pytest.mark.integration)
            item.add_marker(pytest.mark.api)
        
        # Marcar tests lentos
        if any(keyword in item.name.lower() for keyword in ["upload", "process", "batch", "chat"]):
            item.add_marker(pytest.mark.slow) 