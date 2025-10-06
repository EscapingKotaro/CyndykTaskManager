from django.core.management.base import BaseCommand
from releases.models import GameRelease

class Command(BaseCommand):
    help = 'Очищает все записи о релизах из БД'

    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Подтверждение удаления',
        )

    def handle(self, *args, **options):
        total_games = GameRelease.objects.count()
        
        if not options['confirm']:
            self.stdout.write(
                self.style.WARNING(
                    f'⚠️  Вы собираетесь удалить {total_games} игр из БД!'
                )
            )
            self.stdout.write(
                self.style.WARNING(
                    'Для подтверждения запустите команду с флагом --confirm'
                )
            )
            return

        # Удаляем все игры
        deleted_count = GameRelease.objects.all().delete()[0]
        
        self.stdout.write(
            self.style.SUCCESS(
                f'✅ Удалено {deleted_count} игр из БД'
            )
        )