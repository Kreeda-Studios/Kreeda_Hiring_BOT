'use client';

interface ScoreRun {
  _id: string;
  jdFileName: string;
  totalResumes: number;
  completedCount: number;
  failedCount: number;
  status: 'queued' | 'processing' | 'completed' | 'failed';
  createdAt: string;
}

const STATUS_STYLES: Record<string, string> = {
  queued:     'bg-yellow-100 text-yellow-800',
  processing: 'bg-blue-100 text-blue-800',
  completed:  'bg-green-100 text-green-800',
  failed:     'bg-red-100 text-red-800',
};

interface ScoreRunsTableProps {
  runs: ScoreRun[];
  selectedRunId?: string | null;
  onSelectRun: (run: ScoreRun) => void;
}

export function ScoreRunsTable({ runs, selectedRunId, onSelectRun }: ScoreRunsTableProps) {
  if (runs.length === 0) {
    return (
      <div className="flex items-center justify-center h-40 text-muted-foreground text-sm">
        No scoring runs yet. Click &quot;Run Scoring&quot; to get started.
      </div>
    );
  }

  return (
    <div className="overflow-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b text-muted-foreground">
            <th className="text-left py-3 px-4 font-medium">Job Description</th>
            <th className="text-center py-3 px-4 font-medium">Resumes</th>
            <th className="text-center py-3 px-4 font-medium">Progress</th>
            <th className="text-center py-3 px-4 font-medium">Status</th>
            <th className="text-right py-3 px-4 font-medium">Date</th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => {
            const done  = run.completedCount + run.failedCount;
            const total = run.totalResumes;
            const pct   = total > 0 ? Math.round((done / total) * 100) : 0;

            return (
              <tr
                key={run._id}
                onClick={() => onSelectRun(run)}
                className={`border-b cursor-pointer transition-colors hover:bg-muted/50 ${
                  selectedRunId === run._id ? 'bg-muted' : ''
                }`}
              >
                {/* JD name */}
                <td className="py-3 px-4">
                  <span className="truncate max-w-72 block font-medium" title={run.jdFileName}>
                    {run.jdFileName}
                  </span>
                </td>

                {/* N resumes */}
                <td className="py-3 px-4 text-center tabular-nums text-muted-foreground">
                  {total}
                </td>

                {/* Progress bar + count */}
                <td className="py-3 px-4">
                  <div className="flex items-center gap-2 min-w-28">
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
                    <span className="text-xs tabular-nums text-muted-foreground w-10 text-right">
                      {done}/{total}
                    </span>
                  </div>
                </td>

                {/* Status badge */}
                <td className="py-3 px-4 text-center">
                  <span
                    className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium capitalize ${
                      STATUS_STYLES[run.status] ?? ''
                    }`}
                  >
                    {run.status}
                  </span>
                </td>

                {/* Date */}
                <td className="py-3 px-4 text-right text-muted-foreground text-xs">
                  {new Date(run.createdAt).toLocaleDateString(undefined, {
                    month: 'short',
                    day:   'numeric',
                    year:  'numeric',
                  })}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}
