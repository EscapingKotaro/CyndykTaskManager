from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import update_session_auth_hash, logout as auth_logout
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum
from .models import Task, CustomUser, Payment
from .forms import TaskForm, UserForm, CustomPasswordChangeForm, PaymentForm
from .forms import *
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout as auth_logout
from django.http import JsonResponse
import secrets
from datetime import timedelta
from django.contrib.auth import login  # ← Добавляем этот импорт

@login_required
def navigation_buttons(request):
    """
    Управление кастомными кнопками навигации
    """
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для управления навигацией.')
        return redirect('dashboard')
    
    buttons = NavigationButton.objects.order_by('order')
    
    if request.method == 'POST':
        # Обработка создания новой кнопки
        form = NavigationButtonForm(request.POST)
        if form.is_valid():
            button = form.save(commit=False)
            button.save()
            messages.success(request, f'Кнопка "{button.title}" успешно создана!')
            return redirect('navigation_buttons')
    else:
        form = NavigationButtonForm()
    
    return render(request, 'tasks/navigation_buttons.html', {
        'buttons': buttons,
        'form': form
    })

@login_required
def edit_navigation_button(request, button_id):
    """
    Редактирование кнопки навигации
    """
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для редактирования кнопок.')
        return redirect('dashboard')
    
    button = get_object_or_404(NavigationButton, id=button_id)
    
    if request.method == 'POST':
        form = NavigationButtonForm(request.POST, instance=button)
        if form.is_valid():
            form.save()
            messages.success(request, f'Кнопка "{button.title}" успешно обновлена!')
            return redirect('navigation_buttons')
    else:
        form = NavigationButtonForm(instance=button)
    
    return render(request, 'tasks/edit_navigation_button.html', {
        'form': form,
        'button': button
    })

@login_required
def delete_navigation_button(request, button_id):
    """
    Удаление кнопки навигации
    """
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для удаления кнопок.')
        return redirect('dashboard')
    
    button = get_object_or_404(NavigationButton, id=button_id)
    
    if request.method == 'POST':
        button_title = button.title
        button.delete()
        messages.success(request, f'Кнопка "{button_title}" успешно удалена!')
        return redirect('navigation_buttons')
    
    return render(request, 'tasks/delete_navigation_button.html', {'button': button})
@login_required
def task_management(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    tasks = Task.objects.filter(created_by=request.user).order_by('-created_date')
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(assigned_to__username__icontains=search_query) |
            Q(assigned_to__first_name__icontains=search_query)
        )
    
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    return render(request, 'tasks/task_management.html', {
        'tasks': tasks,
        'search_query': search_query,
        'status_filter': status_filter
    })

@login_required
def task_management(request):
    """
    Страница управления задачами для админа
    """
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    tasks = Task.objects.filter(created_by=request.user).order_by('-created_date')
    search_query = request.GET.get('search', '')
    status_filter = request.GET.get('status', '')
    employee_filter = request.GET.get('employee', '')
    
    # Фильтрация по поиску
    if search_query:
        tasks = tasks.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query)
        )
    
    # Фильтрация по статусу
    if status_filter:
        tasks = tasks.filter(status=status_filter)
    
    # Фильтрация по сотруднику
    if employee_filter:
        tasks = tasks.filter(assigned_to_id=employee_filter)
    
    # Сотрудники для фильтра
    employees = CustomUser.objects.filter(manager=request.user)
    
    return render(request, 'tasks/task_management.html', {
        'tasks': tasks,
        'search_query': search_query,
        'status_filter': status_filter,
        'employee_filter': employee_filter,
        'employees': employees,
        'status_choices': Task.STATUS_CHOICES
    })

@login_required
def edit_task(request, task_id):
    """
    Редактирование задачи админом
    """
    if request.user.role not in ['boss', 'manager']:
        messages.error(request, 'У вас нет прав для редактирования задач.')
        return redirect('dashboard')
    
    task = get_object_or_404(Task, id=task_id, created_by=request.user)
    
    if request.method == 'POST':
        form = TaskForm(request.POST, instance=task)
        if form.is_valid():
            updated_task = form.save()
            messages.success(request, f'✅ Задача "{updated_task.title}" успешно обновлена!')
            return redirect('task_management')
        else:
            messages.error(request, '❌ Пожалуйста, исправьте ошибки в форме.')
    else:
        form = TaskForm(instance=task)
        form.fields['assigned_to'].queryset = CustomUser.objects.filter(manager=request.user)
    
    return render(request, 'tasks/edit_task.html', {
        'form': form,
        'task': task
    })

@login_required
def delete_task(request, task_id):
    """
    Удаление задачи админом
    """
    if not request.user.is_staff:
        messages.error(request, 'У вас нет прав для удаления задач.')
        return redirect('dashboard')
    
    task = get_object_or_404(Task, id=task_id, created_by=request.user)
    
    if request.method == 'POST':
        task_title = task.title
        task.delete()
        messages.success(request, f'✅ Задача "{task_title}" успешно удалена!')
        return redirect('task_management')
    
    return render(request, 'tasks/delete_task.html', {'task': task})

@login_required
def task_detail(request, task_id):
    """
    Детальная страница задачи для админа
    """
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    task = get_object_or_404(Task, id=task_id, created_by=request.user)
    
    return render(request, 'tasks/task_detail.html', {
        'task': task
    })

@login_required
def employee_list(request):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    if request.user.role=='boss':
        subordinates = CustomUser.objects.filter(manager=request.user)
    else:
        subordinates = CustomUser.objects.filter(manager=request.user.manager)
    search_query = request.GET.get('search', '')
    
    if search_query:
        subordinates = subordinates.filter(
            Q(username__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(email__icontains=search_query) |
            Q(telegram_username__icontains=search_query) |
            Q(tags__icontains=search_query)
        )
    
    return render(request, 'tasks/employee_list.html', {
        'subordinates': subordinates,
        'search_query': search_query
    })


@login_required
def create_invitation(request):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = InvitationForm(request.POST)
        if form.is_valid():
            # Создаем токен
            token = secrets.token_urlsafe(32)
            expires_at = timezone.now() + timedelta(days=7)
            
            invitation = Invitation(
                token=token,
                tags=form.cleaned_data['tags'],
                created_by=request.user,
                expires_at=expires_at,
            )
            invitation.save()
            
            # Генерируем ссылку
            invitation_url = request.build_absolute_uri(
                f'/register/{token}/'
            )
            
            messages.success(request, f'Приглашение создано! Ссылка: {invitation_url}')
            return redirect('invitation_list')
    else:
        form = InvitationForm()
    
    return render(request, 'tasks/create_invitation.html', {'form': form})

@login_required
def invitation_list(request):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    invitations = Invitation.objects.filter(created_by=request.user).order_by('-created_at')
    return render(request, 'tasks/invitation_list.html', {'invitations': invitations})

def register_with_invitation(request, token):
    try:
        invitation = Invitation.objects.get(token=token, status='pending')
        
        if invitation.is_expired():
            invitation.status = 'expired'
            invitation.save()
            return render(request, 'tasks/invitation_expired.html')
        
        if request.method == 'POST':
            form = UserRegistrationForm(request.POST)
            if form.is_valid():
                user = form.save(commit=False)
                user.set_password(form.cleaned_data['password1'])
                user.tags = invitation.tags
                user.manager = invitation.created_by
                user.is_staff = False
                user.save()
                
                # Обновляем приглашение
                invitation.status = 'accepted'
                invitation.accepted_by = user
                invitation.save()
                
                # Автоматически логиним пользователя
               # login(request, user)
              # messages.success(request, 'Регистрация завершена! Добро пожаловать!')
                return redirect('dashboard')
        else:
            form = UserRegistrationForm()
        
        return render(request, 'tasks/register.html', {
            'form': form,
            'invitation': invitation
        })
    
    except Invitation.DoesNotExist:
        return render(request, 'tasks/invitation_invalid.html')

@login_required
def profile(request):
    if request.method == 'POST':
        form = UserProfileForm(request.POST, request.FILES, instance=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль успешно обновлен!')
            return redirect('profile')
    else:
        form = UserProfileForm(instance=request.user)
    
    return render(request, 'tasks/profile.html', {'form': form})


@login_required
def get_employee_balance(request, employee_id):
    if request.user.role not in ['boss', 'manager']:
        return JsonResponse({'error': 'Access denied'}, status=403)
    
    employee = get_object_or_404(CustomUser, id=employee_id, manager=request.user)
    return JsonResponse({'balance': float(employee.balance)})

# Кастомный logout
def custom_logout(request):
    auth_logout(request)
    return redirect('login')

# Главная страница - разная логика для админа и сотрудника
@login_required
def dashboard(request):
    if request.user.role in ['boss', 'manager']:
        subordinates = CustomUser.objects.filter(manager=request.user)
        tasks = Task.objects.filter(created_by=request.user)
        
        # Статистика для админа
        total_debt = subordinates.aggregate(total=Sum('balance'))['total'] or 0
        pending_tasks = tasks.filter(status='submitted').count()
        
        return render(request, 'tasks/manager_dashboard.html', {
            'subordinates': subordinates,
            'tasks': tasks,
            'total_debt': total_debt,
            'pending_tasks': pending_tasks,
        })
    else:
        tasks = Task.objects.filter(assigned_to=request.user)
        
        # Группируем задачи по статусам с подсчетом статистики
        status_groups = {}
        for status_code, status_name in Task.STATUS_CHOICES:
            status_tasks = tasks.filter(status=status_code)
            total_payment = status_tasks.aggregate(total=Sum('payment_amount'))['total'] or 0
            
            status_groups[status_code] = {
                'name': status_name,
                'tasks': status_tasks,
                'count': status_tasks.count(),
                'total_payment': total_payment
            }
        
        return render(request, 'tasks/employee_dashboard.html', {
            'status_groups': status_groups,
            'total_tasks': tasks.count()
        })

        
# Админ создает нового сотрудника
@login_required
def create_employee(request):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            if request.user.role == 'boss':
                # Босс создает - начальником становится сам босс
                user.manager = request.user
            else:
                # Менеджер создает - находим общего босса
                user.manager = request.user.get_boss()
            user.is_staff = False  # Обычный сотрудник
            user.save()
            return redirect('dashboard')
    else:
        form = UserForm()
    
    return render(request, 'tasks/create_employee.html', {'form': form})

# Админ создает задачу
@login_required
def create_task(request):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TaskForm(request.POST, request=request)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user
            
            # Проверяем права на назначение
            if not request.user.can_assign_task_to(task.assigned_to):
                messages.error(request, 'У вас нет прав назначать задачи этому пользователю')
                return render(request, 'tasks/create_task.html', {'form': form})
            
            task.save()
            messages.success(request, 'Задача создана!')
            return redirect('task_list')
    else:
        form = TaskForm(request=request)
    
    return render(request, 'tasks/create_task.html', {'form': form})


@login_required
def start_task(request, task_id):
    """Сотрудник начинает работу над задачей"""
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
    
    if task.status == 'created':
        task.status = 'in_progress'
        task.started_date = timezone.now()
        task.save()
        
    return redirect('dashboard')
# Сотрудник сдает задачу на отчет
@login_required
def submit_task(request, task_id):
    task = get_object_or_404(Task, id=task_id, assigned_to=request.user)
    
    if request.method == 'POST':
        task.status = 'submitted'
        task.submitted_date = timezone.now()
        task.save()
        return redirect('dashboard')
    
    return render(request, 'tasks/submit_task.html', {'task': task})

# Админ подтверждает выполнение задачи и начисляет деньги
@login_required
def complete_task(request, task_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    task = get_object_or_404(Task, id=task_id, created_by=request.user)
    
    if request.method == 'POST':
        task.status = 'completed'
        task.save()
        
        # Начисляем деньги сотруднику
        employee = task.assigned_to
        employee.balance += task.payment_amount
        employee.save()
        
        return redirect('dashboard')
    
    return render(request, 'tasks/complete_task.html', {'task': task})



@login_required
def change_password(request):
    if request.method == 'POST':
        form = CustomPasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)  # Не разлогиниваем пользователя
            messages.success(request, 'Пароль успешно изменен!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Пожалуйста, исправьте ошибки ниже.')
    else:
        form = CustomPasswordChangeForm(request.user)
    
    return render(request, 'tasks/change_password.html', {'form': form})

# Админ может сменить пароль сотрудника
@login_required
def change_employee_password(request, user_id):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    employee = get_object_or_404(CustomUser, id=user_id, manager=request.user)
    
    if request.method == 'POST':
        new_password = request.POST.get('new_password')
        if new_password:
            employee.set_password(new_password)
            employee.save()
            messages.success(request, f'Пароль для {employee.username} успешно изменен!')
            return redirect('dashboard')
        else:
            messages.error(request, 'Пароль не может быть пустым.')
    
    return render(request, 'tasks/change_employee_password.html', {'employee': employee})



@login_required
def make_payment(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            payment = form.save(commit=False)
            payment.manager = request.user
            
            payment.save()
            messages.success(request, f'Выплата {payment.amount} руб. для {payment.employee} выполнена!')
            return redirect('payment_history')
    else:
        form = PaymentForm()
        form.fields['employee'].queryset = CustomUser.objects.filter(manager=request.user)
    
    return render(request, 'tasks/make_payment.html', {'form': form})

@login_required
def payment_history(request):
    if request.user.is_staff:
        payments = Payment.objects.filter(manager=request.user).order_by('-payment_date')
        return render(request, 'tasks/payment_history.html', {'payments': payments})
    else:
        payments = Payment.objects.filter(employee=request.user).order_by('-payment_date')
        return render(request, 'tasks/payment_history.html', {'payments': payments})

@login_required
def timeline_view(request):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    tasks = Task.objects.filter(created_by=request.user).order_by('due_date')
    tags = request.GET.getlist('tags')
    
    if tags:
        tasks = tasks.filter(
            Q(tags__icontains=tags[0]) | 
            Q(assigned_to__tags__icontains=tags[0])
        )
    
    return render(request, 'tasks/timeline.html', {
        'tasks': tasks,
        'all_tags': get_all_tags(request.user),
        'selected_tags': tags,
    })

def get_all_tags(manager):
    employees = CustomUser.objects.filter(manager=manager)
    tags = set()
    for emp in employees:
        tags.update(emp.get_tags_list())
    return sorted(tags)

def delete_employee(request, user_id):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    employee = get_object_or_404(CustomUser, id=user_id, manager=request.user)
    
    if request.method == 'POST':
        # Проверяем что у сотрудника нет активных задач
        active_tasks = Task.objects.filter(
            assigned_to=employee, 
            status__in=['created', 'submitted']
        )
        
        if active_tasks.exists():
            messages.error(request, f'Нельзя удалить сотрудника с активными задачами!')
            return redirect('dashboard')
        
        username = employee.username
        employee.delete()
        messages.success(request, f'Сотрудник {username} успешно удален!')
        return redirect('dashboard')
    
    return render(request, 'tasks/delete_employee.html', {'employee': employee})


from datetime import datetime, timedelta
from calendar import monthrange

@login_required
def calendar_view(request):
    if request.user.role not in ['boss', 'manager']:
        return redirect('dashboard')
    
    # Получаем год и месяц из параметров или текущие
    year = int(request.GET.get('year', datetime.now().year))
    month = int(request.GET.get('month', datetime.now().month))
    
    # Корректируем если вышли за пределы
    if month > 12:
        month = 1
        year += 1
    elif month < 1:
        month = 12
        year -= 1
    
    # Получаем задачи для этого месяца
    first_day = datetime(year, month, 1)
    last_day = datetime(year, month, monthrange(year, month)[1])
    
    tasks = Task.objects.filter(
        created_by=request.user,
        due_date__range=[first_day, last_day]
    ).order_by('due_date')
    
    # Создаем структуру календаря
    calendar_data = []
    weeks = []
    
    # Первый день месяца
    current_date = first_day
    # Находим понедельник предыдущей недели если месяц начинается не с понедельника
    start_date = current_date - timedelta(days=current_date.weekday())
    
    # Заполняем 6 недель (максимум)
    for week in range(6):
        week_days = []
        for day in range(7):
            date = start_date + timedelta(days=week * 7 + day)
            day_tasks = tasks.filter(due_date=date.date()) if date.month == month else []
            
            week_days.append({
                'date': date,
                'tasks': day_tasks,
                'is_current_month': date.month == month,
                'is_today': date.date() == datetime.now().date()
            })
        weeks.append(week_days)
    
    # Навигация
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    return render(request, 'tasks/calendar.html', {
        'weeks': weeks,
        'current_date': datetime(year, month, 1),
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'month_name': first_day.strftime('%B %Y')
    })

@login_required
def task_details_api(request, task_id):
    task = get_object_or_404(Task, id=task_id, created_by=request.user)
    
    return JsonResponse({
        'title': task.title,
        'description': task.description,
        'assigned_to': str(task.assigned_to),
        'due_date': task.due_date.strftime('%d.%m.%Y'),
        'payment_amount': float(task.payment_amount),
        'status': task.status,
        'status_display': task.get_status_display(),
    })