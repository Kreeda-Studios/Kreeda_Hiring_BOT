#!/usr/bin/env python3
"""
Main JD Processing Orchestrator

Complete pipeline for processing job descriptions:
1. Fetch job from API
2. Extract text from PDF
3. AI parsing (JDGpt.py logic) - returns complete structured data
4. Save all data to database
5. Generate and save embeddings
"""

import sys
import json
import os
import requests
from pathlib import Path

# Add current directory to path for imports
sys.path.append(str(Path(__file__).parent))
sys.path.append(str(Path(__file__).parent.parent))

from a_pdf_text_extractor import process_jd_file
from b_ai_jd_parser import process_jd_with_ai  # New: uses JDGpt.py logic
from c_ai_embedding_generator import process_jd_embeddings
from d_compliance_parser import process_job_compliances  # New: parse mandatory/soft compliances

# Backend API URL - reads from BACKEND_API_URL env var (set in docker-compose)
API_BASE_URL = os.getenv('BACKEND_API_URL', os.getenv('API_BASE_URL', 'http://localhost:3001/api'))

def get_job_details(job_id: str) -> dict:
    """
    Fetch job details from backend API
    
    Args:
        job_id: MongoDB job ID
        
    Returns: {
        'success': bool,
        'data': dict (job object),
        'error': str or None
    }
    """
    try:
        url = f"{API_BASE_URL}/jobs/{job_id}"
        print(f"🌐 Fetching job details from: {url}")
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Failed to fetch job details: {str(e)}")
        return {'success': False, 'error': str(e)}

def update_job_data(job_id: str, data: dict) -> dict:
    """
    Update job data in database via backend API
    
    Args:
        job_id: MongoDB job ID
        data: Dictionary of fields to update
        
    Returns: {
        'success': bool,
        'data': dict (updated job object),
        'error': str or None
    }
    """
    try:
        url = f"{API_BASE_URL}/jobs/{job_id}"
        print(f"🌐 Updating job at: {url}")
        response = requests.patch(url, json=data, timeout=10, headers={'Content-Type': 'application/json'})
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"❌ Failed to update job: {str(e)}")
        return {'success': False, 'error': str(e)}

def process_jd_complete(job_id: str, progress_callback=None) -> dict:
    """
    Complete JD processing pipeline
    
    Args:
        job_id: MongoDB job ID (only parameter needed)
        progress_callback: Optional callback function for progress updates
        
    Returns: {
        'success': bool,
        'job_id': str,
        'processing_stages': dict,
        'error': str or None
    }
    """
    
    def update_progress(stage: str, percent: int, message: str):
        """Helper to send progress updates"""
        if progress_callback:
            progress_callback({
                'stage': stage,
                'percent': percent,
                'message': message,
                'timestamp': __import__('datetime').datetime.now().isoformat()
            })
        print(f"📊 Progress: {percent}% - {stage}: {message}")
    
    processing_stages = {
        'job_fetch': {'completed': False, 'error': None},
        'text_extraction': {'completed': False, 'error': None},
        'compliance_parsing': {'completed': False, 'error': None},
        'ai_parsing': {'completed': False, 'error': None},
        'save_analysis': {'completed': False, 'error': None},
        'embedding_generation': {'completed': False, 'error': None},
        'save_embeddings': {'completed': False, 'error': None},
    }
    
    try:
        # Step 1: Fetch job details from API
        update_progress('job_fetch', 10, 'Fetching job details from database')
        print(f"📥 Step 1: Fetching job details for job {job_id}")
        job_response = get_job_details(job_id)
        
        if not job_response.get('success'):
            error_msg = job_response.get('error', 'Failed to fetch job')
            print(f"❌ Job fetch failed: {error_msg}")
            processing_stages['job_fetch']['error'] = error_msg
            update_progress('job_fetch', 10, f'Failed: {error_msg}')
            return {'success': False, 'job_id': job_id, 'processing_stages': processing_stages, 'error': error_msg}
        
        job_data = job_response.get('data', {})
        processing_stages['job_fetch']['completed'] = True
        print(f"✅ Job fetched: {job_data.get('title', 'N/A')}")
        update_progress('job_fetch', 20, f"Job details loaded: {job_data.get('title', 'N/A')}")
        
        # Step 2: Extract and combine text
        update_progress('text_extraction', 25, 'Extracting text from PDF and JD')
        print(f"🔍 Step 2: Extracting text from JD")
        combined_text = ""
        
        # Extract from PDF if filename exists
        jd_pdf_filename = job_data.get('jd_pdf_filename', '')
        if jd_pdf_filename:
            # Construct file path (uploads/jds/filename)
            file_path = os.path.join('/app', 'uploads', 'jds', jd_pdf_filename)
            print(f"📄 PDF file: {file_path}")
            
            if os.path.exists(file_path):
                print(f"🔄 Extracting text from PDF...")
                text_result = process_jd_file(file_path)
                
                if text_result.get('success'):
                    combined_text += text_result.get('text', '')
                    print(f"✅ Extracted {len(combined_text)} characters from PDF")
                else:
                    print(f"⚠️ PDF extraction failed: {text_result.get('error')}")
            else:
                print(f"⚠️ PDF file not found: {file_path}")
        
        # Add jd_text if exists
        jd_text = job_data.get('jd_text', '')
        if jd_text:
            if combined_text:
                combined_text += "\n\n" + jd_text
            else:
                combined_text = jd_text
            print(f"✅ Added JD text ({len(jd_text)} characters)")
        
        if not combined_text:
            error_msg = "No JD text or PDF content found"
            print(f"❌ {error_msg}")
            processing_stages['text_extraction']['error'] = error_msg
            update_progress('text_extraction', 30, f'Failed: {error_msg}')
            return {'success': False, 'job_id': job_id, 'processing_stages': processing_stages, 'error': error_msg}
        
        processing_stages['text_extraction']['completed'] = True
        print(f"✅ [JD_EXTRACT] Total combined text: {len(combined_text)} characters")
        update_progress('text_extraction', 20, f'Text extracted: {len(combined_text)} characters')
        
        # Step 3: Parse mandatory and soft compliances BEFORE AI parsing
        update_progress('compliance_parsing', 22, 'Parsing compliance requirements')
        print(f"📋 Step 3: Parsing compliance requirements (mandatory & soft)")
        
        try:
            parsed_compliances = process_job_compliances(job_data)
            
            # Update filter_requirements with parsed structured data
            current_filter_reqs = job_data.get('filter_requirements', {})
            
            # Merge: keep mandatory/soft raw_prompts, update structured fields
            updated_filter_requirements = {
                'mandatory_compliances': parsed_compliances.get('mandatory_compliances', {
                    'raw_prompt': '',
                    'structured': {}
                }),
                'soft_compliances': parsed_compliances.get('soft_compliances', {
                    'raw_prompt': '',
                    'structured': {}
                })
            }
            
            # Check if any compliances were parsed
            mandatory_fields = len(updated_filter_requirements['mandatory_compliances'].get('structured', {}))
            soft_fields = len(updated_filter_requirements['soft_compliances'].get('structured', {}))
            
            if mandatory_fields > 0 or soft_fields > 0:
                print(f"✅ [JD_COMPLY] Compliance parsing completed:")
                print(f"   - Mandatory: {mandatory_fields} requirement field(s)")
                print(f"   - Soft: {soft_fields} requirement field(s)")
                processing_stages['compliance_parsing']['completed'] = True
                update_progress('compliance_parsing', 35, f'Compliance parsing completed ({mandatory_fields + soft_fields} fields)')
            else:
                print(f"ℹ️ [JD_COMPLY] No compliances to parse (both empty)")
                processing_stages['compliance_parsing']['completed'] = True
                update_progress('compliance_parsing', 35, 'No compliances specified')
            
        except Exception as e:
            error_msg = f"Compliance parsing failed: {str(e)}"
            print(f"⚠️ [JD_COMPLY] {error_msg} - continuing with empty compliances")
            processing_stages['compliance_parsing']['error'] = error_msg
            # Continue anyway - not critical, use empty compliances
            updated_filter_requirements = job_data.get('filter_requirements', {
                'mandatory_compliances': {'raw_prompt': '', 'structured': {}},
                'soft_compliances': {'raw_prompt': '', 'structured': {}}
            })
            update_progress('compliance_parsing', 35, f'Warning: {error_msg}')
        
        # Step 4: AI JD Parsing
        update_progress('ai_parsing', 40, 'Processing JD with AI (1-2 minutes)')
        print(f"🤖 Step 4: AI JD Parsing")
        
        ai_result = process_jd_with_ai(combined_text)
        
        if not ai_result.get('success'):
            error_msg = ai_result.get('error', 'AI JD parsing failed')
            print(f"❌ [JD_PARSE] {error_msg}")
            processing_stages['ai_parsing']['error'] = error_msg
            update_progress('ai_parsing', 55, f'Failed: {error_msg}')
            return {'success': False, 'job_id': job_id, 'processing_stages': processing_stages, 'error': error_msg}
        
        processing_stages['ai_parsing']['completed'] = True
        parsed_jd = ai_result.get('parsed_data', {})
        print(f"✅ [JD_PARSE] Parsed: {parsed_jd.get('role_title', 'N/A')} | Skills: {len(parsed_jd.get('required_skills', []))} | HR Notes: {parsed_jd.get('hr_points', 0)}")
        update_progress('ai_parsing', 55, 'AI parsing completed')
        
        # Step 5: Save complete data to DB (jd_analysis + filter_requirements)
        update_progress('save_analysis', 58, 'Saving complete analysis to database')
        print(f"💾 Step 5: Saving complete JD data to database")
        
        # Build update payload matching Job schema
        update_payload = {
            'jd_analysis': {
                # Analysis metadata
                'meta': parsed_jd.get('meta', {}),
                
                # HR insights from AI
                'hr_points': parsed_jd.get('hr_points', 0),
                'hr_notes': parsed_jd.get('hr_notes', []),
                'explainability': parsed_jd.get('explainability'),
                'provenance_spans': parsed_jd.get('provenance_spans', []),
                
                # Compliance parsing results
                'mandatory_compliances': updated_filter_requirements.get('mandatory_compliances', {}),
                'soft_compliances': updated_filter_requirements.get('soft_compliances', {}),
                
                # Core fields
                'role_title': parsed_jd.get('role_title'),
                'alt_titles': parsed_jd.get('alt_titles', []),
                'seniority_level': parsed_jd.get('seniority_level'),
                'department': parsed_jd.get('department'),
                'industry': parsed_jd.get('industry'),
                'domain_tags': parsed_jd.get('domain_tags', []),
                
                # Work logistics
                'location': parsed_jd.get('location'),
                'work_model': parsed_jd.get('work_model'),
                'employment_type': parsed_jd.get('employment_type'),
                'contract': parsed_jd.get('contract'),
                'start_date_preference': parsed_jd.get('start_date_preference'),
                'travel_requirement_percent': parsed_jd.get('travel_requirement_percent'),
                'work_hours': parsed_jd.get('work_hours'),
                'shift_details': parsed_jd.get('shift_details'),
                'visa_sponsorship': parsed_jd.get('visa_sponsorship'),
                'clearances_required': parsed_jd.get('clearances_required', []),
                
                # Experience & education
                'years_experience_required': parsed_jd.get('years_experience_required'),
                'education_requirements': parsed_jd.get('education_requirements', []),
                'min_degree_level': parsed_jd.get('min_degree_level'),
                'fields_of_study': parsed_jd.get('fields_of_study', []),
                'certifications_required': parsed_jd.get('certifications_required', []),
                'certifications_preferred': parsed_jd.get('certifications_preferred', []),
                
                # Skills
                'required_skills': parsed_jd.get('required_skills', []),
                'preferred_skills': parsed_jd.get('preferred_skills', []),
                'tools_tech': parsed_jd.get('tools_tech', []),
                'soft_skills': parsed_jd.get('soft_skills', []),
                'languages': parsed_jd.get('languages', []),
                'canonical_skills': parsed_jd.get('canonical_skills', {}),
                'skill_requirements': parsed_jd.get('skill_requirements', []),
                
                # Duties & outcomes
                'responsibilities': parsed_jd.get('responsibilities', []),
                'deliverables': parsed_jd.get('deliverables', []),
                'kpis_okrs': parsed_jd.get('kpis_okrs', []),
                
                # Team context
                'team_context': parsed_jd.get('team_context'),
                
                # Constraints
                'exclusions': parsed_jd.get('exclusions', []),
                'compliance': parsed_jd.get('compliance', []),
                'screening_questions': parsed_jd.get('screening_questions', []),
                
                # Interview & compensation
                'interview_process': parsed_jd.get('interview_process'),
                'compensation': parsed_jd.get('compensation'),
                'benefits': parsed_jd.get('benefits', []),
                
                # Keywords & weighting
                'keywords_flat': parsed_jd.get('keywords_flat', []),
                'keywords_weighted': parsed_jd.get('keywords_weighted', {}),
                'weighting': parsed_jd.get('weighting', {}),
                'embedding_hints': parsed_jd.get('embedding_hints', {}),
            },
            'filter_requirements': updated_filter_requirements,  # Keep raw HR input separate
        }
        
        update_result = update_job_data(job_id, update_payload)
        
        if not update_result.get('success'):
            error_msg = f"Failed to save jd_analysis: {update_result.get('error')}"
            print(f"❌ [JD_SAVE] {error_msg}")
            processing_stages['save_analysis']['error'] = error_msg
            update_progress('save_analysis', 65, f'Failed: {error_msg}')
            return {'success': False, 'job_id': job_id, 'processing_stages': processing_stages, 'error': error_msg}
        else:
            processing_stages['save_analysis']['completed'] = True
            print(f"✅ [JD_SAVE] Complete JD data saved to database")
            update_progress('save_analysis', 65, 'Complete analysis saved to database')
        
        # Step 6: Generate embeddings from jd_analysis
        update_progress('embedding_generation', 68, 'Generating embeddings')
        print(f"🔮 Step 6: Generating embeddings")
        embeddings_result = process_jd_embeddings(parsed_jd)
        
        if not embeddings_result.get('success'):
            error_msg = embeddings_result.get('error', 'Embedding generation failed')
            print(f"❌ [JD_EMBED] {error_msg}")
            processing_stages['embedding_generation']['error'] = error_msg
            update_progress('embedding_generation', 85, f'Warning: {error_msg}')
            # Continue anyway - not critical
        else:
            processing_stages['embedding_generation']['completed'] = True
            sections_count = embeddings_result.get('sections_generated', 6)
            print(f"✅ [JD_EMBED] Generated {sections_count}/6 embeddings (profile, skills, projects, responsibilities, education, overall)")
            update_progress('embedding_generation', 85, 'Embeddings generated')
            
            # Step 7: Save embeddings to DB (top-level embeddings field)
            update_progress('save_embeddings', 88, 'Saving embeddings to database')
            print(f"💾 Step 7: Saving embeddings to database")
            
            # Store all 6 section embeddings at top level
            embeddings_payload = {
                'embeddings': {
                    'embedding_model': embeddings_result.get('embedding_model', 'text-embedding-3-small'),
                    'embedding_dimension': embeddings_result.get('embedding_dimension', 1536),
                    'profile_embedding': embeddings_result.get('profile_embedding'),
                    'skills_embedding': embeddings_result.get('skills_embedding'),
                    'projects_embedding': embeddings_result.get('projects_embedding'),
                    'responsibilities_embedding': embeddings_result.get('responsibilities_embedding'),
                    'education_embedding': embeddings_result.get('education_embedding'),
                    'overall_embedding': embeddings_result.get('overall_embedding')
                }
            }
            
            # Update embeddings field at top level (separate from jd_analysis)
            update_result = update_job_data(job_id, embeddings_payload)
            
            if not update_result.get('success'):
                error_msg = f"Failed to save embeddings: {update_result.get('error')}"
                print(f"⚠️ [JD_EMBED] {error_msg}")
                processing_stages['save_embeddings']['error'] = error_msg
                update_progress('save_embeddings', 100, f'Warning: {error_msg}')
            else:
                processing_stages['save_embeddings']['completed'] = True
                print(f"✅ [JD_EMBED] All 6 section embeddings saved to database")
                update_progress('save_embeddings', 100, 'Embeddings saved successfully')
        
        print(f"✅ JD processing completed successfully for job {job_id}")
        update_progress('completed', 100, 'JD processing completed successfully!')
        
        return {
            'success': True,
            'job_id': job_id,
            'processing_stages': processing_stages
        }
        
    except Exception as e:
        import traceback
        error_traceback = traceback.format_exc()
        print(f"❌ JD processing failed for job {job_id}: {type(e).__name__}: {str(e)}")
        print(f"📋 Full error traceback:\n{error_traceback}")
        return {
            'success': False,
            'job_id': job_id, 
            'processing_stages': processing_stages,
            'error': f"{type(e).__name__}: {str(e)}"
        }
