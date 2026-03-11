/**
 * Update Score Pair Status
 * POST /api/score/update-status
 *
 * Called by the Python worker to mark a pair as processing/completed/failed.
 * Body: { scorePairId: string; status: string; error?: string }
 */

import { NextRequest, NextResponse } from 'next/server';
import { ScoreService } from '@/backend/services/score.service';

export async function POST(request: NextRequest) {
  try {
    const body = await request.json();
    const { scorePairId, status, error } = body;

    if (!scorePairId || !status) {
      return NextResponse.json(
        { error: 'scorePairId and status are required' },
        { status: 400 }
      );
    }

    const valid = ['queued', 'processing', 'completed', 'failed'];
    if (!valid.includes(status)) {
      return NextResponse.json(
        { error: `Invalid status. Must be one of: ${valid.join(', ')}` },
        { status: 400 }
      );
    }

    const updated = await ScoreService.updatePairStatus(scorePairId, status, error);
    if (!updated) {
      return NextResponse.json({ error: 'Score pair not found' }, { status: 404 });
    }

    return NextResponse.json({
      success: true,
      data: { scorePairId: updated._id, status: updated.status },
    });
  } catch (error) {
    console.error('Error updating score run status:', error);
    return NextResponse.json(
      { error: 'Failed to update score run status', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
