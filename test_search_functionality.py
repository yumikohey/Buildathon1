#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
from screenshots.views import search_screenshots
from django.test import RequestFactory
from django.http import QueryDict

def test_search_functionality():
    """Test the search functionality with various queries."""
    print("=== Testing Search Functionality ===")
    
    # Get all completed screenshots
    completed_screenshots = Screenshot.objects.filter(processing_status='completed')
    print(f"Found {completed_screenshots.count()} completed screenshots")
    
    # Test searches
    test_queries = [
        'CaseId',
        'caseid',
        'CASEID',
        'Case',
        'Id',
        'Flow',
        'Salesforce',
        'Chrome'
    ]
    
    factory = RequestFactory()
    
    for query in test_queries:
        print(f"\n--- Testing search for: '{query}' ---")
        
        # Create a mock request
        request = factory.get('/search/', {'q': query})
        
        try:
            # Call the search function directly
            from screenshots.views import perform_search
            results = perform_search(query)
            
            print(f"Found {len(results)} results")
            
            for result in results[:3]:  # Show top 3 results
                print(f"  - Screenshot {result.screenshot.id}: {result.screenshot.filename}")
                print(f"    Overall confidence: {result.overall_confidence:.3f}")
                print(f"    Text confidence: {result.text_confidence:.3f}")
                if result.matched_text_snippets:
                    print(f"    Matched snippets: {result.matched_text_snippets[:2]}")
                print()
                
        except Exception as e:
            print(f"Error during search: {e}")
    
    # Also test by manually checking if any extracted text contains variations of CaseId
    print("\n=== Manual Text Analysis ===")
    for screenshot in completed_screenshots:
        if screenshot.extracted_text:
            text_lower = screenshot.extracted_text.lower()
            variations = ['caseid', 'case id', 'case_id', 'case-id']
            found_variations = []
            
            for variation in variations:
                if variation in text_lower:
                    found_variations.append(variation)
            
            if found_variations:
                print(f"Screenshot {screenshot.id} contains: {found_variations}")
                # Show context
                for variation in found_variations:
                    pos = text_lower.find(variation)
                    start = max(0, pos - 30)
                    end = min(len(screenshot.extracted_text), pos + 50)
                    context = screenshot.extracted_text[start:end]
                    print(f"  Context for '{variation}': ...{context}...")
            else:
                print(f"Screenshot {screenshot.id}: No CaseId variations found")

if __name__ == '__main__':
    test_search_functionality()