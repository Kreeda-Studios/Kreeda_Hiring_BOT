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
  | "jd_processing_started"
  | "jd_processing_failed"
  | "jd_processing_completed"
  | "resume_processing_started"
  | "resume_processing_failed"
  | "resume_processing_completed"
  | "ranking_started"
  | "ranking_completed"
  // Legacy statuses
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
  job_profile: {
    role?: string;
    domain?: string;
    location?: string;
    work_mode?: string;
    job_type?: string;
    notice_period?: string;
  };
  experience_requirements: {
    minimum_experience_months: number;
    maximum_experience_months: number;
  };
  skills: {
    required: string[];
    preferred: string[];
    soft_skills: string[];
  };
  tech_stack: {
    languages: string[];
    frameworks: string[];
    libraries: string[];
    databases: string[];
    cloud: string[];
    tools: string[];
    ai_techniques: string[];
  };
  responsibilities: string[];
  education_requirements: {
    degrees: string[];
    fields: string[];
  };
  certifications: string[];
  mandatory_compliances: string[];
  soft_compliances: string[];
}

export interface CreateJobData {
  title: string;
  description?: string;
}

// ==================== RESUME TYPES ====================

export type ResumeStatus = "pending" | "processing" | "completed" | "failed" | "filtered";

export interface Resume {
  _id: string;
  title?: string;
  description?: string;
  group_id?: string | { _id: string; name: string };
  filename?: string;
  file_path?: string;
  status?: ResumeStatus;
  raw_text?: string;
  jd_compliance_text?: string;
  parsed_content?: ParsedResume;
  candidate_name?: string;
  createdAt: string;
  updatedAt?: string;
  processed_at?: string;
  error_message?: string;
  scores?: {
    hard_requirements?: {
      meets_all_requirements: boolean;
      filter_reason?: string;
    };
  };
}

export interface ParsedResume {
  profile: {
    name?: string;
    contact?: string;
    email?: string;
    linkedin?: string;
    github?: string;
    leetcode?: string;
    hackerrank?: string;
    location?: string;
  };
  domain: string;
  confidence: number;
  skills: {
    provided: string[];
    inferred: string[];
    soft_skills: string[];
  };
  experience: {
    total_full_time_experience: number;
    total_internship_experience_in_months: number;
    details: Experience[];
  };
  projects: Project[];
  educations: Education[];
  certifications: string[];
  achievements: string[];
}

export interface Education {
  start?: string;
  end?: string;
  college?: string;
  degree?: string;
  department?: string;
  grade?: string;
}

export interface Experience {
  company?: string;
  role?: string;
  start?: string;
  end?: string;
  employment_type?: string;
  impact: string[];
}

export interface Project {
  title?: string;
  demo_link?: string;
  code_link?: string;
  metric_ai: {
    impact: number;
    difficulty: number;
    complexity: number;
    domain_relevance: number;
  };
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
  email?: string;
  phone?: string;
  profile?: string;
  location?: string;
  years_experience?: number;
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
  filter_reason?: string;
  selection_reason?: string;
  skills_score?: number;
  education_score?: number;
  experience_score?: number;
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
