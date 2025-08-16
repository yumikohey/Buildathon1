#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot

def check_extracted_text():
    """Check what text was extracted from each screenshot."""
    screenshots = Screenshot.objects.all().order_by('id')
    
    for screenshot in screenshots:
        print(f"\n=== Screenshot ID: {screenshot.id} ===")
        print(f"Filename: {screenshot.filename}")
        print(f"Status: {screenshot.processing_status}")
        print(f"Processing Error: {screenshot.processing_error}")
        
        if screenshot.extracted_text:
            print(f"Extracted Text Length: {len(screenshot.extracted_text)}")
            # Look for 'CaseId' specifically
            if 'CaseId' in screenshot.extracted_text:
                print("✅ FOUND 'CaseId' in extracted text!")
                # Show context around CaseId
                text = screenshot.extracted_text
                case_id_pos = text.find('CaseId')
                start = max(0, case_id_pos - 50)
                end = min(len(text), case_id_pos + 100)
                context = text[start:end]
                print(f"Context: ...{context}...")
            else:
                print("❌ 'CaseId' NOT found in extracted text")
                # Show first 200 characters to see what was extracted
                preview = screenshot.extracted_text[:200]
                print(f"Text preview: {preview}...")
        else:
            print("❌ No extracted text")
        
        print("-" * 50)

if __name__ == '__main__':
    check_extracted_text()