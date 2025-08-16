import re
from datetime import datetime, timedelta
from django.db.models import Q
from django.utils import timezone
from .models import Screenshot, SearchResult


class ScreenshotSearchService:
    """Service for searching screenshots using natural language queries with confidence scoring."""
    
    def __init__(self, user=None):
        self.user = user
        # Enhanced confidence weights for better visual pattern recognition
        self.weights = {
            'text': 0.25,           # 25% - Text matching
            'visual': 0.20,         # 20% - Visual description matching
            'ui': 0.15,             # 15% - UI elements matching
            'color': 0.10,          # 10% - Color matching
            'error_states': 0.15,   # 15% - Error state matching
            'visual_patterns': 0.10, # 10% - Visual pattern matching
            'color_context': 0.05   # 5% - Color-context association
        }
    
    def search(self, query, limit=5):
        """Search screenshots and return top results with confidence scores."""
        # Get completed screenshots for the user
        screenshots = Screenshot.objects.filter(processing_status='completed')
        if self.user:
            screenshots = screenshots.filter(user=self.user)
        
        # Apply timestamp filtering if query contains time-related terms
        time_filter = self._parse_time_query(query)
        if time_filter:
            screenshots = screenshots.filter(time_filter)
        
        results = []
        
        for screenshot in screenshots:
            # Calculate confidence scores for each category
            text_conf = self._calculate_text_confidence(query, screenshot)
            visual_conf = self._calculate_visual_confidence(query, screenshot)
            ui_conf = self._calculate_ui_confidence(query, screenshot)
            color_conf = self._calculate_color_confidence(query, screenshot)
            error_states_conf = self._calculate_error_states_confidence(query, screenshot)
            visual_patterns_conf = self._calculate_visual_patterns_confidence(query, screenshot)
            color_context_conf = self._calculate_color_context_confidence(query, screenshot)
            
            # Calculate overall confidence
            overall_conf = (
                text_conf * self.weights['text'] +
                visual_conf * self.weights['visual'] +
                ui_conf * self.weights['ui'] +
                color_conf * self.weights['color'] +
                error_states_conf * self.weights['error_states'] +
                visual_patterns_conf * self.weights['visual_patterns'] +
                color_context_conf * self.weights['color_context']
            )
            
            # Only include results with meaningful confidence
            if overall_conf > 0.1:  # 10% minimum threshold
                # Create or update search result
                search_result, created = SearchResult.objects.get_or_create(
                    screenshot=screenshot,
                    query=query,
                    defaults={
                        'text_confidence': text_conf,
                        'visual_confidence': visual_conf,
                        'ui_confidence': ui_conf,
                        'color_confidence': color_conf,
                        'overall_confidence': overall_conf,
                    }
                )
                
                if not created:
                    # Update existing result
                    search_result.text_confidence = text_conf
                    search_result.visual_confidence = visual_conf
                    search_result.ui_confidence = ui_conf
                    search_result.color_confidence = color_conf
                    search_result.overall_confidence = overall_conf
                    search_result.save()
                
                results.append(search_result)
        
        # Sort by confidence and return top results
        results.sort(key=lambda x: x.overall_confidence, reverse=True)
        return results[:limit]
    
    def _calculate_text_confidence(self, query, screenshot):
        """Calculate confidence score for text matching."""
        if not screenshot.extracted_text:
            return 0.0
        
        query_lower = query.lower()
        text_lower = screenshot.extracted_text.lower()
        
        # Exact phrase matching (highest score)
        if query_lower in text_lower:
            return 1.0
        
        # Enhanced CaseId matching - handle variations like "Case ID", "Case_Id", "CaseId"
        caseid_confidence = self._calculate_caseid_confidence(query_lower, text_lower)
        if caseid_confidence > 0:
            return caseid_confidence
        
        # Word-by-word matching
        query_words = self._extract_words(query_lower)
        text_words = self._extract_words(text_lower)
        
        if not query_words:
            return 0.0
        
        matched_words = 0
        for word in query_words:
            if word in text_words:
                matched_words += 1
        
        # Calculate partial match score
        word_match_ratio = matched_words / len(query_words)
        
        # Fuzzy matching for similar words
        fuzzy_score = self._fuzzy_text_match(query_words, text_words)
        
        # Combine scores (exact match gets priority)
        return max(word_match_ratio * 0.8, fuzzy_score * 0.6)
    
    def _calculate_error_states_confidence(self, query, screenshot):
        """Calculate confidence score for error states matching."""
        if not screenshot.error_states:
            return 0.0
        
        query_lower = query.lower()
        error_states = [state.lower() for state in screenshot.error_states]
        
        # Error-related keywords in query
        error_keywords = [
            'error', 'fail', 'failed', 'failure', 'problem', 'issue',
            'blocked', 'denied', 'forbidden', 'unauthorized', 'invalid',
            'timeout', 'expired', 'unavailable', 'down', 'offline',
            'warning', 'alert', 'critical', 'exception', 'crash'
        ]
        
        # Direct error state matching
        for error_state in error_states:
            if query_lower in error_state or error_state in query_lower:
                return 1.0
        
        # Keyword-based matching
        query_words = self._extract_words(query_lower)
        error_word_matches = 0
        total_error_words = 0
        
        for word in query_words:
            if word in error_keywords:
                total_error_words += 1
                # Check if this error keyword relates to any error state
                for error_state in error_states:
                    if word in error_state or any(keyword in error_state for keyword in error_keywords):
                        error_word_matches += 1
                        break
        
        if total_error_words > 0:
            return error_word_matches / total_error_words * 0.9
        
        return 0.0
    
    def _parse_time_query(self, query):
        """Parse time-related terms in query and return Django Q filter."""
        query_lower = query.lower()
        now = timezone.now()
        
        # Check for temporal question patterns that should focus on content matching
        temporal_question_patterns = [
            r'\bwhen did i take\b',
            r'\bwhen was this taken\b',
            r'\bwhen did i capture\b',
            r'\bwhen did i screenshot\b',
            r'\bwhat time did i\b',
            r'\bwhen did i save\b',
            r'\bwhen did i get\b'
        ]
        
        # If query matches temporal question patterns, return None to focus on content
        for pattern in temporal_question_patterns:
            if re.search(pattern, query_lower):
                return None
        
        # Time-based keywords and their corresponding time ranges
        time_patterns = {
            # Recent patterns
            r'\b(recent|recently)\b': timedelta(days=7),  # Last 7 days
            r'\btoday\b': timedelta(days=1),
            r'\byesterday\b': (timedelta(days=2), timedelta(days=1)),  # Between 1-2 days ago
            
            # Week patterns
            r'\blast week\b': (timedelta(days=14), timedelta(days=7)),  # 7-14 days ago
            r'\bthis week\b': timedelta(days=7),
            r'\bpast week\b': timedelta(days=7),
            
            # Month patterns
            r'\blast month\b': (timedelta(days=60), timedelta(days=30)),  # 30-60 days ago
            r'\bthis month\b': timedelta(days=30),
            r'\bpast month\b': timedelta(days=30),
            
            # Day patterns
            r'\blast (\d+) days?\b': None,  # Will be handled separately
            r'\bpast (\d+) days?\b': None,  # Will be handled separately
            
            # Hour patterns
            r'\blast (\d+) hours?\b': None,  # Will be handled separately
            r'\bpast (\d+) hours?\b': None,  # Will be handled separately
        }
        
        # Check for specific numeric patterns first
        numeric_day_match = re.search(r'\b(?:last|past) (\d+) days?\b', query_lower)
        if numeric_day_match:
            days = int(numeric_day_match.group(1))
            start_time = now - timedelta(days=days)
            return Q(uploaded_at__gte=start_time)
        
        numeric_hour_match = re.search(r'\b(?:last|past) (\d+) hours?\b', query_lower)
        if numeric_hour_match:
            hours = int(numeric_hour_match.group(1))
            start_time = now - timedelta(hours=hours)
            return Q(uploaded_at__gte=start_time)
        
        # Check for predefined patterns
        for pattern, time_range in time_patterns.items():
            if re.search(pattern, query_lower):
                if isinstance(time_range, tuple):
                    # Range filter (between two times)
                    start_time = now - time_range[0]
                    end_time = now - time_range[1]
                    return Q(uploaded_at__gte=end_time, uploaded_at__lte=start_time)
                elif time_range:
                    # Simple filter (from time_range ago to now)
                    start_time = now - time_range
                    return Q(uploaded_at__gte=start_time)
        
        # Check for file timestamp-based queries if available
        if any(keyword in query_lower for keyword in ['created', 'modified', 'file']):
            # Use file timestamps if available
            if 'created' in query_lower:
                for pattern, time_range in time_patterns.items():
                    if re.search(pattern, query_lower):
                        if isinstance(time_range, tuple):
                            start_time = now - time_range[0]
                            end_time = now - time_range[1]
                            return Q(file_created_at__gte=end_time, file_created_at__lte=start_time)
                        elif time_range:
                            start_time = now - time_range
                            return Q(file_created_at__gte=start_time)
            
            if 'modified' in query_lower:
                for pattern, time_range in time_patterns.items():
                    if re.search(pattern, query_lower):
                        if isinstance(time_range, tuple):
                            start_time = now - time_range[0]
                            end_time = now - time_range[1]
                            return Q(file_modified_at__gte=end_time, file_modified_at__lte=start_time)
                        elif time_range:
                            start_time = now - time_range
                            return Q(file_modified_at__gte=start_time)
        
        return None
    
    def _calculate_visual_patterns_confidence(self, query, screenshot):
        """Calculate confidence score for visual patterns matching."""
        if not screenshot.visual_patterns:
            return 0.0
        
        query_lower = query.lower()
        visual_patterns = [pattern.lower() for pattern in screenshot.visual_patterns]
        
        # Direct pattern matching
        for pattern in visual_patterns:
            if query_lower in pattern or pattern in query_lower:
                return 0.95
        
        # Pattern-related keywords
        pattern_keywords = [
            'layout', 'design', 'style', 'appearance', 'look', 'visual',
            'interface', 'ui', 'ux', 'theme', 'color', 'background',
            'border', 'shadow', 'gradient', 'animation', 'transition'
        ]
        
        query_words = self._extract_words(query_lower)
        pattern_matches = 0
        total_pattern_words = 0
        
        for word in query_words:
            if word in pattern_keywords:
                total_pattern_words += 1
                for pattern in visual_patterns:
                    if word in pattern:
                        pattern_matches += 1
                        break
        
        if total_pattern_words > 0:
            return pattern_matches / total_pattern_words * 0.8
        
        return 0.0
    
    def _calculate_color_context_confidence(self, query, screenshot):
        """Calculate confidence score for color-context associations."""
        if not screenshot.color_context:
            return 0.0
        
        query_lower = query.lower()
        
        # Enhanced color-context mapping for better error recognition
        context_mappings = {
            'error': ['red', 'danger', 'critical', 'fail'],
            'success': ['green', 'ok', 'pass', 'complete'],
            'warning': ['yellow', 'orange', 'caution', 'alert'],
            'info': ['blue', 'information', 'notice'],
            'blocked': ['red', 'stop', 'forbidden', 'denied'],
            'loading': ['blue', 'progress', 'wait'],
            'disabled': ['gray', 'inactive', 'unavailable']
        }
        
        # Check for color-context associations
        for color, context in screenshot.color_context.items():
            color_lower = color.lower()
            context_lower = context.lower()
            
            # Direct matching
            if (color_lower in query_lower and context_lower in query_lower) or \
               (query_lower in context_lower):
                return 1.0
            
            # Semantic matching using context mappings
            for query_context, related_colors in context_mappings.items():
                if query_context in query_lower:
                    if color_lower in related_colors or any(rc in color_lower for rc in related_colors):
                        # Special boost for error-red associations
                        if query_context == 'error' and 'red' in color_lower:
                            return 0.95
                        return 0.8
                    if any(rc in context_lower for rc in related_colors):
                        return 0.7
        
        return 0.0
        
        query_lower = query.lower()
        text_lower = screenshot.extracted_text.lower()
        
        # Exact phrase matching (highest score)
        if query_lower in text_lower:
            return 1.0
        
        # Enhanced CaseId matching - handle variations like "Case ID", "Case_Id", "CaseId"
        caseid_confidence = self._calculate_caseid_confidence(query_lower, text_lower)
        if caseid_confidence > 0:
            return caseid_confidence
        
        # Word-by-word matching
        query_words = self._extract_words(query_lower)
        text_words = self._extract_words(text_lower)
        
        if not query_words:
            return 0.0
        
        matched_words = 0
        for word in query_words:
            if word in text_words:
                matched_words += 1
        
        # Calculate partial match score
        word_match_ratio = matched_words / len(query_words)
        
        # Fuzzy matching for similar words
        fuzzy_score = self._fuzzy_text_match(query_words, text_words)
        
        # Combine scores (exact match gets priority)
        return max(word_match_ratio * 0.8, fuzzy_score * 0.6)
    
    def _calculate_visual_confidence(self, query, screenshot):
        """Calculate confidence score for visual description matching."""
        if not screenshot.visual_description:
            return 0.0
        
        query_lower = query.lower()
        description_lower = screenshot.visual_description.lower()
        
        # Check for visual keywords in query
        visual_keywords = [
            'button', 'menu', 'form', 'dialog', 'popup', 'modal',
            'header', 'footer', 'sidebar', 'navigation', 'nav',
            'card', 'panel', 'widget', 'icon', 'image', 'photo',
            'layout', 'design', 'interface', 'ui', 'screen',
            'page', 'website', 'app', 'application'
        ]
        
        # Exact phrase matching
        if query_lower in description_lower:
            return 0.9
        
        # Keyword matching
        query_words = self._extract_words(query_lower)
        description_words = self._extract_words(description_lower)
        
        visual_word_matches = 0
        total_visual_words = 0
        
        for word in query_words:
            if word in visual_keywords:
                total_visual_words += 1
                if word in description_words:
                    visual_word_matches += 1
        
        if total_visual_words > 0:
            return visual_word_matches / total_visual_words * 0.8
        
        # Enhanced content matching for temporal queries
        # Check if any individual content words have exact matches in description
        content_matches = 0
        content_words = 0
        
        for word in query_words:
            # Skip generic words like 'picture', 'image', 'photo' for content matching
            if word not in ['picture', 'image', 'photo', 'screenshot']:
                content_words += 1
                # Check for exact word match or if word appears in description
                if word in description_words or word in description_lower:
                    content_matches += 1
        
        # If we have content matches, give higher confidence
        if content_words > 0 and content_matches > 0:
            content_confidence = (content_matches / content_words) * 0.8
            # For temporal queries, prioritize content matches
            if any(pattern in query_lower for pattern in ['when did', 'what time', 'when was']):
                return content_confidence
        
        # General word matching
        if query_words:
            matched_words = sum(1 for word in query_words if word in description_words)
            return (matched_words / len(query_words)) * 0.6
        
        return 0.0
    
    def _calculate_ui_confidence(self, query, screenshot):
        """Calculate confidence score for UI elements matching."""
        if not screenshot.ui_elements:
            return 0.0
        
        query_lower = query.lower()
        ui_elements = [elem.lower() for elem in screenshot.ui_elements]
        
        # Direct UI element matching
        ui_keywords = [
            'button', 'link', 'menu', 'dropdown', 'select', 'input',
            'form', 'field', 'checkbox', 'radio', 'toggle', 'switch',
            'tab', 'accordion', 'modal', 'dialog', 'popup', 'tooltip',
            'icon', 'badge', 'alert', 'notification', 'banner'
        ]
        
        query_words = self._extract_words(query_lower)
        
        ui_matches = 0
        total_ui_words = 0
        
        for word in query_words:
            if word in ui_keywords:
                total_ui_words += 1
                if word in ui_elements or any(word in elem for elem in ui_elements):
                    ui_matches += 1
        
        if total_ui_words > 0:
            return ui_matches / total_ui_words
        
        return 0.0
    
    def _calculate_color_confidence(self, query, screenshot):
        """Calculate confidence score for color matching."""
        if not screenshot.dominant_colors:
            return 0.0
        
        query_lower = query.lower()
        
        # Color name mapping
        color_names = {
            'red': ['#ff0000', '#dc3545', '#e74c3c', '#c0392b'],
            'blue': ['#0000ff', '#007bff', '#3498db', '#2980b9'],
            'green': ['#00ff00', '#28a745', '#2ecc71', '#27ae60'],
            'yellow': ['#ffff00', '#ffc107', '#f1c40f', '#f39c12'],
            'orange': ['#ffa500', '#fd7e14', '#e67e22', '#d35400'],
            'purple': ['#800080', '#6f42c1', '#9b59b6', '#8e44ad'],
            'pink': ['#ffc0cb', '#e91e63', '#e83e8c'],
            'black': ['#000000', '#343a40', '#2c3e50'],
            'white': ['#ffffff', '#f8f9fa', '#ecf0f1'],
            'gray': ['#808080', '#6c757d', '#95a5a6', '#7f8c8d'],
            'brown': ['#a52a2a', '#8b4513', '#d2691e']
        }
        
        # Check for color names in query
        for color_name, color_codes in color_names.items():
            if color_name in query_lower:
                # Check if any of the associated color codes match
                for color_code in color_codes:
                    if color_code.lower() in [c.lower() for c in screenshot.dominant_colors]:
                        return 0.8
                # Partial match for similar colors
                return 0.3
        
        # Check for hex color codes in query
        hex_pattern = r'#[0-9a-fA-F]{6}'
        query_colors = re.findall(hex_pattern, query)
        
        if query_colors:
            for query_color in query_colors:
                if query_color.lower() in [c.lower() for c in screenshot.dominant_colors]:
                    return 1.0
        
        return 0.0
    
    def _extract_words(self, text):
        """Extract meaningful words from text."""
        # Remove punctuation and split into words
        words = re.findall(r'\b\w+\b', text.lower())
        
        # Filter out common stop words but keep temporal question words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to',
            'for', 'of', 'with', 'by', 'is', 'are', 'was', 'were', 'be',
            'been', 'being', 'have', 'has', 'had', 'do', 'does', 'did',
            'will', 'would', 'could', 'should', 'may', 'might', 'must',
            'this', 'that', 'these', 'those', 'i', 'you', 'he', 'she',
            'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them',
            # Temporal question words to filter out
            'when', 'what', 'time', 'take', 'taken', 'capture', 'captured',
            'screenshot', 'save', 'saved', 'get'
        }
        
        return [word for word in words if word not in stop_words and len(word) > 2]
    
    def _fuzzy_text_match(self, query_words, text_words):
        """Calculate fuzzy matching score for similar words."""
        if not query_words or not text_words:
            return 0.0
        
        matches = 0
        for query_word in query_words:
            for text_word in text_words:
                # Simple similarity check (can be enhanced with Levenshtein distance)
                if self._words_similar(query_word, text_word):
                    matches += 1
                    break
        
        return matches / len(query_words)
    
    def _words_similar(self, word1, word2, threshold=0.8):
        """Check if two words are similar (simple implementation)."""
        if len(word1) < 3 or len(word2) < 3:
            return word1 == word2
        
        # Check for substring matches
        if word1 in word2 or word2 in word1:
            return True
        
        # Check for common prefix/suffix
        if (word1[:3] == word2[:3] and len(word1) > 4 and len(word2) > 4):
            return True
        
        return False
    
    def _calculate_caseid_confidence(self, query_lower, text_lower):
        """Calculate confidence for CaseId variations matching."""
        import re
        
        # Define CaseId patterns to look for in query
        caseid_patterns = [
            r'\bcaseid\b',
            r'\bcase\s*id\b',
            r'\bcase[_-]id\b'
        ]
        
        # Check if query contains any CaseId pattern
        query_has_caseid = False
        for pattern in caseid_patterns:
            if re.search(pattern, query_lower):
                query_has_caseid = True
                break
        
        if not query_has_caseid:
            return 0.0
        
        # Define patterns to find in text
        text_caseid_patterns = [
            r'\bcaseid\b',
            r'\bcase\s+id\b',
            r'\bcase[_-]id\b'
        ]
        
        # Check if text contains any CaseId variation
        for pattern in text_caseid_patterns:
            if re.search(pattern, text_lower):
                return 0.95  # High confidence for CaseId matches
        
        return 0.0