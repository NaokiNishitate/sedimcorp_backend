"""
Vistas para el módulo de usuarios.
Manejan las peticiones HTTP relacionadas con usuarios, autenticación y perfiles.
"""

from rest_framework import generics, permissions, status, views
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.utils import timezone
from django.core.mail import send_mail
from django.conf import settings
from django.db.models import Q
import secrets
import json

from .models import User, PasswordReset, UserActivity
from .serializers import (
    UserSerializer, UserRegistrationSerializer, UserListSerializer,
    ChangePasswordSerializer, PasswordResetRequestSerializer,
    PasswordResetConfirmSerializer, UserActivitySerializer
)
from .permissions import IsAdmin, IsOwnerOrAdmin, IsStaffOrAdmin
from utils.helpers import generate_token, send_email_template


class RegisterView(generics.CreateAPIView):
    """
    Vista para registro de nuevos usuarios.
    Permite crear una cuenta de participante o instructor.
    """
    
    serializer_class = UserRegistrationSerializer
    permission_classes = [permissions.AllowAny]
    
    def post(self, request, *args, **kwargs):
        """Registra un nuevo usuario y retorna sus datos básicos."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        # Generar tokens JWT
        refresh = RefreshToken.for_user(user)
        
        # Preparar respuesta
        user_data = UserSerializer(user, context={'request': request}).data
        
        return Response({
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            },
            'message': 'Usuario registrado exitosamente'
        }, status=status.HTTP_201_CREATED)


class LoginView(views.APIView):
    """
    Vista para inicio de sesión.
    Autentica usuarios y retorna tokens JWT.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Inicia sesión con email y contraseña."""
        email = request.data.get('email')
        password = request.data.get('password')
        
        if not email or not password:
            return Response({
                'error': 'Debe proporcionar email y contraseña'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Autenticar usuario
        user = authenticate(request, username=email, password=password)
        
        if not user:
            # Registrar intento fallido
            try:
                user_obj = User.objects.get(email=email)
                user_obj.increment_failed_attempts()
                
                # Registrar actividad
                UserActivity.objects.create(
                    user=user_obj,
                    activity_type='LOGIN_FAILED',
                    description='Intento de inicio de sesión fallido',
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', '')
                )
            except User.DoesNotExist:
                pass
            
            return Response({
                'error': 'Credenciales inválidas'
            }, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verificar si la cuenta está bloqueada
        if user.is_locked():
            return Response({
                'error': f'Cuenta bloqueada. Intente nuevamente después de {user.locked_until.strftime("%H:%M")}'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Verificar si el usuario está activo
        if not user.is_active:
            return Response({
                'error': 'Cuenta desactivada. Contacte al administrador'
            }, status=status.HTTP_403_FORBIDDEN)
        
        # Resetear intentos fallidos
        user.reset_failed_attempts()
        
        # Actualizar último login e IP
        user.last_login = timezone.now()
        user.last_ip = self._get_client_ip(request)
        user.save(update_fields=['last_login', 'last_ip'])
        
        # Registrar actividad
        UserActivity.objects.create(
            user=user,
            activity_type='LOGIN',
            description='Inicio de sesión exitoso',
            ip_address=user.last_ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Generar tokens
        refresh = RefreshToken.for_user(user)
        
        # Serializar usuario
        user_data = UserSerializer(user, context={'request': request}).data
        
        return Response({
            'user': user_data,
            'tokens': {
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }
        }, status=status.HTTP_200_OK)
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class LogoutView(views.APIView):
    """
    Vista para cerrar sesión.
    Invalida el token de refresco.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Cierra la sesión del usuario."""
        try:
            refresh_token = request.data.get('refresh')
            if refresh_token:
                token = RefreshToken(refresh_token)
                token.blacklist()
            
            # Registrar actividad
            UserActivity.objects.create(
                user=request.user,
                activity_type='LOGOUT',
                description='Cierre de sesión',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Sesión cerrada exitosamente'
            }, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({
                'error': 'Error al cerrar sesión'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Vista para ver, actualizar o eliminar un usuario específico.
    Solo el propio usuario o administradores pueden acceder.
    """
    
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsOwnerOrAdmin]
    
    def perform_destroy(self, instance):
        """En lugar de eliminar, desactiva el usuario."""
        instance.is_active = False
        instance.save()
        
        # Registrar actividad
        UserActivity.objects.create(
            user=instance,
            activity_type='ACCOUNT_DEACTIVATED',
            description='Cuenta desactivada',
            ip_address=self._get_client_ip(self.request),
            user_agent=self.request.META.get('HTTP_USER_AGENT', '')
        )
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserListView(generics.ListAPIView):
    """
    Vista para listar usuarios con filtros.
    Solo accesible para administradores y staff.
    """
    
    queryset = User.objects.filter(is_active=True)
    serializer_class = UserListSerializer
    permission_classes = [IsStaffOrAdmin]
    pagination_class = None
    filterset_fields = ['user_type', 'is_active', 'email_verified']
    search_fields = ['email', 'first_name', 'last_name', 'document_number']
    ordering_fields = ['date_joined', 'last_login', 'email']
    
    def get_queryset(self):
        """Aplica filtros adicionales según parámetros."""
        queryset = super().get_queryset()
        
        # Filtro por búsqueda en nombre completo
        search = self.request.query_params.get('search', None)
        if search:
            queryset = queryset.filter(
                Q(first_name__icontains=search) |
                Q(last_name__icontains=search) |
                Q(email__icontains=search) |
                Q(document_number__icontains=search)
            )
        
        return queryset


class ChangePasswordView(views.APIView):
    """
    Vista para cambiar la contraseña del usuario autenticado.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def post(self, request):
        """Cambia la contraseña del usuario."""
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            user = request.user
            user.set_password(serializer.validated_data['new_password'])
            user.save()
            
            # Registrar actividad
            UserActivity.objects.create(
                user=user,
                activity_type='PASSWORD_CHANGE',
                description='Cambio de contraseña',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Contraseña actualizada exitosamente'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordResetRequestView(views.APIView):
    """
    Vista para solicitar restablecimiento de contraseña.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Envía email con token para restablecer contraseña."""
        serializer = PasswordResetRequestSerializer(data=request.data)
        
        if serializer.is_valid():
            email = serializer.validated_data['email']
            user = serializer.context['user']
            
            # Generar token único
            token = secrets.token_urlsafe(48)
            
            # Crear registro de reset
            reset_request = PasswordReset.objects.create(
                user=user,
                token=token,
                expires_at=timezone.now() + timezone.timedelta(hours=24),
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Enviar email
            reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
            
            # Aquí se implementaría el envío de email
            # send_email_template(
            #     subject='Restablecer tu contraseña',
            #     template='emails/password_reset.html',
            #     context={'user': user, 'reset_url': reset_url},
            #     to=[user.email]
            # )
            
            return Response({
                'message': 'Si el email está registrado, recibirás instrucciones'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PasswordResetConfirmView(views.APIView):
    """
    Vista para confirmar restablecimiento de contraseña.
    """
    
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        """Restablece la contraseña usando el token."""
        serializer = PasswordResetConfirmSerializer(data=request.data)
        
        if serializer.is_valid():
            reset_request = serializer.context['reset_request']
            new_password = serializer.validated_data['new_password']
            
            # Actualizar contraseña
            user = reset_request.user
            user.set_password(new_password)
            user.save()
            
            # Marcar token como usado
            reset_request.is_used = True
            reset_request.save()
            
            # Registrar actividad
            UserActivity.objects.create(
                user=user,
                activity_type='PASSWORD_RESET',
                description='Contraseña restablecida',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            return Response({
                'message': 'Contraseña restablecida exitosamente'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserActivityView(generics.ListAPIView):
    """
    Vista para listar actividades de un usuario específico.
    """
    
    serializer_class = UserActivitySerializer
    permission_classes = [IsOwnerOrAdmin]
    
    def get_queryset(self):
        """Retorna las actividades del usuario."""
        user_id = self.kwargs.get('pk')
        return UserActivity.objects.filter(user_id=user_id).select_related('user')


class CurrentUserView(views.APIView):
    """
    Vista para obtener los datos del usuario autenticado.
    """
    
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Retorna los datos del usuario actual."""
        serializer = UserSerializer(request.user, context={'request': request})
        return Response(serializer.data, status=status.HTTP_200_OK)
