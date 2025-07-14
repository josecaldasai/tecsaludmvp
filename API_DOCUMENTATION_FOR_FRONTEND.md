# 📚 TecSalud API - Documentación para Frontend

> **Documentación completa de integración para el equipo de frontend**

## 📋 Información General

- **Base URL**: `http://localhost:8000` (desarrollo)
- **API Version**: `v1`
- **Content-Type por defecto**: `application/json`
- **CORS**: Habilitado para desarrollo
- **Documentación interactiva**: `http://localhost:8000/docs`

---

## 🚀 Configuración Inicial

### Headers Requeridos

```javascript
const defaultHeaders = {
  'Content-Type': 'application/json',
  'Accept': 'application/json'
};

// Para uploads de archivos (multipart)
const uploadHeaders = {
  // No incluir Content-Type, el browser lo maneja automáticamente
  'Accept': 'application/json'
};
```

### Cliente HTTP Base

```javascript
const API_BASE_URL = 'http://localhost:8000';

const apiClient = {
  async request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    const config = {
      headers: options.headers || defaultHeaders,
      ...options
    };
    
    try {
      const response = await fetch(url, config);
      const data = await response.json();
      
      if (!response.ok) {
        throw new APIError(data, response.status);
      }
      
      return data;
    } catch (error) {
      console.error('API Error:', error);
      throw error;
    }
  }
};
```

### Manejo de Errores Personalizado

```javascript
class APIError extends Error {
  constructor(errorData, statusCode) {
    super(errorData.error_message?.message || errorData.message || 'API Error');
    this.name = 'APIError';
    this.statusCode = statusCode;
    this.errorCode = errorData.error_code;
    this.details = errorData.error_message || errorData;
    this.timestamp = errorData.timestamp;
    this.suggestion = errorData.error_message?.suggestion;
  }
}
```

---

## 📄 1. DOCUMENTOS - `/api/v1/documents`

### 1.1 Subir Documento Individual

```javascript
// POST /api/v1/documents/upload
async function uploadDocument(file, metadata = {}) {
  const formData = new FormData();
  formData.append('file', file);
  
  if (metadata.user_id) formData.append('user_id', metadata.user_id);
  if (metadata.description) formData.append('description', metadata.description);
  if (metadata.tags) formData.append('tags', JSON.stringify(metadata.tags));
  
  return await apiClient.request('/api/v1/documents/upload', {
    method: 'POST',
    headers: {}, // Sin Content-Type para multipart
    body: formData
  });
}

// Ejemplo de uso
const file = document.getElementById('fileInput').files[0];
const result = await uploadDocument(file, {
  user_id: 'pedro123',
  description: 'Expediente médico de emergencia',
  tags: ['emergencia', 'cardiología']
});

console.log('Documento subido:', result.document_id);
```

**Respuesta exitosa (201):**
```typescript
{
  document_id: string              // "507f1f77bcf86cd799439011"
  processing_id: string            // "proc_20250714_123456_abc123"
  filename: string                 // "documento.pdf"
  storage_info: {
    blob_name: string
    blob_url: string
    container_name: string
  }
  ocr_summary: {
    text_extracted: boolean
    page_count: number
    processing_time: number
  }
  processing_status: string        // "completed" | "failed" | "processing"
  processing_timestamp: string     // ISO timestamp
  expediente?: string              // Extraído del filename
  nombre_paciente?: string         // Extraído del filename
  numero_episodio?: string         // Extraído del filename
  categoria?: string               // "EMER" | "CONS" | etc.
  medical_info_valid: boolean      // ¿Info médica válida?
  medical_info_error?: string      // Error en parsing médico
}
```

### 1.2 Subir Múltiples Documentos (Lote)

```javascript
// POST /api/v1/documents/upload/batch
async function uploadBatch(files, metadata = {}) {
  const formData = new FormData();
  
  // Agregar todos los archivos
  files.forEach(file => formData.append('files', file));
  
  if (metadata.user_id) formData.append('user_id', metadata.user_id);
  if (metadata.batch_description) formData.append('batch_description', metadata.batch_description);
  if (metadata.batch_tags) formData.append('batch_tags', JSON.stringify(metadata.batch_tags));
  
  return await apiClient.request('/api/v1/documents/upload/batch', {
    method: 'POST',
    headers: {},
    body: formData
  });
}

// Ejemplo de uso
const files = Array.from(document.getElementById('multipleFiles').files);
const batchResult = await uploadBatch(files, {
  user_id: 'pedro123',
  batch_description: 'Expedientes del día 14/07/2025',
  batch_tags: ['lote', 'urgencias']
});
```

### 1.3 Listar Documentos

```javascript
// GET /api/v1/documents/
async function listDocuments(filters = {}) {
  const params = new URLSearchParams();
  
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.batch_id) params.append('batch_id', filters.batch_id);
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.skip) params.append('skip', filters.skip.toString());
  
  const query = params.toString() ? `?${params.toString()}` : '';
  return await apiClient.request(`/api/v1/documents/${query}`);
}

// Ejemplos de uso
const allDocs = await listDocuments();
const userDocs = await listDocuments({ user_id: 'pedro123', limit: 10 });
const pagedDocs = await listDocuments({ skip: 20, limit: 10 });
```

**Respuesta exitosa:**
```typescript
{
  documents: DocumentInfo[]        // Array de documentos
  total_found: number              // Total de documentos encontrados
  limit: number                    // Límite aplicado
  skip: number                     // Elementos saltados
  returned_count: number           // Documentos en esta respuesta
  has_next: boolean                // ¿Hay más resultados?
  has_prev: boolean                // ¿Hay resultados anteriores?
  current_page: number             // Página actual (1-based)
  total_pages: number              // Total de páginas
  applied_filters: object          // Filtros aplicados
  request_id: string               // ID de tracking
  search_timestamp: string         // Timestamp de búsqueda
}
```

### 1.4 Obtener Información de Documento

```javascript
// GET /api/v1/documents/{document_id}
async function getDocument(documentId) {
  return await apiClient.request(`/api/v1/documents/${documentId}`);
}

// Ejemplo de uso
const docInfo = await getDocument('507f1f77bcf86cd799439011');
console.log('Texto extraído:', docInfo.extracted_text);
```

### 1.5 Eliminar Documento

```javascript
// DELETE /api/v1/documents/{document_id}
async function deleteDocument(documentId) {
  return await apiClient.request(`/api/v1/documents/${documentId}`, {
    method: 'DELETE'
  });
}

// Ejemplo de uso
const result = await deleteDocument('507f1f77bcf86cd799439011');
console.log('Eliminado:', result.success);
```

---

## 💬 2. CHAT - `/api/v1/chat`

### 2.1 Crear Sesión de Chat

```javascript
// POST /api/v1/chat/sessions
async function createChatSession(userId, documentId, sessionName) {
  return await apiClient.request('/api/v1/chat/sessions', {
    method: 'POST',
    body: JSON.stringify({
      user_id: userId,
      document_id: documentId,
      session_name: sessionName || undefined
    })
  });
}

// Ejemplo de uso
const session = await createChatSession(
  'pedro123', 
  '507f1f77bcf86cd799439011',
  'Consulta sobre radiografía'
);
console.log('Sesión creada:', session.session_id);
```

### 2.2 Listar Sesiones de Chat

```javascript
// GET /api/v1/chat/sessions
async function listChatSessions(userId, filters = {}) {
  const params = new URLSearchParams({ user_id: userId });
  
  if (filters.document_id) params.append('document_id', filters.document_id);
  if (filters.active_only !== undefined) params.append('active_only', filters.active_only);
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.skip) params.append('skip', filters.skip.toString());
  
  return await apiClient.request(`/api/v1/chat/sessions?${params.toString()}`);
}

// Ejemplos de uso
const allSessions = await listChatSessions('pedro123');
const activeSessions = await listChatSessions('pedro123', { active_only: true });
const docSessions = await listChatSessions('pedro123', { 
  document_id: '507f1f77bcf86cd799439011' 
});
```

### 2.3 Preguntar (Streaming)

```javascript
// POST /api/v1/chat/ask (Server-Sent Events)
async function askQuestion(sessionId, userId, documentId, question, onChunk, onComplete, onError) {
  const response = await fetch(`${API_BASE_URL}/api/v1/chat/ask`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'Accept': 'text/event-stream'
    },
    body: JSON.stringify({
      session_id: sessionId,
      user_id: userId,
      document_id: documentId,
      question: question
    })
  });

  if (!response.ok) {
    throw new APIError(await response.json(), response.status);
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = '';

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Guardar línea incompleta

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          try {
            const data = JSON.parse(line.slice(6));
            
            switch (data.type) {
              case 'start':
                console.log('Respuesta iniciada:', data.interaction_id);
                break;
              case 'content':
                onChunk(data.content, data.interaction_id);
                break;
              case 'end':
                onComplete(data.interaction_id);
                return;
              case 'error':
                onError(new Error(data.error));
                return;
            }
          } catch (e) {
            console.warn('Error parsing SSE data:', e);
          }
        }
      }
    }
  } finally {
    reader.releaseLock();
  }
}

// Ejemplo de uso con React
function ChatComponent() {
  const [response, setResponse] = useState('');
  const [isLoading, setIsLoading] = useState(false);

  const handleAsk = async (question) => {
    setIsLoading(true);
    setResponse('');

    await askQuestion(
      sessionId,
      userId,
      documentId,
      question,
      (chunk) => setResponse(prev => prev + chunk), // onChunk
      () => setIsLoading(false), // onComplete
      (error) => {
        setIsLoading(false);
        console.error('Chat error:', error);
      }
    );
  };

  return (
    <div>
      <div>{response}</div>
      {isLoading && <div>Generando respuesta...</div>}
    </div>
  );
}
```

### 2.4 Obtener Interacciones de Sesión

```javascript
// GET /api/v1/chat/sessions/{session_id}/interactions
async function getSessionInteractions(sessionId, userId, pagination = {}) {
  const params = new URLSearchParams({ user_id: userId });
  
  if (pagination.limit) params.append('limit', pagination.limit.toString());
  if (pagination.skip) params.append('skip', pagination.skip.toString());
  
  return await apiClient.request(
    `/api/v1/chat/sessions/${sessionId}/interactions?${params.toString()}`
  );
}

// Ejemplo de uso
const interactions = await getSessionInteractions('session-123', 'pedro123');
interactions.interactions.forEach(interaction => {
  console.log('Q:', interaction.question);
  console.log('A:', interaction.response);
});
```

### 2.5 Eliminar Sesión

```javascript
// DELETE /api/v1/chat/sessions/{session_id}
async function deleteChatSession(sessionId, userId) {
  return await apiClient.request(
    `/api/v1/chat/sessions/${sessionId}?user_id=${userId}`,
    { method: 'DELETE' }
  );
}

// Ejemplo de uso
const result = await deleteChatSession('session-123', 'pedro123');
console.log(`Sesión eliminada. Interacciones eliminadas: ${result.interactions_deleted}`);
```

---

## 🔍 3. BÚSQUEDA - `/api/v1/search`

### 3.1 Búsqueda Fuzzy de Pacientes

```javascript
// GET /api/v1/search/patients
async function searchPatients(searchTerm, filters = {}) {
  const params = new URLSearchParams({ search_term: searchTerm });
  
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.skip) params.append('skip', filters.skip.toString());
  if (filters.min_similarity) params.append('min_similarity', filters.min_similarity.toString());
  
  return await apiClient.request(`/api/v1/search/patients?${params.toString()}`);
}

// Ejemplo de uso
const results = await searchPatients('maria garcia', {
  user_id: 'pedro123',
  min_similarity: 0.5,
  limit: 10
});

results.documents.forEach(doc => {
  console.log(`${doc.nombre_paciente} (Score: ${doc.similarity_score})`);
});
```

### 3.2 Sugerencias de Autocompletado

```javascript
// GET /api/v1/search/patients/suggestions
async function getPatientSuggestions(partialTerm, userId = null, limit = 10) {
  const params = new URLSearchParams({ 
    partial_term: partialTerm,
    limit: limit.toString()
  });
  
  if (userId) params.append('user_id', userId);
  
  return await apiClient.request(`/api/v1/search/patients/suggestions?${params.toString()}`);
}

// Ejemplo para autocompletado en tiempo real
function setupAutoComplete(inputElement, userId) {
  let timeout;
  
  inputElement.addEventListener('input', (e) => {
    clearTimeout(timeout);
    const value = e.target.value;
    
    if (value.length >= 2) {
      timeout = setTimeout(async () => {
        try {
          const suggestions = await getPatientSuggestions(value, userId);
          displaySuggestions(suggestions.suggestions);
        } catch (error) {
          console.warn('Error getting suggestions:', error);
        }
      }, 300);
    }
  });
}
```

### 3.3 Documentos por Paciente

```javascript
// GET /api/v1/search/patients/{patient_name}/documents
async function getDocumentsByPatient(patientName, filters = {}) {
  const params = new URLSearchParams();
  
  if (filters.user_id) params.append('user_id', filters.user_id);
  if (filters.limit) params.append('limit', filters.limit.toString());
  if (filters.skip) params.append('skip', filters.skip.toString());
  
  const query = params.toString() ? `?${params.toString()}` : '';
  const encodedName = encodeURIComponent(patientName);
  
  return await apiClient.request(`/api/v1/search/patients/${encodedName}/documents${query}`);
}

// Ejemplo de uso
const patientDocs = await getDocumentsByPatient('GARCÍA, MARÍA DE LOS ÁNGELES');
console.log(`Encontrados ${patientDocs.total_found} documentos para el paciente`);
```

---

## 🔐 4. TOKENS - `/api/v1/tokens`

### 4.1 Token de Azure Speech

```javascript
// GET /api/v1/tokens/speech
async function getSpeechToken() {
  return await apiClient.request('/api/v1/tokens/speech');
}

// Ejemplo de uso con Web Speech API
async function setupSpeechRecognition() {
  const tokenData = await getSpeechToken();
  
  // Configurar Azure Speech SDK o Web Speech API
  const speechConfig = {
    authorizationToken: tokenData.access_token,
    region: tokenData.region
  };
  
  return speechConfig;
}
```

### 4.2 Token de Azure Storage

```javascript
// GET /api/v1/tokens/storage
async function getStorageToken() {
  return await apiClient.request('/api/v1/tokens/storage');
}

// Ejemplo de uso para acceso directo a blobs
async function getDocumentBlob(blobName) {
  const storageToken = await getStorageToken();
  const blobUrl = `${storageToken.container_url}/${blobName}`;
  
  const response = await fetch(blobUrl);
  return response.blob();
}
```

---

## 🏥 5. HEALTH - `/`

### 5.1 Estado del Sistema

```javascript
// GET /health
async function checkHealth() {
  return await apiClient.request('/health');
}

// GET /
async function getApiInfo() {
  return await apiClient.request('/');
}

// Ejemplo de monitoreo de salud
async function monitorSystemHealth() {
  try {
    const health = await checkHealth();
    console.log('Sistema saludable:', health.status === 'healthy');
    return health.status === 'healthy';
  } catch (error) {
    console.error('Sistema no disponible:', error);
    return false;
  }
}
```

---

## ⚠️ Manejo de Errores

### Códigos de Estado HTTP

| Código | Significado | Acción Recomendada |
|--------|-------------|-------------------|
| 200 | OK | Procesar respuesta normalmente |
| 201 | Created | Recurso creado exitosamente |
| 400 | Bad Request | Verificar parámetros de entrada |
| 403 | Forbidden | Usuario sin permisos |
| 404 | Not Found | Recurso no existe |
| 409 | Conflict | Recurso no listo o conflicto |
| 422 | Validation Error | Error de validación de FastAPI |
| 500 | Server Error | Error interno del servidor |
| 503 | Service Unavailable | Servicio temporalmente no disponible |

### Estructura de Errores

**Formato estándar:**
```typescript
{
  error_code: string           // "HTTP_400", "HTTP_404", etc.
  error_message: {
    error_code: string         // "INVALID_DOCUMENT_ID_FORMAT"
    message: string            // Mensaje descriptivo
    request_id: string         // ID para tracking
    suggestion: string         // Sugerencia para solucionar
    // ... campos específicos del error
  }
  timestamp: number           // Unix timestamp
}
```

**Formato especial para autorización:**
```typescript
{
  error_code: "HTTP_500"
  error_message: {
    error_code: "USER_NOT_AUTHORIZED"
    message: "User is not authorized to create a chat session with this document..."
    request_id: string
    suggestion: "Please verify that you are the owner..."
  }
  timestamp: number
}
```

### Implementación de Manejo de Errores

```javascript
function handleAPIError(error) {
  if (error instanceof APIError) {
    switch (error.statusCode) {
      case 400:
        if (error.details.error_code === 'VALIDATION_ERROR') {
          showValidationError(error.details.message);
        } else if (error.details.error_code === 'INVALID_DOCUMENT_ID_FORMAT') {
          showMessage('Formato de ID inválido', 'error');
        }
        break;
        
      case 403:
        showMessage('No tienes permisos para esta acción', 'warning');
        break;
        
      case 404:
        showMessage('Recurso no encontrado', 'info');
        break;
        
      case 409:
        if (error.details.error_code === 'DOCUMENT_NOT_READY') {
          showMessage('Documento aún procesándose. Intenta más tarde.', 'info');
        }
        break;
        
      case 500:
        if (error.details.error_code === 'USER_NOT_AUTHORIZED') {
          showMessage('No estás autorizado para acceder a este documento', 'error');
        } else {
          showMessage('Error interno del servidor', 'error');
        }
        break;
        
      case 503:
        showMessage('Servicio temporalmente no disponible', 'warning');
        // Implementar retry automático
        setTimeout(() => retryLastOperation(), 5000);
        break;
        
      default:
        showMessage(`Error: ${error.message}`, 'error');
    }
  } else {
    showMessage('Error de conexión', 'error');
  }
}
```

---

## 📝 Casos de Uso Comunes

### 1. Flujo Completo de Upload y Chat

```javascript
async function completeDocumentWorkflow(file, userId) {
  try {
    // 1. Subir documento
    showStatus('Subiendo documento...');
    const uploadResult = await uploadDocument(file, { user_id: userId });
    
    // 2. Verificar que está procesado
    if (uploadResult.processing_status !== 'completed') {
      showStatus('Documento procesándose...');
      // Implementar polling o WebSocket para status updates
      await waitForProcessing(uploadResult.document_id);
    }
    
    // 3. Crear sesión de chat
    showStatus('Creando sesión de chat...');
    const session = await createChatSession(
      userId, 
      uploadResult.document_id,
      `Chat sobre ${uploadResult.filename}`
    );
    
    // 4. Listo para hacer preguntas
    showStatus('¡Listo para chatear!');
    return {
      document: uploadResult,
      session: session
    };
    
  } catch (error) {
    handleAPIError(error);
    throw error;
  }
}
```

### 2. Búsqueda y Selección de Paciente

```javascript
async function patientSearchWorkflow(userId) {
  // Setup autocompletado
  const searchInput = document.getElementById('patientSearch');
  setupAutoComplete(searchInput, userId);
  
  // Búsqueda al enviar
  searchInput.addEventListener('change', async (e) => {
    const searchTerm = e.target.value;
    
    if (searchTerm.length >= 3) {
      try {
        const results = await searchPatients(searchTerm, { user_id: userId });
        displaySearchResults(results);
      } catch (error) {
        handleAPIError(error);
      }
    }
  });
}

function displaySearchResults(results) {
  const container = document.getElementById('searchResults');
  container.innerHTML = '';
  
  results.documents.forEach(doc => {
    const element = document.createElement('div');
    element.className = 'search-result';
    element.innerHTML = `
      <h3>${doc.nombre_paciente}</h3>
      <p>Expediente: ${doc.expediente}</p>
      <p>Similitud: ${(doc.similarity_score * 100).toFixed(1)}%</p>
      <button onclick="selectDocument('${doc.document_id}')">Seleccionar</button>
    `;
    container.appendChild(element);
  });
}
```

### 3. Chat Interactivo con Streaming

```javascript
class ChatInterface {
  constructor(sessionId, userId, documentId) {
    this.sessionId = sessionId;
    this.userId = userId;
    this.documentId = documentId;
    this.isResponding = false;
  }
  
  async sendMessage(question) {
    if (this.isResponding) return;
    
    this.isResponding = true;
    this.addMessage('user', question);
    
    const responseElement = this.addMessage('assistant', '');
    this.showTypingIndicator(responseElement);
    
    try {
      await askQuestion(
        this.sessionId,
        this.userId,
        this.documentId,
        question,
        (chunk) => this.appendToResponse(responseElement, chunk),
        () => this.onResponseComplete(responseElement),
        (error) => this.onResponseError(responseElement, error)
      );
    } catch (error) {
      this.onResponseError(responseElement, error);
    }
  }
  
  addMessage(sender, content) {
    const container = document.getElementById('chatMessages');
    const element = document.createElement('div');
    element.className = `message ${sender}`;
    element.innerHTML = `<div class="content">${content}</div>`;
    container.appendChild(element);
    container.scrollTop = container.scrollHeight;
    return element.querySelector('.content');
  }
  
  appendToResponse(element, chunk) {
    element.textContent += chunk;
  }
  
  onResponseComplete(element) {
    this.hideTypingIndicator(element);
    this.isResponding = false;
  }
  
  onResponseError(element, error) {
    this.hideTypingIndicator(element);
    element.textContent = 'Error generando respuesta. Intenta nuevamente.';
    element.className += ' error';
    this.isResponding = false;
    handleAPIError(error);
  }
  
  showTypingIndicator(element) {
    element.innerHTML = '<div class="typing-indicator">Generando respuesta...</div>';
  }
  
  hideTypingIndicator(element) {
    const indicator = element.querySelector('.typing-indicator');
    if (indicator) indicator.remove();
  }
}
```

---

## 🔧 Utilidades Auxiliares

### Validación de Entrada

```javascript
const validators = {
  documentId: (id) => /^[a-f\d]{24}$/.test(id),
  userId: (id) => id && id.length > 0 && id.length <= 100,
  filename: (name) => name && name.length > 0,
  question: (text) => text && text.trim().length >= 3
};

function validateInput(type, value) {
  const validator = validators[type];
  if (!validator) throw new Error(`No validator for type: ${type}`);
  return validator(value);
}
```

### Formateo de Respuestas

```javascript
const formatters = {
  fileSize: (bytes) => {
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    if (bytes === 0) return '0 Bytes';
    const i = Math.floor(Math.log(bytes) / Math.log(1024));
    return Math.round(bytes / Math.pow(1024, i) * 100) / 100 + ' ' + sizes[i];
  },
  
  timestamp: (isoString) => {
    return new Date(isoString).toLocaleString('es-ES', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  },
  
  similarity: (score) => `${(score * 100).toFixed(1)}%`
};
```

---

## 🚀 Componentes React de Ejemplo

### Hook Personalizado para API

```jsx
import { useState, useCallback } from 'react';

function useAPI() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  
  const callAPI = useCallback(async (apiFunction) => {
    setLoading(true);
    setError(null);
    
    try {
      const result = await apiFunction();
      setLoading(false);
      return result;
    } catch (err) {
      setError(err);
      setLoading(false);
      throw err;
    }
  }, []);
  
  return { loading, error, callAPI };
}
```

### Componente de Upload

```jsx
import React, { useState } from 'react';

function DocumentUploader({ userId, onUploadSuccess }) {
  const [files, setFiles] = useState([]);
  const { loading, error, callAPI } = useAPI();
  
  const handleUpload = async () => {
    if (files.length === 0) return;
    
    try {
      const results = await Promise.all(
        files.map(file => 
          callAPI(() => uploadDocument(file, { user_id: userId }))
        )
      );
      
      onUploadSuccess(results);
      setFiles([]);
    } catch (err) {
      console.error('Upload failed:', err);
    }
  };
  
  return (
    <div className="document-uploader">
      <input
        type="file"
        multiple
        accept=".pdf,.png,.jpg,.jpeg"
        onChange={(e) => setFiles(Array.from(e.target.files))}
      />
      
      {files.length > 0 && (
        <div>
          <p>{files.length} archivo(s) seleccionado(s)</p>
          <button onClick={handleUpload} disabled={loading}>
            {loading ? 'Subiendo...' : 'Subir Documentos'}
          </button>
        </div>
      )}
      
      {error && (
        <div className="error">
          Error: {error.message}
        </div>
      )}
    </div>
  );
}
```

---

## 📊 Mejores Prácticas

### 1. Gestión de Estado

```javascript
// Usar un store global para datos compartidos
const appStore = {
  currentUser: null,
  activeSession: null,
  documents: [],
  
  setCurrentUser(user) {
    this.currentUser = user;
    localStorage.setItem('currentUser', JSON.stringify(user));
  },
  
  setActiveSession(session) {
    this.activeSession = session;
    sessionStorage.setItem('activeSession', JSON.stringify(session));
  }
};
```

### 2. Caché de Respuestas

```javascript
const responseCache = new Map();

async function cachedRequest(key, apiFunction, ttl = 300000) { // 5min TTL
  const cached = responseCache.get(key);
  
  if (cached && Date.now() - cached.timestamp < ttl) {
    return cached.data;
  }
  
  const data = await apiFunction();
  responseCache.set(key, { data, timestamp: Date.now() });
  
  return data;
}

// Uso
const documents = await cachedRequest(
  `documents-${userId}`,
  () => listDocuments({ user_id: userId })
);
```

### 3. Retry Automático

```javascript
async function retryableRequest(apiFunction, maxRetries = 3, delay = 1000) {
  for (let i = 0; i <= maxRetries; i++) {
    try {
      return await apiFunction();
    } catch (error) {
      if (i === maxRetries || error.statusCode < 500) {
        throw error;
      }
      
      await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, i)));
    }
  }
}
```

---

## ⚡ Optimizaciones de Rendimiento

### 1. Lazy Loading de Documentos

```javascript
function useInfiniteDocuments(userId) {
  const [documents, setDocuments] = useState([]);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);
  
  const loadMore = useCallback(async () => {
    if (loading || !hasMore) return;
    
    setLoading(true);
    try {
      const result = await listDocuments({
        user_id: userId,
        skip: documents.length,
        limit: 20
      });
      
      setDocuments(prev => [...prev, ...result.documents]);
      setHasMore(result.has_next);
    } catch (error) {
      console.error('Error loading documents:', error);
    } finally {
      setLoading(false);
    }
  }, [userId, documents.length, loading, hasMore]);
  
  return { documents, loadMore, loading, hasMore };
}
```

### 2. Debounce para Búsquedas

```javascript
function useDebounce(value, delay) {
  const [debouncedValue, setDebouncedValue] = useState(value);
  
  useEffect(() => {
    const handler = setTimeout(() => setDebouncedValue(value), delay);
    return () => clearTimeout(handler);
  }, [value, delay]);
  
  return debouncedValue;
}

// Uso en componente de búsqueda
function PatientSearch() {
  const [searchTerm, setSearchTerm] = useState('');
  const debouncedSearchTerm = useDebounce(searchTerm, 300);
  
  useEffect(() => {
    if (debouncedSearchTerm.length >= 3) {
      performSearch(debouncedSearchTerm);
    }
  }, [debouncedSearchTerm]);
}
```

---

**🎯 Esta documentación te proporciona todo lo necesario para integrar exitosamente con la API de TecSalud. Para dudas específicas, consulta la documentación interactiva en `/docs` o contacta al equipo de backend.** 