from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from django.contrib.auth import authenticate
from django.middleware.csrf import get_token
from django.apps import apps

@api_view(['POST'])
@permission_classes([AllowAny])
def verify_user(request):
    username = request.data.get('username')
    password = request.data.get('password')
    
    # Получаем кастомную модель пользователя
    CustomUser = apps.get_model('users', 'CustomUser')
    
    user = authenticate(username=username, password=password)
    
    if user is not None and isinstance(user, CustomUser):
        return Response({
            'success': True,
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'balance': str(user.balance),
                'telegram_username': user.telegram_username,
                'is_staff': user.is_staff,
                'is_active': user.is_active,
                'date_joined': user.date_joined.isoformat(),
            },
            'csrf_token': get_token(request)
        })
    return Response({'success': False, 'error': 'Invalid credentials'})