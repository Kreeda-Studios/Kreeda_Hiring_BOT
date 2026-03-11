/**
 * Score Pair Mongoose Model
 *
 * One document = one (JD, Resume) evaluation pair, always linked to a parent ScoreRun.
 * When a user submits 1 JD against N resumes, N ScorePair documents are created
 * (one per resume), each enqueued as an independent job.
 */

import mongoose, { Schema, Document, Model } from 'mongoose';

// ========== Interface ==========

export interface IScorePair extends Document {
  // Parent run reference
  scoreRunId: mongoose.Types.ObjectId;

  // JD reference (denormalised for easy job-data lookup)
  jdId: mongoose.Types.ObjectId;

  // Resume reference (denormalised for display)
  resumeId: mongoose.Types.ObjectId;
  resumeFileName: string;
  candidateName?: string;

  // Pair lifecycle
  status: 'queued' | 'processing' | 'completed' | 'failed';
  errorMessage?: string;
  createdAt: Date;
  completedAt?: Date;

  // AI-generated scores (0.0 – 1.0) — filled after processing
  overallScore?: number;
  skillMatch?: number;
  experienceMatch?: number;
  techStackMatch?: number;
  projectRelevance?: number;
  responsibilityMatch?: number;
  impactStrength?: number;
  educationMatch?: number;
  criticalSkillGapScore?: number;

  // Qualitative outputs
  missingSkills: string[];
  strengths: string[];
  concerns: string[];
}

// ========== Schema ==========

const ScorePairSchema = new Schema<IScorePair>(
  {
    scoreRunId: { type: Schema.Types.ObjectId, required: true, ref: 'ScoreRun' },
    jdId:       { type: Schema.Types.ObjectId, required: true, ref: 'JD' },

    resumeId:       { type: Schema.Types.ObjectId, required: true, ref: 'Resume' },
    resumeFileName: { type: String, required: true },
    candidateName:  String,

    status: {
      type:    String,
      enum:    ['queued', 'processing', 'completed', 'failed'],
      default: 'queued',
    },
    errorMessage: String,
    completedAt:  Date,

    // Scores
    overallScore:          { type: Number, min: 0, max: 1 },
    skillMatch:            { type: Number, min: 0, max: 1 },
    experienceMatch:       { type: Number, min: 0, max: 1 },
    techStackMatch:        { type: Number, min: 0, max: 1 },
    projectRelevance:      { type: Number, min: 0, max: 1 },
    responsibilityMatch:   { type: Number, min: 0, max: 1 },
    impactStrength:        { type: Number, min: 0, max: 1 },
    educationMatch:        { type: Number, min: 0, max: 1 },
    criticalSkillGapScore: { type: Number, min: 0, max: 1 },

    missingSkills: { type: [String], default: [] },
    strengths:     { type: [String], default: [] },
    concerns:      { type: [String], default: [] },
  },
  {
    timestamps: true, // createdAt + updatedAt
  }
);

// ========== Indexes ==========

ScorePairSchema.index({ scoreRunId: 1, createdAt: 1 });
ScorePairSchema.index({ jdId: 1 });
ScorePairSchema.index({ resumeId: 1 });
ScorePairSchema.index({ status: 1 });

// ========== Model ==========

const ScorePair: Model<IScorePair> =
  (mongoose.models.ScorePair as Model<IScorePair>) ||
  mongoose.model<IScorePair>('ScorePair', ScorePairSchema);

export default ScorePair;
