from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from django.conf import settings
import json
import os
import tempfile
from datetime import datetime

from .models import Screenshot, SearchResult, BatchJob
from .tasks import queue_screenshot_processing, queue_batch_processing
from .search import ScreenshotSearchService


@login_required
def home(request):
    """Home page with upload interface and recent screenshots."""
    recent_screenshots = Screenshot.objects.filter(
        user=request.user,
        processing_status='completed'
    ).order_by('-file_created_at')[:6]
    
    context = {
        'recent_screenshots': recent_screenshots,
        'total_screenshots': Screenshot.objects.filter(user=request.user).count(),
        'processing_count': Screenshot.objects.filter(user=request.user, processing_status='processing').count(),
    }
    
    return render(request, 'screenshots/home.html', context)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def upload_screenshots(request):
    """Handle bulk screenshot upload via AJAX."""
    if not request.FILES:
        return JsonResponse({'error': 'No files uploaded'}, status=400)
    
    uploaded_files = []
    errors = []
    
    for file_key in request.FILES:
        file = request.FILES[file_key]
        
        # Validate file type
        if not file.content_type.startswith('image/'):
            errors.append(f'{file.name}: Not a valid image file')
            continue
        
        # Validate file size (10MB limit)
        if file.size > 10 * 1024 * 1024:
            errors.append(f'{file.name}: File too large (max 10MB)')
            continue
        
        try:
            # Extract file metadata timestamps if available
            file_created_at = None
            file_modified_at = None
            
            # Try to extract timestamps from form data (sent by frontend)
            file_last_modified = request.POST.get('file_last_modified')
            file_last_modified_date = request.POST.get('file_last_modified_date')
            
            if file_last_modified:
                try:
                    # Convert milliseconds timestamp to datetime
                    file_modified_at = datetime.fromtimestamp(int(file_last_modified) / 1000, tz=timezone.get_current_timezone())
                except (ValueError, TypeError):
                    pass
            elif file_last_modified_date:
                try:
                    # Parse ISO date string
                    file_modified_at = datetime.fromisoformat(file_last_modified_date.replace('Z', '+00:00'))
                    if timezone.is_naive(file_modified_at):
                        file_modified_at = timezone.make_aware(file_modified_at)
                except (ValueError, TypeError):
                    pass
            
            # For now, use modified time as created time if not available separately
            if file_modified_at and not file_created_at:
                file_created_at = file_modified_at
            
            # Create screenshot record
            screenshot = Screenshot.objects.create(
                user=request.user,
                image=file,
                filename=file.name,
                file_size=file.size,
                file_created_at=file_created_at,
                file_modified_at=file_modified_at
            )
            
            uploaded_files.append({
                'id': screenshot.id,
                'filename': screenshot.filename,
                'status': 'queued'
            })
            
        except Exception as e:
            errors.append(f'{file.name}: {str(e)}')
    
    # Decide on processing strategy based on number of uploaded files
    batch_threshold = getattr(settings, 'BATCH_PROCESSING_THRESHOLD', 3)
    
    if len(uploaded_files) >= batch_threshold:
        # Use batch processing for multiple files
        screenshot_ids = [file_info['id'] for file_info in uploaded_files]
        batch_job_id = queue_batch_processing(screenshot_ids, request.user.id)
        
        # Update uploaded files with batch job info
        for file_info in uploaded_files:
            file_info['batch_job_id'] = batch_job_id
            file_info['processing_type'] = 'batch'
    else:
        # Use individual processing for small uploads
        for file_info in uploaded_files:
            job_id = queue_screenshot_processing(file_info['id'])
            file_info['job_id'] = job_id
            file_info['processing_type'] = 'individual'
    
    response_data = {
        'uploaded': uploaded_files,
        'errors': errors,
        'success_count': len(uploaded_files),
        'error_count': len(errors)
    }
    
    return JsonResponse(response_data)


@login_required
def search_screenshots(request):
    """Search screenshots with natural language queries."""
    query = request.GET.get('q', '').strip()
    page = request.GET.get('page', 1)
    
    results = []
    total_results = 0
    
    if query:
        search_service = ScreenshotSearchService(user=request.user)
        results = search_service.search(query, limit=20)
        total_results = len(results)
        
        # Paginate results
        paginator = Paginator(results, 5)
        results = paginator.get_page(page)
    
    context = {
        'query': query,
        'results': results,
        'total_results': total_results,
    }
    
    return render(request, 'screenshots/search.html', context)


@login_required
def screenshot_detail(request, screenshot_id):
    """Display detailed view of a screenshot."""
    screenshot = get_object_or_404(Screenshot, id=screenshot_id, user=request.user)
    
    # Get recent search results for this screenshot
    recent_searches = SearchResult.objects.filter(
        screenshot=screenshot
    ).order_by('-search_timestamp')[:5]
    
    context = {
        'screenshot': screenshot,
        'recent_searches': recent_searches,
    }
    
    return render(request, 'screenshots/detail.html', context)


@login_required
def screenshot_gallery(request):
    """Display all screenshots in a gallery view."""
    status_filter = request.GET.get('status', 'all')
    page = request.GET.get('page', 1)
    
    screenshots = Screenshot.objects.filter(user=request.user)
    
    if status_filter != 'all':
        screenshots = screenshots.filter(processing_status=status_filter)
    
    # Paginate screenshots
    paginator = Paginator(screenshots, 12)
    screenshots = paginator.get_page(page)
    
    context = {
        'screenshots': screenshots,
        'status_filter': status_filter,
        'status_choices': Screenshot.PROCESSING_STATUS_CHOICES,
    }
    
    return render(request, 'screenshots/gallery.html', context)


@require_http_methods(["GET"])
@login_required
def processing_status(request, screenshot_id=None):
    """Get processing status of screenshots via AJAX."""
    if screenshot_id:
        # Individual screenshot status (legacy endpoint)
        try:
            screenshot = Screenshot.objects.get(id=screenshot_id, user=request.user)
            
            response_data = {
                'id': screenshot.id,
                'status': screenshot.processing_status,
                'filename': screenshot.filename,
                'processed_at': screenshot.processed_at.isoformat() if screenshot.processed_at else None,
                'error': screenshot.processing_error,
            }
            
            return JsonResponse(response_data)
            
        except Screenshot.DoesNotExist:
            return JsonResponse({'error': 'Screenshot not found'}, status=404)
    else:
        # Overall processing status for AJAX polling
        user_screenshots = Screenshot.objects.filter(user=request.user)
        
        # Get counts by status
        total_screenshots = user_screenshots.count()
        processing_count = user_screenshots.filter(processing_status='processing').count()
        pending_count = user_screenshots.filter(processing_status='pending').count()
        completed_count = user_screenshots.filter(processing_status='completed').count()
        failed_count = user_screenshots.filter(processing_status='failed').count()
        
        # Get recent screenshots with their status for UI updates
        recent_screenshots = user_screenshots.order_by('-uploaded_at')[:20]
        screenshots_data = []
        
        for screenshot in recent_screenshots:
            screenshots_data.append({
                'id': screenshot.id,
                'filename': screenshot.filename,
                'processing_status': screenshot.processing_status,
                'processed_at': screenshot.processed_at.isoformat() if screenshot.processed_at else None,
            })
        
        response_data = {
            'total_screenshots': total_screenshots,
            'processing_count': processing_count,
            'pending_count': pending_count,
            'completed_count': completed_count,
            'failed_count': failed_count,
            'screenshots': screenshots_data,
        }
        
        return JsonResponse(response_data)


@csrf_exempt
@require_http_methods(["POST"])
@login_required
def reprocess_screenshot(request, screenshot_id):
    """Requeue a screenshot for processing."""
    try:
        screenshot = get_object_or_404(Screenshot, id=screenshot_id, user=request.user)
        
        # Reset processing status
        screenshot.processing_status = 'pending'
        screenshot.processing_error = None
        screenshot.processed_at = None
        screenshot.save()
        
        # Queue for processing
        job_id = queue_screenshot_processing(screenshot.id)
        
        return JsonResponse({
            'success': True,
            'job_id': job_id,
            'message': f'Screenshot {screenshot.filename} queued for reprocessing'
        })
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)


@login_required
def delete_screenshot(request, screenshot_id):
    """Delete a screenshot and its associated data."""
    if request.method == 'POST':
        screenshot = get_object_or_404(Screenshot, id=screenshot_id, user=request.user)
        filename = screenshot.filename
        
        # Delete the file and database record
        if screenshot.image:
            screenshot.image.delete()
        screenshot.delete()
        
        messages.success(request, f'Screenshot "{filename}" deleted successfully.')
        return redirect('screenshots:gallery')
    
    return redirect('screenshots:gallery')


@require_http_methods(["GET"])
@login_required
def api_search(request):
    """API endpoint for search functionality (for HTMX)."""
    query = request.GET.get('q', '').strip()
    
    if not query:
        return JsonResponse({'results': []})
    
    search_service = ScreenshotSearchService(user=request.user)
    results = search_service.search(query, limit=5)
    
    # Serialize results for JSON response
    serialized_results = []
    for result in results:
        serialized_results.append({
            'id': result.screenshot.id,
            'filename': result.screenshot.filename,
            'image_url': result.screenshot.image.url,
            'confidence': round(result.overall_confidence, 3),
            'text_confidence': round(result.text_confidence, 3),
            'visual_confidence': round(result.visual_confidence, 3),
            'ui_confidence': round(result.ui_confidence, 3),
            'color_confidence': round(result.color_confidence, 3),
            'extracted_text': result.screenshot.extracted_text[:200] + '...' if result.screenshot.extracted_text and len(result.screenshot.extracted_text) > 200 else result.screenshot.extracted_text,
            'visual_description': result.screenshot.visual_description[:200] + '...' if result.screenshot.visual_description and len(result.screenshot.visual_description) > 200 else result.screenshot.visual_description,
        })
    
    return JsonResponse({'results': serialized_results})
