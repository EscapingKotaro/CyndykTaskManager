import requests
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from bs4 import BeautifulSoup
import time
import re
import os
from datetime import datetime, timedelta
from django.utils import timezone
from django.core.files import File
from tempfile import NamedTemporaryFile
from .models import GameRelease


class IGNReleaseParser:
    """
    Парсер релизов игр с IGN.com - только ближайшие 2 недели
    """
    
    
    
    def __init__(self):
        self.setup_driver()
        self.stats = {
            'total_pages_loaded': 0,
            'game_links_found': 0,
            'games_parsed': 0,
            'games_saved': 0,
            'invalid_platform_skipped': 0,
            'too_far_skipped': 0,
            'errors': 0
        }
        # Рассчитываем диапазон дат (ближайшие 2 недели)
        self.today = timezone.now().date()
        self.max_date = self.today + timedelta(days=18)
        self.BASE_URL = "https://www.ign.com/upcoming/games"
    
    def setup_driver(self):
        """Настраивает Chrome driver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless=new")
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
        # Явно указываем путь к Chrome
        
        chrome_options.add_argument("--disable-features=VizDisplayCompositor")
        chrome_options.add_argument("--disable-background-timer-throttling")
        chrome_options.add_argument("--disable-backgrounding-occluded-windows")
        chrome_options.add_argument("--disable-renderer-backgrounding")
        chrome_options.add_argument("--disable-ipc-flooding-protection")

        
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        chrome_options.add_argument("--disable-translate")
        chrome_options.add_argument("--disable-default-apps")

        #
        chrome_options.add_argument("--disable-extensions")
        chrome_options.add_argument("--disable-plugins")
        
        chrome_options.binary_location = "/usr/bin/google-chrome"
        # Явно указываем путь к ChromeDriver
        service = webdriver.ChromeService(executable_path="/usr/local/bin/chromedriver")
        
        self.driver = webdriver.Chrome(service=service, options=chrome_options)
    
    def parse_releases(self):
        """
        Основной метод парсинга релизов - только ближайшие 2 недели
        """
        print("🕷️ Запускаем Selenium парсер IGN...")
        print(f"📅 Ищем игры с {self.today} по {self.max_date}")
        
        try:
            # Устанавливаем таймауты для драйвера
            self.driver.set_page_load_timeout(60)
            self.driver.implicitly_wait(10)
            
            print("🌐 Загружаем страницу IGN...")
            
            # Загружаем страницу с повторными попытками
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    self.driver.get(self.BASE_URL)
                    self.stats['total_pages_loaded'] += 1
                    print(f"✅ Страница загружена (попытка {attempt + 1})")
                    break
                except Exception as e:
                    print(f"⚠️ Ошибка загрузки страницы (попытка {attempt + 1}): {e}")
                    if attempt == max_retries - 1:
                        raise e
                    time.sleep(5)
            
            # Ждем загрузки контента
            print("⏳ Ждем загрузки контента...")
            time.sleep(10)
            
            # Проверим что страница загрузилась
            page_title = self.driver.title
            print(f"📄 Заголовок страницы: {page_title}")
            
            # Сохраним скриншот для отладки
            try:
                self.driver.save_screenshot("/tmp/ign_page.png")
                print("📸 Скриншот сохранен: /tmp/ign_page.png")
            except:
                pass
            
            # Парсим игры
            games_data = self._parse_games_from_page()
            
            # Сохраняем в БД
            new_games = self._save_to_database(games_data)
            
            self.stats['games_saved'] = len(new_games)
            self._print_stats()
            
            print(f"✅ Парсинг завершен! Добавлено {len(new_games)} новых игр")


            self._select_calendar_months()

            games_data = self._parse_games_from_page()

            new_games += self._save_to_database(games_data)
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

    def _select_calendar_months(self):
        """Открывает календарь и выбирает нужные месяцы для парсинга"""
        try:
            print("🗓️ Работаем с календарем...")
            
            # 1. Находим и кликаем на кнопку календаря чтобы открыть выпадающее меню
            calendar_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'calendar-dropdown')]")
            calendar_btn.click()
            print("✅ Открыли календарь")
            time.sleep(2)
            
            # 2. Определяем какие месяцы нам нужны
            current_month = timezone.now().month
            current_year = timezone.now().year
            
            # Месяцы которые нужно проверить (текущий и следующий)
            months_to_check = [current_month + 1]
            if current_month == 12:  # Если декабрь, добавляем январь следующего года
                months_to_check = [1]
            
            # 3. Для каждого нужного месяца:
            for month_num in months_to_check:
                # Пропускаем если месяц уже прошел
                if month_num < current_month and month_num != 1:  # Исключение для января
                    continue
                    
                # Получаем код месяца (JAN, FEB, etc)
                month_codes = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 
                            'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']
                month_code = month_codes[month_num - 1]
                
                print(f"🔍 Ищем игры за {month_code}...")
                
                # 4. Если нужно сменить год (при переходе с декабря на январь)
                if month_num == 1 and current_month == 12:
                    next_year_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'next-button')]")
                    next_year_btn.click()
                    print("✅ Перешли на следующий год")
                    time.sleep(1)
                
                # 5. Кликаем на нужный месяц
                month_btn = self.driver.find_element(By.XPATH, f"//button[@data-cy='{month_code}']")
                month_btn.click()
                print(f"✅ Выбрали месяц {month_code}")
                
                # 6. Ждем загрузки игр
                time.sleep(5)
                
                # 7. Парсим игры с этой страницы
                month_games = self._parse_games_from_page()
                print(f"📊 Нашли {len(month_games)} игр за {month_code}")
                
                # 8. Возвращаемся в календарь для следующего месяца
                if month_num != months_to_check[-1]:  # Если не последний месяц в списке
                    calendar_btn = self.driver.find_element(By.XPATH, "//button[contains(@class, 'calendar-dropdown')]")
                    calendar_btn.click()
                    time.sleep(2)
                    
        except Exception as e:
            print(f"⚠️ Ошибка работы с календарем: {e}")
            # Продолжаем парсинг даже если с календарем проблемы
    
    def _parse_games_from_page(self):
        """Парсит игры со страницы - только ближайшие 2 недели"""
        games_data = []
        
        print("\n🎯 ПАРСИНГ ИГР:")
        
        try:
            # Ищем все ссылки на игры
            game_links = self.driver.find_elements(By.XPATH, "//a[contains(@href, '/games/')]")
            print(f"🔎 Найдено {len(game_links)} ссылок на игры")
            
            for i, element in enumerate(game_links):
                try:
                    game_data = self._parse_game_element(element)
                    if not game_data:
                        continue
                        
                    # Проверяем подходит ли игра по дате
                    if self._is_game_in_time_range(game_data):
                        if self._is_valid_game(game_data):
                            games_data.append(game_data)
                            self.stats['games_parsed'] += 1
                            print(f"    ✅ {game_data['title']} - {game_data['release_date']} - {game_data['platforms']}")
                        else:
                            print(f"    ⏩ Пропускаем (неподходящие платформы): {game_data['title']} - {game_data.get('platforms', [])}")
                            self.stats['invalid_platform_skipped'] += 1
                    else:
                        #print(f"    ⏩ Пропускаем (дата вне диапазона): {game_data['title']} - {game_data['release_date']}")
                        self.stats['too_far_skipped'] += 1
                        
                except Exception as e:
                    print(f"  ❌ Ошибка парсинга элемента {i+1}: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ Ошибка при парсинге игр: {e}")
            self.stats['errors'] += 1
        
        return games_data
    
    def _is_game_in_time_range(self, game_data):
        """Проверяет что игра выходит в ближайшие 2 недели"""
        release_date = game_data.get('release_date')
        if not release_date:
            return False
        
        # Проверяем что дата в диапазоне сегодня + 14 дней
        return self.today <= release_date <= self.max_date
    
    def _parse_game_element(self, element):
        """Парсит данные из элемента игры"""
        try:
            game_data = {}
            element_html = element.get_attribute('outerHTML')
            soup = BeautifulSoup(element_html, 'html.parser')
            
            # Название
            title_elem = soup.find('figcaption', class_=re.compile(r'tile-title'))
            if title_elem:
                game_data['title'] = title_elem.get_text(strip=True)
            else:
                element_text = element.text.strip()
                lines = [line.strip() for line in element_text.split('\n') if line.strip()]
                if lines:
                    game_data['title'] = lines[0]
            
            if not game_data.get('title'):
                return None
            
            # Дата
            date_elem = soup.find('div', class_=re.compile(r'tile-meta'))
            if date_elem:
                date_text = date_elem.get_text(strip=True)
                game_data['release_date'] = self._parse_date(date_text)
            else:
                element_text = element.text.strip()
                date_match = re.search(r'([A-Za-z]{3,10}\s+\d{1,2},\s+\d{4})', element_text)
                if date_match:
                    game_data['release_date'] = self._parse_date(date_match.group(1))
                else:
                    # Если дату не нашли, пропускаем игру
                    return None
            
            # Платформы
            platforms_elem = soup.find('div', class_=re.compile(r'platforms'))
            if platforms_elem:
                platforms = self._parse_platforms_from_element(platforms_elem)
                game_data['platforms'] = platforms
            else:
                game_data['platforms'] = []
            
            # Картинка
            img_elem = soup.find('img')
            if img_elem:
                img_src = img_elem.get('src')
                if img_src:
                    game_data['image_url'] = img_src
            
            # URL
            href = element.get_attribute('href')
            if href:
                if href.startswith('/'):
                    href = 'https://www.ign.com' + href
                game_data['url'] = href
            
            return game_data
            
        except Exception as e:
            print(f"❌ Ошибка парсинга элемента: {e}")
            return None
    
    def _parse_platforms_from_element(self, platforms_elem):
        """Парсит платформы из HTML элемента - только нужные нам платформы"""
        platforms = []
        
        # Ищем иконки платформ
        platform_icons = platforms_elem.find_all(['span', 'img'], class_=re.compile(r'platform|icon', re.I))
        
        # Наши допустимые платформы
        ALLOWED_PLATFORMS = ['PS4', 'PS5', 'SWITCH', 'SWITCH2', 'XBOX_ONE', 'XBOX_SERIES']
        
        for icon in platform_icons:
            # Проверяем классы и атрибуты для определения платформы
            class_str = ' '.join(icon.get('class', []))
            alt_text = icon.get('alt', '').lower()
            src = icon.get('src', '').lower()
            
            # Определяем платформу по различным признакам
            platform_map = {
                'ps4': 'PS4',
                'playstation-4': 'PS4',
                'ps5': 'PS5', 
                'playstation-5': 'PS5',
                'xbox-one': 'XBOX_ONE',
                'xbox-series': 'XBOX_SERIES',
                'switch-2': 'SWITCH2',
                'switch2': 'SWITCH2',
                'switch': 'SWITCH',
            }
            
            for key, platform in platform_map.items():
                if (key in class_str or key in alt_text or key in src) and platform in ALLOWED_PLATFORMS:
                    platforms.append(platform)
                    break
        
        # Убираем дубликаты
        platforms = list(set(platforms))
        
        return platforms
    
    def _parse_date(self, date_text):
        """Парсит дату из текста в объект datetime"""
        try:
            # Убираем лишние символы
            clean_date = re.sub(r'[^\w\s,]', '', date_text.strip())
            
            # Пробуем разные форматы дат
            date_formats = [
                '%b %d, %Y',  # Oct 1, 2025
                '%B %d, %Y',  # October 1, 2025
            ]
            
            for fmt in date_formats:
                try:
                    parsed_date = datetime.strptime(clean_date, fmt).date()
                    return parsed_date
                except ValueError:
                    continue
            
            return None
            
        except Exception as e:
            print(f"⚠️ Ошибка парсинга даты '{date_text}': {e}")
            return None
    
    def _download_image(self, image_url, game_title):
        """Скачивает и сохраняет изображение игры"""
        try:
            if not image_url:
                return None
                
            # Очищаем название для имени файла
            clean_title = re.sub(r'[^\w\s-]', '', game_title)
            clean_title = re.sub(r'\s+', '_', clean_title)
            filename = f"{clean_title}.jpg"
            
            # Скачиваем изображение
            response = requests.get(image_url, timeout=10)
            response.raise_for_status()
            
            # Сохраняем во временный файл
            with NamedTemporaryFile(delete=False, suffix='.jpg') as temp_file:
                temp_file.write(response.content)
                temp_file.flush()
                
                return temp_file.name
                
        except Exception as e:
            print(f"⚠️ Ошибка загрузки изображения для {game_title}: {e}")
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
        exclude_words = ['ign', 'game', 'review', 'news', 'trailer', 'video', 'upcoming']
        if any(word in title.lower() for word in exclude_words):
            return False
        
        # Проверяем что есть наши платформы
        platforms = game_data.get('platforms', [])
        allowed_platforms = ['PS4', 'PS5', 'SWITCH', 'SWITCH2', 'XBOX_ONE', 'XBOX_SERIES']
        has_our_platforms = any(platform in allowed_platforms for platform in platforms)
        
        if not has_our_platforms:
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
                    #print(f"⏩ Пропускаем существующую игру: {game_data['title']}")
                    continue
                
                # Скачиваем изображение
                image_path = None
                if game_data.get('image_url'):
                    image_path = self._download_image(game_data['image_url'], game_data['title'])
                
                # Создаем новую игру
                game = GameRelease(
                    title=game_data['title'][:200],
                    release_date=game_data['release_date'],
                    platforms=game_data.get('platforms', []),
                    # Все площадки по умолчанию
                    marketplaces=['AVITO', 'DIFMARK','TELEGRAM', 'WILDBERRIES', 'DIGISELLER','FUNPAY','GGSEL'], # 'DARKSTORE'
                    languages=['UNKNOW'],
                    marketplace_platforms={},  # Пустой словарь вместо публикаций всех платформ
                    description=f"Автоматически добавлено из IGN. {game_data.get('url', '')}",
                    # По умолчанию опубликовано
                    is_published=True
                )
                
                # Сохраняем игру чтобы получить ID
                game.save()

                if game.platforms:  # Если есть платформы
                    game.marketplace_platforms['DIFMARK'] = game.platforms.copy()
                    game.save()
                # Добавляем изображение если скачали
                if image_path and os.path.exists(image_path):
                    try:
                        with open(image_path, 'rb') as img_file:
                            game.icon.save(f"{game.id}_{game.title[:50]}.jpg", File(img_file), save=True)
                        print(f"    🖼️ Изображение сохранено для {game.title}")
                    except Exception as e:
                        print(f"⚠️ Ошибка сохранения изображения: {e}")
                    finally:
                        # Удаляем временный файл
                        try:
                            os.unlink(image_path)
                        except:
                            pass
                
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
        print(f"   ✅ Успешно распарсено игр: {self.stats['games_parsed']}")
        print(f"   ⏩ Пропущено игр с неподходящими платформами: {self.stats['invalid_platform_skipped']}")
        print(f"   ⏩ Пропущено игр с датой вне диапазона: {self.stats['too_far_skipped']}")
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
    
    # Статистика по платформам
    platform_stats = {}
    for game in GameRelease.objects.all():
        for platform in game.get_platforms_list():
            platform_stats[platform] = platform_stats.get(platform, 0) + 1
    
    return {
        'total_games': total_games,
        'upcoming_games': upcoming_games,
        'published_games': published_games,
        'platform_stats': platform_stats  # Добавляем статистику по платформам
    }