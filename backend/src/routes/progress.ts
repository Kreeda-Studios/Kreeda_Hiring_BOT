import { Router, Request, Response } from 'express';
import { Job } from '../models';
import { QueueService } from '../services/queueService';

const router = Router();

/**
 * GET /api/progress/jd/:jobId
 * Get JD processing progress from BullMQ job
 */
router.get('/jd/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;

    // Get job from database
    const job = await Job.findById(jobId);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Get BullMQ job ID
    const bullmqJobId = job.bullmq_jobs?.jd_processing_job_id;
    if (!bullmqJobId) {
      res.json({
        success: true,
        data: {
          job_id: jobId,
          status: job.status,
          progress: 0,
          state: 'not_started',
          message: 'JD processing not yet queued'
        }
      });
      return;
    }

    // Get progress from BullMQ
    const bullmqJob = await QueueService.getJDProcessingJob(bullmqJobId);
    
    if (!bullmqJob) {
      res.json({
        success: true,
        data: {
          job_id: jobId,
          bullmq_job_id: bullmqJobId,
          status: job.status,
          progress: 0,
          state: 'not_found',
          message: 'BullMQ job not found'
        }
      });
      return;
    }

    const state = await bullmqJob.getState();
    const progress = bullmqJob.progress || 0;
    const progressData = typeof progress === 'object' ? progress : { percent: progress };

    res.json({
      success: true,
      data: {
        job_id: jobId,
        bullmq_job_id: bullmqJobId,
        status: job.status,
        state: state,
        progress: typeof progress === 'number' ? progress : (progress as any).percent || 0,
        progress_details: progressData,
        finished_on: bullmqJob.finishedOn,
        processed_on: bullmqJob.processedOn,
        failed_reason: bullmqJob.failedReason,
        return_value: bullmqJob.returnvalue
      }
    });
  } catch (error) {
    console.error('Error fetching JD progress:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch JD processing progress'
    });
  }
});

/**
 * GET /api/progress/resumes/:jobId
 * Get combined resume processing and ranking progress
 * - 0-70%: Resume processing
 * - 70-95%: Ranking
 * - 95-100%: Final completion
 */
router.get('/resumes/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;

    // Get job from database
    const job = await Job.findById(jobId);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    const Resume = (await import('../models')).Resume;
    
    // Get stored totals
    const totalResumes = job.processing_totals?.total_resumes || 0;
    const totalRankingBatches = job.processing_totals?.total_ranking_batches || 0;
    
    let overallProgress = 0;
    let phase = 'not_started';
    let phaseProgress = 0;
    let resumeStats: any = null;
    let rankingStats: any = null;

    // Determine current phase based on job status
    if (job.status === 'draft' || job.status === 'jd_processing_started' || job.status === 'jd_processing_completed') {
      phase = 'not_started';
      overallProgress = 0;
    } else if (job.status === 'resume_processing_started') {
      phase = 'resume_processing';
      
      // Calculate resume processing progress using BullMQ queue counts
      const resumeParentJobId = job.bullmq_jobs?.resume_processing_parent_job_id;
      if (resumeParentJobId && totalResumes > 0) {
        const resumeFlow = await QueueService.getResumeFlowProgress(resumeParentJobId, totalResumes);
        if (resumeFlow.success && resumeFlow.stats) {
          const completed = resumeFlow.stats.completed || 0;
          phaseProgress = Math.round((completed / totalResumes) * 100);
          overallProgress = Math.round((phaseProgress / 100) * 70); // Map to 0-70%
          
          resumeStats = {
            total: totalResumes,
            completed,
            failed: resumeFlow.stats.failed || 0,
            active: resumeFlow.stats.active || 0,
            waiting: resumeFlow.stats.waiting || 0
          };
        }
      }
    } else if (job.status === 'resume_processing_completed') {
      // Resume processing complete, but ranking not started
      phase = 'resume_processing_completed';
      overallProgress = 70;
      phaseProgress = 100;
      
      resumeStats = {
        total: totalResumes,
        completed: totalResumes,
        failed: 0,
        active: 0,
        waiting: 0
      };
    } else if (job.status === 'ranking_started') {
      phase = 'ranking';
      
      // Resume processing is complete (70%)
      resumeStats = {
        total: totalResumes,
        completed: totalResumes,
        failed: 0,
        active: 0,
        waiting: 0
      };
      
      // Calculate ranking progress using BullMQ queue counts
      const rankingParentJobId = job.bullmq_jobs?.ranking_parent_job_id;
      if (rankingParentJobId && totalRankingBatches > 0) {
        const rankingFlow = await QueueService.getRankingFlowProgress(rankingParentJobId, totalRankingBatches);
        if (rankingFlow.success && rankingFlow.stats) {
          const completed = rankingFlow.stats.completed || 0;
          phaseProgress = Math.round((completed / totalRankingBatches) * 100);
          // Map ranking progress to 70-95% range
          overallProgress = 70 + Math.round((phaseProgress / 100) * 25);
          
          rankingStats = {
            total: totalRankingBatches,
            completed,
            failed: rankingFlow.stats.failed || 0,
            active: rankingFlow.stats.active || 0,
            waiting: rankingFlow.stats.waiting || 0
          };
        }
      } else {
        // Ranking started but no batches yet
        overallProgress = 70;
      }
    } else if (job.status === 'ranking_completed') {
      phase = 'completed';
      overallProgress = 100;
      phaseProgress = 100;
      
      resumeStats = {
        total: totalResumes,
        completed: totalResumes,
        failed: 0,
        active: 0,
        waiting: 0
      };
      
      rankingStats = {
        total: totalRankingBatches,
        completed: totalRankingBatches,
        failed: 0,
        active: 0,
        waiting: 0
      };
    } else if (job.status === 'resume_processing_failed' || job.status === 'ranking_failed') {
      phase = 'failed';
      overallProgress = 0;
    }

    res.json({
      success: true,
      data: {
        job_id: jobId,
        status: job.status,
        phase,
        overall_progress: overallProgress,
        phase_progress: phaseProgress,
        resume_stats: resumeStats,
        ranking_stats: rankingStats,
        processing_totals: {
          total_resumes: totalResumes,
          total_ranking_batches: totalRankingBatches
        }
      }
    });
  } catch (error) {
    console.error('Error fetching resume progress:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch resume processing progress'
    });
  }
});

export default router;
