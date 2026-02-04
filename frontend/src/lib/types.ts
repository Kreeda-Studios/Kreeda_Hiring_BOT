// ==================== SCORE TYPES ====================

export interface ScoreResult {
  _id: string;
  job_id: string;
  resume_id: string | Resume;
  keyword_score: number;
  semantic_score: number;
  project_score: number;
  final_score: number;
  hard_requirements_met: boolean;
  score_breakdown?: {
    keyword?: Record<string, any>;
    semantic?: Record<string, any>;
    project?: Record<string, any>;
  };
  created_at: string;
  updated_at: string;
}

// ==================== JOB TYPES ====================

export type JobStatus = 
  | "draft"
  | "active" 
  | "completed" 
  | "archived";

export interface HRRequirements {
  must_have?: string[];
  nice_to_have?: string[];
  education?: string;
  experience_years?: number;
}

export interface Job {
  _id: string;
  title: string;
  description?: string;
  status: JobStatus;
  locked: boolean;
  jd_text?: string;
  jd_pdf_filename?: string;
  jd_file_path?: string;
  jd_content?: string;
  jd_structured?: JDStructured;
  jd_analysis?: Record<string, any>;
  hr_requirements?: HRRequirements;
  filter_requirements?: {
    mandatory_compliances?: {
      raw_prompt: string;
      structured?: Record<string, any>;
    };
    soft_compliances?: {
      raw_prompt: string;
      structured?: Record<string, any>;
    };
  };
  hard_requirements?: string;
  soft_requirements?: string;
  resume_groups?: string[];
  total_resumes?: number;
  processed_resumes?: number;
  created_at: string;
  updated_at: string;
}

export interface JDStructured {
  role_title?: string;
  seniority_level?: string;
  required_skills?: string[];
  preferred_skills?: string[];
  experience?: {
    min?: number;
    max?: number;
  };
  education?: string;
  domain_tags?: string[];
}

export interface CreateJobData {
  title: string;
  description?: string;
}

// ==================== RESUME TYPES ====================

export type ResumeStatus = "pending" | "processing" | "complete" | "failed";

export interface Resume {
  _id: string;
  title?: string;
  description?: string;
  group_id?: string | { _id: string; name: string };
  filename?: string;
  file_path?: string;
  status?: ResumeStatus;
  extraction_status?: ResumeStatus;
  parsing_status?: ResumeStatus;
  embedding_status?: ResumeStatus;
  raw_text?: string;
  jd_compliance_text?: string;
  parsed_content?: ParsedResume;
  candidate_name?: string;
  createdAt: string;
  updatedAt?: string;
  processed_at?: string;
  error_message?: string;
}

export interface ParsedResume {
  name?: string;
  email?: string;
  phone?: string;
  location?: string;
  years_experience?: number;
  skills?: string[];
  education?: Education[];
  experience?: Experience[];
  projects?: Project[];
}

export interface Education {
  degree?: string;
  field?: string;
  institution?: string;
  year?: string;
}

export interface Experience {
  title?: string;
  company?: string;
  duration?: string;
  description?: string;
}

export interface Project {
  name?: string;
  description?: string;
  tech_keywords?: string[];
}

// ==================== RESUME GROUP TYPES ====================

export type ResumeGroupSource = "upload" | "email" | "api";

export interface ResumeGroup {
  _id: string;
  name: string;
  source: ResumeGroupSource;
  source_details?: Record<string, unknown>;
  resume_count: number;
  processed_count?: number;
  total_resumes?: number;
  created_at: string;
}

// ==================== RANKING TYPES ====================

export interface RankedCandidate {
  resume_id: string;
  rank: number;
  candidate_name: string;
  name?: string;
  final_score: number;
  keyword_score: number;
  semantic_score: number;
  project_score: number;
  compliance_score: number;
  is_compliant: boolean;
  group_name?: string;
  re_rank_score?: number;
  score_breakdown?: {
    project: number;
    keyword: number;
    semantic: number;
  };
  compliance_status?: {
    hard_compliance: boolean;
    soft_compliance_score: number;
    requirements_met: string[];
    requirements_missing: string[];
  };
  llm_validated?: boolean;
}

export interface JobRanking {
  _id: string;
  job_id: string;
  ranked_candidates: RankedCandidate[];
  total_candidates: number;
  compliant_candidates: number;
  created_at: string;
  updated_at: string;
}

// ==================== PROGRESS TYPES ====================

export type ProcessingStage = "jd_processing" | "resume_processing" | "ranking";

export interface ProcessingProgress {
  job_id: string;
  stage: ProcessingStage;
  status: "pending" | "processing" | "complete" | "failed";
  progress: number;
  total: number;
  current: number;
  started_at?: string;
  completed_at?: string;
  error_message?: string;
}

export interface JobProgress {
  jd: ProcessingProgress;
  resumes: ProcessingProgress;
  ranking: ProcessingProgress;
}

// ==================== API RESPONSE TYPES ====================

export interface ApiResponse<T> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

export interface PaginatedResponse<T> {
  data: T[];
  total: number;
  page: number;
  limit: number;
  has_more: boolean;
}

// ==================== WEBSOCKET EVENT TYPES ====================

export type WSEventType = 
  | "jd_progress"
  | "resume_progress"
  | "ranking_progress"
  | "job_complete"
  | "error";

export interface WSEvent {
  type: WSEventType;
  job_id: string;
  data: ProcessingProgress | RankedCandidate[] | { error: string };
  timestamp: string;
}
