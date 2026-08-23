from django.urls import path
from . import views

urlpatterns = [
    # Event endpoints
    path('events/', views.EventListCreateView.as_view(), name='event-list-create'),

    # Video asset endpoints
    path('videos/', views.VideoAssetListView.as_view(), name='video-list'),
    path('videos/upload/', views.VideoAssetUploadView.as_view(), name='video-upload'),
    path('videos/<int:pk>/status/', views.VideoAssetStatusView.as_view(), name='video-status'),

    # Analytics endpoints
    path('analytics/<int:pk>/', views.CrowdAnalyticsDetailView.as_view(), name='analytics-detail'),

    # Live endpoint
    path('live/detect/', views.LiveEmotionDetectionView.as_view(), name='live-detect'),
    path('live/classify/', views.LiveEmotionClassificationView.as_view(), name='live-classify'),
]
