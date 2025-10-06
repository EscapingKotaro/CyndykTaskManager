from django import forms
from .models import GameRelease

class GameReleaseForm(forms.ModelForm):
    # Делаем поля для множественного выбора
    platforms = forms.MultipleChoiceField(
        choices=GameRelease.PLATFORM_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Платформы'
    )
    
    marketplaces = forms.MultipleChoiceField(
        choices=GameRelease.MARKETPLACE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Площадки'
    )
    
    languages = forms.MultipleChoiceField(
        choices=GameRelease.LANGUAGE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=True,
        label='Локализации'
    )
    
    class Meta:
        model = GameRelease
        fields = [
            'title', 'icon', 'release_date', 'is_published', 
            'platforms', 'marketplaces', 'languages', 'marketplace_platforms',
            'description', 'price'
        ]
        widgets = {
            'release_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
            'marketplace_platforms': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': '{"Avito": ["PS4", "PS5"], "Digiseller": ["Switch"]}'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Устанавливаем начальные значения для MultipleChoiceField
        if self.instance and self.instance.pk:
            self.fields['platforms'].initial = self.instance.platforms
            self.fields['marketplaces'].initial = self.instance.marketplaces
            self.fields['languages'].initial = self.instance.languages
    
    def save(self, commit=True):
        instance = super().save(commit=False)
        # Сохраняем множественные выборы как JSON
        instance.platforms = self.cleaned_data['platforms']
        instance.marketplaces = self.cleaned_data['marketplaces']
        instance.languages = self.cleaned_data['languages']
        if commit:
            instance.save()
        return instance