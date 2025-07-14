# 🚀 TecSalud MVP - Guía de Integración API Frontend

> **Versión**: 2.0  
> **Fecha**: Enero 2025  
> **API Base URL**: `http://localhost:8000` (desarrollo) | `https://api.tecsalud.com` (producción)

## 📋 Índice

1. [🔧 Configuración Inicial](#configuración-inicial)
2. [📄 Gestión de Documentos](#gestión-de-documentos)
3. [💬 Sistema de Chat](#sistema-de-chat)
4. [🔍 Búsqueda Inteligente](#búsqueda-inteligente)
5. [🔐 Tokens de Autenticación](#tokens-de-autenticación)
6. [⚡ Health Check](#health-check)
7. [🛠️ Manejo de Errores](#manejo-de-errores)
8. [💡 Mejores Prácticas](#mejores-prácticas)

---

## 🔧 Configuración Inicial

### Headers Requeridos
```javascript
const apiConfig = {
  baseURL: 'http://localhost:8000',
  headers: {
    'Accept': 'application/json',
    // Para uploads usar 'Content-Type': 'multipart/form-data'
    // Para JSON usar 'Content-Type': 'application/json'
  }
}
```

### Ejemplo de Cliente HTTP
```javascript
import axios from 'axios';

const apiClient = axios.create({
  baseURL: 'http://localhost:8000',
  timeout: 30000, // 30 segundos para uploads grandes
  headers: {
    'Accept': 'application/json'
  }
});
```

---

## 📄 Gestión de Documentos

### 1. 📤 Subir Documento Individual

```http
POST /api/v1/documents/
```

**Implementación Frontend:**
```javascript
const uploadDocument = async (file, userId, description, tags) => {
  const formData = new FormData();
  formData.append('file', file);
  if (userId) formData.append('user_id', userId);
  if (description) formData.append('description', description);
  if (tags?.length) formData.append('tags', JSON.stringify(tags));

  try {
    const response = await apiClient.post('/api/v1/documents/', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      // Para mostrar progreso de upload
      onUploadProgress: (progressEvent) => {
        const percentCompleted = Math.round(
          (progressEvent.loaded * 100) / progressEvent.total
        );
        console.log(`Upload: ${percentCompleted}%`);
      }
    });
    
    return response.data;
  } catch (error) {
    console.error('Upload failed:', error.response?.data);
    throw error;
  }
};
```

**Respuesta Exitosa (201):**
```json
{
  "document_id": "507f1f77bcf86cd799439011",
  "processing_id": "proc_20250114_123456",
  "filename": "expediente_123.pdf",
  "storage_info": {
    "blob_name": "documents/507f1f77bcf86cd799439011.pdf",
    "blob_url": "https://storage.blob.core.windows.net/...",
    "container_name": "documents"
  },
  "ocr_summary": {
    "text_extracted": true,
    "page_count": 3,
    "processing_time": 2.5
  },
  "processing_status": "completed",
  "processing_timestamp": "2025-01-14T12:34:56.789Z",
  "expediente": "EXP-2025-001",
  "nombre_paciente": "GARCÍA LÓPEZ, MARÍA",
  "numero_episodio": "EP-001-2025",
  "categoria": "EMER",
  "medical_info_valid": true
}
```

### 2. 📚 Subir Múltiples Documentos

```http
POST /api/v1/documents/upload/batch
```

**Implementación Frontend:**
```javascript
const uploadBatch = async (files, userId, batchDescription) => {
  const formData = new FormData();
  
  // Agregar todos los archivos
  files.forEach(file => {
    formData.append('files', file);
  });
  
  if (userId) formData.append('user_id', userId);
  if (batchDescription) formData.append('batch_description', batchDescription);

  const response = await apiClient.post('/api/v1/documents/upload/batch', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 60000 // 1 minuto para batches grandes
  });
  
  return response.data;
};
```

### 3. 📋 Listar Documentos con Paginación

```http
GET /api/v1/documents/
```

**Implementación Frontend:**
```javascript
const getDocuments = async (params = {}) => {
  const queryParams = new URLSearchParams();
  
  if (params.userId) queryParams.append('user_id', params.userId);
  if (params.batchId) queryParams.append('batch_id', params.batchId);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.skip) queryParams.append('skip', params.skip);

  const response = await apiClient.get(`/api/v1/documents/?${queryParams}`);
  return response.data;
};

// Ejemplo de uso con paginación
const loadDocumentsPage = async (page = 1, limit = 10) => {
  const skip = (page - 1) * limit;
  return await getDocuments({ limit, skip, userId: 'current_user' });
};
```

**Respuesta con Paginación:**
```json
{
  "documents": [
    {
      "document_id": "507f1f77bcf86cd799439011",
      "filename": "expediente_123.pdf",
      "user_id": "user_001",
      "processing_status": "completed",
      "nombre_paciente": "GARCÍA LÓPEZ, MARÍA",
      "expediente": "EXP-2025-001",
      "created_at": "2025-01-14T12:34:56.789Z"
    }
  ],
  "total_found": 25,
  "limit": 10,
  "skip": 0,
  "returned_count": 10,
  "has_next": true,
  "has_prev": false,
  "current_page": 1,
  "total_pages": 3,
  "applied_filters": {
    "user_id": "user_001"
  },
  "request_id": "list_docs_20250114_123456_10_0",
  "search_timestamp": "2025-01-14T12:34:56.789Z"
}
```

### 4. 📊 Obtener Información de Documento

```http
GET /api/v1/documents/{document_id}
```

**Implementación Frontend:**
```javascript
const getDocumentInfo = async (documentId) => {
  try {
    const response = await apiClient.get(`/api/v1/documents/${documentId}`);
    return response.data;
  } catch (error) {
    if (error.response?.status === 404) {
      throw new Error('Documento no encontrado');
    }
    throw error;
  }
};
```

### 5. 🗑️ Eliminar Documento

```http
DELETE /api/v1/documents/{document_id}
```

**Implementación Frontend:**
```javascript
const deleteDocument = async (documentId) => {
  const response = await apiClient.delete(`/api/v1/documents/${documentId}`);
  return response.data;
};
```

---

## 💬 Sistema de Chat

### 1. ➕ Crear Sesión de Chat

```http
POST /api/v1/chat/sessions
```

**Implementación Frontend:**
```javascript
const createChatSession = async (userId, documentId, sessionName) => {
  try {
    const response = await apiClient.post('/api/v1/chat/sessions', {
      user_id: userId,
      document_id: documentId,
      session_name: sessionName
    });
    return response.data;
  } catch (error) {
    // Manejo específico de errores de autorización
    if (error.response?.status === 500 && 
        error.response?.data?.error_message?.error_code === 'USER_NOT_AUTHORIZED') {
      throw new Error('No tienes autorización para crear sesiones con este documento');
    }
    throw error;
  }
};
```

**Respuesta Exitosa (201):**
```json
{
  "session_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user_001",
  "document_id": "507f1f77bcf86cd799439011",
  "session_name": "Consulta Expediente EXP-2025-001",
  "is_active": true,
  "created_at": "2025-01-14T12:34:56.789Z",
  "last_interaction_at": "2025-01-14T12:34:56.789Z",
  "interaction_count": 0
}
```

**Error de Autorización (500):**
```json
{
  "error_code": "HTTP_500",
  "error_message": {
    "error_code": "USER_NOT_AUTHORIZED",
    "message": "User is not authorized to create a chat session with this document. Only the document owner can create sessions.",
    "request_id": "create_session_20250114_123456_abc123",
    "suggestion": "Please verify that you are the owner of this document or contact the document owner for access."
  },
  "timestamp": 1736852096.789
}
```

### 2. 📋 Listar Sesiones con Paginación Mejorada

```http
GET /api/v1/chat/sessions?user_id={user_id}
```

**Implementación Frontend:**
```javascript
const getChatSessions = async (params = {}) => {
  if (!params.userId) {
    throw new Error('user_id es requerido');
  }

  const queryParams = new URLSearchParams();
  queryParams.append('user_id', params.userId);
  
  if (params.documentId) queryParams.append('document_id', params.documentId);
  if (params.activeOnly !== undefined) queryParams.append('active_only', params.activeOnly);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.skip) queryParams.append('skip', params.skip);

  const response = await apiClient.get(`/api/v1/chat/sessions?${queryParams}`);
  return response.data;
};

// Hook React para paginación automática
const useChatSessions = (userId, page = 1, limit = 20) => {
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);
  const [paginationInfo, setPaginationInfo] = useState({});

  const loadSessions = async () => {
    setLoading(true);
    try {
      const skip = (page - 1) * limit;
      const data = await getChatSessions({ userId, limit, skip });
      setSessions(data.sessions);
      setPaginationInfo({
        total: data.total_found,
        hasNext: data.has_next,
        hasPrev: data.has_prev,
        currentPage: data.current_page,
        totalPages: data.total_pages
      });
    } catch (error) {
      console.error('Error loading sessions:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    if (userId) loadSessions();
  }, [userId, page, limit]);

  return { sessions, paginationInfo, loading, reload: loadSessions };
};
```

**Respuesta con Paginación Completa:**
```json
{
  "sessions": [
    {
      "session_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": "user_001",
      "document_id": "507f1f77bcf86cd799439011",
      "session_name": "Consulta Expediente EXP-2025-001",
      "is_active": true,
      "created_at": "2025-01-14T12:34:56.789Z",
      "last_interaction_at": "2025-01-14T13:45:12.456Z",
      "interaction_count": 5
    }
  ],
  "total_found": 15,
  "limit": 20,
  "skip": 0,
  "returned_count": 15,
  "has_next": false,
  "has_prev": false,
  "current_page": 1,
  "total_pages": 1,
  "applied_filters": {
    "user_id": "user_001",
    "active_only": true
  },
  "request_id": "list_sessions_20250114_123456_abc123",
  "search_timestamp": "2025-01-14T12:34:56.789Z"
}
```

### 3. 💬 Hacer Pregunta con Streaming

```http
POST /api/v1/chat/ask
```

**Implementación Frontend:**
```javascript
const askQuestion = async (sessionId, userId, documentId, question, onMessage, onError) => {
  try {
    const response = await fetch(`${apiConfig.baseURL}/api/v1/chat/ask`, {
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
      throw new Error(`HTTP ${response.status}: ${response.statusText}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop(); // Mantener línea incompleta

      for (const line of lines) {
        if (line.trim() === '') continue;
        if (!line.startsWith('data: ')) continue;

        const data = line.slice(6); // Remover "data: "
        if (data === '[DONE]') return;

        try {
          const event = JSON.parse(data);
          onMessage(event);
        } catch (e) {
          console.warn('Error parsing SSE data:', e);
        }
      }
    }
  } catch (error) {
    onError(error);
  }
};

// Componente React para Chat
const ChatComponent = ({ sessionId, userId, documentId }) => {
  const [messages, setMessages] = useState([]);
  const [currentResponse, setCurrentResponse] = useState('');
  const [question, setQuestion] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSendMessage = async () => {
    if (!question.trim()) return;

    setLoading(true);
    setCurrentResponse('');
    
    // Agregar pregunta del usuario
    const userMessage = { type: 'user', content: question, timestamp: new Date() };
    setMessages(prev => [...prev, userMessage]);
    
    const currentQuestion = question;
    setQuestion('');

    await askQuestion(
      sessionId,
      userId, 
      documentId,
      currentQuestion,
      (event) => {
        switch (event.type) {
          case 'start':
            console.log('Iniciando respuesta:', event.interaction_id);
            break;
          case 'content':
            setCurrentResponse(prev => prev + event.content);
            break;
          case 'end':
            // Agregar respuesta completa a mensajes
            setMessages(prev => [...prev, {
              type: 'assistant',
              content: currentResponse,
              interaction_id: event.interaction_id,
              timestamp: new Date()
            }]);
            setCurrentResponse('');
            setLoading(false);
            break;
          case 'error':
            console.error('Error en streaming:', event.error);
            setLoading(false);
            break;
        }
      },
      (error) => {
        console.error('Error en pregunta:', error);
        setLoading(false);
      }
    );
  };

  return (
    <div className="chat-container">
      <div className="messages">
        {messages.map((msg, index) => (
          <div key={index} className={`message ${msg.type}`}>
            {msg.content}
          </div>
        ))}
        {currentResponse && (
          <div className="message assistant streaming">
            {currentResponse}
          </div>
        )}
      </div>
      
      <div className="input-area">
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Escribe tu pregunta..."
          disabled={loading}
          onKeyPress={(e) => e.key === 'Enter' && handleSendMessage()}
        />
        <button onClick={handleSendMessage} disabled={loading || !question.trim()}>
          {loading ? 'Enviando...' : 'Enviar'}
        </button>
      </div>
    </div>
  );
};
```

### 4. 📜 Obtener Historial de Interacciones

```http
GET /api/v1/chat/sessions/{session_id}/interactions
```

**Implementación Frontend:**
```javascript
const getSessionInteractions = async (sessionId, userId, page = 1, limit = 50) => {
  const skip = (page - 1) * limit;
  const queryParams = new URLSearchParams({
    user_id: userId,
    limit: limit.toString(),
    skip: skip.toString()
  });

  const response = await apiClient.get(
    `/api/v1/chat/sessions/${sessionId}/interactions?${queryParams}`
  );
  return response.data;
};
```

### 5. 🗑️ Eliminar Sesión

```http
DELETE /api/v1/chat/sessions/{session_id}?user_id={user_id}
```

**Implementación Frontend:**
```javascript
const deleteChatSession = async (sessionId, userId) => {
  const response = await apiClient.delete(
    `/api/v1/chat/sessions/${sessionId}?user_id=${userId}`
  );
  return response.data;
};
```

### 6. 📊 Estadísticas de Chat

```http
GET /api/v1/chat/stats
```

**Implementación Frontend:**
```javascript
const getChatStats = async (params = {}) => {
  const queryParams = new URLSearchParams();
  if (params.userId) queryParams.append('user_id', params.userId);
  if (params.documentId) queryParams.append('document_id', params.documentId);
  if (params.days) queryParams.append('days', params.days);

  const response = await apiClient.get(`/api/v1/chat/stats?${queryParams}`);
  return response.data;
};
```

---

## 🔍 Búsqueda Inteligente

### 1. 🔎 Búsqueda Fuzzy de Pacientes

```http
GET /api/v1/search/patients
```

**Implementación Frontend:**
```javascript
const searchPatients = async (searchTerm, params = {}) => {
  const queryParams = new URLSearchParams();
  queryParams.append('search_term', searchTerm);
  
  if (params.userId) queryParams.append('user_id', params.userId);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.skip) queryParams.append('skip', params.skip);
  if (params.minSimilarity) queryParams.append('min_similarity', params.minSimilarity);

  const response = await apiClient.get(`/api/v1/search/patients?${queryParams}`);
  return response.data;
};

// Hook para búsqueda con debounce
const usePatientSearch = (debounceDelay = 300) => {
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [searchTerm, setSearchTerm] = useState('');

  const debouncedSearch = useCallback(
    debounce(async (term) => {
      if (term.length < 2) {
        setResults([]);
        return;
      }

      setLoading(true);
      try {
        const data = await searchPatients(term, { limit: 10 });
        setResults(data.documents);
      } catch (error) {
        console.error('Search error:', error);
        setResults([]);
      } finally {
        setLoading(false);
      }
    }, debounceDelay),
    []
  );

  useEffect(() => {
    debouncedSearch(searchTerm);
  }, [searchTerm, debouncedSearch]);

  return { results, loading, searchTerm, setSearchTerm };
};
```

### 2. 💡 Sugerencias de Autocompletado

```http
GET /api/v1/search/patients/suggestions
```

**Implementación Frontend:**
```javascript
const getPatientSuggestions = async (partialTerm, userId = null, limit = 10) => {
  const queryParams = new URLSearchParams();
  queryParams.append('partial_term', partialTerm);
  if (userId) queryParams.append('user_id', userId);
  queryParams.append('limit', limit);

  const response = await apiClient.get(`/api/v1/search/patients/suggestions?${queryParams}`);
  return response.data;
};

// Componente de autocompletado
const PatientAutocomplete = ({ onSelect, userId }) => {
  const [input, setInput] = useState('');
  const [suggestions, setSuggestions] = useState([]);
  const [showSuggestions, setShowSuggestions] = useState(false);

  const loadSuggestions = useCallback(
    debounce(async (term) => {
      if (term.length < 2) {
        setSuggestions([]);
        setShowSuggestions(false);
        return;
      }

      try {
        const data = await getPatientSuggestions(term, userId);
        setSuggestions(data.suggestions);
        setShowSuggestions(true);
      } catch (error) {
        console.error('Error loading suggestions:', error);
      }
    }, 200),
    [userId]
  );

  useEffect(() => {
    loadSuggestions(input);
  }, [input, loadSuggestions]);

  return (
    <div className="autocomplete-container">
      <input
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder="Buscar paciente..."
        onFocus={() => setShowSuggestions(suggestions.length > 0)}
        onBlur={() => setTimeout(() => setShowSuggestions(false), 200)}
      />
      
      {showSuggestions && (
        <ul className="suggestions-list">
          {suggestions.map((suggestion, index) => (
            <li
              key={index}
              onClick={() => {
                setInput(suggestion);
                setShowSuggestions(false);
                onSelect(suggestion);
              }}
            >
              {suggestion}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
};
```

### 3. 📁 Documentos por Paciente

```http
GET /api/v1/search/patients/{patient_name}/documents
```

**Implementación Frontend:**
```javascript
const getDocumentsByPatient = async (patientName, params = {}) => {
  const encodedName = encodeURIComponent(patientName);
  const queryParams = new URLSearchParams();
  
  if (params.userId) queryParams.append('user_id', params.userId);
  if (params.limit) queryParams.append('limit', params.limit);
  if (params.skip) queryParams.append('skip', params.skip);

  const response = await apiClient.get(
    `/api/v1/search/patients/${encodedName}/documents?${queryParams}`
  );
  return response.data;
};
```

---

## 🔐 Tokens de Autenticación

### 1. 🎤 Token de Azure Speech

```http
GET /api/v1/tokens/speech
```

**Implementación Frontend:**
```javascript
const getSpeechToken = async () => {
  const response = await apiClient.get('/api/v1/tokens/speech');
  return response.data;
};

// Configurar Azure Speech SDK
const initializeSpeechService = async () => {
  const tokenData = await getSpeechToken();
  
  const speechConfig = SpeechConfig.fromAuthorizationToken(
    tokenData.access_token,
    tokenData.region
  );
  
  speechConfig.speechRecognitionLanguage = 'es-ES';
  return speechConfig;
};
```

### 2. 💾 Token de Azure Storage

```http
GET /api/v1/tokens/storage
```

**Implementación Frontend:**
```javascript
const getStorageToken = async () => {
  const response = await apiClient.get('/api/v1/tokens/storage');
  return response.data;
};

// Acceso directo a archivos
const getDocumentFileUrl = async (blobName) => {
  const storageData = await getStorageToken();
  return `${storageData.base_url}/${storageData.container_name}/${blobName}?${storageData.sas_token}`;
};
```

### 3. 🔗 URL de Blob Específico

```http
GET /api/v1/tokens/storage/blob/{blob_name}
```

**Implementación Frontend:**
```javascript
const getBlobUrl = async (blobName) => {
  const response = await apiClient.get(`/api/v1/tokens/storage/blob/${blobName}`);
  return response.data.blob_url;
};

// Componente para mostrar PDF
const DocumentViewer = ({ document }) => {
  const [pdfUrl, setPdfUrl] = useState('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadPdfUrl = async () => {
      try {
        const url = await getBlobUrl(document.storage_info.blob_name);
        setPdfUrl(url);
      } catch (error) {
        console.error('Error loading PDF URL:', error);
      } finally {
        setLoading(false);
      }
    };

    loadPdfUrl();
  }, [document]);

  if (loading) return <div>Cargando documento...</div>;
  if (!pdfUrl) return <div>Error cargando documento</div>;

  return (
    <iframe
      src={pdfUrl}
      width="100%"
      height="600px"
      title={document.filename}
    />
  );
};
```

---

## ⚡ Health Check

### 1. 🏥 Estado del Sistema

```http
GET /health
```

**Implementación Frontend:**
```javascript
const checkHealth = async () => {
  try {
    const response = await apiClient.get('/health');
    return { status: 'healthy', data: response.data };
  } catch (error) {
    return { status: 'unhealthy', error: error.message };
  }
};

// Hook para monitoreo de salud
const useHealthCheck = (intervalMs = 30000) => {
  const [health, setHealth] = useState({ status: 'unknown' });

  useEffect(() => {
    const check = async () => {
      const result = await checkHealth();
      setHealth(result);
    };

    check(); // Verificación inicial
    const interval = setInterval(check, intervalMs);
    
    return () => clearInterval(interval);
  }, [intervalMs]);

  return health;
};
```

---

## 🛠️ Manejo de Errores

### Códigos de Error Comunes

```javascript
const handleApiError = (error) => {
  const status = error.response?.status;
  const data = error.response?.data;

  switch (status) {
    case 400:
      // Error de validación
      if (data?.error_message?.error_code === 'USER_NOT_AUTHORIZED') {
        return 'No tienes autorización para acceder a este documento';
      }
      return data?.error_message?.message || 'Datos inválidos';
      
    case 404:
      return 'Recurso no encontrado';
      
    case 422:
      // Error de validación de FastAPI
      const validationErrors = data?.detail?.map(err => 
        `${err.loc?.[1] || 'Campo'}: ${err.msg}`
      ).join(', ');
      return `Errores de validación: ${validationErrors}`;
      
    case 500:
      // Errores personalizados del servidor
      if (data?.error_message?.error_code === 'USER_NOT_AUTHORIZED') {
        return 'No estás autorizado para realizar esta acción con este documento';
      }
      if (data?.error_message?.error_code === 'SESSION_CREATION_FAILED') {
        return 'Error creando la sesión. Inténtalo de nuevo.';
      }
      return 'Error interno del servidor';
      
    case 503:
      return 'Servicio no disponible temporalmente';
      
    default:
      return 'Error desconocido';
  }
};

// Interceptor para manejo global de errores
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const errorMessage = handleApiError(error);
    console.error('API Error:', errorMessage, error.response?.data);
    
    // Mostrar notificación global
    showErrorNotification(errorMessage);
    
    return Promise.reject(error);
  }
);
```

### Estructura de Errores Específicos

```typescript
// Error de autorización de documento
interface DocumentAuthError {
  error_code: "HTTP_500";
  error_message: {
    error_code: "USER_NOT_AUTHORIZED";
    message: string;
    request_id: string | null;
    suggestion: string;
  };
  timestamp: number;
}

// Error de validación
interface ValidationError {
  detail: Array<{
    loc: string[];
    msg: string;
    type: string;
  }>;
}

// Error de documento no encontrado
interface NotFoundError {
  error_code: string;
  message: string;
  request_id?: string;
  suggestion?: string;
}
```

---

## 💡 Mejores Prácticas

### 1. 🔄 Manejo de Estado

```javascript
// Context para estado global
const AppContext = createContext();

export const AppProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [documents, setDocuments] = useState([]);
  const [sessions, setSessions] = useState([]);
  const [loading, setLoading] = useState(false);

  const refreshDocuments = async () => {
    if (!user?.id) return;
    
    setLoading(true);
    try {
      const data = await getDocuments({ userId: user.id });
      setDocuments(data.documents);
    } catch (error) {
      console.error('Error refreshing documents:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshSessions = async () => {
    if (!user?.id) return;
    
    try {
      const data = await getChatSessions({ userId: user.id });
      setSessions(data.sessions);
    } catch (error) {
      console.error('Error refreshing sessions:', error);
    }
  };

  return (
    <AppContext.Provider value={{
      user, setUser,
      documents, refreshDocuments,
      sessions, refreshSessions,
      loading
    }}>
      {children}
    </AppContext.Provider>
  );
};
```

### 2. 📊 Paginación Consistente

```javascript
// Hook reutilizable para paginación
const usePagination = (fetchFunction, dependencies = []) => {
  const [data, setData] = useState([]);
  const [pagination, setPagination] = useState({
    page: 1,
    limit: 20,
    total: 0,
    hasNext: false,
    hasPrev: false,
    totalPages: 1
  });
  const [loading, setLoading] = useState(false);

  const loadPage = async (page = 1, limit = 20) => {
    setLoading(true);
    try {
      const response = await fetchFunction({ 
        skip: (page - 1) * limit, 
        limit 
      });
      
      setData(response.documents || response.sessions || response.interactions);
      setPagination({
        page,
        limit,
        total: response.total_found,
        hasNext: response.has_next,
        hasPrev: response.has_prev,
        totalPages: response.total_pages
      });
    } catch (error) {
      console.error('Error loading page:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPage(1, pagination.limit);
  }, dependencies);

  return {
    data,
    pagination,
    loading,
    loadPage,
    nextPage: () => pagination.hasNext && loadPage(pagination.page + 1, pagination.limit),
    prevPage: () => pagination.hasPrev && loadPage(pagination.page - 1, pagination.limit)
  };
};
```

### 3. 🔧 Configuración de Timeouts

```javascript
// Timeouts específicos por tipo de operación
const createApiClient = () => {
  const client = axios.create({
    baseURL: process.env.REACT_APP_API_URL || 'http://localhost:8000',
    headers: {
      'Accept': 'application/json'
    }
  });

  // Interceptor para timeouts dinámicos
  client.interceptors.request.use((config) => {
    // Timeouts específicos por endpoint
    if (config.url?.includes('/upload')) {
      config.timeout = 300000; // 5 minutos para uploads
    } else if (config.url?.includes('/chat/ask')) {
      config.timeout = 120000;  // 2 minutos para chat
    } else {
      config.timeout = 30000;   // 30 segundos por defecto
    }
    
    return config;
  });

  return client;
};
```

### 4. 🎯 Optimización de Rendimiento

```javascript
// Cacheo inteligente de tokens
class TokenCache {
  constructor() {
    this.cache = new Map();
  }

  async getToken(type) {
    const cached = this.cache.get(type);
    
    if (cached && cached.expiresAt > Date.now()) {
      return cached.token;
    }

    // Obtener nuevo token
    let tokenData;
    if (type === 'speech') {
      tokenData = await getSpeechToken();
    } else if (type === 'storage') {
      tokenData = await getStorageToken();
    }

    // Cachear con expiración
    this.cache.set(type, {
      token: tokenData,
      expiresAt: Date.now() + (tokenData.expires_in * 1000) - 60000 // 1 min buffer
    });

    return tokenData;
  }
}

const tokenCache = new TokenCache();

// Debounce utility
const debounce = (func, delay) => {
  let timeoutId;
  return (...args) => {
    clearTimeout(timeoutId);
    timeoutId = setTimeout(() => func.apply(null, args), delay);
  };
};

// Virtual scrolling para listas grandes
const VirtualizedDocumentList = ({ documents, onSelectDocument }) => {
  const [visibleRange, setVisibleRange] = useState({ start: 0, end: 50 });
  const containerRef = useRef();

  const handleScroll = useCallback(
    debounce(() => {
      const container = containerRef.current;
      if (!container) return;

      const itemHeight = 80; // altura estimada por item
      const containerHeight = container.clientHeight;
      const scrollTop = container.scrollTop;

      const start = Math.floor(scrollTop / itemHeight);
      const visibleCount = Math.ceil(containerHeight / itemHeight);
      const end = Math.min(start + visibleCount + 10, documents.length); // buffer

      setVisibleRange({ start: Math.max(0, start - 10), end });
    }, 16),
    [documents.length]
  );

  const visibleDocuments = documents.slice(visibleRange.start, visibleRange.end);

  return (
    <div 
      ref={containerRef}
      className="document-list"
      style={{ height: '500px', overflowY: 'auto' }}
      onScroll={handleScroll}
    >
      <div style={{ height: visibleRange.start * 80 }} />
      {visibleDocuments.map((doc, index) => (
        <DocumentItem
          key={doc.document_id}
          document={doc}
          onClick={() => onSelectDocument(doc)}
        />
      ))}
      <div style={{ height: (documents.length - visibleRange.end) * 80 }} />
    </div>
  );
};
```

### 5. 🔒 Seguridad

```javascript
// Sanitización de inputs
const sanitizeInput = (input) => {
  if (typeof input !== 'string') return input;
  
  return input
    .trim()
    .replace(/[<>]/g, '') // Remover caracteres peligrosos
    .substring(0, 1000);   // Limitar longitud
};

// Validación de IDs
const isValidObjectId = (id) => {
  return /^[0-9a-fA-F]{24}$/.test(id);
};

const isValidUUID = (id) => {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-5][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(id);
};

// Validación antes de enviar requests
const validateChatRequest = (sessionId, userId, documentId, question) => {
  if (!isValidUUID(sessionId)) {
    throw new Error('ID de sesión inválido');
  }
  if (!userId?.trim()) {
    throw new Error('ID de usuario requerido');
  }
  if (!isValidObjectId(documentId)) {
    throw new Error('ID de documento inválido');
  }
  if (!question?.trim() || question.length < 3) {
    throw new Error('La pregunta debe tener al menos 3 caracteres');
  }
  if (question.length > 2000) {
    throw new Error('La pregunta es demasiado larga');
  }
  
  return {
    session_id: sessionId,
    user_id: userId.trim(),
    document_id: documentId,
    question: sanitizeInput(question)
  };
};
```

---

## 📋 Checklist de Integración

### ✅ Configuración Inicial
- [ ] Cliente HTTP configurado con base URL correcta
- [ ] Manejo de errores global implementado
- [ ] Timeouts configurados por tipo de operación
- [ ] Sistema de notificaciones para errores

### ✅ Documentos
- [ ] Upload individual con progress indicator
- [ ] Upload por lotes
- [ ] Listado con paginación
- [ ] Visualización de PDFs
- [ ] Eliminación con confirmación

### ✅ Chat
- [ ] Creación de sesiones con validación de autorización
- [ ] Listado de sesiones con paginación mejorada
- [ ] Chat streaming en tiempo real
- [ ] Historial de conversaciones
- [ ] Eliminación de sesiones

### ✅ Búsqueda
- [ ] Búsqueda fuzzy con debounce
- [ ] Autocompletado de pacientes
- [ ] Filtros por usuario
- [ ] Paginación de resultados

### ✅ Optimización
- [ ] Cacheo de tokens
- [ ] Virtual scrolling para listas grandes
- [ ] Debounce en búsquedas
- [ ] Lazy loading de componentes

### ✅ Seguridad
- [ ] Validación de inputs
- [ ] Sanitización de datos
- [ ] Manejo seguro de tokens
- [ ] Validación de IDs (ObjectId, UUID)

---

## 🚀 Ejemplo de Aplicación Completa

```javascript
// App.js
import React from 'react';
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom';
import { AppProvider } from './context/AppContext';
import DocumentsPage from './pages/DocumentsPage';
import ChatPage from './pages/ChatPage';
import SearchPage from './pages/SearchPage';

function App() {
  return (
    <AppProvider>
      <Router>
        <div className="app">
          <Routes>
            <Route path="/" element={<DocumentsPage />} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/search" element={<SearchPage />} />
          </Routes>
        </div>
      </Router>
    </AppProvider>
  );
}

export default App;
```

---

**🔗 Enlaces Útiles:**
- API Base URL: `http://localhost:8000`
- Documentación Swagger: `http://localhost:8000/docs` (desarrollo)
- Repositorio: [TecSalud MVP](https://github.com/josecaldasai/tecsaludmvp)

**📞 Soporte:**
- Email: [soporte@tecsalud.com](mailto:soporte@tecsalud.com)
- Slack: #tecsalud-dev

---

*Documento generado automáticamente el 14 de Enero 2025*  
*Versión API: v1.0 | Versión Documento: 2.0* 