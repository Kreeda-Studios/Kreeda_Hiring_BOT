#!/usr/bin/env python3

import os
import json
import requests
from typing import Dict, Any, Optional
from datetime import datetime

# Backend API configuration
API_BASE_URL = os.getenv('BACKEND_API_URL', os.getenv('API_BASE_URL', 'http://localhost:3001/api'))
BACKEND_API_KEY = os.getenv('BACKEND_API_KEY', '')

# Direct function imports
from a_pdf_extractor import process_resume_file
from b_ai_parser import parse_resume_with_ai
from c_embedding_generator import generate_resume_embeddings
from d_hard_requirements_checker import check_hard_requirements
from e_keyword_scorer import calculate_keyword_scores
from f_semantic_scorer import calculate_semantic_scores
from g_project_scorer import calculate_project_scores
from h_composite_scorer import calculate_composite_score

class ResumeProcessingError(Exception):
    pass

def update_resume_via_api(resume_id: str, update_data: Dict[str, Any]) -> bool:
    """Update resume data via backend API"""
    try:
        headers = {'Content-Type': 'application/json'}
        if BACKEND_API_KEY:
            headers['Authorization'] = f'Bearer {BACKEND_API_KEY}'
        
        response = requests.put(
            f'{API_BASE_URL}/updates/resume/{resume_id}',
            json=update_data,
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        print(f"✅ Updated resume {resume_id} via API")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API call failed for resume {resume_id}: {e}")
        return False
    except Exception as e:
        print(f"❌ Error updating resume {resume_id}: {e}")
        return False

def get_job_via_api(job_id: str) -> Optional[Dict[str, Any]]:
    """Get job details via backend API"""
    try:
        headers = {}
        if BACKEND_API_KEY:
            headers['Authorization'] = f'Bearer {BACKEND_API_KEY}'
        
        response = requests.get(
            f'{API_BASE_URL}/jobs/{job_id}',
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get('data')
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API call failed for job {job_id}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error getting job {job_id}: {e}")
        return None

def get_resume_via_api(resume_id: str) -> Optional[Dict[str, Any]]:
    """Get resume details via backend API"""
    try:
        headers = {}
        if BACKEND_API_KEY:
            headers['Authorization'] = f'Bearer {BACKEND_API_KEY}'
        
        response = requests.get(
            f'{API_BASE_URL}/updates/resume/{resume_id}',
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        result = response.json()
        return result.get('data')
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API call failed for resume {resume_id}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error getting resume {resume_id}: {e}")
        return None

def save_score_via_api(job_id: str, resume_id: str, scores: Dict) -> bool:
    """Save or update score result via backend API"""
    try:
        headers = {'Content-Type': 'application/json'}
        if BACKEND_API_KEY:
            headers['Authorization'] = f'Bearer {BACKEND_API_KEY}'
        
        response = requests.post(
            f'{API_BASE_URL}/updates/score',
            json={
                'job_id': job_id,
                'resume_id': resume_id,
                'keyword_score': scores.get('keyword_score', 0),
                'semantic_score': scores.get('semantic_score', 0),
                'project_score': scores.get('project_score', 0),
                'final_score': scores.get('final_score', 0),
                'hard_requirements_met': scores.get('hard_requirements_passed', True),
                'score_breakdown': scores.get('breakdown', {})
            },
            headers=headers,
            timeout=30
        )
        response.raise_for_status()
        print(f"✅ Saved score for resume {resume_id} via API")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ API call failed for score save (resume {resume_id}): {e}")
        return False
    except Exception as e:
        print(f"❌ Error saving score for resume {resume_id}: {e}")
        return False

def update_resume_status(resume_id: str, status: str, parsed_content: Dict = None) -> bool:
    """Update resume processing status via backend API"""
    update_data = {}
    
    if status in ('extraction_complete', 'extraction_success'):
        update_data['extraction_status'] = 'success'
    elif status == 'extraction_failed':
        update_data['extraction_status'] = 'failed'
    elif status in ('parsing_complete', 'parsing_success'):
        update_data['parsing_status'] = 'success'
        if parsed_content:
            update_data['parsed_content'] = parsed_content
    elif status == 'parsing_failed':
        update_data['parsing_status'] = 'failed'
    elif status in ('embedding_complete', 'embedding_success'):
        update_data['embedding_status'] = 'success'
    elif status == 'embedding_failed':
        update_data['embedding_status'] = 'failed'
    
    return update_resume_via_api(resume_id, update_data)

def update_resume_embeddings(resume_id: str, section_embeddings: Dict[str, Any]) -> bool:
    """Update resume embeddings (6 sections) via backend API"""
    try:
        import numpy as np
        
        resume_embedding = {'model': 'text-embedding-3-small', 'dimension': 1536}
        
        for section in ['profile', 'skills', 'projects', 'responsibilities', 'education', 'overall']:
            if section in section_embeddings:
                emb_array = section_embeddings[section]
                if isinstance(emb_array, np.ndarray) and emb_array.size > 0:
                    if emb_array.ndim == 2:
                        emb_list = emb_array.tolist()
                    elif emb_array.ndim == 1:
                        emb_list = [emb_array.tolist()]
                    else:
                        emb_list = []
                    resume_embedding[section] = emb_list
                else:
                    resume_embedding[section] = []
        
        update_data = {
            'resume_embedding': resume_embedding,
            'embedding_status': 'success'
        }
        
        return update_resume_via_api(resume_id, update_data)
        
    except Exception as e:
        print(f"❌ Error updating embeddings for resume {resume_id}: {e}")
        return False

def process_resume_pipeline(resume_file_path: str, jd_data: Dict[str, Any], 
                          resume_id: str, job_id: str,
                          progress_callback: Optional[callable] = None) -> Dict[str, Any]:
    """Process resume through complete pipeline with progress updates"""
    
    def report_progress(percent: int, message: str, stage: str = None):
        """Helper to report progress"""
        if progress_callback:
            progress_callback({
                'percent': percent,
                'message': message,
                'stage': stage,
                'resume_id': resume_id,
                'job_id': job_id
            })
        print(f"📊 [{percent}%] {message}")
    
    try:
        report_progress(0, f"Starting resume processing: {resume_file_path}", "starting")
        
        # Extract text from PDF
        text_result = process_resume_file(resume_file_path)
        if not text_result.get('success'):
            update_resume_status(resume_id, 'extraction_failed')
            raise ResumeProcessingError(f"Text extraction failed: {text_result.get('error')}")
        
        update_resume_status(resume_id, 'extraction_success')
        
        char_count = text_result.get('metadata', {}).get('characters', len(text_result.get('text', '')))
        report_progress(15, f"Text extracted: {char_count} chars", "extraction_complete")
        
        # Parse with AI
        report_progress(20, "Starting AI parsing...", "parsing_start")
        parse_result = parse_resume_with_ai(text_result['text'], jd_data)
        if not parse_result.get('success'):
            update_resume_status(resume_id, 'parsing_failed')
            raise ResumeProcessingError(f"AI parsing failed: {parse_result.get('error')}")
        
        parsed_resume = parse_result['parsed_data']
        update_resume_status(resume_id, 'parsing_success', parsed_resume)
        report_progress(35, f"Resume parsed: {parsed_resume.get('name', 'Unknown')}", "parsing_complete")
        
        # Generate embeddings
        report_progress(40, "Generating embeddings...", "embedding_start")
        embed_result = generate_resume_embeddings(parsed_resume)
        if not embed_result.get('success'):
            update_resume_status(resume_id, 'embedding_failed')
            raise ResumeProcessingError(f"Embedding failed: {embed_result.get('error')}")
        
        # Save embeddings to database
        section_embeddings = embed_result.get('section_embeddings', {})
        embedding_saved = update_resume_embeddings(resume_id, section_embeddings)
        
        report_progress(55, f"Embeddings generated for {len(section_embeddings)} sections", "embedding_complete")
        
        # Calculate scores
        report_progress(60, "Calculating scores...", "scoring_start")
        
        # Log actual data for debugging
        try:
            with open('/tmp/debug_resume_data.json', 'w') as f:
                json.dump({
                    'resume_id': resume_id,
                    'job_id': job_id,
                    'parsed_resume': parsed_resume,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2, default=str)
            with open('/tmp/debug_jd_data.json', 'w') as f:
                json.dump({
                    'job_id': job_id,
                    'jd_data': jd_data,
                    'timestamp': datetime.now().isoformat()
                }, f, indent=2, default=str)
            print(f"📝 Debug data logged to /tmp/debug_resume_data.json and /tmp/debug_jd_data.json")
        except Exception as e:
            print(f"⚠️ Failed to log debug data: {e}")
        
        # Hard requirements check
        hard_req_result = check_hard_requirements(parsed_resume, jd_data)
        if not hard_req_result.get('success'):
            hard_req_result = {'all_requirements_met': True, 'overall_compliance_score': 1.0}
        report_progress(65, f"Hard requirements: {'✅ Met' if hard_req_result.get('all_requirements_met') else '❌ Not met'}", "hard_req_complete")
        
        # Project scoring
        project_result = calculate_project_scores(parsed_resume, jd_data)
        if not project_result.get('success'):
            project_result = {'overall_score': 0.0}
        report_progress(70, f"Project score: {project_result.get('overall_score', 0):.2f}", "project_complete")
        
        # Keyword scoring
        keyword_result = calculate_keyword_scores(parsed_resume, jd_data)
        if not keyword_result.get('success'):
            keyword_result = {'overall_score': 0.0}
        report_progress(75, f"Keyword score: {keyword_result.get('overall_score', 0):.2f}", "keyword_complete")
        
        # Semantic scoring
        semantic_result = calculate_semantic_scores(
            embed_result.get('section_embeddings', {}), jd_data
        )
        if not semantic_result.get('success'):
            semantic_result = {'overall_semantic_score': 0.0}
        report_progress(80, f"Semantic score: {semantic_result.get('overall_semantic_score', 0):.2f}", "semantic_complete")
        
        # Calculate final composite score
        report_progress(85, "Calculating final composite score...", "composite_start")
        composite_result = calculate_composite_score(
            hard_req_result, project_result, keyword_result, semantic_result,
            parsed_resume, jd_data.get('jd_analysis', {})
        )
        if not composite_result.get('success'):
            composite_result = {'final_score': 0.0, 'ranking_tier': 'Poor'}
        
        final_score = composite_result.get('final_score', 0.0)
        report_progress(90, f"Final score: {final_score:.2f} ({composite_result.get('ranking_tier', 'Unknown')})", "composite_complete")
        
        # Save scores to database
        report_progress(95, "Saving scores to database...", "saving")
        scores = {
            'keyword_score': keyword_result.get('overall_score', 0.0),
            'semantic_score': semantic_result.get('overall_semantic_score', 0.0),
            'project_score': project_result.get('overall_score', 0.0),
            'final_score': composite_result.get('final_score', 0.0),
            'hard_requirements_passed': hard_req_result.get('all_requirements_met', True)
        }
        save_score_via_api(job_id, resume_id, scores)
        
        report_progress(100, "Resume processing completed successfully", "complete")
        return {
            'success': True,
            'final_score': composite_result.get('final_score', 0.0),
            'ranking_tier': composite_result.get('ranking_tier', 'Poor'),
            'hard_requirements_passed': hard_req_result.get('all_requirements_met', True),
            'resume_data': parsed_resume
        }
        
    except Exception as e:
        return {'success': False, 'error': str(e), 'final_score': 0.0}

def process_resume(resume_file_path: str, jd_data: Dict[str, Any], 
                  resume_id: str, job_id: str) -> Dict[str, Any]:
    """Main entry point for resume processing"""
    # Validate all required inputs upfront
    if not resume_id:
        return {'success': False, 'error': 'Resume ID is required'}
    if not job_id:
        return {'success': False, 'error': 'Job ID is required'}
    if not resume_file_path or not os.path.exists(resume_file_path):
        return {'success': False, 'error': 'Invalid resume file path'}
    if not jd_data or not isinstance(jd_data, dict):
        return {'success': False, 'error': 'Invalid JD data'}
    
    return process_resume_pipeline(resume_file_path, jd_data, resume_id, job_id)

def process_resume_job(job_data: Dict[str, Any]) -> Dict[str, Any]:
    """Process resume job for BullMQ integration - production ready"""
    resume_id = job_data.get('resume_id')
    job_id = job_data.get('job_id')
    
    # Validate required inputs
    if not resume_id:
        return {'success': False, 'error': 'Resume ID is required'}
    if not job_id:
        return {'success': False, 'error': 'Job ID is required'}
    
    # Get resume data from API
    resume_data = get_resume_via_api(resume_id)
    if not resume_data:
        return {'success': False, 'error': f'Failed to get resume data for ID: {resume_id}'}
    
    # Get resume file path
    resume_file_path = resume_data.get('file_path')
    if not resume_file_path or not os.path.exists(resume_file_path):
        return {'success': False, 'error': f'Resume file not found: {resume_file_path}'}
    
    # Get job data from API
    jd_data = get_job_via_api(job_id)
    if not jd_data:
        return {'success': False, 'error': f'Failed to get job data for ID: {job_id}'}
    
    # Process the resume
    return process_resume(resume_file_path, jd_data, resume_id, job_id)