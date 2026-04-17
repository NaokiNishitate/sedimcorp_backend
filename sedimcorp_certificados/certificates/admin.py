"""
Configuración del panel de administración para el módulo de certificados.
"""

from django.contrib import admin
from django.utils.html import format_html
from .models import CertificateTemplate, Certificate, CertificateLog


@admin.register(CertificateTemplate)
class CertificateTemplateAdmin(admin.ModelAdmin):
    """
    Configuración para plantillas en el admin.
    """
    
    list_display = [
        'code', 'name', 'paper_size', 'orientation',
        'is_default', 'is_active', 'preview_link'
    ]
    
    list_filter = ['is_active', 'is_default', 'orientation', 'paper_size']
    search_fields = ['code', 'name', 'description']
    
    fieldsets = (
        ('Información General', {
            'fields': ('code', 'name', 'description', 'template_file', 'background_image')
        }),
        ('Configuración de Página', {
            'fields': ('orientation', 'paper_size', 'margin_top', 'margin_bottom',
                      'margin_left', 'margin_right')
        }),
        ('Configuración de Nombre', {
            'fields': ('name_font_size', 'name_font_color', 'name_position_x', 'name_position_y')
        }),
        ('Configuración de Curso', {
            'fields': ('course_font_size', 'course_position_x', 'course_position_y')
        }),
        ('Configuración de Fecha', {
            'fields': ('date_font_size', 'date_position_x', 'date_position_y')
        }),
        ('Configuración de QR', {
            'fields': ('qr_size', 'qr_position_x', 'qr_position_y')
        }),
        ('Texto y Estado', {
            'fields': ('default_text', 'is_active', 'is_default')
        }),
    )
    
    readonly_fields = ['created_at', 'updated_at']
    
    def preview_link(self, obj):
        """Enlace para previsualizar plantilla."""
        if obj.template_file:
            return format_html(
                '<a href="{}" target="_blank">Ver plantilla</a>',
                obj.template_file.url
            )
        return "Sin archivo"
    preview_link.short_description = 'Previsualización'


@admin.register(Certificate)
class CertificateAdmin(admin.ModelAdmin):
    """
    Configuración para certificados en el admin.
    """
    
    list_display = [
        'certificate_code', 'participant_name', 'course_name',
        'issue_date', 'status', 'downloaded_count', 'view_pdf'
    ]
    
    list_filter = ['status', 'issue_date', 'generated_at']
    search_fields = [
        'certificate_code', 'participant_name',
        'participant_document', 'course_name'
    ]
    
    readonly_fields = [
        'certificate_code', 'validation_hash', 'validation_url',
        'generated_at', 'downloaded_count', 'validated_at',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Información del Certificado', {
            'fields': (
                'certificate_code', 'enrollment', 'template',
                'status', 'issue_date', 'completion_date'
            )
        }),
        ('Datos del Participante', {
            'fields': ('participant_name', 'participant_document')
        }),
        ('Datos del Curso', {
            'fields': ('course_name', 'course_duration', 'custom_text')
        }),
        ('Archivos', {
            'fields': ('pdf_file', 'qr_code')
        }),
        ('Validación', {
            'fields': ('validation_hash', 'validation_url', 'validated_at', 'validated_ip')
        }),
        ('Control', {
            'fields': (
                'generated_by', 'generated_at',
                'downloaded_count', 'downloaded_at'
            )
        }),
        ('Anulación', {
            'fields': ('cancelled_at', 'cancelled_by', 'cancellation_reason'),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['mark_as_sent', 'generate_pdf']
    
    def view_pdf(self, obj):
        """Enlace para ver PDF."""
        if obj.pdf_file:
            return format_html(
                '<a href="{}" target="_blank">Ver PDF</a>',
                obj.pdf_file.url
            )
        return "Sin archivo"
    view_pdf.short_description = 'PDF'
    
    def mark_as_sent(self, request, queryset):
        """Marca certificados como enviados."""
        updated = queryset.update(status='SENT')
        self.message_user(request, f'{updated} certificados marcados como enviados.')
    mark_as_sent.short_description = 'Marcar como enviados'
    
    def generate_pdf(self, request, queryset):
        """Regenera PDFs de certificados."""
        from .generators import CertificateGenerator
        
        success = 0
        errors = 0
        
        for certificate in queryset:
            try:
                generator = CertificateGenerator(certificate.enrollment)
                new_pdf = generator.generate_pdf()
                
                # Guardar nuevo PDF
                pdf_filename = f"certificate_{certificate.certificate_code}.pdf"
                from django.core.files.base import ContentFile
                certificate.pdf_file.save(pdf_filename, ContentFile(new_pdf.getvalue()))
                
                success += 1
            except:
                errors += 1
        
        self.message_user(request, f'PDFs generados: {success}, Errores: {errors}')
    generate_pdf.short_description = 'Regenerar PDFs'


@admin.register(CertificateLog)
class CertificateLogAdmin(admin.ModelAdmin):
    """
    Configuración para logs en el admin.
    """
    
    list_display = ['certificate', 'action', 'user', 'ip_address', 'timestamp']
    list_filter = ['action', 'timestamp']
    search_fields = ['certificate__certificate_code', 'user__email']
    readonly_fields = ['certificate', 'action', 'user', 'ip_address', 'user_agent', 'metadata', 'timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
