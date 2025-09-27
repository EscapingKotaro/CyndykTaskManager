from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import *
import re

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'due_date', 'payment_amount']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class UserForm(forms.ModelForm):
    password = forms.CharField(
        label='Пароль',
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Введите пароль'
        }),
        help_text='Пароль должен содержать минимум 8 символов'
    )
    
    telegram_username = forms.CharField(
        label='Ник в Telegram',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '@username'
        }),
        help_text='Необязательное поле'
    )
    
    tags = forms.CharField(
        label='Теги и навыки',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'дизайн, верстка, копирайтинг...'
        }),
        help_text='Укажите через запятую'
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'email', 'telegram_username', 'tags', 'password']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите логин'
            }),
            'first_name': forms.TextInput(attrs={
                'class': 'form-control', 
                'placeholder': 'Введите имя'
            }),
            'email': forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'email@example.com'
            }),
        }
        help_texts = {
            'username': 'Только английские буквы, цифры и символы @/./+/-/_',
            'email': 'На этот email будут отправляться уведомления',
        }

    def clean_telegram_username(self):
        telegram_username = self.cleaned_data.get('telegram_username', '').strip()
        if telegram_username:
            # Убираем @ если пользователь его ввел
            if telegram_username.startswith('@'):
                telegram_username = telegram_username[1:]
            # Проверяем формат
            if not re.match(r'^[a-zA-Z0-9_]{5,32}$', telegram_username):
                raise forms.ValidationError('Некорректный формат Telegram username')
        return telegram_username

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '').strip()
        if tags:
            # Очищаем и форматируем теги
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if len(tags_list) > 10:
                raise forms.ValidationError('Не более 10 тегов')
            return ', '.join(tags_list)
        return tags

    def clean_password(self):
        password = self.cleaned_data.get('password')
        if len(password) < 8:
            raise forms.ValidationError('Пароль должен содержать минимум 8 символов')
        return password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])
        if commit:
            user.save()
        return user

class PaymentForm(forms.ModelForm):
    class Meta:
        model = Payment
        fields = ['employee', 'amount', 'description']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }


class CustomPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Улучшаем подсказки
        self.fields['new_password1'].help_text = """
            Ваш пароль должен содержать как минимум 8 символов, 
            не должен быть слишком простым или состоять только из цифр.
        """
        
        # Стилизуем поля
        for field_name in self.fields:
            field = self.fields[field_name]
            field.widget.attrs.update({
                'class': 'form-control',
                'placeholder': f'Введите {field.label.lower()}'
            })

            
class InvitationForm(forms.Form):
    tags = forms.CharField(label='Ярлыки (через запятую)', required=False, 
                          widget=forms.TextInput(attrs={'placeholder': 'дизайн, верстка, копирайтинг...'}))
    
class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput)
    telegram_username = forms.CharField(label='Ник в Telegram (необязательно)', required=False)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'telegram_username']
    
    def clean_password2(self):
        password1 = self.cleaned_data.get("password1")
        password2 = self.cleaned_data.get("password2")
        if password1 and password2 and password1 != password2:
            raise forms.ValidationError("Пароли не совпадают")
        return password2

class UserProfileForm(forms.ModelForm):
    avatar = forms.ImageField(label='Аватар', required=False, widget=forms.FileInput)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'telegram_username', 'avatar', 'email']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}),
            'telegram_username': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '@username'}),
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
        }

class NavigationButtonForm(forms.ModelForm):
    class Meta:
        model = NavigationButton
        fields = ['title', 'url', 'icon', 'color', 'order', 'is_active']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Например: Google Диск'}),
            'url': forms.URLInput(attrs={'class': 'form-control', 'placeholder': 'https://drive.google.com/'}),
            'icon': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'например, 🚀 или 📁 или 🔗'}),
            'color': forms.TextInput(attrs={'class': 'form-control', 'type': 'color'}),
            'order': forms.NumberInput(attrs={'class': 'form-control'}),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        help_texts = {
            'icon': 'Можно использовать эмодзи или текст',
            'color': 'Выберите цвет кнопки',
        }