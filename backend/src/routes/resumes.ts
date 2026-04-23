import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import archiver from 'archiver';
import { Resume, Job } from '../models';
import config from '../config';
import { isOperationAllowed } from '../utils/jobStatus';

const router = Router();

// Configure multer for resume uploads
const resumeStorage = multer.diskStorage({
  destination: (req, file, cb) => {
    const jobId = req.body.job_id; // Get job_id from request body
    const uploadDir = path.join('/app', config.uploadPath, jobId, 'resumes');
    if (!fs.existsSync(uploadDir)) {
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, 'resume-' + uniqueSuffix + path.extname(file.originalname));
  }
});

const resumeUpload = multer({
  storage: resumeStorage,
  limits: { fileSize: 50 * 1024 * 1024 }, // 50MB per file
  fileFilter: (req, file, cb) => {
    const allowedTypes = ['.pdf', '.doc', '.docx'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowedTypes.includes(ext)) {
      cb(null, true);
    } else {
      cb(new Error('Only PDF, DOC, and DOCX files are allowed'));
    }
  }
});

// GET /api/resumes - Get all resumes for a job
router.get('/', async (req: Request, res: Response) => {
  try {
    const { job_id } = req.query;
    const filter: any = {};

    if (job_id) filter.job_id = job_id;

    const resumes = await Resume.find(filter)
      .select('filename original_name candidate_name status scores parsed_content createdAt hard_requirements_met processing_error')
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

// GET /api/resumes/:id/download - Download resume file
router.get('/:id/download', async (req: Request, res: Response): Promise<void> => {
  try {
    const resume = await Resume.findById(req.params.id);

    if (!resume) {
      res.status(404).json({
        success: false,
        error: 'Resume not found'
      });
      return;
    }

    // Construct file path
    const filePath = path.join('/app', config.uploadPath, resume.job_id.toString(), 'resumes', resume.filename);

    // Check if file exists
    if (!fs.existsSync(filePath)) {
      res.status(404).json({
        success: false,
        error: 'Resume file not found on disk'
      });
      return;
    }

    // Set headers for download
    res.setHeader('Content-Type', 'application/pdf');
    res.setHeader('Content-Disposition', `inline; filename="${resume.original_name || resume.filename}"`);

    // Stream the file
    const fileStream = fs.createReadStream(filePath);
    fileStream.pipe(res);
  } catch (error) {
    console.error('Error downloading resume:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to download resume'
    });
  }
});

// POST /api/resumes/bulk-download - Download multiple resumes as ZIP
router.post('/bulk-download', async (req: Request, res: Response): Promise<void> => {
  try {
    const { resumeIds } = req.body;

    if (!resumeIds || !Array.isArray(resumeIds) || resumeIds.length === 0) {
      res.status(400).json({
        success: false,
        error: 'Resume IDs array is required'
      });
      return;
    }

    // Fetch all resumes
    const resumes = await Resume.find({ _id: { $in: resumeIds } });

    if (resumes.length === 0) {
      res.status(404).json({
        success: false,
        error: 'No resumes found'
      });
      return;
    }

    // Create ZIP archive
    const archive = archiver('zip', { zlib: { level: 9 } });

    // Set response headers
    const timestamp = new Date().toISOString().split('T')[0];
    res.setHeader('Content-Type', 'application/zip');
    res.setHeader('Content-Disposition', `attachment; filename="resumes-${timestamp}.zip"`);

    // Pipe archive to response
    archive.pipe(res);

    // Add each resume file to the archive
    let addedCount = 0;
    for (const resume of resumes) {
      const filePath = path.join('/app', config.uploadPath, resume.job_id.toString(), 'resumes', resume.filename);

      if (fs.existsSync(filePath)) {
        const candidateName = resume.parsed_content?.profile?.name || resume.filename.replace(/\.(pdf|doc|docx)$/i, '');
        const sanitizedName = candidateName.replace(/[^a-z0-9_-]/gi, '_');
        const ext = path.extname(resume.filename);
        const filename = `${sanitizedName}${ext}`;

        archive.file(filePath, { name: filename });
        addedCount++;
      } else {
        console.warn(`File not found: ${filePath}`);
      }
    }

    if (addedCount === 0) {
      res.status(404).json({
        success: false,
        error: 'No resume files found on disk'
      });
      return;
    }

    // Finalize the archive
    await archive.finalize();

    console.log(`✅ Bulk download: ${addedCount} resumes zipped successfully`);
  } catch (error) {
    console.error('Error during bulk download:', error);
    if (!res.headersSent) {
      res.status(500).json({
        success: false,
        error: 'Failed to create resume archive'
      });
    }
  }
});

// POST /api/resumes/upload - Upload resumes for a job
router.post('/upload', resumeUpload.array('resumes', 500), async (req: Request, res: Response): Promise<void> => {
  try {
    const { job_id } = req.body;
    const files = req.files as Express.Multer.File[];

    if (!files || files.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No files uploaded'
      });
      return;
    }

    if (!job_id) {
      res.status(400).json({
        success: false,
        error: 'Job ID is required'
      });
      return;
    }

    // Verify job exists
    const job = await Job.findById(job_id);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Check if resume upload is allowed based on status level
    const operationCheck = isOperationAllowed(job.status, 'RESUME_UPLOAD');
    if (!operationCheck.allowed) {
      res.status(400).json({
        success: false,
        error: operationCheck.reason
      });
      return;
    }

    const uploadedResumes = [];

    // Create resume records
    for (const file of files) {
      const resume = new Resume({
        filename: file.filename,
        original_name: file.originalname,
        job_id: job_id,
        candidate_name: file.originalname.replace(/\.[^.]+$/, ''), // Use filename without extension
        status: 'pending',
        parsed_content: {
          profile: {
            name: file.originalname.replace(/\.[^.]+$/, ''),
            email: 'pending@extraction.com'
          },
          domain: 'Full stack', // Default domain
          confidence: 0,
          skills: { provided: [], inferred: [], soft_skills: [] },
          experience: { total_full_time_experience: 0, total_internship_experience_in_months: 0, details: [] },
          projects: [],
          educations: [],
          certifications: [],
          achievements: [],
          candidate_id: `resume-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`
        }
      });

      await resume.save();
      uploadedResumes.push(resume);
    }

    res.status(201).json({
      success: true,
      data: uploadedResumes,
      count: uploadedResumes.length,
      message: `${uploadedResumes.length} resumes uploaded successfully`
    });
  } catch (error) {
    console.error('Error uploading resumes:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to upload resumes'
    });
  }
});

// PATCH /api/resumes/:id - Update resume fields
router.patch('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const resumeId = req.params.id;
    const updateData = req.body;

    // Map status values from Python processor to database values
    if (updateData.overall_processing_status) {
      const statusMap: { [key: string]: string } = {
        'processing': 'started',
        'success': 'completed',
        'failed': 'failed',
        'started': 'started',
        'completed': 'completed',
        'draft': 'draft'
      };
      updateData.status = statusMap[updateData.overall_processing_status] || updateData.overall_processing_status;
      delete updateData.overall_processing_status;
    }

    const resume = await Resume.findByIdAndUpdate(
      resumeId,
      updateData,
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

export default router;