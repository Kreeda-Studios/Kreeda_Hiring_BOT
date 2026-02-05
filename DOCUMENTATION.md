# Kreeda Hiring Bot - Complete Project Documentation

## 📋 Table of Contents
- [Overview](#overview)
- [System Architecture](#system-architecture)
- [Technology Stack](#technology-stack)
- [Project Structure](#project-structure)
- [Key Features](#key-features)
- [Data Flow](#data-flow)
- [Setup & Installation](#setup--installation)
- [Development Guide](#development-guide)
- [Production Deployment](#production-deployment)
- [API Documentation](#api-documentation)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

**Kreeda Hiring Bot** is an AI-powered ATS (Applicant Tracking System) that automates resume screening and candidate ranking using advanced NLP, semantic matching, and LLM-based re-ranking.

### What It Does
- **Job Description Processing**: Extract, parse, and structure JD requirements using AI
- **Resume Processing**: Parse resumes, extract skills/experience, generate embeddings
- **Smart Scoring**: Multi-dimensional scoring (keywords, semantic similarity, projects, hard requirements)
- **AI Re-ranking**: LLM-based final ranking with compliance validation
- **Real-time Updates**: Live progress tracking via Server-Sent Events (SSE)

### Use Cases
- **HR Teams**: Automate initial resume screening, saving 80%+ time
- **Recruiters**: Get AI-powered candidate rankings with detailed scoring breakdowns
- **Companies**: Build compliant, consistent, explainable hiring workflows

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                      Frontend (Next.js)                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   Jobs   │  │ Resumes  │  │  Scores  │  │  Admin   │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└───────────────────────────┬─────────────────────────────────────┘
                            │ HTTP/REST + SSE
┌───────────────────────────▼─────────────────────────────────────┐
│                   Backend (Node.js/Express)                      │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────┐       │
│  │   API    │  │  BullMQ  │  │  Socket  │  │  Routes  │       │
│  │ Gateway  │  │  Queue   │  │   .IO    │  │ /Models  │       │
│  └──────────┘  └──────────┘  └──────────┘  └──────────┘       │
└─────┬──────────────────┬──────────────────────┬────────────────┘
      │                  │                      │
      ▼                  ▼                      ▼
┌──────────┐      ┌──────────┐         ┌──────────────┐
│ MongoDB  │      │  Redis   │         │  Uploads/    │
│ Database │      │  Queue   │         │  Files       │
└──────────┘      └─────┬────┘         └──────────────┘
                        │
                        ▼
┌───────────────────────────────────────────────────────────────┐
│           Python Processor (BullMQ Consumer)                  │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐       │
│  │      JD      │  │    Resume    │  │    Final     │       │
│  │  Processing  │  │  Processing  │  │   Ranking    │       │
│  └──────────────┘  └──────────────┘  └──────────────┘       │
│         │                 │                   │               │
│         └─────────────────┴───────────────────┘               │
│                           │                                   │
│                   ┌───────▼────────┐                         │
│                   │  OpenAI GPT    │                         │
│                   │  + Embeddings  │                         │
│                   └────────────────┘                         │
└───────────────────────────────────────────────────────────────┘
```

### Component Responsibilities

| Component | Purpose | Technologies |
|-----------|---------|--------------|
| **Frontend** | User interface for job/resume management | Next.js 16, React 19, TailwindCSS, Radix UI |
| **Backend** | REST API, job queuing, real-time updates | Node.js, Express, TypeScript, BullMQ, Socket.IO |
| **Python Processor** | AI-powered processing (JD/Resume/Ranking) | Python 3.11, OpenAI SDK, scikit-learn, PyMuPDF |
| **MongoDB** | Primary data store (jobs, resumes, scores) | MongoDB 7.0 |
| **Redis** | Queue management + pub/sub | Redis 7 (BullMQ backend) |

---

## 🛠️ Technology Stack

### Frontend Stack
```json
{
  "framework": "Next.js 16.1.4 (App Router)",
  "language": "TypeScript 5",
  "ui": "React 19.2.3",
  "styling": "TailwindCSS 4 + tw-animate-css",
  "components": "Radix UI (shadcn/ui components)",
  "state": "React Hooks + Socket.IO Client",
  "notifications": "Sonner (toast)",
  "icons": "Lucide React"
}
```

### Backend Stack
```json
{
  "runtime": "Node.js ≥18.0.0",
  "framework": "Express 4.18",
  "language": "TypeScript 5.1",
  "database": "MongoDB 7.0 (Mongoose ODM)",
  "queue": "BullMQ 5.67 (Redis-based)",
  "realtime": "Socket.IO 4.8",
  "validation": "Express-validator",
  "security": "Helmet, CORS, Rate-limiting"
}
```

### Python Processor Stack
```json
{
  "runtime": "Python 3.11+",
  "ai": "OpenAI SDK 1.0+ (GPT-4o-mini, text-embedding-3-small)",
  "queue": "BullMQ Python 1.0+",
  "pdf": "PyMuPDF (fitz), python-docx",
  "ml": "scikit-learn, numpy",
  "http": "requests",
  "parsing": "beautifulsoup4, fuzzywuzzy"
}
```

### Infrastructure
```yaml
Orchestration: Docker Compose (dev + prod)
Containerization: Docker (multi-stage builds)
Database: MongoDB 7.0 (containerized)
Cache/Queue: Redis 7 Alpine (containerized)
Reverse Proxy: Nginx (production, optional)
```

---

## 📁 Project Structure

```
Kreeda_Hiring_BOT/
│
├── backend/                      # Node.js Backend (TypeScript)
│   ├── src/
│   │   ├── server.ts            # Entry point
│   │   ├── app.ts               # Express app setup
│   │   ├── config/              # DB, Redis, Queue config
│   │   ├── models/              # Mongoose models (Job, Resume, etc.)
│   │   ├── routes/              # REST API routes
│   │   ├── services/            # Business logic (queue, scoring)
│   │   ├── middleware/          # Auth, error handling
│   │   ├── types/               # TypeScript interfaces
│   │   └── utils/               # Helper functions
│   ├── Dockerfile               # Production container
│   ├── Dockerfile.dev           # Dev container (hot reload)
│   ├── package.json
│   └── tsconfig.json
│
├── frontend/                     # Next.js Frontend (TypeScript + React)
│   ├── src/
│   │   ├── app/                 # Next.js App Router pages
│   │   │   ├── page.tsx         # Home/Dashboard
│   │   │   ├── jobs/            # Job listing & details
│   │   │   └── layout.tsx       # Root layout
│   │   ├── components/          # React components
│   │   │   ├── common/          # Shared UI components
│   │   │   ├── jobs/            # Job-specific components
│   │   │   └── ui/              # shadcn/ui primitives
│   │   ├── hooks/               # Custom React hooks
│   │   └── lib/                 # Utilities (API client, utils)
│   ├── Dockerfile
│   ├── Dockerfile.dev
│   ├── package.json
│   ├── next.config.ts
│   └── tailwind.config.ts
│
├── scripts/                      # Python Processing Scripts
│   ├── bullmq_consumer.py       # Main BullMQ worker (async)
│   ├── openai_client.py         # OpenAI client singleton
│   ├── requirements.txt
│   │
│   ├── common/                  # Shared utilities
│   │   ├── api_client.py        # Backend API client
│   │   ├── job_logger.py        # Structured logging
│   │   └── bullmq_progress.py   # Progress tracking
│   │
│   ├── jd-processing/           # Job Description Processing
│   │   ├── main_jd_processor.py                 # Orchestrator
│   │   ├── a_pdf_text_extractor.py              # PDF → text
│   │   ├── b_ai_jd_parser.py                    # AI parsing (GPT)
│   │   ├── c_ai_embedding_generator.py          # Generate embeddings
│   │   └── d_compliance_parser.py               # Filter requirements
│   │
│   ├── resume-processing/       # Resume Processing Pipeline
│   │   ├── main_resume_processor.py             # Orchestrator
│   │   ├── a_pdf_extractor.py                   # PDF → text
│   │   ├── b_ai_parser.py                       # AI parsing
│   │   ├── c_embedding_generator.py             # Embeddings
│   │   ├── d_hard_requirements_checker.py       # Compliance check
│   │   ├── e_keyword_scorer.py                  # Keyword scoring
│   │   ├── f_semantic_scorer.py                 # Semantic similarity
│   │   ├── g_project_scorer.py                  # Project relevance
│   │   └── h_composite_scorer.py                # Final score
│   │
│   └── final-ranking/           # Final Ranking (LLM Re-rank)
│       └── main_ranking_processor.py            # GPT-4o re-ranking
│
├── uploads/                      # Uploaded files (JDs, Resumes)
│   └── {job_id}/                # Per-job directories
│
├── Old_Code_Archive/            # Legacy code (reference only)
│
├── docker-compose.yml           # Production orchestration
├── docker-compose.dev.yml       # Development orchestration
├── .env.example                 # Environment template
├── test_flow_simple.sh          # Integration test script
└── README.md                    # Quick start guide
```

---

## 🚀 Key Features

### 1. **AI-Powered JD Analysis**
- Extracts structured requirements from raw JD PDFs/text
- Normalizes skills to canonical forms (ML → Machine Learning)
- Generates compliance rules (mandatory vs. soft)
- Creates weighted keywords for ATS scoring
- Provides HR recommendations (salary transparency, clarity improvements)

**Example Output:**
```json
{
  "role_title": "Senior Full Stack Engineer",
  "required_skills": ["React", "Node.js", "TypeScript", "PostgreSQL"],
  "preferred_skills": ["AWS", "Kubernetes", "GraphQL"],
  "years_experience_required": 5,
  "domain_tags": ["Fullstack", "Cloud", "AIML"],
  "weighting": {
    "required_skills": 0.40,
    "responsibilities": 0.25,
    "domain_relevance": 0.15
  }
}
```

### 2. **Smart Resume Parsing**
- Multi-format support (PDF, DOCX)
- Extracts: skills, experience, education, projects, certifications
- Infers missing skills from context (e.g., "built REST APIs" → "API Development")
- Skill proficiency detection (Beginner/Intermediate/Expert)
- Multi-section embeddings for semantic search

### 3. **Multi-Dimensional Scoring**

| Score Type | Weight | Description |
|------------|--------|-------------|
| **Hard Requirements** | 30% | Pass/fail filters (experience, education, must-have skills) |
| **Keyword Match** | 25% | Exact skill/technology matches (weighted by importance) |
| **Semantic Similarity** | 25% | Cosine similarity between JD & resume embeddings |
| **Project Relevance** | 20% | Domain-specific project experience scoring |

**Composite Score Formula:**
```python
composite_score = (
    0.30 * hard_requirements_score +
    0.25 * keyword_score +
    0.25 * semantic_score +
    0.20 * project_score
)
```

### 4. **LLM Re-Ranking**
- Final ranking uses GPT-4o-mini for contextual understanding
- Processes top 30 candidates per batch
- Validates compliance before re-ranking
- Provides detailed explanations for rankings

### 5. **Real-Time Progress Tracking**
- **BullMQ Progress**: % completion per processing stage
- **SSE (Server-Sent Events)**: Live updates pushed to frontend
- **Socket.IO**: Fallback for real-time notifications
- **Status Persistence**: Resume from failures without losing progress

---

## 🔄 Data Flow

### Complete Workflow (Job Creation → Candidate Ranking)

```
1. User Uploads JD + Resumes
   ↓
2. Backend Creates Job + Resume Records
   ↓
3. Backend Enqueues Processing Jobs
   ├── Queue: jd-processing (job_id)
   └── Queue: resume-processing (resume_id, job_id)
   ↓
4. Python Workers Process Asynchronously
   │
   ├─→ JD Processing (5 steps)
   │   ├── Extract PDF text
   │   ├── Parse with GPT-4o-mini
   │   ├── Validate compliance rules
   │   ├── Generate embeddings
   │   └── Save to DB
   │
   └─→ Resume Processing (8 steps per resume)
       ├── Extract PDF text
       ├── Parse with GPT-4o-mini
       ├── Generate embeddings
       ├── Check hard requirements
       ├── Calculate keyword score
       ├── Calculate semantic score
       ├── Calculate project score
       ├── Compute composite score
       └── Save scores to DB
   ↓
5. All Resumes Processed → Trigger Final Ranking
   ↓
6. Final Ranking (LLM Re-rank)
   ├── Fetch all candidates for job
   ├── Batch into groups of 30
   ├── Call GPT-4o-mini for re-ranking
   ├── Merge batches
   └── Update final_ranking in DB
   ↓
7. Frontend Displays Results
   ├── Job status: completed
   ├── Ranked candidate list
   └── Detailed score breakdowns
```

### Queue Architecture

**BullMQ Queues:**
1. **jd-processing**: Processes job descriptions
2. **resume-processing**: Processes individual resumes
3. **final-ranking**: Re-ranks candidates after all resumes processed

**Queue Flow:**
```
Backend (Producer)                Python Worker (Consumer)
    │                                     │
    ├─ Add job to queue                  │
    │  (job_id, resume_id, etc.)         │
    │                                     │
    │  ─────────────────────────────────→│
    │                                     ├─ Receive job
    │                                     ├─ Process (AI calls)
    │                                     ├─ Update progress (%)
    │                                     └─ Complete/Fail job
    │  ←─────────────────────────────────│
    │                                     │
    ├─ Emit SSE event                    │
    └─ Update frontend                   │
```

---

## ⚙️ Setup & Installation

### Prerequisites
- **Docker** 20.10+ & **Docker Compose** 2.0+
- **Node.js** 18+ (for local dev)
- **Python** 3.11+ (for local dev)
- **OpenAI API Key** (required)

### Environment Variables

Create `.env` file in project root:

```bash
# OpenAI API
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxx

# Backend API (used by Python processor)
BACKEND_API_URL=http://backend:3001/api
BACKEND_API_KEY=               # Optional: for secured endpoints

# Frontend (build-time)
NEXT_PUBLIC_API_URL=http://localhost:3001/api

# MongoDB (Docker internal)
MONGODB_URI=mongodb://admin:password123@mongodb:27017/kreeda_hiring_bot?authSource=admin

# Redis (Docker internal)
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASSWORD=password123

# Node Environment
NODE_ENV=production
PORT=3001
```

### Quick Start (Docker Compose - Recommended)

```bash
# 1. Clone repository
git clone <repo-url>
cd Kreeda_Hiring_BOT

# 2. Create .env file (see above)
cp .env.example .env
# Edit .env and add your OPENAI_API_KEY

# 3. Start all services
docker compose up --build

# Services will be available at:
# - Frontend: http://localhost:3000
# - Backend API: http://localhost:3001
# - MongoDB: localhost:27017
# - Redis: localhost:6379
```

### Development Mode (Hot Reload)

```bash
# Use dev compose file (hot reload enabled)
docker compose -f docker-compose.dev.yml up --build

# Or run services individually:

# Terminal 1: Backend
cd backend
npm install
npm run dev

# Terminal 2: Frontend
cd frontend
npm install
npm run dev

# Terminal 3: Python Processor
cd scripts
pip install -r requirements.txt
python bullmq_consumer.py

# Terminal 4: MongoDB + Redis
docker compose up mongodb redis
```

---

## 🧪 Development Guide

### Adding a New API Endpoint

1. **Define Route** ([backend/src/routes/jobs.ts](backend/src/routes/jobs.ts)):
```typescript
router.get('/my-endpoint/:id', async (req, res) => {
  const { id } = req.params;
  const data = await MyService.fetchData(id);
  res.json({ success: true, data });
});
```

2. **Register Route** ([backend/src/app.ts](backend/src/app.ts)):
```typescript
import myRoutes from './routes/myRoutes';
this.app.use('/api/my-route', myRoutes);
```

3. **Frontend API Call** ([frontend/src/lib/api.ts](frontend/src/lib/api.ts)):
```typescript
export async function fetchMyData(id: string) {
  const res = await fetch(`${API_URL}/my-route/my-endpoint/${id}`);
  return res.json();
}
```

### Extending the Python Processor

**Example: Add new scoring dimension**

1. Create new scorer: `scripts/resume-processing/i_custom_scorer.py`
```python
def calculate_custom_score(resume_data: dict, jd_data: dict) -> dict:
    score = 0.0
    details = {}
    
    # Your scoring logic here
    
    return {
        'score': score,
        'max_score': 100.0,
        'details': details
    }
```

2. Update orchestrator: `scripts/resume-processing/main_resume_processor.py`
```python
from i_custom_scorer import calculate_custom_score

# In process_resume_pipeline():
custom_score_result = calculate_custom_score(parsed_resume, jd_analysis)

# Update composite scorer weights in h_composite_scorer.py
```

### Database Schema Changes

1. **Update Mongoose Model** ([backend/src/models/Job.ts](backend/src/models/Job.ts)):
```typescript
interface IJob extends Document {
  // Add new field
  new_field?: string;
}

const jobSchema = new Schema<IJob>({
  new_field: { type: String, default: '' }
});
```

2. **Migration** (if needed):
```bash
# Connect to MongoDB
docker exec -it kreeda-mongo mongosh -u admin -p password123

use kreeda_hiring_bot

# Update existing documents
db.jobs.updateMany(
  { new_field: { $exists: false } },
  { $set: { new_field: 'default_value' } }
)
```

---

## 🚢 Production Deployment

### Docker Compose Production

```bash
# 1. Set production environment variables
export OPENAI_API_KEY=sk-proj-xxxxx
export NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api

# 2. Build and start
docker compose -f docker-compose.yml up -d --build

# 3. Verify health
docker compose ps
curl http://localhost:3001/api/health
```

### Cloud Deployment (AWS ECS / GCP Cloud Run)

**Option 1: Push to Container Registry**
```bash
# Build images
docker build -t kreeda-backend:latest ./backend
docker build -t kreeda-frontend:latest ./frontend
docker build -t kreeda-python:latest ./scripts

# Tag and push
docker tag kreeda-backend:latest gcr.io/your-project/kreeda-backend
docker push gcr.io/your-project/kreeda-backend

# Deploy via cloud provider UI or CLI
```

**Option 2: Kubernetes Helm Chart**
```yaml
# values.yaml
backend:
  replicas: 3
  image: kreeda-backend:latest
  env:
    - name: OPENAI_API_KEY
      valueFrom:
        secretKeyRef:
          name: kreeda-secrets
          key: openai-api-key
```

### Monitoring & Logging

- **Application Logs**: Docker logs or centralized logging (ELK, CloudWatch)
- **Queue Monitoring**: BullMQ Dashboard (optional add-on)
- **Database**: MongoDB Atlas monitoring or self-hosted Prometheus
- **Errors**: Sentry integration (add to backend/frontend)

---

## 📡 API Documentation

### Base URL
```
Development: http://localhost:3001/api
Production: https://api.yourdomain.com/api
```

### Authentication
Currently **no authentication** required. Add JWT/API keys as needed.

### Core Endpoints

#### Jobs

**GET /api/jobs**
- Fetch all jobs (paginated)
- Query params: `page`, `limit`, `status`

**GET /api/jobs/:id**
- Get job details + JD analysis

**POST /api/jobs**
- Create new job
- Body: `{ title, description, jd_file?, jd_text? }`

**PATCH /api/jobs/:id**
- Update job (used by Python processor)

**DELETE /api/jobs/:id**
- Delete job + associated resumes

#### Resumes

**GET /api/resumes?groupId={groupId}**
- Get resumes for a job

**POST /api/resumes**
- Upload resume files (multipart/form-data)

**GET /api/resumes/:id**
- Get single resume details

#### Scores

**GET /api/scores/:jobId**
- Get all candidate scores for job (ranked)

**POST /api/scores**
- Create/update score (used by Python processor)

#### Processing

**POST /api/process/jd/:jobId**
- Trigger JD processing (enqueues job)

**POST /api/process/resume/:resumeId**
- Trigger resume processing

**POST /api/process/final-ranking/:jobId**
- Trigger final ranking

#### Real-Time Updates

**GET /api/sse/job/:jobId**
- Server-Sent Events stream for job progress
- Events: `progress`, `complete`, `error`

**GET /api/updates/scores/:jobId**
- Poll for latest scores

---

## 🐛 Troubleshooting

### Common Issues

#### 1. "OpenAI API key not found"
```bash
# Check .env file exists and has valid key
cat .env | grep OPENAI_API_KEY

# Restart services after adding key
docker compose restart
```

#### 2. "Redis connection failed"
```bash
# Check Redis is running
docker compose ps redis

# Test connection
docker exec kreeda-redis redis-cli -a password123 ping
# Should return: PONG

# Check Python processor logs
docker logs kreeda-python-processor -f
```

#### 3. "MongoDB connection timeout"
```bash
# Verify MongoDB health
docker compose ps mongodb

# Check logs
docker logs kreeda-mongo -f

# Test connection
docker exec kreeda-mongo mongosh -u admin -p password123 --eval "db.runCommand({ping:1})"
```

#### 4. "Job stuck in processing"
```bash
# Check Python processor is running
docker logs kreeda-python-processor -f

# Inspect BullMQ queue (use Redis CLI)
docker exec kreeda-redis redis-cli -a password123
> KEYS bull:*
> HGETALL bull:jd-processing:{job_id}

# Manually fail job (if needed)
curl -X PATCH http://localhost:3001/api/jobs/{job_id} \
  -H "Content-Type: application/json" \
  -d '{"status":"failed","error":"Manual reset"}'
```

#### 5. "Frontend not connecting to backend"
```bash
# Check NEXT_PUBLIC_API_URL
echo $NEXT_PUBLIC_API_URL
# Should be: http://localhost:3001/api (dev) or https://api.domain.com/api (prod)

# Rebuild frontend with correct env
docker compose up --build frontend
```

### Debug Mode

**Enable verbose logging:**

1. **Backend** ([backend/src/config/index.ts](backend/src/config/index.ts)):
```typescript
export default {
  logLevel: 'debug'  // Change from 'info'
}
```

2. **Python Processor** ([scripts/bullmq_consumer.py](scripts/bullmq_consumer.py)):
```python
logging.basicConfig(level=logging.DEBUG)  # Change from INFO
```

3. **View logs:**
```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f python-processor

# Last 100 lines
docker compose logs --tail=100 backend
```

---

## 📚 Additional Resources

### Documentation Links
- **Backend Details**: [BACKEND.md](BACKEND.md)
- **Frontend Details**: [FRONTEND.md](FRONTEND.md)
- **Python Scripts**: [SCRIPTS.md](SCRIPTS.md)

### External References
- [BullMQ Documentation](https://docs.bullmq.io/)
- [OpenAI API Reference](https://platform.openai.com/docs)
- [Next.js App Router](https://nextjs.org/docs/app)
- [Mongoose ODM](https://mongoosejs.com/docs/)

### Support
- **Issues**: Report bugs via GitHub Issues
- **Discussions**: Use GitHub Discussions for questions
- **Email**: support@yourdomain.com

---

## 📄 License

[Your License Here - e.g., MIT]

---

## 👥 Contributors

- **Original Author**: Soham
- **Contributors**: [List contributors]

---

**Last Updated**: February 5, 2026
**Version**: 1.0.0
