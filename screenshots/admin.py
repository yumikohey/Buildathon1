from django.contrib import admin
from .models import Screenshot, SearchResult


@admin.register(Screenshot)
class ScreenshotAdmin(admin.ModelAdmin):
    list_display = ['filename', 'processing_status', 'uploaded_at', 'file_size_mb', 'width', 'height']
    list_filter = ['processing_status', 'uploaded_at']
    search_fields = ['filename', 'extracted_text']
    readonly_fields = ['uploaded_at', 'processed_at', 'file_size', 'width', 'height']
    
    fieldsets = (
        ('File Information', {
            'fields': ('image', 'filename', 'file_size', 'width', 'height')
        }),
        ('Analysis Results', {
            'fields': ('extracted_text', 'visual_description', 'ui_elements', 'dominant_colors')
        }),
        ('Processing Status', {
            'fields': ('processing_status', 'processing_error')
        }),
        ('Timestamps', {
            'fields': ('uploaded_at', 'processed_at')
        }),
    )


@admin.register(SearchResult)
class SearchResultAdmin(admin.ModelAdmin):
    list_display = ['query', 'screenshot', 'overall_confidence', 'search_timestamp']
    list_filter = ['search_timestamp']
    search_fields = ['query', 'screenshot__filename']
    readonly_fields = ['search_timestamp']
    
    fieldsets = (
        ('Search Information', {
            'fields': ('screenshot', 'query')
        }),
        ('Confidence Scores', {
            'fields': ('text_confidence', 'visual_confidence', 'ui_confidence', 'color_confidence', 'overall_confidence')
        }),
        ('Match Details', {
            'fields': ('matched_text_snippets', 'matched_visual_elements', 'matched_ui_elements', 'matched_colors')
        }),
        ('Metadata', {
            'fields': ('search_timestamp',)
        }),
    )
