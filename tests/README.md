# TecSalud MVP - Test Suite

Sistema completo de tests para validar toda la funcionalidad de la API de TecSalud MVP.

## 📋 Descripción

Esta suite de tests incluye:
- **Tests unitarios** para funcionalidades específicas
- **Tests de integración** para validar flujos completos
- **Tests de rendimiento** para verificar tiempos de respuesta
- **Tests de casos edge** para validar manejo de errores
- **Tests end-to-end** para simular recorridos de usuario completos

## 🏗️ Estructura de Archivos

```
tests/
├── __init__.py              # Inicialización del módulo
├── conftest.py              # Configuración de pytest y fixtures
├── pytest.ini              # Configuración de pytest (en raíz)
├── utils.py                 # Utilidades auxiliares para tests
├── API_ENDPOINTS_REFERENCE.md  # Documentación completa de endpoints
├── README.md                # Este archivo
├── test_health.py           # Tests de health checks
├── test_documents.py        # Tests de gestión de documentos
├── test_chat.py            # Tests de chat y sesiones
├── test_search.py          # Tests de búsqueda fuzzy
├── test_tokens.py          # Tests de tokens de Azure
└── test_integration.py     # Tests de integración end-to-end
```

## 🔧 Prerrequisitos

### 1. Servidor ejecutándose
```bash
# Asegúrate de que el servidor esté ejecutándose
python main.py
```

### 2. Base de datos limpia
```bash
# MongoDB debería estar ejecutándose en localhost:27017
# La base de datos se limpia automáticamente en cada test
```

### 3. Configuración de entorno
```bash
# Variables de entorno necesarias (ya configuradas en el proyecto)
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=tecsalud_chatbot
AZURE_STORAGE_CONNECTION_STRING=...
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus
AZURE_OPENAI_ENDPOINT=...
AZURE_OPENAI_API_KEY=...
```

### 4. Dependencias
```bash
# Instalar pytest y dependencias adicionales
pip install pytest pytest-asyncio httpx pymongo requests
```

## 🚀 Ejecución de Tests

### Ejecutar todos los tests
```bash
# Desde la raíz del proyecto
pytest tests/ -v
```

### Ejecutar tests por categoría

#### Tests básicos (rápidos)
```bash
pytest tests/test_health.py -v
pytest tests/test_tokens.py -v
```

#### Tests de funcionalidad principal
```bash
pytest tests/test_documents.py -v
pytest tests/test_chat.py -v
pytest tests/test_search.py -v
```

#### Tests de integración (lentos)
```bash
pytest tests/test_integration.py -v
```

### Ejecutar tests por marcadores

#### Solo tests rápidos
```bash
pytest -v -m "not slow"
```

#### Solo tests lentos
```bash
pytest -v -m "slow"
```

#### Solo tests de integración
```bash
pytest -v -m "integration"
```

#### Solo tests de casos edge
```bash
pytest -v -m "edge_case"
```

### Ejecutar tests específicos

#### Test individual
```bash
pytest tests/test_documents.py::TestDocumentUpload::test_upload_document_success -v
```

#### Clase de tests
```bash
pytest tests/test_chat.py::TestChatSessions -v
```

#### Tests que contienen palabra clave
```bash
pytest -v -k "upload"
pytest -v -k "token"
pytest -v -k "search"
```

## 📊 Escenarios de Testing

### 1. Tests de Health Check (`test_health.py`)
- ✅ Endpoint raíz (`/`)
- ✅ Health check (`/health`)
- ✅ Tiempos de respuesta
- ✅ Múltiples requests consecutivos
- ✅ Manejo de endpoints inexistentes

### 2. Tests de Documentos (`test_documents.py`)
- ✅ Upload individual exitoso
- ✅ Upload con datos mínimos
- ✅ Upload batch exitoso
- ✅ Listado con filtros
- ✅ Obtención de información específica
- ✅ Eliminación de documentos
- ✅ Flujo completo de documento
- ✅ Aislamiento entre usuarios
- ✅ Manejo de errores (archivo inválido, límites excedidos)

### 3. Tests de Chat (`test_chat.py`)
- ✅ Creación de sesiones
- ✅ Listado de sesiones con filtros
- ✅ Preguntas con respuesta streaming
- ✅ Obtención de interacciones
- ✅ Eliminación de sesiones
- ✅ Estadísticas de chat
- ✅ Flujo completo de chat
- ✅ Múltiples sesiones por documento
- ✅ Aislamiento entre usuarios

### 4. Tests de Búsqueda (`test_search.py`)
- ✅ Búsqueda exacta por paciente
- ✅ Búsqueda parcial (fuzzy)
- ✅ Búsqueda insensible a mayúsculas
- ✅ Filtros por usuario
- ✅ Paginación
- ✅ Umbrales de similitud
- ✅ Sugerencias de nombres
- ✅ Documentos por paciente específico
- ✅ Manejo de caracteres especiales
- ✅ Rendimiento con dataset grande

### 5. Tests de Tokens (`test_tokens.py`)
- ✅ Tokens de Azure Speech Services
- ✅ Tokens de Azure Storage
- ✅ Cache de tokens
- ✅ Información de tokens
- ✅ Invalidación de tokens
- ✅ Regeneración después de invalidación
- ✅ URLs firmadas para blobs
- ✅ Múltiples requests concurrentes
- ✅ Independencia entre tipos de tokens

### 6. Tests de Integración (`test_integration.py`)
- ✅ Recorrido completo de usuario individual
- ✅ Recorrido completo con batch upload
- ✅ Aislamiento multi-usuario
- ✅ Recuperación de errores
- ✅ Validación de rendimiento
- ✅ Monitoreo de salud del sistema
- ✅ Operaciones concurrentes
- ✅ Consistencia de datos

## 📈 Métricas y Rendimiento

### Límites de Rendimiento Esperados
- **Upload de documento**: < 30 segundos
- **Listado de documentos**: < 1 segundo
- **Búsqueda fuzzy**: < 2 segundos
- **Generación de token (primera vez)**: < 10 segundos
- **Token desde cache**: < 0.1 segundos
- **Health check**: < 1 segundo

### Monitoreo de Métricas
Los tests incluyen validación automática de:
- Tiempos de respuesta
- Uso de cache
- Consistencia de datos
- Aislamiento entre usuarios
- Manejo de errores
- Recuperación del sistema

## 🔍 Debugging

### Ver output detallado
```bash
pytest tests/ -v -s
```

### Solo mostrar errores
```bash
pytest tests/ -q
```

### Parar en primer error
```bash
pytest tests/ -x
```

### Mostrar timing de tests
```bash
pytest tests/ --durations=10
```

### Ejecutar tests en paralelo (si tienes pytest-xdist)
```bash
pip install pytest-xdist
pytest tests/ -n auto
```

## 🚨 Troubleshooting

### Error: "Server is not running"
```bash
# Asegúrate de que el servidor esté ejecutándose
python main.py
```

### Error: "Cannot connect to MongoDB"
```bash
# Verifica que MongoDB esté ejecutándose
mongod --dbpath /usr/local/var/mongodb
```

### Error: "Token generation failed"
```bash
# Verifica las credenciales de Azure en el archivo .env
# Revisa que las variables de entorno estén configuradas
```

### Error: "Document processing timeout"
```bash
# Verifica que Azure Document Intelligence esté configurado
# Revisa los logs del servidor para errores de procesamiento
```

### Tests lentos
```bash
# Ejecuta solo tests rápidos durante desarrollo
pytest -v -m "not slow"

# O ejecuta tests específicos
pytest tests/test_health.py -v
```

## 📋 Checklist de Validación

### ✅ Antes de ejecutar tests
- [ ] Servidor ejecutándose en localhost:8000
- [ ] MongoDB ejecutándose en localhost:27017
- [ ] Variables de entorno configuradas
- [ ] Base de datos limpia (se limpia automáticamente)

### ✅ Tests básicos (siempre ejecutar)
- [ ] `pytest tests/test_health.py -v`
- [ ] `pytest tests/test_tokens.py -v`

### ✅ Tests de funcionalidad (antes de deploy)
- [ ] `pytest tests/test_documents.py -v`
- [ ] `pytest tests/test_chat.py -v`
- [ ] `pytest tests/test_search.py -v`

### ✅ Tests de integración (antes de release)
- [ ] `pytest tests/test_integration.py -v`

### ✅ Validación completa
- [ ] `pytest tests/ -v` (todos los tests)
- [ ] Verificar que no hay errores en logs del servidor
- [ ] Verificar que la base de datos está limpia después

## 🎯 Casos de Uso Probados

### Escenario 1: Usuario Individual
1. Subir documento médico
2. Esperar procesamiento completo
3. Buscar por nombre de paciente
4. Crear sesión de chat
5. Hacer preguntas sobre el documento
6. Obtener tokens de Azure
7. Generar URL firmada
8. Limpiar recursos

### Escenario 2: Batch Upload
1. Subir múltiples documentos en lote
2. Verificar procesamiento de todos
3. Buscar por diferentes pacientes
4. Crear múltiples sesiones
5. Generar estadísticas consolidadas
6. Limpiar recursos

### Escenario 3: Multi-usuario
1. Dos usuarios suben documentos
2. Verificar aislamiento en listados
3. Verificar aislamiento en búsquedas
4. Verificar aislamiento en chat
5. Verificar seguridad de acceso

### Escenario 4: Recuperación de Errores
1. Operaciones válidas e inválidas mezcladas
2. Verificar que errores no afectan el sistema
3. Verificar que funcionalidad normal continúa
4. Verificar limpieza de recursos

## 🔒 Seguridad Probada

- ✅ Aislamiento entre usuarios
- ✅ Validación de parámetros de entrada
- ✅ Manejo seguro de errores
- ✅ Protección contra acceso no autorizado
- ✅ Validación de tokens
- ✅ Limpieza automática de datos de prueba

## 🎉 Conclusión

Esta suite de tests proporciona validación completa del sistema TecSalud MVP, incluyendo:
- **100+ test cases** cubriendo todos los endpoints
- **Validación de funcionalidad** completa
- **Tests de rendimiento** automatizados
- **Validación de seguridad** multi-usuario
- **Casos edge** y manejo de errores
- **Integración end-to-end** completa

Para cualquier cambio en el código, ejecuta la suite completa para garantizar que no se rompa funcionalidad existente.

```bash
# Comando final para validación completa
pytest tests/ -v --tb=short
```

¡Happy Testing! 🧪✨ 