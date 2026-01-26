import os
import mimetypes

def save_text_to_file(text: str, output_path: str):
    """
    Saves cleaned text to a .txt file.
    """
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(text.strip())

def get_file_extension(filename: str) -> str:
    """
    Returns the lower-case extension of a file (e.g., pdf, docx, txt)
    """
    return filename.split('.')[-1].lower()

def is_pdf_scanned(mime_type: str, raw_text: str) -> bool:
    """
    Heuristic to check if PDF is scanned (i.e., no extractable text).
    """
    return mime_type == 'application/pdf' and len(raw_text.strip()) < 100

def clean_text(text: str) -> str:
    """
    Basic text cleaning for extracted resume content.
    """
    lines = text.splitlines()
    cleaned = [line.strip() for line in lines if line.strip()]
    return "\n".join(cleaned)

def detect_mime_type(filename: str) -> str:
    """
    Detects the MIME type of a file using its extension.
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type or ''
