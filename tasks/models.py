from django.contrib.auth.models import AbstractUser
from django.db import models

class CustomUser(AbstractUser):
    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                               limit_choices_to={'is_staff': True}, related_name='subordinates')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Баланс')
    tags = models.CharField(max_length=500, blank=True, verbose_name='Ярлыки (через запятую)')
    
    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',')] if self.tags else []
    
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
                                   limit_choices_to={'is_staff': False},
                                   related_name='tasks', verbose_name='Сотрудник')
    due_date = models.DateField(verbose_name='Дата выполнения')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма к оплате')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Статус')
    created_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата выдачи')
    submitted_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата сдачи на отчет')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                                  related_name='created_tasks', verbose_name='Кем создана')
    tags = models.CharField(max_length=200, blank=True, verbose_name='Ярлыки задачи')

    def __str__(self):
        return self.title

class Payment(models.Model):
    employee = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments_received', 
                                limit_choices_to={'is_staff': False})
    manager = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='payments_made')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма выплаты')
    payment_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата выплаты')
    description = models.TextField(blank=True, verbose_name='Описание выплаты')
    
    def save(self, *args, **kwargs):
        # При создании выплаты уменьшаем баланс сотрудника
        if not self.pk:
            self.employee.balance -= self.amount
            self.employee.save()
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"Выплата {self.amount} руб. для {self.employee}"