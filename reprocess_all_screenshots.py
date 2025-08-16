#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
import django_rq

def reprocess_all_screenshots():
    """Reprocess all screenshots that are not completed."""
    # Get all screenshots that are not completed
    screenshots = Screenshot.objects.exclude(processing_status='completed')
    
    print(f"Found {screenshots.count()} screenshots to reprocess")
    
    for screenshot in screenshots:
        print(f"\nReprocessing screenshot {screenshot.id}: {screenshot.filename}")
        print(f"Current status: {screenshot.processing_status}")
        
        # Reset status and clear any errors
        screenshot.processing_status = 'pending'
        screenshot.processing_error = None
        screenshot.extracted_text = ''
        screenshot.visual_description = ''
        screenshot.ui_elements = []
        screenshot.dominant_colors = []
        screenshot.processed_at = None
        screenshot.save()
        
        # Queue for processing
        queue = django_rq.get_queue('default')
        job = queue.enqueue('screenshots.tasks.process_screenshot_with_claude', screenshot.id)
        print(f"Queued for processing. Job ID: {job.id}")
    
    print(f"\nAll {screenshots.count()} screenshots have been queued for reprocessing")

if __name__ == '__main__':
    reprocess_all_screenshots()