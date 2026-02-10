import { Router, Request, Response } from 'express';
import ScoreResult from '../models/ScoreResult';
import Resume from '../models/Resume';

const router = Router();

// GET /api/scores - Get all scores with optional filters
router.get('/', async (req: Request, res: Response) => {
  try {
    const { job_id, resume_id, limit = 10, page = 1 } = req.query;
    
    const filter: any = {
      'scores.scoring_status': 'success'
    };
    
    if (job_id) {
      filter.job_id = job_id;
    }
    
    if (resume_id) {
      filter._id = resume_id;
    }
    
    const skip = (parseInt(page as string) - 1) * parseInt(limit as string);
    
    const resumes = await Resume.find(filter)
      .select('filename parsed_content scores group_id')
      .sort({ 'scores.composite_score': -1 })
      .skip(skip)
      .limit(parseInt(limit as string));
    
    // Transform to match expected format
    const scores = resumes.map(resume => ({
      _id: resume._id,
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
      hard_requirements_met: resume.scores?.hard_requirements?.meets_all_requirements || false,
      createdAt: resume.scores?.scored_at || resume.createdAt,
      updatedAt: resume.scores?.scored_at || resume.updatedAt
    }));
    
    const total = await Resume.countDocuments(filter);
    
    res.json({
      success: true,
      data: scores,
      count: total,
      page: parseInt(page as string),
      totalPages: Math.ceil(total / parseInt(limit as string))
    });
  } catch (error) {
    console.error('Error fetching scores:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch scores'
    });
  }
});

// GET /api/scores/job/:jobId - Get scores for a specific job
router.get('/job/:jobId', async (req: Request, res: Response) => {
  try {
    const { jobId } = req.params;
    
    // Find all resumes with scores for this job directly
    const resumes = await Resume.find({
      job_id: jobId,
      'scores.scoring_status': 'success'
    })
      .select('filename parsed_content scores')
      .sort({ 'scores.composite_score': -1 });
    
    // Transform to match expected format
    const scores = resumes.map(resume => ({
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
      hard_requirements_met: resume.scores?.hard_requirements?.meets_all_requirements || false,
      createdAt: resume.scores?.scored_at || resume.createdAt,
      updatedAt: resume.scores?.scored_at || resume.updatedAt
    }));
    
    res.json({
      success: true,
      data: scores,
      count: scores.length
    });
  } catch (error) {
    console.error('Error fetching job scores:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch job scores'
    });
  }
});

// GET /api/scores/:id - Get specific score result
router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const resume = await Resume.findById(req.params.id)
      .select('filename parsed_content scores job_id')
      .populate('job_id', 'title description');
    
    if (!resume || !resume.scores || resume.scores.scoring_status !== 'success') {
      res.status(404).json({
        success: false,
        error: 'Score result not found'
      });
      return;
    }
    
    const score = {
      _id: resume._id,
      job_id: resume.job_id,
      resume_id: {
        _id: resume._id,
        filename: resume.filename,
        candidate_name: (resume.parsed_content as any)?.name || resume.filename,
        parsed_content: resume.parsed_content
      },
      project_score: resume.scores.project_score || 0,
      keyword_score: resume.scores.keyword_score || 0,
      semantic_score: resume.scores.semantic_score || 0,
      final_score: resume.scores.composite_score || 0,
      recalculated_llm_score: resume.scores.composite_score || 0,
      hard_requirements_met: resume.scores.hard_requirements?.meets_all_requirements || false,
      hard_requirements: resume.scores.hard_requirements,
      createdAt: resume.scores.scored_at || resume.createdAt,
      updatedAt: resume.scores.scored_at || resume.updatedAt
    };
    
    res.json({
      success: true,
      data: score
    });
  } catch (error) {
    console.error('Error fetching score:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch score'
    });
  }
});

// GET /api/scores/resumes/:jobId - Get resumes with scores for a specific job
router.get('/resumes/:jobId', async (req: Request, res: Response) => {
  try {
    const { jobId } = req.params;
    
    // Find all resumes with scores for this job directly
    const resumes = await Resume.find({
      job_id: jobId,
      'scores.scoring_status': 'success'
    })
      .select('filename parsed_content scores')
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
      hard_requirements_met: resume.scores?.hard_requirements?.meets_all_requirements || false,
      rank: index + 1,
      adjusted_score: resume.scores?.composite_score || 0,
      score_breakdown: {},
      createdAt: resume.scores?.scored_at || resume.createdAt,
      updatedAt: resume.scores?.scored_at || resume.updatedAt
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