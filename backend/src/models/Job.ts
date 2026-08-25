import mongoose, { Document, Schema } from 'mongoose';

/**
 * Job Model with JD Analysis
 * Standardized structure with separate schemas for different sections
 */

// ==========================================
// INTERFACE DEFINITIONS
// ==========================================

interface IContract {
  duration_months?: number;
  extendable?: boolean;
}

interface ITechStack {
  languages: string[];
  frameworks: string[];
  libraries: string[];
  databases: string[];
  cloud: string[];
  tools: string[];
  ai_techniques: string[];
}

interface IJobProfile {
  role?: string;
  domain?: string;
  location?: string;
  work_mode?: string;
  job_type?: string;
  notice_period?: string;
}

interface IExperienceRequirements {
  minimum_experience_months: number;
  maximum_experience_months: number;
}

interface ISkills {
  required: string[];
  preferred: string[];
  soft_skills: string[];
}

interface IEducationRequirements {
  degrees: string[];
  fields: string[];
}

interface ISkillRequirement {
  skill: string;
  category?: string;
  priority?: string;
  level?: string;
  years_min?: number;
  versions?: string[];
  related_tools?: string[];
  mandatory?: boolean;
  provenance?: string[];
}

interface ITeamContext {
  team_size?: number;
  reports_to?: string;
  manages_team?: boolean;
  direct_reports?: number;
}

interface IInterviewStage {
  name?: string;
  purpose?: string;
  skills_evaluated?: string[];
}

interface IInterviewProcess {
  total_rounds?: number;
  stages?: IInterviewStage[];
  assignment_expected?: boolean;
}

interface ICompensation {
  currency?: string;
  salary_min?: number;
  salary_max?: number;
  period?: string;
  bonus?: string;
  equity?: string;
}

interface IWeighting {
  required_skills?: number;
  preferred_skills?: number;
  responsibilities?: number;
  domain_relevance?: number;
  technical_depth?: number;
  soft_skills?: number;
  education?: number;
  certifications?: number;
  keywords_exact?: number;
  keywords_semantic?: number;
}

interface IEmbeddingHints {
  skills_embed?: string;
  responsibilities_embed?: string;
  overall_embed?: string;
  negatives_embed?: string;
  seniority_embed?: string;
}

interface IExplainability {
  top_jd_sentences?: string[];
  key_phrases?: string[];
  rationales?: string[];
}

interface IProvenanceSpan {
  type: string;
  text: string;
}

interface IHRNote {
  category: string;
  type: 'recommendation' | 'inferred_requirement';
  note: string;
  impact?: number;
  reason?: string;
  source_provenance?: string[];
}

interface IMeta {
  jd_version?: string;
  raw_text_length?: number;
  last_updated?: string;
  sections_detected?: string[];
}

interface IFilterRequirements {
  mandatory_compliances?: {
    raw_prompt?: string;
    structured?: {
      experience?: {
        min?: number;
        max?: number;
        include_intern?: boolean;
      };
      skills?: string[];
    };
  };
  soft_compliances?: {
    raw_prompt?: string;
    structured?: any;
  };
}

interface IJDAnalysis {
  // New Structured Fields
  job_profile: IJobProfile;
  experience_requirements: IExperienceRequirements;
  skills: ISkills;
  tech_stack: ITechStack;
  responsibilities: string[];
  education_requirements: IEducationRequirements;
  certifications: string[];
  mandatory_compliances: string[];
  soft_compliances: string[];

  // Legacy/Meta Fields (Preserved for compatibility with scoring engine)
  keywords_flat: string[];
  keywords_weighted: Record<string, number>;
  weighting: IWeighting;
  embedding_hints?: IEmbeddingHints;
  explainability?: IExplainability;
  hr_points: number;
  hr_notes: IHRNote[];
  meta?: IMeta;
}

interface IEmbeddings {
  embedding_model?: string;
  embedding_dimension?: number;
  profile_embedding?: number[];
  skills_embedding?: number[];
  projects_embedding?: number[];
  responsibilities_embedding?: number[];
  education_embedding?: number[];
  overall_embedding?: number[];
}

export interface IJob extends Document {
  title: string;
  description: string;
  allow_overqualified?: boolean;
  status: 'draft' | 'jd_processing_started' | 'jd_processing_failed' | 'jd_processing_completed' | 'resume_processing_started' | 'resume_processing_failed' | 'resume_processing_completed' | 'ranking_started' | 'ranking_failed' | 'ranking_completed';
  locked: boolean;

  // BullMQ Job Tracking
  bullmq_jobs?: {
    jd_processing_job_id?: string;
    resume_processing_parent_job_id?: string;
    ranking_parent_job_id?: string;
  };

  // Processing totals (stored at queue time, independent of BullMQ counts)
  processing_totals?: {
    total_resumes?: number;
    total_ranking_batches?: number;
  };

  jd_pdf_filename?: string;
  jd_text?: string;

  filter_requirements?: IFilterRequirements;
  jd_analysis: IJDAnalysis;
  jd_embedding?: IEmbeddings;

  createdAt: Date;
  updatedAt: Date;
}

// ==========================================
// SCHEMA DEFINITIONS
// ==========================================

// Filter Requirements Schema - For Compliance (Root level)
const complianceFilterRequirementsSchema = new Schema({
  mandatory_compliances: {
    raw_prompt: { type: String, default: '' },
    structured: {
      experience: {
        min: { type: Number },
        max: { type: Number },
        include_intern: { type: Boolean, default: false }
      },
      skills: { type: [String], default: [] }
    }
  },
  soft_compliances: {
    raw_prompt: { type: String, default: '' },
    structured: { type: Schema.Types.Mixed, default: {} }
  }
}, { _id: false });

// Filter Requirements Schema - For JD Analysis (AI parsed, inside jd_analysis)
const jdAnalysisFilterRequirementsSchema = new Schema({
  raw_prompt: String,
  structured: {
    experience: {
      min: Number,
      max: Number,
      include_intern: { type: Boolean, default: false },
      field: String,
      specified: Boolean
    },
    hard_skills: [String],
    preferred_skills: [String],
    department: {
      category: {
        type: String,
        enum: ['IT', 'Non-IT', 'Specific']
      },
      allowed_departments: [String],
      excluded_departments: [String],
      specified: Boolean
    },
    location: String,
    education: [String],
    other_criteria: [String]
  },
  re_ranking_instructions: String
}, { _id: false });

// JD Analysis Schema
const jdAnalysisSchema = new Schema({
  // New Structured Fields
  job_profile: {
    role: String,
    domain: String,
    location: String,
    work_mode: String,
    job_type: String,
    notice_period: String
  },
  experience_requirements: {
    minimum_experience_months: Number,
    maximum_experience_months: Number
  },
  skills: {
    required: [String],
    preferred: [String],
    soft_skills: [String]
  },
  tech_stack: {
    languages: [String],
    frameworks: [String],
    libraries: [String],
    databases: [String],
    cloud: [String],
    tools: [String],
    ai_techniques: [String]
  },
  responsibilities: { type: [String], required: true },
  education_requirements: {
    degrees: [String],
    fields: [String]
  },
  certifications: [String],
  mandatory_compliances: [String],
  soft_compliances: [String],

  // Legacy/Meta Fields (Preserved for compatibility)
  keywords_flat: { type: [String], required: false, default: [] },
  keywords_weighted: { type: Schema.Types.Mixed, required: false, default: {} },
  weighting: {
    type: {
      required_skills: Number,
      preferred_skills: Number,
      responsibilities: Number,
      domain_relevance: Number,
      technical_depth: Number,
      soft_skills: Number,
      education: Number,
      certifications: Number,
      keywords_exact: Number,
      keywords_semantic: Number
    },
    required: false
  },
  embedding_hints: {
    skills_embed: String,
    responsibilities_embed: String,
    overall_embed: String,
    negatives_embed: String,
    seniority_embed: String
  },
  explainability: {
    top_jd_sentences: [String],
    key_phrases: [String],
    rationales: [String]
  },
  hr_points: { type: Number, required: false, default: 0 },
  hr_notes: {
    type: [{
      category: { type: String },
      type: { type: String, enum: ['recommendation', 'inferred_requirement'] },
      note: { type: String },
      impact: Number,
      reason: String,
      source_provenance: [String]
    }],
    required: false,
    default: []
  },
  meta: {
    jd_version: String,
    raw_text_length: Number,
    last_updated: String,
    sections_detected: [String]
  }
}, { _id: false });

// JD Embeddings Schema
const jdEmbeddingsSchema = new Schema({
  embedding_model: {
    type: String,
    default: 'text-embedding-3-small'
  },
  embedding_dimension: {
    type: Number,
    default: 1536
  },
  profile_embedding: Schema.Types.Mixed,
  skills_embedding: Schema.Types.Mixed,
  projects_embedding: Schema.Types.Mixed,
  responsibilities_embedding: Schema.Types.Mixed,
  education_embedding: Schema.Types.Mixed,
  overall_embedding: Schema.Types.Mixed
}, { _id: false });

// ==========================================
// MAIN JOB SCHEMA
// ==========================================

const jobSchema = new Schema<IJob>({
  title: {
    type: String,
    required: true,
    trim: true
  },
  description: {
    type: String,
    trim: true,
    required: false
  },
  allow_overqualified: {
    type: Boolean,
    default: false
  },
  status: {
    type: String,
    enum: [
      'draft',
      'jd_processing_started',
      'jd_processing_failed',
      'jd_processing_completed',
      'resume_processing_started',
      'resume_processing_completed',
      'ranking_started',
      'ranking_completed'
    ],
    default: 'draft'
  },
  locked: {
    type: Boolean,
    default: false
  },

  // BullMQ Job Tracking
  bullmq_jobs: {
    jd_processing_job_id: String,
    resume_processing_parent_job_id: String,
    ranking_parent_job_id: String
  },

  // Processing totals (stored at queue time, independent of BullMQ counts)
  processing_totals: {
    total_resumes: Number,
    total_ranking_batches: Number
  },

  jd_pdf_filename: String,
  jd_text: String,

  // Compliance filter requirements (Root level - mandatory/soft compliances)
  filter_requirements: complianceFilterRequirementsSchema,
  jd_analysis: jdAnalysisSchema,
  jd_embedding: jdEmbeddingsSchema
}, {
  timestamps: true
});

// Add indexes for better query performance
jobSchema.index({ status: 1 });
jobSchema.index({ jd_processing_status: 1 });
jobSchema.index({ resume_processing_status: 1 });
jobSchema.index({ createdAt: -1 });
jobSchema.index({ 'jd_analysis.job_profile.role': 1 });

export default mongoose.model<IJob>('Job', jobSchema);