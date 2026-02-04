import { Queue, QueueOptions, QueueEvents, FlowProducer } from 'bullmq';
import IORedis from 'ioredis';
import { sseService } from '../services/sseService';

// Redis connection configuration
const redisConfig = {
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD || 'password123',
  maxRetriesPerRequest: null,
  retryDelayOnFailover: 100,
};

// Create Redis connection
export const redisConnection = new IORedis(redisConfig);

// Queue configuration
const queueOptions: QueueOptions = {
  connection: redisConnection,
  defaultJobOptions: {
    removeOnComplete: 100, // Keep last 100 completed jobs
    removeOnFail: 50,      // Keep last 50 failed jobs
    attempts: 3,
    backoff: {
      type: 'exponential',
      delay: 2000,
    },
  },
};

// Job Queue Types - Only 3 queues as per requirements
export const QUEUE_NAMES = {
  JD_PROCESSING: 'jd-processing',
  RESUME_PROCESSING: 'resume-processing', // Includes scoring
  RANKING: 'ranking',
} as const;

// Queue options with concurrency settings
const resumeQueueOptions: QueueOptions = {
  ...queueOptions,
  defaultJobOptions: {
    ...queueOptions.defaultJobOptions,
    // Set concurrency to 4 for resume processing
  },
};

// Create queues
export const jdProcessingQueue = new Queue(QUEUE_NAMES.JD_PROCESSING, queueOptions);
export const resumeProcessingQueue = new Queue(QUEUE_NAMES.RESUME_PROCESSING, resumeQueueOptions);
export const rankingQueue = new Queue(QUEUE_NAMES.RANKING, queueOptions);

// Create FlowProducer for parent-child job hierarchies
export const flowProducer = new FlowProducer({ connection: redisConnection });

// Export all queues
export const queues = {
  jdProcessing: jdProcessingQueue,
  resumeProcessing: resumeProcessingQueue,
  ranking: rankingQueue,
};

// Create QueueEvents to listen to job events across network
const jdQueueEvents = new QueueEvents(QUEUE_NAMES.JD_PROCESSING, { connection: redisConnection });
const resumeQueueEvents = new QueueEvents(QUEUE_NAMES.RESUME_PROCESSING, { connection: redisConnection });
const rankingQueueEvents = new QueueEvents(QUEUE_NAMES.RANKING, { connection: redisConnection });

// Setup progress listeners for SSE using QueueEvents
jdQueueEvents.on('progress', ({ jobId, data }: any) => {
  console.log(`📊 JD Job ${jobId} progress:`, data);
  if (data && typeof data === 'object' && data.stage) {
    // Extract the actual job ID from the job data
    // We need to get the job to extract jobId from data
    jdProcessingQueue.getJob(jobId).then(job => {
      if (job && job.data.jobId) {
        const actualJobId = job.data.jobId;
        console.log(`📤 Sending SSE progress for job ${actualJobId}:`, data);
        sseService.sendProgress(actualJobId, data);
      }
    }).catch(err => {
      console.error(`❌ Failed to get job ${jobId}:`, err);
    });
  }
});

jdQueueEvents.on('completed', ({ jobId }: any) => {
  console.log(`✅ JD Job ${jobId} completed`);
  jdProcessingQueue.getJob(jobId).then(job => {
    if (job && job.data.jobId) {
      const actualJobId = job.data.jobId;
      console.log(`📤 Sending SSE completion for job ${actualJobId}`);
      sseService.sendComplete(actualJobId, true);
    }
  }).catch(err => {
    console.error(`❌ Failed to get completed job ${jobId}:`, err);
  });
});

jdQueueEvents.on('failed', ({ jobId, failedReason }: any) => {
  console.log(`❌ JD Job ${jobId} failed:`, failedReason);
  jdProcessingQueue.getJob(jobId).then(job => {
    if (job && job.data.jobId) {
      const actualJobId = job.data.jobId;
      console.log(`📤 Sending SSE failure for job ${actualJobId}`);
      sseService.sendComplete(actualJobId, false, failedReason);
    }
  }).catch(err => {
    console.error(`❌ Failed to get failed job ${jobId}:`, err);
  });
});

// Resume processing progress
resumeQueueEvents.on('progress', ({ jobId, data }: any) => {
  console.log(`📊 Resume Job ${jobId} progress:`, data);
  if (data && typeof data === 'object' && data.stage) {
    resumeProcessingQueue.getJob(jobId).then(job => {
      if (job && job.data.jobId) {
        const actualJobId = job.data.jobId;
        sseService.sendProgress(actualJobId, data);
      }
    }).catch(err => console.error(`❌ Failed to get resume job:`, err));
  }
});

// Ranking progress
rankingQueueEvents.on('progress', ({ jobId, data }: any) => {
  console.log(`📊 Ranking Job ${jobId} progress:`, data);
  if (data && typeof data === 'object' && data.stage) {
    rankingQueue.getJob(jobId).then(job => {
      if (job && job.data.jobId) {
        const actualJobId = job.data.jobId;
        sseService.sendProgress(actualJobId, data);
      }
    }).catch(err => console.error(`❌ Failed to get ranking job:`, err));
  }
});

// Flow parent job completion tracking
resumeQueueEvents.on('completed', async ({ jobId }: any) => {
  try {
    const job = await resumeProcessingQueue.getJob(jobId);
    if (!job) return;
    
    // Check if this is a parent Flow job
    if (job.name === 'process-resume-group') {
      const parentJobId = jobId;
      const totalResumes = job.data.totalResumes || 0;
      
      // Get children status
      const children = await job.getChildrenValues();
      const childrenKeys = children ? Object.keys(children) : [];
      const completedCount = childrenKeys.length;
      
      console.log(`✅ Flow parent ${parentJobId} completed: ${completedCount}/${totalResumes} children`);
      
      // Send SSE update for Flow completion
      sseService.sendProgress(parentJobId, {
        stage: 'flow-complete',
        percent: 100,
        message: `All ${totalResumes} resumes processed`,
        timestamp: new Date().toISOString()
      });
      
      sseService.sendComplete(parentJobId, true);
    }
  } catch (err) {
    console.error(`❌ Failed to process Flow completion:`, err);
  }
});

// Flow child job progress tracking
resumeQueueEvents.on('completed', async ({ jobId }: any) => {
  try {
    const childJob = await resumeProcessingQueue.getJob(jobId);
    if (!childJob) return;
    
    // Check if this is a child job with a parent
    const parent = await childJob.parent;
    if (parent && parent.id) {
      const parentJob = await resumeProcessingQueue.getJob(parent.id);
      if (parentJob && parentJob.name === 'process-resume-group') {
        // Get updated children status
        const children = await parentJob.getChildrenValues();
        const childrenArray = children ? Object.keys(children) : [];
        const totalResumes = parentJob.data.totalResumes || childrenArray.length;
        
        // Count completed children
        let completedCount = 0;
        let failedCount = 0;
        
        for (const childId of childrenArray) {
          const child = await resumeProcessingQueue.getJob(childId);
          if (child) {
            const state = await child.getState();
            if (state === 'completed') completedCount++;
            if (state === 'failed') failedCount++;
          }
        }
        
        const overallProgress = Math.round(((completedCount + failedCount) / totalResumes) * 100);
        
        console.log(`📊 Flow ${parent.id} progress: ${completedCount}/${totalResumes} completed`);
        
        // Send SSE update for Flow progress
        sseService.sendProgress(parent.id, {
          stage: 'flow-progress',
          percent: overallProgress,
          message: `Processed ${completedCount}/${totalResumes} resumes (${failedCount} failed)`,
          timestamp: new Date().toISOString()
        });
      }
    }
  } catch (err) {
    console.error(`❌ Failed to track child completion:`, err);
  }
});

// Queue health check
export const checkQueueHealth = async (): Promise<boolean> => {
  try {
    await redisConnection.ping();
    return true;
  } catch (error) {
    console.error('Redis connection failed:', error);
    return false;
  }
};