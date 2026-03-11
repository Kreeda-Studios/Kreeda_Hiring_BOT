/**
 * Job Description (JD) Mongoose Model
 * Schema for storing uploaded JD files and their AI-extracted structured data
 */

import mongoose, { Schema, Document, Model } from 'mongoose';

// ========== Interfaces ==========

export interface IJDExtractedData {
  // Placeholder — AI extraction fields to be defined later
  rawText?: string;
  [key: string]: unknown;
}

export interface IJD extends Document {
  // File metadata
  fileName: string;         // Prefixed unique filename stored in S3
  jdFilePath: string;       // S3 key
  originalFileName?: string;
  fileSize?: number;
  fileType?: string;        // 'pdf' | 'docx'

  // Timestamps
  uploadedAt: Date;
  processedAt?: Date;

  // Status lifecycle
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  processingError?: string;

  // AI-extracted data (schema intentionally open — to be filled by team)
  extractedData: IJDExtractedData;
}

// ========== Mongoose Schema ==========

const ExtractedDataSchema = new Schema<IJDExtractedData>(
  {
    rawText: String,
  },
  {
    _id: false,
    strict: false, // Allow any fields — team will extend this
  }
);

const JDSchema = new Schema<IJD>(
  {
    // File metadata
    fileName: { type: String, required: true, unique: true },
    jdFilePath: { type: String, required: true },
    originalFileName: String,
    fileSize: Number,
    fileType: { type: String, enum: ['pdf', 'docx'] },

    // Timestamps
    uploadedAt: { type: Date, default: Date.now },
    processedAt: Date,

    // Status
    status: {
      type: String,
      enum: ['uploaded', 'processing', 'completed', 'failed'],
      default: 'uploaded',
    },
    processingError: String,

    // Extracted data (open schema for flexibility)
    extractedData: {
      type: ExtractedDataSchema,
      default: {},
    },
  },
  {
    timestamps: true, // adds createdAt / updatedAt
  }
);

// ========== Indexes ==========

JDSchema.index({ status: 1, uploadedAt: -1 });

// ========== Model ==========

const JD: Model<IJD> = mongoose.models.JD || mongoose.model<IJD>('JD', JDSchema);

export { JD };
export default JD;
