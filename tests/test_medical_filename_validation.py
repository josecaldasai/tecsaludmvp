"""
Tests específicos para validación estricta de nombres de archivo médicos.
Incluye tests para single upload, batch upload y casos edge.
"""

import pytest
import json
import tempfile
import os
from typing import Dict, Any


class TestMedicalFilenameValidation:
    """Tests para validación estricta de nombres de archivo médicos."""

    def test_upload_document_valid_medical_filename(self, api_client, clean_database):
        """Test que un archivo con formato médico válido se cargue exitosamente."""
        valid_filename = "4000123456_GARCIA LOPEZ, MARIA_6001467010_EMER.pdf"
        
        # Usar el mismo contenido PDF que la fixture existente (más completo)
        pdf_content = b'''\
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000173 00000 n 
0000000301 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF'''
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(pdf_content)
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (valid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                assert response.status_code == 201
                result = response.json()
                
                # Verificar que la información médica se extrajo correctamente
                assert result["expediente"] == "4000123456"
                assert result["nombre_paciente"] == "GARCIA LOPEZ, MARIA"
                assert result["numero_episodio"] == "6001467010"  # Ahora es 10 dígitos
                assert result["categoria"] == "EMER"
                assert result["medical_info_valid"] is True
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_invalid_medical_filename_format(self, api_client, clean_database):
        """Test de error con filename médico inválido - formato incorrecto."""
        invalid_filename = "documento_invalido.pdf"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"PDF content")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                
                assert response.status_code == 400
                
                result = response.json()
                # La respuesta real tiene un handler global que envuelve el error específico
                assert result["error_code"] == "HTTP_400"
                
                # El error específico está dentro de error_message
                error_details = result["error_message"]
                assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME"
                assert "formato médico requerido" in error_details["message"]
                assert error_details["filename"] == invalid_filename
                assert "detailed_error" in error_details
                # Verificar mensaje específico sobre longitud de episodio
                assert "Faltan componentes" in error_details["detailed_error"]
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_invalid_expediente_length(self, api_client, clean_database):
        """Test de error con expediente de longitud incorrecta."""
        invalid_filename = "12345_GARCIA LOPEZ, MARIA_2024010100001_EMER.pdf"  # Expediente muy corto
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"PDF content")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                
                assert response.status_code == 400
                
                result = response.json()
                assert result["error_code"] == "HTTP_400"
                
                error_details = result["error_message"]
                assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME"
                assert "10 dígitos" in error_details["detailed_error"]
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_invalid_patient_name_format(self, api_client, clean_database):
        """Test que un archivo sin coma en el nombre del paciente sea rechazado."""
        invalid_filename = "4000123456_GARCIA LOPEZ MARIA_6001467010_EMER.pdf"  # Falta coma

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nstartxref\n0\n%%EOF")
            temp_file_path = temp_file.name

        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                assert response.status_code == 400
                result = response.json()
                assert result["error_code"] == "HTTP_400"
                error_details = result["error_message"]
                assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME"
                assert "formato médico requerido" in error_details["message"]
                assert error_details["filename"] == invalid_filename
                assert "detailed_error" in error_details
                # El parser rechaza por formato general, no específicamente por coma
                assert "coma separando apellidos" in error_details["detailed_error"]
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_invalid_episode_length(self, api_client, clean_database):
        """Test que un archivo con número de episodio de longitud incorrecta sea rechazado."""
        invalid_filename = "4000123456_GARCIA LOPEZ, MARIA_12345_EMER.pdf"  # Solo 5 dígitos en lugar de 10
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"PDF content")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                
                assert response.status_code == 400
                
                result = response.json()
                assert result["error_code"] == "HTTP_400"
                
                error_details = result["error_message"]
                assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME"
                # El parser rechazará esto por no ser dígitos
                assert "debe tener 10 dígitos" in error_details["detailed_error"]
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_invalid_medical_category(self, api_client, clean_database):
        """Test que un archivo con categoría médica inválida sea rechazado."""
        invalid_filename = "4000123456_GARCIA LOPEZ, MARIA_6001467010_XXXX.pdf"  # Categoría inválida

        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"%PDF-1.4\n1 0 obj\n<<\n/Type /Catalog\n>>\nendobj\nstartxref\n0\n%%EOF")
            temp_file_path = temp_file.name

        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                assert response.status_code == 400
                result = response.json()
                assert result["error_code"] == "HTTP_400"
                error_details = result["error_message"]
                assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME"
                assert "formato médico requerido" in error_details["message"]
                assert error_details["filename"] == invalid_filename
                assert "detailed_error" in error_details
                # Verificar que menciona el problema de categoría
                assert "Categoría médica inválida" in error_details["detailed_error"]
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_non_pdf_extension(self, api_client, clean_database):
        """Test de error con archivo que no es PDF."""
        invalid_filename = "4000123456_GARCIA LOPEZ, MARIA_2024010100001_EMER.txt"  # No PDF
        
        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as temp_file:
            temp_file.write(b"Text content")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "text/plain")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                
                assert response.status_code == 400
                
                result = response.json()
                assert result["error_code"] == "HTTP_400"
                
                error_details = result["error_message"]
                assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME"
                assert "debe ser PDF" in error_details["detailed_error"]
        finally:
            os.unlink(temp_file_path)

    def test_upload_document_invalid_episode_date(self, api_client, clean_database):
        """Test que un archivo con fecha inválida en episodio sea rechazado."""
        # Usar un número de episodio que simplemente sea inválido por otros motivos
        invalid_filename = "4000123456_GARCIA LOPEZ, MARIA_abcdefghij_EMER.pdf"  # Letras en lugar de dígitos
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"PDF content")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                
                assert response.status_code == 400
                
                result = response.json()
                assert result["error_code"] == "HTTP_400"
                
                error_details = result["error_message"]
                assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME"
                assert "debe ser numérico" in error_details["detailed_error"]
        finally:
            os.unlink(temp_file_path)


class TestBatchMedicalFilenameValidation:
    """Tests para validación de filenames médicos en batch upload."""

    def test_batch_upload_all_valid_medical_filenames(self, api_client, clean_database):
        """Test de batch upload exitoso con todos los filenames médicos válidos."""
        valid_files = [
            "4000123456_GARCIA LOPEZ, MARIA_6001467010_EMER.pdf",
            "3000987654_MARTINEZ RODRIGUEZ, CARLOS_6001467011_CONS.pdf",
            "4000555777_HERNANDEZ SILVA, ANA_6001467012_LAB.pdf"
        ]
        
        # Usar el mismo contenido PDF que funciona en single upload
        pdf_content = b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 100
>>
stream
BT
/F1 12 Tf
100 700 Td
(Expediente Medico) Tj
0 -20 Td
(Paciente: Test Patient) Tj
0 -20 Td
(Episodio: Test Episode) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000053 00000 n 
0000000110 00000 n 
0000000190 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
341
%%EOF"""
        
        temp_files = []
        files_data = []
        
        try:
            # Crear archivos temporales con contenido PDF válido
            for filename in valid_files:
                temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                temp_file.write(pdf_content)
                temp_file.close()
                temp_files.append(temp_file.name)
                
                files_data.append(("files", (filename, open(temp_file.name, "rb"), "application/pdf")))
            
            data = {"user_id": "test_user", "batch_description": "Test batch válido"}
            
            response = api_client.post("/api/v1/documents/upload/batch", files=files_data, data=data)
            
            assert response.status_code == 201
            
            result = response.json()
            assert result["total_files"] == 3
            assert result["processed_count"] == 3
            assert result["failed_count"] == 0
            assert result["processing_status"] == "completed"
            
            # Verificar documentos exitosos
            for doc in result["successful_documents"]:
                assert doc["medical_info_valid"] is True
                assert doc["expediente"] is not None
                assert doc["nombre_paciente"] is not None
                
        finally:
            # Cerrar archivos y limpiar
            for file_tuple in files_data:
                file_tuple[1][1].close()
            for temp_file_path in temp_files:
                os.unlink(temp_file_path)

    def test_batch_upload_one_invalid_medical_filename(self, api_client, clean_database):
        """Test de batch upload que falla completamente si UN archivo tiene filename inválido."""
        mixed_files = [
            "4000123456_GARCIA LOPEZ, MARIA_6001467010_EMER.pdf",  # Válido
            "documento_invalido.pdf",  # Inválido
            "3000987654_MARTINEZ RODRIGUEZ, CARLOS_6001467011_CONS.pdf"  # Válido
        ]
        
        temp_files = []
        files_data = []
        
        try:
            # Crear archivos temporales
            for filename in mixed_files:
                temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                temp_file.write(b"PDF content")
                temp_file.close()
                temp_files.append(temp_file.name)
                
                files_data.append(("files", (filename, open(temp_file.name, "rb"), "application/pdf")))
            
            data = {"user_id": "test_user"}
            
            response = api_client.post("/api/v1/documents/upload/batch", files=files_data, data=data)
            
            # El batch completo debe fallar por el archivo inválido
            assert response.status_code == 400
            
            result = response.json()
            assert result["error_code"] == "HTTP_400"
            
            error_details = result["error_message"]
            assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME_BATCH"
            assert "no cumplen con el formato médico" in error_details["message"]
            assert error_details["file_count"] == 3
            assert "documento_invalido.pdf" in error_details["detailed_error"]
            
        finally:
            # Cerrar archivos y limpiar
            for file_tuple in files_data:
                file_tuple[1][1].close()
            for temp_file_path in temp_files:
                os.unlink(temp_file_path)

    def test_batch_upload_invalid_category_in_batch(self, api_client, clean_database):
        """Test de batch upload que falla por categoría inválida en uno de los archivos."""
        invalid_batch_files = [
            "4000123456_GARCIA LOPEZ, MARIA_6001467010_EMER.pdf",  # Válido
            "3000987654_MARTINEZ RODRIGUEZ, CARLOS_6001467011_XXXX.pdf"  # Categoría inválida
        ]
        
        temp_files = []
        files_data = []
        
        try:
            # Crear archivos temporales
            for filename in invalid_batch_files:
                temp_file = tempfile.NamedTemporaryFile(suffix=".pdf", delete=False)
                temp_file.write(b"PDF content")
                temp_file.close()
                temp_files.append(temp_file.name)
                
                files_data.append(("files", (filename, open(temp_file.name, "rb"), "application/pdf")))
            
            data = {"user_id": "test_user"}
            
            response = api_client.post("/api/v1/documents/upload/batch", files=files_data, data=data)
            
            # El batch completo debe fallar
            assert response.status_code == 400
            
            result = response.json()
            assert result["error_code"] == "HTTP_400"
            
            error_details = result["error_message"]
            assert error_details["error_code"] == "INVALID_MEDICAL_FILENAME_BATCH"
            assert "Categoría médica inválida" in error_details["detailed_error"]
            
        finally:
            # Cerrar archivos y limpiar
            for file_tuple in files_data:
                file_tuple[1][1].close()
            for temp_file_path in temp_files:
                os.unlink(temp_file_path)


class TestMedicalFilenameValidationEdgeCases:
    """Tests para casos edge específicos de validación de filenames médicos."""

    def test_valid_medical_categories(self, api_client, clean_database):
        """Test que todas las categorías médicas válidas funcionen."""
        valid_categories = ["EMER", "CONS", "LAB", "RAD", "CIRC", "HOSP", "UCI", "URG"]
        
        # Usar contenido PDF más completo para evitar errores 500
        pdf_content = b'''\
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000173 00000 n 
0000000301 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF'''
        
        for i, category in enumerate(valid_categories):
            filename = f"400012345{i}_GARCIA LOPEZ, MARIA_600146701{i}_{category}.pdf"
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, "rb") as file:
                    files = {"file": (filename, file, "application/pdf")}
                    data = {"user_id": "test_user"}
                    
                    response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                    
                    assert response.status_code == 201, f"Failed for category {category}"
                    
                    result = response.json()
                    assert result["categoria"] == category
                    assert result["medical_info_valid"] is True
            finally:
                os.unlink(temp_file_path)

    def test_patient_name_with_special_characters(self, api_client, clean_database):
        """Test que nombres de pacientes con caracteres especiales funcionen."""
        special_names = [
            "GARCÍA LÓPEZ, MARÍA",
            "HERNÁNDEZ MARTÍNEZ, JOSÉ ANTONIO", 
            "PÉREZ GONZÁLEZ, ANA SOFÍA",
            "RUÍZ FERNÁNDEZ, CARLOS ALBERTO"
        ]
        
        # Usar contenido PDF más completo para evitar errores 500
        pdf_content = b'''\
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000173 00000 n 
0000000301 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF'''
        
        for i, name in enumerate(special_names):
            filename = f"400012345{i}_{name}_600146701{i}_CONS.pdf"
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, "rb") as file:
                    files = {"file": (filename, file, "application/pdf")}
                    data = {"user_id": "test_user"}
                    
                    response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                    
                    assert response.status_code == 201, f"Failed for name {name}"
                    
                    result = response.json()
                    assert result["nombre_paciente"] == name.upper()
                    assert result["medical_info_valid"] is True
            finally:
                os.unlink(temp_file_path)

    def test_edge_case_date_validation(self, api_client, clean_database):
        """Test casos extremos de validación de números de episodio."""
        # Casos válidos con números de episodio reales de 10 dígitos
        valid_cases = [
            "2003091700",  # Formato real encontrado en archivos
            "6001467010",  # Formato real encontrado en archivos  
            "2003097280",  # Formato real encontrado en archivos
        ]
        
        # Usar contenido PDF más completo para evitar errores 500
        pdf_content = b'''\
%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj

2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj

3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj

4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Test content) Tj
ET
endstream
endobj

xref
0 5
0000000000 65535 f 
0000000010 00000 n 
0000000079 00000 n 
0000000173 00000 n 
0000000301 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
398
%%EOF'''
        
        for episode_number in valid_cases:
            filename = f"4000123456_GARCIA LOPEZ, MARIA_{episode_number}_EMER.pdf"
            
            with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
                temp_file.write(pdf_content)
                temp_file_path = temp_file.name
            
            try:
                with open(temp_file_path, "rb") as file:
                    files = {"file": (filename, file, "application/pdf")}
                    data = {"user_id": "test_user"}
                    
                    response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                    
                    assert response.status_code == 201, f"Failed for valid date {episode_number}"
                    result = response.json()
                    assert result["numero_episodio"] == episode_number
                    assert result["medical_info_valid"] is True
            finally:
                os.unlink(temp_file_path)

    def test_error_message_quality(self, api_client, clean_database):
        """Test para verificar la calidad y utilidad de los mensajes de error."""
        invalid_filename = "invalid_format.pdf"
        
        with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as temp_file:
            temp_file.write(b"PDF content")
            temp_file_path = temp_file.name
        
        try:
            with open(temp_file_path, "rb") as file:
                files = {"file": (invalid_filename, file, "application/pdf")}
                data = {"user_id": "test_user"}
                
                response = api_client.post("/api/v1/documents/upload", files=files, data=data)
                
                assert response.status_code == 400
                
                result = response.json()
                assert result["error_code"] == "HTTP_400"
                
                # Verificar que el mensaje de error es útil
                detailed_error = result["error_message"]["detailed_error"]
                assert "Formato esperado" in detailed_error
                assert "EXPEDIENTE" in detailed_error
                assert "NOMBRE_PACIENTE" in detailed_error
                assert "NUMERO_EPISODIO" in detailed_error
                assert "CATEGORIA" in detailed_error
                assert "Ejemplos válidos" in detailed_error
                assert "4000123456_GARCIA LOPEZ, MARIA_6001467010_EMER.pdf" in detailed_error
                
                # Verificar que incluye diagnóstico específico del error
                assert "Faltan componentes" in detailed_error or "formato general incorrecto" in detailed_error.lower()
                
        finally:
            os.unlink(temp_file_path) 