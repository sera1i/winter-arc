from django.contrib import admin
from django.urls import path, include
from accounts.views import landing_view

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('arcs/', include('arcs.urls')),
    path('goals/', include('goals.urls')),
    path('tasks/', include('tasks.urls')),
    path('habits/', include('habits.urls')),
    path('', landing_view, name='home'),
]
