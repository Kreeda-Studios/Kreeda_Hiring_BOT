"""
Main Worker - BullMQ Queue Listener

This module listens to the 'Resume Processing' queue and processes resume jobs
using the BullMQ Python library for proper BullMQ protocol implementation.
"""

import asyncio
import logging
import os
from typing import Any, Dict

from bullmq import Worker
from dotenv import load_dotenv

# Import processing functions from resumeprocessing package
from resumeprocessing.main import process_single_resume_file
from resumeprocessing.s3_download import download_from_s3, cleanup_temp_file
from resumeprocessing.api_updater import (
    update_resume_status,
    send_extracted_data,
    notify_processing_complete,
    notify_processing_failed
)

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration constants
REDIS_HOST = os.getenv('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))
QUEUE_NAME = 'resume-processing'


async def process_job_handler(job: Any, job_token: str) -> Dict[str, Any]:
    """
    Process a single resume job.

    This function is called by BullMQ worker for each job in the queue.

    Flow:
    1. Extract job data (resumeId, s3Key, bucket)
    2. Update status to 'processing'
    3. Download file from S3 to temporary location
    4. Process resume with AI extraction
    5. Send extracted data to backend API
    6. Update status to 'completed'
    7. Cleanup temporary file

    Args:
        job: BullMQ Job object containing data and metadata
        job_token: Token for job locking (managed by BullMQ)

    Returns:
        Dictionary containing processing result

    Raises:
        Exception: Any error during processing (handled by BullMQ for retries)
    """
    job_id = job.id
    job_data = job.data

    logger.info(f"🎯 Processing Job ID: {job_id}")
    logger.debug(f"Job Data: {job_data}")

    # Extract job parameters
    resume_id = job_data.get('resumeId')
    s3_key = job_data.get('s3Key')
    s3_bucket = job_data.get('s3Bucket', 'resumes')
    file_name = job_data.get('fileName', 'unknown.pdf')

    temp_file_path = None

    try:
        # Step 1: Update status to 'processing'
        logger.info(f"📝 Updating resume status to 'processing'")
        await update_resume_status(resume_id, 'processing')

        # Step 2: Download file from S3 to temp location
        logger.info(f"📥 Downloading {s3_key} from bucket '{s3_bucket}'")
        temp_file_path = download_from_s3(s3_key, s3_bucket)

        # Step 3: Process the resume with AI extraction
        logger.info(f"🤖 Processing resume with AI: {file_name}")
        extracted_data = await process_single_resume_file(temp_file_path)

        # Check if extraction returned an error
        if "error" in extracted_data:
            error_msg = extracted_data['error']
            logger.error(f"❌ Extraction failed: {error_msg}")
            raise Exception(error_msg)

        # Step 4: Send extracted data to backend API
        logger.info(f"📤 Sending extracted data to backend")
        await send_extracted_data(resume_id, extracted_data)

        # Step 5: Update status to 'completed'
        logger.info(f"✅ Marking resume as completed")
        await update_resume_status(resume_id, 'completed')

        logger.info(f"🎉 Job {job_id} completed successfully")
        
        return {
            'success': True,
            'resumeId': resume_id,
            'fileName': file_name,
            'status': 'completed'
        }

    except Exception as e:
        error_message = str(e)
        logger.error(f"❌ Job {job_id} failed: {error_message}", exc_info=True)
        
        # Update status to 'failed' with error message
        try:
            await notify_processing_failed(resume_id, error_message)
        except Exception as status_error:
            logger.error(f"⚠️  Failed to update error status: {status_error}")
        
        # Re-raise for BullMQ retry logic
        raise

    finally:
        # Step 6: Always cleanup temporary file
        if temp_file_path:
            logger.info(f"🧹 Cleaning up temporary file")
            cleanup_temp_file(temp_file_path)


async def on_job_completed(job: Any, result: Any) -> None:
    """
    Callback handler for successfully completed jobs.

    Args:
        job: Completed BullMQ Job object
        result: Result returned from job processor
    """
    logger.info(f"✅ Job {job.id} completed with result: {result}")


async def on_job_failed(job: Any, error: Exception) -> None:
    """
    Callback handler for failed jobs.

    Args:
        job: Failed BullMQ Job object
        error: Exception that caused the failure
    """
    logger.error(f"❌ Job {job.id} failed: {str(error)}", exc_info=True)


async def listen_to_queue() -> None:
    """
    Main worker function that creates and starts a BullMQ worker.

    The worker automatically handles:
    - Job polling and locking
    - State transitions (waiting -> active -> completed/failed)
    - Retries and error handling
    - Graceful shutdown
    """
    logger.info("🚀 Starting BullMQ Worker")
    logger.info(f"📡 Redis at {REDIS_HOST}:{REDIS_PORT}")
    logger.info(f"📋 Queue: '{QUEUE_NAME}'")

    worker = Worker(
        QUEUE_NAME,
        process_job_handler,
        {
            'connection': {
                'host': REDIS_HOST,
                'port': REDIS_PORT,
            },
            'concurrency': 16,
        }
    )

    # Register event handlers
    worker.on('completed', on_job_completed)
    worker.on('failed', on_job_failed)

    logger.info("✅ Worker ready - waiting for jobs...")

    try:
        await worker.run()
    except KeyboardInterrupt:
        logger.info("🛑 Worker shutting down gracefully...")
    finally:
        await worker.close()
        logger.info("👋 Worker closed")


def main() -> None:
    """Entry point for the worker application."""
    try:
        asyncio.run(listen_to_queue())
    except Exception as e:
        logger.critical(f"❌ Worker failed to start: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()

