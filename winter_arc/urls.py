from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import landing_view
from core.views import liveness_check, readiness_check

urlpatterns = [
    path('health/', liveness_check, name='health-live'),
    path('health/ready/', readiness_check, name='health-ready'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('arcs/', include('arcs.urls')),
    path('goals/', include('goals.urls')),
    path('tasks/', include('tasks.urls')),
    path('habits/', include('habits.urls')),
    path('analytics/', include('analytics.urls')),
    path('notifications/', include('notifications.urls')),
    path('api/v1/', include('api.urls')),
    path('', landing_view, name='home'),
]

if settings.DEBUG:
    urlpatterns += [
        path('_styleguide/', TemplateView.as_view(template_name='debug/styleguide.html'), name='styleguide'),
        path('_motion-spec/', TemplateView.as_view(template_name='debug/motion_spec.html'), name='motion_spec'),
    ]
