# API Endpoints Reference - TecSalud MVP

Documento de referencia completo para todos los endpoints de la API de TecSalud MVP.

## 📚 Índice

1. [Documentos (`/api/v1/documents`)](#documents)
2. [Chat (`/api/v1/chat`)](#chat)
3. [Búsqueda Fuzzy (`/api/v1/search`)](#search)
4. [Tokens (`/api/v1/tokens`)](#tokens)
5. [Health (`/`)](#health)

---

## 📄 Documents (`/api/v1/documents`) {#documents}

### 1. Upload Document
- **Endpoint**: `POST /api/v1/documents/upload`
- **Descripción**: Subir un documento individual para procesamiento
- **Content-Type**: `multipart/form-data`

**Entrada (Form Data):**
```typescript
{
  file: File                    // Archivo PDF/imagen (requerido)
  user_id?: string             // ID del usuario (opcional, max 100 chars)
  description?: string         // Descripción (opcional, max 1000 chars)
  tags?: string               // Tags como JSON array string (opcional)
}
```

**Salida:**
```typescript
{
  document_id: string          // ID único del documento
  processing_id: string        // ID de procesamiento
  filename: string            // Nombre original del archivo
  storage_info: {             // Información de almacenamiento
    blob_name: string
    blob_url: string
    container_name: string
  }
  ocr_summary: {              // Resumen de procesamiento OCR
    text_extracted: boolean
    page_count: number
    processing_time: number
  }
  processing_status: string    // Estado: "completed", "failed", etc.
  processing_timestamp: string // ISO timestamp
  expediente?: string         // Número de expediente extraído
  nombre_paciente?: string    // Nombre del paciente extraído
  numero_episodio?: string    // Número de episodio extraído
  categoria?: string          // Categoría (EMER, CONS, etc.)
  medical_info_valid?: boolean // ¿Info médica válida?
  medical_info_error?: string  // Error en parsing médico
}
```

### 2. Upload Batch Documents
- **Endpoint**: `POST /api/v1/documents/upload/batch`
- **Descripción**: Subir múltiples documentos en lote
- **Content-Type**: `multipart/form-data`

**Entrada (Form Data):**
```typescript
{
  files: File[]               // Array de archivos (requerido)
  user_id?: string           // ID del usuario (opcional)
  batch_description?: string  // Descripción del lote (opcional)
  batch_tags?: string        // Tags comunes como JSON array (opcional)
}
```

**Salida:**
```typescript
{
  batch_id: string            // ID único del lote
  batch_timestamp: string     // Timestamp del lote
  batch_description?: string  // Descripción del lote
  user_id?: string           // ID del usuario
  total_files: number        // Total de archivos procesados
  processed_count: number    // Archivos procesados exitosamente
  failed_count: number       // Archivos que fallaron
  success_rate: number       // Porcentaje de éxito (0-100)
  processing_status: string  // "completed", "failed", "partial_success"
  successful_documents: DocumentUploadResponse[] // Docs exitosos
  failed_documents: Array<{  // Docs fallidos
    filename: string
    error: string
    index: number
  }>
  processing_summary: object // Resumen detallado
}
```

### 3. List Documents
- **Endpoint**: `GET /api/v1/documents/`
- **Descripción**: Listar documentos con filtros opcionales

**Entrada (Query Params):**
```typescript
{
  user_id?: string    // Filtrar por usuario (opcional)
  batch_id?: string   // Filtrar por lote (opcional)
  limit?: number      // Máximo resultados (1-100, default: 10)
  skip?: number       // Resultados a saltar (default: 0)
}
```

**Salida:**
```typescript
DocumentInfoResponse[] // Array de documentos
```

### 4. Get Document Info
- **Endpoint**: `GET /api/v1/documents/{document_id}`
- **Descripción**: Obtener información específica de un documento

**Entrada (Path Param):**
```typescript
{
  document_id: string // ID del documento (requerido)
}
```

**Salida:**
```typescript
{
  document_id: string
  processing_id: string
  filename: string
  content_type: string        // MIME type
  file_size: number          // Tamaño en bytes
  user_id?: string
  storage_info: object       // Info de almacenamiento
  extracted_text: string     // Texto extraído por OCR
  processing_status: string
  batch_info?: object       // Info del lote si aplica
  description?: string
  tags: string[]
  expediente?: string
  nombre_paciente?: string
  numero_episodio?: string
  categoria?: string
  medical_info_valid?: boolean
  medical_info_error?: string
  created_at: datetime
  updated_at: datetime
}
```

### 5. Delete Document
- **Endpoint**: `DELETE /api/v1/documents/{document_id}`
- **Descripción**: Eliminar documento completamente (MongoDB + Azure Storage)

**Entrada (Path Param):**
```typescript
{
  document_id: string // ID del documento (requerido)
}
```

**Salida:**
```typescript
{
  document_id: string
  success: boolean    // ¿Eliminación exitosa?
  message: string     // Mensaje descriptivo
}
```

---

## 💬 Chat (`/api/v1/chat`) {#chat}

### 1. Create Chat Session
- **Endpoint**: `POST /api/v1/chat/sessions`
- **Descripción**: Crear nueva sesión de chat para un documento

**Entrada (JSON Body):**
```typescript
{
  user_id: string           // ID del usuario (requerido)
  document_id: string       // ID del documento (requerido)
  session_name?: string     // Nombre personalizado (opcional, max 200 chars)
}
```

**Salida:**
```typescript
{
  session_id: string        // ID único de la sesión
  user_id: string
  document_id: string
  session_name: string      // Nombre de la sesión
  is_active: boolean        // ¿Sesión activa?
  created_at: string        // ISO timestamp
  last_interaction_at: string // ISO timestamp
  interaction_count: number  // Número de interacciones
}
```

### 2. List Chat Sessions
- **Endpoint**: `GET /api/v1/chat/sessions`
- **Descripción**: Listar sesiones de chat (requiere user_id)

**Entrada (Query Params):**
```typescript
{
  user_id: string          // ID del usuario (requerido)
  document_id?: string     // Filtrar por documento (opcional)
  active_only?: boolean    // Solo sesiones activas (default: true)
  limit?: number          // Máximo resultados (1-100, default: 20)
  skip?: number           // Resultados a saltar (default: 0)
}
```

**Salida:**
```typescript
{
  sessions: ChatSessionResponse[] // Array de sesiones
  total_found: number            // Total encontrado
  limit: number                  // Límite aplicado
  skip: number                   // Skip aplicado
}
```

### 3. Ask Question (Streaming)
- **Endpoint**: `POST /api/v1/chat/ask`
- **Descripción**: Hacer pregunta sobre documento con respuesta streaming

**Entrada (JSON Body):**
```typescript
{
  session_id: string       // ID de la sesión (requerido)
  user_id: string         // ID del usuario (requerido)
  document_id: string     // ID del documento (requerido)
  question: string        // Pregunta (requerido, min 3 chars)
}
```

**Salida (Server-Sent Events):**
```typescript
// Evento de inicio
{
  type: "start"
  interaction_id: string
  session_id: string
  question: string
  started_at: string
}

// Eventos de contenido (múltiples)
{
  type: "content"
  content: string         // Chunk de respuesta
  interaction_id: string
}

// Evento de finalización
{
  type: "end"
  interaction_id: string
  completed_at: string
}

// Evento de error (si ocurre)
{
  type: "error"
  error: string
  timestamp: string
}
```

### 4. Get Session Info
- **Endpoint**: `GET /api/v1/chat/sessions/{session_id}`
- **Descripción**: Obtener información específica de una sesión

**Entrada:**
```typescript
Path: session_id: string      // ID de la sesión
Query: user_id: string        // ID del usuario (requerido)
```

**Salida:**
```typescript
ChatSessionResponse // Información de la sesión
```

### 5. Get Session Interactions
- **Endpoint**: `GET /api/v1/chat/sessions/{session_id}/interactions`
- **Descripción**: Obtener interacciones de una sesión

**Entrada:**
```typescript
Path: session_id: string      // ID de la sesión
Query: {
  user_id: string            // ID del usuario (requerido)
  limit?: number             // Máximo resultados (1-100, default: 50)
  skip?: number              // Resultados a saltar (default: 0)
}
```

**Salida:**
```typescript
{
  interactions: Array<{
    interaction_id: string
    session_id: string
    user_id: string
    document_id: string
    question: string
    response: string
    created_at: string
    metadata?: object
  }>
  total_found: number
  limit: number
  skip: number
}
```

### 6. Delete Chat Session
- **Endpoint**: `DELETE /api/v1/chat/sessions/{session_id}`
- **Descripción**: Eliminar sesión y todas sus interacciones

**Entrada:**
```typescript
Path: session_id: string      // ID de la sesión
Query: user_id: string        // ID del usuario (requerido)
```

**Salida:**
```typescript
{
  session_id: string
  deleted: boolean             // ¿Eliminación exitosa?
  interactions_deleted: number // Interacciones eliminadas
  message: string             // Mensaje descriptivo
  deleted_timestamp: string   // ISO timestamp
}
```

### 7. Get Chat Statistics
- **Endpoint**: `GET /api/v1/chat/stats`
- **Descripción**: Obtener estadísticas de chat

**Entrada (Query Params):**
```typescript
{
  user_id?: string     // Filtrar por usuario (opcional)
  document_id?: string // Filtrar por documento (opcional)
  days?: number        // Días a analizar (1-365, default: 30)
}
```

**Salida:**
```typescript
{
  period_days: number            // Días analizados
  total_interactions: number     // Total de interacciones
  total_questions: number        // Total de preguntas
  total_responses: number        // Total de respuestas
  avg_question_length: number    // Promedio de caracteres en preguntas
  avg_response_length: number    // Promedio de caracteres en respuestas
  unique_sessions: number        // Sesiones únicas
  unique_documents: number       // Documentos únicos
  interactions_per_day: number   // Interacciones por día
}
```

---

## 🔍 Search (`/api/v1/search`) {#search}

### 1. Search Patients by Name (Fuzzy)
- **Endpoint**: `GET /api/v1/search/patients`
- **Descripción**: Búsqueda fuzzy de documentos por nombre de paciente

**Entrada (Query Params):**
```typescript
{
  search_term: string        // Nombre o parte del nombre (requerido, 1-200 chars)
  user_id?: string          // Filtrar por usuario (opcional)
  limit?: number            // Máximo resultados (1-100, default: 20)
  skip?: number             // Resultados a saltar (default: 0)
  min_similarity?: number   // Umbral de similitud (0.0-1.0, default: 0.3)
  include_score?: boolean   // Incluir score de similitud (default: true)
}
```

**Salida:**
```typescript
{
  search_term: string                    // Término de búsqueda original
  normalized_term: string                // Término normalizado usado
  total_found: number                    // Total encontrado
  documents: Array<{                     // Documentos con score de similitud
    // ... todos los campos de DocumentInfoResponse
    similarity_score: number             // Score 0.0-1.0
    match_type: string                   // "exact", "prefix", "substring", "fuzzy", "text_search"
  }>
  limit: number
  skip: number
  search_strategies_used: string[]       // Estrategias de búsqueda usadas
  min_similarity_threshold: number       // Umbral aplicado
  search_timestamp: string              // ISO timestamp
}
```

### 2. Get Patient Name Suggestions
- **Endpoint**: `GET /api/v1/search/patients/suggestions`
- **Descripción**: Obtener sugerencias de nombres de pacientes (autocompletado)

**Entrada (Query Params):**
```typescript
{
  partial_term: string  // Término parcial (requerido, 1-100 chars)
  user_id?: string     // Filtrar por usuario (opcional)
  limit?: number       // Máximo sugerencias (1-50, default: 10)
}
```

**Salida:**
```typescript
{
  partial_term: string         // Término parcial proporcionado
  suggestions: string[]        // Array de nombres sugeridos
  total_suggestions: number    // Total de sugerencias
  limit: number               // Límite aplicado
}
```

### 3. Get Documents by Patient Name
- **Endpoint**: `GET /api/v1/search/patients/{patient_name}/documents`
- **Descripción**: Obtener todos los documentos de un paciente específico

**Entrada:**
```typescript
Path: patient_name: string    // Nombre exacto del paciente
Query: {
  user_id?: string           // Filtrar por usuario (opcional)
  limit?: number             // Máximo resultados (1-100, default: 20)
  skip?: number              // Resultados a saltar (default: 0)
}
```

**Salida:**
```typescript
FuzzySearchResponse // Misma estructura que búsqueda fuzzy
```

---

## 🔐 Tokens (`/api/v1/tokens`) {#tokens}

### 1. Get Azure Speech Token
- **Endpoint**: `GET /api/v1/tokens/speech`
- **Descripción**: Obtener token de autenticación para Azure Speech Services

**Entrada**: Ninguna

**Salida:**
```typescript
{
  access_token: string    // Token JWT para Speech Services
  token_type: string      // "Bearer"
  expires_in: number      // Segundos hasta expiración (600)
  region: string          // Región de Azure Speech
  issued_at: string       // ISO timestamp de emisión
}
```

### 2. Get Azure Storage Token
- **Endpoint**: `GET /api/v1/tokens/storage`
- **Descripción**: Obtener SAS token para acceso a Azure Storage

**Entrada**: Ninguna

**Salida:**
```typescript
{
  sas_token: string          // SAS token para Storage
  container_url: string      // URL completa del container con SAS
  base_url: string          // URL base de la cuenta de Storage
  container_name: string    // Nombre del container
  account_name: string      // Nombre de la cuenta de Storage
  expires_at: string        // ISO timestamp de expiración
  permissions: string       // Permisos del token ("rl" = read/list)
  resource_type: string     // Tipo de recurso ("container")
  issued_at: string         // ISO timestamp de emisión
}
```

### 3. Get Speech Token Info
- **Endpoint**: `GET /api/v1/tokens/speech/info`
- **Descripción**: Obtener información del token de Speech en cache

**Entrada**: Ninguna

**Salida:**
```typescript
{
  has_cached_token: boolean      // ¿Hay token en cache?
  token_expires_at: string?      // ISO timestamp de expiración
  is_token_valid: boolean        // ¿Token válido actualmente?
  speech_region: string          // Región configurada
  token_endpoint: string         // Endpoint de generación de tokens
}
```

### 4. Get Storage Token Info
- **Endpoint**: `GET /api/v1/tokens/storage/info`
- **Descripción**: Obtener información del token de Storage en cache

**Entrada**: Ninguna

**Salida:**
```typescript
{
  has_cached_token: boolean      // ¿Hay token en cache?
  token_expires_at: string?      // ISO timestamp de expiración
  is_token_valid: boolean        // ¿Token válido actualmente?
  account_name: string           // Nombre de la cuenta
  container_name: string         // Nombre del container
  base_url: string              // URL base
}
```

### 5. Get Blob URL with SAS
- **Endpoint**: `GET /api/v1/tokens/storage/blob/{blob_name}`
- **Descripción**: Obtener URL firmada para blob específico

**Entrada (Path Param):**
```typescript
{
  blob_name: string // Nombre del blob (requerido)
}
```

**Salida:**
```typescript
{
  blob_name: string      // Nombre del blob
  blob_url: string       // URL completa con SAS token
  generated_at: string   // ISO timestamp de generación
}
```

### 6. Invalidate Speech Token
- **Endpoint**: `POST /api/v1/tokens/speech/invalidate`
- **Descripción**: Invalidar token de Speech en cache

**Entrada**: Ninguna

**Salida:**
```typescript
{
  message: string // "Azure Speech token invalidated successfully"
}
```

### 7. Invalidate Storage Token
- **Endpoint**: `POST /api/v1/tokens/storage/invalidate`
- **Descripción**: Invalidar token de Storage en cache

**Entrada**: Ninguna

**Salida:**
```typescript
{
  message: string // "Azure Storage token invalidated successfully"
}
```

---

## 🏥 Health (`/`) {#health}

### 1. Root Endpoint
- **Endpoint**: `GET /`
- **Descripción**: Información básica de la API

**Entrada**: Ninguna

**Salida:**
```typescript
{
  message: string        // "TecSalud Chatbot Document Processing API"
  version: string        // Versión de la API
  status: string         // "healthy"
  timestamp: number      // Unix timestamp
  docs_url?: string      // URL de documentación (solo en desarrollo)
  api_version: string    // "v1"
}
```

### 2. Health Check
- **Endpoint**: `GET /health`
- **Descripción**: Verificación de estado del sistema

**Entrada**: Ninguna

**Salida:**
```typescript
{
  status: string         // "healthy"
  timestamp: number      // Unix timestamp
  version: string        // Versión de la API
  environment: string    // "development" | "production"
}
```

---

## 🔧 Configuración de Testing

### Variables de Entorno Necesarias
```env
# MongoDB
MONGODB_URL=mongodb://localhost:27017
MONGODB_DATABASE=tecsalud_chatbot

# Azure Storage
AZURE_STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=https;...
AZURE_STORAGE_CONTAINER_NAME=documents

# Azure Document Intelligence
AZURE_DOCUMENT_INTELLIGENCE_ENDPOINT=https://...
AZURE_DOCUMENT_INTELLIGENCE_KEY=...

# Azure Speech Services
AZURE_SPEECH_KEY=...
AZURE_SPEECH_REGION=eastus

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
CHAT_MODEL=gpt-4o-mini
```

### Códigos de Estado HTTP

| Código | Descripción |
|--------|-------------|
| 200 | OK - Operación exitosa |
| 201 | Created - Recurso creado exitosamente |
| 400 | Bad Request - Error en la entrada |
| 404 | Not Found - Recurso no encontrado |
| 500 | Internal Server Error - Error del servidor |

### Content Types

| Endpoint | Content-Type |
|----------|-------------|
| Upload endpoints | `multipart/form-data` |
| JSON endpoints | `application/json` |
| Streaming chat | `text/event-stream` |

---

**Última actualización**: 2025-07-13  
**Versión del documento**: 1.0  
**API Version**: v1 