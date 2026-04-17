"""
Señales para el módulo de certificados.
Maneja eventos relacionados con la generación y validación de certificados.
"""

from django.db.models.signals import post_save, pre_save, post_delete
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Certificate, CertificateTemplate, CertificateLog
from events.models import Enrollment
from users.models import UserActivity
import logging
import os

logger = logging.getLogger(__name__)


@receiver(post_save, sender=Enrollment)
def handle_enrollment_completed(sender, instance, created, **kwargs):
    """
    Señal que se activa cuando una inscripción se completa.
    Genera automáticamente el certificado si está configurado.
    """
    if not created and instance.status == 'COMPLETED' and instance.is_approved:
        # Verificar si ya tiene certificado
        if not hasattr(instance, 'certificate') and instance.course.is_certifiable:
            from .generators import CertificateGenerator
            
            try:
                generator = CertificateGenerator(instance)
                # El certificado se genera automáticamente con el sistema
                certificate = generator.create_certificate(None)  # None = sistema
                
                logger.info(f"Certificado generado automáticamente: {certificate.certificate_code}")
                
                # Enviar email al participante
                try:
                    subject = f'Certificado disponible - {instance.course.title}'
                    message = f'''
                    Hola {instance.participant.get_full_name()},
                    
                    ¡Felicitaciones! Has completado exitosamente el curso: {instance.course.title}
                    
                    Tu certificado digital ya está disponible en nuestra plataforma.
                    
                    Puedes descargarlo desde: {settings.FRONTEND_URL}/certificates/{certificate.certificate_code}
                    
                    Código de validación: {certificate.validation_hash}
                    
                    Saludos,
                    Equipo SEDIMCORP
                    '''
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.participant.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.error(f"Error enviando email de certificado: {str(e)}")
                    
            except Exception as e:
                logger.error(f"Error generando certificado automático: {str(e)}")


@receiver(pre_save, sender=Certificate)
def handle_certificate_pre_save(sender, instance, **kwargs):
    """
    Señal que se ejecuta antes de guardar un certificado.
    Genera hash de validación si no existe.
    """
    if not instance.validation_hash:
        import hashlib
        import uuid
        
        base = f"{instance.enrollment.id}{instance.participant_document}{uuid.uuid4()}"
        instance.validation_hash = hashlib.sha256(base.encode()).hexdigest()
    
    if not instance.validation_url:
        instance.validation_url = f"{settings.FRONTEND_URL}/validate?code={instance.validation_hash}"


@receiver(post_save, sender=Certificate)
def handle_certificate_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un certificado.
    """
    if created:
        # Registrar en logs
        CertificateLog.objects.create(
            certificate=instance,
            action='GENERATE',
            user=instance.generated_by,
            ip_address='0.0.0.0',
            metadata={'auto_generated': instance.generated_by is None}
        )
        
        # Registrar actividad del usuario
        if instance.generated_by:
            UserActivity.objects.create(
                user=instance.generated_by,
                activity_type='CERTIFICATE_GENERATED',
                description=f'Certificado generado: {instance.certificate_code}',
                ip_address='0.0.0.0',
                user_agent='Sistema'
            )


@receiver(pre_save, sender=CertificateTemplate)
def handle_template_pre_save(sender, instance, **kwargs):
    """
    Señal que se ejecuta antes de guardar una plantilla.
    """
    if not instance.code:
        import secrets
        instance.code = f"TMP-{secrets.token_hex(4).upper()}"


@receiver(post_save, sender=CertificateTemplate)
def handle_template_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una plantilla.
    """
    if created:
        logger.info(f"Plantilla de certificado creada: {instance.code} - {instance.name}")


@receiver(post_delete, sender=Certificate)
def handle_certificate_deleted(sender, instance, **kwargs):
    """
    Señal que se ejecuta después de eliminar un certificado.
    Elimina los archivos físicos.
    """
    # Eliminar archivo PDF
    if instance.pdf_file and os.path.isfile(instance.pdf_file.path):
        os.remove(instance.pdf_file.path)
    
    # Eliminar código QR
    if instance.qr_code and os.path.isfile(instance.qr_code.path):
        os.remove(instance.qr_code.path)
    
    logger.info(f"Certificado eliminado: {instance.certificate_code}")
