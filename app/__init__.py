"""Chatbot Inteligente para Expedientes con GenAI.

Este proyecto implementa un chatbot inteligente que permite interactuar
con expedientes médicos utilizando tecnologías de inteligencia artificial
generativa (GenAI).

Características principales:
- Carga y procesamiento de documentos médicos
- OCR con Azure Document Intelligence
- Almacenamiento en MongoDB
- Integración con Azure Storage Account
"""

__version__ = "1.0.0"
__author__ = "TecSalud Team"
__email__ = "tech@tecsalud.com"

# Configuración para documentación OpenAPI
TITLE = "Chatbot Inteligente para Expedientes"
DESCRIPTION = """
API robusta para chatbot inteligente que permite cargar y procesar documentos médicos,
realizar OCR con Azure Document Intelligence y almacenar la información en MongoDB.

## Características

* **Carga de documentos**: Permite cargar uno o más documentos médicos
* **OCR avanzado**: Procesamiento con Azure Document Intelligence modelo read
* **Almacenamiento seguro**: Documentos en Azure Storage Account
* **Base de datos**: Metadata y contenido en MongoDB
* **Arquitectura escalable**: Diseño modular y versionado
"""

VERSION = "1.0.0"
CONTACT = {
    "name": "TecSalud Team",
    "email": "tech@tecsalud.com",
}

TAGS_METADATA = [
    {
        "name": "documents",
        "description": "Operaciones relacionadas con la carga y procesamiento de documentos médicos",
    },
    {
        "name": "chat", 
        "description": "Sistema de chat inteligente para preguntas sobre documentos médicos con Azure OpenAI",
    },
    {
        "name": "health",
        "description": "Endpoints para verificar el estado de la aplicación",
    },
] 