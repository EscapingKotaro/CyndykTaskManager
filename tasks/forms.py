from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import *

class TaskForm(forms.ModelForm):
    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'due_date', 'payment_amount']
        widgets = {
            'due_date': forms.DateInput(attrs={'type': 'date'}),
            'description': forms.Textarea(attrs={'rows': 4}),
        }

class UserForm(forms.ModelForm):
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'last_name', 'email', 'password']
        widgets = {
            'password': forms.PasswordInput(),
        }

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
    email = forms.EmailField(label='Email сотрудника')
    tags = forms.CharField(label='Ярлыки (через запятую)', required=False, 
                          widget=forms.TextInput(attrs={'placeholder': 'дизайн, верстка, копирайтинг...'}))
    
class UserRegistrationForm(forms.ModelForm):
    password1 = forms.CharField(label='Пароль', widget=forms.PasswordInput)
    password2 = forms.CharField(label='Подтверждение пароля', widget=forms.PasswordInput)
    telegram_username = forms.CharField(label='Ник в Telegram (необязательно)', required=False)
    
    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'telegram_username', 'tags']
    
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