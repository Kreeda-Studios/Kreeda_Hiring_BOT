#!/usr/bin/env python3
"""
Resume PDF Text Extraction — Production Hybrid 2-Tier Version
==============================================================
Architecture (Hybrid & High-Precision):
  - Tier 1: PyMuPDF (fitz) — Fast digital text layer & hyperlink reader.
  - Tier 2: Tesseract OCR (pytesseract) — 300 DPI preprocessed OCR for 
            scanned image PDFs AND Hybrid PDFs (Canva/Figma templates where 
            headers are text but body sections like Skills/Figma are embedded images).

Quality Gate Validation:
  - Validates total characters AND presence of core resume section anchors 
    ('EXPERIENCE', 'SKILLS', 'EDUCATION', 'PROJECTS', 'SOFTWARE').
  - If PyMuPDF text is incomplete (e.g. <400 chars/page or missing section anchors),
    it automatically triggers Tier 2 OCR and merges OCR body text with PyMuPDF 
    hyperlinks so zero text or skills (like Figma) get lost.
"""

import os
import re
import time
import fitz  # PyMuPDF
from pathlib import Path
from typing import Dict, Any, List, Tuple

# Optional PIL & pytesseract imports with graceful fallback
try:
    from PIL import Image, ImageOps
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

try:
    import pytesseract
    PYTESSERACT_AVAILABLE = True
except ImportError:
    PYTESSERACT_AVAILABLE = False

# Quality Gate Thresholds
MIN_CHARS_PER_PAGE = 350       # A complete resume page typically has 500-1500 chars
MIN_TOTAL_DIGITAL_CHARS = 600  # Below this for a resume triggers hybrid OCR check
MIN_OCR_VALID_CHARS = 50       # Minimum characters required from OCR
MAX_OCR_PAGES = 10             # Memory and CPU safety cap for massive PDFs

# Core Section Anchor Keywords used to validate text completeness
CORE_SECTION_ANCHORS = [
    r'\bEXPERIENCE\b', r'\bWORK\s+HISTORY\b', r'\bEMPLOYMENT\b',
    r'\bSKILLS\b', r'\bSOFTWARE\b', r'\bTECHNICAL\s+SKILLS\b',
    r'\bEDUCATION\b', r'\bACADEMIC\b',
    r'\bPROJECTS\b', r'\bPORTFOLIO\b'
]


def _extract_pymupdf_text(doc: fitz.Document) -> Tuple[str, List[str], int, int]:
    """
    Tier 1: Extract text layer and embedded hyperlinks using PyMuPDF.
    Returns: (full_text, hyperlinks, total_characters, page_count)
    """
    text_blocks = []
    total_chars = 0
    links: set = set()
    page_count = len(doc)

    for page_num in range(page_count):
        page = doc.load_page(page_num)
        text = page.get_text()
        if text.strip():
            text_blocks.append(text)
            total_chars += len(text)

        # Collect embedded hyperlinks (LinkedIn, Behance, Portfolio, Github)
        for link in page.get_links():
            uri = link.get("uri")
            if uri:
                links.add(uri)

    full_text = '\n\n'.join(text_blocks)
    return full_text, sorted(links), total_chars, page_count


def _is_digital_text_complete(text: str, total_chars: int, page_count: int) -> bool:
    """
    Quality Gate: Validates if PyMuPDF digital text is complete or partial/hybrid.
    Returns True ONLY if text meets character density AND contains core section anchors.
    """
    if page_count <= 0:
        return False

    avg_chars_per_page = total_chars / page_count

    # Check 1: Dense text count check
    if total_chars >= MIN_TOTAL_DIGITAL_CHARS and avg_chars_per_page >= MIN_CHARS_PER_PAGE:
        # Verify presence of at least 1 major section anchor
        anchor_matches = sum(1 for pattern in CORE_SECTION_ANCHORS if re.search(pattern, text, re.IGNORECASE))
        if anchor_matches >= 1:
            return True

    # Check 2: Even if total chars is slightly lower, check if at least 2 major section anchors exist
    anchor_matches = sum(1 for pattern in CORE_SECTION_ANCHORS if re.search(pattern, text, re.IGNORECASE))
    if anchor_matches >= 2 and total_chars >= 400:
        return True

    # Otherwise, it's a Hybrid or Scanned PDF (e.g. Canva/Figma template with image body)
    return False


def _preprocess_page_to_image(page: fitz.Page, dpi: int = 300) -> Any:
    """
    Render PDF page at 300 DPI and convert to high-contrast grayscale PIL Image.
    Sharpens thin fonts, grey dots, and subtle text blocks for Tesseract OCR.
    """
    if not PIL_AVAILABLE:
        return None

    # Render page to high-resolution 300 DPI pixmap
    pix = page.get_pixmap(dpi=dpi)
    img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)

    # Grayscale conversion + contrast autoleveling
    img_gray = ImageOps.grayscale(img)
    img_enhanced = ImageOps.autocontrast(img_gray, cutoff=2)
    return img_enhanced


def _extract_tesseract_ocr(doc: fitz.Document, max_pages: int = MAX_OCR_PAGES) -> Tuple[str, int]:
    """
    Tier 2: High-resolution Tesseract OCR for scanned and hybrid image-based PDFs.
    Returns: (ocr_text, characters_count)
    """
    if not (PIL_AVAILABLE and PYTESSERACT_AVAILABLE):
        print("⚠️ [OCR Extractor] pytesseract or PIL is not installed. Skipping Tier 2.")
        return "", 0

    ocr_blocks = []
    total_chars = 0
    pages_to_process = min(len(doc), max_pages)

    for page_num in range(pages_to_process):
        page = doc.load_page(page_num)
        img = _preprocess_page_to_image(page, dpi=300)

        if img is None:
            continue

        # Page segmentation mode 6 (Assume a single uniform block of text)
        page_text = pytesseract.image_to_string(img, config='--psm 6')
        if page_text.strip():
            ocr_blocks.append(page_text)
            total_chars += len(page_text)

    ocr_full_text = '\n\n'.join(ocr_blocks)
    return ocr_full_text, total_chars


def clean_resume_text(text: str) -> str:
    """Clean and normalize raw extracted resume text."""
    if not text:
        return ''

    # Normalize line breaks and spaces
    text = re.sub(r'\n{3,}', '\n\n', text)
    text = re.sub(r' {2,}', ' ', text)
    text = re.sub(r'\t+', ' ', text)

    # Remove null bytes and non-printable control characters
    text = re.sub(r'\x00', '', text)
    text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)

    # Standardize section header aliases
    section_patterns = [
        (r'\bEXPERIENCE\b', 'EXPERIENCE'),
        (r'\bEDUCATION\b', 'EDUCATION'),
        (r'\bSKILLS\b', 'SKILLS'),
        (r'\bPROJECTS\b', 'PROJECTS'),
        (r'\bCERTIFICATIONS?\b', 'CERTIFICATIONS'),
        (r'\bCONTACT\s+INFO\w*\b', 'CONTACT')
    ]

    for pattern, replacement in section_patterns:
        text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)

    return text.strip()


def extract_pdf_text(pdf_path: str) -> Dict[str, Any]:
    """
    Extract text from PDF using Hybrid 2-Tier Fallback:
      Tier 1: PyMuPDF (digital text layer)
      Tier 2: Tesseract OCR (300 DPI image OCR for scanned & Canva/Figma Hybrid PDFs)
    """
    start_time = time.time()
    doc = None

    try:
        doc = fitz.open(pdf_path)

        # ── TIER 1: PyMuPDF Extraction ────────────────────────────────
        t1_text, hyperlinks, t1_chars, page_count = _extract_pymupdf_text(doc)

        # Validate if Tier 1 digital text is complete
        if _is_digital_text_complete(t1_text, t1_chars, page_count):
            processing_time = time.time() - start_time
            doc.close()
            return {
                'success': True,
                'text': t1_text,
                'hyperlinks': hyperlinks,
                'method': 'pymupdf',
                'pages': page_count,
                'characters': t1_chars,
                'processing_time': processing_time,
            }

        # ── TIER 2: Tesseract OCR (Hybrid / Scanned PDF Trigger) ─────
        print(f"ℹ️ [PDF Extractor] Hybrid/Scanned PDF detected ({t1_chars} digital chars across {page_count} pages). Triggering Tier 2 Tesseract OCR (300 DPI) for {pdf_path}")
        t2_text, t2_chars = _extract_tesseract_ocr(doc, max_pages=MAX_OCR_PAGES)
        processing_time = time.time() - start_time
        doc.close()

        if t2_chars >= MIN_OCR_VALID_CHARS:
            # If PyMuPDF had some header text (like links/name), combine with OCR body text
            if t1_chars > 50:
                combined_text = f"{t1_text}\n\n=== OCR EXTRACTED CONTENT ===\n\n{t2_text}"
                extraction_method = 'hybrid_pymupdf_ocr'
            else:
                combined_text = t2_text
                extraction_method = 'tesseract_ocr'

            return {
                'success': True,
                'text': combined_text,
                'hyperlinks': hyperlinks,
                'method': extraction_method,
                'pages': page_count,
                'characters': len(combined_text),
                'processing_time': processing_time,
            }

        # If PyMuPDF had partial text, use whatever we got as fallback
        if t1_chars > 0:
            return {
                'success': True,
                'text': t1_text,
                'hyperlinks': hyperlinks,
                'method': 'pymupdf_partial_fallback',
                'pages': page_count,
                'characters': t1_chars,
                'processing_time': processing_time,
            }

        return {
            'success': False,
            'error': f"Unreadable PDF. PyMuPDF extracted {t1_chars} chars and Tesseract OCR extracted {t2_chars} chars.",
            'text': '',
            'hyperlinks': [],
            'method': 'text_extraction_failed',
            'processing_time': processing_time,
        }

    except Exception as e:
        if doc:
            doc.close()
        return {
            'success': False,
            'error': f"PDF text extraction failed: {str(e)}",
            'text': '',
            'hyperlinks': [],
            'method': 'pymupdf_failed',
            'processing_time': time.time() - start_time,
        }


def process_resume_file(file_path: str) -> Dict[str, Any]:
    """
    Main entry point used by main_resume_processor.py to extract text from a PDF.
    """
    try:
        path_obj = Path(file_path)

        if not path_obj.exists():
            return {
                'success': False,
                'error': f'File not found: {file_path}',
                'text': ''
            }

        if path_obj.suffix.lower() != '.pdf':
            return {
                'success': False,
                'error': f'Only PDF files are supported. Got: {path_obj.suffix}',
                'text': ''
            }

        # Extract text via Hybrid 2-tier fallback
        result = extract_pdf_text(str(path_obj))

        if not result['success']:
            return result

        # Clean extracted text
        cleaned_text = clean_resume_text(result['text'])

        return {
            'success': True,
            'text': cleaned_text,
            'hyperlinks': result.get('hyperlinks', []),
            'method': result.get('method', 'unknown'),
            'metadata': {
                'file_size': path_obj.stat().st_size,
                'pages': result.get('pages', 0),
                'characters': len(cleaned_text),
                'processing_time': result.get('processing_time', 0),
            },
        }

    except Exception as e:
        return {
            'success': False,
            'error': f"Resume processing failed: {str(e)}",
            'text': ''
        }