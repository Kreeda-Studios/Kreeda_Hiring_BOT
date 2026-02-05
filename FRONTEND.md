# Frontend Documentation - Kreeda Hiring Bot

## 📋 Table of Contents
- [Overview](#overview)
- [Architecture](#architecture)
- [Directory Structure](#directory-structure)
- [Technology Stack](#technology-stack)
- [Core Features](#core-features)
- [Component Library](#component-library)
- [State Management](#state-management)
- [API Integration](#api-integration)
- [Real-Time Updates](#real-time-updates)
- [Styling System](#styling-system)
- [Development Guide](#development-guide)
- [Build & Deployment](#build--deployment)

---

## 🎯 Overview

The frontend is a modern **Next.js 16 App Router** application built with **React 19** and **TypeScript**. It provides an intuitive interface for:
- Creating and managing job postings
- Uploading and organizing resumes
- Viewing real-time processing progress
- Analyzing candidate scores and rankings
- Accessing detailed AI-generated insights

### Key Highlights
- **Framework**: Next.js 16 (App Router) with React Server Components
- **UI Library**: Radix UI + shadcn/ui component system
- **Styling**: TailwindCSS 4 with custom design tokens
- **Real-Time**: Server-Sent Events (SSE) + Socket.IO fallback
- **Type Safety**: Full TypeScript coverage
- **Performance**: Optimized with Next.js image optimization, code splitting, lazy loading

---

## 🏗️ Architecture

```
┌──────────────────────────────────────────────────────────────┐
│                    Next.js App Router                        │
├──────────────────────────────────────────────────────────────┤
│  App Pages (src/app/)                                        │
│  ├─ page.tsx             (Dashboard / Home)                 │
│  ├─ layout.tsx           (Root layout + providers)          │
│  ├─ jobs/                                                    │
│  │  ├─ page.tsx          (Job listing)                      │
│  │  ├─ [id]/page.tsx     (Job details)                      │
│  │  └─ new/page.tsx      (Create job)                       │
│  └─ globals.css          (Global styles)                    │
├──────────────────────────────────────────────────────────────┤
│  Components (src/components/)                                │
│  ├─ common/              (Shared components)                │
│  ├─ jobs/                (Job-specific components)          │
│  ├─ resumes/             (Resume components)                │
│  ├─ scores/              (Score display components)         │
│  └─ ui/                  (shadcn/ui primitives)             │
├──────────────────────────────────────────────────────────────┤
│  Hooks (src/hooks/)                                          │
│  ├─ useJobs.ts           (Job data fetching)                │
│  ├─ useResumes.ts        (Resume management)                │
│  ├─ useScores.ts         (Score data)                       │
│  ├─ useSSE.ts            (Server-Sent Events)               │
│  └─ useSocket.ts         (Socket.IO integration)            │
├──────────────────────────────────────────────────────────────┤
│  Utilities (src/lib/)                                        │
│  ├─ api.ts               (API client wrapper)               │
│  ├─ utils.ts             (Helper functions)                 │
│  └─ constants.ts         (App constants)                    │
└──────────────────────────────────────────────────────────────┘
                              │
                              ▼
                     Backend REST API
                   (http://localhost:3001)
```

### Component Flow
```
User Action (Button Click)
      ↓
Event Handler (onClick)
      ↓
Custom Hook (useJobs, useResumes)
      ↓
API Client (fetch wrapper)
      ↓
Backend REST API
      ↓
Response → Update State
      ↓
UI Re-render (React)
```

---

## 📁 Directory Structure

```
frontend/
├── src/
│   ├── app/                         # Next.js App Router pages
│   │   ├── page.tsx                # Home/Dashboard
│   │   ├── layout.tsx              # Root layout (providers, fonts)
│   │   ├── globals.css             # Global styles
│   │   │
│   │   └── jobs/                   # Job management pages
│   │       ├── page.tsx            # Job listing page
│   │       ├── new/
│   │       │   └── page.tsx        # Create new job
│   │       └── [id]/
│   │           ├── page.tsx        # Job detail page
│   │           └── loading.tsx     # Loading state
│   │
│   ├── components/                  # React Components
│   │   ├── common/                 # Shared components
│   │   │   ├── Navbar.tsx         # Top navigation
│   │   │   ├── Sidebar.tsx        # Side navigation
│   │   │   ├── PageContainer.tsx  # Page wrapper
│   │   │   ├── LoadingSpinner.tsx # Loading states
│   │   │   └── ErrorBoundary.tsx  # Error handling
│   │   │
│   │   ├── jobs/                   # Job-specific components
│   │   │   ├── JobCard.tsx        # Job preview card
│   │   │   ├── JobList.tsx        # Job listing grid
│   │   │   ├── JobForm.tsx        # Create/edit job form
│   │   │   ├── JobDetails.tsx     # Job detail view
│   │   │   └── JDUploader.tsx     # JD file upload
│   │   │
│   │   ├── resumes/                # Resume components
│   │   │   ├── ResumeUploader.tsx # Bulk resume upload
│   │   │   ├── ResumeList.tsx     # Resume table view
│   │   │   ├── ResumeCard.tsx     # Individual resume card
│   │   │   └── ResumeDetails.tsx  # Resume detail modal
│   │   │
│   │   ├── scores/                 # Scoring & ranking components
│   │   │   ├── ScoreTable.tsx     # Ranked candidate table
│   │   │   ├── ScoreCard.tsx      # Individual score card
│   │   │   ├── ScoreBreakdown.tsx # Score dimension details
│   │   │   └── ComplianceStatus.tsx # Compliance indicators
│   │   │
│   │   └── ui/                     # shadcn/ui primitives
│   │       ├── button.tsx         # Button component
│   │       ├── dialog.tsx         # Modal dialogs
│   │       ├── dropdown-menu.tsx  # Dropdowns
│   │       ├── progress.tsx       # Progress bars
│   │       ├── tabs.tsx           # Tab navigation
│   │       ├── card.tsx           # Card container
│   │       ├── badge.tsx          # Status badges
│   │       └── ...                # Other UI primitives
│   │
│   ├── hooks/                      # Custom React Hooks
│   │   ├── useJobs.ts             # Job CRUD operations
│   │   ├── useResumes.ts          # Resume management
│   │   ├── useScores.ts           # Score data fetching
│   │   ├── useSSE.ts              # Server-Sent Events
│   │   ├── useSocket.ts           # Socket.IO connection
│   │   ├── useUpload.ts           # File upload handler
│   │   └── useDebounce.ts         # Debounce utility
│   │
│   └── lib/                        # Utilities
│       ├── api.ts                 # API client (fetch wrapper)
│       ├── utils.ts               # Helper functions (cn, formatDate)
│       ├── constants.ts           # App constants
│       └── validators.ts          # Input validation
│
├── public/                         # Static assets
│   ├── favicon.ico
│   └── images/
│
├── Dockerfile                      # Production container
├── Dockerfile.dev                  # Development container
├── next.config.ts                  # Next.js configuration
├── tailwind.config.ts              # TailwindCSS configuration
├── tsconfig.json                   # TypeScript configuration
├── components.json                 # shadcn/ui config
├── postcss.config.mjs              # PostCSS config
├── eslint.config.mjs               # ESLint config
└── package.json                    # Dependencies & scripts
```

---

## 🛠️ Technology Stack

### Core Framework
```json
{
  "framework": "Next.js 16.1.4",
  "react": "19.2.3",
  "typescript": "5.x"
}
```

**Why Next.js 16?**
- **App Router**: File-based routing with server/client components
- **Server Components**: Reduce client bundle size, improve SEO
- **Streaming**: Progressive rendering for better UX
- **Built-in Optimization**: Image, font, and script optimization

---

### UI Framework

**Radix UI + shadcn/ui**
```json
{
  "@radix-ui/react-dialog": "1.1.15",
  "@radix-ui/react-dropdown-menu": "2.1.16",
  "@radix-ui/react-tabs": "1.1.13",
  "@radix-ui/react-progress": "1.1.8",
  "@radix-ui/react-tooltip": "1.2.8"
}
```

**shadcn/ui Philosophy:**
- Copy-paste components (not npm packages)
- Full control over component code
- Built on Radix UI primitives
- Styled with TailwindCSS

---

### Styling

**TailwindCSS 4**
```json
{
  "tailwindcss": "^4",
  "tailwind-merge": "3.4.0",
  "class-variance-authority": "0.7.1",
  "tw-animate-css": "1.4.0"
}
```

**Features:**
- Utility-first CSS framework
- Custom design tokens (colors, spacing, typography)
- Dark mode support
- CSS-in-JS avoided (pure TailwindCSS)

---

### Real-Time Communication

```json
{
  "socket.io-client": "4.7.2"
}
```

**Dual Strategy:**
1. **Primary**: Server-Sent Events (SSE) via native `EventSource`
2. **Fallback**: Socket.IO for older browsers

---

### Additional Libraries

```json
{
  "lucide-react": "0.563.0",        // Icon library
  "sonner": "2.0.7",                // Toast notifications
  "react-dropzone": "14.3.8",       // Drag-drop file upload
  "next-themes": "0.4.6"            // Dark mode management
}
```

---

## 🚀 Core Features

### 1. Job Management

#### Job Listing Page ([src/app/jobs/page.tsx](frontend/src/app/jobs/page.tsx))

**Features:**
- Grid/List view toggle
- Search by title/description
- Filter by status (pending, processing, completed, failed)
- Sort by date/title
- Pagination

**Example:**
```tsx
'use client';

import { useJobs } from '@/hooks/useJobs';
import { JobCard } from '@/components/jobs/JobCard';
import { LoadingSpinner } from '@/components/common/LoadingSpinner';

export default function JobsPage() {
  const { jobs, loading, error } = useJobs();
  
  if (loading) return <LoadingSpinner />;
  if (error) return <div>Error: {error}</div>;
  
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {jobs.map(job => (
        <JobCard key={job._id} job={job} />
      ))}
    </div>
  );
}
```

---

#### Create Job Page ([src/app/jobs/new/page.tsx](frontend/src/app/jobs/new/page.tsx))

**Features:**
- Upload JD as PDF/DOCX or paste text
- Add compliance rules (mandatory/soft)
- Drag-drop file upload
- Form validation
- Auto-save draft (localStorage)

**Flow:**
1. User fills job title + description
2. Upload JD file OR paste JD text
3. (Optional) Add filter requirements
4. Submit → Backend creates job → Redirect to job detail page

---

#### Job Detail Page ([src/app/jobs/[id]/page.tsx](frontend/src/app/jobs/[id]/page.tsx))

**Features:**
- Display job metadata (title, status, created date)
- Show JD analysis (skills, requirements, weighting)
- HR recommendations (if any)
- Resume upload section
- Real-time processing progress
- Ranked candidate table (after processing)

**Tabs:**
1. **Overview**: Job info + JD analysis
2. **Resumes**: List of uploaded resumes
3. **Scores**: Ranked candidate table
4. **Insights**: AI-generated HR notes

---

### 2. Resume Management

#### Resume Uploader ([src/components/resumes/ResumeUploader.tsx](frontend/src/components/resumes/ResumeUploader.tsx))

**Features:**
- Bulk upload (drag-drop or file picker)
- Progress bar per file
- Error handling (invalid format, size limit)
- Preview uploaded files before submission
- Auto-trigger processing after upload

**Supported Formats:**
- PDF (`.pdf`)
- DOCX (`.docx`, `.doc`)

**Example:**
```tsx
import { useCallback } from 'react';
import { useDropzone } from 'react-dropzone';
import { useResumes } from '@/hooks/useResumes';

export function ResumeUploader({ jobId }: { jobId: string }) {
  const { uploadResumes, uploading } = useResumes(jobId);
  
  const onDrop = useCallback(async (files: File[]) => {
    await uploadResumes(files);
  }, [uploadResumes]);
  
  const { getRootProps, getInputProps, isDragActive } = useDropzone({
    onDrop,
    accept: {
      'application/pdf': ['.pdf'],
      'application/vnd.openxmlformats-officedocument.wordprocessingml.document': ['.docx']
    },
    maxSize: 10 * 1024 * 1024, // 10MB
  });
  
  return (
    <div {...getRootProps()} className="border-2 border-dashed p-8 text-center cursor-pointer">
      <input {...getInputProps()} />
      {isDragActive ? (
        <p>Drop files here...</p>
      ) : (
        <p>Drag & drop resumes, or click to select files</p>
      )}
      {uploading && <p>Uploading...</p>}
    </div>
  );
}
```

---

#### Resume List ([src/components/resumes/ResumeList.tsx](frontend/src/components/resumes/ResumeList.tsx))

**Features:**
- Table view with columns: Name, Status, Date
- Click to view details (modal)
- Status badges (pending, processing, success, failed)
- Delete resume option

---

### 3. Candidate Scoring & Ranking

#### Score Table ([src/components/scores/ScoreTable.tsx](frontend/src/components/scores/ScoreTable.tsx))

**Columns:**
1. **Rank** (final_ranking)
2. **Candidate Name**
3. **Composite Score** (weighted average)
4. **Hard Requirements** (Pass/Fail badge)
5. **Keyword Score**
6. **Semantic Score**
7. **Project Score**
8. **Actions** (View details, Download resume)

**Sorting:**
- Default: Sort by `final_ranking` (ascending)
- Can sort by any column (composite score, keyword score, etc.)

**Example:**
```tsx
import { useScores } from '@/hooks/useScores';
import { Badge } from '@/components/ui/badge';

export function ScoreTable({ jobId }: { jobId: string }) {
  const { scores, loading } = useScores(jobId);
  
  if (loading) return <div>Loading scores...</div>;
  
  return (
    <table>
      <thead>
        <tr>
          <th>Rank</th>
          <th>Candidate</th>
          <th>Score</th>
          <th>Hard Reqs</th>
        </tr>
      </thead>
      <tbody>
        {scores.map(score => (
          <tr key={score._id}>
            <td>{score.final_ranking}</td>
            <td>{score.candidate_name}</td>
            <td>{score.composite_score.toFixed(1)}</td>
            <td>
              <Badge variant={score.hard_requirements.passed ? 'success' : 'destructive'}>
                {score.hard_requirements.passed ? 'Pass' : 'Fail'}
              </Badge>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

---

#### Score Breakdown ([src/components/scores/ScoreBreakdown.tsx](frontend/src/components/scores/ScoreBreakdown.tsx))

**Details View (Modal/Drawer):**
- **Hard Requirements**: List of pass/fail checks
- **Keyword Match**: Matched vs. missing keywords
- **Semantic Similarity**: Section-wise similarity scores
- **Project Relevance**: Relevant projects highlighted
- **LLM Explanation**: AI-generated ranking rationale

---

### 4. Real-Time Progress Tracking

#### Progress Component ([src/components/common/ProgressTracker.tsx](frontend/src/components/common/ProgressTracker.tsx))

**Display:**
- Progress bar (0-100%)
- Current stage name
- Status message
- Estimated time remaining (optional)

**Example:**
```tsx
import { useSSE } from '@/hooks/useSSE';
import { Progress } from '@/components/ui/progress';

export function ProgressTracker({ jobId }: { jobId: string }) {
  const { progress, stage, message } = useSSE(jobId);
  
  return (
    <div className="space-y-2">
      <Progress value={progress} />
      <div className="text-sm text-muted-foreground">
        <p><strong>{stage}</strong></p>
        <p>{message}</p>
      </div>
    </div>
  );
}
```

---

## 🎨 Component Library (shadcn/ui)

### Button Component ([src/components/ui/button.tsx](frontend/src/components/ui/button.tsx))

**Variants:**
- `default`: Primary button
- `destructive`: Delete/cancel actions
- `outline`: Secondary button
- `ghost`: Minimal button
- `link`: Text link button

**Sizes:**
- `sm`: Small button
- `default`: Medium button
- `lg`: Large button
- `icon`: Icon-only button

**Usage:**
```tsx
import { Button } from '@/components/ui/button';

<Button variant="default" size="lg">
  Create Job
</Button>

<Button variant="outline" size="sm">
  Cancel
</Button>

<Button variant="destructive">
  Delete Job
</Button>
```

---

### Dialog Component ([src/components/ui/dialog.tsx](frontend/src/components/ui/dialog.tsx))

**Usage (Modal):**
```tsx
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog';

<Dialog>
  <DialogTrigger asChild>
    <Button>View Details</Button>
  </DialogTrigger>
  <DialogContent>
    <DialogHeader>
      <DialogTitle>Candidate Details</DialogTitle>
    </DialogHeader>
    <div>
      {/* Content here */}
    </div>
  </DialogContent>
</Dialog>
```

---

### Tabs Component ([src/components/ui/tabs.tsx](frontend/src/components/ui/tabs.tsx))

**Usage:**
```tsx
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';

<Tabs defaultValue="overview">
  <TabsList>
    <TabsTrigger value="overview">Overview</TabsTrigger>
    <TabsTrigger value="resumes">Resumes</TabsTrigger>
    <TabsTrigger value="scores">Scores</TabsTrigger>
  </TabsList>
  
  <TabsContent value="overview">
    {/* Overview content */}
  </TabsContent>
  
  <TabsContent value="resumes">
    {/* Resumes content */}
  </TabsContent>
  
  <TabsContent value="scores">
    {/* Scores content */}
  </TabsContent>
</Tabs>
```

---

## 🔗 API Integration

### API Client ([src/lib/api.ts](frontend/src/lib/api.ts))

**Wrapper around `fetch` with:**
- Base URL configuration
- Error handling
- Response parsing
- TypeScript types

**Example:**
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:3001/api';

export async function fetchJobs(params?: { page?: number; limit?: number; status?: string }) {
  const query = new URLSearchParams(params as any).toString();
  const res = await fetch(`${API_URL}/jobs?${query}`);
  
  if (!res.ok) {
    throw new Error(`Failed to fetch jobs: ${res.statusText}`);
  }
  
  return res.json();
}

export async function createJob(data: { title: string; description?: string; jd_text?: string }) {
  const res = await fetch(`${API_URL}/jobs`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  });
  
  if (!res.ok) {
    const error = await res.json();
    throw new Error(error.message || 'Failed to create job');
  }
  
  return res.json();
}

export async function uploadResumes(groupId: string, files: File[]) {
  const formData = new FormData();
  formData.append('groupId', groupId);
  files.forEach(file => formData.append('files', file));
  
  const res = await fetch(`${API_URL}/resumes`, {
    method: 'POST',
    body: formData,
  });
  
  if (!res.ok) {
    throw new Error('Failed to upload resumes');
  }
  
  return res.json();
}
```

---

### Custom Hooks

#### useJobs Hook ([src/hooks/useJobs.ts](frontend/src/hooks/useJobs.ts))

**API:**
```typescript
const { jobs, loading, error, createJob, deleteJob, refetch } = useJobs();

// Fetch all jobs
const jobs: Job[];

// Create new job
await createJob({ title: 'Senior Engineer', jd_text: '...' });

// Delete job
await deleteJob(jobId);

// Refetch data
refetch();
```

---

#### useResumes Hook ([src/hooks/useResumes.ts](frontend/src/hooks/useResumes.ts))

**API:**
```typescript
const { resumes, loading, uploadResumes, deleteResume } = useResumes(jobId);

// Upload resumes
await uploadResumes([file1, file2, ...]);

// Delete resume
await deleteResume(resumeId);
```

---

#### useScores Hook ([src/hooks/useScores.ts](frontend/src/hooks/useScores.ts))

**API:**
```typescript
const { scores, loading, error, refetch } = useScores(jobId);

// scores is sorted by final_ranking
scores.forEach(score => {
  console.log(score.candidate_name, score.composite_score);
});
```

---

## 📡 Real-Time Updates

### SSE Hook ([src/hooks/useSSE.ts](frontend/src/hooks/useSSE.ts))

**Implementation:**
```typescript
import { useEffect, useState } from 'react';

interface ProgressData {
  percent: number;
  stage: string;
  message: string;
}

export function useSSE(jobId: string) {
  const [progress, setProgress] = useState<ProgressData>({ percent: 0, stage: '', message: '' });
  const [connected, setConnected] = useState(false);
  
  useEffect(() => {
    const eventSource = new EventSource(`${API_URL}/sse/job/${jobId}`);
    
    eventSource.addEventListener('progress', (e) => {
      const data = JSON.parse(e.data);
      setProgress(data);
    });
    
    eventSource.addEventListener('complete', (e) => {
      console.log('Job completed:', e.data);
      eventSource.close();
    });
    
    eventSource.addEventListener('error', (e) => {
      console.error('SSE error:', e);
      eventSource.close();
    });
    
    eventSource.onopen = () => setConnected(true);
    
    return () => {
      eventSource.close();
    };
  }, [jobId]);
  
  return { progress, connected };
}
```

**Usage:**
```tsx
const { progress } = useSSE(jobId);

return (
  <div>
    <Progress value={progress.percent} />
    <p>{progress.message}</p>
  </div>
);
```

---

## 🎨 Styling System

### TailwindCSS Configuration ([tailwind.config.ts](frontend/tailwind.config.ts))

**Custom Theme:**
```typescript
export default {
  theme: {
    extend: {
      colors: {
        primary: {
          50: '#f0f9ff',
          100: '#e0f2fe',
          500: '#0ea5e9',
          900: '#0c4a6e',
        },
        secondary: { ... },
        accent: { ... },
      },
      fontFamily: {
        sans: ['Inter', 'system-ui', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
      animation: {
        'spin-slow': 'spin 3s linear infinite',
        'fade-in': 'fadeIn 0.3s ease-in',
      },
    },
  },
};
```

---

### Utility Function: `cn()` ([src/lib/utils.ts](frontend/src/lib/utils.ts))

**Merge Tailwind classes safely:**
```typescript
import { clsx, type ClassValue } from 'clsx';
import { twMerge } from 'tailwind-merge';

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}
```

**Usage:**
```tsx
import { cn } from '@/lib/utils';

<div className={cn(
  'p-4 rounded-lg',
  isActive && 'bg-primary text-white',
  isDisabled && 'opacity-50 cursor-not-allowed'
)}>
  Content
</div>
```

---

## 🛠️ Development Guide

### Run Development Server

```bash
cd frontend
npm install
npm run dev

# Opens at http://localhost:3000
```

---

### Add New Page

1. Create file in `src/app/`:
```tsx
// src/app/admin/page.tsx
export default function AdminPage() {
  return <div>Admin Dashboard</div>;
}
```

2. Access at: `http://localhost:3000/admin`

---

### Add New Component

1. Create component file:
```tsx
// src/components/jobs/JobStats.tsx
export function JobStats({ job }) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <div>Total Resumes: {job.total_resumes}</div>
      <div>Processed: {job.processed_resumes}</div>
      <div>Status: {job.status}</div>
    </div>
  );
}
```

2. Use in page:
```tsx
import { JobStats } from '@/components/jobs/JobStats';

<JobStats job={job} />
```

---

### Add shadcn/ui Component

```bash
# Install a new component
npx shadcn-ui@latest add dropdown-menu

# Component will be added to src/components/ui/dropdown-menu.tsx
```

---

### Environment Variables

**Build-time variables** (accessed on client):
```bash
# .env.local
NEXT_PUBLIC_API_URL=http://localhost:3001/api
```

**Usage:**
```typescript
const API_URL = process.env.NEXT_PUBLIC_API_URL;
```

**Important**: Must prefix with `NEXT_PUBLIC_` to expose to browser

---

## 🚀 Build & Deployment

### Production Build

```bash
# Local build
npm run build
npm start

# Docker build
docker build -t kreeda-frontend:latest -f Dockerfile .

# Run container
docker run -d -p 3000:3000 \
  -e NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api \
  kreeda-frontend:latest
```

---

### Environment-Specific Builds

**Development:**
```bash
NEXT_PUBLIC_API_URL=http://localhost:3001/api npm run dev
```

**Staging:**
```bash
NEXT_PUBLIC_API_URL=https://staging-api.yourdomain.com/api npm run build
```

**Production:**
```bash
NEXT_PUBLIC_API_URL=https://api.yourdomain.com/api npm run build
```

---

### Performance Optimization

**Next.js built-in:**
- Automatic code splitting
- Image optimization (next/image)
- Font optimization
- Route prefetching
- Static generation where possible

**Manual optimizations:**
- Lazy load heavy components:
```tsx
import dynamic from 'next/dynamic';

const HeavyChart = dynamic(() => import('./HeavyChart'), {
  loading: () => <p>Loading chart...</p>,
  ssr: false
});
```

- Use React Server Components for data fetching:
```tsx
// app/jobs/page.tsx (Server Component)
async function JobsPage() {
  const jobs = await fetchJobs(); // Direct API call on server
  return <JobList jobs={jobs} />;
}
```

---

## 🧪 Testing (Optional Setup)

### Unit Tests (Jest + React Testing Library)

**Install:**
```bash
npm install -D jest @testing-library/react @testing-library/jest-dom
```

**Example:**
```tsx
// __tests__/components/JobCard.test.tsx
import { render, screen } from '@testing-library/react';
import { JobCard } from '@/components/jobs/JobCard';

test('renders job title', () => {
  const job = { _id: '1', title: 'Test Job', status: 'pending' };
  render(<JobCard job={job} />);
  
  expect(screen.getByText('Test Job')).toBeInTheDocument();
});
```

---

### E2E Tests (Playwright)

**Install:**
```bash
npm install -D @playwright/test
```

**Example:**
```typescript
// e2e/jobs.spec.ts
import { test, expect } from '@playwright/test';

test('create new job', async ({ page }) => {
  await page.goto('/jobs/new');
  await page.fill('[name="title"]', 'Senior Engineer');
  await page.click('button[type="submit"]');
  
  await expect(page).toHaveURL(/\/jobs\/\w+/);
});
```

---

## 📱 Responsive Design

**Breakpoints (Tailwind):**
- `sm`: 640px
- `md`: 768px
- `lg`: 1024px
- `xl`: 1280px
- `2xl`: 1536px

**Example:**
```tsx
<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
  {/* 1 column on mobile, 2 on tablet, 3 on desktop */}
</div>
```

---

## 🔧 Troubleshooting

### "Module not found" error
```bash
# Clear Next.js cache
rm -rf .next
npm run dev
```

---

### Build fails with "Out of memory"
```bash
# Increase Node memory
NODE_OPTIONS=--max-old-space-size=4096 npm run build
```

---

### Hot reload not working
```bash
# Check if polling is needed (Docker on Windows/Mac)
# next.config.ts
export default {
  webpack: (config) => {
    config.watchOptions = {
      poll: 1000,
      aggregateTimeout: 300,
    };
    return config;
  },
};
```

---

**Last Updated**: February 5, 2026
**Version**: 1.0.0
