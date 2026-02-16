import { Router, Request, Response } from 'express';
import Resume from '../models/Resume';

const router = Router();

// GET /api/scores/resumes/:jobId - Get resumes with scores for a specific job
router.get('/resumes/:jobId', async (req: Request, res: Response) => {
  try {
    const { jobId } = req.params;
    
    // Find all resumes with scores for this job
    const resumes = await Resume.find({
      job_id: jobId,
      scores: { $exists: true, $ne: null }
    })
      .select('filename parsed_content scores hard_requirements_met createdAt updatedAt')
      .sort({ 'scores.composite_score': -1 });
    
    // Transform to match frontend expectation
    const scoresData = resumes.map((resume, index) => ({
      _id: resume._id,
      job_id: jobId,
      resume_id: {
        _id: resume._id,
        filename: resume.filename,
        candidate_name: (resume.parsed_content as any)?.name || resume.filename
      },
      project_score: resume.scores?.project_score || 0,
      keyword_score: resume.scores?.keyword_score || 0,
      semantic_score: resume.scores?.semantic_score || 0,
      final_score: resume.scores?.composite_score || 0,
      recalculated_llm_score: resume.scores?.composite_score || 0,
      hard_requirements_met: resume.hard_requirements_met || false,
      rank: index + 1,
      adjusted_score: resume.scores?.composite_score || 0,
      score_breakdown: {},
      createdAt: resume.createdAt,
      updatedAt: resume.updatedAt
    }));
    
    res.json({
      success: true,
      data: scoresData,
      count: scoresData.length
    });
  } catch (error) {
    console.error('Error fetching resume scores:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch resume scores'
    });
  }
});

export default router;