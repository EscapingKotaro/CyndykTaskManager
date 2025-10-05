from django import forms
from .models import GameRelease

class GameReleaseForm(forms.ModelForm):
    class Meta:
        model = GameRelease
        fields = [
            'title', 'icon', 'release_date', 'is_published', 
            'platforms', 'languages', 'marketplace_platforms',
            'description', 'price'
        ]
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'platforms': forms.TextInput(attrs={
                'placeholder': 'PS4, PS5, Switch, Xbox Series...'
            }),
            'languages': forms.TextInput(attrs={
                'placeholder': 'Русский, Английский...'
            }),
        }

class GameReleaseFilterForm(forms.Form):
    platform = forms.ChoiceField(
        choices=[('', 'Все платформы')] + GameRelease.PLATFORM_CHOICES,
        required=False,
        label='Платформа'
    )
    marketplace = forms.ChoiceField(
        choices=[('', 'Все площадки')] + GameRelease.MARKETPLACE_CHOICES,
        required=False,
        label='Площадка'
    )
    language = forms.ChoiceField(
        choices=[('', 'Все языки')] + GameRelease.LANGUAGE_CHOICES,
        required=False,
        label='Язык'
    )
    is_published = forms.ChoiceField(
        choices=[
            ('', 'Все'),
            ('published', 'Опубликованные'),
            ('not_published', 'Неопубликованные')
        ],
        required=False,
        label='Статус публикации'
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('release_date', 'По дате релиза'),
            ('title', 'По названию'),
            ('-created_at', 'Новые сначала'),
        ],
        required=False,
        label='Сортировка'
    )