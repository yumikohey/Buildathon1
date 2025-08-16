#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
import django_rq

# Get screenshot 4 specifically
try:
    screenshot = Screenshot.objects.get(id=4)
    print(f"Found screenshot {screenshot.id}: {screenshot.filename}")
    print(f"Current status: {screenshot.processing_status}")
    
    # Reset status and clear error
    screenshot.processing_status = 'pending'
    screenshot.processing_error = None
    screenshot.extracted_text = ''
    screenshot.visual_description = ''
    screenshot.save()
    
    # Queue for processing
    queue = django_rq.get_queue('default')
    from screenshots.tasks import process_screenshot_with_claude
    job = queue.enqueue(process_screenshot_with_claude, screenshot.id)
    
    print(f"Screenshot {screenshot.id} has been reset and queued for reprocessing")
    print(f"Job ID: {job.id}")
    
except Screenshot.DoesNotExist:
    print("Screenshot 4 not found")