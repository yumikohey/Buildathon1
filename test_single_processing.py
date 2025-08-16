#!/usr/bin/env python
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
from screenshots.tasks import process_screenshot_with_claude

def test_single_processing():
    """Test processing a single screenshot directly (not through queue)."""
    screenshot = Screenshot.objects.filter(processing_status='processing').first()
    
    if screenshot:
        print(f"Testing direct processing of screenshot {screenshot.id}: {screenshot.filename}")
        result = process_screenshot_with_claude(screenshot.id)
        print(f"Result: {result}")
        
        # Check the updated screenshot
        screenshot.refresh_from_db()
        print(f"Status: {screenshot.processing_status}")
        print(f"Extracted text length: {len(screenshot.extracted_text or '')}")
        if screenshot.extracted_text:
            print(f"Extracted text preview: {screenshot.extracted_text[:200]}...")
        if screenshot.processing_error:
            print(f"Error: {screenshot.processing_error}")
    else:
        print("No screenshots in processing status found")

if __name__ == '__main__':
    test_single_processing()