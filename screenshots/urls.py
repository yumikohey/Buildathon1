from django.urls import path
from . import views, auth_views

app_name = 'screenshots'

urlpatterns = [
    # Authentication
    path('login/', auth_views.login_view, name='login'),
    path('register/', auth_views.register_view, name='register'),
    path('logout/', auth_views.logout_view, name='logout'),
    path('profile/', auth_views.profile_view, name='profile'),
    path('delete-account/', auth_views.delete_account_view, name='delete_account'),
    
    # Main pages
    path('', views.home, name='home'),
    path('search/', views.search_screenshots, name='search'),
    path('gallery/', views.screenshot_gallery, name='gallery'),
    path('screenshot/<int:screenshot_id>/', views.screenshot_detail, name='detail'),
    
    # AJAX endpoints
    path('upload/', views.upload_screenshots, name='upload'),
    path('api/search/', views.api_search, name='api_search'),
    path('status/', views.processing_status, name='processing_status'),
    path('status/<int:screenshot_id>/', views.processing_status, name='status'),
    
    # Actions
    path('reprocess/<int:screenshot_id>/', views.reprocess_screenshot, name='reprocess'),
    path('delete/<int:screenshot_id>/', views.delete_screenshot, name='delete'),
]