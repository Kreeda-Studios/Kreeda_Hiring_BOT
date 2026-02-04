import { Router, Request, Response } from 'express';
import { queues } from '../config/queue';
import { Resume, ScoreResult } from '../models';

const router = Router();

// Get processing status for a job
router.get('/job/:jobId/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;

    // Get all jobs related to this jobId across all queues
    const [jdJobs, resumeJobs, rankingJobs] = await Promise.all([
      queues.jdProcessing.getJobs(['active', 'waiting', 'delayed', 'completed', 'failed']),
      queues.resumeProcessing.getJobs(['active', 'waiting', 'delayed', 'completed', 'failed']),
      queues.ranking.getJobs(['active', 'waiting', 'delayed', 'completed', 'failed'])
    ]);

    // Filter jobs by jobId
    const relevantJdJobs = jdJobs.filter((job: any) => job.data.jobId === jobId);
    const relevantResumeJobs = resumeJobs.filter((job: any) => job.data.jobId === jobId);
    const relevantRankingJobs = rankingJobs.filter((job: any) => job.data.jobId === jobId);

    // Get progress for active jobs
    const jdProgress = await Promise.all(
      relevantJdJobs
        .filter((job: any) => job.progress !== undefined)
        .map(async (job: any) => ({
          queueJobId: job.id,
          type: 'jd-processing',
          state: await job.getState(),
          progress: job.progress,
          data: job.data
        }))
    );

    const resumeProgress = await Promise.all(
      relevantResumeJobs
        .filter((job: any) => job.progress !== undefined)
        .map(async (job: any) => ({
          queueJobId: job.id,
          resumeId: job.data.resumeId,
          type: 'resume-processing',
          state: await job.getState(),
          progress: job.progress,
          data: job.data
        }))
    );

    const rankingProgress = await Promise.all(
      relevantRankingJobs
        .filter((job: any) => job.progress !== undefined)
        .map(async (job: any) => ({
          queueJobId: job.id,
          type: 'ranking',
          state: await job.getState(),
          progress: job.progress,
          data: job.data
        }))
    );

    // Count statuses
    const counts = {
      jd: {
        total: relevantJdJobs.length,
        active: relevantJdJobs.filter((job: any) => job.isActive()).length,
        completed: relevantJdJobs.filter((job: any) => job.isCompleted()).length,
        failed: relevantJdJobs.filter((job: any) => job.isFailed()).length
      },
      resumes: {
        total: relevantResumeJobs.length,
        active: relevantResumeJobs.filter((job: any) => job.isActive()).length,
        waiting: relevantResumeJobs.filter((job: any) => job.isWaiting()).length,
        completed: relevantResumeJobs.filter((job: any) => job.isCompleted()).length,
        failed: relevantResumeJobs.filter((job: any) => job.isFailed()).length
      },
      ranking: {
        total: relevantRankingJobs.length,
        active: relevantRankingJobs.filter((job: any) => job.isActive()).length,
        completed: relevantRankingJobs.filter((job: any) => job.isCompleted()).length,
        failed: relevantRankingJobs.filter((job: any) => job.isFailed()).length
      }
    };

    res.json({
      success: true,
      data: {
        jobId,
        counts,
        activeProgress: {
          jd: jdProgress,
          resumes: resumeProgress,
          ranking: rankingProgress
        }
      }
    });
  } catch (error) {
    console.error('Error fetching processing status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch processing status'
    });
  }
});

// Get processing status for a specific resume (includes score status)
router.get('/resume/:resumeId/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resumeId } = req.params;

    // Get resume from database
    const resume = await Resume.findById(resumeId);
    
    if (!resume) {
      res.status(404).json({
        success: false,
        error: 'Resume not found'
      });
      return;
    }

    // Check if scores exist
    const scoreResult = await ScoreResult.findOne({ resume_id: resumeId });
    const hasScore = !!scoreResult;

    // Get BullMQ job status
    const resumeJobs = await queues.resumeProcessing.getJobs([
      'active',
      'waiting',
      'delayed',
      'completed',
      'failed'
    ]);

    const relevantJobs = resumeJobs.filter((job: any) => job.data.resumeId === resumeId);

    const progress = await Promise.all(
      relevantJobs.map(async (job: any) => ({
        queueJobId: job.id,
        state: await job.getState(),
        progress: job.progress,
        finishedOn: job.finishedOn,
        failedReason: job.failedReason,
        data: job.data
      }))
    );

    // Determine overall processing status
    let overallStatus = 'pending';
    if (hasScore) {
      overallStatus = 'completed';
    } else if (resume.extraction_status === 'failed' || resume.parsing_status === 'failed' || resume.embedding_status === 'failed') {
      overallStatus = 'failed';
    } else if (resume.embedding_status === 'success' && !hasScore) {
      overallStatus = 'scoring';
    } else if (resume.parsing_status === 'success') {
      overallStatus = 'embedding';
    } else if (resume.extraction_status === 'success') {
      overallStatus = 'parsing';
    } else if (resume.extraction_status === 'pending') {
      overallStatus = 'extracting';
    }

    res.json({
      success: true,
      data: {
        resumeId,
        filename: resume.filename,
        overallStatus,
        hasScore,
        processingStages: {
          extraction: resume.extraction_status,
          parsing: resume.parsing_status,
          embedding: resume.embedding_status,
          scoring: hasScore ? 'success' : 'pending'
        },
        score: scoreResult ? {
          final_score: scoreResult.final_score,
          keyword_score: scoreResult.keyword_score,
          semantic_score: scoreResult.semantic_score,
          project_score: scoreResult.project_score,
          hard_requirements_met: scoreResult.hard_requirements_met
        } : null,
        jobs: progress
      }
    });
  } catch (error) {
    console.error('Error fetching resume status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch resume status'
    });
  }
});

// Get overall queue statistics
router.get('/stats', async (req: Request, res: Response): Promise<void> => {
  try {
    const [jdCounts, resumeCounts, rankingCounts] = await Promise.all([
      queues.jdProcessing.getJobCounts(),
      queues.resumeProcessing.getJobCounts(),
      queues.ranking.getJobCounts()
    ]);

    res.json({
      success: true,
      data: {
        jdProcessing: jdCounts,
        resumeProcessing: resumeCounts,
        ranking: rankingCounts
      }
    });
  } catch (error) {
    console.error('Error fetching queue stats:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch queue statistics'
    });
  }
});

// Get Flow job status (parent and children)
router.get('/flow/:parentJobId/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const { parentJobId } = req.params;

    // Get parent job
    const parentJob = await queues.resumeProcessing.getJob(parentJobId);
    
    if (!parentJob) {
      res.status(404).json({
        success: false,
        error: 'Flow job not found'
      });
      return;
    }

    // Get parent job details
    const parentState = await parentJob.getState();
    const parentData = parentJob.data;

    // Get children jobs
    const children = await parentJob.getChildrenValues();
    const childrenDetails = [];
    
    if (children) {
      for (const [childJobId, childJobData] of Object.entries(children)) {
        const childJob = await queues.resumeProcessing.getJob(childJobId);
        if (childJob) {
          const resumeId = childJob.data.resumeId;
          
          // Check if resume has score
          const scoreResult = await ScoreResult.findOne({ resume_id: resumeId });
          
          childrenDetails.push({
            jobId: childJobId,
            resumeId,
            resumeIndex: childJob.data.resumeIndex,
            totalResumes: childJob.data.totalResumes,
            fileName: childJob.data.fileName,
            state: await childJob.getState(),
            progress: childJob.progress || 0,
            finishedOn: childJob.finishedOn,
            failedReason: childJob.failedReason,
            hasScore: !!scoreResult,
            score: scoreResult ? {
              final_score: scoreResult.final_score,
              keyword_score: scoreResult.keyword_score,
              semantic_score: scoreResult.semantic_score,
              project_score: scoreResult.project_score
            } : null
          });
        }
      }
    }

    // Calculate overall progress
    const completedChildren = childrenDetails.filter(c => c.state === 'completed').length;
    const failedChildren = childrenDetails.filter(c => c.state === 'failed').length;
    const activeChildren = childrenDetails.filter(c => c.state === 'active').length;
    const waitingChildren = childrenDetails.filter(c => c.state === 'waiting').length;
    const scoredChildren = childrenDetails.filter(c => c.hasScore).length;
    const totalChildren = childrenDetails.length;

    const overallProgress = totalChildren > 0 
      ? Math.round(((completedChildren + failedChildren) / totalChildren) * 100)
      : 0;
    
    const scoringProgress = totalChildren > 0 
      ? Math.round((scoredChildren / totalChildren) * 100)
      : 0;

    res.json({
      success: true,
      data: {
        parentJobId,
        parentState,
        totalResumes: parentData.totalResumes || totalChildren,
        overallProgress,
        scoringProgress,
        children: {
          total: totalChildren,
          completed: completedChildren,
          failed: failedChildren,
          active: activeChildren,
          waiting: waitingChildren,
          scored: scoredChildren
        },
        childrenDetails
      }
    });
  } catch (error) {
    console.error('Error fetching flow status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch flow status'
    });
  }
});

// SSE endpoint for real-time Flow progress updates
router.get('/flow/:parentJobId/sse', async (req: Request, res: Response): Promise<void> => {
  const { parentJobId } = req.params;
  
  // Set SSE headers
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no');
  
  // Send initial connection message
  res.write(`data: ${JSON.stringify({ type: 'connected', parentJobId })}\n\n`);
  
  const sendUpdate = async () => {
    try {
      const parentJob = await queues.resumeProcessing.getJob(parentJobId);
      
      if (!parentJob) {
        res.write(`data: ${JSON.stringify({ type: 'error', message: 'Job not found' })}\n\n`);
        return false;
      }
      
      const parentState = await parentJob.getState();
      const children = await parentJob.getChildrenValues();
      const childrenDetails = [];
      
      if (children) {
        for (const [childJobId, childJobData] of Object.entries(children)) {
          const childJob = await queues.resumeProcessing.getJob(childJobId);
          if (childJob) {
            const state = await childJob.getState();
            const resumeId = childJob.data.resumeId;
            
            // Check if resume has score
            const scoreResult = await ScoreResult.findOne({ resume_id: resumeId });
            
            childrenDetails.push({
              jobId: childJobId,
              resumeId,
              resumeIndex: childJob.data.resumeIndex,
              totalResumes: childJob.data.totalResumes,
              fileName: childJob.data.fileName,
              state,
              progress: childJob.progress || 0,
              finishedOn: childJob.finishedOn,
              failedReason: childJob.failedReason,
              hasScore: !!scoreResult,
              score: scoreResult ? scoreResult.final_score : null
            });
          }
        }
      }
      
      const completedChildren = childrenDetails.filter(c => c.state === 'completed').length;
      const failedChildren = childrenDetails.filter(c => c.state === 'failed').length;
      const activeChildren = childrenDetails.filter(c => c.state === 'active').length;
      const scoredChildren = childrenDetails.filter(c => c.hasScore).length;
      const totalChildren = childrenDetails.length;
      const overallProgress = totalChildren > 0 
        ? Math.round(((completedChildren + failedChildren) / totalChildren) * 100)
        : 0;
      const scoringProgress = totalChildren > 0 
        ? Math.round((scoredChildren / totalChildren) * 100)
        : 0;
      
      const update = {
        type: 'progress',
        parentJobId,
        parentState,
        overallProgress,
        scoringProgress,
        completed: completedChildren,
        failed: failedChildren,
        active: activeChildren,
        scored: scoredChildren,
        total: totalChildren,
        children: childrenDetails
      };
      
      res.write(`data: ${JSON.stringify(update)}\n\n`);
      
      // Stop if job is done
      if (parentState === 'completed' || parentState === 'failed') {
        res.write(`data: ${JSON.stringify({ type: 'complete', state: parentState })}\n\n`);
        return false;
      }
      
      return true;
    } catch (error) {
      console.error('SSE error:', error);
      res.write(`data: ${JSON.stringify({ type: 'error', message: 'Internal error' })}\n\n`);
      return false;
    }
  };
  
  // Send updates every 1 second
  const intervalId = setInterval(async () => {
    const shouldContinue = await sendUpdate();
    if (!shouldContinue) {
      clearInterval(intervalId);
      res.end();
    }
  }, 1000);
  
  // Clean up on client disconnect
  req.on('close', () => {
    clearInterval(intervalId);
    res.end();
  });
});

export default router;