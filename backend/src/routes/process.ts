import { Router, Request, Response } from 'express';
import { Job, Resume, ResumeGroup } from '../models';
import { QueueService } from '../services/queueService';

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
    
    // Check if either JD text or JD PDF filename is present
    if (!job.jd_pdf_filename && !job.jd_text) {
      res.status(400).json({
        success: false,
        error: 'No JD data found to process. Upload JD PDF or enter JD text first.'
      });
      return;
    }

    // Lock the job before processing
    job.locked = true;
    job.status = 'active';
    await job.save();

    // Only pass jobId to the queue
    const jobData = {
      jobId
    };

    const queueResult = await QueueService.addJDProcessingJob(jobData);

    if (!queueResult.success) {
      // Unlock if queue failed
      job.locked = false;
      job.status = 'draft';
      await job.save();
      
      res.status(500).json({
        success: false,
        error: queueResult.error || 'Failed to queue JD processing'
      });
      return;
    }

    // // Save the JD processing job ID in the jobs object
    // if (!job.jobs) job.jobs = {};
    // job.jobs.jd = queueResult.jobId;
    // await job.save();

    res.json({
      success: true,
      data: {
        job_id: jobId,
        jd_job_id: queueResult.jobId,
        status: job.status,
        locked: job.locked
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

    const job = await Job.findById(jobId).populate('resume_groups');
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Check if job has resume groups
    if (!job.resume_groups || job.resume_groups.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No resume groups linked to this job'
      });
      return;
    }

    // Fetch all resumes from all linked groups
    const groupIds = job.resume_groups.map((g: any) => g._id);
    const resumes = await Resume.find({ group_id: { $in: groupIds } });

    if (resumes.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No resumes found in linked groups'
      });
      return;
    }

    // Prepare resume job data
    const resumeJobsData = resumes.map(resume => {
      const groupId = resume.group_id?.toString() || '';
      // Compute file path from group_id and filename (relative to uploads/)
      const filePath = groupId ? `uploads/${groupId}/resumes/${resume.filename}` : '';
      return {
        resumeId: resume._id.toString(),
        jobId: jobId,
        resumeGroupId: groupId,
        fileName: resume.filename || '',
        filePath: filePath
      };
    });

    // Always use Flow for parallel processing
    const flowResult = await QueueService.addResumeGroupFlow(
      {
        jobId: jobId,
        resumeGroupId: groupIds[0]?.toString() || 'multiple-groups',
        totalResumes: resumes.length
      },
      resumeJobsData
    );

    if (!flowResult.success) {
      res.status(500).json({
        success: false,
        error: flowResult.error || 'Failed to create resume processing flow'
      });
      return;
    }

    res.json({
      success: true,
      data: {
        job_id: jobId,
        parent_job_id: flowResult.parentJobId,
        total_resumes: resumes.length,
        children_count: flowResult.childrenCount
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

// POST /ranking/:jobId - Process ranking with batching (30 scores per batch)
router.post('/ranking/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;

    const job = await Job.findById(jobId).populate('resume_groups');
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Check if job has resume groups
    if (!job.resume_groups || job.resume_groups.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No resume groups linked to this job'
      });
      return;
    }

    // Get all scores for this job (we need the actual scores, not just resumes)
    const { ScoreResult } = await import('../models');
    const allScores = await ScoreResult.find({ job_id: jobId }).populate('resume_id', 'candidate_name group_id filename');

    if (allScores.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No scores found for this job. Please run resume processing first.'
      });
      return;
    }

    console.log(`📊 Found ${allScores.length} scores for job ${jobId}`);

    // Batch scores into groups of 30
    const BATCH_SIZE = 30;
    const batches: any[][] = [];
    
    for (let i = 0; i < allScores.length; i += BATCH_SIZE) {
      const batch = allScores.slice(i, i + BATCH_SIZE);
      batches.push(batch);
    }

    console.log(`📦 Created ${batches.length} batches of scores (${BATCH_SIZE} scores per batch)`);

    // Create ranking job data for each batch
    const rankingBatches = batches.map((batch, index) => ({
      jobId,
      resumeGroupId: 'all-groups', // Processing all groups together
      scoreResults: batch.map(score => score._id.toString()),
      // Add ranking criteria that can be used for LLM re-ranking
      rankingCriteria: {
        enable_llm_rerank: false, // Set to true when we want LLM re-ranking
        filter_requirements: {
          structured: {}  // This would come from job requirements in future
        },
        specified_fields: [] // Fields specified by HR for compliance
      }
    }));

    // Create parent flow job data
    const parentData = {
      jobId,
      totalScores: allScores.length,
      totalBatches: batches.length
    };

    // Create ranking flow
    const flowResult = await QueueService.addRankingFlow(parentData, rankingBatches);

    if (!flowResult.success) {
      res.status(500).json({
        success: false,
        error: flowResult.error || 'Failed to create ranking flow'
      });
      return;
    }

    res.json({
      success: true,
      data: {
        job_id: jobId,
        parent_job_id: flowResult.parentJobId,
        total_scores: allScores.length,
        batch_count: batches.length,
        batch_size: BATCH_SIZE
      },
      message: `${allScores.length} scores queued for ranking in ${batches.length} batches via Flow`
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