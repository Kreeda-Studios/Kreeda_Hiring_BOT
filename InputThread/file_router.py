
"""
PDF File Router Script
----------------------
Purpose:
    - Check if a PDF is text-based or image-based.
    - Route text-based PDFs to the Donut non-OCR extractor script.
    - Skip and log image-based or unsupported PDFs.

Logic:
    1. Check if the PDF contains extractable text.
    2. If text-based → pass to extractor function.
    3. If not text-based → log skipped file.

Notes:
    - This script does NOT perform extraction — only classification & routing.
    - Uses PyMuPDF (fitz) for text detection.
"""

import os
import fitz  # PyMuPDF
from datetime import datetime
from InputThread.extract_pdf import process_pdf  # Donut extractor function

SKIPPED_LOG = "Skipped_List.txt"

def is_text_based_pdf(pdf_path):
    try:
        with fitz.open(pdf_path) as doc:
            for page in doc:
                if page.get_text().strip():  # Detect any non-empty text
                    return True
        return False
    except Exception as e:
        print(f"[ERROR] Failed to read {pdf_path}: {e}")
        return False

def log_skipped(pdf_path):
    os.makedirs(os.path.dirname(SKIPPED_LOG), exist_ok=True)
    with open(SKIPPED_LOG, "a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now()} - {pdf_path}\n")

def route_pdf(pdf_path, save_dir, original_name=None):
    if not pdf_path.lower().endswith(".pdf"):
        print(f"❌ Unsupported file format: {pdf_path}")
        return None

    if is_text_based_pdf(pdf_path):
        resume_name = original_name if original_name else os.path.basename(pdf_path)
        print(f"✅ Text-based PDF detected: {resume_name}")
        return process_pdf(pdf_path, save_dir, original_name=original_name)
    else:
        print(f"⚠️ Skipped (image-based or non-text PDF): {os.path.basename(pdf_path)}")
        log_skipped(pdf_path)
        return None

