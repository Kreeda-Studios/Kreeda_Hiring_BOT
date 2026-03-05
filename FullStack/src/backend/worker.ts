/**
 * BullMQ Worker for Resume Processing
 * This worker can be run separately to process resume jobs from the queue
 */

import { Worker, Job } from 'bullmq';
import { redis } from './config/redis';
import { connectToDatabase } from './config/database';
import { ResumeService } from './services/resume.service';

const QUEUE_NAME = 'resume-processing';

interface ResumeJobData {
  resumeId: string;
  fileName: string;
  s3Bucket: string;
  s3Key: string;
  originalFileName: string;
}

async function processResumeJob(job: Job<ResumeJobData>) {
  console.log(`🔄 Processing job ${job.id}:`, job.data);

  const { resumeId, fileName, s3Key } = job.data;

  try {
    // Update status to processing
    await ResumeService.updateResumeStatus(resumeId, 'processing');

    // TODO: Add actual resume processing logic here
    // - Download file from MinIO
    // - Extract text from PDF/DOCX
    // - Parse and analyze resume
    // - Extract candidate information, skills, experience
    // - Calculate matching scores
    // - Store results back to database

    // Simulate processing time
    await new Promise(resolve => setTimeout(resolve, 2000));

    // Update status to completed
    await ResumeService.updateResumeStatus(resumeId, 'completed');

    console.log(`✅ Job ${job.id} completed successfully`);
    return { success: true, resumeId };

  } catch (error) {
    console.error(`❌ Job ${job.id} failed:`, error);
    
    // Update status to failed
    await ResumeService.updateResumeStatus(
      resumeId, 
      'failed', 
      error instanceof Error ? error.message : 'Unknown error'
    );

    throw error; // Re-throw to let BullMQ handle retries
  }
}

async function startWorker() {
  console.log('🚀 Starting BullMQ Worker...');
  console.log(`📡 Connected to Redis`);
  console.log(`📋 Queue: ${QUEUE_NAME}`);

  // Ensure database connection
  await connectToDatabase();

  const worker = new Worker<ResumeJobData>(
    QUEUE_NAME,
    processResumeJob,
    {
      connection: redis,
      concurrency: 1, // Process one job at a time
      limiter: {
        max: 10, // Max 10 jobs
        duration: 1000, // per second
      },
    }
  );

  worker.on('completed', (job) => {
    console.log(`✅ Job ${job.id} completed`);
  });

  worker.on('failed', (job, err) => {
    console.error(`❌ Job ${job?.id} failed:`, err.message);
  });

  worker.on('error', (err) => {
    console.error('❌ Worker error:', err);
  });

  console.log('✅ Worker started successfully');
  console.log('⏳ Waiting for jobs...');

  // Graceful shutdown
  process.on('SIGTERM', async () => {
    console.log('🛑 Received SIGTERM, shutting down gracefully...');
    await worker.close();
    process.exit(0);
  });

  process.on('SIGINT', async () => {
    console.log('🛑 Received SIGINT, shutting down gracefully...');
    await worker.close();
    process.exit(0);
  });
}

// Start worker if this file is run directly
if (require.main === module) {
  startWorker().catch((error) => {
    console.error('❌ Failed to start worker:', error);
    process.exit(1);
  });
}

export { startWorker };
