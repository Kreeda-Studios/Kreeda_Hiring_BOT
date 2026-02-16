import { Router, Request, Response } from 'express';
import { Job, Resume } from '../models';
import { QueueService } from '../services/queueService';
import { isOperationAllowed, getNextStatus } from '../utils/jobStatus';

const router = Router();

// POST /jd/:jobId - Process JD and trigger JD queue
router.post('/jd/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;

    const job = await Job.findById(jobId);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Check if job is already locked
    if (job.locked) {
      res.status(400).json({
        success: false,
        error: 'Job is locked. Cannot process again. JD text, file, and compliance cannot be modified.'
      });
      return;
    }

    // Check if JD processing is allowed based on status level
    const operationCheck = isOperationAllowed(job.status, 'JD_PROCESSING');
    if (!operationCheck.allowed) {
      res.status(400).json({
        success: false,
        error: operationCheck.reason
      });
      return;
    }
    
    // Check if either JD text or JD PDF filename is present
    if (!job.jd_pdf_filename && !job.jd_text) {
      res.status(400).json({
        success: false,
        error: 'No JD data found to process. Upload JD PDF or enter JD text first.'
      });
      return;
    }

    // Lock the job and update status before processing
    job.locked = true;
    job.status = getNextStatus(job.status, 'JD_PROCESSING_START');
    await job.save();

    // Only pass jobId to the queue
    const jobData = {
      jobId
    };

    const queueResult = await QueueService.addJDProcessingJob(jobData);

    if (!queueResult.success) {
      // Unlock and reset status if queue failed
      job.locked = false;
      job.status = 'draft';
      job.status = 'jd_processing_failed';
      await job.save();
      
      res.status(500).json({
        success: false,
        error: queueResult.error || 'Failed to queue JD processing'
      });
      return;
    }

    // Save the JD processing job ID
    if (!job.bullmq_jobs) job.bullmq_jobs = {};
    job.bullmq_jobs.jd_processing_job_id = queueResult.jobId;
    await job.save();

    res.json({
      success: true,
      data: {
        job_id: jobId,
        jd_job_id: queueResult.jobId,
        status: job.status,
        locked: job.locked,
        jd_processing_status: job.status,
        jd_processing_progress: 0
      },
      message: 'JD processing queued successfully. Job is now locked - JD file, text, and compliance cannot be changed.'
    });
  } catch (error) {
    console.error('Error processing JD:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to process JD'
    });
  }
});

// POST /resumes/:jobId - Batch process all resumes from all linked groups using Flow
router.post('/resumes/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;

    const job = await Job.findById(jobId);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Check if resume processing is allowed based on status level
    const operationCheck = isOperationAllowed(job.status, 'RESUME_PROCESSING');
    if (!operationCheck.allowed) {
      res.status(400).json({
        success: false,
        error: operationCheck.reason
      });
      return;
    }

    // Check if job has resumes
    const resumes = await Resume.find({ job_id: jobId });

    if (resumes.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No resumes found for this job'
      });
      return;
    }

    // Update job resume processing status
    job.status = 'resume_processing_started';
    await job.save();

    // Prepare resume job data
    const resumeJobsData = resumes.map(resume => {
      // Compute file path from job_id and filename (relative to uploads/)
      const filePath = `uploads/${jobId}/resumes/${resume.filename}`;
      return {
        resumeId: resume._id.toString(),
        jobId: jobId,
        resumeGroupId: jobId, // Use jobId as group identifier for compatibility
        fileName: resume.filename || '',
        filePath: filePath
      };
    });

    // Update job status to resume processing started
    job.status = getNextStatus(job.status, 'RESUME_PROCESSING_START');
    await job.save();

    // Update all resumes to processing status
    await Resume.updateMany(
      { job_id: jobId },
      { 
        overall_processing_status: 'processing',
        processing_progress: 0
      }
    );

    // Always use Flow for parallel processing
    const flowResult = await QueueService.addResumeGroupFlow(
      {
        jobId: jobId,
        resumeGroupId: jobId, // Use jobId instead of groupId
        totalResumes: resumes.length
      },
      resumeJobsData
    );

    if (!flowResult.success) {
      // Reset status on failure
      job.status = 'resume_processing_failed';
      await job.save();
      
      await Resume.updateMany(
        { job_id: jobId },
        { 
          overall_processing_status: 'failed',
          processing_error: flowResult.error || 'Failed to create resume processing flow'
        }
      );
      
      res.status(500).json({
        success: false,
        error: flowResult.error || 'Failed to create resume processing flow'
      });
      return;
    }

    // Save the parent job ID and total count
    if (!job.bullmq_jobs) job.bullmq_jobs = {};
    job.bullmq_jobs.resume_processing_parent_job_id = flowResult.parentJobId;
    
    if (!job.processing_totals) job.processing_totals = {};
    job.processing_totals.total_resumes = resumes.length;
    
    await job.save();

    res.json({
      success: true,
      data: {
        job_id: jobId,
        parent_job_id: flowResult.parentJobId,
        total_resumes: resumes.length,
        children_count: flowResult.childrenCount,
        resume_processing_status: job.status,
        resume_processing_progress: 0
      },
      message: `${resumes.length} resumes queued for parallel processing via Flow`
    });
  } catch (error) {
    console.error('Error processing resumes:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to process resumes'
    });
  }
});

// POST /ranking/:jobId - Process ranking for completed resumes with hard requirements met
router.post('/ranking/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;

    // Validate job exists
    const job = await Job.findById(jobId);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Get all completed resumes with hard requirements met
    const resumes = await Resume.find({
      job_id: jobId,
      status: 'completed',
      hard_requirements_met: true
    }).select('_id scores');

    if (resumes.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No completed resumes with hard requirements met found for this job'
      });
      return;
    }

    // Calculate min/max scores for keyword and semantic
    let minKeywordScore = Infinity;
    let maxKeywordScore = -Infinity;
    let minSemanticScore = Infinity;
    let maxSemanticScore = -Infinity;

    resumes.forEach(resume => {
      if (resume.scores?.keyword_score !== undefined && resume.scores.keyword_score !== null) {
        minKeywordScore = Math.min(minKeywordScore, resume.scores.keyword_score);
        maxKeywordScore = Math.max(maxKeywordScore, resume.scores.keyword_score);
      }
      if (resume.scores?.semantic_score !== undefined && resume.scores.semantic_score !== null) {
        minSemanticScore = Math.min(minSemanticScore, resume.scores.semantic_score);
        maxSemanticScore = Math.max(maxSemanticScore, resume.scores.semantic_score);
      }
    });

    // Handle case where no scores were found
    if (!isFinite(minKeywordScore)) {
      minKeywordScore = 0;
      maxKeywordScore = 0;
    }
    if (!isFinite(minSemanticScore)) {
      minSemanticScore = 0;
      maxSemanticScore = 0;
    }

    // Batch resume IDs into groups of 30
    const BATCH_SIZE = 30;
    const resumeIds = resumes.map(r => r._id.toString());
    const batches: string[][] = [];
    
    for (let i = 0; i < resumeIds.length; i += BATCH_SIZE) {
      batches.push(resumeIds.slice(i, i + BATCH_SIZE));
    }

    // Prepare ranking job data for each batch
    const rankingBatches = batches.map(batch => ({
      jobId: jobId,
      resumeIds: batch,
      minKeywordScore,
      maxKeywordScore,
      minSemanticScore,
      maxSemanticScore
    }));

    // Update job status to ranking started
    job.status = getNextStatus(job.status, 'RANKING_START');
    await job.save();

    // Create ranking flow with batches
    const flowResult = await QueueService.addRankingFlow(
      {
        jobId: jobId,
        totalScores: resumeIds.length,
        totalBatches: batches.length
      },
      rankingBatches as any // Type assertion since we're passing custom fields
    );

    if (!flowResult.success) {
      // Reset status on failure
      job.status = 'ranking_failed';
      await job.save();
      
      res.status(500).json({
        success: false,
        error: flowResult.error || 'Failed to create ranking flow'
      });
      return;
    }

    // Save the ranking parent job ID and total batch count
    if (!job.bullmq_jobs) job.bullmq_jobs = {};
    job.bullmq_jobs.ranking_parent_job_id = flowResult.parentJobId;
    
    if (!job.processing_totals) job.processing_totals = {};
    job.processing_totals.total_ranking_batches = batches.length;
    
    await job.save();

    res.json({
      success: true,
      data: {
        job_id: jobId,
        parent_job_id: flowResult.parentJobId,
        total_resumes: resumeIds.length,
        total_batches: batches.length,
        batch_size: BATCH_SIZE,
        score_ranges: {
          keyword: {
            min: minKeywordScore,
            max: maxKeywordScore
          },
          semantic: {
            min: minSemanticScore,
            max: maxSemanticScore
          }
        },
        ranking_status: job.status
      },
      message: `${resumeIds.length} resumes queued for ranking in ${batches.length} batches`
    });
  } catch (error) {
    console.error('Error processing ranking:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to process ranking'
    });
  }
});

export default router;