import mongoose, { Document, Schema } from 'mongoose';

/**
 * Resume Model - Standardized structure with separate schemas
 * Stores parsed resume data and scores
 */

// ==========================================
// INTERFACE DEFINITIONS
// ==========================================

interface IContact {
  email: string;
  phone?: string;
  profile?: string;
}

interface ICanonicalSkills {
  programming?: string[];
  ml_ai?: string[];
  frontend?: string[];
  backend?: string[];
  testing?: string[];
  databases?: string[];
  cloud?: string[];
  infra?: string[];
  devtools?: string[];
  methodologies?: string[];
}

interface IInferredSkill {
  skill: string;
  confidence: number;
  provenance: string[];
}

interface ISkillProficiency {
  skill: string;
  level: string;
  years_last_used?: number;
  provenance?: string[];
}

interface IProjectMetrics {
  difficulty: number;
  novelty: number;
  skill_relevance: number;
  complexity: number;
  technical_depth: number;
  domain_relevance: number;
  execution_quality: number;
}

interface IProject {
  name: string;
  duration_start?: string;
  duration_end?: string;
  role?: string;
  domain?: string;
  tech_keywords?: string[];
  approach?: string;
  impact_metrics?: Record<string, any>;
  primary_skills?: string[];
  metrics?: IProjectMetrics;
}

interface IProvenanceSpan {
  start: number;
  end: number;
  text: string;
}

interface IExperienceEntry {
  company: string;
  title: string;
  period_start?: string;
  period_end?: string;
  responsibilities_keywords?: string[];
  achievements?: string[];
  primary_tech?: string[];
  provenance_spans?: IProvenanceSpan[];
}

interface IEducation {
  degree: string;
  field: string;
  institution: string;
  year?: string;
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
  candidate_id: string;
  name: string;
  role_claim?: string;
  years_experience?: number;
  location?: string;
  contact: IContact;
  domain_tags?: string[];
  profile_keywords_line: string;
  canonical_skills: ICanonicalSkills;
  inferred_skills?: IInferredSkill[];
  skill_proficiency?: ISkillProficiency[];
  projects?: IProject[];
  experience_entries?: IExperienceEntry[];
  education?: IEducation[];
  ats_boost_line: string;
  embedding_hints?: IEmbeddingHints;
  explainability?: IExplainability;
  meta?: IMeta;
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
  hard_requirements?: {
    meets_all_requirements: boolean;
    compliance_score: number;
    requirements_met: string[];
    requirements_missing: string[];
    filter_reason?: string;
  };
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
  candidate_id: { type: String, required: true },
  name: { type: String, required: true },
  role_claim: String,
  years_experience: Number,
  location: String,
  contact: {
    email: { type: String, required: true },
    phone: String,
    profile: String
  },
  domain_tags: [String],
  profile_keywords_line: { type: String, required: true },
  canonical_skills: {
    programming: [String],
    ml_ai: [String],
    frontend: [String],
    backend: [String],
    testing: [String],
    databases: [String],
    cloud: [String],
    infra: [String],
    devtools: [String],
    methodologies: [String]
  },
  inferred_skills: [{
    skill: String,
    confidence: Number,
    provenance: [String]
  }],
  skill_proficiency: [{
    skill: String,
    level: String,
    years_last_used: Number,
    provenance: [String]
  }],
  projects: [{
    name: String,
    duration_start: String,
    duration_end: String,
    role: String,
    domain: String,
    tech_keywords: [String],
    approach: String,
    impact_metrics: Schema.Types.Mixed,
    primary_skills: [String],
    metrics: {
      difficulty: Number,
      novelty: Number,
      skill_relevance: Number,
      complexity: Number,
      technical_depth: Number,
      domain_relevance: Number,
      execution_quality: Number
    }
  }],
  experience_entries: [{
    company: String,
    title: String,
    period_start: String,
    period_end: String,
    responsibilities_keywords: [String],
    achievements: [String],
    primary_tech: [String],
    provenance_spans: [{
      start: Number,
      end: Number,
      text: String
    }]
  }],
  education: [{
    degree: String,
    field: String,
    institution: String,
    year: String
  }],
  ats_boost_line: { type: String, required: true },
  embedding_hints: {
    profile_embed: String,
    projects_embed: String,
    skills_embed: String
  },
  explainability: {
    top_matched_sentences: [String],
    top_matched_keywords: [String]
  },
  meta: {
    raw_text_length: Number,
    keyword_occurrences: Schema.Types.Mixed,
    last_updated: String
  }
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
    details: Schema.Types.Mixed
  },
  project_score: Number,
  keyword_score: Number,
  semantic_score: Number,
  composite_score: Number,
  hard_requirements: {
    meets_all_requirements: Boolean,
    compliance_score: Number,
    requirements_met: [String],
    requirements_missing: [String],
    filter_reason: String
  }
}, { _id: false });

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
resumeSchema.index({ 'parsed_content.contact.email': 1 });
resumeSchema.index({ bullmq_job_id: 1 });
resumeSchema.index({ createdAt: -1 });

// Virtual for candidate email
resumeSchema.virtual('candidate_email').get(function () {
  return this.parsed_content?.contact?.email || '';
});

// Ensure virtuals are included in JSON output
resumeSchema.set('toJSON', { virtuals: true });
resumeSchema.set('toObject', { virtuals: true });

export default mongoose.model<IResume>('Resume', resumeSchema);