import express, { Express } from 'express';
import { createServer, Server as HttpServer } from 'http';
import cors from 'cors';
import helmet from 'helmet';
import morgan from 'morgan';
import compression from 'compression';
import rateLimit from 'express-rate-limit';
import dotenv from 'dotenv';
import Database from './config/database';
import config from './config';

// Import routes
import jobRoutes from './routes/jobs';
import resumeRoutes from './routes/resumes';
import resumeGroupRoutes from './routes/resumeGroups';
import processRoutes from './routes/process';
import scoresRoutes from './routes/scores';
import updatesRoutes from './routes/updates';
import statusRoutes from './routes/status';
import sseRoutes from './routes/sse';

// Import queue health check
import { checkQueueHealth } from './config/queue';

dotenv.config();

class App {
  public app: Express;
  public server: HttpServer;
  private database: Database;

  constructor() {
    this.app = express();
    this.server = createServer(this.app);
    this.database = Database.getInstance();
    this.initializeMiddleware();
    this.initializeRoutes();
    this.initializeErrorHandling();
  }

  private initializeMiddleware(): void {
    // Security middleware
    this.app.use(helmet());
    
    // Rate limiting
    const limiter = rateLimit({
      windowMs: 15 * 60 * 1000, // 15 minutes
      max: 1000, // Limit each IP to 1000 requests per windowMs
      message: 'Too many requests from this IP, please try again later.'
    });
    this.app.use(limiter);

    // CORS configuration
    this.app.use(cors({
      origin: config.corsOrigins,
      credentials: true
    }));

    // Compression
    this.app.use(compression());

    // Logging
    if (config.nodeEnv === 'development') {
      this.app.use(morgan('dev'));
    } else {
      this.app.use(morgan('combined'));
    }

    // Body parsing
    this.app.use(express.json({ limit: '100mb' }));
    this.app.use(express.urlencoded({ extended: true, limit: '100mb' }));
    
    // Serve static files from public directory
    this.app.use(express.static('public'));
  }

  private initializeRoutes(): void {
    // Health check
    this.app.get('/api/health', async (req, res) => {
      const queueHealthy = await checkQueueHealth();
      res.json({
        status: 'OK',
        timestamp: new Date().toISOString(),
        environment: config.nodeEnv,
        services: {
          database: this.database.getConnectionStatus() ? 'connected' : 'disconnected',
          redis: queueHealthy ? 'connected' : 'disconnected'
        }
      });
    });

    // API routes
    this.app.use('/api/jobs', jobRoutes);
    this.app.use('/api/resumes', resumeRoutes);
    this.app.use('/api/resume-groups', resumeGroupRoutes);
    this.app.use('/api/procesS', processRoutes);
    this.app.use('/api/scores', scoresRoutes);
    this.app.use('/api/status', statusRoutes);
    this.app.use('/api/sse', sseRoutes);
    this.app.use('/api/updates', updatesRoutes);

    // 404 handler
    this.app.use('*', (req, res) => {
      res.status(404).json({
        error: 'Not Found',
        message: `Route ${req.originalUrl} not found`,
        timestamp: new Date().toISOString()
      });
    });
  }

  private initializeErrorHandling(): void {
    // Global error handler
    this.app.use((error: Error, req: express.Request, res: express.Response, next: express.NextFunction) => {
      console.error('❌ Global error handler:', error);

      const status = (error as any).status || 500;
      const message = config.nodeEnv === 'production' ? 'Internal Server Error' : error.message;

      res.status(status).json({
        error: 'Server Error',
        message,
        timestamp: new Date().toISOString(),
        ...(config.nodeEnv === 'development' && { stack: error.stack })
      });
    });
  }

  public async start(): Promise<void> {
    try {
      // Connect to database
      await this.database.connect();

      // Start server
      this.server.listen(config.port, () => {
        console.log(`🚀 Server running on port ${config.port}`);
        console.log(`📱 Environment: ${config.nodeEnv}`);
        console.log(`🌐 CORS Origins: ${config.corsOrigins.join(', ')}`);
        console.log(`💾 Database: ${this.database.getConnectionStatus() ? 'Connected' : 'Disconnected'}`);
      });

    } catch (error) {
      console.error('❌ Failed to start server:', error);
      process.exit(1);
    }
  }

  public async stop(): Promise<void> {
    await this.database.disconnect();
  }
}

export default App;