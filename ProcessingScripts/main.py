"""
BullMQ Queue Worker - Main Entry Point
=======================================
Minimal queue orchestration file.

This file ONLY handles:
- Queue configuration (names and concurrency)
- BullMQ connection setup
- Starting workers

All business logic is in resumeprocessing/ folder.
To add more queues, copy-paste the queue setup section.
"""

import asyncio
import logging
import os
from typing import Any

from bullmq import Worker
from dotenv import load_dotenv

from resumeprocessing.job_handler import process_resume_job
from resumeprocessing.jd_handler import process_jd_job
from resumeprocessing.score_handler import process_score_job

# ============================================
# CONFIGURATION
# ============================================

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - [%(name)s] %(message)s'
)
logger = logging.getLogger(__name__)

# ============================================
# REDIS CONNECTION
# ============================================

REDIS_HOST = os.getenv('REDIS_HOST', 'hrbot-redis')
REDIS_PORT = int(os.getenv('REDIS_PORT', '6379'))

REDIS_CONNECTION = {
    'host': REDIS_HOST,
    'port': REDIS_PORT,
}

QUEUE_NAMES = {
    'Resume_Processing': 'resume-processing',
    'JD_Processing': 'jd-processing',
    'Score_Processing': 'score-processing',
}

QUEUE_CONCURRENCY = {
    'Resume_Processing': int(os.getenv('RESUME_QUEUE_CONCURRENCY', '8')),
    'JD_Processing': int(os.getenv('JD_QUEUE_CONCURRENCY', '2')),
    'Score_Processing': int(os.getenv('SCORE_QUEUE_CONCURRENCY', '8')),
}


async def on_job_completed(job: Any, result: Any) -> None:
    """Called when a job completes successfully"""
    logger.info(f"✅ Job {job.id} completed")


async def on_job_failed(job: Any, error: Exception) -> None:
    """Called when a job fails (after all retries)"""
    logger.error(f"❌ Job {job.id} permanently failed: {str(error)}")




async def start_workers() -> None:
    """Start all configured BullMQ workers"""
    logger.info("="*60)
    logger.info("🚀 Starting BullMQ Workers")
    logger.info("="*60)
    logger.info(f"Redis: {REDIS_HOST}:{REDIS_PORT}")
    logger.info("="*60)
    
    workers = []

    queue_name = QUEUE_NAMES['Resume_Processing']
    concurrency = QUEUE_CONCURRENCY['Resume_Processing']
    
    logger.info(f"📋 Queue: {queue_name}")
    logger.info(f"   Concurrency: {concurrency}")
    
    resume_worker = Worker(
        queue_name,
        process_resume_job,
        {
            'connection': REDIS_CONNECTION,
            'concurrency': concurrency,
            'lockDuration': 300000,  # 5 minutes
        }
    )
    resume_worker.on('completed', on_job_completed)
    resume_worker.on('failed', on_job_failed)
    workers.append(resume_worker)
    logger.info(f"   ✅ Worker ready")

    # ── JD Processing Worker ──
    jd_queue_name = QUEUE_NAMES['JD_Processing']
    jd_concurrency = QUEUE_CONCURRENCY['JD_Processing']

    logger.info(f"📋 Queue: {jd_queue_name}")
    logger.info(f"   Concurrency: {jd_concurrency}")

    jd_worker = Worker(
        jd_queue_name,
        process_jd_job,
        {
            'connection': REDIS_CONNECTION,
            'concurrency': jd_concurrency,
            'lockDuration': 300000,  # 5 minutes
        }
    )
    jd_worker.on('completed', on_job_completed)
    jd_worker.on('failed', on_job_failed)
    workers.append(jd_worker)
    logger.info(f"   ✅ Worker ready")

    # ── Score Processing Worker ──
    score_queue_name = QUEUE_NAMES['Score_Processing']
    score_concurrency = QUEUE_CONCURRENCY['Score_Processing']

    logger.info(f"📋 Queue: {score_queue_name}")
    logger.info(f"   Concurrency: {score_concurrency}")

    score_worker = Worker(
        score_queue_name,
        process_score_job,
        {
            'connection': REDIS_CONNECTION,
            'concurrency': score_concurrency,
            'lockDuration': 600000,  # 10 minutes (scoring multiple resumes takes longer)
        }
    )
    score_worker.on('completed', on_job_completed)
    score_worker.on('failed', on_job_failed)
    workers.append(score_worker)
    logger.info(f"   ✅ Worker ready")


    logger.info("="*60)
    logger.info(f"✅ {len(workers)} worker(s) ready - waiting for jobs...")
    logger.info("Press Ctrl+C to stop")
    logger.info("="*60)
    
    try:
        if len(workers) == 1:
            try:
                await workers[0].run()
            except ValueError as e:
                if "empty" in str(e).lower():
                    logger.debug(f"BullMQ initialization quirk (safe to ignore): {e}")
                    await asyncio.Event().wait()
                else:
                    raise
        else:
            await asyncio.gather(*[worker.run() for worker in workers])
    except KeyboardInterrupt:
        logger.info("\n🛑 Shutdown signal received")
    except Exception as e:
        logger.error(f"⚠️  Worker error: {e}", exc_info=True)
    finally:
        logger.info("👋 Closing workers...")
        for worker in workers:
            try:
                await worker.close()
            except Exception as e:
                logger.debug(f"Worker close error: {e}")
        logger.info("✅ All workers closed cleanly")



def main() -> None:
    """Application entry point"""
    try:
        asyncio.run(start_workers())
    except Exception as e:
        logger.critical(f"❌ Worker crashed: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
