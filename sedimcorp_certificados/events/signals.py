"""
Señales para el módulo de eventos.
Maneja eventos relacionados con cursos, inscripciones y asistencias.
"""

from django.db.models.signals import post_save, pre_save, post_delete, m2m_changed
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone
from django.utils.text import slugify
from .models import Category, Course, Enrollment, Attendance, CourseModule
from users.models import UserActivity
from django.db import models
import logging

logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Category)
def handle_category_pre_save(sender, instance, **kwargs):
    """
    Señal que se ejecuta antes de guardar una categoría.
    Genera el slug a partir del nombre si no existe.
    """
    if not instance.slug:
        instance.slug = slugify(instance.name)


@receiver(pre_save, sender=Course)
def handle_course_pre_save(sender, instance, **kwargs):
    """
    Señal que se ejecuta antes de guardar un curso.
    Valida fechas y genera código/slug si es necesario.
    """
    if not instance.code:
        # Generar código automático
        import secrets
        instance.code = f"CRS-{secrets.token_hex(4).upper()}"
    
    if not instance.slug:
        instance.slug = slugify(instance.title)
    
    # Validar fechas
    if instance.start_date and instance.end_date:
        if instance.start_date > instance.end_date:
            raise ValueError("La fecha de inicio no puede ser posterior a la fecha de fin")
    
    if instance.enrollment_start and instance.enrollment_end:
        if instance.enrollment_start > instance.enrollment_end:
            raise ValueError("La fecha de inicio de inscripción no puede ser posterior a la fecha de fin")


@receiver(post_save, sender=Course)
def handle_course_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar un curso.
    """
    if created:
        logger.info(f"Curso creado: {instance.code} - {instance.title}")
        
        # Notificar a administradores
        if instance.status == 'PUBLISHED':
            # Aquí se podría enviar notificación a los usuarios interesados
            pass


@receiver(post_save, sender=Enrollment)
def handle_enrollment_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de guardar una inscripción.
    """
    if created:
        # Registrar actividad
        UserActivity.objects.create(
            user=instance.participant,
            activity_type='COURSE_ENROLL',
            description=f'Inscripción al curso: {instance.course.title}',
            ip_address='0.0.0.0',
            user_agent='Sistema'
        )
        
        # Enviar email de confirmación
        try:
            subject = f'Confirmación de inscripción - {instance.course.title}'
            message = f'''
            Hola {instance.participant.get_full_name()},
            
            Te has inscrito exitosamente al curso: {instance.course.title}
            
            Código de inscripción: {instance.enrollment_code}
            Fecha de inicio: {instance.course.start_date}
            
            Pronto recibirás más información sobre el curso.
            
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
            logger.error(f"Error enviando email de inscripción: {str(e)}")
    
    else:
        # Si cambió el estado, registrar
        if instance.tracker.has_changed('status'):
            UserActivity.objects.create(
                user=instance.participant,
                activity_type='ENROLLMENT_UPDATED',
                description=f'Estado de inscripción actualizado: {instance.get_status_display()}',
                ip_address='0.0.0.0',
                user_agent='Sistema'
            )


@receiver(post_save, sender=Attendance)
def handle_attendance_post_save(sender, instance, created, **kwargs):
    """
    Señal que se ejecuta después de registrar una asistencia.
    Actualiza el porcentaje de asistencia de la inscripción.
    """
    if created:
        enrollment = instance.enrollment
        total_sessions = enrollment.course.schedules.count()
        
        if total_sessions > 0:
            attended = enrollment.attendances.filter(is_present=True).count()
            enrollment.attendance_percentage = (attended / total_sessions) * 100
            enrollment.save(update_fields=['attendance_percentage'])
            
            # Verificar si cumple para certificación
            if enrollment.attendance_percentage >= 80 and enrollment.final_grade and enrollment.final_grade >= 13:
                enrollment.status = 'COMPLETED'
                enrollment.is_approved = True
                enrollment.completion_date = timezone.now()
                enrollment.save()


@receiver(m2m_changed, sender=Course.instructors.through)
def handle_course_instructors_changed(sender, instance, action, pk_set, **kwargs):
    """
    Señal que se ejecuta cuando cambian los instructores de un curso.
    """
    if action == 'post_add' and pk_set:
        from users.models import User
        instructors = User.objects.filter(pk__in=pk_set)
        for instructor in instructors:
            logger.info(f"Instructor {instructor.get_full_name()} asignado al curso {instance.code}")


@receiver(pre_save, sender=CourseModule)
def handle_module_pre_save(sender, instance, **kwargs):
    """
    Señal que se ejecuta antes de guardar un módulo.
    """
    if not instance.order:
        # Asignar el siguiente número de orden
        last_order = CourseModule.objects.filter(course=instance.course).aggregate(
            models.Max('order')
        )['order__max']
        instance.order = (last_order or 0) + 1
