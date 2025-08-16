import base64
import json
import uuid
from datetime import timedelta
from io import BytesIO
from PIL import Image
from django.conf import settings
from django.utils import timezone
from anthropic import Anthropic
import django_rq
from .models import Screenshot, BatchJob, BatchRequest


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


def queue_batch_processing(screenshot_ids, user_id):
    """Queue multiple screenshots for batch processing with Claude API."""
    # Create batch job record
    batch_job = BatchJob.objects.create(
        user_id=user_id,
        batch_id=str(uuid.uuid4()),
        status='pending',
        total_requests=len(screenshot_ids),
        metadata={'screenshot_ids': screenshot_ids}
    )
    
    # Queue the batch processing task
    queue = django_rq.get_queue('default')
    job = queue.enqueue(process_batch_with_claude, batch_job.id)
    
    return batch_job.batch_id


def process_batch_with_claude(batch_job_id):
    """Django-RQ task to process multiple screenshots using Claude's Batch API."""
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        batch_job.status = 'processing'
        batch_job.save()
        
        screenshot_ids = batch_job.metadata.get('screenshot_ids', [])
        screenshots = Screenshot.objects.filter(id__in=screenshot_ids)
        
        # Update all screenshots to processing status
        screenshots.update(processing_status='processing')
        
        # Initialize Anthropic client
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Prepare batch requests
        batch_requests = []
        for screenshot in screenshots:
            try:
                # Convert image to base64
                image_data = encode_image_to_base64(screenshot.image.path)
                
                # Create batch request
                request_data = {
                    "custom_id": f"screenshot_{screenshot.id}",
                    "params": {
                        "model": "claude-3-7-sonnet-20250219",
                        "max_tokens": 2000,
                        "messages": [
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
                                        "text": get_analysis_prompt()
                                    }
                                ]
                            }
                        ]
                    }
                }
                
                batch_requests.append(request_data)
                
                # Create BatchRequest record
                BatchRequest.objects.create(
                    batch_job=batch_job,
                    screenshot=screenshot,
                    custom_id=f"screenshot_{screenshot.id}",
                    status='pending'
                )
                
            except Exception as e:
                # Mark individual screenshot as failed
                screenshot.processing_status = 'failed'
                screenshot.processing_error = f"Batch preparation error: {str(e)}"
                screenshot.save()
        
        # Submit batch to Claude API
        batch_response = client.messages.batches.create(
            requests=batch_requests
        )
        
        # Update batch job with Claude batch ID
        batch_job.claude_batch_id = batch_response.id
        batch_job.status = 'submitted'
        batch_job.save()
        
        # Queue polling task to check batch completion
        queue = django_rq.get_queue('default')
        queue.enqueue_in(
            timedelta(minutes=5),  # Check after 5 minutes
            poll_batch_completion,
            batch_job.id
        )
        
        return f"Batch job {batch_job.batch_id} submitted with {len(batch_requests)} requests"
        
    except Exception as e:
        # Update batch job with error status
        try:
            batch_job = BatchJob.objects.get(id=batch_job_id)
            batch_job.status = 'failed'
            batch_job.error_message = str(e)
            batch_job.save()
            
            # Mark all associated screenshots as failed
            screenshot_ids = batch_job.metadata.get('screenshot_ids', [])
            Screenshot.objects.filter(id__in=screenshot_ids).update(
                processing_status='failed',
                processing_error=f"Batch processing error: {str(e)}"
            )
        except:
            pass
        
        return f"Error processing batch {batch_job_id}: {str(e)}"


def poll_batch_completion(batch_job_id):
    """Poll Claude API for batch completion and process results."""
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        
        if not batch_job.claude_batch_id:
            return "No Claude batch ID found"
        
        # Initialize Anthropic client
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        
        # Check batch status
        batch_status = client.messages.batches.retrieve(batch_job.claude_batch_id)
        
        if batch_status.processing_status == 'completed':
            # Process completed batch results
            return process_batch_results(batch_job.id, batch_status)
        elif batch_status.processing_status == 'failed':
            # Handle batch failure
            batch_job.status = 'failed'
            batch_job.error_message = "Claude batch processing failed"
            batch_job.save()
            
            # Mark all screenshots as failed
            screenshot_ids = batch_job.metadata.get('screenshot_ids', [])
            Screenshot.objects.filter(id__in=screenshot_ids).update(
                processing_status='failed',
                processing_error="Batch processing failed"
            )
            
            return "Batch processing failed"
        else:
            # Still processing, schedule another poll
            queue = django_rq.get_queue('default')
            queue.enqueue_in(
                timedelta(minutes=5),
                poll_batch_completion,
                batch_job_id
            )
            return f"Batch still processing, status: {batch_status.processing_status}"
            
    except Exception as e:
        return f"Error polling batch completion: {str(e)}"


def process_batch_results(batch_job_id, batch_status):
    """Process completed batch results and update screenshots."""
    try:
        batch_job = BatchJob.objects.get(id=batch_job_id)
        
        # Get batch results
        client = Anthropic(api_key=settings.ANTHROPIC_API_KEY)
        results = client.messages.batches.results(batch_job.claude_batch_id)
        
        processed_count = 0
        failed_count = 0
        
        for result in results:
            try:
                custom_id = result.custom_id
                screenshot_id = int(custom_id.replace('screenshot_', ''))
                
                screenshot = Screenshot.objects.get(id=screenshot_id)
                batch_request = BatchRequest.objects.get(
                    batch_job=batch_job,
                    custom_id=custom_id
                )
                
                if result.result.type == 'succeeded':
                    # Process successful result
                    response_text = result.result.message.content[0].text
                    analysis_result = parse_claude_response(response_text)
                    
                    # Update screenshot with analysis results
                    screenshot.extracted_text = analysis_result.get('extracted_text', '')
                    screenshot.visual_description = analysis_result.get('visual_description', '')
                    screenshot.ui_elements = analysis_result.get('ui_elements', [])
                    screenshot.dominant_colors = analysis_result.get('dominant_colors', [])
                    screenshot.error_states = analysis_result.get('error_states', [])
                    screenshot.visual_patterns = analysis_result.get('visual_patterns', [])
                    screenshot.color_context = analysis_result.get('color_context', {})
                    screenshot.processing_status = 'completed'
                    screenshot.processed_at = timezone.now()
                    screenshot.save()
                    
                    # Update batch request
                    batch_request.status = 'completed'
                    batch_request.response_data = analysis_result
                    batch_request.save()
                    
                    processed_count += 1
                    
                else:
                    # Handle failed result
                    error_message = getattr(result.result, 'error', {}).get('message', 'Unknown error')
                    screenshot.processing_status = 'failed'
                    screenshot.processing_error = f"Batch processing error: {error_message}"
                    screenshot.save()
                    
                    batch_request.status = 'failed'
                    batch_request.error_message = error_message
                    batch_request.save()
                    
                    failed_count += 1
                    
            except Exception as e:
                failed_count += 1
                print(f"Error processing batch result for {custom_id}: {str(e)}")
        
        # Update batch job status
        batch_job.status = 'completed'
        batch_job.completed_at = timezone.now()
        batch_job.processed_requests = processed_count
        batch_job.failed_requests = failed_count
        batch_job.save()
        
        return f"Batch processing completed: {processed_count} successful, {failed_count} failed"
        
    except Exception as e:
        return f"Error processing batch results: {str(e)}"


def get_analysis_prompt():
    """Get the analysis prompt for Claude API."""
    return """
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


def parse_claude_response(response_text):
    """Parse Claude's response and extract structured data."""
    try:
        # Look for JSON in the response
        json_start = response_text.find('{')
        json_end = response_text.rfind('}') + 1
        
        if json_start != -1 and json_end != -1:
            json_str = response_text[json_start:json_end]
            return json.loads(json_str)
        else:
            # Fallback: create structured data from text response
            return parse_text_response(response_text)
    
    except json.JSONDecodeError:
        # Fallback parsing if JSON is malformed
        return parse_text_response(response_text)