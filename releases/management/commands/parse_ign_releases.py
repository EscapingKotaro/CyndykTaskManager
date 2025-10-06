from django.core.management.base import BaseCommand
from releases.parser import run_parser, get_parser_stats

class Command(BaseCommand):
    help = 'Парсит релизы игр с IGN.com и сохраняет в БД'

    def handle(self, *args, **options):
        self.stdout.write('🎮 Запуск парсера IGN релизов...')
        
        # Запускаем парсер
        new_games = run_parser()
        
        # Показываем статистику
        stats = get_parser_stats()
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Парсинг завершен! '
                f'Добавлено {len(new_games)} новых игр. '
                f'Всего в БД: {stats["total_games"]}, '
                f'Предстоящих: {stats["upcoming_games"]}'
            )
        )