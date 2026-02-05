"""
Backend API Client

Clean, standardized HTTP client for all backend API calls.
Handles authentication, retries, timeouts, and error handling.

Usage:
    from common.api_client import api
    
    # GET request
    job = api.get(f"/jobs/{job_id}")
    
    # POST request
    result = api.post("/updates/score", data=score_data)
    
    # PATCH request
    updated = api.patch(f"/jobs/{job_id}", data=updates)
    
    # PUT request
    updated = api.put(f"/updates/resume/{resume_id}", data=resume_data)
"""

import os
import requests
from typing import Dict, Any, Optional, Union
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import logging

logger = logging.getLogger(__name__)


class APIClient:
    """
    Clean HTTP client for backend API calls.
    
    Features:
    - Automatic retries with exponential backoff
    - Request/response logging
    - Standardized error handling
    - Authentication headers
    - Timeout management
    """
    
    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        timeout: int = 30,
        max_retries: int = 3
    ):
        """
        Initialize API client.
        
        Args:
            base_url: Base API URL (defaults to env BACKEND_API_URL)
            api_key: API key for authentication (defaults to env BACKEND_API_KEY)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.base_url = (
            base_url or 
            os.getenv('BACKEND_API_URL') or 
            os.getenv('API_BASE_URL') or 
            'http://localhost:3001/api'
        ).rstrip('/')
        
        self.api_key = api_key or os.getenv('BACKEND_API_KEY', '')
        self.timeout = timeout
        
        # Create session with retry strategy
        self.session = requests.Session()
        
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,  # Wait 1s, 2s, 4s between retries
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET", "POST", "PUT", "PATCH", "DELETE"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
    
    def _get_headers(self, extra_headers: Optional[Dict[str, str]] = None) -> Dict[str, str]:
        """Build request headers with authentication"""
        headers = {'Content-Type': 'application/json'}
        
        if self.api_key:
            headers['Authorization'] = f'Bearer {self.api_key}'
        
        if extra_headers:
            headers.update(extra_headers)
        
        return headers
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint"""
        endpoint = endpoint.lstrip('/')
        return f"{self.base_url}/{endpoint}"
    
    def _handle_response(self, response: requests.Response, endpoint: str) -> Any:
        """
        Handle API response and extract data.
        
        Returns the data directly, or raises exception on error.
        """
        try:
            response.raise_for_status()
            
            # Try to parse JSON
            try:
                result = response.json()
                
                # Backend returns {success, data, error} format
                if isinstance(result, dict):
                    if result.get('success') is False:
                        raise APIError(
                            result.get('error', 'Unknown error'),
                            endpoint=endpoint,
                            status_code=response.status_code
                        )
                    
                    # Return the data field if present, otherwise full result
                    return result.get('data', result)
                
                return result
                
            except ValueError:
                # Not JSON, return text
                return response.text
        
        except requests.exceptions.HTTPError as e:
            # Try to extract error message from response
            try:
                error_data = response.json()
                error_msg = error_data.get('error') or error_data.get('message') or str(e)
            except:
                error_msg = str(e)
            
            raise APIError(
                error_msg,
                endpoint=endpoint,
                status_code=response.status_code
            ) from e
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        GET request.
        
        Args:
            endpoint: API endpoint (e.g., "/jobs/123" or "jobs/123")
            params: Query parameters
            headers: Extra headers
            timeout: Custom timeout (overrides default)
        
        Returns:
            Response data (parsed from JSON)
        
        Raises:
            APIError: If request fails
        """
        url = self._build_url(endpoint)
        
        try:
            logger.debug(f"GET {url}")
            response = self.session.get(
                url,
                params=params,
                headers=self._get_headers(headers),
                timeout=timeout or self.timeout
            )
            return self._handle_response(response, endpoint)
        
        except requests.exceptions.RequestException as e:
            if not isinstance(e, requests.exceptions.HTTPError):
                raise APIError(
                    f"Request failed: {str(e)}",
                    endpoint=endpoint
                ) from e
            raise
    
    def post(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        POST request.
        
        Args:
            endpoint: API endpoint
            data: Request body (will be JSON-encoded)
            headers: Extra headers
            timeout: Custom timeout
        
        Returns:
            Response data
        """
        url = self._build_url(endpoint)
        
        try:
            logger.debug(f"POST {url}")
            response = self.session.post(
                url,
                json=data,
                headers=self._get_headers(headers),
                timeout=timeout or self.timeout
            )
            return self._handle_response(response, endpoint)
        
        except requests.exceptions.RequestException as e:
            if not isinstance(e, requests.exceptions.HTTPError):
                raise APIError(
                    f"Request failed: {str(e)}",
                    endpoint=endpoint
                ) from e
            raise
    
    def put(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        PUT request.
        
        Args:
            endpoint: API endpoint
            data: Request body
            headers: Extra headers
            timeout: Custom timeout
        
        Returns:
            Response data
        """
        url = self._build_url(endpoint)
        
        try:
            logger.debug(f"PUT {url}")
            response = self.session.put(
                url,
                json=data,
                headers=self._get_headers(headers),
                timeout=timeout or self.timeout
            )
            return self._handle_response(response, endpoint)
        
        except requests.exceptions.RequestException as e:
            if not isinstance(e, requests.exceptions.HTTPError):
                raise APIError(
                    f"Request failed: {str(e)}",
                    endpoint=endpoint
                ) from e
            raise
    
    def patch(
        self,
        endpoint: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        PATCH request.
        
        Args:
            endpoint: API endpoint
            data: Request body
            headers: Extra headers
            timeout: Custom timeout
        
        Returns:
            Response data
        """
        url = self._build_url(endpoint)
        
        try:
            logger.debug(f"PATCH {url}")
            response = self.session.patch(
                url,
                json=data,
                headers=self._get_headers(headers),
                timeout=timeout or self.timeout
            )
            return self._handle_response(response, endpoint)
        
        except requests.exceptions.RequestException as e:
            if not isinstance(e, requests.exceptions.HTTPError):
                raise APIError(
                    f"Request failed: {str(e)}",
                    endpoint=endpoint
                ) from e
            raise
    
    def delete(
        self,
        endpoint: str,
        headers: Optional[Dict[str, str]] = None,
        timeout: Optional[int] = None
    ) -> Any:
        """
        DELETE request.
        
        Args:
            endpoint: API endpoint
            headers: Extra headers
            timeout: Custom timeout
        
        Returns:
            Response data
        """
        url = self._build_url(endpoint)
        
        try:
            logger.debug(f"DELETE {url}")
            response = self.session.delete(
                url,
                headers=self._get_headers(headers),
                timeout=timeout or self.timeout
            )
            return self._handle_response(response, endpoint)
        
        except requests.exceptions.RequestException as e:
            if not isinstance(e, requests.exceptions.HTTPError):
                raise APIError(
                    f"Request failed: {str(e)}",
                    endpoint=endpoint
                ) from e
            raise


class APIError(Exception):
    """Custom exception for API errors"""
    
    def __init__(self, message: str, endpoint: str = "", status_code: Optional[int] = None):
        self.message = message
        self.endpoint = endpoint
        self.status_code = status_code
        super().__init__(self.format_message())
    
    def format_message(self) -> str:
        """Format error message with context"""
        msg = f"API Error: {self.message}"
        if self.endpoint:
            msg += f" (endpoint: {self.endpoint})"
        if self.status_code:
            msg += f" [HTTP {self.status_code}]"
        return msg


# Global singleton instance
api = APIClient()


# Convenience functions for common operations
def get_job(job_id: str) -> Dict[str, Any]:
    """Get job by ID"""
    return api.get(f"/jobs/{job_id}")


def update_job(job_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update job data"""
    return api.patch(f"/jobs/{job_id}", data=data)


def get_resume(resume_id: str) -> Dict[str, Any]:
    """Get resume by ID"""
    return api.get(f"/updates/resume/{resume_id}")


def update_resume(resume_id: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """Update resume data"""
    return api.put(f"/updates/resume/{resume_id}", data=data)


def save_score(job_id: str, resume_id: str, scores: Dict[str, Any]) -> Dict[str, Any]:
    """Save candidate score"""
    return api.post("/updates/score", data={
        'job_id': job_id,
        'resume_id': resume_id,
        **scores
    })


def get_scores(job_id: str) -> list:
    """Get all scores for a job"""
    return api.get(f"/updates/scores/{job_id}")
