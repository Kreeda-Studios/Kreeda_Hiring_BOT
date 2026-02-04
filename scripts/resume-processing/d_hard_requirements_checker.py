#!/usr/bin/env python3

"""
Hard Requirements Checker for Resume Analysis

Checks mandatory HR requirements based on EarlyFilter.py logic.
Filters candidates who don't meet critical requirements.
"""

import re
from typing import Dict, Any, List, Tuple, Optional

def normalize_skill(skill: str) -> str:
    """Normalize skill names for consistent matching"""
    if not skill:
        return ""
    
    # Convert to lowercase and remove special characters
    normalized = re.sub(r'[^\w\s]', ' ', skill.lower().strip())
    
    # Common technology normalizations
    tech_mappings = {
        'javascript': 'javascript', 'js': 'javascript',
        'typescript': 'typescript', 'ts': 'typescript',
        'python': 'python', 'py': 'python',
        'react js': 'react', 'reactjs': 'react', 'react.js': 'react',
        'node js': 'nodejs', 'node.js': 'nodejs',
        'c++': 'cpp', 'c plus plus': 'cpp',
        'c#': 'csharp', 'c sharp': 'csharp'
    }
    
    return tech_mappings.get(normalized, normalized)

def check_experience_requirement(resume: Dict[str, Any], min_experience_years: float) -> Dict[str, Any]:
    """Check if candidate meets minimum experience requirement"""
    try:
        # Extract total experience from resume
        total_experience = 0.0
        
        # Try to get from summary field first
        if resume.get('years_experience'):
            try:
                total_experience = float(resume['years_experience'])
            except (ValueError, TypeError):
                pass
        
        # Calculate from individual experiences if not found in summary
        if total_experience == 0.0 and resume.get('experience'):
            for exp in resume['experience']:
                # Try to get duration_years
                if exp.get('duration_years'):
                    try:
                        total_experience += float(exp['duration_years'])
                    except (ValueError, TypeError):
                        pass
                elif exp.get('start_date') and exp.get('end_date'):
                    # Simple year calculation
                    try:
                        start_year = int(exp['start_date'][:4])
                        end_year = int(exp['end_date'][:4]) if exp['end_date'] != 'Present' else 2024
                        years = max(0, end_year - start_year)
                        total_experience += years
                    except (ValueError, TypeError, IndexError):
                        # Default to 1 year if parsing fails
                        total_experience += 1.0
                else:
                    # Default to 1 year per job if no dates
                    total_experience += 1.0
        
        # Check if meets requirement
        meets_requirement = total_experience >= min_experience_years
        
        return {
            'requirement_type': 'experience',
            'required_years': min_experience_years,
            'candidate_years': total_experience,
            'meets_requirement': meets_requirement,
            'reason': f"Candidate has {total_experience} years, requires {min_experience_years} years" if not meets_requirement else f"Meets experience requirement ({total_experience} years)"
        }
        
    except Exception as e:
        return {
            'requirement_type': 'experience',
            'required_years': min_experience_years,
            'candidate_years': 0.0,
            'meets_requirement': False,
            'reason': f"Error checking experience: {str(e)}"
        }

def check_skills_requirement(resume: Dict[str, Any], required_skills: List[str]) -> Dict[str, Any]:
    """Check if candidate has all required skills"""
    try:
        if not required_skills:
            return {
                'requirement_type': 'skills',
                'required_skills': [],
                'found_skills': [],
                'missing_skills': [],
                'meets_requirement': True,
                'reason': 'No skills requirement specified'
            }
        
        # Collect all skills from resume
        resume_skills = set()
        
        # From skills array
        for skill in resume.get('skills', []):
            if skill:
                resume_skills.add(normalize_skill(skill))
        
        # From canonical skills
        canonical_skills = resume.get('canonical_skills', {})
        for category, skills in canonical_skills.items():
            if isinstance(skills, list):
                for skill in skills:
                    if skill:
                        resume_skills.add(normalize_skill(skill))
        
        # From inferred skills
        for skill_obj in resume.get('inferred_skills', []):
            if skill_obj.get('skill'):
                resume_skills.add(normalize_skill(skill_obj['skill']))
        
        # From skill proficiency
        for skill_obj in resume.get('skill_proficiency', []):
            if skill_obj.get('skill'):
                resume_skills.add(normalize_skill(skill_obj['skill']))
        
        # From projects
        for project in resume.get('projects', []):
            for tech in project.get('technologies', []):
                if tech:
                    resume_skills.add(normalize_skill(tech))
            for keyword in project.get('tech_keywords', []):
                if keyword:
                    resume_skills.add(normalize_skill(keyword))
            for skill in project.get('primary_skills', []):
                if skill:
                    resume_skills.add(normalize_skill(skill))
        
        # Check which required skills are found
        found_skills = []
        missing_skills = []
        
        for req_skill in required_skills:
            normalized_req = normalize_skill(req_skill)
            
            # Check for exact match
            if normalized_req in resume_skills:
                found_skills.append(req_skill)
            else:
                # Check for partial matches
                found_partial = False
                for resume_skill in resume_skills:
                    if normalized_req in resume_skill or resume_skill in normalized_req:
                        found_skills.append(req_skill)
                        found_partial = True
                        break
                
                if not found_partial:
                    missing_skills.append(req_skill)
        
        # All required skills must be found
        meets_requirement = len(missing_skills) == 0
        
        return {
            'requirement_type': 'skills',
            'required_skills': required_skills,
            'found_skills': found_skills,
            'missing_skills': missing_skills,
            'meets_requirement': meets_requirement,
            'reason': f"Found {len(found_skills)}/{len(required_skills)} required skills" + (f". Missing: {', '.join(missing_skills)}" if missing_skills else "")
        }
        
    except Exception as e:
        return {
            'requirement_type': 'skills',
            'required_skills': required_skills,
            'found_skills': [],
            'missing_skills': required_skills,
            'meets_requirement': False,
            'reason': f"Error checking skills: {str(e)}"
        }

def check_education_requirement(resume: Dict[str, Any], required_education: Optional[str] = None) -> Dict[str, Any]:
    """Check if candidate meets education requirements"""
    try:
        education_entries = resume.get('education', [])
        
        if not required_education:
            return {
                'requirement_type': 'education',
                'required_education': None,
                'candidate_education': [edu.get('degree', '') for edu in education_entries],
                'meets_requirement': True,
                'reason': 'No education requirement specified'
            }
        
        if not education_entries:
            return {
                'requirement_type': 'education',
                'required_education': required_education,
                'candidate_education': [],
                'meets_requirement': False,
                'reason': 'No education information found in resume'
            }
        
        # Education level hierarchy
        education_levels = {
            'phd': 7, 'doctorate': 7, 'doctoral': 7,
            'masters': 6, 'master': 6, 'msc': 6, 'mba': 6, 'ms': 6,
            'bachelors': 5, 'bachelor': 5, 'bsc': 5, 'btech': 5, 'be': 5, 'bs': 5,
            'diploma': 4, 'associate': 4,
            'certificate': 3, 'certification': 3,
            'high school': 2, 'secondary': 2,
            '12th': 1, '10th': 0
        }
        
        # Determine required education level
        required_level = 0
        req_lower = required_education.lower()
        for edu_type, level in education_levels.items():
            if edu_type in req_lower:
                required_level = max(required_level, level)
        
        # Find candidate's highest education level
        candidate_level = 0
        best_degree = ""
        
        for edu in education_entries:
            degree = edu.get('degree', '').lower()
            for edu_type, level in education_levels.items():
                if edu_type in degree:
                    if level > candidate_level:
                        candidate_level = level
                        best_degree = edu.get('degree', '')
        
        meets_requirement = candidate_level >= required_level
        
        return {
            'requirement_type': 'education',
            'required_education': required_education,
            'candidate_education': [edu.get('degree', '') for edu in education_entries],
            'best_degree': best_degree,
            'meets_requirement': meets_requirement,
            'reason': f"Candidate has {best_degree}, requires {required_education}" if not meets_requirement else f"Education requirement met: {best_degree}"
        }
        
    except Exception as e:
        return {
            'requirement_type': 'education',
            'required_education': required_education,
            'candidate_education': [],
            'meets_requirement': False,
            'reason': f"Error checking education: {str(e)}"
        }

def check_location_requirement(resume: Dict[str, Any], required_location: Optional[str] = None) -> Dict[str, Any]:
    """Check if candidate meets location requirements"""
    try:
        if not required_location or required_location.lower() in ['any', 'anywhere', 'flexible', 'remote/onsite']:
            return {
                'requirement_type': 'location',
                'required_location': required_location,
                'candidate_location': resume.get('location', 'Not specified'),
                'meets_requirement': True,
                'reason': 'No specific location requirement'
            }
        
        candidate_location = resume.get('location', '')
        if not candidate_location:
            return {
                'requirement_type': 'location',
                'required_location': required_location,
                'candidate_location': 'Not specified',
                'meets_requirement': False,
                'reason': 'Location not specified in resume'
            }
        
        req_lower = required_location.lower()
        cand_lower = candidate_location.lower()
        
        # Check for work arrangement matches
        if 'remote' in req_lower and 'remote' in cand_lower:
            meets_requirement = True
        elif 'onsite' in req_lower and ('onsite' in cand_lower or 'office' in cand_lower):
            meets_requirement = True
        elif 'hybrid' in req_lower and 'hybrid' in cand_lower:
            meets_requirement = True
        # Check for city/state matches
        elif req_lower in cand_lower or cand_lower in req_lower:
            meets_requirement = True
        else:
            meets_requirement = False
        
        return {
            'requirement_type': 'location',
            'required_location': required_location,
            'candidate_location': candidate_location,
            'meets_requirement': meets_requirement,
            'reason': f"Location match: {candidate_location}" if meets_requirement else f"Location mismatch: {candidate_location} (required: {required_location})"
        }
        
    except Exception as e:
        return {
            'requirement_type': 'location',
            'required_location': required_location,
            'candidate_location': resume.get('location', 'Not specified'),
            'meets_requirement': False,
            'reason': f"Error checking location: {str(e)}"
        }

def check_hard_requirements(resume: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to check all hard requirements
    Returns: {
        'success': bool,
        'all_requirements_met': bool,
        'overall_compliance_score': float,
        'requirement_results': dict,
        'failed_requirements': list,
        'error': str or None
    }
    """
    try:
        jd_analysis = jd_data.get('jd_analysis', {})
        
        # Extract requirements from JD
        min_experience = jd_analysis.get('minimum_experience_years', 0.0)
        required_skills = jd_analysis.get('required_skills', [])
        required_education = jd_analysis.get('required_education')
        required_location = jd_analysis.get('location')
        
        # Check each requirement
        requirement_results = {}
        failed_requirements = []
        
        # Experience check
        exp_result = check_experience_requirement(resume, min_experience)
        requirement_results['experience'] = exp_result
        if not exp_result['meets_requirement']:
            failed_requirements.append('experience')
        
        # Skills check
        skills_result = check_skills_requirement(resume, required_skills)
        requirement_results['skills'] = skills_result
        if not skills_result['meets_requirement']:
            failed_requirements.append('skills')
        
        # Education check
        edu_result = check_education_requirement(resume, required_education)
        requirement_results['education'] = edu_result
        if not edu_result['meets_requirement']:
            failed_requirements.append('education')
        
        # Location check
        loc_result = check_location_requirement(resume, required_location)
        requirement_results['location'] = loc_result
        if not loc_result['meets_requirement']:
            failed_requirements.append('location')
        
        # Calculate overall compliance
        total_requirements = len(requirement_results)
        met_requirements = total_requirements - len(failed_requirements)
        
        overall_compliance_score = met_requirements / total_requirements if total_requirements > 0 else 1.0
        all_requirements_met = len(failed_requirements) == 0
        
        return {
            'success': True,
            'all_requirements_met': all_requirements_met,
            'overall_compliance_score': overall_compliance_score,
            'requirement_results': requirement_results,
            'failed_requirements': failed_requirements,
            'requirements_summary': {
                'total_requirements': total_requirements,
                'met_requirements': met_requirements,
                'failed_requirements': len(failed_requirements)
            }
        }
        
    except Exception as e:
        return {
            'success': False,
            'all_requirements_met': False,
            'overall_compliance_score': 0.0,
            'requirement_results': {},
            'failed_requirements': [],
            'error': f"Hard requirements check failed: {str(e)}"
        }