from django.urls import path, include
import rest_framework.renderers
from rest_framework.routers import DefaultRouter
from rest_framework.schemas import get_schema_view
from rest_framework.authtoken.views import obtain_auth_token

from .views import (
    MeView,
    ArcViewSet,
    GoalViewSet,
    MilestoneViewSet,
    TaskViewSet,
    HabitViewSet,
    JournalViewSet,
    NotificationViewSet,
    NotificationPreferenceView,
    AnalyticsView,
    GamificationView,
    PresetListView,
    PresetDetailView,
)

router = DefaultRouter()
router.register(r'arcs', ArcViewSet, basename='arc')
router.register(r'goals', GoalViewSet, basename='goal')
router.register(r'milestones', MilestoneViewSet, basename='milestone')
router.register(r'tasks', TaskViewSet, basename='task')
router.register(r'habits', HabitViewSet, basename='habit')
router.register(r'journal', JournalViewSet, basename='journal')
router.register(r'notifications', NotificationViewSet, basename='notification')

urlpatterns = [
    # Auth & Current User
    path('token-auth/', obtain_auth_token, name='api_token_auth'),
    path('me/', MeView.as_view(), name='api_me'),

    # Preferences & Read-Only Domain Views
    path('notifications/preferences/', NotificationPreferenceView.as_view(), name='api_notification_preferences'),
    path('analytics/', AnalyticsView.as_view(), name='api_analytics'),
    path('gamification/', GamificationView.as_view(), name='api_gamification'),
    path('presets/', PresetListView.as_view(), name='api_presets'),
    path('presets/<str:key>/', PresetDetailView.as_view(), name='api_preset_detail'),

    # OpenAPI Schema (JSON format)
    path(
        'schema/',
        get_schema_view(
            title="Winter Arc REST API",
            description="Production-grade API for Winter Arc personal mastery and discipline tracking",
            version="1.0.0",
            renderer_classes=[rest_framework.renderers.JSONOpenAPIRenderer],
            permission_classes=[rest_framework.permissions.AllowAny],
            public=True,
        ),
        name='openapi-schema'
    ),

    # Router ViewSets
    path('', include(router.urls)),
]
