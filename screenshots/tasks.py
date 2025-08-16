import base64
import json
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.utils import timezone
from anthropic import Anthropic
import django_rq
from .models import Screenshot


def process_screenshot_with_claude(screenshot_id):
    """Django-RQ task to process screenshot with Claude API for OCR and visual analysis."""
    try:
        screenshot = Screenshot.objects.get(id=screenshot_id)
        screenshot.processing_status = 'processing'
        screenshot.save()
        
        # Initialize Anthropic client
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Convert image to base64
        image_data = encode_image_to_base64(screenshot.image.path)
        
        # Prepare the enhanced prompt for Claude with focus on visual patterns and error states
        ocr_prompt = """
        Please analyze this screenshot with special attention to visual patterns, error states, and contextual associations. Provide:
        
        1. **Extracted Text**: All visible text in the image, including:
           - UI labels, buttons, menu items
           - Body text, headings, captions
           - Error messages, notifications, alerts, warnings
           - Status messages, confirmations, system responses
           - Any other readable text
        
        2. **Visual Description**: Describe the visual elements with emphasis on:
           - Overall layout and design patterns
           - Error states, warning indicators, success states
           - Visual hierarchy and emphasis (bold, highlighted, colored text)
           - Color-coded elements and their contextual meaning
           - Loading states, blocked states, disabled elements
           - Icons that indicate status (error icons, warning triangles, checkmarks)
           - Visual patterns that suggest system states or user feedback
        
        3. **UI Elements**: List interactive and visual elements, categorizing by state:
           - Buttons (normal, disabled, error, success states)
           - Form fields (valid, invalid, required, error states)
           - Navigation menus, tabs, breadcrumbs
           - Icons, images, graphics (especially status indicators)
           - Modal dialogs, popups, alerts, notifications
           - Progress indicators, loading spinners
           - Error banners, warning messages, success confirmations
        
        4. **Dominant Colors**: Identify colors and their contextual associations:
           - Background colors and their mood/state implications
           - Text colors (especially red for errors, green for success, yellow for warnings)
           - Accent colors and their semantic meaning
           - Brand colors if visible
           - Color patterns that indicate system states (red borders for errors, etc.)
        
        5. **Error and State Detection**: Specifically identify:
           - Error messages and their visual presentation
           - Warning states and indicators
           - Success confirmations and positive feedback
           - Loading or processing states
           - Blocked, disabled, or unavailable states
           - System status indicators
        
        6. **Visual Context Associations**: Note relationships between:
           - Colors and their meanings (red=error, green=success, yellow=warning, blue=info)
           - Visual patterns and system states
           - Text content and visual presentation
           - Icons and their contextual meaning
        
        Please format your response as JSON with the following structure:
        {
            "extracted_text": "All visible text...",
            "visual_description": "Description focusing on visual patterns, states, and contextual elements...",
            "ui_elements": ["button", "error_banner", "warning_icon", "success_message", ...],
            "dominant_colors": ["#ffffff", "#000000", "#ff0000", ...],
            "error_states": ["IP blocked error", "connection timeout", "validation failed", ...],
            "visual_patterns": ["red error styling", "warning triangle icon", "disabled button state", ...],
            "color_context": {"#ff0000": "error indication", "#00ff00": "success state", "#ffaa00": "warning"}
        }
        """
        
        # Make API call to Claude
        message = client.messages.create(
            model="claude-3-7-sonnet-20250219",
            max_tokens=2000,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": "image/jpeg",
                                "data": image_data
                            }
                        },
                        {
                            "type": "text",
                            "text": ocr_prompt
                        }
                    ]
                }
            ]
        )
        
        # Parse Claude's response
        response_text = message.content[0].text
        
        # Try to extract JSON from the response
        try:
            # Look for JSON in the response
            json_start = response_text.find('{')
            json_end = response_text.rfind('}') + 1
            
            if json_start != -1 and json_end != -1:
                json_str = response_text[json_start:json_end]
                analysis_result = json.loads(json_str)
            else:
                # Fallback: create structured data from text response
                analysis_result = parse_text_response(response_text)
        
        except json.JSONDecodeError:
            # Fallback parsing if JSON is malformed
            analysis_result = parse_text_response(response_text)
        
        # Update screenshot with analysis results
        screenshot.extracted_text = analysis_result.get('extracted_text', '')
        screenshot.visual_description = analysis_result.get('visual_description', '')
        screenshot.ui_elements = analysis_result.get('ui_elements', [])
        screenshot.dominant_colors = analysis_result.get('dominant_colors', [])
        # Enhanced visual pattern analysis fields
        screenshot.error_states = analysis_result.get('error_states', [])
        screenshot.visual_patterns = analysis_result.get('visual_patterns', [])
        screenshot.color_context = analysis_result.get('color_context', {})
        screenshot.processing_status = 'completed'
        screenshot.processed_at = timezone.now()
        screenshot.save()
        
        return f"Successfully processed screenshot {screenshot.filename}"
        
    except Screenshot.DoesNotExist:
        return f"Screenshot with id {screenshot_id} not found"
    
    except Exception as e:
        # Update screenshot with error status
        try:
            screenshot = Screenshot.objects.get(id=screenshot_id)
            screenshot.processing_status = 'failed'
            screenshot.processing_error = str(e)
            screenshot.save()
        except:
            pass
        
        return f"Error processing screenshot {screenshot_id}: {str(e)}"


def encode_image_to_base64(image_path):
    """Convert image file to base64 string for Claude API."""
    with Image.open(image_path) as img:
        # Convert to RGB if necessary
        if img.mode != 'RGB':
            img = img.convert('RGB')
        
        # Resize if too large (Claude has size limits)
        max_size = (1024, 1024)
        img.thumbnail(max_size, Image.Resampling.LANCZOS)
        
        # Convert to base64
        buffer = BytesIO()
        img.save(buffer, format='JPEG', quality=85)
        img_data = buffer.getvalue()
        
        return base64.b64encode(img_data).decode('utf-8')


def parse_text_response(response_text):
    """Fallback parser for non-JSON responses from Claude."""
    result = {
        'extracted_text': '',
        'visual_description': '',
        'ui_elements': [],
        'dominant_colors': [],
        'error_states': [],
        'visual_patterns': [],
        'color_context': {}
    }
    
    # Simple text parsing logic
    lines = response_text.split('\n')
    current_section = None
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # Detect sections
        if 'extracted text' in line.lower():
            current_section = 'extracted_text'
        elif 'visual description' in line.lower():
            current_section = 'visual_description'
        elif 'ui elements' in line.lower():
            current_section = 'ui_elements'
        elif 'dominant colors' in line.lower():
            current_section = 'dominant_colors'
        elif 'error states' in line.lower() or 'error and state' in line.lower():
            current_section = 'error_states'
        elif 'visual patterns' in line.lower():
            current_section = 'visual_patterns'
        elif 'color context' in line.lower() or 'visual context' in line.lower():
            current_section = 'color_context'
        elif current_section:
            # Add content to current section
            if current_section == 'extracted_text':
                result['extracted_text'] += line + ' '
            elif current_section == 'visual_description':
                result['visual_description'] += line + ' '
            elif current_section == 'ui_elements':
                # Extract UI elements (simple parsing)
                if line.startswith('-') or line.startswith('*'):
                    element = line.lstrip('-* ').lower()
                    if element:
                        result['ui_elements'].append(element)
            elif current_section == 'dominant_colors':
                # Extract color codes
                import re
                colors = re.findall(r'#[0-9a-fA-F]{6}', line)
                result['dominant_colors'].extend(colors)
            elif current_section == 'error_states':
                # Extract error states
                if line.startswith('-') or line.startswith('*'):
                    error_state = line.lstrip('-* ').strip()
                    if error_state:
                        result['error_states'].append(error_state)
            elif current_section == 'visual_patterns':
                # Extract visual patterns
                if line.startswith('-') or line.startswith('*'):
                    pattern = line.lstrip('-* ').strip()
                    if pattern:
                        result['visual_patterns'].append(pattern)
            elif current_section == 'color_context':
                # Extract color-context associations
                import re
                # Look for patterns like "#ff0000: error indication" or "red: error"
                color_context_match = re.search(r'(#[0-9a-fA-F]{6}|\b\w+\b)\s*[:=]\s*(.+)', line)
                if color_context_match:
                    color, context = color_context_match.groups()
                    result['color_context'][color.strip()] = context.strip()
    
    # Clean up text fields
    result['extracted_text'] = result['extracted_text'].strip()
    result['visual_description'] = result['visual_description'].strip()
    
    return result


def queue_screenshot_processing(screenshot_id):
    """Queue a screenshot for processing with Claude API."""
    queue = django_rq.get_queue('default')
    job = queue.enqueue(process_screenshot_with_claude, screenshot_id)
    return job.id