/**
 * JD Preview Panel
 * Shows the JD PDF and (when processed) extracted structured data
 */

'use client';

import { useEffect, useState } from 'react';
import { X, Loader2, FileText } from 'lucide-react';
import { Button } from '@/frontend/components/ui/button';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/frontend/components/ui/tabs';
import { PDFViewer } from '@/frontend/components/resume/pdf-viewer';

interface JDPreviewPanelProps {
  jdId: string;
  onClose: () => void;
}

interface JDData {
  jd: {
    _id: string;
    fileName: string;
    originalFileName: string;
    status: 'uploaded' | 'processing' | 'completed' | 'failed';
    uploadedAt: string;
    processedAt?: string;
    processingError?: string;
    extractedData?: Record<string, unknown>;
  };
  fileUrl: string;
}

export function JDPreviewPanel({ jdId, onClose }: JDPreviewPanelProps) {
  const [data, setData] = useState<JDData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchJD = async () => {
      try {
        setLoading(true);
        setError(null);

        const response = await fetch(`/api/jd/${jdId}`);
        if (!response.ok) throw new Error('Failed to fetch JD');

        const result = await response.json();
        setData(result.data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load JD');
      } finally {
        setLoading(false);
      }
    };

    fetchJD();
  }, [jdId]);

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center bg-background border-l">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  if (error) {
    return (
      <div className="h-full flex items-center justify-center bg-background border-l">
        <div className="text-center space-y-2">
          <p className="text-red-500">{error}</p>
          <Button variant="outline" onClick={onClose}>Close</Button>
        </div>
      </div>
    );
  }

  if (!data) return null;

  const { jd, fileUrl } = data;

  const statusColors = {
    uploaded:   'text-gray-600 bg-gray-100 dark:bg-gray-800',
    processing: 'text-blue-600 bg-blue-100 dark:bg-blue-900/30',
    completed:  'text-green-600 bg-green-100 dark:bg-green-900/30',
    failed:     'text-red-600 bg-red-100 dark:bg-red-900/30',
  };

  return (
    <div className="h-full flex flex-col bg-background border-l overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <FileText className="h-5 w-5 text-muted-foreground shrink-0" />
          <div className="min-w-0">
            <p className="text-sm font-medium truncate" title={jd.originalFileName}>
              {jd.originalFileName}
            </p>
            <span
              className={`inline-block text-xs px-2 py-0.5 rounded-full font-medium mt-0.5 ${statusColors[jd.status]}`}
            >
              {jd.status}
            </span>
          </div>
        </div>
        <Button variant="ghost" size="sm" onClick={onClose} className="shrink-0 ml-2">
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-hidden">
        <Tabs defaultValue="pdf" className="h-full flex flex-col">
          <TabsList className="mx-4 mt-3 shrink-0 w-fit">
            <TabsTrigger value="pdf">PDF</TabsTrigger>
            <TabsTrigger value="analysis">Analysis</TabsTrigger>
          </TabsList>

          {/* PDF Tab */}
          <TabsContent value="pdf" className="flex-1 overflow-hidden m-0 mt-3">
            {fileUrl ? (
              <PDFViewer url={fileUrl} />
            ) : (
              <div className="h-full flex items-center justify-center text-muted-foreground">
                <p className="text-sm">PDF not available</p>
              </div>
            )}
          </TabsContent>

          {/* Analysis Tab */}
          <TabsContent value="analysis" className="flex-1 overflow-y-auto p-4 m-0 mt-3">
            {jd.status === 'uploaded' && (
              <div className="text-center py-10 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                <p className="text-sm">Queued for processing…</p>
              </div>
            )}

            {jd.status === 'processing' && (
              <div className="text-center py-10 text-muted-foreground">
                <Loader2 className="h-6 w-6 animate-spin mx-auto mb-2" />
                <p className="text-sm">Processing with AI…</p>
              </div>
            )}

            {jd.status === 'failed' && (
              <div className="rounded-lg border border-red-200 bg-red-50 dark:bg-red-900/10 p-4">
                <p className="text-sm font-medium text-red-700">Processing failed</p>
                {jd.processingError && (
                  <p className="text-xs text-red-600 mt-1">{jd.processingError}</p>
                )}
              </div>
            )}

            {jd.status === 'completed' && jd.extractedData && (
              <div className="space-y-4">
                <p className="text-sm font-medium text-muted-foreground">Extracted Data</p>
                {/* Placeholder — team will render structured fields here */}
                <pre className="text-xs bg-muted rounded-lg p-4 overflow-auto whitespace-pre-wrap">
                  {JSON.stringify(jd.extractedData, null, 2)}
                </pre>
              </div>
            )}
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
