from django.urls import path
from . import views

app_name = 'releases'

urlpatterns = [
    path('', views.release_list, name='release_list'),
    path('game/<int:pk>/', views.release_detail, name='release_detail'),
    path('game/create/', views.release_create, name='release_create'),
    path('game/<int:pk>/edit/', views.release_update, name='release_update'),
    path('game/<int:pk>/toggle-publish/', views.toggle_publish, name='toggle_publish'),
    path('game/<int:pk>/modal/', views.release_modal, name='release_modal'),
]