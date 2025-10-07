from django.db import models
from django.core.validators import MinValueValidator
from decimal import Decimal
from django.conf import settings

class GameRelease(models.Model):
    PLATFORM_CHOICES = [
        ('PS4', 'PlayStation 4'),
        ('PS5', 'PlayStation 5'),
        ('SWITCH', 'Nintendo Switch'),
        ('SWITCH2', 'Nintendo Switch 2'),
        ('XBOX_ONE', 'Xbox One'),
        ('XBOX_SERIES', 'Xbox Series X/S'),
    ]
    
    MARKETPLACE_CHOICES = [
        ('AVITO', 'Avito'),
        ('DIFMARK', 'Difmark'),
        ('WILDBERRIES', 'Wildberries'),
        ('DIGISELLER', 'Digiseller'),
    ]
    
    LANGUAGE_CHOICES = [
        ('RUSSIAN', 'Русский'),
        ('ENGLISH', 'Английский'),
    ]
    
    # Основная информация
    title = models.CharField(max_length=200, verbose_name='Название игры')
    icon = models.ImageField(upload_to='game_icons/', blank=True, null=True, verbose_name='Иконка игры')
    release_date = models.DateField(verbose_name='Дата релиза')
    is_published = models.BooleanField(default=False, verbose_name='Опубликовано')
    
    # Платформы (многие ко многим через JSON)
    platforms = models.JSONField(
        default=list,
        verbose_name='Платформы',
        help_text='Список платформ: ["PS4", "PS5", "Switch"]'
    )
    
    # Площадки (многие ко многим через JSON)
    marketplaces = models.JSONField(
        default=["Avito", "Difmark", "Wildberries", "Digiseller"],
        verbose_name='Площадки',
        help_text='Список площадок: ["Avito", "Digiseller"]'
    )
    
    # Локализации (многие ко многим через JSON)
    languages = models.JSONField(
        default=list,
        verbose_name='Локализации',
        help_text='Список языков: ["Русский", "Английский"]'
    )
    
    # Публикации по площадкам и платформам (JSON поле для хранения связок площадка-платформы)
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
        return self.platforms if isinstance(self.platforms, list) else []
    
    def get_marketplaces_list(self):
        """Возвращает список площадок"""
        return self.marketplaces if isinstance(self.marketplaces, list) else []
    
    def get_languages_list(self):
        """Возвращает список языков"""
        return self.languages if isinstance(self.languages, list) else []
    
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
    
    def get_all_marketplaces(self):
        """Возвращает все возможные площадки"""
        return [choice[0] for choice in self.MARKETPLACE_CHOICES]
    
    def get_platform_icon(self, platform):
        """Возвращает иконку для платформы"""
        icons = {
            'PS4': '🎮',
            'PS5': '🎮',
            'SWITCH': '🎮', 
            'SWITCH2': '🎮',
            'XBOX_ONE': '🎮',
            'XBOX_SERIES': '🎮',
        }
        return icons.get(platform, '🎮')
    
    def get_marketplace_icon(self, marketplace):
        """Возвращает иконку для площадки"""
        icons = {
            'AVITO': 'platform_icons/avito.jpg',
            'DIFMARK': 'platform_icons/difmark.png', 
            'WILDBERRIES': 'platform_icons/wb.jpg',
            'DIGISELLER': 'platform_icons/diga.png',
        }
        return icons.get(marketplace, '')
    def get_all_marketplaces_display(self):
        """Возвращает данные по всем площадкам с иконками"""
        MARKETPLACE_ICONS = {
            'AVITO': 'platform_icons/avito.jpg',
            'DIFMARK': 'platform_icons/difmark.png', 
            'WILDBERRIES': 'platform_icons/wb.jpg',
            'DIGISELLER': 'platform_icons/diga.png',
        }
        #
        all_marketplaces = [choice[0] for choice in self.MARKETPLACE_CHOICES]
        #
        marketplaces = []
        i=0
        for marketplace in ['AVITO', 'DIFMARK', 'WILDBERRIES', 'DIGISELLER']:
            icon_path = MARKETPLACE_ICONS.get(marketplace)
            icon_url = f"{icon_path}" if icon_path else ""
            
            marketplaces.append({
                'code': all_marketplaces[i][1],
                'name': dict(self.MARKETPLACE_CHOICES).get(marketplace, marketplace),  # или просто marketplace
                'is_selected': getattr(self, f'marketplace_{marketplace.lower()}', False),
                'icon_url': icon_url
            })
            i+=1
        return marketplaces
    def toggle_platform_publication(self, marketplace, platform):
        """Переключает публикацию платформы на площадке"""
        publications = self.get_marketplace_platforms_dict()
        
        if marketplace not in publications:
            publications[marketplace] = []
        
        if platform in publications[marketplace]:
            publications[marketplace].remove(platform)
            # Если массив пустой, удаляем площадку
            if not publications[marketplace]:
                del publications[marketplace]
        else:
            publications[marketplace].append(platform)
        
        self.marketplace_platforms = publications
        self.save()
        return platform in publications.get(marketplace, [])

    def get_marketplace_status(self, marketplace):
        """Возвращает статус площадки"""
        publications = self.get_marketplace_platforms_dict()
        marketplace_platforms = publications.get(marketplace, [])
        all_platforms = self.get_platforms_list()
        
        if not marketplace_platforms:
            return 'not_published'
        elif len(marketplace_platforms) == len(all_platforms):
            return 'fully_published'
        else:
            return 'partially_published'

    def get_platform_publication_status(self, marketplace, platform):
        """Возвращает статус публикации платформы на площадке"""
        publications = self.get_marketplace_platforms_dict()
        return platform in publications.get(marketplace, [])
    def get_marketplace_status_display(self, status):
        """Возвращает текстовое представление статуса"""
        status_map = {
            'not_published': 'Не опубликовано',
            'partially_published': 'Частично опубликовано', 
            'fully_published': 'Опубликовано'
        }
        return status_map.get(status, 'Не опубликовано')