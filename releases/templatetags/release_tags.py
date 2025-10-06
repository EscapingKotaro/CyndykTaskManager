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

@register.filter
def get_marketplace_status(game, marketplace):
    """Возвращает отображаемый статус площадки"""
    try:
        status = game.get_marketplace_status(marketplace)
        dct={
            'Не опубликовано':'not_published',
            "Опубликовано":"fully_published",
            "Частично опубликовано":"partially_published",
        }
        st = game.get_marketplace_status_display(status)
        return dct.get(st,'not_published')
    except:
        return 'not_published'