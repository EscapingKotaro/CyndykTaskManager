from django.db.models import Q, Sum
from collections import OrderedDict
from .models import *

def get_kanban_data(user, assigned_to_user=None):
    """
    Универсальная функция для получения данных канбана
    assigned_to_user - если None, то задачи текущего пользователя
    """
    if assigned_to_user:
        # Для просмотра задач конкретного пользователя (руководителем)
        tasks = Task.objects.filter(assigned_to=assigned_to_user)
    else:
        # Для обычного пользователя
        tasks = Task.objects.filter(assigned_to=user)
    
    # Создаем упорядоченные статусы
    status_order = ['proposed', 'created', 'in_progress', 'submitted', 'completed']
    status_groups = OrderedDict()
    
    for status_code in status_order:
        status_name = dict(Task.STATUS_CHOICES).get(status_code, '')
        status_tasks = tasks.filter(status=status_code).order_by('due_date', 'created_date')
        total_payment = status_tasks.aggregate(total=Sum('payment_amount'))['total'] or 0
        
        status_groups[status_code] = {
            'name': status_name,
            'tasks': status_tasks,
            'count': status_tasks.count(),
            'total_payment': total_payment,
            'code': status_code
        }
    
    return {
        'status_groups': status_groups,
        'total_tasks': tasks.count(),
        'total_payment': tasks.aggregate(total=Sum('payment_amount'))['total'] or 0
    }

def get_team_kanban_data(manager_user):
    """
    Канбан данные для всей команды руководителя
    """
    team_users = manager_user.get_team_users()
    tasks = Task.objects.filter(assigned_to__in=team_users)
    
    status_order = ['proposed', 'created', 'in_progress', 'submitted', 'completed']
    status_groups = OrderedDict()
    
    for status_code in status_order:
        status_name = dict(Task.STATUS_CHOICES).get(status_code, '')
        status_tasks = tasks.filter(status=status_code).select_related('assigned_to')
        total_payment = status_tasks.aggregate(total=Sum('payment_amount'))['total'] or 0
        
        # Группируем задачи по пользователям внутри статуса
        user_tasks = {}
        for task in status_tasks:
            user = task.assigned_to
            if user not in user_tasks:
                user_tasks[user] = []
            user_tasks[user].append(task)
        
        status_groups[status_code] = {
            'name': status_name,
            'tasks': status_tasks,
            'user_tasks': user_tasks,  # Задачи сгруппированные по пользователям
            'count': status_tasks.count(),
            'total_payment': total_payment,
            'code': status_code
        }
    
    return {
        'status_groups': status_groups,
        'team_users': team_users,
        'total_tasks': tasks.count(),
        'total_payment': tasks.aggregate(total=Sum('payment_amount'))['total'] or 0
    }