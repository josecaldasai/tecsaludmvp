"""
Tests para endpoints de tokens de Azure (Speech Services y Storage).
Incluye generación de tokens, información de cache, invalidación y URLs firmadas.
"""

import pytest
import time
import json
from datetime import datetime, timedelta
from typing import Dict, Any


class TestAzureSpeechTokens:
    """Tests para tokens de Azure Speech Services."""

    def test_get_speech_token_success(self, api_client, server_health_check, token_cache_cleanup):
        """Test de obtención exitosa de token de Speech Services."""
        response = api_client.get("/api/v1/tokens/speech")
        
        assert response.status_code == 200
        
        token_data = response.json()
        assert "access_token" in token_data
        assert "token_type" in token_data
        assert "expires_in" in token_data
        assert "region" in token_data
        assert "issued_at" in token_data
        
        assert token_data["token_type"] == "Bearer"
        assert token_data["expires_in"] == 600  # 10 minutos
        assert token_data["region"] == "eastus"
        assert len(token_data["access_token"]) > 0
        
        # Verificar formato de timestamp
        issued_at = token_data["issued_at"]
        assert isinstance(issued_at, str)
        # Debería poder parsear como ISO timestamp
        datetime.fromisoformat(issued_at.replace('Z', '+00:00'))

    def test_get_speech_token_caching(self, api_client, server_health_check, token_cache_cleanup):
        """Test de cache de tokens de Speech Services."""
        # Primera llamada
        response1 = api_client.get("/api/v1/tokens/speech")
        assert response1.status_code == 200
        token1 = response1.json()
        
        # Segunda llamada inmediata - debería usar cache
        response2 = api_client.get("/api/v1/tokens/speech")
        assert response2.status_code == 200
        token2 = response2.json()
        
        # Deberían ser el mismo token (cache funcionando)
        assert token1["access_token"] == token2["access_token"]
        # El issued_at puede ser diferente ya que se genera en cada request (es correcto)

    def test_get_speech_token_info_empty(self, api_client, server_health_check, token_cache_cleanup):
        """Test de información cuando no hay token en cache."""
        response = api_client.get("/api/v1/tokens/speech/info")
        
        assert response.status_code == 200
        
        info = response.json()
        assert "has_cached_token" in info
        assert "is_token_valid" in info
        assert "speech_region" in info
        assert "token_endpoint" in info
        
        assert info["has_cached_token"] is False
        assert info["is_token_valid"] is False
        assert info["speech_region"] == "eastus"

    def test_get_speech_token_info_with_cached_token(self, api_client, server_health_check, token_cache_cleanup):
        """Test de información con token en cache."""
        # Generar token primero
        token_response = api_client.get("/api/v1/tokens/speech")
        assert token_response.status_code == 200
        
        # Obtener información
        info_response = api_client.get("/api/v1/tokens/speech/info")
        assert info_response.status_code == 200
        
        info = info_response.json()
        assert info["has_cached_token"] is True
        assert info["is_token_valid"] is True
        assert "token_expires_at" in info
        assert info["speech_region"] == "eastus"

    def test_invalidate_speech_token(self, api_client, server_health_check, token_cache_cleanup):
        """Test de invalidación de token de Speech Services."""
        # Generar token primero
        token_response = api_client.get("/api/v1/tokens/speech")
        assert token_response.status_code == 200
        
        # Verificar que está en cache
        info_response1 = api_client.get("/api/v1/tokens/speech/info")
        assert info_response1.json()["has_cached_token"] is True
        
        # Invalidar
        invalidate_response = api_client.post("/api/v1/tokens/speech/invalidate")
        assert invalidate_response.status_code == 200
        
        result = invalidate_response.json()
        assert "message" in result
        assert "invalidated successfully" in result["message"]
        
        # Verificar que ya no está en cache
        info_response2 = api_client.get("/api/v1/tokens/speech/info")
        assert info_response2.json()["has_cached_token"] is False

    def test_speech_token_regeneration_after_invalidation(self, api_client, server_health_check, token_cache_cleanup):
        """Test de regeneración de token después de invalidación."""
        # Generar token inicial
        response1 = api_client.get("/api/v1/tokens/speech")
        assert response1.status_code == 200
        token1 = response1.json()["access_token"]
        
        # Invalidar
        invalidate_response = api_client.post("/api/v1/tokens/speech/invalidate")
        assert invalidate_response.status_code == 200
        
        # Generar nuevo token
        response2 = api_client.get("/api/v1/tokens/speech")
        assert response2.status_code == 200
        token2 = response2.json()["access_token"]
        
        # Deberían ser tokens diferentes
        assert token1 != token2

    def test_multiple_speech_token_requests(self, api_client, server_health_check, token_cache_cleanup):
        """Test de múltiples requests de tokens simultáneas."""
        responses = []
        
        # Hacer múltiples requests
        for _ in range(5):
            response = api_client.get("/api/v1/tokens/speech")
            responses.append(response)
        
        # Todas deberían ser exitosas
        for response in responses:
            assert response.status_code == 200
            token_data = response.json()
            assert "access_token" in token_data
            assert len(token_data["access_token"]) > 0
        
        # Todos los tokens deberían ser iguales (cache funcionando)
        first_token = responses[0].json()["access_token"]
        for response in responses[1:]:
            assert response.json()["access_token"] == first_token

    @pytest.mark.edge_case
    def test_speech_token_invalid_method(self, api_client, server_health_check):
        """Test de método HTTP inválido en endpoint de tokens."""
        response = api_client.post("/api/v1/tokens/speech")
        
        assert response.status_code == 405  # Method Not Allowed

    @pytest.mark.edge_case
    def test_speech_token_info_invalid_method(self, api_client, server_health_check):
        """Test de método HTTP inválido en endpoint de info."""
        response = api_client.post("/api/v1/tokens/speech/info")
        
        assert response.status_code == 405  # Method Not Allowed


class TestAzureStorageTokens:
    """Tests para tokens de Azure Storage."""

    def test_get_storage_token_success(self, api_client, server_health_check, token_cache_cleanup):
        """Test de obtención exitosa de token de Storage."""
        response = api_client.get("/api/v1/tokens/storage")
        
        assert response.status_code == 200
        
        token_data = response.json()
        assert "sas_token" in token_data
        assert "container_url" in token_data
        assert "base_url" in token_data
        assert "container_name" in token_data
        assert "account_name" in token_data
        assert "expires_at" in token_data
        assert "permissions" in token_data
        assert "resource_type" in token_data
        assert "issued_at" in token_data
        
        assert token_data["permissions"] == "rl"  # read/list
        assert token_data["resource_type"] == "container"
        assert token_data["container_name"] == "documents"
        assert len(token_data["sas_token"]) > 0
        assert token_data["container_url"].startswith("https://")
        assert token_data["base_url"].startswith("https://")
        
        # Verificar formato de timestamps
        issued_at = token_data["issued_at"]
        expires_at = token_data["expires_at"]
        assert isinstance(issued_at, str)
        assert isinstance(expires_at, str)
        
        # Debería poder parsear como ISO timestamps
        datetime.fromisoformat(issued_at.replace('Z', '+00:00'))
        datetime.fromisoformat(expires_at.replace('Z', '+00:00'))

    def test_get_storage_token_caching(self, api_client, server_health_check, token_cache_cleanup):
        """Test de cache de tokens de Storage."""
        # Primera llamada
        response1 = api_client.get("/api/v1/tokens/storage")
        assert response1.status_code == 200
        token1 = response1.json()
        
        # Segunda llamada inmediata - debería usar cache
        response2 = api_client.get("/api/v1/tokens/storage")
        assert response2.status_code == 200
        token2 = response2.json()
        
        # Deberían ser el mismo token (cache funcionando)
        assert token1["sas_token"] == token2["sas_token"]
        assert token1["expires_at"] == token2["expires_at"]
        # El issued_at puede ser diferente ya que se genera en cada request (es correcto)

    def test_get_storage_token_info_empty(self, api_client, server_health_check, token_cache_cleanup):
        """Test de información cuando no hay token en cache."""
        response = api_client.get("/api/v1/tokens/storage/info")
        
        assert response.status_code == 200
        
        info = response.json()
        assert "has_cached_token" in info
        assert "is_token_valid" in info
        assert "account_name" in info
        assert "container_name" in info
        assert "base_url" in info
        
        assert info["has_cached_token"] is False
        assert info["is_token_valid"] is False
        assert info["container_name"] == "documents"

    def test_get_storage_token_info_with_cached_token(self, api_client, server_health_check, token_cache_cleanup):
        """Test de información con token en cache."""
        # Generar token primero
        token_response = api_client.get("/api/v1/tokens/storage")
        assert token_response.status_code == 200
        
        # Obtener información
        info_response = api_client.get("/api/v1/tokens/storage/info")
        assert info_response.status_code == 200
        
        info = info_response.json()
        assert info["has_cached_token"] is True
        assert info["is_token_valid"] is True
        assert "token_expires_at" in info
        assert info["container_name"] == "documents"

    def test_invalidate_storage_token(self, api_client, server_health_check, token_cache_cleanup):
        """Test de invalidación de token de Storage."""
        # Generar token primero
        token_response = api_client.get("/api/v1/tokens/storage")
        assert token_response.status_code == 200
        
        # Verificar que está en cache
        info_response1 = api_client.get("/api/v1/tokens/storage/info")
        assert info_response1.json()["has_cached_token"] is True
        
        # Invalidar
        invalidate_response = api_client.post("/api/v1/tokens/storage/invalidate")
        assert invalidate_response.status_code == 200
        
        result = invalidate_response.json()
        assert "message" in result
        assert "invalidated successfully" in result["message"]
        
        # Verificar que ya no está en cache
        info_response2 = api_client.get("/api/v1/tokens/storage/info")
        assert info_response2.json()["has_cached_token"] is False

    def test_storage_token_regeneration_after_invalidation(self, api_client, server_health_check, token_cache_cleanup):
        """Test de regeneración de token después de invalidación."""
        # Generar token inicial
        response1 = api_client.get("/api/v1/tokens/storage")
        assert response1.status_code == 200
        token1_data = response1.json()
        
        # Invalidar
        invalidate_response = api_client.post("/api/v1/tokens/storage/invalidate")
        assert invalidate_response.status_code == 200
        
        # Esperar un poco para que cambie el tiempo de expiración
        time.sleep(2)
        
        # Generar nuevo token
        response2 = api_client.get("/api/v1/tokens/storage")
        assert response2.status_code == 200
        token2_data = response2.json()
        
        # Los tokens deberían ser diferentes (diferentes tiempos de expiración)
        assert token1_data["expires_at"] != token2_data["expires_at"]

    def test_get_blob_url_success(self, api_client, server_health_check, token_cache_cleanup):
        """Test de obtención exitosa de URL firmada para blob."""
        blob_name = "test-document.pdf"
        
        response = api_client.get(f"/api/v1/tokens/storage/blob/{blob_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert "blob_name" in result
        assert "blob_url" in result
        assert "generated_at" in result
        
        assert result["blob_name"] == blob_name
        assert result["blob_url"].startswith("https://")
        assert blob_name in result["blob_url"]
        assert "?" in result["blob_url"]  # Debería contener query parameters (SAS)
        
        # Verificar timestamp
        generated_at = result["generated_at"]
        assert isinstance(generated_at, str)
        datetime.fromisoformat(generated_at.replace('Z', '+00:00'))

    def test_get_blob_url_with_special_characters(self, api_client, server_health_check, token_cache_cleanup):
        """Test de URL para blob con caracteres especiales."""
        blob_name = "4000123456_GARCÍA LÓPEZ, MARÍA_2024010100001_EMER.pdf"
        
        response = api_client.get(f"/api/v1/tokens/storage/blob/{blob_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["blob_name"] == blob_name
        assert result["blob_url"].startswith("https://")

    @pytest.mark.skip(reason="Endpoint no soporta paths anidados actualmente")
    def test_get_blob_url_nested_path(self, api_client, server_health_check, token_cache_cleanup):
        """Test de URL para blob en path anidado."""
        blob_name = "documents/2024/01/test-document.pdf"
        
        response = api_client.get(f"/api/v1/tokens/storage/blob/{blob_name}")
        
        assert response.status_code == 200
        
        result = response.json()
        assert result["blob_name"] == blob_name
        assert "documents%2F2024%2F01%2Ftest-document.pdf" in result["blob_url"] or blob_name in result["blob_url"]

    @pytest.mark.edge_case
    def test_get_blob_url_empty_name(self, api_client, server_health_check):
        """Test de error con nombre de blob vacío."""
        response = api_client.get("/api/v1/tokens/storage/blob/")
        
        # Debería fallar o redirigir
        assert response.status_code in [400, 404, 422]

    def test_multiple_storage_token_requests(self, api_client, server_health_check, token_cache_cleanup):
        """Test de múltiples requests de tokens simultáneas."""
        responses = []
        
        # Hacer múltiples requests
        for _ in range(5):
            response = api_client.get("/api/v1/tokens/storage")
            responses.append(response)
        
        # Todas deberían ser exitosas
        for response in responses:
            assert response.status_code == 200
            token_data = response.json()
            assert "sas_token" in token_data
            assert len(token_data["sas_token"]) > 0
        
        # Todos los tokens deberían ser iguales (cache funcionando)
        first_token = responses[0].json()["sas_token"]
        for response in responses[1:]:
            assert response.json()["sas_token"] == first_token

    @pytest.mark.edge_case
    def test_storage_token_invalid_method(self, api_client, server_health_check):
        """Test de método HTTP inválido en endpoint de tokens."""
        response = api_client.post("/api/v1/tokens/storage")
        
        assert response.status_code == 405  # Method Not Allowed

    @pytest.mark.edge_case
    def test_storage_token_info_invalid_method(self, api_client, server_health_check):
        """Test de método HTTP inválido en endpoint de info."""
        response = api_client.post("/api/v1/tokens/storage/info")
        
        assert response.status_code == 405  # Method Not Allowed


class TestTokensWorkflow:
    """Tests de flujo completo de tokens."""

    def test_complete_tokens_workflow(self, api_client, server_health_check, token_cache_cleanup):
        """Test del flujo completo de tokens."""
        
        # 1. Verificar que no hay tokens en cache
        speech_info1 = api_client.get("/api/v1/tokens/speech/info")
        storage_info1 = api_client.get("/api/v1/tokens/storage/info")
        
        assert speech_info1.json()["has_cached_token"] is False
        assert storage_info1.json()["has_cached_token"] is False
        
        # 2. Generar tokens
        speech_token_response = api_client.get("/api/v1/tokens/speech")
        storage_token_response = api_client.get("/api/v1/tokens/storage")
        
        assert speech_token_response.status_code == 200
        assert storage_token_response.status_code == 200
        
        speech_token = speech_token_response.json()
        storage_token = storage_token_response.json()
        
        # 3. Verificar que están en cache
        speech_info2 = api_client.get("/api/v1/tokens/speech/info")
        storage_info2 = api_client.get("/api/v1/tokens/storage/info")
        
        assert speech_info2.json()["has_cached_token"] is True
        assert storage_info2.json()["has_cached_token"] is True
        
        # 4. Usar token de storage para generar URL de blob
        blob_url_response = api_client.get("/api/v1/tokens/storage/blob/test-document.pdf")
        assert blob_url_response.status_code == 200
        
        # 5. Invalidar ambos tokens
        invalidate_speech = api_client.post("/api/v1/tokens/speech/invalidate")
        invalidate_storage = api_client.post("/api/v1/tokens/storage/invalidate")
        
        assert invalidate_speech.status_code == 200
        assert invalidate_storage.status_code == 200
        
        # 6. Verificar que ya no están en cache
        speech_info3 = api_client.get("/api/v1/tokens/speech/info")
        storage_info3 = api_client.get("/api/v1/tokens/storage/info")
        
        assert speech_info3.json()["has_cached_token"] is False
        assert storage_info3.json()["has_cached_token"] is False
        
        # 7. Regenerar tokens (con delay para asegurar diferencias)
        time.sleep(2)
        
        speech_token_response2 = api_client.get("/api/v1/tokens/speech")
        storage_token_response2 = api_client.get("/api/v1/tokens/storage")
        
        assert speech_token_response2.status_code == 200
        assert storage_token_response2.status_code == 200
        
        # 8. Verificar que son tokens diferentes
        new_speech_token = speech_token_response2.json()
        new_storage_token = storage_token_response2.json()
        
        assert new_speech_token["access_token"] != speech_token["access_token"]
        # Para storage, verificar que al menos el tiempo de expiración es diferente
        assert new_storage_token["expires_at"] != storage_token["expires_at"]

    def test_tokens_independence(self, api_client, server_health_check, token_cache_cleanup):
        """Test de independencia entre tokens de Speech y Storage."""
        
        # Generar solo token de Speech
        speech_response = api_client.get("/api/v1/tokens/speech")
        assert speech_response.status_code == 200
        
        # Verificar estados
        speech_info = api_client.get("/api/v1/tokens/speech/info")
        storage_info = api_client.get("/api/v1/tokens/storage/info")
        
        assert speech_info.json()["has_cached_token"] is True
        assert storage_info.json()["has_cached_token"] is False
        
        # Invalidar solo token de Speech
        invalidate_speech = api_client.post("/api/v1/tokens/speech/invalidate")
        assert invalidate_speech.status_code == 200
        
        # Generar token de Storage
        storage_response = api_client.get("/api/v1/tokens/storage")
        assert storage_response.status_code == 200
        
        # Verificar estados finales
        final_speech_info = api_client.get("/api/v1/tokens/speech/info")
        final_storage_info = api_client.get("/api/v1/tokens/storage/info")
        
        assert final_speech_info.json()["has_cached_token"] is False
        assert final_storage_info.json()["has_cached_token"] is True

    def test_tokens_concurrent_access(self, api_client, server_health_check, token_cache_cleanup):
        """Test de acceso concurrente a tokens."""
        
        # Simular acceso concurrente mezclando requests
        responses = []
        
        # Mezclar requests de Speech y Storage
        for i in range(10):
            if i % 2 == 0:
                response = api_client.get("/api/v1/tokens/speech")
            else:
                response = api_client.get("/api/v1/tokens/storage")
            responses.append(response)
        
        # Todas deberían ser exitosas
        for response in responses:
            assert response.status_code == 200
            token_data = response.json()
            assert len(token_data) > 0
        
        # Verificar que ambos tipos de tokens están funcionando
        speech_info = api_client.get("/api/v1/tokens/speech/info")
        storage_info = api_client.get("/api/v1/tokens/storage/info")
        
        assert speech_info.json()["has_cached_token"] is True
        assert storage_info.json()["has_cached_token"] is True

    @pytest.mark.slow
    def test_tokens_performance(self, api_client, server_health_check, token_cache_cleanup):
        """Test de rendimiento de tokens."""
        
        # Medir tiempo de generación inicial
        start_time = time.time()
        
        # Primera generación (no cache)
        speech_response1 = api_client.get("/api/v1/tokens/speech")
        storage_response1 = api_client.get("/api/v1/tokens/storage")
        
        first_generation_time = time.time() - start_time
        
        assert speech_response1.status_code == 200
        assert storage_response1.status_code == 200
        
        # Medir tiempo de acceso con cache
        start_time = time.time()
        
        # Accesos con cache
        for _ in range(10):
            speech_response = api_client.get("/api/v1/tokens/speech")
            storage_response = api_client.get("/api/v1/tokens/storage")
            assert speech_response.status_code == 200
            assert storage_response.status_code == 200
        
        cached_access_time = time.time() - start_time
        
        # El acceso con cache debería ser significativamente más rápido
        average_cached_time = cached_access_time / 10
        
        # Cache debería ser al menos 2x más rápido que la generación inicial
        assert average_cached_time * 2 < first_generation_time
        
        # Verificar que el cache está funcionando
        speech_info = api_client.get("/api/v1/tokens/speech/info")
        storage_info = api_client.get("/api/v1/tokens/storage/info")
        
        assert speech_info.json()["has_cached_token"] is True
        assert storage_info.json()["has_cached_token"] is True

    def test_tokens_expiration_handling(self, api_client, server_health_check, token_cache_cleanup):
        """Test de manejo de expiración de tokens."""
        
        # Generar tokens
        speech_response = api_client.get("/api/v1/tokens/speech")
        storage_response = api_client.get("/api/v1/tokens/storage")
        
        assert speech_response.status_code == 200
        assert storage_response.status_code == 200
        
        speech_token = speech_response.json()
        storage_token = storage_response.json()
        
        # Verificar que tienen timestamps de expiración válidos
        speech_info = api_client.get("/api/v1/tokens/speech/info")
        storage_info = api_client.get("/api/v1/tokens/storage/info")
        
        assert speech_info.json()["is_token_valid"] is True
        assert storage_info.json()["is_token_valid"] is True
        
        # Verificar que los timestamps son futuros
        now = datetime.now()
        
        if "token_expires_at" in speech_info.json():
            speech_expires = datetime.fromisoformat(speech_info.json()["token_expires_at"].replace('Z', '+00:00'))
            assert speech_expires > now
        
        if "token_expires_at" in storage_info.json():
            storage_expires = datetime.fromisoformat(storage_info.json()["token_expires_at"].replace('Z', '+00:00'))
            assert storage_expires > now

    def test_blob_url_generation_with_different_names(self, api_client, server_health_check, token_cache_cleanup):
        """Test de generación de URLs para diferentes nombres de blob."""
        
        blob_names = [
            "simple-document.pdf",
            "document with spaces.pdf",
            "4000123456_PATIENT_NAME_2024010100001_EMER.pdf",
            "document-with-dashes_and_underscores.pdf",
            "DOCUMENT_IN_CAPS.PDF"
        ]
        
        for blob_name in blob_names:
            response = api_client.get(f"/api/v1/tokens/storage/blob/{blob_name}")
            
            assert response.status_code == 200
            
            result = response.json()
            assert result["blob_name"] == blob_name
            assert result["blob_url"].startswith("https://")
            assert "?" in result["blob_url"]  # Debería contener query parameters (SAS)
            
            # Verificar que la URL contiene el nombre del blob (puede estar codificado)
            assert blob_name in result["blob_url"] or blob_name.replace(" ", "%20") in result["blob_url"] 