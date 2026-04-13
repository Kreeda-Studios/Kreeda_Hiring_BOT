"""
FastAPI Server for Resume Intelligence Extraction Engine
======================================================
This module exposes a REST endpoint to process a candidate's resume from a provided S3 URL.
It downloads the resume, extracts the intelligence via the existing LLM pipeline, 
and returns a structured JSON response.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
import logging
from typing import Dict, Any

from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel, HttpUrl
import httpx

# Import core extraction logic from our existing main.py
from main import (
    extract_pdf_content,
    extract_resume_data,
    transform_output
)

# Configure basic logging for visibility and debugging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - [%(levelname)s] - %(message)s")
logger = logging.getLogger(__name__)

# Initialize FastAPI app instance
app = FastAPI(
    title="Resume Extraction API",
    description="Endpoint for extracting structured data from candidate resumes using public/pre-signed S3 links.",
    version="1.0.0"
)

# ──────────────────────────────────────────────
# Pydantic Schemas for Request & Responses
# ──────────────────────────────────────────────

class ResumeExtractRequest(BaseModel):
    """
    Schema for the incoming request payload.
    Requires a unique candidate ID and an accessible S3 URL pointing to the resume PDF.
    """
    candidate_id: str
    s3_link: HttpUrl


# ──────────────────────────────────────────────
# Helper Functions
# ──────────────────────────────────────────────

async def download_s3_file_to_temp(url: str) -> str:
    """
    Downloads a file asynchronously from a given URL to a temporary file on disk.
    
    Args:
        url (str): The pre-signed or public URL of the PDF to download.
        
    Returns:
        str: The absolute path to the downloaded temporary file.
        
    Raises:
        HTTPException: If the download fails (e.g., 404 Not Found, 403 Forbidden).
    """
    logger.info(f"Attempting to download file from: {url}")
    try:
        # Provide a generous timeout for downloading potentially large PDFs
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            
            # Immediately raise an exception for typical HTTP errors (e.g., 403, 404)
            response.raise_for_status()
            
            # Create an anonymous temporary file that we can clean up later
            fd, temp_file_path = tempfile.mkstemp(suffix=".pdf")
            with os.fdopen(fd, 'wb') as f:
                async for chunk in response.aiter_bytes(chunk_size=1024 * 64):
                    f.write(chunk)
            
            logger.info(f"Successfully downloaded file to temp path: {temp_file_path}")
            return temp_file_path

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error occurred while downloading file: {e.response.status_code}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to download resume from the provided link. HTTP Status: {e.response.status_code}"
        )
    except httpx.RequestError as e:
        logger.error(f"Request error while connecting to S3 link: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to establish a connection to the provided S3 link. Verify the URL is reachable."
        )
    except Exception as e:
        logger.error(f"Unexpected error during download: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred while downloading the resume."
        )

# ──────────────────────────────────────────────
# Primary API Endpoint
# ──────────────────────────────────────────────

@app.post("/extract-resume", status_code=status.HTTP_200_OK)
async def extract_resume_endpoint(payload: ResumeExtractRequest) -> Dict[str, Any]:
    """
    Primary endpoint that coordinates the extraction workflow:
    1. Validates the candidate ID and S3 link (handled automatically by FastAPI).
    2. Downloads the resume to a temporary file locally.
    3. Extracts raw text and links using PyMuPDF (delegated to a separate thread).
    4. Passes the raw text to the GPT pipeline defined in main.py for intelligence extraction.
    5. Returns the structured JSON, enriched with the incoming Candidate ID.
    """
    temp_pdf_path = None
    
    try:
        # 1. Download the PDF
        url_str = str(payload.s3_link)
        temp_pdf_path = await download_s3_file_to_temp(url_str)
        
        # 2. Extract raw text and links (using asyncio.to_thread to prevent blocking the event loop on I/O)
        logger.info(f"Extracting PDF content (Candidate ID: {payload.candidate_id})")
        try:
            raw_text, hyperlinks = await asyncio.to_thread(extract_pdf_content, temp_pdf_path)
        except Exception as e:
            logger.error(f"Failed to parse PDF document for candidate {payload.candidate_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to read the PDF document. It may be corrupted, encrypted, or not a valid PDF."
            )
            
        # Validate that the extracted text is substantial enough to process
        if not raw_text or not raw_text.strip():
            logger.warning(f"Empty or malformed text extracted for Candidate {payload.candidate_id}")
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Extracted resume text is empty or unreadable."
            )
            
        # 3. Process unstructured text via LLM
        logger.info(f"Calling LLM for data extraction (Candidate ID: {payload.candidate_id})")
        structured_data = await extract_resume_data(raw_text, hyperlinks)
        
        # 4. Transform Output matching existing application format
        final_result = transform_output(structured_data, raw_text)
        
        # 5. Inject candidate ID into the top level of the returned payload
        final_result["candidate_id"] = payload.candidate_id
        
        logger.info(f"Successfully finalized resume processing for Candidate ID: {payload.candidate_id}")
        return final_result

    except HTTPException:
        # Bubble up any known FastAPI exceptions we deliberately threw above
        raise
    except Exception as e:
        # Final catch-all to prevent server crashing on unknown errors
        logger.error(f"Unexpected error during resume processing (Candidate ID: {payload.candidate_id}): {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected system error occurred during the resume extraction process."
        )
    finally:
        # 6. Crucial step: Securely remove the temporary file to prevent disk exhaustion
        if temp_pdf_path and os.path.exists(temp_pdf_path):
            try:
                os.remove(temp_pdf_path)
                logger.debug(f"Cleaned up temporary file: {temp_pdf_path}")
            except Exception as e:
                logger.warning(f"Failed to clean up temporary file {temp_pdf_path}: {e}")

# ──────────────────────────────────────────────
# Application Bootstrapper
# ──────────────────────────────────────────────

if __name__ == "__main__":
    # Provides an execution profile directly from the module
    import uvicorn
    # uvicorn api:app --reload --host 0.0.0.0 --port 8000
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
