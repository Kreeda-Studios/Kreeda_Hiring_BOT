import { Router, Request, Response } from 'express';
import { Resume } from '../models';

const router = Router();

// GET /api/resumes - Get all resumes for a job
router.get('/', async (req: Request, res: Response) => {
  try {
    const { job_id } = req.query;
    const filter: any = {};
    
    if (job_id) filter.job_id = job_id;

    const resumes = await Resume.find(filter)
      .select('filename original_name extraction_status parsing_status embedding_status processing_status createdAt')
      .sort({ createdAt: -1 });

    res.json({
      success: true,
      data: resumes,
      count: resumes.length
    });
  } catch (error) {
    console.error('Error fetching resumes:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch resumes'
    });
  }
});

// GET /api/resumes/:id - Get resume by ID
router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const resume = await Resume.findById(req.params.id);

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

// POST /api/resumes - Create new resume (title and description only)
router.post('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const { title, description } = req.body;

    if (!title) {
      res.status(400).json({
        success: false,
        error: 'title is required'
      });
      return;
    }

    const resume = new Resume({
      title,
      description: description || ''
    });

    await resume.save();

    res.status(201).json({
      success: true,
      data: resume,
      message: 'Resume created successfully'
    });
  } catch (error) {
    console.error('Error creating resume:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create resume'
    });
  }
});

// PUT /api/resumes/:id - Update resume (flexible - all fields optional)
// Can update: raw_text, jd_compliance_text, group_id, parsed_content, and status fields
router.put('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const allowedUpdates = [
      'title',
      'description',
      'raw_text',
      'jd_compliance_text',
      'group_id',
      'candidate_name',
      'extraction_status',
      'parsed_content',
      'parsing_status',
      'embedding',
      'embedding_status'
    ];

    // Filter only allowed fields from request body
    const updates: any = {};
    Object.keys(req.body).forEach(key => {
      if (allowedUpdates.includes(key)) {
        updates[key] = req.body[key];
      }
    });

    if (Object.keys(updates).length === 0) {
      res.status(400).json({
        success: false,
        error: 'No valid fields to update'
      });
      return;
    }

    const resume = await Resume.findByIdAndUpdate(
      req.params.id,
      { $set: updates },
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
      data: resume,
      message: 'Resume updated successfully'
    });
  } catch (error) {
    console.error('Error updating resume:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update resume'
    });
  }
});

// DELETE /api/resumes/:id - Delete resume
router.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const resume = await Resume.findByIdAndDelete(req.params.id);

    if (!resume) {
      res.status(404).json({
        success: false,
        error: 'Resume not found'
      });
      return;
    }

    res.json({
      success: true,
      message: 'Resume deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting resume:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to delete resume'
    });
  }
});

export default router;