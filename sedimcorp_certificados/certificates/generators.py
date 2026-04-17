"""
Generadores de certificados en PDF con códigos QR.
Utiliza ReportLab para generar PDFs personalizados.
"""

import os
import hashlib
import qrcode
from io import BytesIO
from datetime import datetime
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, A5, letter, landscape
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PIL import Image
import uuid

from .models import Certificate, CertificateTemplate, CertificateLog


class CertificateGenerator:
    """
    Clase para generar certificados en PDF.
    """
    
    # Mapeo de tamaños de papel
    PAPER_SIZES = {
        'A4': A4,
        'A5': A5,
        'LETTER': letter,
        'LEGAL': (612, 1008),  # Legal en puntos
    }
    
    def __init__(self, enrollment, template=None, custom_text=None):
        """
        Inicializa el generador de certificados.
        
        Args:
            enrollment: Objeto Enrollment de la inscripción
            template: Plantilla a utilizar (opcional)
            custom_text: Texto personalizado (opcional)
        """
        self.enrollment = enrollment
        self.participant = enrollment.participant
        self.course = enrollment.course
        
        # Usar plantilla del curso o la por defecto
        if template:
            self.template = template
        elif self.course.certificate_template:
            self.template = self.course.certificate_template
        else:
            self.template = CertificateTemplate.objects.filter(is_default=True).first()
        
        if not self.template:
            raise ValueError("No hay plantilla de certificado disponible")
        
        self.custom_text = custom_text or self.course.certificate_text or self.template.default_text
        
        # Datos del certificado
        self.participant_name = self.participant.get_full_name().upper()
        self.course_name = self.course.title
        self.issue_date = timezone.now().date()
        self.completion_date = enrollment.completion_date or timezone.now().date()
        
        # Calcular duración
        duration_text = f"{self.course.duration_hours} horas"
        if self.course.duration_weeks:
            duration_text += f" ({self.course.duration_weeks} semanas)"
        self.course_duration = duration_text
        
        # Generar hash de validación único
        self.validation_hash = self.generate_validation_hash()
        
        # URL de validación
        self.validation_url = f"{settings.FRONTEND_URL}/validate/{self.validation_hash}"
        
    def generate_validation_hash(self):
        """
        Genera un hash único para validación.
        
        Returns:
            str: Hash SHA256 único
        """
        base = f"{self.enrollment.id}{self.participant.document_number}{self.course.id}{uuid.uuid4()}"
        return hashlib.sha256(base.encode()).hexdigest()
    
    def generate_qr_code(self):
        """
        Genera código QR con la URL de validación.
        
        Returns:
            BytesIO: Imagen del QR en memoria
        """
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        qr.add_data(self.validation_url)
        qr.make(fit=True)
        
        qr_image = qr.make_image(fill_color="black", back_color="white")
        
        # Redimensionar al tamaño especificado en la plantilla
        qr_image = qr_image.resize(
            (self.template.qr_size, self.template.qr_size),
            Image.Resampling.LANCZOS
        )
        
        # Convertir a BytesIO
        qr_buffer = BytesIO()
        qr_image.save(qr_buffer, format='PNG')
        qr_buffer.seek(0)
        
        return qr_buffer
    
    def generate_pdf(self):
        """
        Genera el PDF del certificado.
        
        Returns:
            BytesIO: PDF generado en memoria
        """
        # Configurar página
        if self.template.orientation == 'LANDSCAPE':
            page_size = landscape(self.PAPER_SIZES.get(self.template.paper_size, A4))
        else:
            page_size = self.PAPER_SIZES.get(self.template.paper_size, A4)
        
        # Crear buffer para PDF
        buffer = BytesIO()
        
        # Crear canvas
        c = canvas.Canvas(buffer, pagesize=page_size)
        width, height = page_size
        
        # Agregar imagen de fondo si existe
        if self.template.background_image and os.path.exists(self.template.background_image.path):
            bg_image = ImageReader(self.template.background_image.path)
            c.drawImage(bg_image, 0, 0, width=width, height=height, preserveAspectRatio=True, mask='auto')
        
        # Configurar fuente (usar Helvetica por defecto)
        c.setFont("Helvetica-Bold", self.template.name_font_size)
        
        # Dibujar texto personalizado (si existe)
        if self.custom_text:
            c.setFont("Helvetica", 20)
            c.drawString(
                self.template.name_position_x,
                height - self.template.name_position_y - 60,
                self.custom_text
            )
        
        # Dibujar nombre del participante
        c.setFont("Helvetica-Bold", self.template.name_font_size)
        c.setFillColor(self.template.name_font_color)
        c.drawString(
            self.template.name_position_x,
            height - self.template.name_position_y,
            self.participant_name
        )
        
        # Dibujar nombre del curso
        c.setFont("Helvetica", self.template.course_font_size)
        c.setFillColor("#000000")
        c.drawString(
            self.template.course_position_x,
            height - self.template.course_position_y,
            self.course_name
        )
        
        # Dibujar fecha
        c.setFont("Helvetica", self.template.date_font_size)
        fecha_texto = f"Emitido el: {self.issue_date.strftime('%d de %B de %Y')}"
        c.drawString(
            self.template.date_position_x,
            height - self.template.date_position_y,
            fecha_texto
        )
        
        # Generar y agregar código QR
        qr_buffer = self.generate_qr_code()
        qr_image = ImageReader(qr_buffer)
        c.drawImage(
            qr_image,
            self.template.qr_position_x,
            height - self.template.qr_position_y - self.template.qr_size,
            width=self.template.qr_size,
            height=self.template.qr_size,
            preserveAspectRatio=True
        )
        
        # Agregar texto de validación
        c.setFont("Helvetica", 8)
        c.drawString(
            self.template.qr_position_x,
            height - self.template.qr_position_y - self.template.qr_size - 15,
            "Escanee para validar"
        )
        
        # Agregar código de certificado
        c.setFont("Helvetica", 8)
        c.drawString(
            50, 50,
            f"Código: {self.validation_hash[:16].upper()}"
        )
        
        # Finalizar página
        c.showPage()
        c.save()
        
        buffer.seek(0)
        return buffer
    
    def create_certificate(self, generated_by):
        """
        Crea y guarda el certificado en la base de datos.
        
        Args:
            generated_by: Usuario que genera el certificado
            
        Returns:
            Certificate: Certificado creado
        """
        # Verificar si ya existe certificado
        if hasattr(self.enrollment, 'certificate'):
            return self.enrollment.certificate
        
        # Generar PDF
        pdf_buffer = self.generate_pdf()
        
        # Generar QR como imagen
        qr_buffer = self.generate_qr_code()
        
        # Crear certificado en BD
        certificate = Certificate.objects.create(
            enrollment=self.enrollment,
            template=self.template,
            participant_name=self.participant_name,
            participant_document=self.participant.document_number,
            course_name=self.course_name,
            course_duration=self.course_duration,
            issue_date=self.issue_date,
            completion_date=self.completion_date,
            custom_text=self.custom_text,
            validation_hash=self.validation_hash,
            validation_url=self.validation_url,
            generated_by=generated_by,
            generated_at=timezone.now(),
            status='GENERATED',
            metadata={
                'course_code': self.course.code,
                'enrollment_code': self.enrollment.enrollment_code,
                'duration_hours': float(self.course.duration_hours),
                'template_code': self.template.code
            }
        )
        
        # Guardar archivos
        pdf_filename = f"certificate_{certificate.certificate_code}.pdf"
        certificate.pdf_file.save(pdf_filename, ContentFile(pdf_buffer.getvalue()))
        
        qr_filename = f"qr_{certificate.certificate_code}.png"
        certificate.qr_code.save(qr_filename, ContentFile(qr_buffer.getvalue()))
        
        # Registrar log
        CertificateLog.objects.create(
            certificate=certificate,
            action='GENERATE',
            user=generated_by,
            ip_address=getattr(generated_by, 'last_ip', None),
            metadata={'generator': 'CertificateGenerator'}
        )
        
        return certificate
    
    @staticmethod
    def validate_certificate(validation_hash):
        """
        Valida un certificado por su hash.
        
        Args:
            validation_hash: Hash de validación
            
        Returns:
            tuple: (Certificate, bool) certificado y si es válido
        """
        try:
            certificate = Certificate.objects.get(
                validation_hash=validation_hash,
                status__in=['GENERATED', 'DOWNLOADED', 'VALIDATED']
            )
            return certificate, True
        except Certificate.DoesNotExist:
            return None, False


class BatchCertificateGenerator:
    """
    Generador de certificados por lote.
    """
    
    def __init__(self, course):
        """
        Inicializa generador por lote.
        
        Args:
            course: Curso para generar certificados
        """
        self.course = course
        self.enrollments = course.enrollments.filter(
            status='COMPLETED',
            is_approved=True,
            certificate__isnull=True
        )
    
    def generate_all(self, generated_by):
        """
        Genera certificados para todas las inscripciones aprobadas.
        
        Args:
            generated_by: Usuario que genera los certificados
            
        Returns:
            dict: Estadísticas de generación
        """
        generated = []
        errors = []
        
        for enrollment in self.enrollments:
            try:
                generator = CertificateGenerator(enrollment)
                certificate = generator.create_certificate(generated_by)
                generated.append({
                    'enrollment': enrollment.enrollment_code,
                    'certificate': certificate.certificate_code
                })
            except Exception as e:
                errors.append({
                    'enrollment': enrollment.enrollment_code,
                    'error': str(e)
                })
        
        return {
            'total': len(self.enrollments),
            'generated': len(generated),
            'errors': len(errors),
            'generated_list': generated,
            'error_list': errors
        }
