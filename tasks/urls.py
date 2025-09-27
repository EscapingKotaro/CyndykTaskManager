from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('login/', auth_views.LoginView.as_view(template_name='tasks/login.html'), name='login'),
    path('logout/', views.custom_logout, name='logout'),  
    path('create-employee/', views.create_employee, name='create_employee'),
    path('create-task/', views.create_task, name='create_task'),
    path('task/<int:task_id>/start/', views.start_task, name='start_task'),
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
    path('invitations/', views.invitation_list, name='invitation_list'),
    path('invitations/create/', views.create_invitation, name='create_invitation'),
    path('register/<str:token>/', views.register_with_invitation, name='register_with_invitation'),
    path('profile/', views.profile, name='profile'),
    path('employees/', views.employee_list, name='employee_list'),
    path('tasks/manage/', views.task_management, name='task_management'),
    path('tasks/<int:task_id>/', views.task_detail, name='task_detail'),
    path('tasks/<int:task_id>/edit/', views.edit_task, name='edit_task'),
    path('tasks/<int:task_id>/delete/', views.delete_task, name='delete_task'),
    path('navigation-buttons/', views.navigation_buttons, name='navigation_buttons'),
    path('navigation-buttons/<int:button_id>/edit/', views.edit_navigation_button, name='edit_navigation_button'),
    path('navigation-buttons/<int:button_id>/delete/', views.delete_navigation_button, name='delete_navigation_button'),
]

