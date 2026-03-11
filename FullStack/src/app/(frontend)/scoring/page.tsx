/**
 * Scoring Page
 * Select a JD + resumes, generate AI-powered candidate rankings
 */

'use client';

import { useState, useEffect, useCallback } from 'react';
import { AppLayout } from '@/frontend/components/layout';
import { ScoreRunDialog, ScoreRunsTable, ScoreRunDetail } from '@/frontend/components/scoring';

interface ScoreRunSummary {
  _id: string;
  jdFileName: string;
  totalResumes: number;
  completedCount: number;
  failedCount: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  createdAt: string;
}

export default function ScoringPage() {
  const [runs, setRuns] = useState<ScoreRunSummary[]>([]);
  const [page, setPage] = useState(1);
  const [totalPages, setTotalPages] = useState(1);
  const [loading, setLoading] = useState(true);
  const [selectedRunId, setSelectedRunId] = useState<string | null>(null);

  const fetchRuns = useCallback(async () => {
    try {
      setLoading(true);
      const res = await fetch(`/api/score/runs?page=${page}&limit=20`);
      if (res.ok) {
        const result = await res.json();
        setRuns(result.data?.scoreRuns ?? []);
        setTotalPages(result.data?.totalPages ?? 1);
      }
    } catch (e) {
      console.error('Failed to fetch score runs:', e);
    } finally {
      setLoading(false);
    }
  }, [page]);

  useEffect(() => {
    fetchRuns();
  }, [fetchRuns]);

  // Auto-refresh while any run is in a live state
  useEffect(() => {
    const hasLive = runs.some(
      (r) => r.status === 'queued' || r.status === 'processing'
    );
    if (!hasLive) return;
    const timer = setInterval(fetchRuns, 5000);
    return () => clearInterval(timer);
  }, [runs, fetchRuns]);

  const handleRunCreated = () => {
    setPage(1);
    fetchRuns();
  };

  const handleSelectRun = (run: ScoreRunSummary) => {
    setSelectedRunId((prev) => (prev === run._id ? null : run._id));
  };

  return (
    <AppLayout>
      <div className="h-[calc(100vh-4rem)] overflow-hidden flex flex-col">
        {/* Header */}
        <div className="p-6 border-b bg-background shrink-0">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="text-3xl font-bold tracking-tight">Scoring</h1>
              <p className="text-muted-foreground">
                Rank candidates against a job description with AI-powered analysis
              </p>
            </div>
            <ScoreRunDialog onRunCreated={handleRunCreated} />
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-hidden flex">
          {/* Runs list */}
          <div
            className={`transition-all duration-300 ${
              selectedRunId ? 'w-1/2' : 'w-full'
            } overflow-y-auto p-6`}
          >
            <div className="rounded-lg border bg-card">
              <div className="p-6 border-b">
                <h2 className="text-xl font-semibold">Scoring Runs</h2>
                <p className="text-sm text-muted-foreground mt-0.5">
                  Click a run to see individual resume scores
                </p>
              </div>
              <div>
                {loading && runs.length === 0 ? (
                  <div className="text-center py-12">
                    <p className="text-muted-foreground">Loading…</p>
                  </div>
                ) : (
                  <>
                    <ScoreRunsTable
                      runs={runs}
                      selectedRunId={selectedRunId}
                      onSelectRun={handleSelectRun}
                    />
                    {totalPages > 1 && (
                      <div className="flex items-center justify-between p-4 border-t">
                        <span className="text-xs text-muted-foreground">
                          Page {page} of {totalPages}
                        </span>
                        <div className="flex gap-2">
                          <button
                            className="px-3 py-1 rounded border text-xs disabled:opacity-50"
                            disabled={page <= 1}
                            onClick={() => setPage((p) => p - 1)}
                          >
                            Prev
                          </button>
                          <button
                            className="px-3 py-1 rounded border text-xs disabled:opacity-50"
                            disabled={page >= totalPages}
                            onClick={() => setPage((p) => p + 1)}
                          >
                            Next
                          </button>
                        </div>
                      </div>
                    )}
                  </>
                )}
              </div>
            </div>
          </div>

          {/* Detail panel */}
          {selectedRunId && (
            <div className="w-1/2 overflow-hidden border-l">
              <ScoreRunDetail runId={selectedRunId} />
            </div>
          )}
        </div>
      </div>
    </AppLayout>
  );
}
