import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta
import re
from django.utils import timezone
from .models import GameRelease

class IGNReleaseParser:
    """
    Парсер релизов игр с IGN.com
    """
    
    BASE_URL = "https://www.ign.com/upcoming/games"
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
    
    def parse_releases(self):
        """
        Основной метод парсинга релизов
        Возвращает список новых игр, добавленных в БД
        """
        print("🕷️ Начинаем парсинг IGN...")
        
        try:
            # Получаем HTML страницы
            response = self.session.get(self.BASE_URL, timeout=10)
            response.raise_for_status()
            
            # Парсим HTML
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Ищем блоки с играми
            games_data = self._extract_games_data(soup)
            
            # Сохраняем в БД
            new_games = self._save_to_database(games_data)
            
            print(f"✅ Парсинг завершен! Добавлено {len(new_games)} новых игр")
            return new_games
            
        except Exception as e:
            print(f"❌ Ошибка парсинга: {e}")
            return []
    
    def _extract_games_data(self, soup):
        """
        Извлекает данные об играх из HTML
        """
        games_data = []
        
        # Ищем блоки с играми (может потребоваться корректировка селекторов)
        game_cards = soup.find_all('div', class_=re.compile(r'game|release|item', re.I))
        
        for card in game_cards:
            try:
                game_data = self._parse_game_card(card)
                if game_data and self._is_valid_game(game_data):
                    games_data.append(game_data)
                    
            except Exception as e:
                print(f"⚠️ Ошибка парсинга карточки игры: {e}")
                continue
        
        # Если не нашли стандартным способом, пробуем альтернативные селекторы
        if not games_data:
            games_data = self._fallback_parsing(soup)
        
        print(f"📊 Найдено {len(games_data)} игр для обработки")
        return games_data
    
    def _parse_game_card(self, card):
        """
        Парсит отдельную карточку игры
        """
        game_data = {}
        
        # Название игры
        title_elem = (card.find('h2') or card.find('h3') or 
                     card.find('a', class_=re.compile(r'title|name', re.I)))
        if title_elem:
            game_data['title'] = title_elem.get_text().strip()
        
        # Дата релиза
        date_elem = card.find('span', class_=re.compile(r'date|release', re.I))
        if date_elem:
            game_data['release_date'] = self._parse_date(date_elem.get_text().strip())
        
        # Платформы
        platforms_elem = card.find('span', class_=re.compile(r'platform|console', re.I))
        if platforms_elem:
            game_data['platforms'] = self._parse_platforms(platforms_elem.get_text().strip())
        
        # Если не хватает критических данных, пропускаем
        if not game_data.get('title') or not game_data.get('release_date'):
            return None
            
        return game_data
    
    def _fallback_parsing(self, soup):
        """
        Альтернативные методы парсинга если основные не работают
        """
        games_data = []
        
        # Пробуем найти по структуре данных JSON-LD
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                # Здесь можно добавить парсинг JSON-LD если он есть на странице
                pass
            except:
                pass
        
        # Пробуем найти по другим селекторам
        items = soup.find_all('div', class_=re.compile(r'item|card|product', re.I))
        for item in items:
            try:
                title_elem = item.find(['h1', 'h2', 'h3', 'h4'])
                date_elem = item.find(text=re.compile(r'202[4-9]|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec', re.I))
                
                if title_elem and date_elem:
                    game_data = {
                        'title': title_elem.get_text().strip(),
                        'release_date': self._parse_date(date_elem),
                        'platforms': ['PS5', 'XBOX_SERIES', 'PC']  # Дефолтные платформы
                    }
                    games_data.append(game_data)
                    
            except Exception as e:
                continue
        
        return games_data
    
    def _parse_date(self, date_text):
        """
        Парсит дату из текста в объект datetime
        """
        try:
            # Убираем лишние слова
            clean_date = re.sub(r'[^\w\s,\.]', '', date_text)
            
            # Пробуем разные форматы дат
            date_formats = [
                '%B %d, %Y',  # October 15, 2024
                '%b %d, %Y',  # Oct 15, 2024  
                '%Y-%m-%d',   # 2024-10-15
                '%m/%d/%Y',   # 10/15/2024
                '%d.%m.%Y',   # 15.10.2024
            ]
            
            for fmt in date_formats:
                try:
                    return datetime.strptime(clean_date.strip(), fmt).date()
                except ValueError:
                    continue
            
            # Если не распарсилось, ставим дату через 3 месяца
            return timezone.now().date() + timedelta(days=90)
            
        except Exception:
            # Дефолтная дата если не удалось распарсить
            return timezone.now().date() + timedelta(days=90)
    
    def _parse_platforms(self, platforms_text):
        """
        Парсит платформы из текста
        """
        platforms = []
        text_lower = platforms_text.lower()
        
        # Маппинг платформ
        platform_map = {
            'ps4': 'PS4',
            'ps5': 'PS5', 
            'playstation 4': 'PS4',
            'playstation 5': 'PS5',
            'xbox one': 'XBOX_ONE',
            'xbox series': 'XBOX_SERIES',
            'switch': 'SWITCH',
            'nintendo switch': 'SWITCH',
        }
        
        for key, platform in platform_map.items():
            if key in text_lower:
                platforms.append(platform)
        
        # Убираем дубликаты
        platforms = list(set(platforms))
        
        # Если платформы не определились, ставим дефолтные
        if not platforms:
            platforms = ['PS5']
            
        return platforms
    
    def _is_valid_game(self, game_data):
        """
        Проверяет валидность данных игры
        """
        # Проверяем что есть название и дата
        if not game_data.get('title') or not game_data.get('release_date'):
            return False
        
        # Проверяем что дата в будущем или не очень далеком прошлом (до 1 года)
        max_past_date = timezone.now().date() - timedelta(days=365)
        if game_data['release_date'] < max_past_date:
            return False
            
        return True
    
    def _save_to_database(self, games_data):
        """
        Сохраняет игры в БД, только новые
        """
        new_games = []
        
        for game_data in games_data:
            try:
                # Проверяем существует ли уже такая игра
                existing_game = GameRelease.objects.filter(
                    title__iexact=game_data['title']
                ).first()
                
                if existing_game:
                    print(f"⏩ Пропускаем существующую игру: {game_data['title']}")
                    continue
                
                # Создаем новую игру
                game = GameRelease(
                    title=game_data['title'],
                    release_date=game_data['release_date'],
                    platforms=game_data.get('platforms', ['PS5', 'PC']),
                    marketplaces=[],  # Пока пустые площадки
                    languages=['ENGLISH', 'RUSSIAN'],  # Дефолтные языки
                    marketplace_platforms={},
                    description=f"Автоматически добавлено из IGN. Дата релиза: {game_data['release_date']}",
                    is_published=False  # По умолчанию не опубликовано
                )
                
                game.save()
                new_games.append(game)
                print(f"✅ Добавлена новая игра: {game_data['title']}")
                
            except Exception as e:
                print(f"❌ Ошибка сохранения игры {game_data.get('title')}: {e}")
                continue
        
        return new_games


# Утилитарные функции для запуска
def run_parser():
    """
    Запускает парсер и возвращает результат
    """
    parser = IGNReleaseParser()
    return parser.parse_releases()

def get_parser_stats():
    """
    Возвращает статистику по играм в БД
    """
    total_games = GameRelease.objects.count()
    upcoming_games = GameRelease.objects.filter(
        release_date__gte=timezone.now().date()
    ).count()
    
    return {
        'total_games': total_games,
        'upcoming_games': upcoming_games
    }