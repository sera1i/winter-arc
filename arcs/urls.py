from django.urls import path
from . import views

app_name = 'arcs'

urlpatterns = [
    path('', views.arc_list, name='list'),
    path('new/', views.arc_create, name='create'),
    path('<int:pk>/', views.arc_detail, name='detail'),
    path('<int:pk>/edit/', views.arc_update, name='update'),
    path('<int:pk>/delete/', views.arc_delete, name='delete'),
    path('<int:pk>/make_primary/', views.arc_make_primary, name='make_primary'),
]
