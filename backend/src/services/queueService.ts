import { Request, Response } from 'express';
import { queues, QUEUE_NAMES, flowProducer } from '../config/queue';
import { 
  JDProcessingJobData, 
  ResumeProcessingJobData,
  ResumeGroupFlowJobData,
  RankingJobData,
  RankingFlowJobData
} from '../types/jobs';

export class QueueService {
  
  // Add JD Processing Job
  static async addJDProcessingJob(jobData: JDProcessingJobData) {
    try {
      const job = await queues.jdProcessing.add('process-jd', jobData);
      return { success: true, jobId: job.id, message: 'JD processing job queued' };
    } catch (error) {
      console.error('Error adding JD processing job:', error);
      return { success: false, error: 'Failed to queue JD processing job' };
    }
  }

  // Add Resume Processing Job
  static async addResumeProcessingJob(jobData: ResumeProcessingJobData) {
    try {
      const job = await queues.resumeProcessing.add('process-resume', jobData);
      return { success: true, jobId: job.id, message: 'Resume processing job queued' };
    } catch (error) {
      console.error('Error adding resume processing job:', error);
      return { success: false, error: 'Failed to queue resume processing job' };
    }
  }

  // Add Resume Group Flow (Parent-Child) for parallel processing
  static async addResumeGroupFlow(
    parentData: ResumeGroupFlowJobData,
    resumes: ResumeProcessingJobData[]
  ) {
    try {
      const totalResumes = resumes.length;
      console.log(`🔄 Creating resume group flow for ${totalResumes} resumes`);
      
      // Create parent job with children - add counter to each resume
      const flow = await flowProducer.add({
        name: 'process-resume-group',
        queueName: QUEUE_NAMES.RESUME_PROCESSING,
        data: parentData,
        opts: {
          // Parent job options
          removeOnComplete: 1000,
          removeOnFail: 1000,  // Keep last 100 failed jobs
          ignoreDependencyOnFailure: true,  // Allow parent to run even if some children fail
        },
        children: resumes.map((resumeData, index) => ({
          name: 'process-resume',
          queueName: QUEUE_NAMES.RESUME_PROCESSING,
          data: {
            ...resumeData,
            resumeIndex: index + 1,  // 1-based index
            totalResumes: totalResumes  // Total count
          },
          opts: {
            attempts: 3,  // Retry up to 3 times
            backoff: {
              type: 'exponential',
              delay: 5000, // Wait 5s, then 10s, etc.
            },
            removeOnComplete: 100,
            removeOnFail: 100,  // Keep last 100 failed jobs
          },
        })),
      });

      console.log(`✅ Resume group flow created with parent job: ${flow.job.id}`);
      return { 
        success: true, 
        parentJobId: flow.job.id,
        childrenCount: resumes.length,
        message: `Resume group flow created with ${resumes.length} child jobs` 
      };
    } catch (error) {
      console.error('❌ Error creating resume group flow:', error);
      return { success: false, error: 'Failed to create resume group flow' };
    }
  }

  // Add Ranking Flow (Parent-Child) for batch processing
  static async addRankingFlow(
    parentData: RankingFlowJobData,
    rankingBatches: RankingJobData[]
  ) {
    try {
      const totalBatches = rankingBatches.length;
      console.log(`🔄 Creating ranking flow for ${totalBatches} batches (30 scores each)`);
      
      // Create parent job with children - add batch info to each batch
      const flow = await flowProducer.add({
        name: 'process-ranking-batches',
        queueName: QUEUE_NAMES.RANKING,
        data: parentData,
        opts: {
          // Parent job options
          removeOnComplete: 1000,
          removeOnFail: 1000,  // Keep last 100 failed jobs
          ignoreDependencyOnFailure: true,  // Allow parent to run even if some batches fail
        },
        children: rankingBatches.map((batchData, index) => ({
          name: 'calculate-ranking',
          queueName: QUEUE_NAMES.RANKING,
          data: {
            ...batchData,
            batchIndex: index + 1,  // 1-based index
            totalBatches: totalBatches  // Total count
          },
          opts: {
            attempts: 3,  // Retry up to 3 times
            backoff: {
              type: 'exponential',
              delay: 5000, // Wait 5s, then 10s, etc.
            },
            removeOnComplete: 100,
            removeOnFail: 100,  // Keep last 100 failed jobs
          },
        })),
      });

      console.log(`✅ Ranking flow created with parent job: ${flow.job.id}`);
      return { 
        success: true, 
        parentJobId: flow.job.id,
        childrenCount: rankingBatches.length,
        message: `Ranking flow created with ${rankingBatches.length} batch jobs` 
      };
    } catch (error) {
      console.error('❌ Error creating ranking flow:', error);
      return { success: false, error: 'Failed to create ranking flow' };
    }
  }

  // Add single Ranking Job (for individual batches)
  static async addRankingJob(jobData: RankingJobData) {
    try {
      const job = await queues.ranking.add('calculate-ranking', jobData);
      return { success: true, jobId: job.id, message: 'Ranking job queued' };
    } catch (error) {
      console.error('Error adding ranking job:', error);
      return { success: false, error: 'Failed to queue ranking job' };
    }
  }

  // Get JD Processing Job by ID
  static async getJDProcessingJob(jobId: string) {
    try {
      const job = await queues.jdProcessing.getJob(jobId);
      return job;
    } catch (error) {
      console.error('Error getting JD processing job:', error);
      return null;
    }
  }

  // Get Resume Flow Progress - using queue counts instead of individual job fetching
  static async getResumeFlowProgress(parentJobId: string, totalResumes: number) {
    try {
      const parentJob = await queues.resumeProcessing.getJob(parentJobId);
      
      if (!parentJob) {
        return { 
          success: false, 
          error: 'Parent job not found' 
        };
      }

      // Get queue counts efficiently
      const counts = await queues.resumeProcessing.getJobCounts('waiting', 'active', 'delayed', 'failed');
      
      // Calculate completed: total - (waiting + active + delayed + failed)
      // Note: We use the stored total instead of counting completed jobs
      const waiting = counts.waiting || 0;
      const active = counts.active || 0;
      const delayed = counts.delayed || 0;
      const failed = counts.failed || 0;
      const completed = Math.max(0, totalResumes - waiting - active - delayed - failed);

      console.log(`📊 Resume Queue Stats: Total=${totalResumes}, Waiting=${waiting}, Active=${active}, Delayed=${delayed}, Failed=${failed}, Completed=${completed}`);

      const parentState = await parentJob.getState();

      return {
        success: true,
        stats: {
          total: totalResumes,
          completed,
          failed,
          active,
          waiting,
          delayed,
          state: parentState,
          parentState: parentState,
          parentProgress: parentJob.progress
        }
      };
    } catch (error) {
      console.error('Error getting resume flow progress:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Failed to get flow progress' 
      };
    }
  }

  // Get Ranking Flow Progress - using queue counts instead of individual job fetching
  static async getRankingFlowProgress(parentJobId: string, totalBatches: number) {
    try {
      const parentJob = await queues.ranking.getJob(parentJobId);
      
      if (!parentJob) {
        return { 
          success: false, 
          error: 'Parent job not found' 
        };
      }

      // Get queue counts efficiently
      const counts = await queues.ranking.getJobCounts('waiting', 'active', 'delayed', 'failed');
      
      // Calculate completed: total - (waiting + active + delayed + failed)
      const waiting = counts.waiting || 0;
      const active = counts.active || 0;
      const delayed = counts.delayed || 0;
      const failed = counts.failed || 0;
      const completed = Math.max(0, totalBatches - waiting - active - delayed - failed);

      console.log(`📊 Ranking Queue Stats: Total=${totalBatches}, Waiting=${waiting}, Active=${active}, Delayed=${delayed}, Failed=${failed}, Completed=${completed}`);

      const parentState = await parentJob.getState();

      return {
        success: true,
        stats: {
          total: totalBatches,
          completed,
          failed,
          active,
          waiting,
          delayed,
          state: parentState,
          parentState: parentState,
          parentProgress: parentJob.progress
        }
      };
    } catch (error) {
      console.error('Error getting ranking flow progress:', error);
      return { 
        success: false, 
        error: error instanceof Error ? error.message : 'Failed to get ranking flow progress' 
      };
    }
  }
}