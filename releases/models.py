from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal

class GameRelease(models.Model):
    PLATFORM_CHOICES = [
        ('PS4', 'PlayStation 4'),
        ('PS5', 'PlayStation 5'),
        ('SWITCH', 'Nintendo Switch'),
        ('SWITCH2', 'Nintendo Switch 2'),
        ('XBOX_ONE', 'Xbox One'),
        ('XBOX_SERIES', 'Xbox Series X/S'),
        ('PC', 'PC'),
    ]
    
    MARKETPLACE_CHOICES = [
        ('AVITO', 'Avito'),
        ('DIFMARK', 'Difmark'),
        ('WILDBERRIES', 'Wildberries'),
        ('DIGISELLER', 'Digiseller'),
        ('STEAM', 'Steam'),
        ('EPIC', 'Epic Games Store'),
    ]
    
    LANGUAGE_CHOICES = [
        ('RUSSIAN', 'Русский'),
        ('ENGLISH', 'Английский'),
        ('MULTI', 'Мульти язык'),
        ('OTHER', 'Другая'),
    ]
    
    # Основная информация
    title = models.CharField(max_length=200, verbose_name='Название игры')
    icon = models.ImageField(upload_to='game_icons/', blank=True, null=True, verbose_name='Иконка игры')
    release_date = models.DateField(verbose_name='Дата релиза')
    is_published = models.BooleanField(default=False, verbose_name='Опубликовано')
    
    # Платформы (многие ко многим)
    platforms = models.CharField(max_length=300, verbose_name='Платформы')
    
    # Локализации (многие ко многим)
    languages = models.CharField(max_length=200, verbose_name='Локализации')
    
    # Площадки публикации (JSON поле для хранения связок площадка-платформы)
    marketplace_platforms = models.JSONField(
        default=dict,
        verbose_name='Публикации по площадкам',
        help_text='Формат: {"Avito": ["PS4", "PS5"], "Digiseller": ["Switch"]}'
    )
    
    # Дополнительная информация
    description = models.TextField(blank=True, verbose_name='Описание игры')
    price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        default=0,
        verbose_name='Цена',
        validators=[MinValueValidator(Decimal('0'))]
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name='Дата создания')
    updated_at = models.DateTimeField(auto_now=True, verbose_name='Дата обновления')
    
    class Meta:
        verbose_name = 'Релиз игры'
        verbose_name_plural = 'Релизы игр'
        ordering = ['release_date', 'title']
        indexes = [
            models.Index(fields=['release_date']),
            models.Index(fields=['is_published']),
        ]
    
    def __str__(self):
        return f"{self.title} ({self.release_date})"
    
    def get_platforms_list(self):
        """Возвращает список платформ"""
        return [p.strip() for p in self.platforms.split(',')] if self.platforms else []
    
    def get_languages_list(self):
        """Возвращает список языков"""
        return [lang.strip() for lang in self.languages.split(',')] if self.languages else []
    
    def get_marketplace_platforms_dict(self):
        """Возвращает словарь площадка->платформы"""
        return self.marketplace_platforms or {}
    
    def is_released(self):
        """Проверяет, вышел ли уже релиз"""
        from django.utils import timezone
        return self.release_date <= timezone.now().date()
    
    def days_until_release(self):
        """Количество дней до релиза"""
        from django.utils import timezone
        from datetime import date
        today = timezone.now().date()
        delta = self.release_date - today
        return delta.days if delta.days >= 0 else 0