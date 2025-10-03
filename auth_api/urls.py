from django.urls import path
from . import views

app_name = 'auth_api'

urlpatterns = [
    path('verify-user/', views.verify_user, name='verify_user'),
]