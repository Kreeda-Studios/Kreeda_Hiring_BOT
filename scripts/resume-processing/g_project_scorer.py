#!/usr/bin/env python3

"""
Project Scorer for Resume Analysis

Calculates project relevance and quality scores based on 
ProjectProcess.py logic from the existing codebase.
"""

from typing import Dict, Any, List, Optional

def calculate_skill_relevance_score(project: Dict[str, Any], jd_skills: List[str]) -> float:
    """Calculate how relevant project skills are to JD requirements"""
    try:
        project_skills = []
        
        # Collect project skills
        project_skills.extend(project.get('technologies', []))
        project_skills.extend(project.get('tech_keywords', []))
        project_skills.extend(project.get('primary_skills', []))
        
        if not project_skills or not jd_skills:
            return 0.0
        
        # Normalize skills for comparison
        project_skills_normalized = [skill.lower().strip() for skill in project_skills if skill]
        jd_skills_normalized = [skill.lower().strip() for skill in jd_skills if skill]
        
        # Count matches
        matches = 0
        for jd_skill in jd_skills_normalized:
            for proj_skill in project_skills_normalized:
                if jd_skill in proj_skill or proj_skill in jd_skill:
                    matches += 1
                    break
        
        # Calculate relevance score
        relevance_score = min(1.0, matches / len(jd_skills_normalized))
        return relevance_score
        
    except Exception:
        return 0.0

def calculate_domain_relevance_score(project: Dict[str, Any], jd_domain: str) -> float:
    """Calculate how relevant project domain is to JD domain"""
    try:
        if not jd_domain:
            return 0.5  # Neutral if no domain specified
        
        project_description = project.get('description', '').lower()
        project_name = project.get('name', '').lower()
        jd_domain_lower = jd_domain.lower()
        
        # Domain keyword matching
        domain_keywords = {
            'web development': ['web', 'website', 'frontend', 'backend', 'fullstack', 'react', 'angular', 'vue'],
            'data science': ['data', 'analytics', 'machine learning', 'ml', 'ai', 'analysis', 'visualization'],
            'mobile development': ['mobile', 'android', 'ios', 'app', 'flutter', 'react native'],
            'cloud computing': ['cloud', 'aws', 'azure', 'gcp', 'kubernetes', 'docker', 'microservices'],
            'machine learning': ['ml', 'machine learning', 'ai', 'neural network', 'deep learning', 'nlp'],
            'software engineering': ['software', 'development', 'engineering', 'system', 'architecture'],
            'devops': ['devops', 'ci/cd', 'deployment', 'infrastructure', 'automation', 'jenkins'],
            'cybersecurity': ['security', 'encryption', 'authentication', 'vulnerability', 'penetration']
        }
        
        # Find relevant keywords for JD domain
        relevant_keywords = []
        for domain, keywords in domain_keywords.items():
            if domain in jd_domain_lower:
                relevant_keywords.extend(keywords)
        
        if not relevant_keywords:
            # Fallback: use JD domain words directly
            relevant_keywords = jd_domain_lower.split()
        
        # Check for keyword matches in project
        matches = 0
        for keyword in relevant_keywords:
            if keyword in project_description or keyword in project_name:
                matches += 1
        
        # Calculate domain relevance
        if len(relevant_keywords) > 0:
            domain_score = min(1.0, matches / len(relevant_keywords) * 2)  # Allow for partial matches
        else:
            domain_score = 0.0
        
        return domain_score
        
    except Exception:
        return 0.0

def calculate_technical_depth_score(project: Dict[str, Any]) -> float:
    """Calculate technical depth based on project complexity indicators"""
    try:
        score = 0.0
        
        # Base score from description length and detail
        description = project.get('description', '')
        if len(description) > 200:
            score += 0.3
        elif len(description) > 100:
            score += 0.2
        elif len(description) > 50:
            score += 0.1
        
        # Technology diversity bonus
        technologies = project.get('technologies', [])
        tech_count = len(set(tech.lower() for tech in technologies if tech))
        if tech_count >= 5:
            score += 0.3
        elif tech_count >= 3:
            score += 0.2
        elif tech_count >= 2:
            score += 0.1
        
        # Architecture/system design indicators
        description_lower = description.lower()
        architecture_keywords = ['architecture', 'design', 'system', 'scalable', 'microservices', 'api', 'database', 'integration']
        architecture_matches = sum(1 for keyword in architecture_keywords if keyword in description_lower)
        if architecture_matches >= 3:
            score += 0.2
        elif architecture_matches >= 2:
            score += 0.15
        elif architecture_matches >= 1:
            score += 0.1
        
        # Advanced technology indicators
        advanced_tech = ['docker', 'kubernetes', 'aws', 'azure', 'gcp', 'redis', 'elasticsearch', 'mongodb', 'postgresql', 'react', 'angular', 'vue', 'node.js', 'django', 'flask', 'spring']
        tech_text = ' '.join(technologies).lower() + ' ' + description_lower
        advanced_matches = sum(1 for tech in advanced_tech if tech in tech_text)
        if advanced_matches >= 4:
            score += 0.2
        elif advanced_matches >= 2:
            score += 0.15
        elif advanced_matches >= 1:
            score += 0.1
        
        return min(1.0, score)
        
    except Exception:
        return 0.0

def calculate_execution_quality_score(project: Dict[str, Any]) -> float:
    """Calculate execution quality based on project indicators"""
    try:
        score = 0.0
        
        # GitHub/deployment links bonus
        github_url = project.get('github_url', '')
        live_url = project.get('live_url', '')
        
        if github_url:
            score += 0.3
        if live_url:
            score += 0.3
        
        # Project completion indicators
        description = project.get('description', '').lower()
        completion_keywords = ['deployed', 'production', 'live', 'completed', 'finished', 'published', 'released']
        if any(keyword in description for keyword in completion_keywords):
            score += 0.2
        
        # Quality indicators
        quality_keywords = ['tested', 'testing', 'responsive', 'optimized', 'performance', 'secure', 'scalable']
        quality_matches = sum(1 for keyword in quality_keywords if keyword in description)
        if quality_matches >= 2:
            score += 0.2
        elif quality_matches >= 1:
            score += 0.1
        
        return min(1.0, score)
        
    except Exception:
        return 0.0

def calculate_project_metrics(project: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """Calculate comprehensive project metrics"""
    try:
        jd_analysis = jd_data.get('jd_analysis', {})
        
        # Extract JD requirements
        required_skills = jd_analysis.get('required_skills', [])
        preferred_skills = jd_analysis.get('preferred_skills', [])
        all_jd_skills = required_skills + preferred_skills
        
        jd_domain = jd_analysis.get('job_domain', '') or jd_analysis.get('role_type', '')
        
        # Calculate individual metrics
        skill_relevance = calculate_skill_relevance_score(project, all_jd_skills)
        domain_relevance = calculate_domain_relevance_score(project, jd_domain)
        technical_depth = calculate_technical_depth_score(project)
        execution_quality = calculate_execution_quality_score(project)
        
        # Calculate complexity (combination of technical depth and skill diversity)
        technologies = project.get('technologies', [])
        complexity = min(1.0, (technical_depth + len(technologies) * 0.1) / 2)
        
        # Calculate novelty (based on unique technology combinations)
        novelty = min(1.0, len(set(tech.lower() for tech in technologies)) * 0.15)
        
        # Calculate difficulty (based on technical indicators and description complexity)
        description = project.get('description', '')
        difficulty_keywords = ['complex', 'advanced', 'challenging', 'sophisticated', 'enterprise', 'large-scale']
        difficulty_score = sum(1 for keyword in difficulty_keywords if keyword.lower() in description.lower())
        difficulty = min(1.0, (difficulty_score * 0.2) + (technical_depth * 0.8))
        
        # Define metric weights (from original ProjectProcess.py)
        weights = {
            'difficulty': 0.142857,
            'novelty': 0.142857,
            'skill_relevance': 0.142857,
            'complexity': 0.142857,
            'technical_depth': 0.142857,
            'domain_relevance': 0.142857,
            'execution_quality': 0.142857
        }
        
        # Calculate weighted score
        metrics = {
            'difficulty': round(difficulty, 3),
            'novelty': round(novelty, 3),
            'skill_relevance': round(skill_relevance, 3),
            'complexity': round(complexity, 3),
            'technical_depth': round(technical_depth, 3),
            'domain_relevance': round(domain_relevance, 3),
            'execution_quality': round(execution_quality, 3)
        }
        
        # Calculate weighted average
        weighted_score = 0.0
        for metric, weight in weights.items():
            weighted_score += metrics[metric] * weight
        
        return {
            'metrics': metrics,
            'weighted_score': round(weighted_score, 3),
            'weights_used': weights,
            'project_name': project.get('name', 'Unnamed Project')
        }
        
    except Exception as e:
        return {
            'metrics': {},
            'weighted_score': 0.0,
            'error': f"Error calculating project metrics: {str(e)}"
        }

def calculate_project_scores(resume: Dict[str, Any], jd_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Main function to calculate project scores
    Returns: {
        'success': bool,
        'overall_score': float,
        'project_scores': list,
        'project_summary': dict,
        'error': str or None
    }
    """
    try:
        projects = resume.get('projects', [])
        
        if not projects:
            return {
                'success': True,
                'overall_score': 0.0,
                'project_scores': [],
                'project_summary': {
                    'total_projects': 0,
                    'average_score': 0.0,
                    'best_project_score': 0.0,
                    'projects_with_links': 0
                }
            }
        
        # Calculate scores for each project
        project_results = []
        
        for i, project in enumerate(projects):
            project_metrics = calculate_project_metrics(project, jd_data)
            
            project_result = {
                'project_index': i,
                'project_name': project.get('name', f'Project {i+1}'),
                'score': project_metrics['weighted_score'],
                'metrics': project_metrics['metrics'],
                'has_github': bool(project.get('github_url')),
                'has_live_url': bool(project.get('live_url')),
                'technology_count': len(project.get('technologies', [])),
                'description_length': len(project.get('description', ''))
            }
            
            project_results.append(project_result)
        
        # Calculate overall project score (average of all projects)
        project_scores = [p['score'] for p in project_results]
        overall_score = sum(project_scores) / len(project_scores) if project_scores else 0.0
        
        # Generate project summary
        project_summary = {
            'total_projects': len(projects),
            'average_score': round(overall_score, 3),
            'best_project_score': round(max(project_scores), 3) if project_scores else 0.0,
            'worst_project_score': round(min(project_scores), 3) if project_scores else 0.0,
            'projects_with_github': sum(1 for p in project_results if p['has_github']),
            'projects_with_live_url': sum(1 for p in project_results if p['has_live_url']),
            'total_technologies': sum(p['technology_count'] for p in project_results),
            'avg_technologies_per_project': round(sum(p['technology_count'] for p in project_results) / len(project_results), 1) if project_results else 0.0
        }
        
        return {
            'success': True,
            'overall_score': round(overall_score, 3),
            'project_scores': project_results,
            'project_summary': project_summary
        }
        
    except Exception as e:
        return {
            'success': False,
            'overall_score': 0.0,
            'project_scores': [],
            'project_summary': {},
            'error': f"Project scoring failed: {str(e)}"
        }