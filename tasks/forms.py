from django import forms
from django.contrib.auth.forms import PasswordChangeForm
from .models import *
import re

class UserEditForm(forms.ModelForm):
    # Поле для смены пароля (необязательное при редактировании)
    new_password = forms.CharField(
        label='Новый пароль',
        required=False,
        widget=forms.PasswordInput(attrs={
            'class': 'form-control',
            'placeholder': 'Оставьте пустым, если не меняете пароль'
        }),
        help_text='Минимум 8 символов'
    )
    
    telegram_username = forms.CharField(
        label='Ник в Telegram',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '@username'
        })
    )
    
    tags = forms.CharField(
        label='Теги и навыки',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'дизайн, верстка, копирайтинг...'
        })
    )

    class Meta:
        model = CustomUser
        fields = ['username', 'first_name', 'email', 'telegram_username', 'tags', 
                 'role', 'manager', 'balance', 'new_password']
        widgets = {
            'username': forms.TextInput(attrs={'class': 'form-control'}),
            'first_name': forms.TextInput(attrs={'class': 'form-control'}), 
            'email': forms.EmailInput(attrs={'class': 'form-control'}),
            'balance': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'role': forms.Select(attrs={'class': 'form-control'}),
            'manager': forms.Select(attrs={'class': 'form-control'}),
        }

    def __init__(self, *args, **kwargs):
        self.editing_user = kwargs.pop('editing_user', None)  # Кто редактирует
        super().__init__(*args, **kwargs)
        
        # Если редактируем существующего пользователя, убираем поле пароля из обязательных
        if self.instance.pk:
            self.fields['new_password'].required = False
        
        # Ограничиваем выбор менеджера только boss'ами
        if 'manager' in self.fields:
            self.fields['manager'].queryset = CustomUser.objects.filter(role='boss')
            self.fields['manager'].required = False
            self.fields['manager'].empty_label = "Не назначен"
        
        # Настраиваем доступ к полям в зависимости от роли редактирующего
        if self.editing_user:
            if self.editing_user.role == 'manager':
                # Менеджер не может менять роль и менеджера
                if 'role' in self.fields:
                    del self.fields['role']
                if 'manager' in self.fields:
                    del self.fields['manager']
            
            # Никто не может менять свою собственную роль
            if self.instance == self.editing_user and 'role' in self.fields:
                del self.fields['role']

    def clean_telegram_username(self):
        telegram_username = self.cleaned_data.get('telegram_username', '').strip()
        if telegram_username:
            if telegram_username.startswith('@'):
                telegram_username = telegram_username[1:]
            if not re.match(r'^[a-zA-Z0-9_]{5,32}$', telegram_username):
                raise forms.ValidationError('Некорректный формат Telegram username')
        return telegram_username

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '').strip()
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if len(tags_list) > 10:
                raise forms.ValidationError('Не более 10 тегов')
            return ', '.join(tags_list)
        return tags

    def clean_new_password(self):
        password = self.cleaned_data.get('new_password')
        if password and len(password) < 8:
            raise forms.ValidationError('Пароль должен содержать минимум 8 символов')
        return password

    def clean(self):
        cleaned_data = super().clean()
        editing_user = self.editing_user
        target_user = self.instance
        
        # Проверяем права на редактирование роли
        if 'role' in cleaned_data and editing_user:
            new_role = cleaned_data.get('role')
            if editing_user.role != 'boss':
                raise forms.ValidationError('Только босс может менять роли пользователей')
            
            # Нельзя понизить босса
            if target_user.role == 'boss' and new_role != 'boss':
                raise forms.ValidationError('Нельзя изменить роль босса')

    def save(self, commit=True):
        user = super().save(commit=False)
        
        # Обновляем пароль если указан новый
        new_password = self.cleaned_data.get('new_password')
        if new_password:
            user.set_password(new_password)
        
        if commit:
            user.save()
        return user
# forms.py
class TaskForm(forms.ModelForm):
    due_date = forms.DateField(
        label='📅 Дата выполнения',
        widget=forms.DateInput(attrs={
            'type': 'date',
            'class': 'form-control',
            'placeholder': 'Выберите дату'
        })
    )
    
    payment_amount = forms.DecimalField(
        label='💰 Сумма к оплате (руб.)',
        max_digits=10,
        decimal_places=2,
        initial=0,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': '0.00',
            'step': '0.01',
            'min': '0'
        })
    )
    
    tags = forms.CharField(
        label='🏷️ Ярлыки задачи',
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'срочно, важное, дизайн...'
        }),
        help_text='Укажите через запятую'
    )

    class Meta:
        model = Task
        fields = ['title', 'description', 'assigned_to', 'due_date', 'payment_amount', 'tags', 'controlled_by']
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Введите название задачи'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Подробное описание задачи...'
            }),
            'assigned_to': forms.Select(attrs={'class': 'form-control'}),
            'controlled_by': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def __init__(self, *args, **kwargs):
        self.request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        
        if self.request and self.request.user.is_authenticated:
            user = self.request.user
            
            # Фильтруем исполнителей (только не staff)
            if user.role == 'boss':
                users = user.get_team_users().filter(is_staff=False, is_active=True)
            elif user.role == 'manager':
                users = user.get_team_users().filter(is_staff=False, is_active=True)
            else:
                users = CustomUser.objects.filter(id=user.id, is_staff=False, is_active=True)
            
            self.fields['assigned_to'].queryset = users

            # Фильтруем контролеров (только boss и manager)
            self.fields['controlled_by'].queryset = user.get_team_leadership()
            
            # Если пользователь не boss/manager - устанавливаем контролера по умолчанию
            if user.role not in ['boss']:
                boss = user.manager
                if boss:
                    self.fields['controlled_by'].initial = boss
            
            # Если пользователь boss/manager - может оставить поле пустым
            #if user.role in ['boss', 'manager']:
            #    self.fields['controlled_by'].required = False
            #    self.fields['controlled_by'].empty_label = "Не назначен"

    def clean_tags(self):
        tags = self.cleaned_data.get('tags', '').strip()
        if tags:
            tags_list = [tag.strip() for tag in tags.split(',') if tag.strip()]
            if len(tags_list) > 10:
                raise forms.ValidationError('Не более 10 тегов')
            return ', '.join(tags_list)
        return tags

    def clean_payment_amount(self):
        payment_amount = self.cleaned_data.get('payment_amount')
        if payment_amount < 0:
            raise forms.ValidationError('Сумма не может быть отрицательной')
        return payment_amount
            

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
        fields = ['username', 'first_name', 'email','role', 'telegram_username', 'tags', 'password']
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
    def __init__(self, *args, **kwargs):
        self.editing_user = kwargs.pop('editing_user', None)  # Кто редактирует
        super().__init__(*args, **kwargs)
        
        # Если редактируем существующего пользователя, убираем поле пароля из обязательных
        if self.instance.pk:
            self.fields['new_password'].required = False
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
    def clean(self):
        cleaned_data = super().clean()
        editing_user = self.editing_user
        target_user = self.instance
        
        # Проверяем права на редактирование роли
        if 'role' in cleaned_data and editing_user:
            new_role = cleaned_data.get('role')
            if editing_user.role != 'boss':
                raise forms.ValidationError('Только босс может менять роли пользователей')
            
            # Нельзя понизить босса
            if target_user.role == 'boss' and new_role != 'boss':
                raise forms.ValidationError('Нельзя изменить роль босса')
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

# forms.py
from django import forms

class TaskFilterForm(forms.Form):
    user_filter = forms.ModelChoiceField(
        queryset=CustomUser.objects.none(),
        required=False,
        empty_label="Все сотрудники",
        label="Фильтр по сотруднику"
    )
    
    def __init__(self, *args, **kwargs):
        request = kwargs.pop('request', None)
        super().__init__(*args, **kwargs)
        if request and request.user.is_authenticated:
            self.fields['user_filter'].queryset = request.user.get_team_users()