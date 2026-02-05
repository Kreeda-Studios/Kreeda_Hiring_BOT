# Backend Documentation - Kreeda Hiring Bot

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Core Components](#core-components)
- [API Routes](#api-routes)
- [Database Models](#database-models)
- [Queue Management](#queue-management)
- [Real-Time Updates](#real-time-updates)
- [Configuration](#configuration)
- [Error Handling](#error-handling)
- [Testing](#testing)
- [Deployment](#deployment)

---

## 🎯 Overview

The backend is a **Node.js/Express/TypeScript** application that serves as the orchestration layer for the Kreeda Hiring Bot. It handles:
- REST API for job and resume management
- BullMQ queue management for asynchronous processing
- MongoDB database operations via Mongoose
- Real-time progress updates via Server-Sent Events (SSE)
- File uploads and storage management

### Key Technologies
- **Runtime**: Node.js 18+
- **Framework**: Express 4.18
- **Language**: TypeScript 5.1
- **Database**: MongoDB 7.0 (Mongoose ODM)
- **Queue**: BullMQ 5.67 (Redis-backed)
- **Real-Time**: Socket.IO 4.8 + SSE
- **Security**: Helmet, CORS, Rate Limiting

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Express Application                      │
├─────────────────────────────────────────────────────────────┤
│  Middleware Layer                                            │
│  ├─ Helmet (Security headers)                               │
│  ├─ CORS (Cross-origin)                                     │
│  ├─ Rate Limiter (DDoS protection)                          │
│  ├─ Morgan (Logging)                                        │
│  ├─ Compression (gzip)                                      │
│  └─ Body Parser (JSON/URL-encoded)                         │
├─────────────────────────────────────────────────────────────┤
│  Route Layer                                                 │
│  ├─ /api/jobs          (Job CRUD operations)               │
│  ├─ /api/resumes       (Resume upload & management)        │
│  ├─ /api/resume-groups (Grouping resumes by job)           │
│  ├─ /api/process       (Trigger processing jobs)           │
│  ├─ /api/scores        (Score retrieval & updates)         │
│  ├─ /api/status        (Processing status checks)          │
│  ├─ /api/sse           (Server-Sent Events streams)        │
│  └─ /api/updates       (Poll-based updates)                │
├─────────────────────────────────────────────────────────────┤
│  Service Layer                                               │
│  ├─ QueueService       (BullMQ job management)             │
│  ├─ ScoreService       (Score calculation & aggregation)   │
│  ├─ FileService        (Upload handling)                   │
│  └─ SSEManager         (Event stream management)           │
├─────────────────────────────────────────────────────────────┤
│  Data Access Layer                                           │
│  ├─ JobModel           (Mongoose schema for jobs)          │
│  ├─ ResumeModel        (Mongoose schema for resumes)       │
│  ├─ ResumeGroupModel   (Grouping resumes)                  │
│  └─ ScoreResultModel   (Scoring results)                   │
└─────────────────────────────────────────────────────────────┘
         │                          │                    │
         ▼                          ▼                    ▼
    MongoDB                     Redis                 Filesystem
  (Persistent DB)          (Queue Backend)          (uploads/)
```

---

## 📁 Directory Structure

```
backend/
├── src/
│   ├── server.ts              # Application entry point
│   ├── app.ts                 # Express app configuration
│   │
│   ├── config/                # Configuration modules
│   │   ├── index.ts          # Central config export
│   │   ├── database.ts       # MongoDB connection (singleton)
│   │   └── queue.ts          # BullMQ setup (Redis connection)
│   │
│   ├── models/                # Mongoose Models (Database Schemas)
│   │   ├── index.ts          # Model exports
│   │   ├── Job.ts            # Job model (JD + analysis)
│   │   ├── Resume.ts         # Resume model (parsed content)
│   │   ├── ResumeGroup.ts    # Resume grouping by job
│   │   └── ScoreResult.ts    # Scoring results
│   │
│   ├── routes/                # API Route Handlers
│   │   ├── jobs.ts           # Job CRUD endpoints
│   │   ├── resumes.ts        # Resume upload/management
│   │   ├── resumeGroups.ts   # Resume group operations
│   │   ├── process.ts        # Processing triggers
│   │   ├── scores.ts         # Score retrieval
│   │   ├── status.ts         # Status checks
│   │   ├── sse.ts            # Server-Sent Events
│   │   └── updates.ts        # Poll-based updates
│   │
│   ├── services/              # Business Logic Layer
│   │   ├── queueService.ts   # BullMQ job enqueuing
│   │   ├── scoreService.ts   # Score aggregation
│   │   └── sseManager.ts     # SSE connection management
│   │
│   ├── middleware/            # Custom Middleware
│   │   ├── errorHandler.ts   # Global error handling
│   │   ├── validateRequest.ts # Input validation
│   │   └── uploadHandler.ts   # Multer file upload config
│   │
│   ├── types/                 # TypeScript Type Definitions
│   │   ├── express.d.ts      # Express augmentations
│   │   └── queue.types.ts    # BullMQ job data types
│   │
│   └── utils/                 # Utility Functions
│       ├── logger.ts         # Winston logger
│       ├── validators.ts     # Input validators
│       └── helpers.ts        # Common helpers
│
├── public/                    # Static assets
├── Dockerfile                 # Production container
├── Dockerfile.dev             # Development container (hot reload)
├── package.json               # Dependencies & scripts
├── tsconfig.json              # TypeScript configuration
└── .env                       # Environment variables (not in git)
```

---

## 🔧 Core Components

### 1. Application Entry Point ([src/server.ts](backend/src/server.ts))

```typescript
import App from './app';

const startServer = async () => {
  const app = new App();
  
  // Graceful shutdown handlers
  process.on('SIGTERM', () => gracefulShutdown(app, 'SIGTERM'));
  process.on('SIGINT', () => gracefulShutdown(app, 'SIGINT'));
  
  await app.start();
};

startServer();
```

**Key Responsibilities:**
- Initialize `App` class
- Register shutdown handlers (SIGTERM, SIGINT)
- Handle uncaught exceptions
- Graceful shutdown on termination

---

### 2. Express App ([src/app.ts](backend/src/app.ts))

```typescript
class App {
  public app: Express;
  public server: HttpServer;
  private database: Database;

  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.database = Database.getInstance();
    this.initializeMiddleware();
    this.initializeRoutes();
    this.initializeErrorHandling();
  }

  async start() {
    await this.database.connect();
    this.server.listen(config.port, () => {
      console.log(`🚀 Server running on port ${config.port}`);
    });
  }

  async stop() {
    await this.database.disconnect();
    this.server.close();
  }
}
```

**Lifecycle:**
1. Constructor: Setup middleware & routes
2. `start()`: Connect DB → Start HTTP server
3. `stop()`: Disconnect DB → Close HTTP server

---

### 3. Database Connection ([src/config/database.ts](backend/src/config/database.ts))

**Singleton Pattern:**
```typescript
class Database {
  private static instance: Database;
  private connection: typeof mongoose | null = null;

  static getInstance(): Database {
    if (!Database.instance) {
      Database.instance = new Database();
    }
    return Database.instance;
  }

  async connect(): Promise<void> {
    const uri = process.env.MONGODB_URI || 'mongodb://localhost:27017/kreeda';
    
    await mongoose.connect(uri, {
      maxPoolSize: 10,
      serverSelectionTimeoutMS: 5000,
      socketTimeoutMS: 45000,
    });
    
    this.connection = mongoose;
    console.log('✅ MongoDB connected');
  }

  async disconnect(): Promise<void> {
    await mongoose.disconnect();
    console.log('🔌 MongoDB disconnected');
  }

  getConnectionStatus(): boolean {
    return mongoose.connection.readyState === 1;
  }
}
```

**Features:**
- Singleton pattern (one connection pool)
- Auto-reconnect on failure
- Connection pooling (10 connections)
- Graceful disconnect on shutdown

---

### 4. Queue Management ([src/config/queue.ts](backend/src/config/queue.ts))

**BullMQ Setup:**
```typescript
import { Queue, QueueOptions } from 'bullmq';
import IORedis from 'ioredis';

// Redis connection
const connection = new IORedis({
  host: process.env.REDIS_HOST || 'localhost',
  port: parseInt(process.env.REDIS_PORT || '6379'),
  password: process.env.REDIS_PASSWORD,
  maxRetriesPerRequest: null,
});

// Queue instances
export const jdProcessingQueue = new Queue('jd-processing', { connection });
export const resumeProcessingQueue = new Queue('resume-processing', { connection });
export const finalRankingQueue = new Queue('final-ranking', { connection });

// Health check
export async function checkQueueHealth(): Promise<boolean> {
  try {
    await connection.ping();
    return true;
  } catch {
    return false;
  }
}
```

**Queue Types:**
1. **jd-processing**: Job description processing
2. **resume-processing**: Individual resume processing
3. **final-ranking**: Final candidate re-ranking

**Job Data Structure:**
```typescript
// JD Processing Job
{
  jobId: string;
}

// Resume Processing Job
{
  resumeId: string;
  jobId: string;
}

// Final Ranking Job
{
  jobId: string;
}
```

---

## 🛣️ API Routes

### Jobs API ([src/routes/jobs.ts](backend/src/routes/jobs.ts))

#### `GET /api/jobs`
Fetch all jobs (with pagination & filtering)

**Query Params:**
- `page` (default: 1)
- `limit` (default: 20)
- `status` (filter: pending, processing, completed, failed)
- `search` (search by title)

**Response:**
```json
{
  "success": true,
  "jobs": [
    {
      "_id": "69845ac02b5a0fb4253385c7",
      "title": "Senior Full Stack Engineer",
      "status": "completed",
      "created_at": "2026-02-01T10:30:00.000Z",
      "jd_analysis": { ... },
      "total_resumes": 45,
      "processed_resumes": 45
    }
  ],
  "pagination": {
    "page": 1,
    "limit": 20,
    "total": 10,
    "totalPages": 1
  }
}
```

---

#### `GET /api/jobs/:id`
Get single job details + full JD analysis

**Response:**
```json
{
  "success": true,
  "job": {
    "_id": "69845ac02b5a0fb4253385c7",
    "title": "Senior Full Stack Engineer",
    "description": "We are looking for...",
    "status": "completed",
    "jd_analysis": {
      "role_title": "Senior Full Stack Engineer",
      "required_skills": ["React", "Node.js", "TypeScript"],
      "years_experience_required": 5,
      "weighting": {
        "required_skills": 0.40,
        "responsibilities": 0.25
      },
      "hr_points": 3,
      "hr_notes": [...]
    },
    "jd_embedding": {
      "model": "text-embedding-3-small",
      "dimension": 1536,
      "skills_embed": "...",
      "responsibilities_embed": "..."
    },
    "filter_requirements": {
      "mandatory_compliances": { ... },
      "soft_compliances": { ... }
    },
    "created_at": "2026-02-01T10:30:00.000Z",
    "updated_at": "2026-02-01T10:35:00.000Z"
  }
}
```

---

#### `POST /api/jobs`
Create new job (JD upload or text input)

**Request Body (multipart/form-data or JSON):**
```json
{
  "title": "Senior Full Stack Engineer",
  "description": "Optional description text",
  "jd_text": "Paste JD text here...",
  "jd_file": "<file upload>",
  "filter_requirements": {
    "mandatory_compliances": {
      "raw_prompt": "Must have 5+ years React experience"
    }
  }
}
```

**Response:**
```json
{
  "success": true,
  "job": {
    "_id": "69845ac02b5a0fb4253385c7",
    "title": "Senior Full Stack Engineer",
    "status": "pending",
    "created_at": "2026-02-01T10:30:00.000Z"
  }
}
```

---

#### `PATCH /api/jobs/:id`
Update job (used by Python processor to save analysis)

**Request Body:**
```json
{
  "status": "processing",
  "jd_analysis": { ... },
  "jd_embedding": { ... },
  "error": "Error message (if failed)"
}
```

---

#### `DELETE /api/jobs/:id`
Delete job + all associated resumes and scores

**Response:**
```json
{
  "success": true,
  "deleted": {
    "job": true,
    "resumes": 45,
    "scores": 45
  }
}
```

---

### Resumes API ([src/routes/resumes.ts](backend/src/routes/resumes.ts))

#### `GET /api/resumes?groupId={groupId}`
Get all resumes for a job (via resume group)

**Query Params:**
- `groupId` (required): Resume group ID (linked to job)

**Response:**
```json
{
  "success": true,
  "resumes": [
    {
      "_id": "698460a12b5a0fb4253385d1",
      "filename": "john_doe_resume.pdf",
      "original_name": "john_doe_resume.pdf",
      "group_id": "69845ac02b5a0fb4253385c8",
      "extraction_status": "success",
      "parsing_status": "success",
      "embedding_status": "success",
      "parsed_content": {
        "name": "John Doe",
        "email": "john@example.com",
        "phone": "+1234567890",
        "experience": [ ... ],
        "skills": [ ... ],
        "education": [ ... ]
      },
      "createdAt": "2026-02-01T10:32:00.000Z"
    }
  ]
}
```

---

#### `POST /api/resumes`
Upload resume files (batch upload)

**Request (multipart/form-data):**
```
POST /api/resumes
Content-Type: multipart/form-data

files: [<file1.pdf>, <file2.pdf>, ...]
groupId: 69845ac02b5a0fb4253385c8
```

**Response:**
```json
{
  "success": true,
  "uploaded": [
    {
      "resumeId": "698460a12b5a0fb4253385d1",
      "filename": "john_doe_resume.pdf",
      "status": "uploaded"
    }
  ],
  "failed": []
}
```

---

#### `GET /api/resumes/:id`
Get single resume details

**Response:**
```json
{
  "success": true,
  "resume": {
    "_id": "698460a12b5a0fb4253385d1",
    "filename": "john_doe_resume.pdf",
    "parsed_content": { ... },
    "resume_embedding": {
      "model": "text-embedding-3-small",
      "dimension": 1536,
      "profile": [[0.123, 0.456, ...]],
      "skills": [[0.789, 0.012, ...]],
      "projects": [[...]],
      "responsibilities": [[...]],
      "education": [[...]],
      "overall": [[...]]
    }
  }
}
```

---

### Processing API ([src/routes/process.ts](backend/src/routes/process.ts))

#### `POST /api/process/jd/:jobId`
Trigger JD processing (enqueue job)

**Response:**
```json
{
  "success": true,
  "jobId": "job_12345",
  "message": "JD processing job enqueued"
}
```

---

#### `POST /api/process/resume/:resumeId`
Trigger single resume processing

**Request Body:**
```json
{
  "jobId": "69845ac02b5a0fb4253385c7"
}
```

**Response:**
```json
{
  "success": true,
  "jobId": "resume_12345",
  "message": "Resume processing job enqueued"
}
```

---

#### `POST /api/process/final-ranking/:jobId`
Trigger final ranking (after all resumes processed)

**Response:**
```json
{
  "success": true,
  "jobId": "ranking_12345",
  "message": "Final ranking job enqueued"
}
```

---

### Scores API ([src/routes/scores.ts](backend/src/routes/scores.ts))

#### `GET /api/scores/:jobId`
Get all candidate scores for a job (sorted by rank)

**Response:**
```json
{
  "success": true,
  "scores": [
    {
      "_id": "698470b12b5a0fb425338600",
      "job_id": "69845ac02b5a0fb4253385c7",
      "resume_id": "698460a12b5a0fb4253385d1",
      "candidate_name": "John Doe",
      "composite_score": 87.5,
      "final_ranking": 1,
      "hard_requirements": {
        "passed": true,
        "score": 100,
        "details": { ... }
      },
      "keyword_score": {
        "score": 85.0,
        "matched_keywords": ["React", "Node.js", "TypeScript"]
      },
      "semantic_score": {
        "score": 90.0,
        "similarity_details": { ... }
      },
      "project_score": {
        "score": 80.0,
        "relevant_projects": [ ... ]
      },
      "llm_explanation": "Strong technical skills with 6 years of full-stack experience..."
    }
  ]
}
```

---

#### `POST /api/scores`
Create/update score (used by Python processor)

**Request Body:**
```json
{
  "job_id": "69845ac02b5a0fb4253385c7",
  "resume_id": "698460a12b5a0fb4253385d1",
  "candidate_name": "John Doe",
  "composite_score": 87.5,
  "hard_requirements": { ... },
  "keyword_score": { ... },
  "semantic_score": { ... },
  "project_score": { ... }
}
```

---

### Real-Time Updates ([src/routes/sse.ts](backend/src/routes/sse.ts))

#### `GET /api/sse/job/:jobId`
Server-Sent Events stream for job progress

**Response (SSE stream):**
```
event: progress
data: {"stage":"ai_parsing","percent":45,"message":"Parsing JD with AI"}

event: progress
data: {"stage":"embedding_generation","percent":75,"message":"Generating embeddings"}

event: complete
data: {"jobId":"69845ac02b5a0fb4253385c7","status":"completed"}
```

**Client Usage (Frontend):**
```typescript
const eventSource = new EventSource(`/api/sse/job/${jobId}`);

eventSource.addEventListener('progress', (e) => {
  const data = JSON.parse(e.data);
  console.log(`Progress: ${data.percent}% - ${data.message}`);
});

eventSource.addEventListener('complete', (e) => {
  console.log('Job completed!');
  eventSource.close();
});
```

---

## 💾 Database Models

### Job Model ([src/models/Job.ts](backend/src/models/Job.ts))

**Schema:**
```typescript
interface IJob extends Document {
  title: string;
  description?: string;
  jd_file?: string;
  jd_text?: string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  error?: string;
  
  // AI Analysis Results
  jd_analysis?: {
    role_title?: string;
    required_skills?: string[];
    preferred_skills?: string[];
    years_experience_required?: number;
    weighting?: Record<string, number>;
    hr_points?: number;
    hr_notes?: Array<{
      category: string;
      type: 'recommendation' | 'inferred_requirement';
      note: string;
      impact?: number;
    }>;
    // ... (50+ fields, see full schema in Job.ts)
  };
  
  // Embeddings
  jd_embedding?: {
    model?: string;
    dimension?: number;
    skills_embed?: string;
    responsibilities_embed?: string;
    overall_embed?: string;
  };
  
  // Filter Requirements
  filter_requirements?: {
    mandatory_compliances?: Record<string, any>;
    soft_compliances?: Record<string, any>;
  };
  
  created_at: Date;
  updated_at: Date;
}
```

**Indexes:**
- `status`: For filtering by status
- `created_at`: For sorting by date

---

### Resume Model ([src/models/Resume.ts](backend/src/models/Resume.ts))

**Schema:**
```typescript
interface IResume extends Document {
  filename: string;
  original_name: string;
  group_id?: mongoose.Types.ObjectId; // Reference to ResumeGroup
  
  raw_text?: string;
  
  // Processing Status
  extraction_status: 'pending' | 'success' | 'failed';
  parsing_status: 'pending' | 'success' | 'failed';
  embedding_status: 'pending' | 'success' | 'failed';
  
  // AI Parser Output
  parsed_content?: {
    name?: string;
    email?: string;
    phone?: string;
    experience?: Array<{
      title: string;
      company: string;
      duration: string;
      description: string;
      skills_used?: string[];
    }>;
    education?: Array<{
      degree: string;
      institution: string;
      year: string;
    }>;
    skills?: string[];
    canonical_skills?: Record<string, string[]>;
    projects?: Array<any>;
    certifications?: string[];
    // ... (see full schema in Resume.ts)
  };
  
  // Resume Embeddings (6 sections)
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
  
  createdAt: Date;
  updatedAt: Date;
}
```

**Indexes:**
- `filename`: Unique filename lookup
- `group_id`: For filtering resumes by job
- `extraction_status`, `parsing_status`, `embedding_status`: Processing filters

---

### ScoreResult Model ([src/models/ScoreResult.ts](backend/src/models/ScoreResult.ts))

**Schema:**
```typescript
interface IScoreResult extends Document {
  job_id: mongoose.Types.ObjectId;
  resume_id: mongoose.Types.ObjectId;
  candidate_name?: string;
  
  // Composite Score (weighted average)
  composite_score: number;
  
  // Individual Scores
  hard_requirements: {
    passed: boolean;
    score: number;
    details: Record<string, any>;
  };
  
  keyword_score: {
    score: number;
    matched_keywords: string[];
    missing_keywords: string[];
  };
  
  semantic_score: {
    score: number;
    similarity_details: Record<string, number>;
  };
  
  project_score: {
    score: number;
    relevant_projects: Array<any>;
  };
  
  // Final Ranking (after LLM re-ranking)
  final_ranking?: number;
  llm_explanation?: string;
  
  created_at: Date;
  updated_at: Date;
}
```

**Indexes:**
- `job_id`: For fetching all scores for a job
- `resume_id`: For fetching score for a resume
- `composite_score`: For sorting by score
- `final_ranking`: For sorting by final rank

---

## 📤 Queue Management

### Enqueuing Jobs ([src/services/queueService.ts](backend/src/services/queueService.ts))

```typescript
import { jdProcessingQueue, resumeProcessingQueue, finalRankingQueue } from '../config/queue';

export class QueueService {
  // Enqueue JD processing
  static async enqueueJDProcessing(jobId: string) {
    const job = await jdProcessingQueue.add(
      'process-jd',
      { jobId },
      {
        attempts: 3,
        backoff: {
          type: 'exponential',
          delay: 5000,
        },
        removeOnComplete: false, // Keep for debugging
        removeOnFail: false,
      }
    );
    
    return job.id;
  }
  
  // Enqueue resume processing
  static async enqueueResumeProcessing(resumeId: string, jobId: string) {
    const job = await resumeProcessingQueue.add(
      'process-resume',
      { resumeId, jobId },
      {
        attempts: 3,
        backoff: { type: 'exponential', delay: 5000 },
      }
    );
    
    return job.id;
  }
  
  // Enqueue final ranking
  static async enqueueFinalRanking(jobId: string) {
    const job = await finalRankingQueue.add(
      'final-ranking',
      { jobId },
      {
        attempts: 2,
        backoff: { type: 'fixed', delay: 10000 },
      }
    );
    
    return job.id;
  }
}
```

### Job Progress Tracking

Python processor updates job progress via BullMQ's `job.updateProgress()`:
```python
await job.updateProgress({
  'percent': 50,
  'stage': 'ai_parsing',
  'message': 'Parsing JD with AI'
})
```

Backend listens to progress updates and broadcasts via SSE:
```typescript
jdProcessingQueue.on('progress', (job, progress) => {
  sseManager.broadcast(job.data.jobId, 'progress', progress);
});
```

---

## 📡 Real-Time Updates

### SSE Manager ([src/services/sseManager.ts](backend/src/services/sseManager.ts))

```typescript
import { Response } from 'express';

class SSEManager {
  private connections: Map<string, Set<Response>> = new Map();
  
  // Register client connection
  addClient(jobId: string, res: Response) {
    if (!this.connections.has(jobId)) {
      this.connections.set(jobId, new Set());
    }
    this.connections.get(jobId)!.add(res);
    
    // Setup SSE headers
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
    });
    
    // Send initial ping
    res.write(`data: {"type":"connected"}\n\n`);
    
    // Cleanup on disconnect
    res.on('close', () => {
      this.connections.get(jobId)?.delete(res);
    });
  }
  
  // Broadcast event to all clients watching a job
  broadcast(jobId: string, event: string, data: any) {
    const clients = this.connections.get(jobId);
    if (!clients) return;
    
    const message = `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
    
    clients.forEach(res => {
      try {
        res.write(message);
      } catch (err) {
        clients.delete(res);
      }
    });
  }
  
  // Cleanup connections for a job
  cleanup(jobId: string) {
    const clients = this.connections.get(jobId);
    if (clients) {
      clients.forEach(res => res.end());
      this.connections.delete(jobId);
    }
  }
}

export const sseManager = new SSEManager();
```

---

## ⚙️ Configuration

### Environment Variables

```bash
# Node Environment
NODE_ENV=production              # development | production
PORT=3001                        # Server port

# MongoDB
MONGODB_URI=mongodb://admin:password123@mongodb:27017/kreeda_hiring_bot?authSource=admin

# Redis (BullMQ)
REDIS_HOST=redis                 # Redis host
REDIS_PORT=6379                  # Redis port
REDIS_PASSWORD=password123       # Redis password

# CORS
CORS_ORIGINS=http://localhost:3000,https://yourdomain.com

# OpenAI (for backend-initiated AI calls, if any)
OPENAI_API_KEY=sk-proj-xxxxx    # Optional: backend doesn't use AI directly

# File Uploads
MAX_FILE_SIZE=10485760           # 10MB in bytes
UPLOAD_DIR=./uploads             # Upload directory

# Rate Limiting
RATE_LIMIT_WINDOW_MS=900000      # 15 minutes
RATE_LIMIT_MAX=1000              # Max requests per window
```

### Configuration Module ([src/config/index.ts](backend/src/config/index.ts))

```typescript
import dotenv from 'dotenv';
dotenv.config();

export default {
  nodeEnv: process.env.NODE_ENV || 'development',
  port: parseInt(process.env.PORT || '3001'),
  
  mongodb: {
    uri: process.env.MONGODB_URI || 'mongodb://localhost:27017/kreeda'
  },
  
  redis: {
    host: process.env.REDIS_HOST || 'localhost',
    port: parseInt(process.env.REDIS_PORT || '6379'),
    password: process.env.REDIS_PASSWORD || ''
  },
  
  corsOrigins: (process.env.CORS_ORIGINS || 'http://localhost:3000')
    .split(',')
    .map(o => o.trim()),
  
  upload: {
    maxFileSize: parseInt(process.env.MAX_FILE_SIZE || '10485760'),
    uploadDir: process.env.UPLOAD_DIR || './uploads'
  }
};
```

---

## 🚨 Error Handling

### Global Error Handler ([src/middleware/errorHandler.ts](backend/src/middleware/errorHandler.ts))

```typescript
import { Request, Response, NextFunction } from 'express';

export class AppError extends Error {
  constructor(
    public statusCode: number,
    public message: string,
    public isOperational = true
  ) {
    super(message);
    Object.setPrototypeOf(this, AppError.prototype);
  }
}

export const errorHandler = (
  err: Error | AppError,
  req: Request,
  res: Response,
  next: NextFunction
) => {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      success: false,
      error: err.message,
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
    });
  }
  
  // Unknown error
  console.error('❌ Unhandled error:', err);
  
  res.status(500).json({
    success: false,
    error: 'Internal server error',
    ...(process.env.NODE_ENV === 'development' && {
      message: err.message,
      stack: err.stack
    })
  });
};
```

**Usage in routes:**
```typescript
import { AppError } from '../middleware/errorHandler';

router.get('/jobs/:id', async (req, res, next) => {
  try {
    const job = await Job.findById(req.params.id);
    if (!job) {
      throw new AppError(404, 'Job not found');
    }
    res.json({ success: true, job });
  } catch (err) {
    next(err); // Pass to error handler
  }
});
```

---

## 🧪 Testing

### Unit Tests (Example with Jest)

```typescript
// tests/models/Job.test.ts
import mongoose from 'mongoose';
import Job from '../../src/models/Job';

describe('Job Model', () => {
  beforeAll(async () => {
    await mongoose.connect(process.env.MONGO_TEST_URI!);
  });
  
  afterAll(async () => {
    await mongoose.disconnect();
  });
  
  it('should create a job', async () => {
    const job = await Job.create({
      title: 'Test Job',
      description: 'Test description'
    });
    
    expect(job.title).toBe('Test Job');
    expect(job.status).toBe('pending');
  });
});
```

### Integration Tests

```typescript
// tests/routes/jobs.test.ts
import request from 'supertest';
import app from '../../src/app';

describe('Jobs API', () => {
  it('GET /api/jobs should return jobs', async () => {
    const res = await request(app).get('/api/jobs');
    
    expect(res.status).toBe(200);
    expect(res.body.success).toBe(true);
    expect(Array.isArray(res.body.jobs)).toBe(true);
  });
});
```

---

## 🚀 Deployment

### Docker Build

```bash
# Build production image
docker build -t kreeda-backend:latest -f Dockerfile .

# Run container
docker run -d \
  -p 3001:3001 \
  -e MONGODB_URI=mongodb://... \
  -e REDIS_HOST=redis \
  -e OPENAI_API_KEY=sk-... \
  --name kreeda-backend \
  kreeda-backend:latest
```

### Health Check Endpoint

```bash
curl http://localhost:3001/api/health
```

**Response:**
```json
{
  "status": "OK",
  "timestamp": "2026-02-05T10:30:00.000Z",
  "environment": "production",
  "services": {
    "database": "connected",
    "redis": "connected"
  }
}
```

---

## 🔧 Maintenance

### Database Migrations

```bash
# Connect to MongoDB
docker exec -it kreeda-mongo mongosh -u admin -p password123

use kreeda_hiring_bot

# Add index
db.jobs.createIndex({ "created_at": -1 })

# Update schema
db.jobs.updateMany(
  { new_field: { $exists: false } },
  { $set: { new_field: 'default' } }
)
```

### Queue Cleanup

```bash
# Clear all queues (Redis CLI)
docker exec -it kreeda-redis redis-cli -a password123

# Delete all jobs
KEYS bull:*:*
# (manually delete or use script)

# Flush all Redis data (CAUTION)
FLUSHALL
```

---

**Last Updated**: February 5, 2026
**Version**: 1.0.0
