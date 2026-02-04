import { Router, Request, Response } from 'express';
import multer from 'multer';
import path from 'path';
import fs from 'fs';
import ResumeGroup from '../models/ResumeGroup';
import { Job, Resume } from '../models';
import { QueueService } from '../services/queueService';
import config from '../config';

const router = Router();

// Configure multer for file uploads
const storage = multer.diskStorage({
  destination: (req, file, cb) => {
    // Get group_id from URL params (/:groupId/upload)
    const groupId = req.params.groupId || req.body.group_id;
    if (!groupId) {
      return cb(new Error('group_id is required'), '');
    }
    // Use absolute path from Docker mount point
    const uploadDir = path.join('/app', config.uploadPath, groupId, 'resumes');
    console.log('📁 Resume upload destination:', uploadDir);
    if (!fs.existsSync(uploadDir)) {
      console.log('📁 Creating directory:', uploadDir);
      fs.mkdirSync(uploadDir, { recursive: true });
    }
    cb(null, uploadDir);
  },
  filename: (req, file, cb) => {
    const uniqueSuffix = Date.now() + '-' + Math.round(Math.random() * 1E9);
    cb(null, file.fieldname + '-' + uniqueSuffix + path.extname(file.originalname));
  }
});

const upload = multer({
  storage: storage,
  limits: {
    fileSize: 50 * 1024 * 1024, // 50MB per file
    files: undefined, // No limit on number of files
    fieldSize: 25 * 1024 * 1024, // 25MB for non-file fields
    fields: undefined, // No limit on number of fields
    parts: undefined // No limit on number of parts
  },
  fileFilter: (req, file, cb) => {
    console.log('📁 FileFilter - Processing file:', file.fieldname, file.originalname);
    const allowedTypes = ['.pdf', '.doc', '.docx'];
    const ext = path.extname(file.originalname).toLowerCase();
    if (allowedTypes.includes(ext)) {
      cb(null, true);
    } else {
      console.log('📁 FileFilter - Rejected file type:', ext);
      cb(new Error('Only PDF, DOC, and DOCX files are allowed'));
    }
  }
});

// GET /api/resume-groups - Get all resume groups
router.get('/', async (req: Request, res: Response) => {
  try {
    const { page = 1, limit = 10 } = req.query;
    
    const pageNum = parseInt(page as string);
    const limitNum = parseInt(limit as string);
    const skip = (pageNum - 1) * limitNum;

    const [resumeGroups, total] = await Promise.all([
      ResumeGroup.find()
        .sort({ createdAt: -1 })
        .skip(skip)
        .limit(limitNum),
      ResumeGroup.countDocuments()
    ]);

    res.json({
      success: true,
      data: resumeGroups,
      count: total,
      page: pageNum,
      totalPages: Math.ceil(total / limitNum)
    });
    return;
  } catch (error) {
    console.error('Error fetching resume groups:', error);
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to fetch resume groups' 
    });
    return;
  }
});

// GET /api/resume-groups/:id - Get resume group by ID
router.get('/:id', async (req: Request, res: Response) => {
  try {
    const resumeGroup = await ResumeGroup.findById(req.params.id);

    if (!resumeGroup) {
      return res.status(404).json({ 
        success: false, 
        error: 'Resume group not found' 
      });
    }

    res.json({
      success: true,
      data: resumeGroup
    });
    return;
  } catch (error) {
    console.error('Error fetching resume group:', error);
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to fetch resume group' 
    });
    return;
  }
});

// POST /api/resume-groups - Create new resume group and optionally link to job
router.post('/', async (req: Request, res: Response) => {
  try {
    const { name, source = 'upload', job_id } = req.body;

    if (!name) {
      return res.status(400).json({ 
        success: false, 
        error: 'name is required' 
      });
    }

    const resumeGroup = new ResumeGroup({
      name,
      source,
      resume_count: 0
    });

    await resumeGroup.save();

    // If job_id is provided, link this resume group to the job
    if (job_id) {
      const job = await Job.findById(job_id);
      if (job) {
        job.resume_groups.push(resumeGroup._id);
        await job.save();
      }
    }

    res.status(201).json({
      success: true,
      data: resumeGroup
    });
    return;
  } catch (error) {
    console.error('Error creating resume group:', error);
    res.status(400).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to create resume group' 
    });
    return;
  }
});

// PUT /api/resume-groups/:id - Update resume group
router.put('/:id', async (req: Request, res: Response) => {
  try {
    const { name, source } = req.body;
    
    const resumeGroup = await ResumeGroup.findByIdAndUpdate(
      req.params.id,
      { name, source },
      { new: true, runValidators: true }
    );

    if (!resumeGroup) {
      return res.status(404).json({ 
        success: false, 
        error: 'Resume group not found' 
      });
    }

    res.json({
      success: true,
      data: resumeGroup
    });
    return;
  } catch (error) {
    console.error('Error updating resume group:', error);
    res.status(400).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to update resume group' 
    });
    return;
  }
});

// DELETE /api/resume-groups/:id - Delete resume group
router.delete('/:id', async (req: Request, res: Response) => {
  try {
    const resumeGroup = await ResumeGroup.findByIdAndDelete(req.params.id);

    if (!resumeGroup) {
      return res.status(404).json({ 
        success: false, 
        error: 'Resume group not found' 
      });
    }

    res.json({
      success: true,
      message: 'Resume group deleted successfully'
    });
    return;
  } catch (error) {
    console.error('Error deleting resume group:', error);
    res.status(500).json({ 
      success: false, 
      error: error instanceof Error ? error.message : 'Failed to delete resume group' 
    });
    return;
  }
});

// POST /api/resume-groups/:groupId/upload - Upload resumes to a resume group
router.post('/:groupId/upload', (req: Request, res: Response, next: any) => {
  console.log('📤 Resume upload request received:');
  console.log('📤 Request headers:', req.headers);
  console.log('📤 Content-Type:', req.get('Content-Type'));
  console.log('📤 Route params:', req.params);
  next();
}, upload.array('resumes', 1000), (error: any, req: Request, res: Response, next: any) => {
  if (error) {
    console.error('📤 Multer error during resume upload:', error);
    console.error('📤 Error code:', error.code);
    console.error('📤 Error field:', error.field);
    console.error('📤 Request body keys:', Object.keys(req.body || {}));
    console.error('📤 Request files:', req.files);
    
    if (error.code === 'LIMIT_UNEXPECTED_FILE') {
      return res.status(400).json({
        success: false,
        error: `Unexpected field: ${error.field}. Expected field name is 'resumes'`
      });
    }
    
    return res.status(400).json({
      success: false,
      error: error.message || 'File upload error'
    });
  }
  next();
  return;
}, async (req: Request, res: Response): Promise<void> => {
  try {
    const { groupId } = req.params;
    const { job_id } = req.body;
    const files = req.files as Express.Multer.File[];
    
    console.log('📤 Uploaded files count:', files?.length || 0);

    if (!files || files.length === 0) {
      res.status(400).json({
        success: false,
        error: 'No files uploaded'
      });
      return;
    }

    // Verify resume group exists
    const resumeGroup = await ResumeGroup.findById(groupId);
    if (!resumeGroup) {
      res.status(404).json({
        success: false,
        error: 'Resume group not found'
      });
      return;
    }

    const uploadedResumes = [];
    const resumeJobsData = [];

    // Create resume records and prepare job data
    for (const file of files) {
      // Store relative path for cross-environment compatibility
      const relativePath = path.join(config.uploadPath, groupId, 'resumes', file.filename);
      
      const resume = new Resume({
        filename: file.filename,
        original_name: file.originalname,
        group_id: groupId,
        extraction_status: 'pending',
        parsing_status: 'pending',
        embedding_status: 'pending'
      });

      await resume.save();
      uploadedResumes.push(resume);

      // Prepare job data for Flow
      resumeJobsData.push({
        resumeId: resume._id.toString(),
        jobId: job_id || '', // Optional job context
        resumeGroupId: groupId,
        fileName: file.originalname,
        filePath: relativePath
      });
    }

    // Update resume group count
    await ResumeGroup.findByIdAndUpdate(
      groupId,
      { $inc: { resume_count: files.length } }
    );

    // Always use Flow for parallel processing
    const queueResult = await QueueService.addResumeGroupFlow(
      {
        jobId: job_id || `group-${groupId}`,
        resumeGroupId: groupId,
        totalResumes: files.length
      },
      resumeJobsData
    );

    if (!queueResult.success) {
      res.status(500).json({
        success: false,
        error: queueResult.error || 'Failed to create Flow'
      });
      return;
    }

    res.status(201).json({
      success: true,
      data: uploadedResumes,
      count: uploadedResumes.length,
      flowJobId: queueResult.parentJobId,
      childrenCount: queueResult.childrenCount,
      message: `${uploadedResumes.length} resumes uploaded and queued for parallel processing via Flow`
    });
  } catch (error) {
    console.error('Error uploading resumes to group:', error);
    res.status(500).json({
      success: false,
      error: 'Failed to upload resumes to group'
    });
  }
});

export default router;