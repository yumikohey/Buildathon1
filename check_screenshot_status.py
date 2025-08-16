#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
from django.contrib.auth.models import User

def check_screenshot_status():
    """Check the current status of all screenshots."""
    try:
        user = User.objects.get(username='demo')
        screenshots = Screenshot.objects.filter(user=user)
        
        print(f'Total screenshots for demo user: {screenshots.count()}')
        print('\nStatus breakdown:')
        for status in ['pending', 'processing', 'completed', 'failed']:
            count = screenshots.filter(processing_status=status).count()
            print(f'{status}: {count}')
        
        print('\nRecent screenshots:')
        for s in screenshots.order_by('-uploaded_at')[:10]:
            print(f'ID {s.id}: {s.filename} - {s.processing_status} (uploaded: {s.uploaded_at})')
            
    except User.DoesNotExist:
        print('Demo user not found')
    except Exception as e:
        print(f'Error: {e}')

if __name__ == '__main__':
    check_screenshot_status()