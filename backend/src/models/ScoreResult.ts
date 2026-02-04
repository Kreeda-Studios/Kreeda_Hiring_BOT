import mongoose, { Document, Schema } from 'mongoose';

export interface IScoreResult extends Document {
  job_id: mongoose.Types.ObjectId;
  resume_id: mongoose.Types.ObjectId;
  project_score: number;
  keyword_score: number;
  semantic_score: number;
  final_score: number;
  recalculated_llm_score: number;
  hard_requirements_met: boolean;
  rank?: number;
  adjusted_score?: number;
  score_breakdown?: {
    project_metrics?: {
      difficulty?: number;
      novelty?: number;
      skill_relevance?: number;
      complexity?: number;
      technical_depth?: number;
      domain_relevance?: number;
      execution_quality?: number;
      weighted_avg?: number;
    };
    keyword_components?: {
      required_skills_match?: number;
      preferred_skills_match?: number;
      experience_keywords?: number;
      weighted_score?: number;
    };
    semantic_components?: {
      skills_similarity?: number;
      projects_similarity?: number;
      experience_similarity?: number;
      weighted_score?: number;
    };
    llm_feedback?: string;
  };
  createdAt: Date;
  updatedAt: Date;
}

const scoreResultSchema = new Schema<IScoreResult>({
  job_id: {
    type: Schema.Types.ObjectId,
    ref: 'Job',
    required: true
  },
  resume_id: {
    type: Schema.Types.ObjectId,
    ref: 'Resume',
    required: true
  },
  project_score: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  keyword_score: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  semantic_score: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  final_score: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  recalculated_llm_score: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  hard_requirements_met: {
    type: Boolean,
    default: true
  },
  rank: {
    type: Number,
    required: false
  },
  adjusted_score: {
    type: Number,
    required: false
  },
  score_breakdown: {
    type: Schema.Types.Mixed,
    required: false
  }
}, {
  timestamps: true
});

// Add compound index for unique job-resume pair
scoreResultSchema.index({ job_id: 1, resume_id: 1 }, { unique: true });

// Add index for sorting by score
scoreResultSchema.index({ job_id: 1, final_score: -1 });

export default mongoose.model<IScoreResult>('ScoreResult', scoreResultSchema);