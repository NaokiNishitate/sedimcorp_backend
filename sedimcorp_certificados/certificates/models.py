"""
Modelos para la gestión de certificados digitales.
Define plantillas, certificados emitidos y configuración de generación.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, FileExtensionValidator
from django.utils import timezone
from django.conf import settings
import uuid
import os


def certificate_template_path(instance, filename):
    """Genera ruta para plantillas de certificados."""
    ext = filename.split('.')[-1]
    filename = f"{instance.code}_{timezone.now().strftime('%Y%m%d_%H%M%S')}.{ext}"
    return os.path.join('certificates/templates/', filename)


def certificate_pdf_path(instance, filename):
    """Genera ruta para PDFs de certificados emitidos."""
    ext = filename.split('.')[-1]
    filename = f"{instance.certificate_code}_{timezone.now().strftime('%Y%m%d')}.{ext}"
    return os.path.join('certificates/issued/', filename)


class CertificateTemplate(models.Model):
    """
    Plantillas para certificados.
    Define el diseño y formato de los certificados.
    """
    
    # Orientaciones
    ORIENTATION_CHOICES = [
        ('PORTRAIT', 'Vertical'),
        ('LANDSCAPE', 'Horizontal'),
    ]
    
    # Tamaños de papel
    PAPER_SIZE_CHOICES = [
        ('A4', 'A4'),
        ('A5', 'A5'),
        ('LETTER', 'Carta'),
        ('LEGAL', 'Oficio'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código de plantilla'
    )
    
    name = models.CharField(
        max_length=200,
        verbose_name='Nombre de la plantilla'
    )
    
    description = models.TextField(
        max_length=500,
        verbose_name='Descripción',
        blank=True,
        null=True
    )
    
    # Archivos de plantilla
    template_file = models.FileField(
        upload_to=certificate_template_path,
        verbose_name='Archivo de plantilla',
        validators=[FileExtensionValidator(['html', 'pdf', 'jpg', 'png'])],
        help_text='HTML, PDF o imagen de fondo'
    )
    
    background_image = models.ImageField(
        upload_to='certificates/backgrounds/',
        verbose_name='Imagen de fondo',
        blank=True,
        null=True
    )
    
    # Configuración de diseño
    orientation = models.CharField(
        max_length=10,
        choices=ORIENTATION_CHOICES,
        default='LANDSCAPE',
        verbose_name='Orientación'
    )
    
    paper_size = models.CharField(
        max_length=10,
        choices=PAPER_SIZE_CHOICES,
        default='A4',
        verbose_name='Tamaño de papel'
    )
    
    margin_top = models.FloatField(
        default=50,
        verbose_name='Margen superior (px)'
    )
    
    margin_bottom = models.FloatField(
        default=50,
        verbose_name='Margen inferior (px)'
    )
    
    margin_left = models.FloatField(
        default=50,
        verbose_name='Margen izquierdo (px)'
    )
    
    margin_right = models.FloatField(
        default=50,
        verbose_name='Margen derecho (px)'
    )
    
    # Configuración de campos
    name_font_size = models.IntegerField(
        default=48,
        verbose_name='Tamaño fuente del nombre'
    )
    
    name_font_color = models.CharField(
        max_length=20,
        default='#000000',
        verbose_name='Color del nombre'
    )
    
    name_position_x = models.FloatField(
        default=300,
        verbose_name='Posición X del nombre'
    )
    
    name_position_y = models.FloatField(
        default=400,
        verbose_name='Posición Y del nombre'
    )
    
    course_font_size = models.IntegerField(
        default=24,
        verbose_name='Tamaño fuente del curso'
    )
    
    course_position_x = models.FloatField(
        default=300,
        verbose_name='Posición X del curso'
    )
    
    course_position_y = models.FloatField(
        default=500,
        verbose_name='Posición Y del curso'
    )
    
    date_font_size = models.IntegerField(
        default=18,
        verbose_name='Tamaño fuente de la fecha'
    )
    
    date_position_x = models.FloatField(
        default=300,
        verbose_name='Posición X de la fecha'
    )
    
    date_position_y = models.FloatField(
        default=600,
        verbose_name='Posición Y de la fecha'
    )
    
    qr_size = models.IntegerField(
        default=100,
        verbose_name='Tamaño del código QR'
    )
    
    qr_position_x = models.FloatField(
        default=600,
        verbose_name='Posición X del QR'
    )
    
    qr_position_y = models.FloatField(
        default=500,
        verbose_name='Posición Y del QR'
    )
    
    # Texto por defecto
    default_text = models.TextField(
        max_length=1000,
        verbose_name='Texto por defecto',
        default='Otorga el presente certificado a:',
        help_text='Texto que aparecerá antes del nombre'
    )
    
    # Estado y auditoría
    is_active = models.BooleanField(
        default=True,
        verbose_name='¿Activa?'
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name='¿Plantilla por defecto?'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_templates',
        verbose_name='Creado por'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Plantilla de certificado'
        verbose_name_plural = 'Plantillas de certificados'
        ordering = ['-is_default', 'name']
    
    def __str__(self):
        return f"{self.code} - {self.name}"
    
    def save(self, *args, **kwargs):
        """Si es plantilla por defecto, desmarcar otras."""
        if self.is_default:
            CertificateTemplate.objects.filter(is_default=True).update(is_default=False)
        super().save(*args, **kwargs)


class Certificate(models.Model):
    """
    Certificados emitidos a participantes.
    """
    
    # Estados del certificado
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('GENERATED', 'Generado'),
        ('SENT', 'Enviado'),
        ('DOWNLOADED', 'Descargado'),
        ('VALIDATED', 'Validado'),
        ('CANCELLED', 'Anulado'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    certificate_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código del certificado'
    )
    
    enrollment = models.OneToOneField(
        'events.Enrollment',
        on_delete=models.PROTECT,
        related_name='certificate',
        verbose_name='Inscripción'
    )
    
    template = models.ForeignKey(
        CertificateTemplate,
        on_delete=models.PROTECT,
        related_name='certificates',
        verbose_name='Plantilla utilizada'
    )
    
    # Archivos generados
    pdf_file = models.FileField(
        upload_to=certificate_pdf_path,
        verbose_name='Archivo PDF',
        blank=True,
        null=True
    )
    
    qr_code = models.ImageField(
        upload_to='certificates/qrcodes/',
        verbose_name='Código QR',
        blank=True,
        null=True
    )
    
    # Datos del certificado
    participant_name = models.CharField(
        max_length=200,
        verbose_name='Nombre del participante'
    )
    
    participant_document = models.CharField(
        max_length=20,
        verbose_name='Documento del participante'
    )
    
    course_name = models.CharField(
        max_length=200,
        verbose_name='Nombre del curso'
    )
    
    course_duration = models.CharField(
        max_length=100,
        verbose_name='Duración del curso'
    )
    
    issue_date = models.DateField(
        default=timezone.now,
        verbose_name='Fecha de emisión'
    )
    
    completion_date = models.DateField(
        verbose_name='Fecha de culminación'
    )
    
    custom_text = models.TextField(
        max_length=1000,
        verbose_name='Texto personalizado',
        blank=True,
        null=True
    )
    
    # Validación
    validation_hash = models.CharField(
        max_length=64,
        unique=True,
        verbose_name='Hash de validación'
    )
    
    validation_url = models.URLField(
        max_length=255,
        verbose_name='URL de validación'
    )
    
    # Metadatos adicionales
    metadata = models.JSONField(
        verbose_name='Metadatos',
        default=dict,
        blank=True
    )
    
    # Control y auditoría
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='Estado'
    )
    
    generated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='generated_certificates',
        verbose_name='Generado por'
    )
    
    generated_at = models.DateTimeField(
        verbose_name='Fecha de generación',
        blank=True,
        null=True
    )
    
    downloaded_at = models.DateTimeField(
        verbose_name='Fecha de descarga',
        blank=True,
        null=True
    )
    
    downloaded_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Número de descargas'
    )
    
    validated_at = models.DateTimeField(
        verbose_name='Fecha de validación',
        blank=True,
        null=True
    )
    
    validated_ip = models.GenericIPAddressField(
        verbose_name='IP de validación',
        blank=True,
        null=True
    )
    
    cancelled_at = models.DateTimeField(
        verbose_name='Fecha de anulación',
        blank=True,
        null=True
    )
    
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='cancelled_certificates',
        verbose_name='Anulado por',
        blank=True,
        null=True
    )
    
    cancellation_reason = models.TextField(
        max_length=500,
        verbose_name='Motivo de anulación',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Certificado'
        verbose_name_plural = 'Certificados'
        ordering = ['-issue_date', '-created_at']
        indexes = [
            models.Index(fields=['certificate_code', 'validation_hash']),
            models.Index(fields=['status', 'issue_date']),
            models.Index(fields=['participant_document']),
        ]
    
    def __str__(self):
        return f"{self.certificate_code} - {self.participant_name}"
    
    def save(self, *args, **kwargs):
        """Genera código único si no existe."""
        if not self.certificate_code:
            self.certificate_code = self.generate_certificate_code()
        super().save(*args, **kwargs)
    
    def generate_certificate_code(self):
        """Genera un código único para el certificado."""
        import hashlib
        import time
        
        base = f"{self.enrollment.id}{self.participant_document}{time.time()}"
        hash_object = hashlib.sha256(base.encode())
        return f"CERT-{hash_object.hexdigest()[:12].upper()}"
    
    def register_download(self, request=None):
        """Registra una descarga del certificado."""
        self.downloaded_count += 1
        self.downloaded_at = timezone.now()
        if self.status == 'GENERATED':
            self.status = 'DOWNLOADED'
        self.save(update_fields=['downloaded_count', 'downloaded_at', 'status'])
    
    def register_validation(self, ip_address=None):
        """Registra una validación del certificado."""
        self.status = 'VALIDATED'
        self.validated_at = timezone.now()
        self.validated_ip = ip_address
        self.save(update_fields=['status', 'validated_at', 'validated_ip'])


class CertificateLog(models.Model):
    """
    Registro de acciones sobre certificados.
    """
    
    ACTION_CHOICES = [
        ('GENERATE', 'Generación'),
        ('DOWNLOAD', 'Descarga'),
        ('VALIDATE', 'Validación'),
        ('EMAIL', 'Envío por email'),
        ('CANCEL', 'Anulación'),
        ('RENEW', 'Renovación'),
    ]
    
    certificate = models.ForeignKey(
        Certificate,
        on_delete=models.CASCADE,
        related_name='logs',
        verbose_name='Certificado'
    )
    
    action = models.CharField(
        max_length=20,
        choices=ACTION_CHOICES,
        verbose_name='Acción'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='certificate_logs',
        verbose_name='Usuario',
        blank=True,
        null=True
    )
    
    ip_address = models.GenericIPAddressField(
        verbose_name='Dirección IP'
    )
    
    user_agent = models.TextField(
        verbose_name='User Agent',
        blank=True,
        null=True
    )
    
    metadata = models.JSONField(
        verbose_name='Metadatos',
        default=dict,
        blank=True
    )
    
    timestamp = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha y hora'
    )
    
    class Meta:
        verbose_name = 'Registro de certificado'
        verbose_name_plural = 'Registros de certificados'
        ordering = ['-timestamp']
    
    def __str__(self):
        return f"{self.certificate.certificate_code} - {self.get_action_display()} - {self.timestamp}"
