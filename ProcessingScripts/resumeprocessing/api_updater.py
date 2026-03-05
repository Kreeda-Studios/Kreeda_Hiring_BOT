"""
Backend API Client
==================
Handles communication with the FullStack backend API.
Used to update resume processing status and data.
"""

import os
import logging
from typing import Dict, Any, Optional

import httpx

logger = logging.getLogger(__name__)


def get_api_base_url() -> str:
    """
    Get the base URL for the backend API
    
    Environment Variables:
        API_BASE_URL: Base URL of the FullStack API (default: 'http://nextjs:3000')
    
    Returns:
        Base URL string
    """
    return os.getenv('API_BASE_URL', 'http://nextjs:3000')


async def update_resume_status(
    resume_id: str,
    status: str,
    error: Optional[str] = None
) -> Dict[str, Any]:
    """
    Update the processing status of a resume
    
    Args:
        resume_id: MongoDB ObjectId of the resume
        status: New status ('processing', 'completed', or 'failed')
        error: Optional error message (used when status is 'failed')
    
    Returns:
        API response as a dictionary
    
    Raises:
        httpx.HTTPError: If the API request fails
    
    Example:
        >>> await update_resume_status('507f1f77bcf86cd799439011', 'processing')
        >>> await update_resume_status('507f1f77bcf86cd799439011', 'failed', 'File corrupted')
    """
    base_url = get_api_base_url()
    url = f"{base_url}/api/resume/update-status"
    
    payload = {
        "resumeId": resume_id,
        "status": status
    }
    
    if error:
        payload["error"] = error
    
    logger.info(f"📤 Updating resume {resume_id[:8]}... status to '{status}'")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Status updated successfully")
            return result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"❌ Request failed: {e}")
        raise


async def send_extracted_data(
    resume_id: str,
    extracted_data: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Send extracted resume data to the backend API
    
    This updates the resume document with all the AI-extracted information
    including profile, skills, experience, projects, education, etc.
    
    Args:
        resume_id: MongoDB ObjectId of the resume
        extracted_data: Dictionary containing all extracted data from AI processing
    
    Returns:
        API response as a dictionary
    
    Raises:
        httpx.HTTPError: If the API request fails
    
    Example:
        >>> data = {
        ...     "profile": {"name": "John Doe", "email": "john@example.com"},
        ...     "skills": {"provided": ["Python", "JavaScript"]},
        ...     "experience": {...}
        ... }
        >>> await send_extracted_data('507f1f77bcf86cd799439011', data)
    """
    base_url = get_api_base_url()
    url = f"{base_url}/api/resume/update-processed"
    
    payload = {
        "resumeId": resume_id,
        "extractedData": extracted_data
    }
    
    logger.info(f"📤 Sending extracted data for resume {resume_id[:8]}...")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            result = response.json()
            logger.info(f"✅ Extracted data saved successfully")
            return result
            
    except httpx.HTTPStatusError as e:
        logger.error(f"❌ HTTP {e.response.status_code}: {e.response.text}")
        raise
    except httpx.RequestError as e:
        logger.error(f"❌ Request failed: {e}")
        raise


async def notify_processing_complete(
    resume_id: str,
    extracted_data: Dict[str, Any]
) -> None:
    """
    Complete workflow: Send data and mark as completed
    
    This is a convenience function that:
    1. Sends the extracted data to the backend
    2. Updates the status to 'completed'
    
    Args:
        resume_id: MongoDB ObjectId of the resume
        extracted_data: Dictionary containing all extracted data
    
    Raises:
        httpx.HTTPError: If any API request fails
    
    Example:
        >>> await notify_processing_complete('507f1f77bcf86cd799439011', extracted_data)
    """
    # Send the extracted data
    await send_extracted_data(resume_id, extracted_data)
    
    # Mark as completed
    await update_resume_status(resume_id, 'completed')


async def notify_processing_failed(resume_id: str, error_message: str) -> None:
    """
    Notify the backend that processing failed
    
    Args:
        resume_id: MongoDB ObjectId of the resume
        error_message: Description of what went wrong
    
    Example:
        >>> await notify_processing_failed('507f1f77bcf86cd799439011', 'Invalid PDF format')
    """
    try:
        await update_resume_status(resume_id, 'failed', error_message)
    except Exception as e:
        logger.error(f"⚠️  Failed to update error status: {e}")
