"""
Configuración del panel de administración para el módulo de validación.
"""

from django.contrib import admin
from .models import ValidationAttempt, CertificateAccess


@admin.register(ValidationAttempt)
class ValidationAttemptAdmin(admin.ModelAdmin):
    """
    Configuración para intentos de validación en el admin.
    """
    
    list_display = [
        'id', 'certificate', 'validation_hash_short',
        'was_successful', 'ip_address', 'timestamp'
    ]
    
    list_filter = ['was_successful', 'timestamp']
    search_fields = ['validation_hash', 'ip_address', 'certificate__certificate_code']
    readonly_fields = ['certificate', 'validation_hash', 'was_successful', 
                       'ip_address', 'user_agent', 'timestamp']
    
    def validation_hash_short(self, obj):
        """Muestra solo los primeros caracteres del hash."""
        return obj.validation_hash[:16] + "..."
    validation_hash_short.short_description = 'Hash'
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(CertificateAccess)
class CertificateAccessAdmin(admin.ModelAdmin):
    """
    Configuración para accesos a certificados en el admin.
    """
    
    list_display = [
        'certificate', 'access_type', 'ip_address',
        'timestamp', 'referer'
    ]
    
    list_filter = ['access_type', 'timestamp']
    search_fields = ['certificate__certificate_code', 'ip_address']
    readonly_fields = ['certificate', 'access_type', 'ip_address', 
                       'user_agent', 'referer', 'timestamp']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False
