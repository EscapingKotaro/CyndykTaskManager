from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.utils import timezone
from .models import GameRelease
from .forms import *
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.http import JsonResponse
from django.core.paginator import Paginator


from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from django.db.models import Q
from datetime import datetime, date


def require_api_key(view_func):
    """Декоратор для проверки API ключа"""
    def wrapper(request, *args, **kwargs):
        # Получаем API ключ из заголовков
        api_key = request.headers.get('X-API-Key') or request.GET.get('api_key')
        
        if not api_key:
            return JsonResponse({
                'success': False,
                'error': 'API key is required',
                'code': 'MISSING_API_KEY'
            }, status=401)
        
        try:
            request.api_key = api_key
            
            if api_key!="vvgahbjcgt4uhcJWfwehirjfbkygh23457JKWER":
                return JsonResponse({
                    'success': False,
                    'error': 'Invalid or inactive API key',
                    'code': 'INVALID_API_KEY'
                }, status=401)
        
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': 'API key validation error',
                'code': 'API_KEY_ERROR'
            }, status=500)
        
        return view_func(request, *args, **kwargs)
    
    return wrapper

def parse_release_date(date_str):
    """
    Парсит строку даты в объект date.
    Поддерживаем форматы:
    - "2026-03-31"
    - "2026-03-31 00:00" (время игнорируется, т.к. поле DateField)
    - "2026-03-31T00:00"
    """
    for fmt in ("%Y-%m-%d", "%Y-%m-%d %H:%M", "%Y-%m-%dT%H:%M"):
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.date()  # возвращаем только дату
        except ValueError:
            continue
    raise ValueError(f"Invalid date format: {date_str}. Use: YYYY-MM-DD")


@require_http_methods(["GET"])
@require_api_key
def get_game_releases(request):
    """
    Возвращает опубликованные релизы игр за указанный период.
    
    Параметры:
        - date_from: "2026-03-01" (начало диапазона, включительно)
        - date_to: "2026-03-31" (конец диапазона, включительно)
        - platform: "PS5" (опционально, фильтр по платформе)
        - marketplace: "Avito" (опционально, фильтр по площадке)
        - language: "Русский" (опционально, фильтр по языку)
        - search: "God of War" (опционально, поиск по названию)
    """
    
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    
    # Валидация обязательных параметров
    if not date_from or not date_to:
        return JsonResponse({
            'success': False,
            'error': 'Missing required parameters: date_from and date_to',
            'code': 'MISSING_PARAMETERS'
        }, status=400)
    
    # Парсинг дат
    try:
        dt_from = parse_release_date(date_from)
        dt_to = parse_release_date(date_to)
    except ValueError as e:
        return JsonResponse({
            'success': False,
            'error': str(e),
            'code': 'INVALID_DATE_FORMAT'
        }, status=400)
    
    # Базовый фильтр: опубликованные + диапазон дат
    queryset = GameRelease.objects.filter(
        is_published=True,
        release_date__gte=dt_from,
        release_date__lte=dt_to
    )
    
    # 🔍 Опциональные фильтры
    
    # Платформа (ищем в JSONField platforms)
    platform = request.GET.get('platform')
    if platform:
        queryset = queryset.filter(platforms__contains=[platform])
    
    # Площадка (ищем в JSONField marketplaces)
    marketplace = request.GET.get('marketplace')
    if marketplace:
        queryset = queryset.filter(marketplaces__contains=[marketplace])
    
    # Язык (ищем в JSONField languages)
    language = request.GET.get('language')
    if language:
        queryset = queryset.filter(languages__contains=[language])
    
    # Поиск по названию (регистронезависимый)
    search = request.GET.get('search')
    if search:
        queryset = queryset.filter(title__icontains=search)
    
    # Формируем ответ
    releases = []
    for release in queryset.order_by('release_date'):
        releases.append({
            'id': release.id,
            'title': release.title,
            'icon': request.build_absolute_uri(release.icon.url) if release.icon else None,
            'release_date': release.release_date.strftime("%Y-%m-%d"),
            'platforms': release.platforms,
            'marketplaces': release.marketplaces,
            'languages': release.languages,
            'marketplace_platforms': release.marketplace_platforms,
            'description': release.description,
            'price': str(release.price),  # Decimal → str для JSON
            'created_at': release.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            'updated_at': release.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
        })
    
    return JsonResponse({
        'success': True,
        'count': len(releases),
        'filters': {
            'date_from': dt_from.strftime("%Y-%m-%d"),
            'date_to': dt_to.strftime("%Y-%m-%d"),
            'platform': platform,
            'marketplace': marketplace,
            'language': language,
            'search': search,
        },
        'data': releases
    }, status=200, json_dumps_params={'ensure_ascii': False})

@login_required
def toggle_marketplace(request, pk):
    """AJAX запрос для переключения площадки"""
    if request.method == 'POST':
        game = get_object_or_404(GameRelease, pk=pk)
        marketplace = request.POST.get('marketplace')
        
        if marketplace:
            # Получаем текущий список площадок
            current_marketplaces = game.get_marketplaces_list()
            
            # Переключаем площадку
            if marketplace in current_marketplaces:
                # Убираем площадку
                current_marketplaces.remove(marketplace)
                # Также убираем все публикации для этой площадки
                marketplace_platforms = game.get_marketplace_platforms_dict()
                if marketplace in marketplace_platforms:
                    del marketplace_platforms[marketplace]
                game.marketplace_platforms = marketplace_platforms
            else:
                # Добавляем площадку
                current_marketplaces.append(marketplace)
            
            # Сохраняем обновленный список
            game.marketplaces = current_marketplaces
            game.save()
            
            return JsonResponse({
                'success': True,
                'is_selected': marketplace in game.get_marketplaces_list(),
                'marketplace': marketplace
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})

@login_required
def toggle_platform_publication(request, pk):
    """AJAX запрос для переключения публикации платформы"""
    if request.method == 'POST':
        game = get_object_or_404(GameRelease, pk=pk)
        marketplace = request.POST.get('marketplace')
        platform = request.POST.get('platform')
        
        if marketplace and platform:
            # Используем реальный метод модели
            is_published = game.toggle_platform_publication(marketplace, platform)
            status = game.get_marketplace_status(marketplace)
            
            return JsonResponse({
                'success': True,
                'is_published': is_published,
                'marketplace_status': status,
                'marketplace_status_display': game.get_marketplace_status_display(status)
            })
    
    return JsonResponse({'success': False, 'error': 'Invalid request'})
@login_required
def release_modal(request, pk):
    """Детальная информация для модального окна"""
    game = get_object_or_404(GameRelease, pk=pk)
    return render(request, 'releases/release_modal.html', {'game': game})
@login_required
def release_list(request):
    """Список релизов с фильтрами"""
    games = GameRelease.objects.all()
    
    # Применяем фильтры
    form = GameReleaseFilterForm(request.GET or None)
    if form.is_valid():
        platform = form.cleaned_data.get('platform')
        marketplace = form.cleaned_data.get('marketplace')
        language = form.cleaned_data.get('language')
        is_published = form.cleaned_data.get('is_published')
        sort_by = form.cleaned_data.get('sort_by') or 'release_date'
        
        # Фильтр по платформе
    
        if platform:
            games = games.filter(platforms__icontains=platform)
            
            # Фильтр по площадке
        if marketplace:
            games = games.filter(
                    Q(marketplace_platforms__icontains=marketplace) |
                    Q(marketplace_platforms__has_key=marketplace)
                )
            
            # Фильтр по языку
        if language:
            games = games.filter(languages__icontains=language)
            
            # Фильтр по статусу публикации
        if is_published == 'published':
            games = games.filter(is_published=True)
        elif is_published == 'not_published':
            games = games.filter(is_published=False)
            
            # Сортировка
        games = games.order_by(sort_by)
    
    # Статистика
    total_games = games.count()
    published_games = games.filter(is_published=True).count()
    upcoming_games = games.filter(release_date__gt=timezone.now().date()).count()
    # 🔥 ПАГИНАЦИЯ - ДОБАВЛЯЕМ ПОСЛЕ СОРТИРОВКИ
    paginator = Paginator(games, 20)  # 20 игр на страницу
    page_number = request.GET.get('page')

    # Если страница не указана, находим страницу с сегодняшними релизами
    if not page_number:
        today = timezone.now().date()
        # Находим индекс первого релиза на сегодня или позже
        for index, game in enumerate(games):
            if game.release_date >= today:
                page_number = (index // 20) + 1  # 20 - размер страницы
                break

    page_obj = paginator.get_page(page_number)

    # Заменяем games на page_obj в контексте
    games = page_obj
    
    context = {
        'games': games,
        'form': form,
        'total_games': total_games,
        'published_games': published_games,
        'upcoming_games': upcoming_games,
    }
    
    return render(request, 'releases/release_list.html', context)

@login_required
def release_detail(request, pk):
    """Детальная страница релиза"""
    game = get_object_or_404(GameRelease, pk=pk)
    return render(request, 'releases/release_detail.html', {'game': game})

@login_required
def release_create(request):
    """Создание нового релиза"""
    if request.method == 'POST':
        form = GameReleaseForm(request.POST, request.FILES)
        if form.is_valid():
            game = form.save()
            return redirect('releases:release_list')
    else:
        form = GameReleaseForm()
    
    return render(request, 'releases/release_form.html', {'form': form})

@login_required
def release_update(request, pk):
    """Редактирование релиза"""
    game = get_object_or_404(GameRelease, pk=pk)
    
    if request.method == 'POST':
        form = GameReleaseForm(request.POST, request.FILES, instance=game)
        if form.is_valid():
            form.save()
            return redirect('releases:release_list')
    else:
        form = GameReleaseForm(instance=game)
    
    return render(request, 'releases/release_form.html', {'form': form})

@login_required
def toggle_publish(request, pk):
    if request.user.is_superuser:
        game = get_object_or_404(GameRelease, id=pk)
        game.is_published = not game.is_published
        game.save()
        
        return JsonResponse({
            'success': True,
            'is_published': game.is_published,
            'game_id': pk
        })
