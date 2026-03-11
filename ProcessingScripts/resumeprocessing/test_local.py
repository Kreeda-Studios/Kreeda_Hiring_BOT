#!/usr/bin/env python3
"""
Simple Test Script for AI Team
Run this to test your changes without any infrastructure
"""

import asyncio
import json
from resumeprocessing.main import process_resume


async def test_basic():
    """Test basic resume processing."""
    print("=" * 60)
    print("Testing Resume Processing")
    print("=" * 60)
    
    # Sample test data
    test_data = {
        'jobId': 'test-001',
        'resumePath': './test_data/sample_resume.pdf',
        'jdPath': './test_data/sample_jd.txt',
    }
    
    print(f"\nTest Data: {json.dumps(test_data, indent=2)}\n")
    
    try:
        result = await process_resume(test_data)
        print("\n✅ SUCCESS!")
        print(f"Result: {json.dumps(result, indent=2)}")
    except Exception as e:
        print(f"\n❌ FAILED: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(test_basic())
