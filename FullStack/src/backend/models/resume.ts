/**
 * Resume Mongoose Model
 * Comprehensive schema for storing parsed resume data
 */

import mongoose, { Schema, Document, Model } from 'mongoose';

// ========== Interfaces ==========

export interface IProfile {
  name?: string;
  contact?: string;
  email?: string;
  linkedin?: string;
  github?: string;
  leetcode?: string;
  hackerrank?: string;
  location?: string;
}

export interface ISkills {
  provided: string[];
  inferred: string[];
  softSkills: string[]; // Soft skills like "Team collaboration", "Problem solving"
}

export type EmploymentType = 'Full Time' | 'Part Time' | 'Intern' | 'Contract';

export interface IExperience {
  company: string;
  role: string;
  startDate?: Date;
  endDate?: Date | string; // Allow "present" for current roles
  employmentType: EmploymentType;
  skillsUsed: string[];
  achievements: string[];
}

export interface IProjectMetrics {
  impact?: number; // 0-1 scale
  difficulty?: number; // 1-10 scale
  complexity?: number; // 1-10 scale
  domainRelevance?: number; // 1-10 scale
}

export interface IProject {
  title: string;
  domain?: string;
  skillsUsed: string[];
  demoLink?: string;
  codeLink?: string;
  description?: string;
  metrics?: IProjectMetrics;
}

export interface IEducation {
  startDate?: Date;
  endDate?: Date | string; // Allow "present" for ongoing education
  college: string;
  degree: string;
  department: string;
  grade?: string;
}

export interface ICertification {
  title: string;
  url?: string;
  skills: string[];
  issuedDate?: Date;
  expiryDate?: Date;
}

export interface IAchievements {
  hackathons: string[];
  researchPapers: string[];
  awards: string[];
  other: string[];
}

export interface IExperienceSummary {
  totalFullTime: number; // in months
  totalInternship: number; // in months
}

export interface IResume extends Document {
  // File metadata
  fileName: string; // Random prefix + original filename (e.g., "abc123_resume.pdf")
  resumeFilePath: string;
  originalFileName?: string;
  fileSize?: number;
  fileType?: string; // 'pdf' | 'docx'
  
  // Timestamps
  uploadedAt: Date;
  processedAt?: Date;
  
  // Status
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  processingError?: string;
  
  // Resume content
  profile: IProfile;
  domain?: string; // User-provided or AI-inferred
  domainConfidence?: number; // 0-1 scale, AI confidence in domain classification
  skills: ISkills;
  experienceSummary: IExperienceSummary;
  experience: IExperience[];
  projects: IProject[];
  education: IEducation[];
  certifications: ICertification[];
  achievements: IAchievements;

}

// ========== Mongoose Schemas ==========

const ProfileSchema = new Schema<IProfile>({
  name: String,
  contact: String,
  email: String,
  linkedin: String,
  github: String,
  leetcode: String,
  hackerrank: String,
  location: String,
}, { _id: false });

const SkillsSchema = new Schema<ISkills>({
  provided: [String],
  inferred: [String],
  softSkills: [String],
}, { _id: false });

const ExperienceSchema = new Schema<IExperience>({
  company: { type: String, required: true },
  role: { type: String, required: true },
  startDate: Date,
  endDate: { type: Schema.Types.Mixed }, // Allow Date or "present" string
  employmentType: {
    type: String,
    enum: ['Full Time', 'Part Time', 'Intern', 'Contract'],
    required: true,
  },
  skillsUsed: [String],
  achievements: [String],
}, { _id: false });

const ProjectMetricsSchema = new Schema<IProjectMetrics>({
  impact: { type: Number, min: 0, max: 1 },
  difficulty: { type: Number, min: 1, max: 10 },
  complexity: { type: Number, min: 1, max: 10 },
  domainRelevance: { type: Number, min: 1, max: 10 },
}, { _id: false });

const ProjectSchema = new Schema<IProject>({
  title: { type: String, required: true },
  domain: String,
  skillsUsed: [String],
  demoLink: String,
  codeLink: String,
  description: String,
  metrics: ProjectMetricsSchema,
}, { _id: false });

const EducationSchema = new Schema<IEducation>({
  startDate: Date,
  endDate: { type: Schema.Types.Mixed }, // Allow Date or "present" string
  college: { type: String, required: true },
  degree: { type: String, required: true },
  department: { type: String, required: true },
  grade: String,
}, { _id: false });

const CertificationSchema = new Schema<ICertification>({
  title: { type: String, required: true },
  url: String,
  skills: [String],
  issuedDate: Date,
  expiryDate: Date,
}, { _id: false });

const AchievementsSchema = new Schema<IAchievements>({
  hackathons: [String],
  researchPapers: [String],
  awards: [String],
  other: [String],
}, { _id: false });

const ExperienceSummarySchema = new Schema<IExperienceSummary>({
  totalFullTime: { type: Number, default: 0 },
  totalInternship: { type: Number, default: 0 },
}, { _id: false });

// ========== Main Resume Schema ==========

const ResumeSchema = new Schema<IResume>(
  {
    // File metadata
    fileName: { type: String, required: true, unique: true },
    resumeFilePath: { type: String, required: true },
    originalFileName: String,
    fileSize: Number,
    fileType: { type: String, enum: ['pdf', 'docx'] },
    
    // Timestamps
    uploadedAt: { type: Date, default: Date.now },
    processedAt: Date,
    
    // Status
    status: {
      type: String,
      enum: ['uploaded', 'processing', 'completed', 'failed'],
      default: 'uploaded',
    },
    processingError: String,
    
    // Resume content
    profile: { type: ProfileSchema, default: {} },
    domain: String,
    domainConfidence: { type: Number, min: 0, max: 1 },
    skills: { type: SkillsSchema, default: { provided: [], inferred: [], softSkills: [] } },
    experienceSummary: {
      type: ExperienceSummarySchema,
      default: { totalFullTime: 0, totalInternship: 0 },
    },
    experience: { type: [ExperienceSchema], default: [] },
    projects: { type: [ProjectSchema], default: [] },
    education: { type: [EducationSchema], default: [] },
    certifications: { type: [CertificationSchema], default: [] },
    achievements: {
      type: AchievementsSchema,
      default: { hackathons: [], researchPapers: [], awards: [], other: [] },
    }
  },
  {
    timestamps: true, // Adds createdAt and updatedAt automatically
  }
);

// ========== Indexes ==========

ResumeSchema.index({ status: 1, uploadedAt: -1 });
ResumeSchema.index({ jobId: 1 });
ResumeSchema.index({ 'profile.email': 1 });

// ========== Model ==========

const Resume: Model<IResume> = mongoose.models.Resume || mongoose.model<IResume>('Resume', ResumeSchema);

export { Resume };
export default Resume;
