from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils import timezone
from django.db.models import Q, Sum

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
    def can_edit_user(self, target_user):
        """Может ли пользователь редактировать target_user"""
        if self.role == 'boss':
            # Босс может редактировать всех в своей команде
            return target_user.manager == self
        elif self.role == 'manager':
            # Менеджер может редактировать только своих подчиненных
            return target_user.manager == self
        return False
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
    def get_team_leadership(self):
    """Возвращает руководство команды (босс + все менеджеры)"""
    if self.role == 'boss':
        # Босс возвращает себя + всех менеджеров в его команде
        managers = CustomUser.objects.filter(manager=self, role='manager')
        return CustomUser.objects.filter(
            models.Q(id=self.id) |  # Сам босс
            models.Q(id__in=managers)  # Все его менеджеры
        ).distinct()
    elif self.role == 'manager':
        # Менеджер возвращает своего босса + всех менеджеров с тем же боссом
        boss = self.manager
        if boss:
            same_boss_managers = CustomUser.objects.filter(
                manager=boss, 
                role='manager'
            ).exclude(id=self.id)  # Исключаем себя
            return CustomUser.objects.filter(
                models.Q(id=boss.id) |  # Босс
                models.Q(id__in=same_boss_managers) |  # Другие менеджеры
                models.Q(id=self.id)  # Сам менеджер
            ).distinct()
        else:
            return CustomUser.objects.filter(id=self.id)
    else:
        # Техник возвращает своего босса + менеджера (если есть)
        boss = self.manager
        if boss:
            # Ищем менеджера который управляет этим техником
            direct_manager = CustomUser.objects.filter(
                manager=boss,
                role='manager',
                id=self.manager.id  # Если у техника менеджер не босс
            ).first()
            
            leadership = [boss]
            if direct_manager and direct_manager != boss:
                leadership.append(direct_manager)
            return CustomUser.objects.filter(id__in=[user.id for user in leadership])
        else:
            return CustomUser.objects.none()
    def get_team_users(self):
        """Возвращает пользователей, которых видит текущий пользователь"""
        if self.role == 'boss':
            # Босс видит всех, у кого ОН указан как manager
            return CustomUser.objects.filter(manager=self)
        elif self.role == 'manager':
            # Менеджер видит всех, у кого ТОТ ЖЕ boss (тот же manager)
            return CustomUser.objects.filter(manager=self.manager)
        else:
            # Техник видит только себя
            return CustomUser.objects.filter(id=self.id)
    
    def can_assign_task_to(self, target_user):
        """Может ли пользователь назначать задачи target_user"""
        if self.role == 'boss':
            # Босс может всем, у кого ОН manager
            return target_user.manager == self
        elif self.role == 'manager':
            # Менеджер может всем, у кого ТОТ ЖЕ manager (тот же boss)
            return target_user.manager == self.manager
        elif self.role == 'technician':
            return target_user == self  # Техник только себе
        return False
    def get_boss(self):
        """
        Возвращает босса пользователя (верхнего в иерархии)
        """
        current = self
        while current.manager is not None:
            current = current.manager
        return current
class Task(models.Model):
    STATUS_CHOICES = [
        ('proposed', '🟡 Предложена'),
        ('created', '🟢 Создана'), 
        ('in_progress', '🔵 В работе'),
        ('completed', '✅ Завершена'),
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
    controlled_by = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True,
                                     related_name='controlled_tasks', verbose_name='На контроле у')
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