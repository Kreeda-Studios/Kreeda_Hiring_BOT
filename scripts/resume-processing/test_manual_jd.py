#!/usr/bin/env python3

"""
Manual JD Test - Create a test JD and resume to verify scoring works
"""

from e_keyword_scorer import calculate_keyword_scores
from f_semantic_scorer import calculate_semantic_scores

def create_test_jd():
    """Create a test JD with proper structure"""
    return {
        'jd_analysis': {
            'required_skills': ['Python', 'Machine Learning', 'TensorFlow', 'SQL'],
            'preferred_skills': ['AWS', 'Docker', 'Kubernetes'],
            'tools_tech': ['Git', 'Linux', 'MongoDB'],
            'soft_skills': ['Communication', 'Problem Solving'],
            'keywords_flat': ['Python', 'ML', 'Data Science', 'Analytics'],
            'keywords_weighted': {
                'Python': 0.9,
                'Machine Learning': 0.8,
                'TensorFlow': 0.7,
                'SQL': 0.6
            }
        },
        'embeddings': {
            'profile': [0.1, 0.2, 0.3] * 512,  # Mock embedding
            'skills': [0.2, 0.3, 0.4] * 512,
            'responsibilities': [0.3, 0.4, 0.5] * 512,
            'overall': [0.1, 0.1, 0.1] * 512
        }
    }

def create_test_resume():
    """Create a test resume with some matching skills"""
    return {
        'skills': ['Python', 'JavaScript', 'SQL', 'Git', 'Communication'],
        'experience': [
            {
                'description': 'Developed machine learning models using Python and TensorFlow',
                'responsibilities': ['Built ML pipelines', 'Worked with data analysis']
            }
        ],
        'keywords_flat': ['Python', 'ML', 'JavaScript', 'Web Development']
    }

def create_test_resume_embeddings():
    """Create test resume embeddings"""
    return {
        'section_embeddings': {
            'profile': [0.1, 0.15, 0.25] * 512,  # Mock embedding similar to JD
            'skills': [0.2, 0.25, 0.35] * 512,
            'projects': [0.25, 0.35, 0.45] * 512,
            'responsibilities': [0.3, 0.35, 0.45] * 512,
            'education': [0.1, 0.2, 0.3] * 512,
            'overall': [0.15, 0.15, 0.15] * 512
        }
    }

def test_manual_scoring():
    """Test the scoring system with manual data"""
    print("=== MANUAL JD TEST ===")
    
    # Create test data
    jd_data = create_test_jd()
    resume_data = create_test_resume()
    resume_embeddings = create_test_resume_embeddings()
    
    print("Test JD Analysis:")
    print(f"  Required skills: {jd_data['jd_analysis']['required_skills']}")
    print(f"  Preferred skills: {jd_data['jd_analysis']['preferred_skills']}")
    print(f"  Tools & Tech: {jd_data['jd_analysis']['tools_tech']}")
    
    print("\nTest Resume:")
    print(f"  Skills: {resume_data['skills']}")
    print(f"  Keywords: {resume_data['keywords_flat']}")
    
    # Test keyword scoring
    print("\n--- KEYWORD SCORING TEST ---")
    try:
        keyword_result = calculate_keyword_scores(resume_data, jd_data)
        print(f"Keyword scoring success: {keyword_result.get('success', False)}")
        print(f"Keyword score: {keyword_result.get('overall_score', 0)}")
        if not keyword_result.get('success'):
            print(f"Keyword error: {keyword_result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"Keyword scoring failed: {e}")
    
    # Test semantic scoring
    print("\n--- SEMANTIC SCORING TEST ---")
    try:
        semantic_result = calculate_semantic_scores(
            resume_embeddings['section_embeddings'], 
            jd_data
        )
        print(f"Semantic scoring success: {semantic_result.get('success', False)}")
        print(f"Semantic score: {semantic_result.get('overall_score', 0)}")
        if not semantic_result.get('success'):
            print(f"Semantic error: {semantic_result.get('error', 'Unknown')}")
    except Exception as e:
        print(f"Semantic scoring failed: {e}")

if __name__ == "__main__":
    test_manual_scoring()