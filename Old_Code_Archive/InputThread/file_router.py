
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
import json
import pymupdf as fitz  # PyMuPDF
from datetime import datetime
from pathlib import Path
from InputThread.extract_pdf import process_pdf  # Donut extractor function

SKIPPED_LOG = "Skipped_List.txt"
SKIPPED_JSON = Path("Ranking/Skipped.json")

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
    # Log to text file (legacy)
    os.makedirs(os.path.dirname(SKIPPED_LOG), exist_ok=True)
    with open(SKIPPED_LOG, "a", encoding="utf-8") as log_file:
        log_file.write(f"{datetime.now()} - {pdf_path}\n")
    
    # Also log to Skipped.json for consistency
    try:
        SKIPPED_JSON.parent.mkdir(parents=True, exist_ok=True)
        pdf_name = os.path.basename(pdf_path)
        
        skipped_entry = {
            "timestamp": datetime.utcnow().isoformat(),
            "name": Path(pdf_path).stem,
            "candidate_id": None,
            "reason": "Image-based or non-text PDF - extraction skipped",
            "file": pdf_name
        }
        
        # Load existing skipped entries
        existing_skipped = []
        if SKIPPED_JSON.exists():
            try:
                with open(SKIPPED_JSON, "r", encoding="utf-8") as f:
                    existing_skipped = json.load(f)
                    if not isinstance(existing_skipped, list):
                        existing_skipped = []
            except Exception:
                existing_skipped = []
        
        # Add skipped entry
        existing_skipped.append(skipped_entry)
        
        # Save back
        # #region agent log
        with open(".cursor/debug.log", "a", encoding="utf-8") as log:
            log.write(json.dumps({"sessionId":"debug-session","runId":"file-router","hypothesisId":"G","location":"file_router.py:74","message":"Writing skipped PDF to Skipped.json","data":{"pdf":pdf_name,"total_entries":len(existing_skipped)},"timestamp":int(datetime.now().timestamp()*1000)})+"\n")
        # #endregion
        with open(SKIPPED_JSON, "w", encoding="utf-8") as f:
            json.dump(existing_skipped, f, indent=2)
        # #region agent log
        with open(".cursor/debug.log", "a", encoding="utf-8") as log:
            log.write(json.dumps({"sessionId":"debug-session","runId":"file-router","hypothesisId":"G","location":"file_router.py:76","message":"Successfully wrote to Skipped.json","data":{"file":str(SKIPPED_JSON)},"timestamp":int(datetime.now().timestamp()*1000)})+"\n")
        # #endregion
    except Exception as e:
        # #region agent log
        with open(".cursor/debug.log", "a", encoding="utf-8") as log:
            log.write(json.dumps({"sessionId":"debug-session","runId":"file-router","hypothesisId":"G","location":"file_router.py:78","message":"Error writing to Skipped.json","data":{"error":str(e)},"timestamp":int(datetime.now().timestamp()*1000)})+"\n")
        # #endregion
        # Don't fail if logging to Skipped.json fails
        print(f"⚠️ Could not log to Skipped.json: {e}")

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

