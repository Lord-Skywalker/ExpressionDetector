from rest_framework import serializers
from .models import Event, VideoAsset, CrowdAnalytics


class EventSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ['id', 'name', 'date', 'location', 'created_at']


class VideoAssetSerializer(serializers.ModelSerializer):
    class Meta:
        model = VideoAsset
        fields = ['id', 'event', 'file_path', 'status', 'progress_percent', 'uploaded_at']
        read_only_fields = ['status', 'progress_percent', 'uploaded_at']


class CrowdAnalyticsSerializer(serializers.ModelSerializer):
    class Meta:
        model = CrowdAnalytics
        fields = ['id', 'video_asset', 'timeline_data', 'created_at']


class VideoAssetDetailSerializer(serializers.ModelSerializer):
    """Full detail serializer that nests analytics alongside asset metadata."""
    analytics = CrowdAnalyticsSerializer(read_only=True)

    class Meta:
        model = VideoAsset
        fields = ['id', 'event', 'file_path', 'status', 'progress_percent', 'uploaded_at', 'analytics']
