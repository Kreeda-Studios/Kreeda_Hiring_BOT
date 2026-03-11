/**
 * JD Processor Page
 * Upload, view, and manage job descriptions
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { AppLayout } from '@/frontend/components/layout';
import { JDUploadDialog } from '@/frontend/components/jd/upload-dialog';
import { JDsTable } from '@/frontend/components/jd/jds-table';
import { JDPreviewPanel } from '@/frontend/components/jd/preview-panel';
import type { JD } from '@/frontend/components/jd/jds-table';

export default function JDProcessorPage() {
  const [jds, setJDs] = useState<JD[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedJDId, setSelectedJDId] = useState<string | null>(null);

  const fetchJDs = useCallback(async () => {
    try {
      setLoading(true);
      const response = await fetch(`/api/jd/list?page=${page}&limit=10`);
      if (!response.ok) throw new Error('Failed to fetch JDs');

      const result = await response.json();
      setJDs(result.data.jds);
      setTotalPages(result.data.totalPages);
    } catch (error) {
      console.error('Error fetching JDs:', error);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchJDs();
  }, [fetchJDs]);

  // Auto-refresh every 10 s to pick up processing status changes
  useEffect(() => {
    const interval = setInterval(fetchJDs, 10_000);
    return () => clearInterval(interval);
  }, [fetchJDs]);

  const handleUploadComplete = () => {
    setPage(1);
    fetchJDs();
  };

  const handleJDClick = (jdId: string) => {
    setSelectedJDId(jdId);
  };

  const handleClosePreview = () => {
    setSelectedJDId(null);
  };

  return (
    <AppLayout>
      <div className="h-[calc(100vh-4rem)] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b bg-background shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">JD Processor</h1>
              <p className="text-muted-foreground">
                Upload and process job descriptions with AI-powered analysis
              </p>
            </div>
            <JDUploadDialog onUploadComplete={handleUploadComplete} />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* JDs Table */}
          <div
            className={`transition-all duration-300 ${
              selectedJDId ? 'w-1/2' : 'w-full'
            } overflow-y-auto p-6`}
          >
            <div className="rounded-lg border bg-card">
              <div className="p-6 border-b">
                <h2 className="text-xl font-semibold">Job Descriptions</h2>
              </div>
              <div className="p-6">
                {loading ? (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">Loading…</p>
                  </div>
                ) : (
                  <JDsTable
                    jds={jds}
                    page={page}
                    totalPages={totalPages}
                    onPageChange={setPage}
                    onJDClick={handleJDClick}
                    selectedJDId={selectedJDId || undefined}
                  />
                )}
              </div>
            </div>
          </div>

          {/* Preview Panel */}
          {selectedJDId && (
            <div className="w-1/2 overflow-hidden border-l">
              <JDPreviewPanel jdId={selectedJDId} onClose={handleClosePreview} />
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
