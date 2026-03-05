"""
S3/MinIO File Handler
Handles downloading and uploading files from MinIO/S3 storage
"""

import os
import tempfile
from pathlib import Path
from typing import Optional
import logging

from minio import Minio
from minio.error import S3Error

logger = logging.getLogger(__name__)

# Configuration from environment
MINIO_ENDPOINT = os.getenv('MINIO_ENDPOINT', 'localhost:9000')
MINIO_ACCESS_KEY = os.getenv('MINIO_ACCESS_KEY', 'minioadmin')
MINIO_SECRET_KEY = os.getenv('MINIO_SECRET_KEY', 'minioadmin')
MINIO_USE_SSL = os.getenv('MINIO_USE_SSL', 'false').lower() == 'true'
MINIO_BUCKET = os.getenv('MINIO_BUCKET', 'resumes')

# Initialize MinIO client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=MINIO_USE_SSL
)


class S3FileHandler:
    """
    Handles S3/MinIO file operations with temporary storage
    Supports concurrent file processing
    """
    
    def __init__(self, bucket_name: str = MINIO_BUCKET):
        self.bucket_name = bucket_name
        self.client = minio_client
        self._ensure_bucket_exists()
    
    def _ensure_bucket_exists(self):
        """Ensure the bucket exists"""
        try:
            if not self.client.bucket_exists(self.bucket_name):
                logger.warning(f"Bucket '{self.bucket_name}' does not exist")
        except S3Error as e:
            logger.error(f"Error checking bucket: {e}")
    
    def download_to_temp(self, s3_key: str, suffix: Optional[str] = None) -> Path:
        """
        Download a file from S3 to a temporary location
        
        Args:
            s3_key: The S3 object key (file path in bucket)
            suffix: Optional file suffix (e.g., '.pdf')
        
        Returns:
            Path object pointing to the temporary file
        
        Raises:
            S3Error: If download fails
        """
        try:
            # Determine file extension
            if suffix is None:
                suffix = Path(s3_key).suffix or '.pdf'
            
            # Create temporary file
            temp_file = tempfile.NamedTemporaryFile(
                delete=False,
                suffix=suffix,
                prefix='resume_'
            )
            temp_path = Path(temp_file.name)
            temp_file.close()
            
            logger.info(f"Downloading {s3_key} from bucket '{self.bucket_name}' to {temp_path}")
            
            # Download from MinIO
            self.client.fget_object(
                self.bucket_name,
                s3_key,
                str(temp_path)
            )
            
            logger.info(f"Successfully downloaded {s3_key}")
            return temp_path
            
        except S3Error as e:
            logger.error(f"Failed to download {s3_key}: {e}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error downloading {s3_key}: {e}")
            raise
    
    def cleanup_temp_file(self, file_path: Path) -> None:
        """
        Clean up a temporary file
        
        Args:
            file_path: Path to the temporary file to delete
        """
        try:
            if file_path.exists():
                file_path.unlink()
                logger.info(f"Cleaned up temporary file: {file_path}")
        except Exception as e:
            logger.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    def upload_file(self, local_path: Path, s3_key: str) -> str:
        """
        Upload a file to S3/MinIO
        
        Args:
            local_path: Path to local file
            s3_key: Destination key in S3
        
        Returns:
            The S3 key of uploaded file
        """
        try:
            logger.info(f"Uploading {local_path} to {s3_key}")
            
            self.client.fput_object(
                self.bucket_name,
                s3_key,
                str(local_path)
            )
            
            logger.info(f"Successfully uploaded to {s3_key}")
            return s3_key
            
        except S3Error as e:
            logger.error(f"Failed to upload {local_path}: {e}")
            raise


def download_resume(s3_key: str, bucket: Optional[str] = None) -> Path:
    """
    Convenience function to download a resume file
    
    Args:
        s3_key: S3 object key
        bucket: Optional bucket name (uses default if not provided)
    
    Returns:
        Path to temporary file
    """
    handler = S3FileHandler(bucket or MINIO_BUCKET)
    return handler.download_to_temp(s3_key)


def cleanup_file(file_path: Path) -> None:
    """
    Convenience function to cleanup a temporary file
    
    Args:
        file_path: Path to file to delete
    """
    handler = S3FileHandler()
    handler.cleanup_temp_file(file_path)
