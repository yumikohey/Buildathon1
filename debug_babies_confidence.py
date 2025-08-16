#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.models import Screenshot
from screenshots.search import ScreenshotSearchService
from django.contrib.auth.models import User

def debug_babies_confidence():
    """Debug confidence scores for babies screenshots."""
    print("=== Debugging Babies Confidence Scores ===")
    
    # Get user for testing
    user = User.objects.first()
    if not user:
        print("No users found, creating test user")
        user = User.objects.create_user('testuser', 'test@example.com', 'password')
    
    search_service = ScreenshotSearchService(user=user)
    
    # Get screenshots with 'babies' in visual description
    babies_screenshots = Screenshot.objects.filter(
        processing_status='completed',
        visual_description__icontains='babies'
    )
    
    print(f"Found {babies_screenshots.count()} screenshots with 'babies' in description")
    
    query = 'babies'
    print(f"\nTesting query: '{query}'")
    
    for screenshot in babies_screenshots:
        print(f"\n--- Screenshot {screenshot.id}: {screenshot.filename} ---")
        print(f"Visual description: {screenshot.visual_description[:100]}...")
        
        # Calculate individual confidence scores
        text_conf = search_service._calculate_text_confidence(query, screenshot)
        visual_conf = search_service._calculate_visual_confidence(query, screenshot)
        ui_conf = search_service._calculate_ui_confidence(query, screenshot)
        color_conf = search_service._calculate_color_confidence(query, screenshot)
        
        print(f"Text confidence: {text_conf}")
        print(f"Visual confidence: {visual_conf}")
        print(f"UI confidence: {ui_conf}")
        print(f"Color confidence: {color_conf}")
        
        # Calculate overall confidence using the same weights as the search service
        overall_conf = (
            text_conf * search_service.weights['text'] +
            visual_conf * search_service.weights['visual'] +
            ui_conf * search_service.weights['ui'] +
            color_conf * search_service.weights['color']
        )
        
        print(f"Overall confidence: {overall_conf}")
        print(f"Above threshold (0.1): {overall_conf > 0.1}")
        
        # Debug visual confidence calculation
        print("\n--- Visual Confidence Debug ---")
        query_lower = query.lower()
        description_lower = screenshot.visual_description.lower()
        
        # Check exact phrase matching
        if query_lower in description_lower:
            print(f"✓ Exact phrase match found: '{query_lower}' in description")
        else:
            print(f"✗ No exact phrase match for '{query_lower}'")
        
        # Check word matching
        query_words = search_service._extract_words(query_lower)
        description_words = search_service._extract_words(description_lower)
        
        print(f"Query words: {query_words}")
        print(f"Description words (first 10): {description_words[:10]}")
        
        matched_words = [word for word in query_words if word in description_words]
        print(f"Matched words: {matched_words}")
        
        if query_words:
            word_match_ratio = len(matched_words) / len(query_words)
            print(f"Word match ratio: {word_match_ratio}")
            print(f"Expected visual confidence: {word_match_ratio * 0.6}")
    
    # Test temporal query
    print("\n" + "="*50)
    temporal_query = 'when did I take picture of babies'
    print(f"Testing temporal query: '{temporal_query}'")
    
    for screenshot in babies_screenshots:
        print(f"\n--- Screenshot {screenshot.id}: {screenshot.filename} ---")
        
        # Calculate individual confidence scores
        text_conf = search_service._calculate_text_confidence(temporal_query, screenshot)
        visual_conf = search_service._calculate_visual_confidence(temporal_query, screenshot)
        ui_conf = search_service._calculate_ui_confidence(temporal_query, screenshot)
        color_conf = search_service._calculate_color_confidence(temporal_query, screenshot)
        
        print(f"Text confidence: {text_conf}")
        print(f"Visual confidence: {visual_conf}")
        print(f"UI confidence: {ui_conf}")
        print(f"Color confidence: {color_conf}")
        
        # Calculate overall confidence
        overall_conf = (
            text_conf * search_service.weights['text'] +
            visual_conf * search_service.weights['visual'] +
            ui_conf * search_service.weights['ui'] +
            color_conf * search_service.weights['color']
        )
        
        print(f"Overall confidence: {overall_conf}")
        print(f"Above threshold (0.1): {overall_conf > 0.1}")
        
        # Debug temporal query word extraction
        query_words = search_service._extract_words(temporal_query.lower())
        print(f"Temporal query words after filtering: {query_words}")

if __name__ == '__main__':
    debug_babies_confidence()