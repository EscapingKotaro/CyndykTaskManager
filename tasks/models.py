from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone

class CustomUser(AbstractUser):
    ROLE_CHOICES = [
        ('boss', 'Босс'),
        ('manager', 'Менеджер'), 
        ('technician', 'Техник'),
    ]

    manager = models.ForeignKey('self', on_delete=models.SET_NULL, null=True, blank=True, 
                               limit_choices_to={'is_staff': True}, related_name='subordinates')
    balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name='Баланс')
    tags = models.CharField(max_length=500, blank=True, verbose_name='Ярлыки (через запятую)')
    telegram_username = models.CharField(max_length=100, blank=True, verbose_name='Ник в Telegram')
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True, verbose_name='Аватар')
    
    # Убираем фамилию из обязательных
    first_name = models.CharField(max_length=30, blank=True, verbose_name='Имя')
    last_name = models.CharField(max_length=150, blank=True, verbose_name='Фамилия')  # Делаем необязательной
    role = models.CharField(
        max_length=20, 
        choices=ROLE_CHOICES, 
        default='technician',
        verbose_name='Роль',
        blank=True,
        null=True
    )

    def get_display_name(self):
        return self.first_name or self.username
    
    def get_tags_list(self):
        return [tag.strip() for tag in self.tags.split(',')] if self.tags else []
    
    def __str__(self):
        return self.get_display_name()
    def get_avatar_url(self):
        if self.avatar and hasattr(self.avatar, 'url'):
            return self.avatar.url
        return None
    def is_boss(self):
        return self.role == 'boss'
    
    def is_manager(self):
        return self.role == 'manager'
    
    def is_technician(self):
        return self.role == 'technician' or not self.role
class Task(models.Model):
    STATUS_CHOICES = [
        ('created', 'Создана'),
        ('in_progress', 'В исполнении'),
        ('submitted', 'Сдана на отчет'),
        ('completed', 'Выполнена'),
    ]

    title = models.CharField(max_length=200, verbose_name='Название')
    description = models.TextField(verbose_name='Описание')
    assigned_to = models.ForeignKey(CustomUser, on_delete=models.CASCADE, 
                                   limit_choices_to={'is_staff': False},
                                   related_name='tasks', verbose_name='Сотрудник')
    due_date = models.DateField(verbose_name='Дата выполнения')
    payment_amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Сумма к оплате', default=0)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='created', verbose_name='Статус')
    created_date = models.DateTimeField(auto_now_add=True, verbose_name='Дата выдачи')
    started_date = models.DateTimeField(null=True, blank=True, verbose_name='Дата начала работы')  # НОВОЕ ПОЛЕ
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

class Invitation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает'),
        ('accepted', 'Принята'),
        ('expired', 'Просрочена'),
    ]

    token = models.CharField(max_length=100, unique=True, verbose_name='Токен')
    created_by = models.ForeignKey(CustomUser, on_delete=models.CASCADE, verbose_name='Кем создано')
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    expires_at = models.DateTimeField(verbose_name='Действительно до')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name='Статус')
    accepted_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, 
                                   related_name='accepted_invitations', verbose_name='Кем принято')
    tags = models.CharField(max_length=500, blank=True, verbose_name='Ярлыки (через запятую)')

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"Приглашение для {self.email}"



class NavigationButton(models.Model):
    title = models.CharField(max_length=100, verbose_name='Название кнопки')
    url = models.CharField(max_length=500, verbose_name='URL ссылка')
    icon = models.CharField(max_length=50, default='🔗', verbose_name='Иконка')
    color = models.CharField(max_length=7, default='#2563eb', verbose_name='Цвет кнопки')
    order = models.IntegerField(default=0, verbose_name='Порядок отображения')
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Кнопка навигации'
        verbose_name_plural = 'Кнопки навигации'
    
    def __str__(self):
        return self.title