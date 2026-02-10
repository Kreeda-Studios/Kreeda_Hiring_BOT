import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import { Job, Resume } from '../models';
import config from '../config';

const router = Router();

// Configure multer for JD file uploads
const jdStorage = multer.diskStorage({
  destination: (req, file, cb) => {
    // Use absolute path from Docker mount point or local
    const uploadDir = path.join('/app', config.uploadPath, 'jds');
    console.log('📁 Multer destination:', uploadDir);
    if (!fs.existsSync(uploadDir)) {
      console.log('📁 Creating directory:', uploadDir);
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    const filename = uniqueSuffix + '-' + file.originalname;
    console.log('\ud83d\udcdd Multer filename:', filename);
    cb(null, filename);
  }
});

const jdUpload = multer({
  storage: jdStorage,
  limits: { fileSize: 10 * 1024 * 1024 }, // 10MB limit
  fileFilter: (req, file, cb) => {
    console.log('\ud83d\udd0d File filter check:', file.mimetype);
    if (file.mimetype === 'application/pdf') {
      cb(null, true);
    } else {
      cb(new Error('Only PDF files are allowed for JD upload'));
    }
  }
});

// GET /api/jobs - Get all jobs
router.get('/', async (req: Request, res: Response) => {
  try {
    const jobs = await Job.find()
      .select('title description status createdAt updatedAt')
      .sort({ createdAt: -1 });

    res.json({
      success: true,
      data: jobs,
      count: jobs.length
    });
  } catch (error) {
    console.error('Error fetching jobs:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch jobs'
    });
  }
});

// GET /api/jobs/:id - Get job by ID
router.get('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const job = await Job.findById(req.params.id);

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
    console.error('Error fetching job:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch job'
    });
  }
});

// GET /api/jobs/:id/status - Get job processing status and resume status
router.get('/:id/status', async (req: Request, res: Response): Promise<void> => {
  try {
    const job = await Job.findById(req.params.id).select(
      'title status locked jd_processing_status jd_processing_progress jd_processing_error ' +
      'resume_processing_status resume_processing_progress resume_processing_error bullmq_jobs'
    );

    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Get resume statistics
    const resumes = await Resume.find({ job_id: req.params.id }).select(
      'filename original_name overall_processing_status processing_progress processing_error bullmq_job_id'
    );

    const resumeStats = {
      total_resumes: resumes.length,
      processing_count: resumes.filter(r => r.overall_processing_status === 'processing').length,
      completed_count: resumes.filter(r => r.overall_processing_status === 'success').length,
      failed_count: resumes.filter(r => r.overall_processing_status === 'failed').length,
    };

    const statusData = {
      job: {
        id: job._id,
        title: job.title,
        status: job.status,
        locked: job.locked,
        jd_processing: {
          status: job.jd_processing_status,
          progress: job.jd_processing_progress || 0,
          error: job.jd_processing_error,
          job_id: job.bullmq_jobs?.jd_processing_job_id
        },
        resume_processing: {
          status: job.resume_processing_status,
          progress: job.resume_processing_progress || 0,
          error: job.resume_processing_error,
          parent_job_id: job.bullmq_jobs?.resume_processing_parent_job_id,
          ...resumeStats
        }
      },
      resumes: resumes.map(resume => ({
        id: resume._id,
        filename: resume.filename,
        original_name: resume.original_name,
        status: resume.overall_processing_status,
        progress: resume.processing_progress || 0,
        error: resume.processing_error,
        job_id: resume.bullmq_job_id
      }))
    };

    res.json({
      success: true,
      data: statusData
    });
  } catch (error) {
    console.error('Error fetching job status:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to fetch job status'
    });
  }
});

// POST /api/jobs - Create new job
router.post('/', async (req: Request, res: Response): Promise<void> => {
  try {
    const { title, description } = req.body;

    // Validate required fields
    if (!title) {
      res.status(400).json({
        success: false,
        error: 'Title is required'
      });
      return;
    }


    const job = new Job({
      title,
      description,
      status: 'draft',
      resume_groups: []
    });

    await job.save();

    res.status(201).json({
      success: true,
      data: job,
      message: 'Job created successfully'
    });
    return;
  } catch (error) {
    console.error('Error creating job:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to create job'
    });
    return;
  }
});

// PUT /api/jobs/:id - Update job
router.put('/:id', async (req: Request, res: Response): Promise<void> => {
  try {

    // Check if job exists first
    const existingJob = await Job.findById(req.params.id);
    if (!existingJob) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Check if job is locked
    if (existingJob.locked) {
      res.status(400).json({
        success: false,
        error: 'Job is locked and cannot be modified. JD has already been processed.'
      });
      return;
    }

    // Accept four variables directly in the request body
    const {
      jd_pdf_filename = '',
      jd_text = '',
      mandatory_compliances = '',
      soft_compliances = ''
    } = req.body;

    // Structure filter_requirements from the variables
    const filter_requirements = {
      mandatory_compliances: {
        raw_prompt: mandatory_compliances,
        structured: {}
      },
      soft_compliances: {
        raw_prompt: soft_compliances,
        structured: {}
      }
    };

    const updateData: any = {
      jd_pdf_filename,
      jd_text,
      filter_requirements
    };

    const job = await Job.findByIdAndUpdate(
      req.params.id,
      updateData,
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
    console.error('Error updating job:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update job'
    });
  }
});

// PATCH /api/jobs/:id - Partial update job (for scripts to update specific fields)
router.patch('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const updateData = req.body;

    const job = await Job.findByIdAndUpdate(
      req.params.id,
      { $set: updateData },
      { new: true, runValidators: false }
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
    console.error('Error updating job:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to update job'
    });
  }
});

// DELETE /api/jobs/:id - Delete job
router.delete('/:id', async (req: Request, res: Response): Promise<void> => {
  try {
    const job = await Job.findByIdAndDelete(req.params.id);

    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    res.json({
      success: true,
      message: 'Job deleted successfully'
    });
  } catch (error) {
    console.error('Error deleting job:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to delete job'
    });
  }
});

// POST /api/jobs/:id/upload-jd - Upload JD PDF (only saves path)
router.post('/:id/upload-jd', jdUpload.single('jd_pdf'), async (req: Request, res: Response): Promise<void> => {
  try {
    // Check if job exists and is not locked
    const job = await Job.findById(req.params.id);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    if (job.locked) {
      res.status(400).json({
        success: false,
        error: 'Job is locked and cannot be modified. JD has already been processed.'
      });
      return;
    }

    const file = req.file as Express.Multer.File;
    if (!file) {
      res.status(400).json({
        success: false,
        error: 'No JD PDF file uploaded'
      });
      return;
    }

    console.log('📁 File uploaded:', {
      filename: file.filename,
      path: file.path,
      size: file.size,
      mimetype: file.mimetype
    });

    // Verify file was actually saved
    if (!fs.existsSync(file.path)) {
      console.error('❌ File upload failed - file does not exist at path:', file.path);
      res.status(500).json({
        success: false,
        error: 'File upload failed - file not saved'
      });
      return;
    }

    console.log('✅ File exists on disk:', file.path);

    // Only return the file name, do not save to DB
    res.json({
      success: true,
      data: {
        filename: file.filename
      },
      message: 'JD PDF uploaded successfully.'
    });
    return;
  } catch (error) {
    console.error('❌ Error uploading JD PDF:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to upload JD PDF'
    });
    return;
  }
});

// Configure multer for resume uploads
const resumeStorage = multer.diskStorage({
  destination: (req, file, cb) => {
    const jobId = req.params.id;
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

// POST /api/jobs/:id/upload-resumes - Upload resumes for a job
router.post('/:id/upload-resumes', resumeUpload.array('resumes', 500), async (req: Request, res: Response): Promise<void> => {
  try {
    const jobId = req.params.id;
    const files = req.files as Express.Multer.File[];
    
    if (!files || files.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No files uploaded'
      });
      return;
    }

    // Verify job exists
    const job = await Job.findById(jobId);
    if (!job) {
      res.status(404).json({
        success: false,
        error: 'Job not found'
      });
      return;
    }

    // Prevent upload if resume processing is in progress
    if (job.resume_processing_status === 'processing') {
      res.status(400).json({
        success: false,
        error: 'Cannot upload resumes while resume processing is in progress. Please wait for current processing to complete.'
      });
      return;
    }

    const uploadedResumes = [];

    // Create resume records
    for (const file of files) {
      const resume = new Resume({
        filename: file.filename,
        original_name: file.originalname,
        job_id: jobId,
        overall_processing_status: 'pending',
        processing_progress: 0,
        extraction_status: 'pending',
        parsing_status: 'pending',
        embedding_status: 'pending'
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


export default router;