import { S3Client } from '@aws-sdk/client-s3';
import { Client as MinioClient } from 'minio';

const S3_ENDPOINT = process.env.S3_ENDPOINT || 'localhost:9000';
const S3_ACCESS_KEY = process.env.S3_ACCESS_KEY || 'minioadmin';
const S3_SECRET_KEY = process.env.S3_SECRET_KEY || 'minioadmin';
const S3_USE_SSL = process.env.S3_USE_SSL === 'true';
const S3_REGION = process.env.S3_REGION || 'us-east-1';
const S3_BUCKET_RESUMES = process.env.S3_BUCKET_RESUMES || 'resumes';
const S3_BUCKET_JDS = process.env.S3_BUCKET_JDS || 'jds';

const [host, portStr] = S3_ENDPOINT.split(':');
const port = parseInt(portStr, 10);

// AWS SDK S3 Client for standard operations
export const s3Client = new S3Client({
  endpoint: `http${S3_USE_SSL ? 's' : ''}://${S3_ENDPOINT}`,
  region: S3_REGION,
  credentials: {
    accessKeyId: S3_ACCESS_KEY,
    secretAccessKey: S3_SECRET_KEY,
  },
  forcePathStyle: true, // Required for MinIO and some S3-compatible services
});

// MinIO native client for streaming operations (compatible with AWS S3)
export const minioClient = new MinioClient({
  endPoint: host,
  port: port,
  useSSL: S3_USE_SSL,
  accessKey: S3_ACCESS_KEY,
  secretKey: S3_SECRET_KEY,
});

export const s3Config = {
  endpoint: S3_ENDPOINT,
  host,
  port,
  useSSL: S3_USE_SSL,
  region: S3_REGION,
  accessKey: S3_ACCESS_KEY,
  secretKey: S3_SECRET_KEY,
  buckets: {
    resumes: S3_BUCKET_RESUMES,
    jds: S3_BUCKET_JDS,
  },
};

/**
 * Get public URL for a file
 * Returns Next.js proxy URL to keep S3 internal
 * Easy to change to direct S3 URLs when migrating to AWS S3
 */
export function getPublicUrl(bucket: string, key: string): string {
  const baseUrl = (process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000').replace(/\/$/, '');
  return `${baseUrl}/api/files/${bucket}/${key}`;
  
  // For future direct S3 access, just uncomment this:
  // const protocol = S3_USE_SSL ? 'https' : 'http';
  // return `${protocol}://${S3_PUBLIC_ENDPOINT}/${bucket}/${key}`;
}
