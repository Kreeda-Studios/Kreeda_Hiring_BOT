import { Server as HttpServer } from 'http';
import { Server as SocketIOServer, Socket } from 'socket.io';
import { queues, redisConnection } from '../config/queue';
import { QueueEvents } from 'bullmq';
import { sseService } from './sseService';

interface ProgressData {
  progress: number;
  stage: string;
  message: string;
}

export class WebSocketService {
  private io: SocketIOServer;
  private static instance: WebSocketService;
  private queueEvents: {
    jdProcessing: QueueEvents;
    resumeProcessing: QueueEvents;
    ranking: QueueEvents;
  };

  private constructor(server: HttpServer) {
    this.io = new SocketIOServer(server, {
      cors: {
        origin: process.env.FRONTEND_URL || 'http://localhost:3000',
        methods: ['GET', 'POST'],
        credentials: true
      }
    });

    // Initialize QueueEvents for listening to job events
    this.queueEvents = {
      jdProcessing: new QueueEvents('jd-processing', { connection: redisConnection }),
      resumeProcessing: new QueueEvents('resume-processing', { connection: redisConnection }),
      ranking: new QueueEvents('ranking', { connection: redisConnection })
    };

    this.setupEventListeners();
    this.setupQueueListeners();
  }

  public static initialize(server: HttpServer): WebSocketService {
    if (!WebSocketService.instance) {
      WebSocketService.instance = new WebSocketService(server);
      console.log('✅ WebSocket service initialized');
    }
    return WebSocketService.instance;
  }

  public static getInstance(): WebSocketService {
    if (!WebSocketService.instance) {
      throw new Error('WebSocketService not initialized. Call initialize() first.');
    }
    return WebSocketService.instance;
  }

  private setupEventListeners(): void {
    this.io.on('connection', (socket: Socket) => {
      console.log(`🔌 Client connected: ${socket.id}`);

      // Subscribe to job-specific updates
      socket.on('subscribe:job', (jobId: string) => {
        socket.join(`job:${jobId}`);
        console.log(`📡 Client ${socket.id} subscribed to job:${jobId}`);
      });

      // Unsubscribe from job updates
      socket.on('unsubscribe:job', (jobId: string) => {
        socket.leave(`job:${jobId}`);
        console.log(`📡 Client ${socket.id} unsubscribed from job:${jobId}`);
      });

      // Subscribe to resume-specific updates
      socket.on('subscribe:resume', (resumeId: string) => {
        socket.join(`resume:${resumeId}`);
        console.log(`📡 Client ${socket.id} subscribed to resume:${resumeId}`);
      });

      // Unsubscribe from resume updates
      socket.on('unsubscribe:resume', (resumeId: string) => {
        socket.leave(`resume:${resumeId}`);
        console.log(`📡 Client ${socket.id} unsubscribed from resume:${resumeId}`);
      });

      socket.on('disconnect', () => {
        console.log(`🔌 Client disconnected: ${socket.id}`);
      });
    });
  }

  private setupQueueListeners(): void {
    // JD Processing Queue Listeners
    this.queueEvents.jdProcessing.on('progress', async ({ jobId, data }) => {
      const job = await queues.jdProcessing.getJob(jobId);
      if (!job) return;
      
      const jobDbId = job.data.jobId;
      const progressData: ProgressData = typeof data === 'object' 
        ? data as ProgressData
        : { progress: 0, stage: 'processing', message: String(data) };
      
      const eventData = {
        jobId: jobDbId,
        queueJobId: jobId,
        type: 'jd-processing',
        progress: progressData.progress || 0,
        stage: progressData.stage || 'processing',
        message: progressData.message || 'Processing JD...',
        timestamp: new Date().toISOString()
      };
      
      this.emitToJob(jobDbId, 'jd:progress', eventData);
      
      // Also send to SSE clients
      sseService.sendProgress(jobDbId, {
        stage: eventData.stage,
        percent: eventData.progress,
        message: eventData.message,
        timestamp: eventData.timestamp
      });
    });

    this.queueEvents.jdProcessing.on('completed', async ({ jobId }) => {
      const job = await queues.jdProcessing.getJob(jobId);
      if (!job) return;
      
      const jobDbId = job.data.jobId;
      const eventData = {
        jobId: jobDbId,
        queueJobId: jobId,
        type: 'jd-processing',
        message: 'JD processing completed',
        timestamp: new Date().toISOString()
      };
      
      this.emitToJob(jobDbId, 'jd:completed', eventData);
      
      // Also send to SSE clients
      sseService.sendComplete(jobDbId, true);
    });

    this.queueEvents.jdProcessing.on('failed', async ({ jobId, failedReason }) => {
      const job = await queues.jdProcessing.getJob(jobId);
      if (!job) return;
      
      const jobDbId = job.data.jobId;
      const eventData = {
        jobId: jobDbId,
        queueJobId: jobId,
        type: 'jd-processing',
        error: failedReason,
        timestamp: new Date().toISOString()
      };
      
      this.emitToJob(jobDbId, 'jd:failed', eventData);
      
      // Also send to SSE clients
      sseService.sendComplete(jobDbId, false, failedReason);
    });


    // Resume Processing Queue Listeners
    this.queueEvents.resumeProcessing.on('progress', async ({ jobId, data }) => {
      const job = await queues.resumeProcessing.getJob(jobId);
      if (!job) return;
      
      const resumeId = job.data.resumeId;
      const jobDbId = job.data.jobId;
      const progressData: ProgressData = typeof data === 'object' 
        ? data as ProgressData
        : { progress: 0, stage: 'processing', message: String(data) };
      
      // Emit to both resume and job rooms
      if (resumeId) {
        this.emitToResume(resumeId, 'resume:progress', {
          resumeId,
          jobId: jobDbId,
          queueJobId: jobId,
          type: 'resume-processing',
          progress: progressData.progress || 0,
          stage: progressData.stage || 'processing',
          message: progressData.message || 'Processing resume...',
          timestamp: new Date().toISOString()
        });
      }
      
      if (jobDbId) {
        this.emitToJob(jobDbId, 'resume:progress', {
          resumeId,
          jobId: jobDbId,
          queueJobId: jobId,
          type: 'resume-processing',
          progress: progressData.progress || 0,
          stage: progressData.stage || 'processing',
          message: progressData.message || 'Processing resume...',
          timestamp: new Date().toISOString()
        });
      }
    });

    this.queueEvents.resumeProcessing.on('completed', async ({ jobId }) => {
      const job = await queues.resumeProcessing.getJob(jobId);
      if (!job) return;
      
      const resumeId = job.data.resumeId;
      const jobDbId = job.data.jobId;
      
      if (resumeId) {
        this.emitToResume(resumeId, 'resume:completed', {
          resumeId,
          jobId: jobDbId,
          queueJobId: jobId,
          type: 'resume-processing',
          message: 'Resume processing completed',
          timestamp: new Date().toISOString()
        });
      }
      
      if (jobDbId) {
        this.emitToJob(jobDbId, 'resume:completed', {
          resumeId,
          jobId: jobDbId,
          queueJobId: jobId,
          type: 'resume-processing',
          message: 'Resume processing completed',
          timestamp: new Date().toISOString()
        });
      }
    });

    this.queueEvents.resumeProcessing.on('failed', async ({ jobId, failedReason }) => {
      const job = await queues.resumeProcessing.getJob(jobId);
      if (!job) return;
      
      const resumeId = job.data.resumeId;
      const jobDbId = job.data.jobId;
      
      if (resumeId) {
        this.emitToResume(resumeId, 'resume:failed', {
          resumeId,
          jobId: jobDbId,
          queueJobId: jobId,
          type: 'resume-processing',
          error: failedReason,
          timestamp: new Date().toISOString()
        });
      }
      
      if (jobDbId) {
        this.emitToJob(jobDbId, 'resume:failed', {
          resumeId,
          jobId: jobDbId,
          queueJobId: jobId,
          type: 'resume-processing',
          error: failedReason,
          timestamp: new Date().toISOString()
        });
      }
    });

    // Ranking Queue Listeners
    this.queueEvents.ranking.on('progress', async ({ jobId, data }) => {
      const job = await queues.ranking.getJob(jobId);
      if (!job) return;
      
      const jobDbId = job.data.jobId;
      const progressData: ProgressData = typeof data === 'object' 
        ? data as ProgressData
        : { progress: 0, stage: 'processing', message: String(data) };
      
      this.emitToJob(jobDbId, 'ranking:progress', {
        jobId: jobDbId,
        queueJobId: jobId,
        type: 'ranking',
        progress: progressData.progress || 0,
        stage: progressData.stage || 'processing',
        message: progressData.message || 'Calculating rankings...',
        timestamp: new Date().toISOString()
      });
    });

    this.queueEvents.ranking.on('completed', async ({ jobId }) => {
      const job = await queues.ranking.getJob(jobId);
      if (!job) return;
      
      const jobDbId = job.data.jobId;
      this.emitToJob(jobDbId, 'ranking:completed', {
        jobId: jobDbId,
        queueJobId: jobId,
        type: 'ranking',
        message: 'Ranking completed',
        timestamp: new Date().toISOString()
      });
    });

    this.queueEvents.ranking.on('failed', async ({ jobId, failedReason }) => {
      const job = await queues.ranking.getJob(jobId);
      if (!job) return;
      
      const jobDbId = job.data.jobId;
      this.emitToJob(jobDbId, 'ranking:failed', {
        jobId: jobDbId,
        queueJobId: jobId,
        type: 'ranking',
        error: failedReason,
        timestamp: new Date().toISOString()
      });
    });

    console.log('✅ Queue listeners setup complete');
  }

  // Emit to specific job room
  public emitToJob(jobId: string, event: string, data: any): void {
    this.io.to(`job:${jobId}`).emit(event, data);
  }

  // Emit to specific resume room
  public emitToResume(resumeId: string, event: string, data: any): void {
    this.io.to(`resume:${resumeId}`).emit(event, data);
  }

  // Broadcast to all connected clients
  public broadcast(event: string, data: any): void {
    this.io.emit(event, data);
  }

  // Get connected clients count
  public getConnectedClientsCount(): number {
    return this.io.sockets.sockets.size;
  }
}
