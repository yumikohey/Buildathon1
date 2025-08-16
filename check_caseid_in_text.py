#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
import re

# Check each screenshot for CaseId variations
screenshots = Screenshot.objects.filter(processing_status='completed')

for screenshot in screenshots:
    print(f"\n=== Screenshot ID {screenshot.id} ===")
    
    if screenshot.extracted_text:
        text = screenshot.extracted_text
        print(f"Text length: {len(text)}")
        
        # Search for various CaseId patterns
        patterns = [
            r'(?i)case\s*id',  # case id (case insensitive, optional space)
            r'(?i)case[_-]id',  # case_id or case-id
            r'(?i)caseid',      # caseid
        ]
        
        found_matches = []
        for pattern in patterns:
            matches = re.findall(pattern, text)
            if matches:
                found_matches.extend(matches)
        
        if found_matches:
            print(f"Found CaseId variations: {found_matches}")
            
            # Show context around matches
            for pattern in patterns:
                for match in re.finditer(pattern, text):
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    context = text[start:end].replace('\n', ' ').strip()
                    print(f"Context: ...{context}...")
        else:
            print("No CaseId variations found")
            
        # Show first 200 characters for manual inspection
        print(f"First 200 chars: {text[:200]}")
        
        # Show last 200 characters
        print(f"Last 200 chars: {text[-200:]}")
    else:
        print("No extracted text")