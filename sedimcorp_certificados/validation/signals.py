"""
Señales para el módulo de validación.
Maneja eventos relacionados con la validación de certificados.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone
from .models import ValidationAttempt, CertificateAccess
from certificates.models import Certificate
import logging

logger = logging.getLogger(__name__)


@receiver(post_save, sender=ValidationAttempt)
def handle_validation_attempt(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de un intento de validación.
    """
    if created:
        if instance.was_successful:
            logger.info(f"Validación exitosa: {instance.validation_hash[:16]}... desde IP {instance.ip_address}")
            
            # Actualizar estadísticas del certificado
            if instance.certificate:
                instance.certificate.register_validation(instance.ip_address)
        else:
            logger.warning(f"Validación fallida: {instance.validation_hash[:16]}... desde IP {instance.ip_address}")
            
            # Detectar posibles ataques
            recent_failures = ValidationAttempt.objects.filter(
                ip_address=instance.ip_address,
                was_successful=False,
                timestamp__gte=timezone.now() - timezone.timedelta(minutes=5)
            ).count()
            
            if recent_failures >= 10:
                logger.error(f"Posible ataque de fuerza bruta desde IP {instance.ip_address}")


@receiver(post_save, sender=CertificateAccess)
def handle_certificate_access(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta cuando se accede a un certificado.
    """
    if created:
        logger.info(f"Acceso a certificado: {instance.certificate.certificate_code} - {instance.get_access_type_display()}")
        
        # Actualizar contador de descargas si es necesario
        if instance.access_type == 'DOWNLOAD':
            instance.certificate.downloaded_count += 1
            instance.certificate.downloaded_at = timezone.now()
            instance.certificate.save(update_fields=['downloaded_count', 'downloaded_at'])


@receiver(post_save, sender=Certificate)
def handle_certificate_status_change(sender, instance, **kwargs):
    """
    Señal que detecta cambios de estado en certificados.
    """
    if instance.pk:
        try:
            old = Certificate.objects.get(pk=instance.pk)
            if old.status != instance.status and instance.status == 'VALIDATED':
                # Registrar validación exitosa
                ValidationAttempt.objects.create(
                    certificate=instance,
                    validation_hash=instance.validation_hash,
                    was_successful=True,
                    ip_address='0.0.0.0',
                    user_agent='Sistema'
                )
        except Certificate.DoesNotExist:
            pass
