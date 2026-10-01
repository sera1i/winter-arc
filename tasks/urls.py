from django.urls import path
from . import views

app_name = 'tasks'

urlpatterns = [
    path('', views.task_list, name='list'),
    path('new/', views.task_create, name='create'),
    path('<int:pk>/', views.task_detail, name='detail'),
    path('<int:pk>/edit/', views.task_update, name='update'),
    path('<int:pk>/complete/', views.task_complete, name='complete'),
    path('<int:pk>/uncomplete/', views.task_uncomplete, name='uncomplete'),
    path('<int:pk>/delete/', views.task_delete, name='delete'),
]
