import docx
import os

def extract_text_from_docx(docx_path):
    ext = os.path.splitext(docx_path)[1].lower()

    if ext == '.txt':
        with open(docx_path, 'r', encoding='utf-8') as f:
            return f.read()

    try:
        doc = docx.Document(docx_path)
        return '\n'.join([para.text for para in doc.paragraphs])
    except Exception as e:
        raise RuntimeError(f"Failed to extract text from DOCX: {e}")
