/**
 * Score Run Mongoose Model — Parent Record
 *
 * One ScoreRun = one submission: 1 JD evaluated against N resumes.
 * Each individual (JD, Resume) pair is stored as a ScorePair child document,
 * and enqueued as its own independent job.
 *
 * The ScoreRun holds aggregate progress counts so the runs list can be
 * rendered without fetching every pair.
 */

import mongoose, { Schema, Document, Model } from 'mongoose';

// ========== Interface ==========

export interface IScoreRun extends Document {
  // JD reference (denormalised for display)
  jdId: mongoose.Types.ObjectId;
  jdFileName: string;

  // Aggregate progress
  totalResumes:    number;
  completedCount:  number;
  failedCount:     number;

  // Overall run lifecycle (derived from pair statuses)
  status: 'queued' | 'processing' | 'completed' | 'failed';

  createdAt:   Date;
  completedAt?: Date;
}

// ========== Schema ==========

const ScoreRunSchema = new Schema<IScoreRun>(
  {
    jdId:       { type: Schema.Types.ObjectId, required: true, ref: 'JD' },
    jdFileName: { type: String, required: true },

    totalResumes:   { type: Number, required: true, default: 0 },
    completedCount: { type: Number, default: 0 },
    failedCount:    { type: Number, default: 0 },

    status: {
      type:    String,
      enum:    ['queued', 'processing', 'completed', 'failed'],
      default: 'queued',
    },
    completedAt: Date,
  },
  {
    timestamps: true, // createdAt + updatedAt
  }
);

// ========== Indexes ==========

ScoreRunSchema.index({ jdId: 1, createdAt: -1 });
ScoreRunSchema.index({ status: 1 });

// ========== Model ==========

const ScoreRun: Model<IScoreRun> =
  (mongoose.models.ScoreRun as Model<IScoreRun>) ||
  mongoose.model<IScoreRun>('ScoreRun', ScoreRunSchema);

export default ScoreRun;
