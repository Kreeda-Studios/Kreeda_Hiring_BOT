/**
 * JD List API Route
 * GET /api/jd/list
 *
 * Returns a paginated list of JDs with optional filtering
 */

import { NextRequest, NextResponse } from 'next/server';
import { JDService } from '@/backend/services/jd.service';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);

    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '10', 10);
    const status = searchParams.get('status') as 'uploaded' | 'processing' | 'completed' | 'failed' | null;
    const search = searchParams.get('search') || undefined;

    const result = await JDService.getJDs(
      { status: status || undefined, search },
      { page, limit }
    );

    return NextResponse.json({
      success: true,
      data: result,
    });

  } catch (error) {
    console.error('Error listing JDs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch JDs', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
