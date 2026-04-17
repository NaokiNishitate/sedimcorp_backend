"""
Serializadores para el módulo de usuarios.
Manejan la conversión de objetos User a JSON y viceversa, con validaciones.
"""

from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from django.core import exceptions as django_exceptions
from django.utils import timezone
from .models import User, PasswordReset, UserActivity
import re


class UserRegistrationSerializer(serializers.ModelSerializer):
    """
    Serializador para el registro de nuevos usuarios.
    Incluye validación de contraseña y creación de usuario.
    """
    
    password = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password],
        error_messages={
            'required': 'La contraseña es obligatoria',
            'blank': 'La contraseña no puede estar vacía'
        }
    )
    
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'},
        error_messages={
            'required': 'Debe confirmar la contraseña',
            'blank': 'La confirmación no puede estar vacía'
        }
    )
    
    class Meta:
        model = User
        fields = [
            'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'document_type',
            'document_number', 'phone', 'gender',
            'birth_date', 'address', 'user_type',
            'professional_title'
        ]
        extra_kwargs = {
            'first_name': {'required': True},
            'last_name': {'required': True},
            'document_number': {'required': True},
            'email': {'required': True},
        }
    
    def validate_email(self, value):
        """Valida que el email tenga un formato correcto."""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Este email ya está registrado')
        
        # Validar formato de email
        email_regex = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        if not re.match(email_regex, value):
            raise serializers.ValidationError('Formato de email inválido')
        
        return value
    
    def validate_document_number(self, value):
        """Valida que el número de documento sea único."""
        if User.objects.filter(document_number=value).exists():
            raise serializers.ValidationError('Este número de documento ya está registrado')
        return value
    
    def validate_phone(self, value):
        """Valida el formato del teléfono si se proporciona."""
        if value:
            phone_regex = r'^9\d{8}$'
            if not re.match(phone_regex, value):
                raise serializers.ValidationError('El celular debe tener 9 dígitos y comenzar con 9')
        return value
    
    def validate(self, attrs):
        """Validaciones cruzadas entre campos."""
        # Verificar que las contraseñas coincidan
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError({
                'password_confirm': 'Las contraseñas no coinciden'
            })
        
        # Eliminar password_confirm ya que no se guarda en el modelo
        attrs.pop('password_confirm', None)
        
        # Validar que si es instructor, tenga título profesional
        if attrs.get('user_type') == 'INSTRUCTOR' and not attrs.get('professional_title'):
            raise serializers.ValidationError({
                'professional_title': 'Los instructores deben tener un título profesional'
            })
        
        return attrs
    
    def create(self, validated_data):
        """Crea un nuevo usuario con la contraseña encriptada."""
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            **{k: v for k, v in validated_data.items() if k not in ['email', 'password']}
        )
        
        # Registrar actividad
        request = self.context.get('request')
        if request:
            UserActivity.objects.create(
                user=user,
                activity_type='REGISTRATION',
                description='Registro de nuevo usuario',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return user
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserSerializer(serializers.ModelSerializer):
    """
    Serializador principal para usuarios.
    Incluye todos los campos del modelo.
    """
    
    full_name = serializers.SerializerMethodField()
    age = serializers.SerializerMethodField()
    is_profile_complete = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'user_type', 'first_name', 'last_name',
            'full_name', 'document_type', 'document_number', 'phone',
            'gender', 'birth_date', 'age', 'address', 'profile_image',
            'professional_title', 'specialization', 'biography',
            'is_active', 'email_verified', 'phone_verified',
            'date_joined', 'last_login', 'is_profile_complete',
            'receive_notifications', 'receive_promotions',
            'language_preference'
        ]
        read_only_fields = [
            'id', 'email_verified', 'phone_verified',
            'date_joined', 'last_login', 'is_active'
        ]
    
    def get_full_name(self, obj):
        """Retorna el nombre completo del usuario."""
        return obj.get_full_name()
    
    def get_age(self, obj):
        """Calcula la edad del usuario basado en su fecha de nacimiento."""
        if obj.birth_date:
            today = timezone.now().date()
            age = today.year - obj.birth_date.year
            if today.month < obj.birth_date.month or \
               (today.month == obj.birth_date.month and today.day < obj.birth_date.day):
                age -= 1
            return age
        return None
    
    def get_is_profile_complete(self, obj):
        """Verifica si el perfil está completo."""
        required_fields = ['first_name', 'last_name', 'document_number', 'phone']
        return all(getattr(obj, field) for field in required_fields)
    
    def update(self, instance, validated_data):
        """Actualización de usuario con registro de actividad."""
        # Registrar actividad antes de actualizar
        request = self.context.get('request')
        
        # Actualizar campos
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        instance.save()
        
        # Registrar actividad
        if request and request.user == instance:
            UserActivity.objects.create(
                user=instance,
                activity_type='PROFILE_UPDATE',
                description='Actualización de perfil',
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
        
        return instance
    
    def _get_client_ip(self, request):
        """Obtiene la IP real del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class UserListSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para listados de usuarios.
    """
    
    full_name = serializers.SerializerMethodField()
    
    class Meta:
        model = User
        fields = [
            'id', 'email', 'full_name', 'user_type',
            'document_number', 'is_active', 'date_joined'
        ]
    
    def get_full_name(self, obj):
        return obj.get_full_name()


class ChangePasswordSerializer(serializers.Serializer):
    """
    Serializador para cambio de contraseña.
    """
    
    old_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        error_messages={'required': 'La contraseña actual es obligatoria'}
    )
    
    new_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password],
        error_messages={'required': 'La nueva contraseña es obligatoria'}
    )
    
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        error_messages={'required': 'Debe confirmar la nueva contraseña'}
    )
    
    def validate_old_password(self, value):
        """Valida que la contraseña actual sea correcta."""
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('La contraseña actual es incorrecta')
        return value
    
    def validate(self, attrs):
        """Valida que las nuevas contraseñas coincidan."""
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas no coinciden'
            })
        
        # Verificar que la nueva contraseña no sea igual a la anterior
        if attrs['old_password'] == attrs['new_password']:
            raise serializers.ValidationError({
                'new_password': 'La nueva contraseña debe ser diferente a la actual'
            })
        
        return attrs


class PasswordResetRequestSerializer(serializers.Serializer):
    """
    Serializador para solicitar restablecimiento de contraseña.
    """
    
    email = serializers.EmailField(
        required=True,
        error_messages={'required': 'El email es obligatorio'}
    )
    
    def validate_email(self, value):
        """Valida que el email exista en el sistema."""
        try:
            user = User.objects.get(email=value, is_active=True)
        except User.DoesNotExist:
            # Por seguridad, no revelamos si el email existe o no
            raise serializers.ValidationError(
                'Si el email está registrado, recibirás instrucciones'
            )
        
        # Guardar el usuario en el contexto para usarlo después
        self.context['user'] = user
        return value


class PasswordResetConfirmSerializer(serializers.Serializer):
    """
    Serializador para confirmar restablecimiento de contraseña.
    """
    
    token = serializers.CharField(
        required=True,
        error_messages={'required': 'El token es obligatorio'}
    )
    
    new_password = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        validators=[validate_password],
        error_messages={'required': 'La nueva contraseña es obligatoria'}
    )
    
    new_password_confirm = serializers.CharField(
        required=True,
        style={'input_type': 'password'},
        error_messages={'required': 'Debe confirmar la nueva contraseña'}
    )
    
    def validate(self, attrs):
        """Valida el token y las contraseñas."""
        # Validar que las contraseñas coincidan
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({
                'new_password_confirm': 'Las contraseñas no coinciden'
            })
        
        # Buscar el token
        try:
            reset_request = PasswordReset.objects.select_related('user').get(
                token=attrs['token'],
                is_used=False,
                expires_at__gt=timezone.now()
            )
        except PasswordReset.DoesNotExist:
            raise serializers.ValidationError({
                'token': 'El token es inválido o ha expirado'
            })
        
        # Guardar el reset request en el contexto
        self.context['reset_request'] = reset_request
        
        return attrs


class UserActivitySerializer(serializers.ModelSerializer):
    """
    Serializador para actividades de usuario.
    """
    
    activity_type_display = serializers.CharField(
        source='get_activity_type_display',
        read_only=True
    )
    
    class Meta:
        model = UserActivity
        fields = [
            'id', 'activity_type', 'activity_type_display',
            'description', 'ip_address', 'timestamp', 'metadata'
        ]
        read_only_fields = fields
