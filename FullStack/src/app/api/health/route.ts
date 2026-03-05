/**
 * Health Check API Route
 * GET /api/health
 * 
 * Simple health check endpoint for the API
 */

import { NextResponse } from 'next/server';

export async function GET() {
  return NextResponse.json({
    status: 'ok',
    timestamp: new Date().toISOString(),
    service: 'Kreeda Hiring Bot API',
  });
}
