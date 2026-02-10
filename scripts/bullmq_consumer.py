#!/usr/bin/env python3
"""
BullMQ Consumer for Kreeda Hiring Bot

Proper BullMQ Python implementation with async/await and concurrency support.
Processes jobs from Redis BullMQ queues using the official bullmq Python library.
"""

import asyncio
import signal
import logging
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add script directories to path
base_path = Path(__file__).parent
sys.path.append(str(base_path / 'jd-processing'))
sys.path.append(str(base_path / 'resume-processing'))
sys.path.append(str(base_path / 'final-ranking'))

try:
    from bullmq import Worker, Queue
except ImportError:
    print("❌ BullMQ library not found. Install with: pip install bullmq")
    sys.exit(1)

from main_jd_processor import process_jd_complete
from main_resume_processor import process_resume_pipeline
from main_ranking_processor import process_final_ranking

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bullmq_consumer')

class KreedaJobProcessor:
    """Async job processor for Kreeda Hiring Bot using proper BullMQ"""
    
    def __init__(self):
        """Initialize Redis connection configuration"""
        redis_host = os.getenv('REDIS_HOST', 'localhost')
        redis_port = int(os.getenv('REDIS_PORT', 6379))
        redis_password = os.getenv('REDIS_PASSWORD', 'password123')
        
        self.redis_config = {
            "host": redis_host,
            "port": redis_port,
            "password": redis_password
        }
        
        self.workers = []
        self.shutdown_event = asyncio.Event()
        
        logger.info(f"✅ Initialized with Redis at {redis_host}:{redis_port}")
    
    async def process_jd_job(self, job, job_token):
        """Process JD processing job"""
        logger.info(f"🔍 Processing JD job {job.id}")
        
        job_data = job.data
        job_id = job_data.get('jobId')
        
        try:
            logger.info(f"📋 Job data: jobId={job_id}")
            logger.info(f"🚀 Calling process_jd_complete for job {job_id}")
            
            # Call with job object (ProgressTracker handles BullMQ updates)
            result = await process_jd_complete(job)
            
            logger.info(f"📊 Result from process_jd_complete: success={result.get('success')}, error={result.get('error')}")
            
            if result.get('success'):
                logger.info(f"✅ JD job {job.id} completed successfully")
                return result
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ JD processing returned failure: {error_msg}")
                raise Exception(f"JD processing failed: {error_msg}")
                
        except Exception as e:
            import traceback
            error_details = traceback.format_exc()
            logger.error(f"❌ JD job {job.id} failed with exception: {type(e).__name__}: {str(e)}")
            logger.error(f"📋 Full traceback:\n{error_details}")
            raise e
    
    async def process_resume_job(self, job, job_token):
        """Process resume processing job"""
        job_name = job.name
        logger.info(f"📄 Processing resume job {job.id} (name: {job_name})")
        
        job_data = job.data
        
        # Handle parent Flow job (process-resume-group)
        if job_name == 'process-resume-group':
            logger.info(f"👨‍👩‍👧‍👦 Parent Flow job detected - tracking {job_data.get('totalResumes', 0)} child jobs")
            total_resumes = job_data.get('totalResumes', 0)
            
            # Parent job just waits for children to complete
            return {
                'success': True,
                'message': f'Parent job tracking {total_resumes} resume processing jobs',
                'totalResumes': total_resumes
            }
        
        # Handle child job (process-resume) - actual processing
        resume_id = job_data.get('resumeId') or job_data.get('resume_id')
        job_id = job_data.get('jobId') or job.data.get('job_id')
        resume_index = job.data.get('resumeIndex', 0) or job.data.get('index', 0)
        total_resumes = job.data.get('totalResumes', 0) or job.data.get('total', 0)
        
        # Normalize job data for processor
        normalized_data = {
            'resume_id': resume_id,
            'job_id': job_id,
            'index': resume_index,
            'total': total_resumes
        }
        job.data = normalized_data
        
        resume_label = f"[{resume_index}/{total_resumes}]" if resume_index else ""
        logger.info(f"📄 {resume_label} Processing resume ID: {resume_id}, Job ID: {job_id}")
        
        try:
            logger.info(f"🚀 {resume_label} Calling process_resume_pipeline for resume {resume_id}")
            
            # Call with job object (ProgressTracker handles BullMQ updates)
            result = await process_resume_pipeline(job)
            
            logger.info(f"📊 Result: success={result.get('success')}, score={result.get('final_score')}")
            
            if result.get('success'):
                logger.info(f"✅ {resume_label} Resume job {job.id} completed with score {result.get('final_score')}")
                return result
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Resume processing failed: {error_msg}")
                raise Exception(f"Resume processing failed: {error_msg}")
                
        except Exception as e:
            import traceback
            logger.error(f"❌ Resume job {job.id} failed: {type(e).__name__}: {str(e)}")
            logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
            raise e
    
    async def process_ranking_job(self, job, job_token):
        """Process ranking job with new batch structure"""
        logger.info(f"🏆 Processing ranking job {job.id}")
        
        job_data = job.data
        job_id = job_data.get('jobId')
        
        try:
            logger.info(f"🚀 Starting ranking calculation for job {job_id}")
            
            # Extract job parameters for new batch structure
            score_result_ids = job_data.get('scoreResults', [])
            batch_index = job_data.get('batchIndex', 1)
            total_batches = job.data.get('totalBatches', 1)
            ranking_criteria = job.data.get('rankingCriteria', {})
            batch_identifier = job.data.get('resumeGroupId', job_id)  # Use jobId as batch identifier
            
            logger.info(f"📊 Batch {batch_index}/{total_batches}, {len(score_result_ids)} scores")
            
            # Run in thread pool to allow parallel processing
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(
                None,
                process_final_ranking,
                job_id,
                batch_identifier,
                score_result_ids,
                batch_index,
                total_batches,
                ranking_criteria
            )
            
            if result.get('success'):
                logger.info(f"✅ Ranking batch {batch_index}/{total_batches} completed successfully")
                return result
            else:
                error_msg = result.get('error', 'Unknown error')
                logger.error(f"❌ Ranking batch {batch_index}/{total_batches} failed: {error_msg}")
                raise Exception(f"Ranking processing failed: {error_msg}")
                
        except Exception as e:
            import traceback
            logger.error(f"❌ Ranking job {job.id} failed: {type(e).__name__}: {str(e)}")
            logger.error(f"📋 Traceback:\n{traceback.format_exc()}")
            raise e
    
    def setup_signal_handlers(self):
        """Setup graceful shutdown signal handlers"""
        def signal_handler(signum, frame):
            logger.info(f"📡 Received signal {signum}, initiating graceful shutdown...")
            self.shutdown_event.set()

        signal.signal(signal.SIGTERM, signal_handler)
        signal.signal(signal.SIGINT, signal_handler)
    
    async def start_workers(self):
        """Start all BullMQ workers with proper concurrency"""
        logger.info("🚀 Starting Kreeda BullMQ Workers")
        
        # JD Processing Worker (concurrency: 1)
        jd_worker = Worker(
            "jd-processing", 
            self.process_jd_job, 
            {
                "connection": self.redis_config,
                "concurrency": 1
            }
        )
        self.workers.append(jd_worker)
        logger.info("✅ Started JD Processing Worker (concurrency: 1)")
        
        # Resume Processing Worker (concurrency: 4 as requested)
        resume_worker = Worker(
            "resume-processing", 
            self.process_resume_job, 
            {
                "connection": self.redis_config,
                "concurrency": 16  # Set to 4 as requested
            }
        )
        self.workers.append(resume_worker)
        logger.info("✅ Started Resume Processing Worker (concurrency: 4)")
        
        # Ranking Worker (concurrency: 2)
        ranking_worker = Worker(
            "ranking", 
            self.process_ranking_job, 
            {
                "connection": self.redis_config,
                "concurrency": 2
            }
        )
        self.workers.append(ranking_worker)
        logger.info("✅ Started Ranking Worker (concurrency: 2)")
        
        logger.info(f"🎯 All {len(self.workers)} workers started successfully")
    
    async def shutdown_workers(self):
        """Gracefully shutdown all workers"""
        logger.info("🔄 Shutting down workers...")
        
        for i, worker in enumerate(self.workers):
            try:
                logger.info(f"Closing worker {i+1}/{len(self.workers)}...")
                await worker.close()
                logger.info(f"✅ Worker {i+1} closed successfully")
            except Exception as e:
                logger.error(f"❌ Error closing worker {i+1}: {e}")
        
        logger.info("✅ All workers shut down successfully")
    
    async def log_queue_counts(self):
        """Log the number of jobs in each queue at startup"""
        try:
            from bullmq import Queue
        except ImportError:
            logger.error("❌ BullMQ library not found. Install with: pip install bullmq")
            return
        
        queue_names = ["jd-processing", "resume-processing", "ranking"]
        for name in queue_names:
            try:
                q = Queue(name, {"connection": self.redis_config})
                # Use getJobCounts() instead of count()
                counts = await q.getJobCounts()
                total = sum(counts.values()) if counts else 0
                logger.info(f"📦 Queue '{name}' has  {total} jobs (waiting: {counts.get('waiting', 0)}, active: {counts.get('active', 0)})")
            except Exception as e:
                logger.warning(f"⚠️ Could not get count for queue '{name}': {e}")

    async def run(self):
        """Main run method with proper lifecycle management"""
        try:
            # Setup signal handlers
            self.setup_signal_handlers()

            # Log job counts in each queue at startup
            await self.log_queue_counts()

            # Start all workers
            await self.start_workers()

            logger.info("🎯 Kreeda Job Processor is running. Press Ctrl+C to stop.")

            # Wait for shutdown signal
            await self.shutdown_event.wait()

        except Exception as e:
            logger.error(f"❌ Fatal error in processor: {e}")
            raise
        finally:
            # Clean shutdown
            await self.shutdown_workers()

async def main():
    """Main entry point"""
    processor = KreedaJobProcessor()
    try:
        await processor.run()
    except KeyboardInterrupt:
        logger.info("👋 Received keyboard interrupt")
    except Exception as e:
        logger.error(f"❌ Application error: {e}")
        sys.exit(1)
    
    logger.info("👋 Kreeda Job Processor shut down successfully")

if __name__ == "__main__":
    # Run the async main function
    asyncio.run(main())