#!/usr/bin/env python3
"""
Script de pruebas para el sistema de búsqueda fuzzy de documentos por nombre de paciente.
"""

import requests
import json
from typing import Dict, List, Any

# Configuración
BASE_URL = "http://localhost:8000"
FUZZY_SEARCH_URL = f"{BASE_URL}/api/v1/search"


def test_fuzzy_search_basic():
    """Prueba básica de búsqueda fuzzy."""
    print("🔍 Prueba básica de búsqueda fuzzy")
    print("-" * 50)
    
    # Casos de prueba
    test_cases = [
        "GARCIA",
        "PEDRO",
        "CARDENAS",
        "MARIA",
        "LOPEZ",
        "JAVIER"
    ]
    
    for search_term in test_cases:
        print(f"\n📝 Buscando: '{search_term}'")
        
        try:
            response = requests.get(
                f"{FUZZY_SEARCH_URL}/patients",
                params={
                    "search_term": search_term,
                    "limit": 5,
                    "min_similarity": 0.3
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ Encontrados: {data['total_found']} documentos")
                print(f"🔤 Término normalizado: '{data['normalized_term']}'")
                
                for i, doc in enumerate(data['documents'][:3]):  # Mostrar primeros 3
                    print(f"   {i+1}. {doc['nombre_paciente']} - Score: {doc['similarity_score']:.3f} ({doc['match_type']})")
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error en la prueba: {e}")


def test_fuzzy_search_with_user_filter():
    """Prueba de búsqueda fuzzy con filtro por usuario."""
    print("\n\n👤 Prueba con filtro por usuario")
    print("-" * 50)
    
    search_term = "GARCIA"
    user_id = "test_user"
    
    try:
        response = requests.get(
            f"{FUZZY_SEARCH_URL}/patients",
            params={
                "search_term": search_term,
                "user_id": user_id,
                "limit": 10,
                "min_similarity": 0.2
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Encontrados: {data['total_found']} documentos para usuario '{user_id}'")
            
            for doc in data['documents']:
                print(f"   - {doc['nombre_paciente']} (Usuario: {doc['user_id']}) - Score: {doc['similarity_score']:.3f}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")


def test_suggestions():
    """Prueba de sugerencias de nombres."""
    print("\n\n💡 Prueba de sugerencias")
    print("-" * 50)
    
    partial_terms = ["GAR", "PED", "MAR", "CARD"]
    
    for partial_term in partial_terms:
        print(f"\n🔤 Sugerencias para: '{partial_term}'")
        
        try:
            response = requests.get(
                f"{FUZZY_SEARCH_URL}/patients/suggestions",
                params={
                    "partial_term": partial_term,
                    "limit": 5
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"✅ {data['total_suggestions']} sugerencias:")
                
                for i, suggestion in enumerate(data['suggestions']):
                    print(f"   {i+1}. {suggestion}")
            else:
                print(f"❌ Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"❌ Error en la prueba: {e}")


def test_exact_patient_search():
    """Prueba de búsqueda exacta por nombre de paciente."""
    print("\n\n🎯 Prueba de búsqueda exacta por paciente")
    print("-" * 50)
    
    # Primero obtener un nombre de paciente real
    try:
        response = requests.get(
            f"{FUZZY_SEARCH_URL}/patients",
            params={
                "search_term": "GARCIA",
                "limit": 1
            }
        )
        
        if response.status_code == 200:
            data = response.json()
            if data['documents']:
                patient_name = data['documents'][0]['nombre_paciente']
                print(f"📝 Buscando documentos para: '{patient_name}'")
                
                # Ahora buscar todos los documentos de ese paciente
                response = requests.get(
                    f"{FUZZY_SEARCH_URL}/patients/{patient_name}/documents",
                    params={
                        "limit": 10
                    }
                )
                
                if response.status_code == 200:
                    data = response.json()
                    print(f"✅ Encontrados: {data['total_found']} documentos")
                    
                    for doc in data['documents']:
                        print(f"   - {doc['filename']} (Expediente: {doc['expediente']}) - Score: {doc['similarity_score']:.3f}")
                else:
                    print(f"❌ Error {response.status_code}: {response.text}")
            else:
                print("❌ No se encontraron documentos para obtener un nombre de paciente")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error en la prueba: {e}")


def test_similarity_thresholds():
    """Prueba de diferentes umbrales de similitud."""
    print("\n\n📊 Prueba de umbrales de similitud")
    print("-" * 50)
    
    search_term = "GARCIA"
    thresholds = [0.1, 0.3, 0.5, 0.7, 0.9]
    
    for threshold in thresholds:
        print(f"\n🎚️  Umbral: {threshold}")
        
        try:
            response = requests.get(
                f"{FUZZY_SEARCH_URL}/patients",
                params={
                    "search_term": search_term,
                    "min_similarity": threshold,
                    "limit": 20
                }
            )
            
            if response.status_code == 200:
                data = response.json()
                print(f"   Encontrados: {data['total_found']} documentos")
                
                # Mostrar distribución de tipos de match
                match_types = {}
                for doc in data['documents']:
                    match_type = doc['match_type']
                    match_types[match_type] = match_types.get(match_type, 0) + 1
                
                if match_types:
                    print(f"   Tipos de match: {match_types}")
            else:
                print(f"   ❌ Error {response.status_code}: {response.text}")
                
        except Exception as e:
            print(f"   ❌ Error en la prueba: {e}")


def test_health_check():
    """Verificar que la API esté funcionando."""
    print("🏥 Verificando estado de la API")
    print("-" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/health")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ API funcionando correctamente")
            print(f"   Status: {data['status']}")
            print(f"   Timestamp: {data['timestamp']}")
        else:
            print(f"❌ Error {response.status_code}: {response.text}")
            
    except Exception as e:
        print(f"❌ Error conectando a la API: {e}")


def main():
    """Ejecutar todas las pruebas."""
    print("🚀 INICIANDO PRUEBAS DEL SISTEMA DE BÚSQUEDA FUZZY")
    print("=" * 60)
    
    # Verificar que la API esté funcionando
    test_health_check()
    
    # Ejecutar pruebas de búsqueda fuzzy
    test_fuzzy_search_basic()
    test_fuzzy_search_with_user_filter()
    test_suggestions()
    test_exact_patient_search()
    test_similarity_thresholds()
    
    print("\n\n🏁 PRUEBAS COMPLETADAS")
    print("=" * 60)
    print("🔗 Documentación disponible en: http://localhost:8000/docs")
    print("🔍 Endpoints de búsqueda fuzzy:")
    print("   - GET /api/v1/search/patients - Búsqueda fuzzy")
    print("   - GET /api/v1/search/patients/suggestions - Sugerencias")
    print("   - GET /api/v1/search/patients/{name}/documents - Búsqueda exacta")


if __name__ == "__main__":
    main() 