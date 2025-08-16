#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
from screenshots.search import ScreenshotSearchService
from django.contrib.auth.models import User

def test_babies_search():
    """Test search functionality for 'babies' content."""
    print("=== Testing Babies Search Functionality ===")
    
    # Get all completed screenshots
    completed_screenshots = Screenshot.objects.filter(processing_status='completed')
    print(f"Found {completed_screenshots.count()} completed screenshots")
    
    # Check if any screenshots contain 'babies' in their descriptions
    print("\n=== Checking for 'babies' in visual descriptions ===")
    babies_screenshots = []
    for screenshot in completed_screenshots:
        if screenshot.visual_description and 'babies' in screenshot.visual_description.lower():
            babies_screenshots.append(screenshot)
            print(f"Screenshot {screenshot.id}: {screenshot.filename}")
            print(f"  Visual description: {screenshot.visual_description[:200]}...")
            print(f"  Uploaded: {screenshot.uploaded_at}")
            print(f"  File created: {screenshot.file_created_at}")
    
    if not babies_screenshots:
        print("No screenshots found with 'babies' in visual descriptions")
        
        # Check extracted text too
        print("\n=== Checking for 'babies' in extracted text ===")
        for screenshot in completed_screenshots:
            if screenshot.extracted_text and 'babies' in screenshot.extracted_text.lower():
                babies_screenshots.append(screenshot)
                print(f"Screenshot {screenshot.id}: {screenshot.filename}")
                print(f"  Extracted text contains 'babies'")
                print(f"  Uploaded: {screenshot.uploaded_at}")
    
    # Test search queries
    print("\n=== Testing Search Queries ===")
    
    # Get the demo user who owns the babies screenshots
    try:
        user = User.objects.get(username='demo')
        print(f"Using demo user for testing")
    except User.DoesNotExist:
        print("Demo user not found, testing without user filtering")
        user = None
    
    search_service = ScreenshotSearchService(user=user)
    
    test_queries = [
        'babies',
        'baby',
        'when did I take picture of babies',
        'when did I take picture of babies?',
        'picture of babies'
    ]
    
    for query in test_queries:
        print(f"\n--- Testing query: '{query}' ---")
        try:
            results = search_service.search(query, limit=10)
            print(f"Found {len(results)} results")
            
            for i, result in enumerate(results, 1):
                screenshot = result.screenshot
                confidence = result.overall_confidence
                print(f"  {i}. {screenshot.filename} (confidence: {confidence:.2f})")
                print(f"     Uploaded: {screenshot.uploaded_at}")
                if screenshot.file_created_at:
                    print(f"     File created: {screenshot.file_created_at}")
                
                # Show why it matched
                if screenshot.visual_description and 'babies' in screenshot.visual_description.lower():
                    print(f"     ✓ Visual description contains 'babies'")
                if screenshot.extracted_text and 'babies' in screenshot.extracted_text.lower():
                    print(f"     ✓ Extracted text contains 'babies'")
                    
        except Exception as e:
            print(f"Error during search: {e}")
            import traceback
            traceback.print_exc()

if __name__ == '__main__':
    test_babies_search()