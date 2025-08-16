import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot

# Check all screenshots in database
screenshots = Screenshot.objects.all()
print(f'Total screenshots: {screenshots.count()}')
print('\nScreenshot details:')
for s in screenshots:
    print(f'ID: {s.id}')
    print(f'Filename: {s.filename}')
    print(f'Status: {s.processing_status}')
    print(f'Extracted text length: {len(s.extracted_text or "")}')
    if s.extracted_text:
        print(f'Extracted text preview: {s.extracted_text[:200]}...')
    print(f'Visual description length: {len(s.visual_description or "")}')
    if s.visual_description:
        print(f'Visual description preview: {s.visual_description[:200]}...')
    print(f'Processing error: {s.processing_error or "None"}')
    print('-' * 50)