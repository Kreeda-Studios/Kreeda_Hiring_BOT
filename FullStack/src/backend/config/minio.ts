/**
 * MinIO S3 Client Configuration
 * S3-compatible object storage for file uploads
 */

import { S3Client } from '@aws-sdk/client-s3';

const MINIO_ENDPOINT = process.env.MINIO_ENDPOINT || 'localhost:9000';
const MINIO_ACCESS_KEY = process.env.MINIO_ACCESS_KEY || 'minioadmin';
const MINIO_SECRET_KEY = process.env.MINIO_SECRET_KEY || 'minioadmin123';
const MINIO_USE_SSL = process.env.MINIO_USE_SSL === 'true';

// Extract host and port from endpoint
const [host, portStr] = MINIO_ENDPOINT.split(':');
const port = parseInt(portStr || '9000', 10);

export const s3Client = new S3Client({
  endpoint: `http${MINIO_USE_SSL ? 's' : ''}://${MINIO_ENDPOINT}`,
  region: 'us-east-1', // MinIO doesn't require a specific region
  credentials: {
    accessKeyId: MINIO_ACCESS_KEY,
    secretAccessKey: MINIO_SECRET_KEY,
  },
  forcePathStyle: true, // Required for MinIO
});

export const minioConfig = {
  endpoint: MINIO_ENDPOINT,
  host,
  port,
  useSSL: MINIO_USE_SSL,
  accessKey: MINIO_ACCESS_KEY,
  secretKey: MINIO_SECRET_KEY,
  // Bucket names
  buckets: {
    resumes: process.env.MINIO_BUCKET_RESUMES || 'resumes',
    documents: process.env.MINIO_BUCKET_DOCUMENTS || 'documents',
  },
};

// Helper function to get public URL
export function getPublicUrl(bucket: string, key: string): string {
  const protocol = MINIO_USE_SSL ? 'https' : 'http';
  return `${protocol}://${MINIO_ENDPOINT}/${bucket}/${key}`;
}
