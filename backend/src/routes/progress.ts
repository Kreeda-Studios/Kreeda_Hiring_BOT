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

    // Fetch absolute ground-truth resume counts from MongoDB
    const failedResumes = await Resume.countDocuments({ job_id: jobId, status: 'failed' });
    const completedResumes = await Resume.countDocuments({ job_id: jobId, status: 'completed' });
    const totalProcessedResumes = failedResumes + completedResumes;

    // Base ground-truth stats for resumes
    resumeStats = {
      total: totalResumes,
      completed: completedResumes,
      failed: failedResumes,
      active: 0,
      waiting: 0
    };

    // Determine current phase based on job status
    if (job.status === 'draft' || job.status === 'jd_processing_started' || job.status === 'jd_processing_completed') {
      phase = 'not_started';
      overallProgress = 0;
    } else if (job.status === 'resume_processing_started') {
      phase = 'resume_processing';
      
      phaseProgress = totalResumes > 0 ? Math.round((totalProcessedResumes / totalResumes) * 100) : 0;
      overallProgress = Math.round((phaseProgress / 100) * 70); // Map to 0-70%
      
      // Enhance with BullMQ active/waiting counts
      const resumeParentJobId = job.bullmq_jobs?.resume_processing_parent_job_id;
      if (resumeParentJobId && totalResumes > 0) {
        const resumeFlow = await QueueService.getResumeFlowProgress(resumeParentJobId, totalResumes);
        if (resumeFlow.success && resumeFlow.stats) {
          resumeStats.active = resumeFlow.stats.active || 0;
          resumeStats.waiting = resumeFlow.stats.waiting || 0;
        }
      }
    } else if (job.status === 'resume_processing_completed') {
      phase = 'resume_processing_completed';
      overallProgress = 70;
      phaseProgress = 100;
    } else if (job.status === 'ranking_started') {
      phase = 'ranking';
      
      const rankingParentJobId = job.bullmq_jobs?.ranking_parent_job_id;
      if (rankingParentJobId && totalRankingBatches > 0) {
        const rankingFlow = await QueueService.getRankingFlowProgress(rankingParentJobId, totalRankingBatches);
        if (rankingFlow.success && rankingFlow.stats) {
          const completed = rankingFlow.stats.completed || 0;
          phaseProgress = Math.round((completed / totalRankingBatches) * 100);
          overallProgress = 70 + Math.round((phaseProgress / 100) * 25); // Map to 70-95%
          
          rankingStats = {
            total: totalRankingBatches,
            completed,
            failed: rankingFlow.stats.failed || 0,
            active: rankingFlow.stats.active || 0,
            waiting: rankingFlow.stats.waiting || 0
          };
        }
      } else {
        overallProgress = 70;
      }
    } else if (job.status === 'ranking_completed') {
      phase = 'completed';
      overallProgress = 100;
      phaseProgress = 100;
      
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
