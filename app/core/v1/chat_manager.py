"""Chat Manager for handling Azure OpenAI conversations with streaming."""


from typing import Dict, Any, List, Optional, AsyncGenerator, Tuple
from datetime import datetime

from openai import AsyncAzureOpenAI
from openai.types.chat import ChatCompletion, ChatCompletionChunk
import tiktoken

from app.settings.v1.openai import OpenAISettings
from app.core.v1.exceptions import ChatException
from app.core.v1.log_manager import LogManager


class ChatManager:
    """
    Chat Manager for handling Azure OpenAI conversations with streaming support.
    """
    
    def __init__(self):
        """Initialize Chat Manager with Azure OpenAI client."""
        self.logger = LogManager(__name__)
        
        # Get OpenAI configuration
        openai_settings = OpenAISettings()
        
        # Initialize Azure OpenAI client
        self.client = AsyncAzureOpenAI(
            api_key=openai_settings.AZURE_OPENAI_API_KEY,
            api_version="2024-10-21",
            azure_endpoint=openai_settings.AZURE_OPENAI_ENDPOINT
        )
        
        # Chat configuration
        self.chat_model = openai_settings.CHAT_MODEL
        self.max_tokens = openai_settings.MAX_TOKENS
        self.temperature = openai_settings.TEMPERATURE
        self.max_conversation_history = openai_settings.MAX_CONVERSATION_HISTORY
        self.context_window_size = openai_settings.CONTEXT_WINDOW_SIZE
        
        # Initialize tiktoken encoder for token counting
        try:
            self.tiktoken_encoder = tiktoken.encoding_for_model(self.chat_model)
        except KeyError:
            # Fallback to gpt-4 encoding if model not found
            self.tiktoken_encoder = tiktoken.encoding_for_model("gpt-4")
        
        # System prompt template
        self.system_prompt_template = """Eres un asistente médico especializado de TecSalud que ayuda a los usuarios a entender y analizar documentos médicos.

CONTEXTO DEL DOCUMENTO:
{document_content}

INFORMACIÓN MÉDICA:
- Expediente: {expediente}
- Paciente: {nombre_paciente}
- Episodio: {numero_episodio}
- Categoría: {categoria}

INSTRUCCIONES:
1. Responde únicamente basándote en la información del documento proporcionado
2. Sé preciso y profesional en tus respuestas médicas
3. Si la pregunta no puede responderse con la información disponible, indícalo claramente
4. Mantén la confidencialidad y privacidad médica
5. Proporciona explicaciones claras y comprensibles
6. Si hay términos médicos complejos, explícalos de manera sencilla

Responde de manera útil y precisa a las preguntas del usuario sobre este documento médico."""
        
        self.logger.info("Chat Manager initialized successfully")
    
    def _prepare_system_prompt(self, document_content: str, medical_info: Dict[str, Any]) -> str:
        """
        Prepare system prompt with document content and medical information.
        
        Args:
            document_content: Extracted text from the document
            medical_info: Medical information from document
            
        Returns:
            Formatted system prompt
        """
        return self.system_prompt_template.format(
            document_content=document_content,
            expediente=medical_info.get("expediente", "N/A"),
            nombre_paciente=medical_info.get("nombre_paciente", "N/A"),
            numero_episodio=medical_info.get("numero_episodio", "N/A"),
            categoria=medical_info.get("categoria", "N/A")
        )
    
    def _prepare_messages(
        self, 
        system_prompt: str, 
        conversation_history: List[Dict[str, Any]], 
        user_question: str
    ) -> List[Dict[str, str]]:
        """
        Prepare messages for OpenAI chat completion.
        
        Args:
            system_prompt: System prompt with document context
            conversation_history: Previous conversation messages
            user_question: Current user question
            
        Returns:
            Formatted messages for OpenAI
        """
        messages = [{"role": "system", "content": system_prompt}]
        
        # Add conversation history (limit to max_conversation_history)
        recent_history = conversation_history[-self.max_conversation_history:] if conversation_history else []
        
        for interaction in recent_history:
            messages.append({"role": "user", "content": interaction.get("question", "")})
            messages.append({"role": "assistant", "content": interaction.get("response", "")})
        
        # Add current user question
        messages.append({"role": "user", "content": user_question})
        
        return messages
    
    def _calculate_token_count(self, messages: List[Dict[str, str]]) -> int:
        """
        Calculate actual token count for messages using tiktoken.
        
        Args:
            messages: List of messages
            
        Returns:
            Actual token count
        """
        try:
            # Calculate tokens for each message
            total_tokens = 0
            
            for message in messages:
                # Count tokens for role and content
                role_tokens = len(self.tiktoken_encoder.encode(message["role"]))
                content_tokens = len(self.tiktoken_encoder.encode(message["content"]))
                
                # Add overhead for message formatting (OpenAI uses ~4 tokens per message)
                message_tokens = role_tokens + content_tokens + 4
                total_tokens += message_tokens
            
            # Add tokens for chat completion formatting
            total_tokens += 3  # Every reply is primed with assistant
            
            return total_tokens
            
        except Exception as e:
            self.logger.warning(f"Error calculating token count: {e}")
            # Fallback to character-based estimation
            total_chars = sum(len(msg["content"]) for msg in messages)
            return total_chars // 4
    
    def _truncate_messages(self, messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
        """
        Truncate messages if they exceed context window.
        
        Args:
            messages: List of messages
            
        Returns:
            Truncated messages
        """
        while self._calculate_token_count(messages) > self.context_window_size and len(messages) > 2:
            # Remove oldest conversation (keep system prompt and current question)
            if len(messages) > 2:
                # Remove the oldest user-assistant pair
                messages.pop(1)  # Remove first user message after system
                if len(messages) > 2:
                    messages.pop(1)  # Remove corresponding assistant message
        
        return messages
    
    async def stream_chat_response(
        self,
        user_question: str,
        document_content: str,
        medical_info: Dict[str, Any],
        conversation_history: List[Dict[str, Any]] = None
    ) -> AsyncGenerator[Tuple[str, bool], None]:
        """
        Stream chat response from Azure OpenAI.
        
        Args:
            user_question: User's question
            document_content: Extracted text from document
            medical_info: Medical information from document
            conversation_history: Previous conversation messages
            
        Yields:
            Tuple[str, bool]: (chunk_content, is_final)
        """
        try:
            self.logger.info(
                "Starting streaming chat response",
                question_length=len(user_question),
                document_content_length=len(document_content),
                history_count=len(conversation_history) if conversation_history else 0
            )
            
            # Prepare system prompt with document context
            system_prompt = self._prepare_system_prompt(document_content, medical_info)
            
            # Prepare messages
            messages = self._prepare_messages(
                system_prompt, 
                conversation_history or [], 
                user_question
            )
            
            # Truncate if necessary
            messages = self._truncate_messages(messages)
            
            # Log token estimation
            estimated_tokens = self._calculate_token_count(messages)
            print(messages)
            self.logger.info(f"Estimated tokens: {estimated_tokens}")
            
            # Create streaming chat completion
            stream = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature,
                stream=True
            )
            
            full_response = ""
            async for chunk in stream:
                if chunk.choices and chunk.choices[0].delta.content:
                    content = chunk.choices[0].delta.content
                    full_response += content
                    yield content, False
            
            # Yield final marker
            yield "", True
            
            self.logger.info(
                "Streaming chat response completed",
                response_length=len(full_response),
                estimated_tokens_used=self._calculate_token_count([{"content": full_response}])
            )
            
        except Exception as err:
            self.logger.error(f"Error in streaming chat response: {err}")
            raise ChatException(f"Chat streaming failed: {err}") from err
    
    async def get_chat_response(
        self,
        user_question: str,
        document_content: str,
        medical_info: Dict[str, Any],
        conversation_history: List[Dict[str, Any]] = None
    ) -> str:
        """
        Get complete chat response (non-streaming).
        
        Args:
            user_question: User's question
            document_content: Extracted text from document
            medical_info: Medical information from document
            conversation_history: Previous conversation messages
            
        Returns:
            Complete chat response
        """
        try:
            self.logger.info(
                "Getting complete chat response",
                question_length=len(user_question),
                document_content_length=len(document_content)
            )
            
            # Prepare system prompt with document context
            system_prompt = self._prepare_system_prompt(document_content, medical_info)
            
            # Prepare messages
            messages = self._prepare_messages(
                system_prompt, 
                conversation_history or [], 
                user_question
            )
            
            # Truncate if necessary
            messages = self._truncate_messages(messages)
            
            # Create chat completion
            response = await self.client.chat.completions.create(
                model=self.chat_model,
                messages=messages,
                max_tokens=self.max_tokens,
                temperature=self.temperature
            )
            
            if response.choices and response.choices[0].message.content:
                content = response.choices[0].message.content
                
                self.logger.info(
                    "Chat response completed",
                    response_length=len(content),
                    tokens_used=response.usage.total_tokens if response.usage else 0
                )
                
                return content
            else:
                raise ChatException("No response content received from OpenAI")
                
        except Exception as err:
            self.logger.error(f"Error getting chat response: {err}")
            raise ChatException(f"Chat completion failed: {err}") from err
    
    def validate_chat_input(self, user_question: str, document_content: str) -> bool:
        """
        Validate chat input parameters.
        
        Args:
            user_question: User's question
            document_content: Document content
            
        Returns:
            True if valid, raises exception if not
        """
        if not user_question or not user_question.strip():
            raise ChatException("User question cannot be empty")
        
        if not document_content or not document_content.strip():
            raise ChatException("Document content cannot be empty")
        
        if len(user_question) > 2000:  # Reasonable limit for questions
            raise ChatException("User question is too long (max 2000 characters)")
        
        return True 