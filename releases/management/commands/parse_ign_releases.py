from django.core.management.base import BaseCommand
from releases.models import GameRelease
from releases.parser import run_parser, get_parser_stats

class Command(BaseCommand):
    help = 'Парсит релизы игр с IGN.com и сохраняет в БД'

    def handle(self, *args, **options):
        self.stdout.write('🎮 Запуск парсера IGN релизов...')
        
        # Запускаем парсер
        new_games = run_parser()
        
        # Показываем статистику
        stats = get_parser_stats()
        
        self.stdout.write("\n📈 ФИНАЛЬНАЯ СТАТИСТИКА:")
        self.stdout.write(f"   🎮 Всего игр в БД: {stats['total_games']}")
        self.stdout.write(f"   📅 Предстоящих релизов: {stats['upcoming_games']}")
        self.stdout.write(f"   ✅ Опубликовано: {stats['published_games']}")
        
        # Добавляем статистику по платформам если есть
        if 'platform_stats' in stats and stats['platform_stats']:
            self.stdout.write("\n🎮 СТАТИСТИКА ПО ПЛАТФОРМАМ:")
            for platform, count in stats['platform_stats'].items():
                self.stdout.write(f"   {platform}: {count} игр")
        
        self.stdout.write(
            self.style.SUCCESS(
                f'\n✅ Парсинг завершен! Добавлено {len(new_games)} новых игр'
            )
        )