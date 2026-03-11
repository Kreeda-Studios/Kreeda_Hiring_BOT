/**
 * Job Description (JD) Service
 * Business logic for JD operations
 */

import { JD } from '../models';
import type { IJD } from '../models/jd';
import { jdQueue } from '../config/bullmq';
import { connectToDatabase } from '../config/database';
import { s3Config } from '../config/s3';

export interface CreateJDData {
  fileName: string;
  originalFileName: string;
  jdFilePath: string;
  fileSize: number;
  fileType: 'pdf' | 'docx';
}

export interface JDFilters {
  status?: 'uploaded' | 'processing' | 'completed' | 'failed';
  search?: string;
}

export interface PaginationParams {
  page: number;
  limit: number;
}

export interface PaginatedJDs {
  jds: IJD[];
  total: number;
  page: number;
  totalPages: number;
}

export class JDService {
  /**
   * Create a new JD entry in the database
   */
  static async createJD(data: CreateJDData): Promise<IJD> {
    await connectToDatabase();

    const jd = await JD.create({
      fileName: data.fileName,
      originalFileName: data.originalFileName,
      jdFilePath: data.jdFilePath,
      fileSize: data.fileSize,
      fileType: data.fileType,
      status: 'uploaded',
      uploadedAt: new Date(),
      extractedData: {},
    });

    return jd;
  }

  /**
   * Get paginated list of JDs with optional filters
   */
  static async getJDs(
    filters: JDFilters,
    pagination: PaginationParams
  ): Promise<PaginatedJDs> {
    await connectToDatabase();

    const query: Record<string, unknown> = {};

    if (filters.status) {
      query.status = filters.status;
    }

    if (filters.search) {
      query.$or = [
        { fileName: { $regex: filters.search, $options: 'i' } },
        { originalFileName: { $regex: filters.search, $options: 'i' } },
      ];
    }

    const total = await JD.countDocuments(query);
    const totalPages = Math.ceil(total / pagination.limit);
    const skip = (pagination.page - 1) * pagination.limit;

    const jds = await JD.find(query)
      .sort({ uploadedAt: -1 })
      .skip(skip)
      .limit(pagination.limit);

    return { jds, total, page: pagination.page, totalPages };
  }

  /**
   * Get a single JD by ID
   */
  static async getJDById(id: string): Promise<IJD | null> {
    await connectToDatabase();
    return JD.findById(id);
  }

  /**
   * Update JD processing status
   */
  static async updateJDStatus(
    id: string,
    status: 'uploaded' | 'processing' | 'completed' | 'failed',
    error?: string
  ): Promise<IJD | null> {
    await connectToDatabase();

    const update: Record<string, unknown> = { status };

    if (status === 'completed') {
      update.processedAt = new Date();
    }

    if (error) {
      update.processingError = error;
    }

    return JD.findByIdAndUpdate(id, update, { new: true });
  }

  /**
   * Update JD with AI-extracted data
   */
  static async updateJDExtractedData(
    id: string,
    extractedData: Record<string, unknown>
  ): Promise<IJD | null> {
    await connectToDatabase();

    return JD.findByIdAndUpdate(
      id,
      {
        extractedData,
        status: 'completed',
        processedAt: new Date(),
      },
      { new: true }
    );
  }

  /**
   * Add JD to the processing queue
   */
  static async addToQueue(jdId: string, fileName: string, s3Key: string): Promise<void> {
    await jdQueue.add(
      'process-jd',
      {
        jdId,
        fileName,
        s3Bucket: s3Config.buckets.jds,
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
   * Get JD processing statistics
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
      JD.countDocuments(),
      JD.countDocuments({ status: 'uploaded' }),
      JD.countDocuments({ status: 'processing' }),
      JD.countDocuments({ status: 'completed' }),
      JD.countDocuments({ status: 'failed' }),
    ]);

    return { total, uploaded, processing, completed, failed };
  }
}
