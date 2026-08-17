import mongoose, { Document, Schema } from 'mongoose';

/**
 * Resume Model - Standardized structure with separate schemas
 * Stores parsed resume data and scores
 */

// ==========================================
// INTERFACE DEFINITIONS
// ==========================================

interface IContact {
  email?: string;
  phone?: string;
  profile?: string;
}

interface IProfile {
  name?: string;
  contact?: string;
  email?: string;
  linkedin?: string;
  github?: string;
  leetcode?: string;
  hackerrank?: string;
  location?: string;
}

interface IMetricAI {
  impact: number;
  difficulty: number;
  complexity: number;
  domain_relevance: number;
}

interface IProject {
  title?: string;
  demo_link?: string;
  code_link?: string;
  metric_ai: IMetricAI;
}

interface IExperienceDetail {
  company?: string;
  role?: string;
  start?: string;
  end?: string;
  employment_type?: string;
  impact: string[];
}

interface IExperience {
  total_full_time_experience: number;
  total_internship_experience_in_months: number;
  details: IExperienceDetail[];
}

interface ISkills {
  provided: string[];
  inferred: string[];
  soft_skills: string[];
}

interface IEducation {
  start?: string;
  end?: string;
  college?: string;
  degree?: string;
  department?: string;
  grade?: string;
}

interface IEmbeddingHints {
  profile_embed?: string;
  projects_embed?: string;
  skills_embed?: string;
}

interface IExplainability {
  top_matched_sentences?: string[];
  top_matched_keywords?: string[];
}

interface IMeta {
  raw_text_length?: number;
  keyword_occurrences?: Record<string, any>;
  last_updated?: string;
}

interface IParsedContent {
  profile: IProfile;
  domain: string;
  confidence: number;
  skills: ISkills;
  experience: IExperience;
  projects: IProject[];
  educations: IEducation[];
  certifications: string[];
  achievements: string[];

  // Internal fields
  candidate_id: string;
  processed_date?: string;
  raw_text?: string;
  meta_data?: any;
}

interface IResumeEmbedding {
  model?: string;
  dimension?: number;
  profile?: number[][];
  skills?: number[][];
  projects?: number[][];
  responsibilities?: number[][];
  education?: number[][];
  overall?: number[][];
}

interface IScores {
  hard_requirements?: {
    meets_all_requirements?: boolean;
    compliance_score?: number;
    requirements_met?: string[];
    requirements_missing?: string[];
    filter_reason?: string;
    details?: any;
  };
  project_score?: number;
  keyword_score?: number;
  semantic_score?: number;
  composite_score?: number;
}

export interface IResume extends Document {
  // File information
  filename: string;
  original_name: string;
  job_id: mongoose.Types.ObjectId;
  candidate_name: string;

  // Processing status
  status: 'pending' | 'processing' | 'completed' | 'failed' | 'filtered';
  processing_progress?: number; // 0-100
  processing_error?: string;
  bullmq_job_id?: string; // Individual resume processing job ID

  // AI Parser output - structured according to b_ai_parser.py PARSE_FUNCTION
  parsed_content: IParsedContent;

  // Resume embeddings for semantic scoring (6 sections from d_embedding_generator.py)
  resume_embedding?: IResumeEmbedding;

  // Scoring results
  scores?: IScores;

  // Hard requirements compliance (main field, not under scores)
  hard_requirements_met?: boolean;

  // Timestamps
  createdAt: Date;
  updatedAt: Date;
}


// ==========================================
// SCHEMA DEFINITIONS
// ==========================================

// Parsed Content Schema
const parsedContentSchema = new Schema({
  profile: {
    name: String,
    contact: String,
    email: String,
    linkedin: String,
    github: String,
    leetcode: String,
    hackerrank: String,
    location: String
  },
  domain: { type: String, required: true },
  confidence: { type: Number, required: true },
  skills: {
    provided: [String],
    inferred: [String],
    soft_skills: [String]
  },
  experience: {
    total_full_time_experience: Number,
    total_internship_experience_in_months: Number,
    details: [{
      company: String,
      role: String,
      start: String,
      end: String,
      employment_type: String,
      impact: [String]
    }]
  },
  projects: [{
    title: String,
    demo_link: String,
    code_link: String,
    metric_ai: {
      impact: Number,
      difficulty: Number,
      complexity: Number,
      domain_relevance: Number
    }
  }],
  educations: [{
    start: String,
    end: String,
    college: String,
    degree: String,
    department: String,
    grade: String
  }],
  certifications: [String],
  achievements: [String],

  // Internal fields
  candidate_id: { type: String, required: true },
  processed_date: String,
  raw_text: String,
  meta_data: Schema.Types.Mixed
}, { _id: false });

// Resume Embedding Schema
const resumeEmbeddingSchema = new Schema({
  model: {
    type: String,
    default: 'text-embedding-3-small'
  },
  dimension: {
    type: Number,
    default: 1536
  },
  profile: [[Number]],
  skills: [[Number]],
  projects: [[Number]],
  responsibilities: [[Number]],
  education: [[Number]],
  overall: [[Number]]
}, { _id: false });

// Scores Schema
const scoresSchema = new Schema({
  hard_requirements: {
    meets_all_requirements: Boolean,
    compliance_score: Number,
    requirements_met: [String],
    requirements_missing: [String],
    filter_reason: String,
    selection_reason: String,
    details: Schema.Types.Mixed
  },
  project_score: Number,
  keyword_score: Number,
  semantic_score: Number,
  section_scores: Schema.Types.Mixed,
  composite_score: Number,
}, { _id: false, strict: false });

// ==========================================
// MAIN RESUME SCHEMA
// ==========================================

const resumeSchema = new Schema<IResume>({
  // File information
  filename: {
    type: String,
    required: true,
    index: true
  },
  original_name: {
    type: String,
    required: true
  },
  job_id: {
    type: Schema.Types.ObjectId,
    ref: 'Job',
    required: true,
    index: true
  },
  candidate_name: {
    type: String,
    required: false,
    index: true
  },

  // Processing status
  status: {
    type: String,
    enum: ['pending', 'processing', 'completed', 'failed', 'filtered'],
    default: 'pending'
  },
  processing_progress: {
    type: Number,
    min: 0,
    max: 100,
    default: 0
  },
  processing_error: String,
  bullmq_job_id: {
    type: String,
    index: true
  },

  // Hard requirements compliance (main field)
  hard_requirements_met: {
    type: Boolean,
    index: true
  },

  // Structured data (clean sub-schemas)
  parsed_content: parsedContentSchema,
  resume_embedding: resumeEmbeddingSchema,
  scores: scoresSchema
}, {
  timestamps: true
});

// Add indexes for better query performance
resumeSchema.index({ job_id: 1, status: 1 });
resumeSchema.index({ job_id: 1, hard_requirements_met: 1 });
resumeSchema.index({ candidate_name: 1 });
resumeSchema.index({ 'parsed_content.profile.email': 1 });
resumeSchema.index({ bullmq_job_id: 1 });
resumeSchema.index({ createdAt: -1 });

// Virtual for candidate email
resumeSchema.virtual('candidate_email').get(function () {
  return this.parsed_content?.profile?.email || '';
});

// Ensure virtuals are included in JSON output
resumeSchema.set('toJSON', { virtuals: true });
resumeSchema.set('toObject', { virtuals: true });

export default mongoose.model<IResume>('Resume', resumeSchema);