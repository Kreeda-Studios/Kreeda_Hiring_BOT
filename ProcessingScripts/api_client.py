"""
Backend API Client
Handles communication with the FullStack backend API
"""

import os
import logging
from typing import Dict, Any, Optional
import httpx

logger = logging.getLogger(__name__)

# Configuration
API_BASE_URL = os.getenv('API_BASE_URL', 'http://nextjs:3000')
API_TIMEOUT = int(os.getenv('API_TIMEOUT', '30'))


class BackendAPIClient:
    """
    Client for communicating with the FullStack backend API
    """
    
    def __init__(self, base_url: str = API_BASE_URL):
        self.base_url = base_url.rstrip('/')
        self.timeout = API_TIMEOUT
    
    async def update_resume_data(
        self,
        resume_id: str,
        extracted_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """
        Update resume with extracted data
        
        Args:
            resume_id: MongoDB resume ID
            extracted_data: Extracted resume data from AI processing
        
        Returns:
            API response dictionary
        
        Raises:
            httpx.HTTPError: If the request fails
        """
        url = f"{self.base_url}/api/resume/update-processed"
        
        payload = {
            "resumeId": resume_id,
            "extractedData": extracted_data
        }
        
        logger.info(f"Updating resume {resume_id} via API")
        logger.debug(f"Payload: {payload}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully updated resume {resume_id}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error updating resume {resume_id}: {e.response.status_code} - {e.response.text}")
            raise
        except httpx.RequestError as e:
            logger.error(f"Request error updating resume {resume_id}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error updating resume {resume_id}: {e}")
            raise
    
    async def update_resume_status(
        self,
        resume_id: str,
        status: str,
        error: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update resume processing status
        
        Args:
            resume_id: MongoDB resume ID
            status: New status ('processing', 'completed', 'failed')
            error: Optional error message if status is 'failed'
        
        Returns:
            API response dictionary
        """
        url = f"{self.base_url}/api/resume/update-status"
        
        payload = {
            "resumeId": resume_id,
            "status": status
        }
        
        if error:
            payload["error"] = error
        
        logger.info(f"Updating resume {resume_id} status to {status}")
        
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                
                result = response.json()
                logger.info(f"Successfully updated status for resume {resume_id}")
                return result
                
        except httpx.HTTPError as e:
            logger.error(f"Error updating status for resume {resume_id}: {e}")
            raise
    
    async def health_check(self) -> bool:
        """
        Check if the API is reachable
        
        Returns:
            True if API is healthy, False otherwise
        """
        url = f"{self.base_url}/api/health"
        
        try:
            async with httpx.AsyncClient(timeout=5) as client:
                response = await client.get(url)
                return response.status_code == 200
        except Exception as e:
            logger.warning(f"Health check failed: {e}")
            return False


# Convenience functions

async def update_resume(resume_id: str, extracted_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Convenience function to update resume data
    
    Args:
        resume_id: MongoDB resume ID
        extracted_data: Extracted resume data
    
    Returns:
        API response
    """
    client = BackendAPIClient()
    return await client.update_resume_data(resume_id, extracted_data)


async def update_status(resume_id: str, status: str, error: Optional[str] = None) -> Dict[str, Any]:
    """
    Convenience function to update resume status
    
    Args:
        resume_id: MongoDB resume ID
        status: New status
        error: Optional error message
    
    Returns:
        API response
    """
    client = BackendAPIClient()
    return await client.update_resume_status(resume_id, status, error)
