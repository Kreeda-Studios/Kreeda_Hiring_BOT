/**
 * Resume Service
 * Business logic for resume operations
 */

import { Resume } from '../models';
import type { IResume } from '../models/resume';
import { resumeQueue } from '../config/bullmq';
import { connectToDatabase } from '../config/database';

export interface CreateResumeData {
  fileName: string;
  originalFileName: string;
  resumeFilePath: string;
  fileSize: number;
  fileType: 'pdf' | 'docx';
}

export interface ResumeFilters {
  status?: 'uploaded' | 'processing' | 'completed' | 'failed';
  search?: string;
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginatedResumes {
  resumes: IResume[];
  total: number;
  page: number;
  totalPages: number;
}

export class ResumeService {
  /**
   * Create a new resume entry in database
   */
  static async createResume(data: CreateResumeData): Promise<IResume> {
    await connectToDatabase();
    
    const resume = await Resume.create({
      fileName: data.fileName,
      originalFileName: data.originalFileName,
      resumeFilePath: data.resumeFilePath,
      fileSize: data.fileSize,
      fileType: data.fileType,
      status: 'uploaded',
      uploadedAt: new Date(),
    });

    return resume;
  }

  /**
   * Get paginated list of resumes with filters
   */
  static async getResumes(
    filters: ResumeFilters,
    pagination: PaginationParams
  ): Promise<PaginatedResumes> {
    await connectToDatabase();

    const query: any = {};

    if (filters.status) {
      query.status = filters.status;
    }

    if (filters.search) {
      query.$or = [
        { fileName: { $regex: filters.search, $options: 'i' } },
        { originalFileName: { $regex: filters.search, $options: 'i' } },
        { 'profile.name': { $regex: filters.search, $options: 'i' } },
      ];
    }

    const total = await Resume.countDocuments(query);
    const totalPages = Math.ceil(total / pagination.limit);
    const skip = (pagination.page - 1) * pagination.limit;

    const resumes = await Resume.find(query)
      .sort({ uploadedAt: -1 })
      .skip(skip)
      .limit(pagination.limit);

    return {
      resumes,
      total,
      page: pagination.page,
      totalPages,
    };
  }

  /**
   * Get a single resume by ID
   */
  static async getResumeById(id: string): Promise<IResume | null> {
    await connectToDatabase();
    return Resume.findById(id);
  }

  /**
   * Update resume status
   */
  static async updateResumeStatus(
    id: string,
    status: 'uploaded' | 'processing' | 'completed' | 'failed',
    error?: string
  ): Promise<IResume | null> {
    await connectToDatabase();

    const update: any = { status };

    if (status === 'completed') {
      update.processedAt = new Date();
    }

    if (error) {
      update.processingError = error;
    }

    return Resume.findByIdAndUpdate(id, update, { new: true });
  }

  /**
   * Add resume to processing queue
   */
  static async addToQueue(resumeId: string, fileName: string, s3Key: string): Promise<void> {
    await resumeQueue.add(
      'process-resume',
      {
        resumeId,
        fileName,
        s3Bucket: process.env.MINIO_BUCKET_RESUMES!,
        s3Key,
        originalFileName: fileName,
      },
      {
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 2000,
        },
      }
    );
  }

  /**
   * Get resume statistics
   */
  static async getStats(): Promise<{
    total: number;
    uploaded: number;
    processing: number;
    completed: number;
    failed: number;
  }> {
    await connectToDatabase();

    const [total, uploaded, processing, completed, failed] = await Promise.all([
      Resume.countDocuments(),
      Resume.countDocuments({ status: 'uploaded' }),
      Resume.countDocuments({ status: 'processing' }),
      Resume.countDocuments({ status: 'completed' }),
      Resume.countDocuments({ status: 'failed' }),
    ]);

    return { total, uploaded, processing, completed, failed };
  }
}
