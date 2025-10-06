from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup
import time
import re
from datetime import datetime, timedelta
from django.utils import timezone
from .models import GameRelease

class IGNReleaseParser:
    """
    Парсер релизов игр с IGN.com с использованием Selenium
    """
    
    BASE_URL = "https://www.ign.com/upcoming/games"
    
    def __init__(self):
        self.setup_driver()
        self.stats = {
            'total_pages_loaded': 0,
            'game_links_found': 0,
            'game_cards_found': 0,
            'games_parsed': 0,
            'games_saved': 0,
            'errors': 0
        }
    
    def setup_driver(self):
        """Настраивает Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        
        self.driver = webdriver.Chrome(options=chrome_options)
        self.wait = WebDriverWait(self.driver, 15)
    
    def parse_releases(self):
        """
        Основной метод парсинга релизов
        """
        print("🕷️ Запускаем Selenium парсер IGN...")
        
        try:
            # Загружаем страницу
            self.driver.get(self.BASE_URL)
            self.stats['total_pages_loaded'] += 1
            
            # Ждем загрузки контента
            time.sleep(5)
            
            # Делаем скриншот для дебага
            self.driver.save_screenshot('ign_page.png')
            print("📸 Скриншот страницы сохранен как 'ign_page.png'")
            
            # Получаем HTML после полной загрузки
            page_source = self.driver.page_source
            
            # Сохраняем HTML для дебага
            with open('ign_page.html', 'w', encoding='utf-8') as f:
                f.write(page_source)
            print("💾 HTML страницы сохранен как 'ign_page.html'")
            
            # Анализируем структуру страницы
            self._analyze_page_structure(page_source)
            
            # Парсим игры
            games_data = self._parse_games_from_page()
            
            # Сохраняем в БД
            new_games = self._save_to_database(games_data)
            
            self.stats['games_saved'] = len(new_games)
            self._print_stats()
            
            print(f"✅ Парсинг завершен! Добавлено {len(new_games)} новых игр")
            return new_games
            
        except Exception as e:
            print(f"❌ Критическая ошибка парсинга: {e}")
            self.stats['errors'] += 1
            self._print_stats()
            return []
        finally:
            self.driver.quit()
    
    def _analyze_page_structure(self, page_source):
        """Анализирует структуру страницы для дебага"""
        soup = BeautifulSoup(page_source, 'html.parser')
        
        print("\n🔍 АНАЛИЗ СТРУКТУРЫ СТРАНИЦЫ:")
        print(f"📄 Длина HTML: {len(page_source)} символов")
        
        # Ищем различные элементы
        game_links = soup.find_all('a', href=re.compile(r'/games/|/reviews/'))
        self.stats['game_links_found'] = len(game_links)
        print(f"🔗 Найдено ссылок на игры: {len(game_links)}")
        
        # Ищем карточки игр
        game_cards = soup.find_all(['div', 'article'], class_=re.compile(r'game|item|card|product', re.I))
        self.stats['game_cards_found'] = len(game_cards)
        print(f"🎮 Найдено карточек игр: {len(game_cards)}")
        
        # Выводим первые 5 ссылок для примера
        print("\n📋 Примеры найденных ссылок:")
        for i, link in enumerate(game_links[:5]):
            href = link.get('href', '')
            text = link.get_text(strip=True)
            print(f"  {i+1}. {text} -> {href}")
        
        # Выводим первые 5 карточек для примера
        print("\n📋 Примеры найденных карточек:")
        for i, card in enumerate(game_cards[:5]):
            text = card.get_text(strip=True)[:100] + "..." if len(card.get_text(strip=True)) > 100 else card.get_text(strip=True)
            print(f"  {i+1}. {text}")
    
    def _parse_games_from_page(self):
        """Парсит игры со страницы используя Selenium"""
        games_data = []
        
        print("\n🎯 ПАРСИНГ ИГР:")
        
        try:
            # Пробуем разные селекторы для поиска игр
            selectors = [
                "//a[contains(@href, '/games/')]",
                "//article[contains(@class, 'game')]",
                "//div[contains(@class, 'game-item')]",
                "//figure//a",  # Твой xPath
                "//*[@id='main-content']//a",
            ]
            
            for selector in selectors:
                try:
                    elements = self.driver.find_elements(By.XPATH, selector)
                    print(f"🔎 Селектор '{selector}': найдено {len(elements)} элементов")
                    
                    if elements:
                        for i, element in enumerate(elements[:10]):  # Ограничим для теста
                            try:
                                game_data = self._parse_game_element(element)
                                if game_data and self._is_valid_game(game_data):
                                    games_data.append(game_data)
                                    self.stats['games_parsed'] += 1
                                    print(f"  ✅ Игра {i+1}: {game_data['title']}")
                            except Exception as e:
                                print(f"  ❌ Ошибка парсинга элемента {i+1}: {e}")
                                continue
                        
                        break  # Если нашли элементы, выходим из цикла
                        
                except Exception as e:
                    print(f"🔎 Селектор '{selector}': ошибка - {e}")
                    continue
            
            # Если не нашли через XPath, пробуем через CSS
            if not games_data:
                css_selectors = [
                    "a[href*='/games/']",
                    ".game-item",
                    ".item-game",
                    "article.game",
                ]
                
                for css_selector in css_selectors:
                    try:
                        elements = self.driver.find_elements(By.CSS_SELECTOR, css_selector)
                        print(f"🔎 CSS селектор '{css_selector}': найдено {len(elements)} элементов")
                        
                        if elements:
                            for i, element in enumerate(elements[:10]):
                                try:
                                    game_data = self._parse_game_element(element)
                                    if game_data and self._is_valid_game(game_data):
                                        games_data.append(game_data)
                                        self.stats['games_parsed'] += 1
                                        print(f"  ✅ Игра {i+1}: {game_data['title']}")
                                except Exception as e:
                                    print(f"  ❌ Ошибка парсинга элемента {i+1}: {e}")
                                    continue
                            
                            break
                            
                    except Exception as e:
                        print(f"🔎 CSS селектор '{css_selector}': ошибка - {e}")
                        continue
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге игр: {e}")
            self.stats['errors'] += 1
        
        return games_data
    
    def _parse_game_element(self, element):
        """Парсит данные из элемента игры"""
        try:
            game_data = {}
            
            # Получаем текст элемента
            element_text = element.text.strip()
            if not element_text or len(element_text) < 2:
                return None
            
            # Название игры - берем из текста элемента
            game_data['title'] = element_text.split('\n')[0] if '\n' in element_text else element_text
            
            # Пробуем получить ссылку
            href = element.get_attribute('href')
            if href:
                game_data['url'] = href
            
            # Дата релиза - пока ставим дефолтную
            game_data['release_date'] = timezone.now().date() + timedelta(days=60)
            
            # Платформы - дефолтные
            game_data['platforms'] = ['PS5']
            
            # Дополнительная информация из атрибутов
            title_attr = element.get_attribute('title')
            if title_attr and len(title_attr) > len(game_data['title']):
                game_data['title'] = title_attr
            
            return game_data
            
        except Exception as e:
            print(f"❌ Ошибка парсинга элемента: {e}")
            return None
    
    def _is_valid_game(self, game_data):
        """Проверяет валидность данных игры"""
        if not game_data.get('title'):
            return False
        
        # Проверяем что название не слишком короткое и не содержит мусор
        title = game_data['title']
        if len(title) < 2 or len(title) > 200:
            return False
        
        # Исключаем мусорные названия
        exclude_words = ['ign', 'game', 'review', 'news', 'trailer', 'video']
        if any(word in title.lower() for word in exclude_words):
            return False
            
        return True
    
    def _save_to_database(self, games_data):
        """Сохраняет игры в БД, только новые"""
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
                    title=game_data['title'][:200],  # Ограничиваем длину
                    release_date=game_data['release_date'],
                    platforms=game_data.get('platforms', ['PS5', 'PC']),
                    marketplaces=[],  # Пока пустые площадки
                    languages=['ENGLISH', 'RUSSIAN'],
                    marketplace_platforms={},
                    description=f"Автоматически добавлено из IGN. {game_data.get('url', '')}",
                    is_published=False
                )
                
                game.save()
                new_games.append(game)
                print(f"✅ Добавлена новая игра: {game_data['title']}")
                
            except Exception as e:
                print(f"❌ Ошибка сохранения игры {game_data.get('title')}: {e}")
                self.stats['errors'] += 1
                continue
        
        return new_games
    
    def _print_stats(self):
        """Выводит детальную статистику"""
        print("\n📊 ДЕТАЛЬНАЯ СТАТИСТИКА ПАРСИНГА:")
        print(f"   📄 Загружено страниц: {self.stats['total_pages_loaded']}")
        print(f"   🔗 Найдено ссылок на игры: {self.stats['game_links_found']}")
        print(f"   🎮 Найдено карточек игр: {self.stats['game_cards_found']}")
        print(f"   ✅ Успешно распарсено игр: {self.stats['games_parsed']}")
        print(f"   💾 Сохранено в БД: {self.stats['games_saved']}")
        print(f"   ❌ Ошибок: {self.stats['errors']}")


# Утилитарные функции
def run_parser():
    """Запускает парсер"""
    parser = IGNReleaseParser()
    return parser.parse_releases()

def get_parser_stats():
    """Возвращает статистику по играм в БД"""
    total_games = GameRelease.objects.count()
    upcoming_games = GameRelease.objects.filter(
        release_date__gte=timezone.now().date()
    ).count()
    published_games = GameRelease.objects.filter(is_published=True).count()
    
    return {
        'total_games': total_games,
        'upcoming_games': upcoming_games,
        'published_games': published_games
    }