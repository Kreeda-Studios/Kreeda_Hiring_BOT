#!/usr/bin/env python3
"""
Resume PDF Text Extraction - Production Version

Extracts text from resume PDF files using PyMuPDF only.
No OCR support - returns false for image-based PDFs.
"""

import os
import fitz  # PyMuPDF
import re
import time
from typing import Dict, Any
from pathlib import Path


def extract_pdf_text(pdf_path: str) -> Dict[str, Any]:
    """Extract text from PDF using PyMuPDF"""
    try:
        start_time = time.time()
        
        doc = fitz.open(pdf_path)
        text_blocks = []
        total_chars = 0
        
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text = page.get_text()
            
            if text.strip():
                text_blocks.append(text)
                total_chars += len(text)
        
        doc.close()
        
        # If no text extracted, it's likely an image-based PDF
        if total_chars < 50:
            return {
                'success': False,
                'error': 'PDF appears to be image-based. OCR not supported.',
                'text': '',
                'method': 'text_extraction_failed'
            }
        
        full_text = '\n\n'.join(text_blocks)
        processing_time = time.time() - start_time
        
        return {
            'success': True,
            'text': full_text,
            'method': 'pymupdf',
            'pages': len(text_blocks),
            'characters': total_chars,
            'processing_time': processing_time
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"PDF text extraction failed: {str(e)}",
            'text': '',
            'method': 'pymupdf_failed'
        }


def clean_resume_text(text: str) -> str:
    """Clean and normalize resume text"""
    if not text:
        return ''
    
    # Remove excessive whitespace
    text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
    text = re.sub(r' {2,}', ' ', text)      # Max 1 space
    text = re.sub(r'\t+', ' ', text)        # Replace tabs with spaces
    
    # Remove common PDF artifacts
    text = re.sub(r'\x00', '', text)        # Null bytes
    text = re.sub(r'[^\x20-\x7E\n\r\t]', ' ', text)  # Non-printable chars
    
    # Normalize common resume sections
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


def validate_resume_text(text: str) -> bool:
    """Simple validation - check if text looks like a resume"""
    if not text or len(text) < 100:
        return False
    
    # Check for common resume indicators
    resume_indicators = [
        r'\b(?:experience|education|skills|projects|work)\b',
        r'\b(?:email|phone|contact)\b',
        r'\b(?:university|college|degree)\b'
    ]
    
    indicators_found = 0
    for pattern in resume_indicators:
        if re.search(pattern, text, re.IGNORECASE):
            indicators_found += 1
    
    return indicators_found >= 2


def process_resume_file(file_path: str) -> Dict[str, Any]:
    """
    Main function to extract text from resume PDF file
    Returns single result - success/failure with text
    """
    try:
        file_path = Path(file_path)
        
        if not file_path.exists():
            return {
                'success': False,
                'error': f'File not found: {file_path}',
                'text': ''
            }
        
        file_ext = file_path.suffix.lower()
        
        # Only support PDF files
        if file_ext != '.pdf':
            return {
                'success': False,
                'error': f'Only PDF files supported. Got: {file_ext}',
                'text': ''
            }
        
        # Extract text from PDF
        result = extract_pdf_text(str(file_path))
        
        if not result['success']:
            return result
        
        # Clean the extracted text
        cleaned_text = clean_resume_text(result['text'])
        
        # Validate text quality
        if not validate_resume_text(cleaned_text):
            return {
                'success': False,
                'error': 'Extracted text does not appear to be a valid resume',
                'text': ''
            }
        
        return {
            'success': True,
            'text': cleaned_text,
            'metadata': {
                'file_size': file_path.stat().st_size,
                'pages': result.get('pages', 0),
                'characters': len(cleaned_text),
                'processing_time': result.get('processing_time', 0)
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"Resume processing failed: {str(e)}",
            'text': ''
        }