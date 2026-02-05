import { Router, Request, Response } from 'express';
import { Job, Resume, ScoreResult } from '../models';

const router = Router();

// ==================== JD UPDATE APIS ====================

// PUT /api/updates/jd/:jobId/analysis - Update JD analysis (called by workers)
router.put('/jd/:jobId/analysis', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;
    const { jd_analysis } = req.body;

    if (!jd_analysis) {
      res.status(400).json({
        success: false,
        error: 'jd_analysis is required'
      });
      return;
    }

    const job = await Job.findByIdAndUpdate(
      jobId,
      { jd_analysis },
      { new: true, runValidators: true }
    );

    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    res.json({
      success: true,
      data: job
    });
  } catch (error) {
    console.error('Error updating JD analysis:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update JD analysis'
    });
  }
});

// PUT /api/updates/jd/:jobId/compliance - Update compliance structure (called by workers)
router.put('/jd/:jobId/compliance', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;
    const { filter_requirements } = req.body;

    if (!filter_requirements) {
      res.status(400).json({
        success: false,
        error: 'filter_requirements is required'
      });
      return;
    }

    const job = await Job.findByIdAndUpdate(
      jobId,
      { filter_requirements },
      { new: true, runValidators: true }
    );

    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    res.json({
      success: true,
      data: job
    });
  } catch (error) {
    console.error('Error updating compliance:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update compliance'
    });
  }
});

// PUT /api/updates/jd/:jobId/meta - Update meta information (called by workers)
router.put('/jd/:jobId/meta', async (req: Request, res: Response): Promise<void> => {
  try {
    const { jobId } = req.params;
    const updateFields: any = {};

    // Allow updating specific fields
    if (req.body.meta) updateFields.meta = req.body.meta;
    if (req.body.jd_text) updateFields.jd_text = req.body.jd_text;
    if (req.body.status) updateFields.status = req.body.status;

    const job = await Job.findByIdAndUpdate(
      jobId,
      updateFields,
      { new: true, runValidators: true }
    );

    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    res.json({
      success: true,
      data: job
    });
  } catch (error) {
    console.error('Error updating job meta:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update job meta'
    });
  }
});

// ==================== RESUME UPDATE APIS ====================

// GET /api/updates/resume/:resumeId - Get resume details (for workers)
router.get('/resume/:resumeId', async (req: Request, res: Response): Promise<void> => {
  try {
    const resume = await Resume.findById(req.params.resumeId);
    if (!resume) {
      res.status(404).json({
        success: false,
        error: 'Resume not found'
      });
      return;
    }

    res.json({
      success: true,
      data: resume
    });
  } catch (error) {
    console.error('Error fetching resume:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch resume'
    });
  }
});

// PUT /api/updates/resume/:resumeId - Update resume details (called by workers)
router.put('/resume/:resumeId', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resumeId } = req.params;
    const updateFields: any = {};

    // Allow updating specific fields
    if (req.body.raw_text) updateFields.raw_text = req.body.raw_text;
    if (req.body.parsed_content) updateFields.parsed_content = req.body.parsed_content;
    if (req.body.resume_embedding) updateFields.resume_embedding = req.body.resume_embedding;
    if (req.body.extraction_status) updateFields.extraction_status = req.body.extraction_status;
    if (req.body.parsing_status) updateFields.parsing_status = req.body.parsing_status;
    if (req.body.embedding_status) updateFields.embedding_status = req.body.embedding_status;
    if (req.body.candidate_name) updateFields.candidate_name = req.body.candidate_name;

    const resume = await Resume.findByIdAndUpdate(
      resumeId,
      updateFields,
      { new: true, runValidators: true }
    );

    if (!resume) {
      res.status(404).json({
        success: false,
        error: 'Resume not found'
      });
      return;
    }

    res.json({
      success: true,
      data: resume
    });
  } catch (error) {
    console.error('Error updating resume:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update resume'
    });
  }
});

// ==================== SCORE UPDATE APIS ====================

// POST /api/updates/score - Create or update score result (called by workers)
router.post('/score', async (req: Request, res: Response): Promise<void> => {
  try {
    const {
      job_id,
      resume_id,
      keyword_score,
      semantic_score,
      project_score,
      final_score,
      recalculated_llm_score,
      hard_requirements_met,
      score_breakdown,
      rank,
      adjusted_score
    } = req.body;

    if (!job_id || !resume_id) {
      res.status(400).json({
        success: false,
        error: 'job_id and resume_id are required'
      });
      return;
    }

    // Check if score already exists
    let scoreResult = await ScoreResult.findOne({ job_id, resume_id });

    if (scoreResult) {
      // Update existing score
      if (keyword_score !== undefined) scoreResult.keyword_score = keyword_score;
      if (semantic_score !== undefined) scoreResult.semantic_score = semantic_score;
      if (project_score !== undefined) scoreResult.project_score = project_score;
      if (final_score !== undefined) scoreResult.final_score = final_score;
      if (recalculated_llm_score !== undefined) scoreResult.recalculated_llm_score = recalculated_llm_score;
      if (hard_requirements_met !== undefined) scoreResult.hard_requirements_met = hard_requirements_met;
      if (score_breakdown) scoreResult.score_breakdown = score_breakdown;
      if (rank !== undefined) scoreResult.rank = rank;
      if (adjusted_score !== undefined) scoreResult.adjusted_score = adjusted_score;
      
      await scoreResult.save();
    } else {
      // Create new score
      scoreResult = new ScoreResult({
        job_id,
        resume_id,
        keyword_score: keyword_score ?? 0,
        semantic_score: semantic_score ?? 0,
        project_score: project_score ?? 0,
        final_score: final_score ?? 0,
        recalculated_llm_score: recalculated_llm_score ?? 0,
        hard_requirements_met: hard_requirements_met ?? true,
        score_breakdown: score_breakdown ?? {},
        rank: rank,
        adjusted_score: adjusted_score
      });
      
      await scoreResult.save();
    }

    res.json({
      success: true,
      data: scoreResult
    });
  } catch (error) {
    console.error('Error creating/updating score:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create/update score'
    });
  }
});

// GET /api/updates/scores/:jobId - Get all scores for a job (for workers)
router.get('/scores/:jobId', async (req: Request, res: Response): Promise<void> => {
  try {
    const scores = await ScoreResult.find({ job_id: req.params.jobId })
      .populate('resume_id');

    res.json({
      success: true,
      data: scores,
      count: scores.length
    });
  } catch (error) {
    console.error('Error fetching scores:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch scores'
    });
  }
});

export default router;
