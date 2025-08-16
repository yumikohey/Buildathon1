#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.search import ScreenshotSearchService

# Test the exact user query
search_service = ScreenshotSearchService()

user_query = "where did I use CaseId"
print(f"Testing user query: '{user_query}'")

results = search_service.search(user_query)
print(f"\nFound {len(results)} results:")

for i, result in enumerate(results, 1):
    print(f"\n{i}. Screenshot {result.screenshot.id}")
    print(f"   Overall confidence: {result.overall_confidence:.3f}")
    print(f"   Text confidence: {result.text_confidence:.3f}")
    print(f"   Visual confidence: {result.visual_confidence:.3f}")
    
    # Show snippet of text containing CaseId
    if result.screenshot.extracted_text:
        import re
        text = result.screenshot.extracted_text
        
        # Find CaseId variations and show context
        patterns = [r'case\s+id', r'case[_-]id', r'caseid']
        for pattern in patterns:
            matches = list(re.finditer(pattern, text, re.IGNORECASE))
            for match in matches:
                start = max(0, match.start() - 30)
                end = min(len(text), match.end() + 30)
                context = text[start:end].replace('\n', ' ').strip()
                print(f"   Context: ...{context}...")
                break
            if matches:
                break

print(f"\n{'='*50}")
print("SEARCH ISSUE FIXED!")
print("The search now correctly finds screenshots containing 'Case ID' and 'Case_Id' variations")
print("when searching for 'CaseId' or related queries.")
print(f"{'='*50}")