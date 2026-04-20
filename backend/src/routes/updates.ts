/**
 * Worker Update APIs
 * 
 * GET  /api/updates/job/:jobId            - Get job data for processing
 * GET  /api/updates/resume/:resumeId      - Get resume data for processing
 * POST /api/updates/jd/parsed             - Save JD analysis data from AI parser
 * POST /api/updates/jd/embeddings         - Save JD embeddings from embedding service
 * POST /api/updates/jd/compliance         - Save JD compliance filter requirements
 * POST /api/updates/jd/status             - Update JD processing status (success/failed) with job_id, success boolean
 * POST /api/updates/resume/parsed         - Save resume parsed content from AI parser
 * POST /api/updates/resume/embeddings     - Save resume embeddings from embedding service
 * POST /api/updates/resume/scores         - Save resume scores (keyword, semantic, project, composite)
 * POST /api/updates/resume/status         - Update resume processing status (success/failed) with job_id, success boolean
 * POST /api/updates/resume/status/single  - Update single resume processing status (completed/failed) with resume_id, success boolean
 */

import { Router, Request, Response } from 'express';
import { Job, Resume } from '../models';
import { getNextStatus } from '../utils/jobStatus';

const router = Router();

router.get('/job/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const job = await Job.findById(req.params.jobId);
    
    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    res.json({ success: true, data: job });
  } catch (error) {
    console.error('Error fetching job:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch job' });
  }
});

router.get('/resume/:resumeId', async (req: Request, res: Response): Promise<void> => {
  try {
    const resume = await Resume.findById(req.params.resumeId);
    
    if (!resume) {
      res.status(404).json({ success: false, error: 'Resume not found' });
      return;
    }

    res.json({ success: true, data: resume });
  } catch (error) {
    console.error('Error fetching resume:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch resume' });
  }
});

router.post('/jd/parsed', async (req: Request, res: Response): Promise<void> => {
  try {
    const { job_id, jd_analysis } = req.body;

    if (!job_id || !jd_analysis) {
      res.status(400).json({ success: false, error: 'job_id and jd_analysis are required' });
      return;
    }

    const job = await Job.findByIdAndUpdate(job_id, { jd_analysis }, { new: true });

    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    res.json({ success: true, data: { job_id, updated: true } });
  } catch (error) {
    console.error('Error updating JD parsed data:', error);
    res.status(500).json({ success: false, error: 'Failed to update JD parsed data' });
  }
});

router.post('/jd/embeddings', async (req: Request, res: Response): Promise<void> => {
  try {
    const { job_id, jd_embedding } = req.body;

    if (!job_id || !jd_embedding) {
      res.status(400).json({ success: false, error: 'job_id and jd_embedding are required' });
      return;
    }

    console.log(`Saving JD embeddings for job ${job_id}:`, {
      hasEmbedding: !!jd_embedding,
      embeddingKeys: jd_embedding ? Object.keys(jd_embedding) : []
    });

    const job = await Job.findByIdAndUpdate(job_id, { jd_embedding }, { new: true });

    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    console.log(`JD embeddings saved successfully for job ${job_id}`);
    res.json({ success: true, data: { job_id, updated: true } });
  } catch (error) {
    console.error('Error updating JD embeddings:', error);
    res.status(500).json({ success: false, error: 'Failed to update JD embeddings' });
  }
});

router.post('/jd/compliance', async (req: Request, res: Response): Promise<void> => {
  try {
    const { job_id, filter_requirements } = req.body;

    if (!job_id || !filter_requirements) {
      res.status(400).json({ success: false, error: 'job_id and filter_requirements are required' });
      return;
    }

    const job = await Job.findByIdAndUpdate(job_id, { filter_requirements }, { new: true });

    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    res.json({ success: true, data: { job_id, updated: true } });
  } catch (error) {
    console.error('Error updating JD compliance:', error);
    res.status(500).json({ success: false, error: 'Failed to update JD compliance' });
  }
});

router.post('/resume/parsed', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resume_id, parsed_content } = req.body;

    if (!resume_id || !parsed_content) {
      res.status(400).json({ success: false, error: 'resume_id and parsed_content are required' });
      return;
    }

    const resume = await Resume.findByIdAndUpdate(
      resume_id,
      { parsed_content, parsing_status: 'success' },
      { new: true }
    );

    if (!resume) {
      res.status(404).json({ success: false, error: 'Resume not found' });
      return;
    }

    res.json({ success: true, data: { resume_id, updated: true } });
  } catch (error) {
    console.error('Error updating resume parsed data:', error);
    res.status(500).json({ success: false, error: 'Failed to update resume parsed data' });
  }
});

router.post('/resume/embeddings', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resume_id, resume_embedding } = req.body;

    if (!resume_id || !resume_embedding) {
      res.status(400).json({ success: false, error: 'resume_id and resume_embedding are required' });
      return;
    }

    const resume = await Resume.findByIdAndUpdate(
      resume_id,
      { resume_embedding, embedding_status: 'success' },
      { new: true }
    );

    if (!resume) {
      res.status(404).json({ success: false, error: 'Resume not found' });
      return;
    }

    res.json({ success: true, data: { resume_id, updated: true } });
  } catch (error) {
    console.error('Error updating resume embeddings:', error);
    res.status(500).json({ success: false, error: 'Failed to update resume embeddings' });
  }
});

router.post('/resume/scores', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resume_id, scores } = req.body;

    if (!resume_id || !scores) {
      res.status(400).json({ success: false, error: 'resume_id and scores are required' });
      return;
    }

    // Extract hard_requirements_met from scores if present
    const hard_requirements_met = scores.hard_requirements?.meets_all_requirements;

    const updatePayload: Record<string, any> = { scores };
    
    if (hard_requirements_met !== undefined) {
      updatePayload.hard_requirements_met = hard_requirements_met;
    }

    const resume = await Resume.findByIdAndUpdate(
      resume_id,
      updatePayload,
      { new: true }
    );

    if (!resume) {
      res.status(404).json({ success: false, error: 'Resume not found' });
      return;
    }

    res.json({ success: true, data: { resume_id, updated: true } });
  } catch (error) {
    console.error('Error updating resume scores:', error);
    res.status(500).json({ success: false, error: 'Failed to update resume scores' });
  }
});

router.post('/jd/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const { job_id, success, error } = req.body;

    if (!job_id || success === undefined) {
      res.status(400).json({ success: false, error: 'job_id and success (boolean) are required' });
      return;
    }

    const job = await Job.findById(job_id);
    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    // Update job status based on success/failure
    if (success) {
      job.status = getNextStatus(job.status, 'JD_PROCESSING_COMPLETE');
    } else {
      job.status = getNextStatus(job.status, 'JD_PROCESSING_FAIL');
      job.locked = false; // Unlock job to allow retry on failure
    }

    await job.save();

    res.json({ 
      success: true, 
      data: { 
        job_id, 
        status: job.status,
        locked: job.locked,
        message: success ? 'JD processing completed successfully' : 'JD processing failed'
      } 
    });
  } catch (error) {
    console.error('Error updating JD status:', error);
    res.status(500).json({ success: false, error: 'Failed to update JD status' });
  }
});

router.post('/resume/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const { job_id, success, error } = req.body;

    if (!job_id || success === undefined) {
      res.status(400).json({ success: false, error: 'job_id and success (boolean) are required' });
      return;
    }

    const job = await Job.findById(job_id);
    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    // Update job status based on success/failure
    if (success) {
      job.status = getNextStatus(job.status, 'RESUME_PROCESSING_COMPLETE');
      
      // Update all resumes to completed status
      await Resume.updateMany(
        { job_id: job_id },
        { 
          status: 'completed',
          overall_processing_status: 'completed',
          processing_progress: 100
        }
      );
    } else {
      job.status = getNextStatus(job.status, 'RESUME_PROCESSING_FAIL');
      
      // Update resumes to failed status
      await Resume.updateMany(
        { job_id: job_id },
        { 
          status: 'failed',
          overall_processing_status: 'failed',
          processing_error: error || 'Resume processing failed'
        }
      );
    }

    await job.save();

    res.json({ 
      success: true, 
      data: { 
        job_id, 
        status: job.status,
        message: success ? 'Resume processing completed successfully' : 'Resume processing failed'
      } 
    });
  } catch (error) {
    console.error('Error updating resume status:', error);
    res.status(500).json({ success: false, error: 'Failed to update resume status' });
  }
});

router.post('/resume/status/single', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resume_id, success, error, processing_progress, hard_requirements_met } = req.body;

    if (!resume_id || success === undefined) {
      res.status(400).json({ success: false, error: 'resume_id and success (boolean) are required' });
      return;
    }

    const updatePayload: Record<string, any> = success
      ? {
          status: 'completed',
          processing_progress: processing_progress ?? 100,
          processing_error: undefined
        }
      : {
          status: 'failed',
          processing_error: error || 'Resume processing failed'
        };

    // Set hard_requirements_met if provided and set status to 'filtered' if hard requirements not met
    if (hard_requirements_met !== undefined) {
      updatePayload.hard_requirements_met = hard_requirements_met;
      if (!hard_requirements_met && success) {
        updatePayload.status = 'filtered';
      }
    }

    const resume = await Resume.findByIdAndUpdate(resume_id, updatePayload, { new: true });

    if (!resume) {
      res.status(404).json({ success: false, error: 'Resume not found' });
      return;
    }

    res.json({
      success: true,
      data: {
        resume_id,
        status: resume.status,
        message: success ? 'Resume status updated to completed' : 'Resume status updated to failed'
      }
    });
  } catch (error) {
    console.error('Error updating single resume status:', error);
    res.status(500).json({ success: false, error: 'Failed to update single resume status' });
  }
});

// POST /api/updates/resume/scores/batch - Update scores for multiple resumes
router.post('/resume/scores/batch', async (req: Request, res: Response): Promise<void> => {
  try {
    const { updates } = req.body;

    if (!updates || !Array.isArray(updates)) {
      res.status(400).json({ success: false, error: 'updates array is required' });
      return;
    }

    // Validate updates format
    for (const update of updates) {
      if (!update.resume_id || !update.scores) {
        res.status(400).json({ 
          success: false, 
          error: 'Each update must have resume_id and scores' 
        });
        return;
      }
    }

    // Bulk update all resumes
    const bulkOps = updates.map(update => ({
      updateOne: {
        filter: { _id: update.resume_id },
        update: { 
          $set: { 
            scores: update.scores 
          } 
        }
      }
    }));

    const result = await Resume.bulkWrite(bulkOps);

    res.json({ 
      success: true, 
      data: { 
        updated_count: result.modifiedCount,
        matched_count: result.matchedCount
      } 
    });
  } catch (error) {
    console.error('Error updating resume scores in batch:', error);
    res.status(500).json({ success: false, error: 'Failed to update resume scores in batch' });
  }
});

// POST /api/updates/resumes/batch - Get resume data for multiple resume IDs
router.post('/resumes/batch', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resume_ids } = req.body;

    if (!resume_ids || !Array.isArray(resume_ids)) {
      res.status(400).json({ success: false, error: 'resume_ids array is required' });
      return;
    }

    const resumes = await Resume.find({
      _id: { $in: resume_ids }
    }).select('_id job_id filename candidate_name scores hard_requirements_met parsed_content');

    res.json({ 
      success: true, 
      data: resumes,
      count: resumes.length 
    });
  } catch (error) {
    console.error('Error fetching resumes in batch:', error);
    res.status(500).json({ success: false, error: 'Failed to fetch resumes in batch' });
  }
});

router.post('/ranking/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const { job_id, success, error } = req.body;

    if (!job_id || success === undefined) {
      res.status(400).json({ success: false, error: 'job_id and success (boolean) are required' });
      return;
    }

    const job = await Job.findById(job_id);
    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    // Update job status based on success/failure
    if (success) {
      job.status = getNextStatus(job.status, 'RANKING_COMPLETE');
    } else {
      job.status = getNextStatus(job.status, 'RANKING_FAIL');
    }

    await job.save();

    res.json({ 
      success: true, 
      data: { 
        job_id, 
        status: job.status,
        message: success ? 'Ranking completed successfully' : 'Ranking failed'
      } 
    });
  } catch (error) {
    console.error('Error updating ranking status:', error);
    res.status(500).json({ success: false, error: 'Failed to update ranking status' });
  }
});

export default router;
