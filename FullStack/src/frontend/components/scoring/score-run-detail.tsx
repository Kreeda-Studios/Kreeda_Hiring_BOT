'use client';

import { useEffect, useState, useCallback } from 'react';
import { Loader2, AlertCircle } from 'lucide-react';

// ─── Types ────────────────────────────────────────────────────────────────────

interface ScoreRun {
  _id: string;
  jdFileName: string;
  totalResumes: number;
  completedCount: number;
  failedCount: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  createdAt: string;
  completedAt?: string;
}

interface ScorePair {
  _id: string;
  resumeFileName: string;
  candidateName?: string;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  errorMessage?: string;
  overallScore?: number;
  skillMatch?: number;
  experienceMatch?: number;
  techStackMatch?: number;
  projectRelevance?: number;
  responsibilityMatch?: number;
  impactStrength?: number;
  educationMatch?: number;
  criticalSkillGapScore?: number;
  missingSkills: string[];
  strengths: string[];
  concerns: string[];
  createdAt: string;
}

// ─── Constants ────────────────────────────────────────────────────────────────

const SUB_SCORES: { key: keyof ScorePair; label: string; weight: string }[] = [
  { key: 'skillMatch',            label: 'Skill Match',          weight: '30%' },
  { key: 'responsibilityMatch',   label: 'Responsibility Match', weight: '20%' },
  { key: 'experienceMatch',       label: 'Experience Match',     weight: '15%' },
  { key: 'techStackMatch',        label: 'Tech Stack Match',     weight: '10%' },
  { key: 'projectRelevance',      label: 'Project Relevance',    weight: '10%' },
  { key: 'impactStrength',        label: 'Impact Strength',      weight: '10%' },
  { key: 'educationMatch',        label: 'Education Match',      weight: '3%'  },
  { key: 'criticalSkillGapScore', label: 'Critical Skill Gap',   weight: '2%'  },
];

const STATUS_STYLES: Record<string, string> = {
  queued:     'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed:  'bg-green-100 text-green-800',
  failed:     'bg-red-100 text-red-800',
};

// ─── Mini components ──────────────────────────────────────────────────────────

function ScoreBar({ value }: { value?: number }) {
  const pct = value !== undefined ? Math.round(value * 100) : null;
  const color =
    pct === null  ? 'bg-muted'
    : pct >= 70   ? 'bg-green-500'
    : pct >= 40   ? 'bg-yellow-500'
    :                'bg-red-500';

  return (
    <div className="flex items-center gap-2">
      <div className="flex-1 bg-muted rounded-full h-1.5 overflow-hidden">
        <div
          className={`h-full rounded-full transition-all ${color}`}
          style={{ width: pct !== null ? `${pct}%` : '0%' }}
        />
      </div>
      <span className="text-xs tabular-nums w-8 text-right text-muted-foreground">
        {pct !== null ? `${pct}%` : '—'}
      </span>
    </div>
  );
}

function PairRow({
  pair,
  selected,
  onClick,
}: {
  pair: ScorePair;
  selected: boolean;
  onClick: () => void;
}) {
  const pct = pair.overallScore !== undefined ? Math.round(pair.overallScore * 100) : null;

  return (
    <div
      onClick={onClick}
      className={`flex items-center gap-3 p-3 rounded-lg border cursor-pointer transition-colors ${
        selected ? 'border-primary bg-primary/5' : 'hover:bg-muted/50'
      }`}
    >
      {/* Score circle */}
      <div
        className={`shrink-0 w-12 h-12 rounded-full flex items-center justify-center text-sm font-bold border-2 ${
          pct === null         ? 'border-muted text-muted-foreground'
          : pct >= 70          ? 'border-green-400 text-green-700 bg-green-50'
          : pct >= 40          ? 'border-yellow-400 text-yellow-700 bg-yellow-50'
          :                      'border-red-400 text-red-700 bg-red-50'
        }`}
      >
        {pct !== null ? `${pct}%` : '—'}
      </div>

      {/* Candidate info */}
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate">
          {pair.candidateName || pair.resumeFileName}
        </p>
        {pair.candidateName && (
          <p className="text-xs text-muted-foreground truncate">{pair.resumeFileName}</p>
        )}
        {pair.errorMessage && (
          <p className="text-xs text-red-500 truncate mt-0.5">{pair.errorMessage}</p>
        )}
      </div>

      {/* Status badge */}
      <span
        className={`shrink-0 inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${
          STATUS_STYLES[pair.status] ?? ''
        }`}
      >
        {pair.status === 'processing' && (
          <Loader2 className="h-3 w-3 animate-spin mr-1" />
        )}
        {pair.status}
      </span>
    </div>
  );
}

function PairDetail({ pair }: { pair: ScorePair }) {
  const pct = pair.overallScore !== undefined ? Math.round(pair.overallScore * 100) : null;

  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-5 border-t">
      {/* Header */}
      <div className="flex items-start gap-3">
        <div
          className={`shrink-0 w-14 h-14 rounded-full flex items-center justify-center text-base font-bold border-2 ${
            pct === null  ? 'border-muted text-muted-foreground'
            : pct >= 70   ? 'border-green-400 text-green-700 bg-green-50'
            : pct >= 40   ? 'border-yellow-400 text-yellow-700 bg-yellow-50'
            :                'border-red-400 text-red-700 bg-red-50'
          }`}
        >
          {pct !== null ? `${pct}%` : '—'}
        </div>
        <div className="min-w-0">
          <p className="font-semibold text-base truncate">
            {pair.candidateName || pair.resumeFileName}
          </p>
          {pair.candidateName && (
            <p className="text-xs text-muted-foreground truncate">{pair.resumeFileName}</p>
          )}
          <p className="text-xs text-muted-foreground">{pct !== null ? 'overall match' : pair.status}</p>
        </div>
      </div>

      {pair.status === 'completed' && (
        <>
          {/* Score breakdown */}
          <div>
            <p className="text-xs font-medium text-muted-foreground uppercase tracking-wide mb-2">
              Score Breakdown
            </p>
            <div className="space-y-2">
              {SUB_SCORES.map(({ key, label, weight }) => (
                <div key={key} className="grid grid-cols-[1fr_auto_130px] gap-2 items-center">
                  <span className="text-sm truncate">{label}</span>
                  <span className="text-[10px] text-muted-foreground">{weight}</span>
                  <ScoreBar value={pair[key] as number | undefined} />
                </div>
              ))}
            </div>
          </div>

          {/* Strengths */}
          {pair.strengths?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-green-700 uppercase tracking-wide mb-1">Strengths</p>
              <ul className="space-y-1">
                {pair.strengths.map((s, i) => (
                  <li key={i} className="text-sm text-muted-foreground flex gap-1.5">
                    <span className="text-green-500 shrink-0 mt-0.5">✓</span>
                    {s}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Concerns */}
          {pair.concerns?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-red-700 uppercase tracking-wide mb-1">Concerns</p>
              <ul className="space-y-1">
                {pair.concerns.map((c, i) => (
                  <li key={i} className="text-sm text-muted-foreground flex gap-1.5">
                    <span className="text-red-400 shrink-0 mt-0.5">✗</span>
                    {c}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {/* Missing skills */}
          {pair.missingSkills?.length > 0 && (
            <div>
              <p className="text-xs font-medium text-orange-700 uppercase tracking-wide mb-1">Missing Skills</p>
              <div className="flex flex-wrap gap-1.5">
                {pair.missingSkills.map((s, i) => (
                  <span key={i} className="px-2 py-0.5 rounded-full bg-orange-50 text-orange-700 text-xs border border-orange-200">
                    {s}
                  </span>
                ))}
              </div>
            </div>
          )}
        </>
      )}

      {pair.status === 'failed' && pair.errorMessage && (
        <div className="flex items-start gap-2 text-red-500 text-sm">
          <AlertCircle className="h-4 w-4 mt-0.5 shrink-0" />
          <p>{pair.errorMessage}</p>
        </div>
      )}
    </div>
  );
}

// ─── Main component ───────────────────────────────────────────────────────────

interface ScoreRunDetailProps {
  runId: string;
}

export function ScoreRunDetail({ runId }: ScoreRunDetailProps) {
  const [run, setRun]             = useState<ScoreRun | null>(null);
  const [pairs, setPairs]         = useState<ScorePair[]>([]);
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState<string | null>(null);
  const [selectedPairId, setSelectedPairId] = useState<string | null>(null);

  const loadRun = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`/api/score/runs/${runId}`);
      if (!res.ok) throw new Error('Failed to load scoring run');
      const data = await res.json();
      setRun(data.data?.run ?? null);
      const incoming: ScorePair[] = data.data?.pairs ?? [];
      setPairs(incoming);
      // Auto-select first pair when list first loads
      setSelectedPairId((prev) => prev ?? incoming[0]?._id ?? null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Unknown error');
    } finally {
      setLoading(false);
    }
  }, [runId]);

  useEffect(() => {
    loadRun();
  }, [loadRun]);

  // Auto-refresh while any pair is still live
  useEffect(() => {
    const hasLive = pairs.some(
      (p) => p.status === 'queued' || p.status === 'processing'
    );
    if (!hasLive) return;
    const timer = setInterval(loadRun, 4000);
    return () => clearInterval(timer);
  }, [pairs, loadRun]);

  if (loading && !run) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex flex-col items-center justify-center h-full gap-2 text-red-500">
        <AlertCircle className="h-6 w-6" />
        <p className="text-sm">{error}</p>
      </div>
    );
  }

  if (!run) return null;

  const done        = run.completedCount + run.failedCount;
  const pct         = run.totalResumes > 0 ? Math.round((done / run.totalResumes) * 100) : 0;
  const isLive      = run.status === 'queued' || run.status === 'processing';
  const selectedPair = pairs.find((p) => p._id === selectedPairId) ?? null;

  return (
    <div className="flex flex-col h-full overflow-hidden">
      {/* Run header */}
      <div className="p-4 border-b shrink-0">
        <div className="flex items-start justify-between gap-2">
          <div className="min-w-0 flex-1">
            <h2 className="font-semibold truncate text-base" title={run.jdFileName}>
              {run.jdFileName}
            </h2>
            <p className="text-xs text-muted-foreground mt-0.5">
              {run.totalResumes} resume{run.totalResumes !== 1 ? 's' : ''} •{' '}
              {done} scored
              {run.failedCount > 0 && (
                <span className="text-red-500"> · {run.failedCount} failed</span>
              )}
            </p>
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {isLive && <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />}
            <span
              className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${
                run.status === 'completed'   ? 'bg-green-100 text-green-800'
                : run.status === 'failed'   ? 'bg-red-100 text-red-800'
                : run.status === 'processing' ? 'bg-blue-100 text-blue-800'
                : 'bg-yellow-100 text-yellow-800'
              }`}
            >
              {run.status}
            </span>
          </div>
        </div>
        {/* Overall progress bar */}
        <div className="mt-2 flex items-center gap-2">
          <div className="flex-1 bg-muted rounded-full h-1.5 overflow-hidden">
            <div
              className={`h-full rounded-full transition-all ${
                run.status === 'failed' ? 'bg-red-500'
                : run.status === 'completed' ? 'bg-green-500'
                : 'bg-blue-500'
              }`}
              style={{ width: `${pct}%` }}
            />
          </div>
          <span className="text-xs tabular-nums text-muted-foreground">{pct}%</span>
        </div>
      </div>

      {/* Split: pair list (left) + pair detail (right) */}
      <div className="flex flex-1 overflow-hidden">
        {/* Pair list */}
        <div className="w-2/5 overflow-y-auto border-r p-3 space-y-2 shrink-0">
          {pairs.map((pair) => (
            <PairRow
              key={pair._id}
              pair={pair}
              selected={selectedPairId === pair._id}
              onClick={() => setSelectedPairId(pair._id)}
            />
          ))}
        </div>

        {/* Pair detail */}
        <div className="flex-1 overflow-hidden flex flex-col">
          {selectedPair ? (
            <PairDetail pair={selectedPair} />
          ) : (
            <div className="flex items-center justify-center h-full text-sm text-muted-foreground">
              Select a candidate to see details
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
