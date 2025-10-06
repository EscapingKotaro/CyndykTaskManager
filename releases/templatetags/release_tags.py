from django import template

register = template.Library()

@register.filter
def get_platform_status(game, args):
    """Возвращает статус публикации платформы"""
    try:
        marketplace, platform = args.split(',')
        return game.get_platform_publication_status(marketplace, platform)
    except:
        return False

@register.filter
def get_marketplace_status_display(game, marketplace):
    """Возвращает отображаемый статус площадки"""
    try:
        status = game.get_marketplace_status(marketplace)
        return game.get_marketplace_status_display(status)
    except:
        return 'Не опубликовано'