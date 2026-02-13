import os
from docxtpl import DocxTemplate
from docx2pdf import convert


class GeneradorCertificadosWord:
    """
    Clase utilitaria para la generación de documentos PDF a partir de plantillas
    de Microsoft Word (.docx) utilizando sustitución de variables.
    """

    @staticmethod
    def generar(ruta_plantilla_docx, datos_diccionario, ruta_salida_pdf):
        """
        Genera un certificado PDF basado en una plantilla Word reemplazando las variables
        proporcionadas.

        Args:
            ruta_plantilla_docx (str): Ruta del sistema de archivos a la plantilla .docx.
            datos_diccionario (dict): Diccionario con claves y valores a reemplazar en la plantilla (contexto).
            ruta_salida_pdf (str): Ruta completa donde se guardará el archivo PDF resultante.

        Returns:
            bool: True si la generación fue exitosa.

        Raises:
            FileNotFoundError: Si la plantilla .docx no existe en la ruta especificada.
            RuntimeError: Si ocurre un error durante la conversión de Word a PDF.
            Exception: Para cualquier otro error no controlado durante el proceso.
        """
        if not os.path.exists(ruta_plantilla_docx):
            raise FileNotFoundError(f"No existe la plantilla: {ruta_plantilla_docx}")

        try:
            # 1. Rellenar Word
            doc = DocxTemplate(ruta_plantilla_docx)
            doc.render(datos_diccionario)

            # 2. Guardar temporalmente
            ruta_temp_docx = ruta_salida_pdf.replace(".pdf", "_temp.docx")
            doc.save(ruta_temp_docx)

            # 3. Convertir a PDF
            try:
                # pythoncom.CoInitialize() # Descomentar si es necesario en Windows
                convert(ruta_temp_docx, ruta_salida_pdf)
            except Exception as e:
                raise RuntimeError(f"Fallo al convertir Word a PDF: {e}")
            finally:
                if os.path.exists(ruta_temp_docx):
                    os.remove(ruta_temp_docx)
            return True

        except Exception as e:
            print(f"Error Generador Word: {e}")
            raise e