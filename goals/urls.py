from django.urls import path
from . import views

app_name = 'goals'

urlpatterns = [
    path('arc/<int:arc_id>/new/', views.goal_create, name='create'),
    path('<int:pk>/', views.goal_detail, name='detail'),
    path('<int:pk>/edit/', views.goal_update, name='update'),
    path('<int:pk>/delete/', views.goal_delete, name='delete'),
    
    path('<int:goal_id>/milestones/new/', views.milestone_create, name='milestone_create'),
    path('milestones/<int:pk>/edit/', views.milestone_update, name='milestone_update'),
    path('milestones/<int:pk>/toggle/', views.milestone_toggle, name='milestone_toggle'),
    path('milestones/<int:pk>/delete/', views.milestone_delete, name='milestone_delete'),
]
