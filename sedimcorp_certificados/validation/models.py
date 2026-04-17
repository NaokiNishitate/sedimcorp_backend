"""
Modelos para el módulo de validación de certificados.
Registra intentos de validación y mantiene estadísticas.
"""

from django.db import models
from django.conf import settings
import uuid


class ValidationAttempt(models.Model):
    """
    Registro de intentos de validación de certificados.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    certificate = models.ForeignKey(
        'certificates.Certificate',
        on_delete=models.CASCADE,
        related_name='validation_attempts',
        verbose_name='Certificado',
        blank=True,
        null=True
    )
    
    validation_hash = models.CharField(
        max_length=64,
        verbose_name='Hash intentado',
        db_index=True
    )
    
    was_successful = models.BooleanField(
        default=False,
        verbose_name='¿Fue exitoso?'
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name='Dirección IP'
    )
    
    user_agent = models.TextField(
        verbose_name='User Agent',
        blank=True,
        null=True
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y hora'
    )
    
    class Meta:
        verbose_name = 'Intento de validación'
        verbose_name_plural = 'Intentos de validación'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['validation_hash', 'timestamp']),
        ]
    
    def __str__(self):
        return f"{self.validation_hash[:16]} - {self.timestamp}"


class CertificateAccess(models.Model):
    """
    Registro de accesos a certificados (descargas, visualizaciones).
    """
    
    ACCESS_TYPES = [
        ('VIEW', 'Visualización'),
        ('DOWNLOAD', 'Descarga'),
        ('EMAIL', 'Envío por email'),
        ('SHARE', 'Compartir'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    certificate = models.ForeignKey(
        'certificates.Certificate',
        on_delete=models.CASCADE,
        related_name='accesses',
        verbose_name='Certificado'
    )
    
    access_type = models.CharField(
        max_length=20,
        choices=ACCESS_TYPES,
        verbose_name='Tipo de acceso'
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name='Dirección IP'
    )
    
    user_agent = models.TextField(
        verbose_name='User Agent',
        blank=True,
        null=True
    )
    
    referer = models.URLField(
        max_length=500,
        verbose_name='Origen',
        blank=True,
        null=True
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y hora'
    )
    
    class Meta:
        verbose_name = 'Acceso a certificado'
        verbose_name_plural = 'Accesos a certificados'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.certificate.certificate_code} - {self.get_access_type_display()} - {self.timestamp}"
