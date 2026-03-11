"""
S3 File Download Handler
=========================
Handles downloading resume files from S3-compatible storage (MinIO/AWS S3) to temporary locations.
Supports concurrent processing by using unique temp files.
"""

import os
import tempfile
import logging
from pathlib import Path
from typing import Optional

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)


def get_s3_client() -> Minio:
    """
    Create and return an S3 client using environment variables
    Compatible with AWS S3 and S3-compatible services (MinIO)
    
    Environment Variables:
        S3_ENDPOINT: S3 server endpoint (e.g., 's3:9000' or 's3.amazonaws.com')
        S3_ACCESS_KEY: Access key for authentication
        S3_SECRET_KEY: Secret key for authentication
        S3_USE_SSL: Whether to use SSL ('true' or 'false')
    
    Returns:
        Configured Minio client instance (compatible with S3)
    """
    endpoint = os.getenv('S3_ENDPOINT', 'localhost:9000')
    access_key = os.getenv('S3_ACCESS_KEY', 'minioadmin')
    secret_key = os.getenv('S3_SECRET_KEY', 'minioadmin')
    use_ssl = os.getenv('S3_USE_SSL', 'false').lower() == 'true'
    
    return Minio(
        endpoint,
        access_key=access_key,
        secret_key=secret_key,
        secure=use_ssl
    )


def download_from_s3(s3_key: str, bucket: str) -> Path:
    """
    Download a file from S3 to a temporary location
    
    This function:
    1. Creates a unique temporary file with proper extension
    2. Downloads the file from S3
    3. Returns the path to the temp file
    
    The caller is responsible for cleaning up the temp file after processing.
    
    Args:
        s3_key: The file path in the S3 bucket (e.g., 'uuid_resume.pdf')
        bucket: The bucket name (e.g., 'resumes')
    
    Returns:
        Path object pointing to the downloaded temporary file
    
    Raises:
        S3Error: If the download fails (file not found, permission denied, etc.)
    
    Example:
        >>> temp_file = download_from_s3('abc123_resume.pdf', 'resumes')
        >>> # Process the file
        >>> temp_file.unlink()  # Clean up when done
    """
    logger.info(f"📥 Downloading {s3_key} from bucket '{bucket}'")
    
    # Get file extension from S3 key
    file_extension = Path(s3_key).suffix or '.pdf'
    
    # Create a unique temporary file
    temp_fd, temp_path_str = tempfile.mkstemp(
        suffix=file_extension,
        prefix='resume_',
        dir=None  # Uses system temp directory
    )
    os.close(temp_fd)  # Close the file descriptor
    temp_path = Path(temp_path_str)
    
    try:
        # Download from S3
        client = get_s3_client()
        client.fget_object(bucket, s3_key, str(temp_path))
        
        logger.info(f"✅ Downloaded to: {temp_path}")
        return temp_path
        
    except S3Error as e:
        # Clean up temp file if download failed
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"❌ Failed to download {s3_key}: {e}")
        raise
    except Exception as e:
        # Clean up temp file on any error
        if temp_path.exists():
            temp_path.unlink()
        logger.error(f"❌ Unexpected error downloading {s3_key}: {e}")
        raise


def cleanup_temp_file(file_path: Path) -> None:
    """
    Safely delete a temporary file
    
    Args:
        file_path: Path to the temporary file to delete
    
    Example:
        >>> temp_file = Path('/tmp/resume_abc123.pdf')
        >>> cleanup_temp_file(temp_file)
    """
    try:
        if file_path and file_path.exists():
            file_path.unlink()
            logger.info(f"🧹 Cleaned up: {file_path.name}")
    except Exception as e:
        logger.warning(f"⚠️  Failed to cleanup {file_path}: {e}")
