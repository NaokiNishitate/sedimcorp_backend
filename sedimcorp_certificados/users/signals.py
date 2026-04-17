"""
Señales para el módulo de usuarios.
Maneja eventos relacionados con usuarios: creación, actualización, etc.
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import User, UserActivity
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def handle_user_created(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un usuario.
    Envía email de bienvenida y registra la creación.
    """
    if created:
        # Registrar actividad
        UserActivity.objects.create(
            user=instance,
            activity_type='REGISTRATION',
            description='Usuario registrado en el sistema',
            ip_address=instance.last_ip or '0.0.0.0',
            user_agent='Sistema'
        )
        
        # Enviar email de bienvenida (si está configurado)
        try:
            subject = 'Bienvenido a SEDIMCORP'
            message = f'''
            Hola {instance.get_full_name()},
            
            Bienvenido a SEDIMCORP, tu plataforma de certificación digital.
            
            Tu cuenta ha sido creada exitosamente. Ya puedes acceder a nuestros cursos y certificaciones.
            
            Saludos,
            Equipo SEDIMCORP
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [instance.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Error enviando email de bienvenida a {instance.email}: {str(e)}")


@receiver(pre_save, sender=User)
def handle_user_pre_save(sender, instance, **kwargs):
    """
    Señal que se ejecuta antes de guardar un usuario.
    Actualiza campos calculados y valida datos.
    """
    if instance.pk:  # Si es una actualización
        try:
            old_instance = User.objects.get(pk=instance.pk)
            
            # Verificar si el email cambió
            if old_instance.email != instance.email:
                instance.email_verified = False
                
            # Registrar cambios importantes
            changes = []
            if old_instance.is_active != instance.is_active:
                changes.append(f"is_active: {old_instance.is_active} -> {instance.is_active}")
            if old_instance.user_type != instance.user_type:
                changes.append(f"user_type: {old_instance.user_type} -> {instance.user_type}")
                
            if changes and hasattr(instance, '_changes'):
                instance._changes = changes
                
        except User.DoesNotExist:
            pass


@receiver(post_save, sender=User)
def handle_user_updated(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de actualizar un usuario.
    Registra los cambios importantes.
    """
    if not created and hasattr(instance, '_changes'):
        for change in instance._changes:
            UserActivity.objects.create(
                user=instance,
                activity_type='PROFILE_UPDATE',
                description=f'Usuario actualizado: {change}',
                ip_address='0.0.0.0',
                user_agent='Sistema'
            )


@receiver(post_delete, sender=User)
def handle_user_deleted(sender, instance, **kwargs):
    """
    Señal que se ejecuta después de eliminar un usuario.
    Limpia datos relacionados y registra la eliminación.
    """
    logger.info(f"Usuario eliminado: {instance.email} - {instance.get_full_name()}")


@receiver(post_save, sender=UserActivity)
def handle_activity_created(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta al crear una actividad.
    Útil para notificaciones en tiempo real.
    """
    if created and instance.activity_type == 'LOGIN_FAILED':
        # Si hay muchos intentos fallidos, notificar al admin
        failed_attempts = UserActivity.objects.filter(
            user=instance.user,
            activity_type='LOGIN_FAILED',
            timestamp__gte=timezone.now() - timezone.timedelta(minutes=30)
        ).count()
        
        if failed_attempts >= 5:
            logger.warning(f"Múltiples intentos fallidos para usuario {instance.user.email}")
            # Aquí se podría enviar una notificación al administrador
