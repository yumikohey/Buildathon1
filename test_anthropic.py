import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from django.conf import settings
from anthropic import Anthropic

print(f"ANTHROPIC_API_KEY exists: {hasattr(settings, 'ANTHROPIC_API_KEY')}")
print(f"ANTHROPIC_API_KEY value: {getattr(settings, 'ANTHROPIC_API_KEY', 'NOT_SET')[:10]}...")

try:
    # Test Anthropic client initialization
    client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
    print("Anthropic client initialized successfully!")
    
    # Test a simple API call
    message = client.messages.create(
        model="claude-3-sonnet-20240229",
        max_tokens=10,
        messages=[
            {
                "role": "user",
                "content": "Hello"
            }
        ]
    )
    print(f"API call successful: {message.content[0].text}")
    
except Exception as e:
    print(f"Error: {e}")
    print(f"Error type: {type(e)}")