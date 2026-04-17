"""
Modelos para la gestión de usuarios del sistema SEDIMCORP.
Define los diferentes tipos de usuarios, perfiles y configuraciones de acceso.
"""

from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.utils import timezone
from django.core.validators import RegexValidator, MinLengthValidator
import uuid

class UserManager(BaseUserManager):
    """
    Manager personalizado para el modelo User.
    Proporciona métodos para crear usuarios normales y superusuarios.
    """
    
    def create_user(self, email, password=None, **extra_fields):
        """
        Crea y guarda un usuario regular con el email y contraseña dados.
        
        Args:
            email (str): Correo electrónico del usuario
            password (str): Contraseña del usuario
            **extra_fields: Campos adicionales del modelo
        
        Returns:
            User: Instancia del usuario creado
        
        Raises:
            ValueError: Si el email no está proporcionado
        """
        if not email:
            raise ValueError('El email es obligatorio')
        
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        """
        Crea y guarda un superusuario con todos los permisos.
        
        Args:
            email (str): Correo electrónico del superusuario
            password (str): Contraseña del superusuario
            **extra_fields: Campos adicionales del modelo
        
        Returns:
            User: Instancia del superusuario creado
        """
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        extra_fields.setdefault('user_type', 'ADMIN')
        extra_fields.setdefault('email_verified', True)
        
        if extra_fields.get('is_staff') is not True:
            raise ValueError('El superusuario debe tener is_staff=True')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('El superusuario debe tener is_superuser=True')
        
        return self.create_user(email, password, **extra_fields)

class User(AbstractBaseUser, PermissionsMixin):
    """
    Modelo personalizado de usuario para el sistema SEDIMCORP.
    Extiende AbstractBaseUser y PermissionsMixin para mayor flexibilidad.
    """
    
    # Tipos de usuario
    USER_TYPE_CHOICES = [
        ('ADMIN', 'Administrador'),
        ('STAFF', 'Personal Administrativo'),
        ('INSTRUCTOR', 'Instructor'),
        ('PARTICIPANT', 'Participante'),
    ]
    
    # Género
    GENDER_CHOICES = [
        ('M', 'Masculino'),
        ('F', 'Femenino'),
        ('O', 'Otro'),
        ('N', 'Prefiero no decirlo'),
    ]
    
    # Tipo de documento
    DOCUMENT_TYPE_CHOICES = [
        ('DNI', 'DNI'),
        ('CE', 'Carnet de Extranjería'),
        ('PASSPORT', 'Pasaporte'),
        ('RUC', 'RUC'),
    ]
    
    # Validadores
    phone_regex = RegexValidator(
        regex=r'^9\d{8}$',
        message='El número de celular debe tener 9 dígitos y comenzar con 9'
    )
    
    document_regex = RegexValidator(
        regex=r'^\d{8}$|^\d{12}$|^[a-zA-Z0-9]{9,12}$',
        message='Formato de documento inválido'
    )
    
    # Campos de identificación
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    email = models.EmailField(
        unique=True,
        db_index=True,
        verbose_name='Correo electrónico'
    )
    
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='PARTICIPANT',
        verbose_name='Tipo de usuario'
    )
    
    # Datos personales
    first_name = models.CharField(
        max_length=100,
        verbose_name='Nombres'
    )
    
    last_name = models.CharField(
        max_length=100,
        verbose_name='Apellidos'
    )
    
    document_type = models.CharField(
        max_length=10,
        choices=DOCUMENT_TYPE_CHOICES,
        default='DNI',
        verbose_name='Tipo de documento'
    )
    
    document_number = models.CharField(
        max_length=20,
        validators=[document_regex],
        unique=True,
        verbose_name='Número de documento'
    )
    
    phone = models.CharField(
        max_length=9,
        validators=[phone_regex],
        verbose_name='Celular',
        blank=True,
        null=True
    )
    
    gender = models.CharField(
        max_length=2,
        choices=GENDER_CHOICES,
        verbose_name='Género',
        blank=True,
        null=True
    )
    
    birth_date = models.DateField(
        verbose_name='Fecha de nacimiento',
        blank=True,
        null=True
    )
    
    address = models.TextField(
        max_length=255,
        verbose_name='Dirección',
        blank=True,
        null=True
    )
    
    profile_image = models.ImageField(
        upload_to='users/profiles/',
        verbose_name='Foto de perfil',
        blank=True,
        null=True
    )
    
    # Campos profesionales (para instructores)
    professional_title = models.CharField(
        max_length=200,
        verbose_name='Título profesional',
        blank=True,
        null=True
    )
    
    specialization = models.CharField(
        max_length=200,
        verbose_name='Especialización',
        blank=True,
        null=True
    )
    
    biography = models.TextField(
        max_length=1000,
        verbose_name='Biografía profesional',
        blank=True,
        null=True
    )
    
    # Campos de control de acceso
    is_active = models.BooleanField(
        default=True,
        verbose_name='¿Está activo?'
    )
    
    is_staff = models.BooleanField(
        default=False,
        verbose_name='¿Es personal?'
    )
    
    email_verified = models.BooleanField(
        default=False,
        verbose_name='¿Email verificado?'
    )
    
    phone_verified = models.BooleanField(
        default=False,
        verbose_name='¿Teléfono verificado?'
    )
    
    # Campos de auditoría
    last_login = models.DateTimeField(
        verbose_name='Último acceso',
        blank=True,
        null=True
    )
    
    date_joined = models.DateTimeField(
        default=timezone.now,
        verbose_name='Fecha de registro'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    last_ip = models.GenericIPAddressField(
        verbose_name='Última IP',
        blank=True,
        null=True
    )
    
    # Campos de seguridad
    failed_login_attempts = models.IntegerField(
        default=0,
        verbose_name='Intentos fallidos'
    )
    
    locked_until = models.DateTimeField(
        verbose_name='Bloqueado hasta',
        blank=True,
        null=True
    )
    
    # Notificaciones y preferencias
    receive_notifications = models.BooleanField(
        default=True,
        verbose_name='Recibir notificaciones'
    )
    
    receive_promotions = models.BooleanField(
        default=False,
        verbose_name='Recibir promociones'
    )
    
    language_preference = models.CharField(
        max_length=10,
        default='es',
        verbose_name='Idioma preferido'
    )
    
    # Relaciones con otras apps se definen como Generic Relations o ForeignKeys
    # que se implementarán en otros módulos
    
    objects = UserManager()
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name', 'document_number']
    
    class Meta:
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['-date_joined']
        indexes = [
            models.Index(fields=['email', 'document_number']),
            models.Index(fields=['user_type', 'is_active']),
        ]
    
    def __str__(self):
        """Representación en string del usuario."""
        return f"{self.get_full_name()} - {self.email}"
    
    def get_full_name(self):
        """Retorna el nombre completo del usuario."""
        return f"{self.first_name} {self.last_name}".strip()
    
    def get_short_name(self):
        """Retorna el nombre corto del usuario."""
        return self.first_name
    
    def is_locked(self):
        """Verifica si la cuenta está bloqueada."""
        if self.locked_until and timezone.now() < self.locked_until:
            return True
        return False
    
    def increment_failed_attempts(self):
        """Incrementa el contador de intentos fallidos y bloquea si es necesario."""
        self.failed_login_attempts += 1
        if self.failed_login_attempts >= 5:
            self.locked_until = timezone.now() + timezone.timedelta(minutes=30)
        self.save(update_fields=['failed_login_attempts', 'locked_until'])
    
    def reset_failed_attempts(self):
        """Resetea el contador de intentos fallidos."""
        self.failed_login_attempts = 0
        self.locked_until = None
        self.save(update_fields=['failed_login_attempts', 'locked_until'])


class PasswordReset(models.Model):
    """
    Modelo para gestionar solicitudes de restablecimiento de contraseña.
    """
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='password_resets',
        verbose_name='Usuario'
    )
    
    token = models.CharField(
        max_length=255,
        unique=True,
        verbose_name='Token'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    expires_at = models.DateTimeField(
        verbose_name='Fecha de expiración'
    )
    
    is_used = models.BooleanField(
        default=False,
        verbose_name='¿Fue usado?'
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name='Dirección IP',
        blank=True,
        null=True
    )
    
    user_agent = models.TextField(
        verbose_name='User Agent',
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = 'Restablecimiento de contraseña'
        verbose_name_plural = 'Restablecimientos de contraseña'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Reset para {self.user.email} - {self.created_at}"
    
    def is_valid(self):
        """Verifica si el token es válido y no ha expirado."""
        return not self.is_used and timezone.now() < self.expires_at


class UserActivity(models.Model):
    """
    Modelo para registrar la actividad de los usuarios en el sistema.
    """
    
    ACTIVITY_TYPES = [
        ('LOGIN', 'Inicio de sesión'),
        ('LOGOUT', 'Cierre de sesión'),
        ('PASSWORD_CHANGE', 'Cambio de contraseña'),
        ('PROFILE_UPDATE', 'Actualización de perfil'),
        ('CERTIFICATE_VIEW', 'Visualización de certificado'),
        ('CERTIFICATE_DOWNLOAD', 'Descarga de certificado'),
        ('PAYMENT', 'Pago realizado'),
        ('COURSE_ENROLL', 'Inscripción a curso'),
    ]
    
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='activities',
        verbose_name='Usuario'
    )
    
    activity_type = models.CharField(
        max_length=50,
        choices=ACTIVITY_TYPES,
        verbose_name='Tipo de actividad'
    )
    
    description = models.CharField(
        max_length=255,
        verbose_name='Descripción',
        blank=True,
        null=True
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name='Dirección IP'
    )
    
    user_agent = models.TextField(
        verbose_name='User Agent'
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y hora'
    )
    
    metadata = models.JSONField(
        verbose_name='Metadatos adicionales',
        default=dict,
        blank=True
    )
    
    class Meta:
        verbose_name = 'Actividad de usuario'
        verbose_name_plural = 'Actividades de usuarios'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['user', '-timestamp']),
            models.Index(fields=['activity_type']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.get_activity_type_display()} - {self.timestamp}"
