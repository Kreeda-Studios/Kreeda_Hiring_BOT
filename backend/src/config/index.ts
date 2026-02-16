import dotenv from 'dotenv';

dotenv.config();

interface AppConfig {
  port: number;
  nodeEnv: string;
  mongoUri: string;
  jwtSecret: string;
  corsOrigins: string[];
  uploadPath: string;
  maxFileSize: number;
}

const config: AppConfig = {
  port: parseInt(process.env.PORT!, 10),
  nodeEnv: process.env.NODE_ENV!,
  mongoUri: process.env.MONGODB_URI!,
  jwtSecret: process.env.JWT_SECRET!,
  corsOrigins: (process.env.CORS_ORIGINS || 'http://localhost:3000').split(','),
  uploadPath: process.env.UPLOAD_PATH!,  // Relative path for storage
  maxFileSize: parseInt(process.env.MAX_FILE_SIZE!, 10), // 10MB
};

// Validate required config
const requiredEnvVars = [
  'MONGODB_URI',
  'JWT_SECRET', 
  'NODE_ENV',
  'PORT',
  'CORS_ORIGINS',
  'UPLOAD_PATH',
  'MAX_FILE_SIZE'
];
const missingEnvVars = requiredEnvVars.filter(envVar => !process.env[envVar]);

if (missingEnvVars.length > 0) {
  console.error(`❌ Missing required environment variables: ${missingEnvVars.join(', ')}`);
  console.error('❌ Please ensure all required variables are set in your .env file');
  process.exit(1);
}

export default config;