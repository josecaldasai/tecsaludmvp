"""
Tests para endpoints de health check y verificación del servidor.
"""

import pytest
import time


class TestHealthEndpoints:
    """Tests para endpoints de salud del sistema."""

    def test_root_endpoint(self, api_client, server_health_check):
        """Test del endpoint raíz - información básica de la API."""
        response = api_client.get("/")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data
        assert "status" in data
        assert "timestamp" in data
        assert "api_version" in data
        
        assert data["message"] == "TecSalud Chatbot Document Processing API"
        assert data["status"] == "healthy"
        assert data["api_version"] == "v1"
        assert isinstance(data["timestamp"], (int, float))

    def test_health_check_endpoint(self, api_client, server_health_check):
        """Test del endpoint de health check."""
        response = api_client.get("/health")
        
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "environment" in data
        
        assert data["status"] == "healthy"
        assert data["environment"] in ["development", "production"]
        assert isinstance(data["timestamp"], (int, float))

    def test_health_check_timing(self, api_client, server_health_check):
        """Test que el health check responde rápidamente."""
        start_time = time.time()
        response = api_client.get("/health")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Debería responder en menos de 1 segundo

    def test_root_endpoint_timing(self, api_client, server_health_check):
        """Test que el endpoint raíz responde rápidamente."""
        start_time = time.time()
        response = api_client.get("/")
        end_time = time.time()
        
        assert response.status_code == 200
        assert (end_time - start_time) < 1.0  # Debería responder en menos de 1 segundo

    def test_multiple_health_checks(self, api_client, server_health_check):
        """Test de múltiples health checks consecutivos."""
        responses = []
        
        for _ in range(5):
            response = api_client.get("/health")
            responses.append(response)
        
        # Todos deberían ser exitosos
        for response in responses:
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "healthy"

    @pytest.mark.edge_case
    def test_nonexistent_endpoint(self, api_client, server_health_check):
        """Test de endpoint que no existe - debería retornar 404."""
        response = api_client.get("/nonexistent-endpoint")
        
        assert response.status_code == 404

    @pytest.mark.edge_case
    def test_invalid_method_on_health(self, api_client, server_health_check):
        """Test de método HTTP inválido en endpoint de health."""
        response = api_client.post("/health")
        
        assert response.status_code == 405  # Method Not Allowed

    @pytest.mark.edge_case
    def test_invalid_method_on_root(self, api_client, server_health_check):
        """Test de método HTTP inválido en endpoint raíz."""
        response = api_client.post("/")
        
        assert response.status_code == 405  # Method Not Allowed 