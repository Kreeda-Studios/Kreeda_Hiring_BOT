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

interface ICanonicalSkills {
  programming?: string[];
  frameworks?: string[];
  libraries?: string[];
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
  raw_prompt?: string;
  structured?: {
    experience?: {
      min?: number;
      max?: number;
      field?: string;
      specified?: boolean;
    };
    hard_skills?: string[];
    preferred_skills?: string[];
    department?: {
      category?: 'IT' | 'Non-IT' | 'Specific';
      allowed_departments?: string[];
      excluded_departments?: string[];
      specified?: boolean;
    };
    location?: string;
    education?: string[];
    other_criteria?: string[];
  };
  re_ranking_instructions?: string;
}

interface IJDAnalysis {
  // Core role context
  role_title: string;
  alt_titles?: string[];
  seniority_level?: string;
  department?: string;
  industry?: string;
  domain_tags?: string[];

  // Work model & logistics
  location?: string;
  work_model?: string;
  employment_type?: string;
  contract?: IContract;
  start_date_preference?: string;
  travel_requirement_percent?: number;
  work_hours?: string;
  shift_details?: string;
  visa_sponsorship?: boolean;
  clearances_required?: string[];

  // Experience & education
  years_experience_required?: number;
  education_requirements?: string[];
  min_degree_level?: string;
  fields_of_study?: string[];
  certifications_required?: string[];
  certifications_preferred?: string[];

  // Skills
  required_skills: string[];
  preferred_skills?: string[];
  tools_tech?: string[];
  soft_skills?: string[];
  languages?: string[];
  canonical_skills?: ICanonicalSkills;
  skill_requirements?: ISkillRequirement[];

  // Duties & outcomes
  responsibilities: string[];
  deliverables?: string[];
  kpis_okrs?: string[];

  // Team & reporting
  team_context?: ITeamContext;

  // Constraints / exclusions / compliance
  exclusions?: string[];
  compliance?: string[];
  screening_questions?: string[];

  // Interview process
  interview_process?: IInterviewProcess;

  // Compensation & benefits
  compensation?: ICompensation;
  benefits?: string[];

  // Keywords for ATS scoring
  keywords_flat: string[];
  keywords_weighted: Record<string, number>;

  // Weighting hints
  weighting: IWeighting;
  embedding_hints?: IEmbeddingHints;

  // Explainability
  explainability?: IExplainability;
  provenance_spans?: IProvenanceSpan[];

  // HR insights
  hr_points: number;
  hr_notes: IHRNote[];

  // Filter requirements
  filter_requirements?: IFilterRequirements;

  // Meta
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
    structured: { type: Schema.Types.Mixed, default: {} }
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
  // Core role context
  role_title: { type: String, required: true },
  alt_titles: [String],
  seniority_level: String,
  department: String,
  industry: String,
  domain_tags: [String],

  // Work model & logistics
  location: String,
  work_model: String,
  employment_type: String,
  contract: {
    duration_months: Number,
    extendable: Boolean
  },
  start_date_preference: String,
  travel_requirement_percent: Number,
  work_hours: String,
  shift_details: String,
  visa_sponsorship: Boolean,
  clearances_required: [String],

  // Experience & education
  years_experience_required: Number,
  education_requirements: [String],
  min_degree_level: String,
  fields_of_study: [String],
  certifications_required: [String],
  certifications_preferred: [String],

  // Skills
  required_skills: { type: [String], required: true },
  preferred_skills: [String],
  tools_tech: [String],
  soft_skills: [String],
  languages: [String],
  canonical_skills: {
    programming: [String],
    frameworks: [String],
    libraries: [String],
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
  skill_requirements: [{
    skill: String,
    category: String,
    priority: String,
    level: String,
    years_min: Number,
    versions: [String],
    related_tools: [String],
    mandatory: Boolean,
    provenance: [String]
  }],

  // Duties & outcomes
  responsibilities: { type: [String], required: true },
  deliverables: [String],
  kpis_okrs: [String],

  // Team & reporting
  team_context: {
    team_size: Number,
    reports_to: String,
    manages_team: Boolean,
    direct_reports: Number
  },

  // Constraints / exclusions / compliance
  exclusions: [String],
  compliance: [String],
  screening_questions: [String],

  // Interview process
  interview_process: {
    total_rounds: Number,
    stages: [{
      name: String,
      purpose: String,
      skills_evaluated: [String]
    }],
    assignment_expected: Boolean
  },

  // Compensation & benefits
  compensation: {
    currency: String,
    salary_min: Number,
    salary_max: Number,
    period: String,
    bonus: String,
    equity: String
  },
  benefits: [String],

  // Keywords for ATS scoring
  keywords_flat: { type: [String], required: false, default: [] },
  keywords_weighted: { type: Schema.Types.Mixed, required: false, default: {} },

  // Weighting hints
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
    required: true
  },
  embedding_hints: {
    skills_embed: String,
    responsibilities_embed: String,
    overall_embed: String,
    negatives_embed: String,
    seniority_embed: String
  },

  // Explainability
  explainability: {
    top_jd_sentences: [String],
    key_phrases: [String],
    rationales: [String]
  },
  provenance_spans: [{
    type: { type: String },
    text: String
  }],

  // HR insights
  hr_points: { type: Number, required: true },
  hr_notes: {
    type: [{
      category: { type: String },
      type: { type: String, enum: ['recommendation', 'inferred_requirement'] },
      note: { type: String },
      impact: Number,
      reason: String,
      source_provenance: [String]
    }],
    required: true
  },

  // Filter requirements (embedded) - AI parsed structure
  filter_requirements: jdAnalysisFilterRequirementsSchema,

  // Meta
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
jobSchema.index({ 'jd_analysis.role_title': 1 });
jobSchema.index({ 'jd_analysis.department': 1 });

export default mongoose.model<IJob>('Job', jobSchema);