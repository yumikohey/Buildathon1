from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from PIL import Image
import os


class Screenshot(models.Model):
    """Model for storing screenshot information and analysis results."""
    
    # User association
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='screenshots')
    
    # File information
    image = models.ImageField(upload_to='screenshots/%Y/%m/%d/')
    filename = models.CharField(max_length=255)
    file_size = models.PositiveIntegerField()  # in bytes
    
    # Image metadata
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    
    # OCR and analysis results
    extracted_text = models.TextField(blank=True, null=True)
    visual_description = models.TextField(blank=True, null=True)
    ui_elements = models.JSONField(default=list, blank=True)  # List of UI elements detected
    dominant_colors = models.JSONField(default=list, blank=True)  # List of dominant colors
    
    # Enhanced visual pattern analysis
    error_states = models.JSONField(default=list, blank=True)  # List of detected error states
    visual_patterns = models.JSONField(default=list, blank=True)  # List of visual patterns identified
    color_context = models.JSONField(default=dict, blank=True)  # Color-to-context mapping
    
    # Processing status
    PROCESSING_STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('processing', 'Processing'),
        ('completed', 'Completed'),
        ('failed', 'Failed'),
    ]
    processing_status = models.CharField(
        max_length=20,
        choices=PROCESSING_STATUS_CHOICES,
        default='pending'
    )
    processing_error = models.TextField(blank=True, null=True)
    
    # Timestamps
    uploaded_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(blank=True, null=True)
    file_created_at = models.DateTimeField(blank=True, null=True)  # Original file creation time
    file_modified_at = models.DateTimeField(blank=True, null=True)  # Original file modification time
    
    class Meta:
        ordering = ['-uploaded_at']
        indexes = [
            models.Index(fields=['processing_status']),
            models.Index(fields=['uploaded_at']),
            models.Index(fields=['file_created_at']),
            models.Index(fields=['file_modified_at']),
        ]
    
    def __str__(self):
        return f"Screenshot: {self.filename}"
    
    def save(self, *args, **kwargs):
        """Override save to extract image metadata."""
        if self.image and not self.width:
            # Extract image dimensions
            with Image.open(self.image) as img:
                self.width, self.height = img.size
        
        if not self.filename:
            self.filename = os.path.basename(self.image.name)
        
        if not self.file_size and self.image:
            self.file_size = self.image.size
        
        super().save(*args, **kwargs)
    
    @property
    def file_size_mb(self):
        """Return file size in MB."""
        return round(self.file_size / (1024 * 1024), 2)
    
    @property
    def aspect_ratio(self):
        """Return aspect ratio as width:height."""
        if self.height:
            ratio = self.width / self.height
            return f"{self.width}:{self.height}"
        return "Unknown"


class SearchResult(models.Model):
    """Model for storing search results and confidence scores."""
    
    screenshot = models.ForeignKey(Screenshot, on_delete=models.CASCADE, related_name='search_results')
    query = models.TextField()
    
    # Confidence scores (0.0 to 1.0)
    text_confidence = models.FloatField(default=0.0)
    visual_confidence = models.FloatField(default=0.0)
    ui_confidence = models.FloatField(default=0.0)
    color_confidence = models.FloatField(default=0.0)
    overall_confidence = models.FloatField(default=0.0)
    
    # Match details
    matched_text_snippets = models.JSONField(default=list, blank=True)
    matched_visual_elements = models.JSONField(default=list, blank=True)
    matched_ui_elements = models.JSONField(default=list, blank=True)
    matched_colors = models.JSONField(default=list, blank=True)
    
    # Metadata
    search_timestamp = models.DateTimeField(default=timezone.now)
    
    class Meta:
        ordering = ['-overall_confidence', '-search_timestamp']
        indexes = [
            models.Index(fields=['query']),
            models.Index(fields=['overall_confidence']),
            models.Index(fields=['search_timestamp']),
        ]
    
    def __str__(self):
        return f"Search: '{self.query[:50]}...' -> {self.screenshot.filename} ({self.overall_confidence:.2f})"
    
    def calculate_overall_confidence(self):
        """Calculate overall confidence using weighted algorithm."""
        # Weights based on technical architecture: text(40%), visual(30%), UI(20%), colors(10%)
        weights = {
            'text': 0.4,
            'visual': 0.3,
            'ui': 0.2,
            'color': 0.1
        }
        
        self.overall_confidence = (
            self.text_confidence * weights['text'] +
            self.visual_confidence * weights['visual'] +
            self.ui_confidence * weights['ui'] +
            self.color_confidence * weights['color']
        )
        
        return self.overall_confidence
