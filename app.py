import os
import sys
from pathlib import Path

# Add the project directory to Python path
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

# Set Django settings module
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')

# Import Django WSGI application
from visual_memory_search.wsgi import application

# Expose the WSGI application as 'app' for Vercel
app = application# Force Vercel redeploy
