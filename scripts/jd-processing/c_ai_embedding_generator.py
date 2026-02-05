  #!/usr/bin/env python3
"""
AI Embedding Generation for Job Descriptions

Generates 6 section-specific embeddings for semantic matching:
1. profile - Role title and seniority
2. skills - Required + preferred skills
3. projects - Project-related expectations
4. responsibilities - Job duties and deliverables
5. education - Education and certifications
6. overall - Complete JD summary

Uses OpenAI text-embedding-3-small (1536 dimensions)
"""

import os
import sys
import time
from typing import Dict, Any, List
from pathlib import Path

# Add parent directory to path for OpenAI client import
sys.path.append(str(Path(__file__).parent.parent))

try:
    from openai_client import create_embedding
except ImportError:
    #print("❌ Failed to import OpenAI client")
    sys.exit(1)


def generate_section_embedding(text: str, section_name: str) -> Dict[str, Any]:
    """Generate embedding for a single section"""
    try:
        if not text or not text.strip():
            return {
                'success': False,
                'error': f'Empty text for {section_name}'
            }
        
        embedding = create_embedding(text.strip())
        
        return {
            'success': True,
            'embedding': embedding,
            'dimension': len(embedding),
            'section': section_name
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"{section_name} embedding failed: {str(e)}"
        }


def build_section_texts(parsed_jd: Dict[str, Any]) -> Dict[str, str]:
    """
    Build text representations for each of the 6 sections
    Matches old system's section structure for semantic scoring
    """
    sections = {}
    
    # 1. PROFILE - Role identity and seniority
    profile_parts = []
    if parsed_jd.get('role_title'):
        profile_parts.append(parsed_jd['role_title'])
    if parsed_jd.get('seniority_level'):
        profile_parts.append(f"{parsed_jd['seniority_level']} level")
    if parsed_jd.get('department'):
        profile_parts.append(f"in {parsed_jd['department']}")
    if parsed_jd.get('industry'):
        profile_parts.append(f"({parsed_jd['industry']} industry)")
    if parsed_jd.get('years_experience_required'):
        profile_parts.append(f"{parsed_jd['years_experience_required']}+ years experience")
    
    sections['profile'] = ' '.join(profile_parts) if profile_parts else parsed_jd.get('role_title', 'Job Position')
    
    # 2. SKILLS - All technical and soft skills
    skills_parts = []
    required = parsed_jd.get('required_skills', [])
    preferred = parsed_jd.get('preferred_skills', [])
    tools = parsed_jd.get('tools_tech', [])
    soft = parsed_jd.get('soft_skills', [])
    
    if required:
        skills_parts.append(f"Required: {', '.join(required)}")
    if preferred:
        skills_parts.append(f"Preferred: {', '.join(preferred)}")
    if tools:
        skills_parts.append(f"Tools: {', '.join(tools)}")
    if soft:
        skills_parts.append(f"Soft skills: {', '.join(soft)}")
    
    sections['skills'] = '. '.join(skills_parts) if skills_parts else 'Technical skills required'
    
    # 3. PROJECTS - Project expectations and deliverables
    projects_parts = []
    
    # Use embedding_hints if available (for compatibility)
    if parsed_jd.get('embedding_hints', {}).get('projects_embed'):
        projects_parts.append(parsed_jd['embedding_hints']['projects_embed'])
    else:
        # Build from deliverables and responsibilities
        if parsed_jd.get('deliverables'):
            projects_parts.append(f"Deliverables: {'. '.join(parsed_jd['deliverables'])}")
        
        if parsed_jd.get('kpis_okrs'):
            projects_parts.append(f"Outcomes: {'. '.join(parsed_jd['kpis_okrs'])}")
        
        # Add project-relevant responsibilities
        responsibilities = parsed_jd.get('responsibilities', [])
        project_keywords = ['build', 'develop', 'design', 'implement', 'create', 'deliver', 'architect']
        project_resps = [r for r in responsibilities if any(kw in r.lower() for kw in project_keywords)]
        if project_resps:
            projects_parts.append(f"Projects: {'. '.join(project_resps[:3])}")
    
    sections['projects'] = '. '.join(projects_parts) if projects_parts else 'Project development and delivery'
    
    # 4. RESPONSIBILITIES - Core job duties
    responsibilities = parsed_jd.get('responsibilities', [])
    if responsibilities:
        sections['responsibilities'] = '. '.join(responsibilities)
    else:
        sections['responsibilities'] = 'Job responsibilities and daily tasks'
    
    # 5. EDUCATION - Education and certifications
    education_parts = []
    
    if parsed_jd.get('min_degree_level'):
        education_parts.append(f"Degree: {parsed_jd['min_degree_level']}")
    
    if parsed_jd.get('fields_of_study'):
        education_parts.append(f"Fields: {', '.join(parsed_jd['fields_of_study'])}")
    
    if parsed_jd.get('certifications_required'):
        education_parts.append(f"Required certifications: {', '.join(parsed_jd['certifications_required'])}")
    
    if parsed_jd.get('certifications_preferred'):
        education_parts.append(f"Preferred certifications: {', '.join(parsed_jd['certifications_preferred'])}")
    
    if parsed_jd.get('education_requirements'):
        education_parts.extend(parsed_jd['education_requirements'])
    
    sections['education'] = '. '.join(education_parts) if education_parts else 'Educational background'
    
    # 6. OVERALL - Complete JD summary
    # Use embedding_hints if available, otherwise build comprehensive text
    if parsed_jd.get('embedding_hints', {}).get('overall_embed'):
        sections['overall'] = parsed_jd['embedding_hints']['overall_embed']
    else:
        overall_parts = [
            sections['profile'],
            sections['responsibilities'][:500] if len(sections['responsibilities']) > 500 else sections['responsibilities'],
            sections['skills'][:300] if len(sections['skills']) > 300 else sections['skills']
        ]
        sections['overall'] = '. '.join(overall_parts)
    
    return sections


def generate_and_format_embeddings(parsed_jd: dict) -> Dict:
    """
    Generate embeddings and format for database (API-ready payload)
    
    Args:
        parsed_jd: Parsed JD data from AI
        
    Returns: {
        'success': bool,
        'embeddings_payload': {  # Ready for API PATCH
            'embeddings': {
                'embedding_model': str,
                'embedding_dimension': int,
                'profile_embedding': list,
                'skills_embedding': list,
                'projects_embedding': list,
                'responsibilities_embedding': list,
                'education_embedding': list,
                'overall_embedding': list
            }
        },
        'stats': {
            'sections_generated': int,
            'total_sections': int,
            'model': str,
            'dimension': int
        },
        'error': str or None
    }
    """
    result = process_jd_embeddings(parsed_jd)
    
    if not result.get('success'):
        return {
            'success': False,
            'embeddings_payload': None,
            'stats': {
                'sections_generated': 0,
                'total_sections': 6,
                'model': None,
                'dimension': None
            },
            'error': result.get('error', 'Embedding generation failed')
        }
    
    embeddings_payload = {
        'embeddings': {
            'embedding_model': result.get('embedding_model', 'text-embedding-3-small'),
            'embedding_dimension': result.get('embedding_dimension', 1536),
            'profile_embedding': result.get('profile_embedding'),
            'skills_embedding': result.get('skills_embedding'),
            'projects_embedding': result.get('projects_embedding'),
            'responsibilities_embedding': result.get('responsibilities_embedding'),
            'education_embedding': result.get('education_embedding'),
            'overall_embedding': result.get('overall_embedding')
        }
    }
    
    sections_count = result.get('sections_generated', 6)
    
    return {
        'success': True,
        'embeddings_payload': embeddings_payload,
        'stats': {
            'sections_generated': sections_count,
            'total_sections': 6,
            'model': result.get('embedding_model', 'text-embedding-3-small'),
            'dimension': result.get('embedding_dimension', 1536)
        },
        'error': None
    }


def process_jd_embeddings(parsed_jd: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate all 6 section embeddings for JD (matches old system)
    
    Returns:
    {
        'success': bool,
        'profile_embedding': list[float],
        'skills_embedding': list[float],
        'projects_embedding': list[float],
        'responsibilities_embedding': list[float],
        'education_embedding': list[float],
        'overall_embedding': list[float],
        'embedding_model': str,
        'error': str (if failed)
    }
    """
    try:
        start_time = time.time()
        
        # Build section texts
        sections = build_section_texts(parsed_jd)
        
        # Generate embeddings for all 6 sections
        results = {}
        section_names = ['profile', 'skills', 'projects', 'responsibilities', 'education', 'overall']
        
        for section in section_names:
            result = generate_section_embedding(sections[section], section)
            
            if not result['success']:
                #print(f"⚠️ Warning: {section} embedding failed: {result.get('error')}")
                # Use empty embedding as fallback
                results[f'{section}_embedding'] = None
            else:
                results[f'{section}_embedding'] = result['embedding']
        
        processing_time = time.time() - start_time
        
        # Check if at least some embeddings were generated
        successful_embeddings = sum(1 for v in results.values() if v is not None)
        
        if successful_embeddings == 0:
            return {
                'success': False,
                'error': 'All section embeddings failed to generate'
            }
        
        return {
            'success': True,
            **results,
            'embedding_model': 'text-embedding-3-small',
            'embedding_dimension': 1536,
            'sections_generated': successful_embeddings,
            'processing_time': processing_time
        }
        
    except Exception as e:
        return {
            'success': False,
            'error': f"JD embeddings processing failed: {str(e)}"
        }
