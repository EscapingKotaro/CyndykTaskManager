import time
import requests
from bs4 import BeautifulSoup
from django.core.management.base import BaseCommand
from django.utils import timezone
from releases.models import GameRelease


class Command(BaseCommand):
    help = 'Проверяет русскую локализацию для игр на DekuDeals и обновляет БД'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--delay',
            type=float,
            default=2.0,
            help='Задержка между запросами в секундах (по умолчанию: 2)'
        )
        parser.add_argument(
            '--game-id',
            type=int,
            help='Проверить только конкретную игру по ID'
        )
        parser.add_argument(
            '--force-all',
            action='store_true',
            help='Проверить все игры, не только с русским языком'
        )

    def __init__(self):
        super().__init__()
        self.session_cookies = [
            'BAh7DEkiD3Nlc3Npb25faWQGOgZFVG86HVJhY2s6OlNlc3Npb246OlNlc3Npb25JZAY6D0BwdWJsaWNfaWRJIkU0ZjEzMjA3OWZjNWFmYTY0NjI0Njk2OGQyOGYzZTdhMzUyNGJlNzMzMTU0OTkzMDUzYmQ5Y2U5MWU3YmExZGEyBjsARkkiCWNzcmYGOwBGSSIxUnVPMWN3WkUwS3hXWE5jd2l1ZlpTdkctMDJHLUUtMl9ISFRXVjhfNWxUYz0GOwBGSSIOX19GTEFTSF9fBjsARnsASSILc291cmNlBjsARiIXaHR0cHM6Ly9lLm1haWwucnUvSSIMbGFuZGluZwY7AEZJIgYvBjsAVEkiDGNvdW50cnkGOwBGSSIHdXMGOwBUSSIJYWJpZAY7AEZJIhk5MDQyNDgxOTg2OTYxNTk0ODk5MgY7AEY%3D--be10e9f18362118284078c9f9c33b6f92eb694a7'
        ]
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:109.0) Gecko/20100101 Firefox/115.0',
        }

    def get_dekudeals_url(self, game_title):
        """Генерирует URL для DekuDeals на основе названия игры"""
        slug = game_title.lower()
        slug = ''.join(c if c.isalnum() or c == ' ' else ' ' for c in slug)
        slug = '-'.join(slug.split())
        return f"https://www.dekudeals.com/items/{slug}"

    def check_game_localization(self, game_title):
        """Проверяет наличие русской локализации для игры"""
        url = self.get_dekudeals_url(game_title)
        loco=[]
        
        for cookie in self.session_cookies:
            try:
                cookies = {'rack.session': cookie}
                response = requests.get(url, cookies=cookies, headers=self.headers, timeout=10)
                
                if response.status_code == 200:
                    soup = BeautifulSoup(response.content, "html.parser")
                    
                    # Ищем блок с языками
                    language_sections = soup.select('div > div > ul > li')
                    for section in language_sections:
                        text = section.get_text(strip=True)
                        if 'Languages:' in text or 'Language:' in text:
                            has_russian = any(word in text for word in ['Russian', 'русский', 'Русский'])
                            if has_russian and 'RUSSIAN' not in loco: loco.append('RUSSIAN')
                        if 'Languages:' in text or 'Language:' in text:
                            has_russian = any(word in text for word in ['English'])
                            if has_russian and 'ENGLISH' not in loco: loco.append('ENGLISH')
                    
                    # Альтернативные селекторы
                    details_sections = soup.select('.item-details, .game-info, .details')
                    for section in details_sections:
                        text = section.get_text()
                        if any(word in text for word in ['Languages:', 'Language:', 'Языки:', 'Язык:']):
                            has_russian = any(word in text for word in ['Russian', 'русский', 'Русский'])
                            if has_russian and 'RUSSIAN' not in loco: loco.append('RUSSIAN')
                        if any(word in text for word in ['Languages:', 'Language:', 'Языки:', 'Язык:']):
                            has_russian = any(word in text for word in ['English'])
                            if has_russian and 'ENGLISH' not in loco: loco.append('ENGLISH')



                            
                
                return loco
                time.sleep(1)
                
            except requests.RequestException as e:
                self.stdout.write(self.style.WARNING(f"Ошибка при проверке {game_title}: {e}"))
                continue
        
        return None

    def handle(self, *args, **options):
        delay = options['delay']
        game_id = options['game_id']
        force_all = options['force_all']
        
        self.stdout.write(self.style.SUCCESS('🚀 Запуск проверки локализаций...'))
        
        # Определяем какие игры проверять
        if game_id:
            games = GameRelease.objects.filter(id=game_id)
            self.stdout.write(f"Проверяем игру с ID: {game_id}")
        elif force_all:
            games = GameRelease.objects.all()
            self.stdout.write("Проверяем ВСЕ игры (режим --force-all)")
        else:
            # Только игры с русским языком
            games_with_russian = []
            all_games = GameRelease.objects.all()
            
            for game in all_games:
                languages = game.get_languages_list()
                if 'UNKNOW' in languages:
                    games_with_russian.append(game)
            
            games = games_with_russian
            self.stdout.write(f"Проверяем игры с русским языком: {len(games)} шт")
        
        if not games:
            self.stdout.write(self.style.WARNING("❌ Не найдено игр для проверки"))
            return
        
        updated_count = 0
        failed_count = 0
        total = len(games)
        
        for i, game in enumerate(games, 1):
            self.stdout.write(f"[{i}/{total}] Проверяем: {game.title}")
            
            new_loco = self.check_game_localization(game.title)
            new_loco.sort()
            
            if new_loco is not None:

                if new_loco!=[]:
                    game.languages = new_loco
                    game.save()
                    updated_count += 1
            else:
                self.stdout.write(self.style.ERROR(f"  ⚠️  Не удалось проверить"))
                failed_count += 1
            
            # Задержка между запросами
            if i < total:  # Не ждать после последней игры
                time.sleep(delay)
        
        # Итоги
        self.stdout.write("\n" + "="*50)
        self.stdout.write(self.style.SUCCESS(f"🎉 ПРОВЕРКА ЗАВЕРШЕНА!"))
        self.stdout.write(f"📊 Обработано игр: {total}")
        self.stdout.write(f"✅ Обновлено: {updated_count}")
        self.stdout.write(f"❌ Ошибок: {failed_count}")
        self.stdout.write("="*50)