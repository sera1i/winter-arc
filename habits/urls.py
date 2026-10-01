from django.urls import path
from . import views

app_name = 'habits'

urlpatterns = [
    path('', views.habit_list, name='list'),
    path('new/', views.habit_create, name='create'),
    path('<int:pk>/', views.habit_detail, name='detail'),
    path('<int:pk>/edit/', views.habit_update, name='update'),
    path('<int:pk>/complete/', views.habit_complete, name='complete'),
    path('<int:pk>/archive/', views.habit_archive, name='archive'),
]
