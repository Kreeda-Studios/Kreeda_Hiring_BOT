import mongoose, { Document, Schema } from 'mongoose';

/**
 * Resume Model - Stores parsed resume data and scores
 * 
 * Core fields:
 * - resume_id (auto-generated _id)
 * - job_id (reference to Job)
 * - filename, original_name (file info)
 * - raw_text (extracted text from PDF)
 * - status fields (extraction_status, parsing_status, embedding_status)
 * - parsed_content (structured resume data from AI parser)
 * - resume_embedding (6-section embeddings for semantic scoring)
 * - scores (keyword, semantic, project, composite scores)
 * - timestamps
 */

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

export interface IResume extends Document {

  // File information
  filename: string;
  original_name: string;
  job_id: mongoose.Types.ObjectId;
  
  // Extracted text
  raw_text?: string;
  
  // Processing status
  extraction_status: 'pending' | 'success' | 'failed';
  parsing_status: 'pending' | 'success' | 'failed';
  embedding_status: 'pending' | 'success' | 'failed';
  
  // AI Parser output - structured according to b_ai_parser.py PARSE_FUNCTION
  parsed_content?: IParsedContent;
  
  // Resume embeddings for semantic scoring (6 sections from d_embedding_generator.py)
  // Each section contains array of sentence embeddings (2D: [[emb1], [emb2], ...])
  resume_embedding?: {
    model?: string;
    dimension?: number;
    profile?: number[][];
    skills?: number[][];
    projects?: number[][];
    responsibilities?: number[][];
    education?: number[][];
    overall?: number[][];
  };
  
  // Scoring results
  scores?: {
    hard_requirements?: {
      meets_all_requirements?: boolean;
      compliance_score?: number;
      requirements_met?: string[];
      requirements_missing?: string[];
      filter_reason?: string;
    };
    project_score?: number;
    keyword_score?: number;
    semantic_score?: number;
    composite_score?: number;
    scoring_status?: 'pending' | 'success' | 'failed';
    scored_at?: Date;
  };
  
  // Timestamps
  createdAt: Date;
  updatedAt: Date;
}

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
  
  // Extracted text from PDF
  raw_text: {
    type: String
  },
  
  // Processing status fields
  extraction_status: {
    type: String,
    enum: ['pending', 'success', 'failed'],
    default: 'pending',
    index: true
  },
  parsing_status: {
    type: String,
    enum: ['pending', 'success', 'failed'],
    default: 'pending',
    index: true
  },
  embedding_status: {
    type: String,
    enum: ['pending', 'success', 'failed'],
    default: 'pending',
    index: true
  },
  
  parsed_content: {
    candidate_id: {
      type: String
    },
    name: {
      type: String
    },
    role_claim: String,
    years_experience: Number,
    location: String,
    contact: {
      email: {
        type: String
      },
      phone: String,
      profile: String
    },
    domain_tags: [String],
    profile_keywords_line: {
      type: String
    },
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
    ats_boost_line: {
      type: String
    },
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
  },
  
  // Resume embeddings (6 sections for semantic scoring)
  // Each section is 2D array: [[emb1], [emb2], ...] for multiple sentences
  resume_embedding: {
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
  },
  
  // Scoring results
  scores: {
    hard_requirements: {
      meets_all_requirements: Boolean,
      compliance_score: Number,
      requirements_met: [String],
      requirements_missing: [String],
      filter_reason: String
    },
    project_score: Number,
    keyword_score: Number,
    semantic_score: Number,
    composite_score: Number,
    scoring_status: {
      type: String,
      enum: ['pending', 'success', 'failed'],
      default: 'pending'
    },
    scored_at: Date
  }
}, {
  timestamps: true
});

// Indexes for efficient queries
resumeSchema.index({ job_id: 1, parsing_status: 1 });
resumeSchema.index({ job_id: 1, 'scores.scoring_status': 1 });
resumeSchema.index({ 'parsed_content.name': 1 });
resumeSchema.index({ 'parsed_content.contact_info.email': 1 });

// Virtual for candidate name (extracted from parsed_content)
resumeSchema.virtual('candidate_name').get(function() {
  return this.parsed_content?.name || this.original_name || 'Unknown';
});

// Virtual for candidate email
resumeSchema.virtual('candidate_email').get(function() {
  return this.parsed_content?.contact?.email || '';
});

// Ensure virtuals are included in JSON output
resumeSchema.set('toJSON', { virtuals: true });
resumeSchema.set('toObject', { virtuals: true });

export default mongoose.model<IResume>('Resume', resumeSchema);