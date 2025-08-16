#!/usr/bin/env python
import os
import django
from django.conf import settings

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
from screenshots.tasks import process_screenshot_with_claude
import django_rq

def reprocess_failed_screenshots():
    """Reprocess all failed screenshots."""
    failed_screenshots = Screenshot.objects.filter(processing_status='failed')
    
    print(f"Found {failed_screenshots.count()} failed screenshots to reprocess")
    
    queue = django_rq.get_queue('default')
    
    for screenshot in failed_screenshots:
        print(f"Queuing screenshot {screenshot.id}: {screenshot.filename}")
        # Reset status to pending
        screenshot.processing_status = 'pending'
        screenshot.processing_error = ''
        screenshot.save()
        
        # Queue for reprocessing
        queue.enqueue(process_screenshot_with_claude, screenshot.id)
    
    print("All failed screenshots have been queued for reprocessing")

if __name__ == '__main__':
    reprocess_failed_screenshots()