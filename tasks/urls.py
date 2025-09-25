from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='tasks/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),  
    path('create-employee/', views.create_employee, name='create_employee'),
    path('create-task/', views.create_task, name='create_task'),
    path('task/<int:task_id>/submit/', views.submit_task, name='submit_task'),
    path('task/<int:task_id>/complete/', views.complete_task, name='complete_task'),
    path('change-password/', views.change_password, name='change_password'),
    path('change-password/<int:user_id>/', views.change_employee_password, name='change_employee_password'),
    path('make-payment/', views.make_payment, name='make_payment'),
    path('payment-history/', views.payment_history, name='payment_history'),
    path('timeline/', views.timeline_view, name='timeline'),
    path('api/employee-balance/<int:employee_id>/', views.get_employee_balance, name='employee_balance'),
    path('delete-employee/<int:user_id>/', views.delete_employee, name='delete_employee'),
    path('calendar/', views.calendar_view, name='calendar'),
path('api/task-details/<int:task_id>/', views.task_details_api, name='task_details_api'),
]
