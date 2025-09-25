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

@login_required
def get_employee_balance(request, employee_id):
    if not request.user.is_staff:
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
    if request.user.is_staff:
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
        return render(request, 'tasks/employee_dashboard.html', {'tasks': tasks})

# Админ создает нового сотрудника
@login_required
def create_employee(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.manager = request.user  # Начальником становится текущий админ
            user.is_staff = False  # Обычный сотрудник
            user.save()
            return redirect('dashboard')
    else:
        form = UserForm()
    
    return render(request, 'tasks/create_employee.html', {'form': form})

# Админ создает задачу
@login_required
def create_task(request):
    if not request.user.is_staff:
        return redirect('dashboard')
    
    if request.method == 'POST':
        form = TaskForm(request.POST)
        if form.is_valid():
            task = form.save(commit=False)
            task.created_by = request.user  # Кем создана задача
            task.save()
            return redirect('dashboard')
    else:
        form = TaskForm()
        # Показываем только подчиненных текущего админа
        form.fields['assigned_to'].queryset = CustomUser.objects.filter(manager=request.user)
    
    return render(request, 'tasks/create_task.html', {'form': form})

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
    if not request.user.is_staff:
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
            
            if payment.amount > payment.employee.balance:
                messages.error(request, 'Сумма выплаты не может превышать баланс сотрудника!')
            else:
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
    if not request.user.is_staff:
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
    if not request.user.is_staff:
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