/**
 * Resume Processor Page
 * Upload, view, and manage resumes
 */

'use client';

import { useState, useEffect } from 'react';
import { AppLayout } from "@/frontend/components/layout";
import { UploadDialog } from '@/frontend/components/resume/upload-dialog';
import { ResumesTable } from '@/frontend/components/resume/resumes-table';
import { PreviewPanel } from '@/frontend/components/resume/preview-panel';

interface Resume {
  _id: string;
  fileName: string;
  originalFileName: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  uploadedAt: string;
  profile?: {
    name?: string;
  };
}

export default function ResumeProcessorPage() {
  const [resumes, setResumes] = useState<Resume[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [selectedResumeId, setSelectedResumeId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  const fetchResumes = async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/resume/list?page=${page}&limit=10`);
      if (response.ok) {
        const result = await response.json();
        console.log('Fetched resumes:', result.data.resumes);
        setResumes(result.data.resumes);
        setTotalPages(result.data.totalPages);
      }
    } catch (error) {
      console.error('Failed to fetch resumes:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchResumes();
  }, [page]);

  const handleUploadComplete = () => {
    setPage(1);
    fetchResumes();
  };

  const handleResumeClick = (resumeId: string) => {
    console.log('Selected resume ID:', resumeId);
    setSelectedResumeId(resumeId);
  };

  const handleClosePreview = () => {
    setSelectedResumeId(null);
  };

  return (
    <AppLayout>
      <div className="h-[calc(100vh-4rem)] overflow-hidden flex flex-col">
        {/* Header with Upload Button */}
        <div className="p-6 border-b bg-background shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Resume Processor</h1>
              <p className="text-muted-foreground">
                Upload and process resumes with AI-powered analysis
              </p>
            </div>
            <UploadDialog onUploadComplete={handleUploadComplete} />
          </div>
        </div>

        {/* Content Area */}
        <div className="flex-1 overflow-hidden flex">
          {/* Resumes Table */}
          <div className={`transition-all duration-300 ${selectedResumeId ? 'w-1/2' : 'w-full'} overflow-y-auto p-6`}>
            <div className="rounded-lg border bg-card">
              <div className="p-6 border-b">
                <h2 className="text-xl font-semibold">Resumes</h2>
              </div>
              <div className="p-6">
                {loading ? (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">Loading...</p>
                  </div>
                ) : (
                  <ResumesTable
                    resumes={resumes}
                    page={page}
                    totalPages={totalPages}
                    onPageChange={setPage}
                    onResumeClick={handleResumeClick}
                    selectedResumeId={selectedResumeId || undefined}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Preview Panel */}
          {selectedResumeId && (
            <div className="w-1/2 shrink-0 overflow-hidden">
              <PreviewPanel 
                resumeId={selectedResumeId} 
                onClose={handleClosePreview}
              />
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
