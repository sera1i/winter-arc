from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from django.conf import settings
from django.conf.urls.static import static
from accounts.views import landing_view
from core.views import health_liveness, health_readiness, robots_txt, sitemap_xml, custom_404

urlpatterns = [
    path('robots.txt', robots_txt, name='robots_txt'),
    path('sitemap.xml', sitemap_xml, name='sitemap_xml'),
    path('health/', health_liveness, name='health_liveness'),
    path('health/ready/', health_readiness, name='health_readiness'),
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('arcs/', include('arcs.urls')),
    path('goals/', include('goals.urls')),
    path('tasks/', include('tasks.urls')),
    path('habits/', include('habits.urls')),
    path('journal/', include('journal.urls')),
    path('analytics/', include('analytics.urls')),
    path('notifications/', include('notifications.urls')),
    path('api/v1/', include('api.urls')),
    path('', include('core.urls_seo')),
    path('', landing_view, name='home'),
]

handler404 = 'core.views.custom_404'

if settings.DEBUG:
    urlpatterns += [
        path('404/', custom_404, name='custom_404'),
        path('_styleguide/', TemplateView.as_view(template_name='debug/styleguide.html'), name='styleguide'),
        path('_motion-spec/', TemplateView.as_view(template_name='debug/motion_spec.html'), name='motion_spec'),
    ]
