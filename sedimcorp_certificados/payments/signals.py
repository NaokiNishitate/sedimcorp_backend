"""
Señales para el módulo de pagos.
Maneja eventos relacionados con transacciones y pagos.
"""

from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from .models import Payment, PaymentTransaction, Refund
from events.models import Enrollment
from users.models import UserActivity
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Payment)
def handle_payment_pre_save(sender, instance, **kwargs):
    """
    Señal que se ejecuta antes de guardar un pago.
    """
    if not instance.payment_code:
        import secrets
        instance.payment_code = f"PAY-{secrets.token_hex(6).upper()}"
    
    # Calcular montos si no existen
    if not instance.net_amount and instance.payment_method:
        instance.commission = instance.payment_method.calculate_commission(instance.amount)
        instance.net_amount = instance.amount - instance.commission


@receiver(post_save, sender=Payment)
def handle_payment_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un pago.
    """
    if created:
        logger.info(f"Pago creado: {instance.payment_code} - {instance.amount}")
        
        # Registrar actividad
        UserActivity.objects.create(
            user=instance.user,
            activity_type='PAYMENT',
            description=f'Pago realizado: {instance.payment_code}',
            ip_address='0.0.0.0',
            user_agent='Sistema'
        )
    
    # Si el pago se confirma, actualizar inscripción
    if instance.status == 'COMPLETED' and instance.payment_confirmed:
        try:
            enrollment = instance.enrollment
            if enrollment.status == 'PENDING':
                enrollment.status = 'CONFIRMED'
                enrollment.payment_confirmed = True
                enrollment.payment_date = instance.confirmed_at or timezone.now()
                enrollment.save()
                
                logger.info(f"Inscripción confirmada por pago: {enrollment.enrollment_code}")
                
                # Enviar email de confirmación
                try:
                    subject = 'Pago confirmado - SEDIMCORP'
                    message = f'''
                    Hola {instance.user.get_full_name()},
                    
                    Tu pago por el curso {enrollment.course.title} ha sido confirmado.
                    
                    Código de pago: {instance.payment_code}
                    Monto: S/ {instance.amount}
                    Fecha: {instance.confirmed_at}
                    
                    Ya puedes acceder al curso desde tu dashboard.
                    
                    Saludos,
                    Equipo SEDIMCORP
                    '''
                    
                    send_mail(
                        subject,
                        message,
                        settings.DEFAULT_FROM_EMAIL,
                        [instance.user.email],
                        fail_silently=True,
                    )
                except Exception as e:
                    logger.error(f"Error enviando email de confirmación de pago: {str(e)}")
                    
        except Enrollment.DoesNotExist:
            logger.error(f"Enrollment no encontrado para payment {instance.payment_code}")


@receiver(post_save, sender=PaymentTransaction)
def handle_transaction_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una transacción.
    """
    if created:
        if instance.status == 'FAILED':
            logger.warning(f"Transacción fallida: {instance.gateway} - {instance.gateway_transaction_id}")
            
            # Actualizar estado del pago
            payment = instance.payment
            if payment.status == 'PROCESSING':
                payment.status = 'FAILED'
                payment.save()
        elif instance.status == 'COMPLETED':
            logger.info(f"Transacción exitosa: {instance.gateway} - {instance.gateway_transaction_id}")


@receiver(post_save, sender=Refund)
def handle_refund_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un reembolso.
    """
    if created:
        logger.info(f"Reembolso solicitado: {instance.refund_code} - {instance.amount}")
        
        # Actualizar estado del pago
        payment = instance.payment
        payment.status = 'REFUNDED'
        payment.save()
        
        # Actualizar inscripción
        enrollment = payment.enrollment
        enrollment.status = 'REFUNDED'
        enrollment.save()
        
        # Enviar email al usuario
        try:
            subject = 'Reembolso procesado - SEDIMCORP'
            message = f'''
            Hola {payment.user.get_full_name()},
            
            Se ha procesado tu solicitud de reembolso.
            
            Código de reembolso: {instance.refund_code}
            Monto: S/ {instance.amount}
            Motivo: {instance.get_reason_display()}
            
            El dinero será devuelto a tu método de pago original en los próximos días hábiles.
            
            Saludos,
            Equipo SEDIMCORP
            '''
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [payment.user.email],
                fail_silently=True,
            )
        except Exception as e:
            logger.error(f"Error enviando email de reembolso: {str(e)}")


@receiver(post_save, sender=Payment)
def handle_payment_status_change(sender, instance, **kwargs):
    """
    Señal que detecta cambios de estado en pagos.
    """
    if instance.pk:
        try:
            old = Payment.objects.get(pk=instance.pk)
            if old.status != instance.status:
                logger.info(f"Pago {instance.payment_code} cambió de estado: {old.status} -> {instance.status}")
                
                # Registrar actividad
                UserActivity.objects.create(
                    user=instance.user,
                    activity_type='PAYMENT_STATUS',
                    description=f'Estado de pago actualizado: {instance.get_status_display()}',
                    ip_address='0.0.0.0',
                    user_agent='Sistema'
                )
        except Payment.DoesNotExist:
            pass
