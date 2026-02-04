import { Response } from 'express';
import { EventEmitter } from 'events';

interface SSEClient {
  id: string;
  jobId: string;
  res: Response;
}

interface ProgressUpdate {
  stage: string;
  percent: number;
  message: string;
  timestamp: string;
}

/**
 * Server-Sent Events Service
 * Manages SSE connections and broadcasts progress updates to connected clients
 */
class SSEService extends EventEmitter {
  private clients: Map<string, SSEClient[]> = new Map();

  /**
   * Add a new SSE client connection
   */
  addClient(jobId: string, res: Response): string {
    const clientId = `${jobId}_${Date.now()}_${Math.random()}`;
    
    // Setup SSE headers
    res.writeHead(200, {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no', // Disable buffering for Nginx
    });

    // Send initial connection message
    res.write(`data: ${JSON.stringify({ type: 'connected', jobId, clientId })}\n\n`);

    // Add client to the list
    if (!this.clients.has(jobId)) {
      this.clients.set(jobId, []);
    }
    
    const clients = this.clients.get(jobId)!;
    clients.push({ id: clientId, jobId, res });

    console.log(`✅ SSE client connected: ${clientId} for job ${jobId}`);
    console.log(`📊 Total clients for job ${jobId}: ${clients.length}`);

    // Handle client disconnect
    res.on('close', () => {
      this.removeClient(clientId, jobId);
    });

    // Keep-alive ping every 30 seconds
    const keepAliveInterval = setInterval(() => {
      if (res.writableEnded) {
        clearInterval(keepAliveInterval);
        return;
      }
      res.write(`:keepalive\n\n`);
    }, 30000);

    res.on('close', () => clearInterval(keepAliveInterval));

    return clientId;
  }

  /**
   * Remove a client connection
   */
  removeClient(clientId: string, jobId: string): void {
    const clients = this.clients.get(jobId);
    if (!clients) return;

    const index = clients.findIndex(c => c.id === clientId);
    if (index !== -1) {
      clients.splice(index, 1);
      console.log(`❌ SSE client disconnected: ${clientId}`);
      console.log(`📊 Remaining clients for job ${jobId}: ${clients.length}`);

      if (clients.length === 0) {
        this.clients.delete(jobId);
        console.log(`🗑️  No more clients for job ${jobId}, cleaned up`);
      }
    }
  }

  /**
   * Send progress update to all clients listening to a specific job
   */
  sendProgress(jobId: string, progress: ProgressUpdate): void {
    const clients = this.clients.get(jobId);
    if (!clients || clients.length === 0) {
      console.log(`⚠️  No clients connected for job ${jobId}, skipping progress update`);
      return;
    }

    const message = {
      type: 'progress',
      jobId,
      ...progress,
    };

    console.log(`📤 Sending progress to ${clients.length} client(s) for job ${jobId}:`, progress);

    clients.forEach(client => {
      try {
        if (!client.res.writableEnded) {
          client.res.write(`data: ${JSON.stringify(message)}\n\n`);
        }
      } catch (error) {
        console.error(`❌ Failed to send to client ${client.id}:`, error);
        this.removeClient(client.id, jobId);
      }
    });
  }

  /**
   * Send completion message to all clients
   */
  sendComplete(jobId: string, success: boolean, error?: string): void {
    const clients = this.clients.get(jobId);
    if (!clients || clients.length === 0) return;

    const message = {
      type: 'complete',
      jobId,
      success,
      error,
      timestamp: new Date().toISOString(),
    };

    console.log(`✅ Sending completion to ${clients.length} client(s) for job ${jobId}`);

    clients.forEach(client => {
      try {
        if (!client.res.writableEnded) {
          client.res.write(`data: ${JSON.stringify(message)}\n\n`);
          client.res.end();
        }
      } catch (error) {
        console.error(`❌ Failed to send completion to client ${client.id}:`, error);
      }
    });

    // Clean up all clients for this job
    this.clients.delete(jobId);
  }

  /**
   * Get count of connected clients for a job
   */
  getClientCount(jobId: string): number {
    return this.clients.get(jobId)?.length || 0;
  }

  /**
   * Get total number of connected clients across all jobs
   */
  getTotalClientCount(): number {
    let total = 0;
    this.clients.forEach(clients => {
      total += clients.length;
    });
    return total;
  }
}

// Export singleton instance
export const sseService = new SSEService();
