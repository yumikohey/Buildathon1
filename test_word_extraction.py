#!/usr/bin/env python
import os
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'visual_memory_search.settings')
django.setup()

from screenshots.search import ScreenshotSearchService

# Test word extraction
search_service = ScreenshotSearchService()

# Test cases
test_cases = [
    "CaseId",
    "Case ID", 
    "Case_Id",
    "case id",
    "where did I use CaseId",
    "Case ID: 12345"
]

print("Testing word extraction:")
for test_case in test_cases:
    words = search_service._extract_words(test_case)
    print(f"'{test_case}' -> {words}")

print("\nTesting similarity matching:")
query_words = search_service._extract_words("CaseId")
text_words = search_service._extract_words("Case ID: 12345")
print(f"Query words: {query_words}")
print(f"Text words: {text_words}")

# Test word similarity
for query_word in query_words:
    for text_word in text_words:
        similar = search_service._words_similar(query_word, text_word)
        print(f"'{query_word}' similar to '{text_word}': {similar}")

# Test fuzzy matching
fuzzy_score = search_service._fuzzy_text_match(query_words, text_words)
print(f"\nFuzzy match score: {fuzzy_score}")