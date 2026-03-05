/**
 * Resume Stats API Route
 * GET /api/resume/stats
 */

import { NextResponse } from 'next/server';
import { ResumeService } from '@/backend/services/resume.service';

export async function GET() {
  try {
    const stats = await ResumeService.getStats();

    return NextResponse.json({
      success: true,
      data: stats,
    });

  } catch (error) {
    console.error('Get stats error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to fetch stats', 
        details: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    );
  }
}
