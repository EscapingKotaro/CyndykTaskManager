import json
from mozilla_django_oidc.auth import OIDCAuthenticationBackend
from django.contrib.auth import get_user_model
import uuid
import logging

logger = logging.getLogger(__name__)
User = get_user_model()

class AuthentikOIDCBackend(OIDCAuthenticationBackend):
    
    def create_user(self, claims):
        username = self.generate_username(claims)
        email = claims.get('email', '')
        
        if not email:
            email = f"no-email-{uuid.uuid4().hex[:8]}@placeholder.local"
            
        user = User.objects.create_user(
            username=username,
            email=email,
            password=None,
            first_name=claims.get('given_name', ''),
            last_name=claims.get('family_name', ''),
        )
        
        self._update_permissions(user, claims)
        logger.info(f"Created new user: {username}")
        return user

    def update_user(self, user, claims):



        updated = False
        
        # 1. Логирование того, что реально пришло (Смотри в консоль сервера!)
        # ВНИМАНИЕ: В продакшене лучше логировать только ключи, а не весь токен
        logger.warning(f"OIDC Claims for {user.username}: {list(claims.keys())}")
        logger.warning(f"OIDC Groups/Roles found: {claims.get('groups', claims.get('roles', 'NOT FOUND'))}")

        # 2. Обновление личных данных
        new_first_name = claims.get('given_name', '')
        new_last_name = claims.get('family_name', '')
        new_email = claims.get('email', '')

        if user.first_name != new_first_name:
            user.first_name = new_first_name
            updated = True
            
        if user.last_name != new_last_name:
            user.last_name = new_last_name
            updated = True
            
        if new_email and user.email != new_email:
            user.email = new_email
            updated = True
            
        # 3. Обновление прав
        if self._update_permissions(user, claims):
            updated = True

        if updated:
            user.save()
            logger.info(f"Updated user: {user.username}")
            
        return user

    def _update_permissions(self, user, claims):
        changed = False
        
        # Пытаемся найти группы в разных возможных полях
        # Authentik может класть их в 'groups', 'roles', или даже в кастомное поле
        groups = claims.get('user', [])
        if not groups:
            groups = claims.get('roles', [])
        
        # Если это строка, превращаем в список
        if isinstance(groups, str):
            try:
                groups = json.loads(groups) # Иногда приходит JSON строкой
            except:
                groups = [groups]
        
        # Приводим к нижнему регистру для надежности
        groups_lower = [g.lower() if isinstance(g, str) else g for g in groups]

        # ЛОГИКА НАЗНАЧЕНИЯ ПРАВ
        # mastern - админ, manager - редактор, operator - читатель
        
        is_master = 'master' in groups_lower or 'admin' in groups_lower
        is_manager = 'manager' in groups_lower or 'editor' in groups_lower
        
        # Если Мастер -> is_staff = True (доступ в админку/CRM)
        if is_master:
            if not user.is_staff:
                user.is_staff = True
                changed = True
                logger.info(f"Granted staff status to {user.username} (Role: Master)")
        else:
            # Если нужен строгий контроль: убираем стафф, если не мастер
            # Но осторожно, чтобы не выгнать себя
            if user.is_staff and not is_manager: 
                # Оставляем стафф менеджерам, убираем остальным? 
                # Реши сам, кому нужен доступ в CRM. 
                # Допустим, CRM доступна только мастерам и менеджерам.
                pass 

        # Можно также использовать is_superuser для полных прав
        if is_master:
            if not user.is_superuser:
                user.is_superuser = True
                changed = True

        return changed

    def filter_users_by_claims(self, claims):
        email = claims.get('email')
        if email:
            try:
                return [User.objects.get(email__iexact=email)]
            except User.DoesNotExist:
                pass
        
        username = claims.get('preferred_username')
        if username:
            try:
                return [User.objects.get(username=username)]
            except User.DoesNotExist:
                pass

        return User.objects.none()

    def generate_username(self, claims):
        username = claims.get('preferred_username')
        if username:
            if not User.objects.filter(username=username).exists():
                return username
                
        email = claims.get('email')
        if email:
            base = email.split('@')[0]
            base = "".join([c for c in base if c.isalnum() or c == '_'])
            if not User.objects.filter(username=base).exists():
                return base
        
        sub = claims.get('sub')
        if sub:
            safe_sub = sub.replace('-', '_')[:30]
            if not User.objects.filter(username=safe_sub).exists():
                return f"user_{safe_sub}"
            
        return f"user_{uuid.uuid4().hex[:8]}"