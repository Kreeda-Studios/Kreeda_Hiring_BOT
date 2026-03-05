/**
 * PDF Viewer Component
 * Professional PDF viewing experience with zoom, pan, and navigation
 */

'use client';

import { memo } from 'react';
import { Worker, Viewer, SpecialZoomLevel } from '@react-pdf-viewer/core';
import { defaultLayoutPlugin } from '@react-pdf-viewer/default-layout';
import '@react-pdf-viewer/core/lib/styles/index.css';
import '@react-pdf-viewer/default-layout/lib/styles/index.css';

interface PDFViewerProps {
  url: string;
}

const PDFViewerComponent = ({ url }: PDFViewerProps) => {
  // Create plugin instance at top level, not inside useMemo
  const defaultLayoutPluginInstance = defaultLayoutPlugin({
    sidebarTabs: (defaultTabs) => [
      defaultTabs[0], // Thumbnails
      defaultTabs[1], // Bookmarks
    ],
    toolbarPlugin: {
      fullScreenPlugin: {
        onEnterFullScreen: (zoom) => {
          zoom(SpecialZoomLevel.PageFit);
        },
        onExitFullScreen: (zoom) => {
          zoom(SpecialZoomLevel.PageWidth);
        },
      },
    },
  });

  return (
    <div className="h-full w-full bg-muted/10">
      <Worker workerUrl="https://unpkg.com/pdfjs-dist@3.11.174/build/pdf.worker.min.js">
        <Viewer
          fileUrl={url}
          plugins={[defaultLayoutPluginInstance]}
          defaultScale={SpecialZoomLevel.PageWidth}
        />
      </Worker>
    </div>
  );
};

// Memoize the component to prevent re-renders when URL hasn't changed
export const PDFViewer = memo(PDFViewerComponent, (prevProps, nextProps) => {
  // Only re-render if the URL actually changed
  return prevProps.url === nextProps.url;
});
