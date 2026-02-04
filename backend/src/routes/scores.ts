import { Router, Request, Response } from 'express';
import ScoreResult from '../models/ScoreResult';

const router = Router();

// GET /api/scores - Get all scores with optional filters
router.get('/', async (req: Request, res: Response) => {
  try {
    const { job_id, resume_id, limit = 10, page = 1 } = req.query;
    
    const filter: any = {};
    if (job_id) filter.job_id = job_id;
    if (resume_id) filter.resume_id = resume_id;
    
    const skip = (parseInt(page as string) - 1) * parseInt(limit as string);
    
    const scores = await ScoreResult.find(filter)
      .populate('job_id', 'title')
      .populate({
        path: 'resume_id',
        select: 'filename parsed_content',
        transform: (doc: any) => {
          if (!doc) return doc;
          return {
            ...doc.toObject(),
            candidate_name: doc.parsed_content?.name || null
          };
        }
      })
      .sort({ final_score: -1 })
      .skip(skip)
      .limit(parseInt(limit as string));
    
    const total = await ScoreResult.countDocuments(filter);
    
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
    
    const scores = await ScoreResult.find({ job_id: jobId })
      .populate({
        path: 'resume_id',
        select: 'filename candidate_name',
      })
      .sort({ final_score: -1 });
    
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
    const score = await ScoreResult.findById(req.params.id)
      .populate('job_id', 'title description')
      .populate('resume_id', 'filename candidate_name parsed_content');
    
    if (!score) {
      res.status(404).json({
        success: false,
        error: 'Score result not found'
      });
      return;
    }
    
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

export default router;