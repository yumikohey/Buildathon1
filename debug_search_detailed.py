#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.search import ScreenshotSearchService
from screenshots.models import Screenshot

# Test the actual search function
search_service = ScreenshotSearchService()

# Test queries
test_queries = ["CaseId", "Case ID", "where did I use CaseId"]

for query in test_queries:
    print(f"\n=== Testing query: '{query}' ===")
    
    # Get all completed screenshots
    screenshots = Screenshot.objects.filter(processing_status='completed')
    print(f"Found {screenshots.count()} completed screenshots")
    
    for screenshot in screenshots:
        print(f"\n--- Screenshot ID {screenshot.id} ---")
        print(f"Has extracted_text: {bool(screenshot.extracted_text)}")
        
        if screenshot.extracted_text:
            # Test text confidence calculation
            text_conf = search_service._calculate_text_confidence(query, screenshot)
            print(f"Text confidence: {text_conf}")
            
            # Show word extraction for debugging
            query_words = search_service._extract_words(query.lower())
            text_words = search_service._extract_words(screenshot.extracted_text.lower())
            print(f"Query words: {query_words}")
            print(f"Text words (first 10): {text_words[:10]}")
            
            # Check for exact phrase match
            if query.lower() in screenshot.extracted_text.lower():
                print("EXACT PHRASE MATCH FOUND!")
            else:
                print("No exact phrase match")
            
            # Check word matches
            matched_words = [word for word in query_words if word in text_words]
            print(f"Matched words: {matched_words}")
            
            # Check fuzzy matches
            fuzzy_score = search_service._fuzzy_text_match(query_words, text_words)
            print(f"Fuzzy score: {fuzzy_score}")
        
        # Calculate overall confidence
        visual_conf = search_service._calculate_visual_confidence(query, screenshot)
        ui_conf = search_service._calculate_ui_confidence(query, screenshot)
        color_conf = search_service._calculate_color_confidence(query, screenshot)
        
        overall_conf = (
            text_conf * 0.4 +
            visual_conf * 0.3 +
            ui_conf * 0.2 +
            color_conf * 0.1
        )
        
        print(f"Visual conf: {visual_conf}, UI conf: {ui_conf}, Color conf: {color_conf}")
        print(f"Overall confidence: {overall_conf}")
        print(f"Above threshold (0.1): {overall_conf > 0.1}")
    
    # Test actual search function
    print(f"\n--- Actual search results for '{query}' ---")
    results = search_service.search(query)
    print(f"Found {len(results)} results")
    for result in results:
        print(f"Screenshot {result.screenshot.id}: confidence {result.overall_confidence}")