from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate
from django.db.models import Q
from .models import Task, CustomUser
from .forms import *
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth import logout as auth_logout

# Кастомный logout
def custom_logout(request):
    auth_logout(request)
    return redirect('login')

# Главная страница - разная логика для админа и сотрудника
@login_required
def dashboard(request):
    if request.user.is_staff:  # Это админ
        # Показываем всех подчиненных и их задачи
        subordinates = CustomUser.objects.filter(manager=request.user)
        tasks = Task.objects.filter(created_by=request.user)
        return render(request, 'tasks/manager_dashboard.html', {
            'subordinates': subordinates,
            'tasks': tasks
        })
    else:  # Это обычный сотрудник
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