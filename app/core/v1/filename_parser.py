"""Parser para extraer información médica del nombre del archivo."""

import re
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass

logger = logging.getLogger(__name__)

@dataclass
class MedicalFileInfo:
    """Información médica extraída del nombre del archivo."""
    expediente: Optional[str] = None
    nombre_paciente: Optional[str] = None
    numero_episodio: Optional[str] = None
    categoria: Optional[str] = None
    is_valid: bool = False
    error_message: Optional[str] = None

class MedicalFilenameParser:
    """Parser para extraer información médica del nombre del archivo."""
    
    def __init__(self):
        # Patrón para archivos médicos: {expediente}_{nombre_paciente}_{numero_episodio}_{categoria}.pdf
        self.medical_pattern = re.compile(
            r'^(\d+)_([^_]+(?:,\s*[^_]+)*)_(\d+)_([A-Z]+)\.pdf$',
            re.IGNORECASE
        )
        
    def parse_filename(self, filename: str) -> MedicalFileInfo:
        """
        Extrae información médica del nombre del archivo.
        
        Args:
            filename: Nombre del archivo a analizar
            
        Returns:
            MedicalFileInfo: Información extraída del archivo
        """
        try:
            logger.info(f"Parsing filename: {filename}")
            
            # Verificar si el archivo tiene el patrón médico
            match = self.medical_pattern.match(filename)
            
            if not match:
                logger.warning(f"Filename doesn't match medical pattern: {filename}")
                return MedicalFileInfo(
                    is_valid=False,
                    error_message=f"Filename doesn't match expected medical pattern: {filename}"
                )
            
            # Extraer información
            expediente = match.group(1)
            nombre_paciente = match.group(2).strip()
            numero_episodio = match.group(3)
            categoria = match.group(4).upper()
            
            logger.info(
                f"Successfully parsed filename - Expediente: {expediente}, "
                f"Paciente: {nombre_paciente}, Episodio: {numero_episodio}, "
                f"Categoría: {categoria}"
            )
            
            return MedicalFileInfo(
                expediente=expediente,
                nombre_paciente=nombre_paciente,
                numero_episodio=numero_episodio,
                categoria=categoria,
                is_valid=True
            )
            
        except Exception as e:
            logger.error(f"Error parsing filename {filename}: {str(e)}")
            return MedicalFileInfo(
                is_valid=False,
                error_message=f"Error parsing filename: {str(e)}"
            )
    
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
            "is_valid": file_info.is_valid,
            "error_message": file_info.error_message
        } 