import os
import pymupdf as fitz  # PyMuPDF

JD_FILE = "InputThread/JD/JD.txt"

def process_jd_pdf(pdf_path):
    """
    Extract text from a JD PDF and save into JD.txt (overwrite existing).
    
    Args:
        pdf_path (str): Path to the uploaded JD PDF.
    Returns:
        str or None: Path to JD.txt if successful, else None.
    """
    try:
        doc = fitz.open(pdf_path)
        all_text = []

        for page_index in range(len(doc)):
            page = doc[page_index]
            page_text = page.get_text("text")
            if page_text.strip():
                all_text.append(page_text.strip())

        final_text = "\n".join(all_text).strip()

        if final_text:
            os.makedirs(os.path.dirname(JD_FILE), exist_ok=True)
            with open(JD_FILE, "w", encoding="utf-8") as f:
                f.write(final_text)
            return JD_FILE
        else:
            return None

    except Exception:
        return None
