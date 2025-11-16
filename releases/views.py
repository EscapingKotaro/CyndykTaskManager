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
    
    platform = form.cleaned_data.get('platform')
    marketplace = form.cleaned_data.get('marketplace')
    language = form.cleaned_data.get('language')
    is_published = form.cleaned_data.get('is_published')
    sort_by = form.cleaned_data.get('sort_by') or 'release_date'
        
        # Фильтр по платформе
    if form.is_valid():
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
