"""
Resume Job Processing Handler
==============================
Contains all the business logic for processing resume jobs.

This module handles:
- Downloading files from S3
- Processing with AI
- Updating backend API
- Cleanup and error handling

Called by main.py worker for each job received from BullMQ.
"""

import logging
from typing import Any, Dict

from .processor import process_single_resume_file
from .s3_handler import download_from_s3, cleanup_temp_file
from .api_client import (
    update_resume_status,
    send_extracted_data,
    notify_processing_failed
)

logger = logging.getLogger(__name__)


async def process_resume_job(job: Any, job_token: str) -> Dict[str, Any]:
    """
    Process a single resume job from the queue.
    
    This function contains all the business logic for resume processing.
    
    Job Data Expected:
        - resumeId: MongoDB ObjectId string
        - s3Key: File path in S3 bucket
        - s3Bucket: Bucket name (usually 'resumes')
        - fileName: Original file name
    
    Returns:
        Dictionary with success status and metadata
    
    Raises:
        Exception: Job will be retried by BullMQ
    """
    job_id = job.id
    job_data = job.data
    
    logger.info(f"{'='*60}")
    logger.info(f"🎯 Processing Job ID: {job_id}")
    logger.info(f"{'='*60}")
    
    # Extract job parameters
    resume_id = job_data.get('resumeId')
    s3_key = job_data.get('s3Key')
    s3_bucket = job_data.get('s3Bucket', 'resumes')
    file_name = job_data.get('fileName', 'resume.pdf')
    
    if not resume_id or not s3_key:
        error_msg = f"Missing required fields: resumeId={resume_id}, s3Key={s3_key}"
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)
    
    temp_file_path = None
    
    try:
        # ========================================
        # STEP 1: Update status to 'processing'
        # ========================================
        logger.info(f"📝 Step 1/5: Updating status to 'processing'")
        await update_resume_status(resume_id, 'processing')
        
        # ========================================
        # STEP 2: Download file from S3
        # ========================================
        logger.info(f"📥 Step 2/5: Downloading from S3")
        logger.info(f"   Bucket: {s3_bucket}")
        logger.info(f"   Key: {s3_key}")
        temp_file_path = download_from_s3(s3_key, s3_bucket)
        logger.info(f"   ✅ Downloaded to: {temp_file_path}")
        
        # ========================================
        # STEP 3: Process with AI
        # ========================================
        logger.info(f"🤖 Step 3/5: Processing with AI")
        logger.info(f"   File: {file_name}")
        extracted_data = await process_single_resume_file(temp_file_path)
        
        # Check for errors in extraction
        if "error" in extracted_data:
            error_msg = extracted_data['error']
            logger.error(f"❌ AI extraction failed: {error_msg}")
            raise Exception(error_msg)
        
        logger.info(f"   ✅ Extraction complete")
        
        # ========================================
        # STEP 4: Send data to backend API
        # ========================================
        logger.info(f"📤 Step 4/5: Sending data to backend")
        await send_extracted_data(resume_id, extracted_data)
        logger.info(f"   ✅ Data saved to database")
        
        # ========================================
        # STEP 5: Update status to 'completed'
        # ========================================
        logger.info(f"✅ Step 5/5: Marking as completed")
        await update_resume_status(resume_id, 'completed')
        
        logger.info(f"{'='*60}")
        logger.info(f"🎉 SUCCESS - Job {job_id} completed")
        logger.info(f"{'='*60}")
        
        return {
            'success': True,
            'resumeId': resume_id,
            'fileName': file_name,
            'status': 'completed'
        }
        
    except Exception as e:
        error_message = str(e)
        logger.error(f"{'='*60}")
        logger.error(f"❌ FAILED - Job {job_id}")
        logger.error(f"Error: {error_message}")
        logger.error(f"{'='*60}", exc_info=True)
        
        # Update backend with failure status
        try:
            await notify_processing_failed(resume_id, error_message)
        except Exception as status_error:
            logger.error(f"⚠️  Could not update failure status: {status_error}")
        
        # Re-raise for BullMQ retry mechanism
        raise
        
    finally:
        # ========================================
        # CLEANUP: Always delete temp file
        # ========================================
        if temp_file_path:
            logger.info(f"🧹 Cleaning up temporary file")
            cleanup_temp_file(temp_file_path)
