/**
 * Resume List API Route
 * GET /api/resume/list
 */

import { NextRequest, NextResponse } from 'next/server';
import { ResumeService } from '@/backend/services/resume.service';

export async function GET(request: NextRequest) {
  try {
    const searchParams = request.nextUrl.searchParams;
    
    // Parse pagination params
    const page = parseInt(searchParams.get('page') || '1', 10);
    const limit = parseInt(searchParams.get('limit') || '10', 10);
    
    // Parse filter params
    const statusParam = searchParams.get('status');
    const status = (statusParam && statusParam !== 'all') 
      ? statusParam as 'uploaded' | 'processing' | 'completed' | 'failed'
      : null;
    const search = searchParams.get('search') || undefined;

    // Build filters
    const filters: any = {};
    if (status) {
      filters.status = status;
    }
    if (search) {
      filters.search = search;
    }

    // Get paginated resumes
    const result = await ResumeService.getResumes(filters, { page, limit });
    
    console.log('List API - Total resumes:', result.resumes.length);
    if (result.resumes.length > 0) {
      console.log('First resume ID:', result.resumes[0]._id);
      console.log('First resume ID type:', typeof result.resumes[0]._id);
    }

    return NextResponse.json({
      success: true,
      data: result,
    });

  } catch (error) {
    console.error('Get resumes error:', error);
    return NextResponse.json(
      { 
        error: 'Failed to fetch resumes', 
        details: error instanceof Error ? error.message : 'Unknown error' 
      },
      { status: 500 }
    );
  }
}
