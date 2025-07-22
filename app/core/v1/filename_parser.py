"""Parser para extraer información médica del nombre del archivo."""

import re
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

from app.core.v1.exceptions import (
    InvalidMedicalFilenameFormatException,
    MedicalFilenameParsingException
)

logger = logging.getLogger(__name__)

@dataclass
class MedicalFileInfo:
    """Información médica extraída del nombre del archivo."""
    expediente: str
    nombre_paciente: str
    numero_episodio: str
    categoria: str
    is_valid: bool = True
    error_message: Optional[str] = None

class MedicalFilenameParser:
    """Parser para extraer información médica del nombre del archivo."""
    
    def __init__(self):
        # Patrón para archivos médicos: {expediente}_{nombre_paciente}_{numero_episodio}_{categoria}.pdf
        # Sin re.IGNORECASE para mantener exactitud en el formato
        # Categoría puede tener 3-4 caracteres (LAB, RAD, UCI vs EMER, CONS, etc.)
        # Número de episodio: 10 dígitos (formato real usado en el sistema médico)
        self.medical_pattern = re.compile(
            r'^(\d{10})_([A-ZÁÉÍÓÚÑÜ\s,]+)_(\d{10})_([A-Z]{3,4})\.pdf$'
        )
        
        # Categorías médicas válidas
        self.valid_categories = {
            "EMER": "Emergencia",
            "CONS": "Consulta",
            "LAB": "Laboratorio", 
            "RAD": "Radiología",
            "CIRC": "Cirugía",
            "HOSP": "Hospitalización",
            "UCI": "Unidad de Cuidados Intensivos",
            "URG": "Urgencias"
        }
        
    def get_expected_format_description(self) -> str:
        """Devuelve una descripción detallada del formato esperado."""
        return """
Formato esperado para nombres de archivo médicos:
{EXPEDIENTE}_{NOMBRE_PACIENTE}_{NUMERO_EPISODIO}_{CATEGORIA}.pdf

Donde:
- EXPEDIENTE: 10 dígitos (ej: 4000123456)
- NOMBRE_PACIENTE: Apellidos y nombres en mayúsculas, separados por coma (ej: GARCIA LOPEZ, MARIA)
- NUMERO_EPISODIO: 10 dígitos (ej: 6001467010)
- CATEGORIA: 3-4 letras en mayúsculas (EMER, CONS, LAB, RAD, CIRC, HOSP, UCI, URG)

Ejemplos válidos:
- 4000123456_GARCIA LOPEZ, MARIA_6001467010_EMER.pdf
- 3000987654_MARTINEZ RODRIGUEZ, CARLOS ALBERTO_2003091700_CONS.pdf
- 4000555777_HERNANDEZ SILVA, ANA LUCIA_6001468992_LAB.pdf
"""
        
    def parse_filename(self, filename: str) -> MedicalFileInfo:
        """
        Extrae información médica del nombre del archivo.
        
        Args:
            filename: Nombre del archivo a analizar
            
        Returns:
            MedicalFileInfo: Información extraída del archivo
            
        Raises:
            InvalidMedicalFilenameFormatException: Si el formato no es válido
            MedicalFilenameParsingException: Si hay error en el parsing
        """
        try:
            logger.info(f"Parsing medical filename: {filename}")
            
            # Validación básica de extensión
            if not filename.lower().endswith('.pdf'):
                raise InvalidMedicalFilenameFormatException(
                    f"El archivo debe ser PDF. Archivo recibido: '{filename}'\n"
                    f"{self.get_expected_format_description()}"
                )
            
            # Verificar si el archivo tiene el patrón médico
            match = self.medical_pattern.match(filename)
            
            if not match:
                logger.warning(f"Filename doesn't match medical pattern: {filename}")
                
                # Análisis detallado del error para dar feedback específico
                error_details = self._analyze_filename_error(filename)
                
                raise InvalidMedicalFilenameFormatException(
                    f"El nombre del archivo no cumple con el formato médico requerido.\n"
                    f"Archivo recibido: '{filename}'\n"
                    f"Error específico: {error_details}\n"
                    f"{self.get_expected_format_description()}"
                )
            
            # Extraer información
            expediente = match.group(1)
            nombre_paciente = match.group(2).strip().upper()
            numero_episodio = match.group(3)
            categoria = match.group(4).upper()
            
            # Validar categoría médica
            if categoria not in self.valid_categories:
                raise InvalidMedicalFilenameFormatException(
                    f"Categoría médica inválida: '{categoria}'. "
                    f"Categorías válidas: {', '.join(self.valid_categories.keys())} "
                    f"({', '.join([f'{k}={v}' for k, v in self.valid_categories.items()])})\n"
                    f"{self.get_expected_format_description()}"
                )
            
            # Validaciones adicionales
            self._validate_expediente(expediente)
            self._validate_nombre_paciente(nombre_paciente)
            self._validate_numero_episodio(numero_episodio)
            
            logger.info(
                f"Successfully parsed medical filename - Expediente: {expediente}, "
                f"Paciente: {nombre_paciente}, Episodio: {numero_episodio}, "
                f"Categoría: {categoria} ({self.valid_categories[categoria]})"
            )
            
            return MedicalFileInfo(
                expediente=expediente,
                nombre_paciente=nombre_paciente,
                numero_episodio=numero_episodio,
                categoria=categoria,
                is_valid=True
            )
            
        except (InvalidMedicalFilenameFormatException, MedicalFilenameParsingException):
            # Re-raise medical exceptions
            raise
        except Exception as e:
            logger.error(f"Unexpected error parsing filename {filename}: {str(e)}")
            raise MedicalFilenameParsingException(
                f"Error inesperado al procesar el nombre del archivo: {str(e)}\n"
                f"Archivo: '{filename}'\n"
                f"{self.get_expected_format_description()}"
            ) from e
    
    def _analyze_filename_error(self, filename: str) -> str:
        """Analiza el filename para dar un error específico."""
        # Validar extensión PDF (case insensitive para extensión)
        if not filename.lower().endswith('.pdf'):
            return "El archivo debe tener extensión .pdf"
        
        # Remover extensión para análisis (mantener case para el resto)
        name_without_ext = filename[:-4]  # Remover '.pdf'
        parts = name_without_ext.split('_')
        
        if len(parts) < 4:
            return f"Faltan componentes. Se encontraron {len(parts)} partes, se requieren 4 (expediente_paciente_episodio_categoria)"
        
        if len(parts) > 4:
            return f"Demasiados componentes. Se encontraron {len(parts)} partes, se requieren exactamente 4"
        
        expediente, paciente, episodio, categoria = parts
        
        # Validar expediente
        if not expediente.isdigit():
            return f"Expediente debe ser numérico: '{expediente}'"
        if len(expediente) != 10:
            return f"Expediente debe tener 10 dígitos: '{expediente}' ({len(expediente)} dígitos)"
        
        # Validar episodio
        if not episodio.isdigit():
            return f"Número de episodio debe ser numérico: '{episodio}'"
        if len(episodio) != 10:
            return f"Número de episodio debe tener 10 dígitos: '{episodio}' ({len(episodio)} dígitos)"
        
        # Validar categoría (debe ser exactamente mayúsculas, 3-4 caracteres)
        if len(categoria) < 3 or len(categoria) > 4:
            return f"Categoría debe tener 3-4 caracteres: '{categoria}' ({len(categoria)} caracteres)"
        if not categoria.isalpha():
            return f"Categoría debe contener solo letras: '{categoria}'"
        if not categoria.isupper():
            return f"Categoría debe estar en mayúsculas: '{categoria}' (debería ser '{categoria.upper()}')"
        
        # Validar nombre del paciente (debe estar en mayúsculas)
        if not paciente:
            return "Nombre del paciente no puede estar vacío"
        if ',' not in paciente:
            return f"Nombre del paciente debe contener coma separando apellidos de nombres: '{paciente}'"
        if not paciente.isupper():
            return f"Nombre del paciente debe estar en mayúsculas: '{paciente}'"
        
        return "Formato general incorrecto"
    
    def _validate_expediente(self, expediente: str) -> None:
        """Valida el número de expediente."""
        if not expediente.isdigit():
            raise InvalidMedicalFilenameFormatException(
                f"Expediente debe contener solo dígitos: '{expediente}'"
            )
        if len(expediente) != 10:
            raise InvalidMedicalFilenameFormatException(
                f"Expediente debe tener exactamente 10 dígitos: '{expediente}' ({len(expediente)} dígitos)"
            )
        # Validar que no sea todo ceros o patrón inválido
        if expediente == "0000000000":
            raise InvalidMedicalFilenameFormatException(
                "Expediente no puede ser todo ceros"
            )
    
    def _validate_nombre_paciente(self, nombre: str) -> None:
        """Valida el formato del nombre del paciente."""
        if not nombre:
            raise InvalidMedicalFilenameFormatException(
                "Nombre del paciente no puede estar vacío"
            )
        
        if ',' not in nombre:
            raise InvalidMedicalFilenameFormatException(
                f"Nombre del paciente debe contener coma separando apellidos de nombres: '{nombre}'\n"
                f"Formato esperado: 'APELLIDOS, NOMBRES'"
            )
        
        partes = nombre.split(',')
        if len(partes) != 2:
            raise InvalidMedicalFilenameFormatException(
                f"Nombre del paciente debe tener formato 'APELLIDOS, NOMBRES': '{nombre}'"
            )
        
        apellidos, nombres = [p.strip() for p in partes]
        
        if not apellidos:
            raise InvalidMedicalFilenameFormatException(
                "Los apellidos no pueden estar vacíos"
            )
        
        if not nombres:
            raise InvalidMedicalFilenameFormatException(
                "Los nombres no pueden estar vacíos"
            )
        
        # Validar caracteres permitidos (letras, espacios, acentos)
        allowed_pattern = re.compile(r'^[A-ZÁÉÍÓÚÑÜ\s]+$')
        if not allowed_pattern.match(apellidos):
            raise InvalidMedicalFilenameFormatException(
                f"Los apellidos contienen caracteres no válidos: '{apellidos}'\n"
                f"Solo se permiten letras mayúsculas, espacios y acentos"
            )
        
        if not allowed_pattern.match(nombres):
            raise InvalidMedicalFilenameFormatException(
                f"Los nombres contienen caracteres no válidos: '{nombres}'\n"
                f"Solo se permiten letras mayúsculas, espacios y acentos"
            )
    
    def _validate_numero_episodio(self, episodio: str) -> None:
        """Valida el número de episodio."""
        if not episodio.isdigit():
            raise InvalidMedicalFilenameFormatException(
                f"Número de episodio debe contener solo dígitos: '{episodio}'"
            )
        if len(episodio) != 10:
            raise InvalidMedicalFilenameFormatException(
                f"Número de episodio debe tener exactamente 10 dígitos: '{episodio}' ({len(episodio)} dígitos)"
            )
        
        # Validación básica de rango numérico (los números reales no siguen formato de fecha estricto)
        try:
            numero = int(episodio)
            if numero <= 0:
                raise InvalidMedicalFilenameFormatException(
                    f"Número de episodio debe ser un número positivo: '{episodio}'"
                )
        except ValueError as e:
            raise InvalidMedicalFilenameFormatException(
                f"Número de episodio inválido: '{episodio}'"
            ) from e
    
    def to_dict(self, file_info: MedicalFileInfo) -> Dict[str, Any]:
        """
        Convierte MedicalFileInfo a diccionario para almacenar en MongoDB.
        
        Args:
            file_info: Información del archivo médico
            
        Returns:
            Dict[str, Any]: Diccionario con la información médica
        """
        return {
            "expediente": file_info.expediente,
            "nombre_paciente": file_info.nombre_paciente,
            "numero_episodio": file_info.numero_episodio,
            "categoria": file_info.categoria,
            "medical_info_valid": file_info.is_valid,
            "medical_info_error": file_info.error_message
        } 