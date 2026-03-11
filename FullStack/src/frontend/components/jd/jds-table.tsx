/**
 * JDs Table Component
 * Displays list of uploaded job descriptions with pagination
 */

'use client';

import { formatDistanceToNow } from 'date-fns';
import { ChevronLeft, ChevronRight } from 'lucide-react';
import { Button } from '@/frontend/components/ui/button';

export interface JD {
  _id: string;
  fileName: string;
  originalFileName: string;
  status: 'uploaded' | 'processing' | 'completed' | 'failed';
  uploadedAt: string;
}

interface JDsTableProps {
  jds: JD[];
  page: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onJDClick: (jdId: string) => void;
  selectedJDId?: string;
}

export function JDsTable({
  jds,
  page,
  totalPages,
  onPageChange,
  onJDClick,
  selectedJDId,
}: JDsTableProps) {
  const getStatusBadge = (status: JD['status']) => {
    const styles = {
      uploaded:   'bg-gray-100 text-gray-800 dark:bg-gray-800 dark:text-gray-300',
      processing: 'bg-blue-100 text-blue-800 dark:bg-blue-900/30 dark:text-blue-400',
      completed:  'bg-green-100 text-green-800 dark:bg-green-900/30 dark:text-green-400',
      failed:     'bg-red-100 text-red-800 dark:bg-red-900/30 dark:text-red-400',
    };

    return (
      <span className={`px-2 py-1 text-xs font-medium rounded-full ${styles[status]}`}>
        {status.charAt(0).toUpperCase() + status.slice(1)}
      </span>
    );
  };

  if (jds.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-muted-foreground">No job descriptions uploaded yet</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Table */}
      <div className="rounded-lg border overflow-x-auto">
        <table className="w-full min-w-[600px]">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4 font-medium text-sm whitespace-nowrap">File Name</th>
              <th className="text-left p-4 font-medium text-sm whitespace-nowrap">Status</th>
              <th className="text-left p-4 font-medium text-sm whitespace-nowrap">Uploaded</th>
            </tr>
          </thead>
          <tbody>
            {jds.map((jd) => (
              <tr
                key={jd._id}
                onClick={() => onJDClick(jd._id)}
                className={`border-t cursor-pointer transition-colors hover:bg-muted/50 ${
                  selectedJDId === jd._id ? 'bg-muted' : ''
                }`}
              >
                <td className="p-4">
                  <div className="flex flex-col max-w-[400px]">
                    <span className="text-sm font-medium truncate" title={jd.fileName}>
                      {jd.fileName}
                    </span>
                    <span className="text-xs text-muted-foreground truncate" title={jd.originalFileName}>
                      {jd.originalFileName}
                    </span>
                  </div>
                </td>
                <td className="p-4">{getStatusBadge(jd.status)}</td>
                <td className="p-4">
                  <span className="text-sm text-muted-foreground whitespace-nowrap">
                    {formatDistanceToNow(new Date(jd.uploadedAt), { addSuffix: true })}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Pagination */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between">
          <p className="text-sm text-muted-foreground">
            Page {page} of {totalPages}
          </p>
          <div className="flex gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page - 1)}
              disabled={page <= 1}
            >
              <ChevronLeft className="h-4 w-4" />
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => onPageChange(page + 1)}
              disabled={page >= totalPages}
            >
              <ChevronRight className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
