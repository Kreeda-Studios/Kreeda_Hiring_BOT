/**
 * List Score Runs
 * GET /api/score/runs?page=1&limit=20
 *
 * Returns a paginated list of parent ScoreRun records (one per submission).
 * Each run includes aggregate progress counts.
 */

import { NextRequest, NextResponse } from 'next/server';
import { ScoreService } from '@/backend/services/score.service';

export async function GET(request: NextRequest) {
  try {
    const { searchParams } = new URL(request.url);
    const page  = parseInt(searchParams.get('page')  || '1',  10);
    const limit = parseInt(searchParams.get('limit') || '20', 10);

    const { runs, total, totalPages } = await ScoreService.getScoreRuns(page, limit);

    return NextResponse.json({
      success: true,
      data: { scoreRuns: runs, total, totalPages },
    });
  } catch (error) {
    console.error('Error listing score runs:', error);
    return NextResponse.json(
      { error: 'Failed to fetch score runs', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
