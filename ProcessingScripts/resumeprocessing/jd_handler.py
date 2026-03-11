"""
JD (Job Description) Job Processing Handler
=============================================
Contains all the business logic for processing JD jobs from BullMQ.

This module handles:
- Downloading the JD PDF from S3
- Processing with AI (via jd_processor.py)
- Sending extracted data back to the backend API
- Cleanup and error handling

Called by main.py worker for each job received from the 'jd-processing' queue.

Job Data Expected:
    {
        "jdId":           "MongoDB ObjectId string",
        "s3Key":          "File path in S3 bucket",
        "s3Bucket":       "jds",
        "fileName":       "Original file name"
    }
"""

import logging
from typing import Any, Dict

from .jd_processor import process_single_jd_file
from .s3_handler import download_from_s3, cleanup_temp_file
from .api_client import (
    update_jd_status,
    send_jd_extracted_data,
    notify_jd_processing_failed,
)

logger = logging.getLogger(__name__)


async def process_jd_job(job: Any, job_token: str) -> Dict[str, Any]:
    """
    Process a single JD job from the BullMQ queue.

    Args:
        job:       BullMQ Job object
        job_token: BullMQ job token (used for lock extension on long jobs)

    Returns:
        Dictionary with success status and metadata

    Raises:
        Exception: Job will be retried by BullMQ on failure
    """
    job_id = job.id
    job_data = job.data

    logger.info(f"{'='*60}")
    logger.info(f"📋 Processing JD Job ID: {job_id}")
    logger.info(f"{'='*60}")

    # Extract job parameters
    jd_id = job_data.get('jdId')
    s3_key = job_data.get('s3Key')
    s3_bucket = job_data.get('s3Bucket', 'jds')
    file_name = job_data.get('fileName', 'jd.pdf')

    if not jd_id or not s3_key:
        error_msg = f"Missing required fields: jdId={jd_id}, s3Key={s3_key}"
        logger.error(f"❌ {error_msg}")
        raise ValueError(error_msg)

    temp_file_path = None

    try:
        # ========================================
        # STEP 1: Update status to 'processing'
        # ========================================
        logger.info(f"📝 Step 1/5: Updating status to 'processing'")
        await update_jd_status(jd_id, 'processing')

        # ========================================
        # STEP 2: Download JD PDF from S3
        # ========================================
        logger.info(f"📥 Step 2/5: Downloading from S3")
        logger.info(f"   Bucket: {s3_bucket}")
        logger.info(f"   Key:    {s3_key}")
        temp_file_path = download_from_s3(s3_key, s3_bucket)
        logger.info(f"   ✅ Downloaded to: {temp_file_path}")

        # ========================================
        # STEP 3: Process / extract data
        # ========================================
        logger.info(f"🤖 Step 3/5: Processing JD")
        logger.info(f"   File: {file_name}")
        extracted_data = await process_single_jd_file(temp_file_path)

        if "error" in extracted_data:
            error_msg = extracted_data['error']
            logger.error(f"❌ JD extraction failed: {error_msg}")
            raise Exception(error_msg)

        logger.info(f"   ✅ Extraction complete")

        # ========================================
        # STEP 4: Send extracted data to backend
        # ========================================
        logger.info(f"📤 Step 4/5: Sending extracted data to backend API")
        await send_jd_extracted_data(jd_id, extracted_data)
        logger.info(f"   ✅ Data saved")

        # ========================================
        # STEP 5: Update status to 'completed'
        # ========================================
        logger.info(f"✅ Step 5/5: Marking as 'completed'")
        await update_jd_status(jd_id, 'completed')

        logger.info(f"🎉 JD Job {job_id} finished successfully")
        return {
            "success": True,
            "jdId": jd_id,
            "fileName": file_name,
        }

    except Exception as exc:
        logger.error(f"❌ JD Job {job_id} failed: {exc}", exc_info=True)

        try:
            await notify_jd_processing_failed(jd_id, str(exc))
        except Exception as notify_err:
            logger.error(f"⚠️  Could not update failed status: {notify_err}")

        raise  # Let BullMQ handle retries

    finally:
        # Always clean up the temp file
        if temp_file_path:
            cleanup_temp_file(temp_file_path)
            logger.info(f"🧹 Temp file cleaned up")
