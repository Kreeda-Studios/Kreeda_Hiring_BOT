import pytesseract
from pdf2image import convert_from_path
import tempfile
import os

def extract_text_from_scanned_pdf(pdf_path):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            images = convert_from_path(pdf_path, dpi=300, output_folder=temp_dir)
            text = ''
            for image in images:
                text += pytesseract.image_to_string(image)
            return text
    except Exception as e:
        raise RuntimeError(f"OCR failed for scanned PDF: {e}")
