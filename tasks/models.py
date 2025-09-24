from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    # Если пользователь не суперпользователь, то у него должен быть начальник
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                               limit_choices_to={'is_staff': True}, related_name='subordinates')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Баланс')
    
    def __str__(self):
        return f"{self.username} ({self.get_full_name()})"

class Task(models.Model):
    STATUS_CHOICES = [
        ('created', 'Создана'),
        ('submitted', 'Сдана на отчет'),
        ('completed', 'Выполнена'),
    ]

    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                                   limit_choices_to={'is_staff': False},  # Задачи можно назначать только обычным сотрудникам
                                   related_name='tasks', verbose_name='Сотрудник')
    due_date = models.DateField(verbose_name='Дата выполнения')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма к оплате')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Статус')
    created_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата выдачи')
    submitted_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата сдачи на отчет')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                                  related_name='created_tasks', verbose_name='Кем создана')

    def __str__(self):
        return self.title