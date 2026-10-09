from django.urls import path
from . import views

app_name = 'focus'

urlpatterns = [
    path('', views.focus_view, name='index'),
    path('', views.focus_view, name='focus'),
]
