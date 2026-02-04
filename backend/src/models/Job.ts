import mongoose, { Document, Schema } from 'mongoose';

interface IComplianceRequirement {
  raw_prompt?: string;
  structured?: {
    experience?: {
      min?: number;
      max?: number;
      field?: string;
      specified?: boolean;
      type?: string;
      unit?: string;
    };
    hard_skills?: string[];
    preferred_skills?: string[];
    department?: {
      category?: 'IT' | 'Non-IT' | 'Specific';
      allowed_departments?: string[];
      excluded_departments?: string[];
      specified?: boolean;
    };
    location?: {
      type?: string;
      specified?: boolean;
      required?: string;
      allowed?: string[];
    } | string | null;
    education?: {
      type?: string;
      specified?: boolean;
      minimum?: string;
      required?: string;
    } | string[];
    other_criteria?: string[];
    [key: string]: any;  // Allow dynamic fields
  };
}

interface IFilterRequirements {
  mandatory_compliances?: IComplianceRequirement;
  soft_compliances?: IComplianceRequirement;
}

interface IHRNote {
  category: string;
  type: 'recommendation' | 'inferred_requirement';
  note: string;
  impact?: number;
  reason?: string;
  source_provenance?: string[];
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

interface IJDAnalysis {
  // Analysis metadata
  meta?: {
    jd_version?: string;
    raw_text_length?: number;
    sections_detected?: string[];
  };
  
  // HR insights
  hr_points?: number;
  hr_notes?: IHRNote[];
  explainability?: IExplainability;
  provenance_spans?: IProvenanceSpan[];
  
  // Compliance parsing results
  mandatory_compliances?: IComplianceRequirement;
  soft_compliances?: IComplianceRequirement;
  
  // Core role context
  role_title?: string;
  alt_titles?: string[];
  seniority_level?: string;
  department?: string;
  industry?: string;
  domain_tags?: string[];
  
  // Work model & logistics
  location?: string;
  work_model?: string;
  employment_type?: string;
  contract?: {
    duration_months?: number;
    extendable?: boolean;
  };
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
  preferred_skills: string[];
  tools_tech: string[];
  soft_skills: string[];
  languages?: string[];
  canonical_skills: Record<string, any>;
  skill_requirements?: Array<{
    skill: string;
    category?: string;
    priority?: string;
    level?: string;
    years_min?: number;
    versions?: string[];
    related_tools?: string[];
    mandatory?: boolean;
    provenance?: string[];
  }>;
  
  // Duties & outcomes
  responsibilities: string[];
  deliverables?: string[];
  kpis_okrs?: string[];
  
  // Team & reporting
  team_context?: {
    team_size?: number;
    reports_to?: string;
    manages_team?: boolean;
    direct_reports?: number;
  };
  
  // Constraints / exclusions / compliance
  exclusions?: string[];
  compliance?: string[];
  screening_questions?: string[];
  
  // Interview process
  interview_process?: {
    total_rounds?: number;
    stages?: Array<{
      name?: string;
      purpose?: string;
      skills_evaluated?: string[];
    }>;
    assignment_expected?: boolean;
  };
  
  // Compensation & benefits
  compensation?: {
    currency?: string;
    salary_min?: number;
    salary_max?: number;
    period?: string;
    bonus?: string;
    equity?: string;
  };
  benefits?: string[];
  
  // Keywords for ATS scoring
  keywords_flat: string[];
  keywords_weighted: Record<string, number>;
  
  // Weighting hints
  weighting: Record<string, any>;
  embedding_hints: Record<string, any>;
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
  company_name?: string;
  status: 'draft' | 'active' | 'completed' | 'archived';
  locked: boolean;
  resume_groups: mongoose.Types.ObjectId[];
  jd_file_path?: string;
  jd_pdf_filename?: string;
  jd_text?: string;
  filter_requirements?: IFilterRequirements;
  jd_analysis: IJDAnalysis;
  embeddings?: IEmbeddings;
  explainability?: IExplainability;
  provenance_spans?: IProvenanceSpan[];
  createdAt: Date;
  updatedAt: Date;
}

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
  company_name: {
    type: String,
    trim: true
  },
  status: {
    type: String,
    enum: ['draft', 'active', 'completed', 'archived'],
    default: 'draft'
  },
  locked: {
    type: Boolean,
    default: false
  },
  resume_groups: [{
    type: Schema.Types.ObjectId,
    ref: 'ResumeGroup'
  }],
  jd_file_path: {
    type: String
  },
  jd_pdf_filename: {
    type: String
  },
  jd_text: {
    type: String
  },
  filter_requirements: {
    mandatory_compliances: {
      raw_prompt: String,
      structured: Schema.Types.Mixed
    },
    soft_compliances: {
      raw_prompt: String,
      structured: Schema.Types.Mixed
    }
  },
  jd_analysis: {
    // Analysis metadata
    meta: {
      jd_version: {
        type: String,
        default: "1.0"
      },
      raw_text_length: Number,
      sections_detected: [String]
    },
    
    // HR insights
    hr_points: {
      type: Number,
      default: 0
    },
    hr_notes: [{
      category: {
        type: String,
        required: true
      },
      type: {
        type: String,
        enum: ['recommendation', 'inferred_requirement'],
        required: true
      },
      note: {
        type: String,
        required: true
      },
      impact: Number,
      reason: String,
      source_provenance: [String]
    }],
    explainability: {
      top_jd_sentences: [String],
      key_phrases: [String],
      rationales: [String]
    },
    provenance_spans: [{
      type: {
        type: String,
        required: true
      },
      text: {
        type: String,
        required: true
      }
    }],
    
    // Compliance parsing results
    mandatory_compliances: {
      raw_prompt: String,
      structured: Schema.Types.Mixed
    },
    soft_compliances: {
      raw_prompt: String,
      structured: Schema.Types.Mixed
    },
    // Core role context
    role_title: String,
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
    required_skills: [String],
    preferred_skills: [String],
    tools_tech: [String],
    soft_skills: [String],
    languages: [String],
    canonical_skills: {
      type: Schema.Types.Mixed,
      default: {}
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
    responsibilities: [String],
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
    keywords_flat: [String],
    keywords_weighted: {
      type: Schema.Types.Mixed,
      default: {}
    },
    
    // Weighting hints
    weighting: {
      type: Schema.Types.Mixed,
      default: {}
    },
    embedding_hints: {
      type: Schema.Types.Mixed,
      default: {}
    }
  },
  embeddings: {
    embedding_model: {
      type: String,
      default: 'text-embedding-3-small'
    },
    embedding_dimension: {
      type: Number,
      default: 1536
    },
    profile_embedding: [Number],
    skills_embedding: [Number],
    projects_embedding: [Number],
    responsibilities_embedding: [Number],
    education_embedding: [Number],
    overall_embedding: [Number]
  }
}, {
  timestamps: true
});

export default mongoose.model<IJob>('Job', jobSchema);