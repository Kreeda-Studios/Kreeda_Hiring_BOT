/**
 * JD Statistics API Route
 * GET /api/jd/stats
 */

import { NextResponse } from 'next/server';
import { JDService } from '@/backend/services/jd.service';

export async function GET() {
  try {
    const stats = await JDService.getStats();

    return NextResponse.json({
      success: true,
      data: stats,
    });

  } catch (error) {
    console.error('Error fetching JD stats:', error);
    return NextResponse.json(
      { error: 'Failed to fetch JD stats', details: error instanceof Error ? error.message : 'Unknown error' },
      { status: 500 }
    );
  }
}
