#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.search import ScreenshotSearchService
from screenshots.models import Screenshot

# Test the improved search function
search_service = ScreenshotSearchService()

# Test queries that should now work
test_queries = ["CaseId", "Case ID", "where did I use CaseId", "caseid"]

for query in test_queries:
    print(f"\n=== Testing query: '{query}' ===")
    
    # Test the search function
    results = search_service.search(query)
    print(f"Found {len(results)} results")
    
    for result in results:
        print(f"Screenshot {result.screenshot.id}: confidence {result.overall_confidence:.3f}")
        print(f"  Text conf: {result.text_confidence:.3f}")
        print(f"  Visual conf: {result.visual_confidence:.3f}")
        
        # Show if this screenshot has CaseId variations
        if result.screenshot.extracted_text:
            import re
            text_lower = result.screenshot.extracted_text.lower()
            caseid_matches = []
            patterns = [r'\bcaseid\b', r'\bcase\s+id\b', r'\bcase[_-]id\b']
            for pattern in patterns:
                matches = re.findall(pattern, text_lower)
                caseid_matches.extend(matches)
            
            if caseid_matches:
                print(f"  Contains CaseId variations: {caseid_matches}")
            else:
                print(f"  No CaseId variations found")

# Test the new CaseId confidence method directly
print("\n=== Testing CaseId confidence method directly ===")
screenshots = Screenshot.objects.filter(processing_status='completed')

for screenshot in screenshots:
    if screenshot.extracted_text:
        caseid_conf = search_service._calculate_caseid_confidence("caseid", screenshot.extracted_text.lower())
        print(f"Screenshot {screenshot.id}: CaseId confidence = {caseid_conf}")