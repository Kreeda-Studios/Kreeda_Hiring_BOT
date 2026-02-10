/**
 * Worker Update APIs
 * 
 * GET  /api/updates/job/:jobId            - Get job data for processing
 * GET  /api/updates/resume/:resumeId      - Get resume data for processing
 * POST /api/updates/jd/parsed             - Save JD analysis data from AI parser
 * POST /api/updates/jd/embeddings         - Save JD embeddings from embedding service
 * POST /api/updates/jd/compliance         - Save JD compliance filter requirements
 * POST /api/updates/jd/status             - Update JD processing status (success/failed)
 * POST /api/updates/resume/parsed         - Save resume parsed content from AI parser
 * POST /api/updates/resume/embeddings     - Save resume embeddings from embedding service
 * POST /api/updates/resume/scores         - Save resume scores (keyword, semantic, project, composite)
 * POST /api/updates/resume/status         - Update resume processing status (success/failed)
 */

import { Router, Request, Response } from 'express';
import { Job, Resume } from '../models';

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

    const resume = await Resume.findByIdAndUpdate(
      resume_id,
      { 
        scores: {
          ...scores,
          scoring_status: 'success',
          scored_at: new Date()
        }
      },
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
    const { job_id, status } = req.body;

    if (!job_id || !status) {
      res.status(400).json({ success: false, error: 'job_id and status are required' });
      return;
    }

    const job = await Job.findByIdAndUpdate(
      job_id,
      { processing_status: status },
      { new: true }
    );

    if (!job) {
      res.status(404).json({ success: false, error: 'Job not found' });
      return;
    }

    res.json({ success: true, data: { job_id, status } });
  } catch (error) {
    console.error('Error updating JD status:', error);
    res.status(500).json({ success: false, error: 'Failed to update JD status' });
  }
});

router.post('/resume/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resume_id, status } = req.body;

    if (!resume_id || !status) {
      res.status(400).json({ success: false, error: 'resume_id and status are required' });
      return;
    }

    const resume = await Resume.findByIdAndUpdate(
      resume_id,
      { processing_status: status },
      { new: true }
    );

    if (!resume) {
      res.status(404).json({ success: false, error: 'Resume not found' });
      return;
    }

    res.json({ success: true, data: { resume_id, status } });
  } catch (error) {
    console.error('Error updating resume status:', error);
    res.status(500).json({ success: false, error: 'Failed to update resume status' });
  }
});

export default router;
