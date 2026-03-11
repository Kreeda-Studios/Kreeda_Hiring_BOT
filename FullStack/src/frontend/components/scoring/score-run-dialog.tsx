/**
 * Score Run Dialog
 * Step 1: Pick a JD  →  Step 2: Pick resumes  →  Submit
 */

'use client';

import { useState, useEffect } from 'react';
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/frontend/components/ui/dialog';
import { Button } from '@/frontend/components/ui/button';
import { BarChart2, Loader2, ChevronLeft, ChevronRight } from 'lucide-react';

interface JD {
  _id: string;
  originalFileName: string;
  fileName: string;
  status: string;
}

interface ResumeItem {
  _id: string;
  originalFileName: string;
  fileName: string;
  status: string;
  profile?: { name?: string };
}

interface ScoreRunDialogProps {
  onRunCreated: () => void;
}

export function ScoreRunDialog({ onRunCreated }: ScoreRunDialogProps) {
  const [open, setOpen] = useState(false);
  const [step, setStep] = useState<1 | 2>(1);

  // JD selection
  const [jds, setJDs] = useState<JD[]>([]);
  const [jdLoading, setJDLoading] = useState(false);
  const [selectedJD, setSelectedJD] = useState<JD | null>(null);

  // Resume selection
  const [resumes, setResumes] = useState<ResumeItem[]>([]);
  const [resumeLoading, setResumeLoading] = useState(false);
  const [selectedResumeIds, setSelectedResumeIds] = useState<Set<string>>(new Set());
  const [resumePage, setResumePage] = useState(1);
  const [resumeTotalPages, setResumeTotalPages] = useState(1);

  // Submission
  const [submitting, setSubmitting] = useState(false);
  const [submitError, setSubmitError] = useState<string | null>(null);

  // ── Load JDs (completed only) ──
  useEffect(() => {
    if (!open) return;
    const load = async () => {
      setJDLoading(true);
      try {
        const res = await fetch('/api/jd/list?status=completed&limit=100');
        const data = await res.json();
        setJDs(data.data?.jds ?? []);
      } finally {
        setJDLoading(false);
      }
    };
    load();
  }, [open]);

  // ── Load resumes (completed only, paginated) ──
  useEffect(() => {
    if (!open || step !== 2) return;
    const load = async () => {
      setResumeLoading(true);
      try {
        const res = await fetch(`/api/resume/list?status=completed&page=${resumePage}&limit=15`);
        const data = await res.json();
        setResumes(data.data?.resumes ?? []);
        setResumeTotalPages(data.data?.totalPages ?? 1);
      } finally {
        setResumeLoading(false);
      }
    };
    load();
  }, [open, step, resumePage]);

  const toggleResume = (id: string) => {
    setSelectedResumeIds((prev) => {
      const next = new Set(prev);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  };

  const handleSubmit = async () => {
    if (!selectedJD || selectedResumeIds.size === 0) return;
    setSubmitting(true);
    setSubmitError(null);
    try {
      const res = await fetch('/api/score/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          jdId: selectedJD._id,
          resumeIds: Array.from(selectedResumeIds),
        }),
      });
      if (!res.ok) throw new Error('Failed to start scoring run');
      onRunCreated();
      handleClose();
    } catch (e) {
      setSubmitError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    setOpen(false);
    setStep(1);
    setSelectedJD(null);
    setSelectedResumeIds(new Set());
    setSubmitError(null);
    setResumePage(1);
  };

  return (
    <Dialog open={open} onOpenChange={(v) => (v ? setOpen(true) : handleClose())}>
      <DialogTrigger asChild>
        <Button>
          <BarChart2 className="h-4 w-4 mr-2" />
          Run Scoring
        </Button>
      </DialogTrigger>

      <DialogContent className="sm:max-w-160 max-h-[80vh] flex flex-col overflow-hidden">
        <DialogHeader>
          <DialogTitle>New Scoring Run</DialogTitle>
          <DialogDescription>
            {step === 1
              ? 'Step 1 of 2 — Select a processed Job Description'
              : `Step 2 of 2 — Select resumes to rank (${selectedResumeIds.size} selected)`}
          </DialogDescription>
        </DialogHeader>

        {/* ── Step 1: JD selection ── */}
        {step === 1 && (
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {jdLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : jds.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-10">
                No processed JDs found. Upload and process a JD first.
              </p>
            ) : (
              jds.map((jd) => (
                <div
                  key={jd._id}
                  onClick={() => setSelectedJD(jd)}
                  className={`p-3 rounded-lg border cursor-pointer transition-colors ${
                    selectedJD?._id === jd._id
                      ? 'border-primary bg-primary/5'
                      : 'hover:bg-muted/50'
                  }`}
                >
                  <p className="text-sm font-medium truncate">
                    {jd.originalFileName || jd.fileName}
                  </p>
                </div>
              ))
            )}
          </div>
        )}

        {/* ── Step 2: Resume selection ── */}
        {step === 2 && (
          <div className="flex-1 overflow-y-auto space-y-2 pr-1">
            {resumeLoading ? (
              <div className="flex justify-center py-10">
                <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
              </div>
            ) : resumes.length === 0 ? (
              <p className="text-sm text-muted-foreground text-center py-10">
                No processed resumes found.
              </p>
            ) : (
              <>
                {resumes.map((r) => (
                  <label
                    key={r._id}
                    className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
                      selectedResumeIds.has(r._id)
                        ? 'border-primary bg-primary/5'
                        : 'hover:bg-muted/50'
                    }`}
                  >
                    <input
                      type="checkbox"
                      className="h-4 w-4 accent-primary"
                      checked={selectedResumeIds.has(r._id)}
                      onChange={() => toggleResume(r._id)}
                    />
                    <div className="min-w-0">
                      <p className="text-sm font-medium truncate">
                        {r.profile?.name || r.originalFileName || r.fileName}
                      </p>
                      {r.profile?.name && (
                        <p className="text-xs text-muted-foreground truncate">{r.originalFileName}</p>
                      )}
                    </div>
                  </label>
                ))}
                {/* Pagination */}
                {resumeTotalPages > 1 && (
                  <div className="flex items-center justify-between pt-2">
                    <span className="text-xs text-muted-foreground">
                      Page {resumePage} of {resumeTotalPages}
                    </span>
                    <div className="flex gap-2">
                      <Button variant="outline" size="sm" disabled={resumePage <= 1}
                        onClick={() => setResumePage((p) => p - 1)}>
                        <ChevronLeft className="h-3 w-3" />
                      </Button>
                      <Button variant="outline" size="sm" disabled={resumePage >= resumeTotalPages}
                        onClick={() => setResumePage((p) => p + 1)}>
                        <ChevronRight className="h-3 w-3" />
                      </Button>
                    </div>
                  </div>
                )}
              </>
            )}
          </div>
        )}

        {submitError && (
          <p className="text-sm text-red-500 mt-1">{submitError}</p>
        )}

        {/* ── Footer actions ── */}
        <div className="flex justify-between items-center pt-3 border-t shrink-0">
          <Button variant="outline" onClick={handleClose}>
            Cancel
          </Button>
          <div className="flex gap-2">
            {step === 2 && (
              <Button variant="outline" onClick={() => setStep(1)}>
                <ChevronLeft className="h-4 w-4 mr-1" /> Back
              </Button>
            )}
            {step === 1 && (
              <Button disabled={!selectedJD} onClick={() => setStep(2)}>
                Next <ChevronRight className="h-4 w-4 ml-1" />
              </Button>
            )}
            {step === 2 && (
              <Button
                disabled={selectedResumeIds.size === 0 || submitting}
                onClick={handleSubmit}
              >
                {submitting ? (
                  <><Loader2 className="h-4 w-4 mr-2 animate-spin" /> Starting…</>
                ) : (
                  <><BarChart2 className="h-4 w-4 mr-2" /> Start Scoring</>
                )}
              </Button>
            )}
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}
