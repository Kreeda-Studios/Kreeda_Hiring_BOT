/**
 * MinIO S3 Client Configuration
 */

import { S3Client } from '@aws-sdk/client-s3';
import { Client as MinioClient } from 'minio';

const MINIO_ENDPOINT = process.env.MINIO_ENDPOINT || 'localhost:9000';
const MINIO_PUBLIC_ENDPOINT = process.env.MINIO_PUBLIC_ENDPOINT || 'localhost:9000';
const MINIO_ACCESS_KEY = process.env.MINIO_ACCESS_KEY || 'minioadmin';
const MINIO_SECRET_KEY = process.env.MINIO_SECRET_KEY || 'minioadmin';
const MINIO_USE_SSL = process.env.MINIO_USE_SSL === 'true';
const MINIO_BUCKET_RESUMES = process.env.MINIO_BUCKET_RESUMES || 'resumes';
const MINIO_BUCKET_DOCUMENTS = process.env.MINIO_BUCKET_DOCUMENTS || 'documents';

const [host, portStr] = MINIO_ENDPOINT.split(':');
const port = parseInt(portStr, 10);

export const s3Client = new S3Client({
  endpoint: `http${MINIO_USE_SSL ? 's' : ''}://${MINIO_ENDPOINT}`,
  region: 'us-east-1',
  credentials: {
    accessKeyId: MINIO_ACCESS_KEY,
    secretAccessKey: MINIO_SECRET_KEY,
  },
  forcePathStyle: true,
});

// MinIO native client for streaming operations
export const minioClient = new MinioClient({
  endPoint: host,
  port: port,
  useSSL: MINIO_USE_SSL,
  accessKey: MINIO_ACCESS_KEY,
  secretKey: MINIO_SECRET_KEY,
});

export const minioConfig = {
  endpoint: MINIO_ENDPOINT,
  host,
  port,
  useSSL: MINIO_USE_SSL,
  accessKey: MINIO_ACCESS_KEY,
  secretKey: MINIO_SECRET_KEY,
  buckets: {
    resumes: MINIO_BUCKET_RESUMES,
    documents: MINIO_BUCKET_DOCUMENTS,
  },
};

/**
 * Get public URL for a file
 * Returns Next.js proxy URL to keep MinIO internal
 * Easy to change to direct S3 URLs when migrating to AWS/external S3
 */
export function getPublicUrl(bucket: string, key: string): string {
  const baseUrl = process.env.NEXT_PUBLIC_BASE_URL || 'http://localhost:3000';
  return `${baseUrl}/api/files/${bucket}/${key}`;
  
  // For future direct S3 access, just uncomment this:
  // const protocol = MINIO_USE_SSL ? 'https' : 'http';
  // return `${protocol}://${MINIO_PUBLIC_ENDPOINT}/${bucket}/${key}`;
}
