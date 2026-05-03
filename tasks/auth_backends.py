import uuid
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth import get_user_model
from django.conf import settings

User = get_user_model()

class AuthentikOIDCBackend(OIDCAuthenticationBackend):
    
    def create_user(self, claims):
        """
        Создает CustomUser с дефолтными значениями
        """
        email = claims.get('email', '')
        if not email:
            email = f"no-email-{uuid.uuid4().hex[:8]}@placeholder.local"
            
        username = self.generate_username(claims)
        
        # Создаем пользователя
        user = User.objects.create_user(
            username=username,
            email=email,
            password=None, # Пароль не нужен, вход через OIDC
            first_name=claims.get('given_name', ''),
            last_name=claims.get('family_name', ''),
        )
        
        # Явно проставляем дефолты для твоей модели, если они не заданы в models.py default=...
        user.role = 'technician' # Или какая роль по умолчанию для новых из LDAP
        user.balance = 0.00
        user.save(update_fields=['role', 'balance'])
        
        return user

    def filter_users_by_claims(self, claims):
        """
        Ищем по Email. Если нет - создаем нового.
        """
        email = claims.get('email')
        if not email:
            return self.UserModel.objects.none()
        
        try:
            return [self.UserModel.objects.get(email__iexact=email)]
        except self.UserModel.DoesNotExist:
            return self.UserModel.objects.none()

    def generate_username(self, claims):
        email = claims.get('email')
        if email:
            base = email.split('@')[0]
            # Проверка на уникальность username (вдруг такой уже есть локально)
            if not self.UserModel.objects.filter(username=base).exists():
                return base
            # Если занят, добавляем хвост
            return f"{base}_{uuid.uuid4().hex[:4]}"
        
        sub = claims.get('sub')
        if sub:
            return f"user_{sub[:10]}"
            
        return f"user_{uuid.uuid4().hex[:8]}"

    def update_user(self, user, claims):
        """
        Опционально: обновлять имя/фамилию при каждом входе, 
        если они изменились в LDAP/Authentik
        """
        user.first_name = claims.get('given_name', user.first_name)
        user.last_name = claims.get('family_name', user.last_name)
        user.save(update_fields=['first_name', 'last_name'])
        return user