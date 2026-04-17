"""
Configuración del panel de administración para el módulo de usuarios.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _
from .models import User, PasswordReset, UserActivity


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    """
    Configuración personalizada para el modelo User en el admin.
    """
    
    list_display = [
        'email', 'get_full_name', 'user_type', 
        'document_number', 'is_active', 'email_verified',
        'date_joined'
    ]
    
    list_filter = [
        'user_type', 'is_active', 'email_verified',
        'phone_verified', 'date_joined'
    ]
    
    search_fields = [
        'email', 'first_name', 'last_name', 
        'document_number', 'phone'
    ]
    
    ordering = ['-date_joined']
    
    fieldsets = (
        (_('Información de cuenta'), {
            'fields': (
                'email', 'password', 'user_type',
                'is_active', 'email_verified', 'phone_verified'
            )
        }),
        (_('Información personal'), {
            'fields': (
                'first_name', 'last_name', 'document_type',
                'document_number', 'phone', 'gender',
                'birth_date', 'address', 'profile_image'
            )
        }),
        (_('Información profesional'), {
            'fields': (
                'professional_title', 'specialization',
                'biography'
            ),
            'classes': ('collapse',)
        }),
        (_('Seguridad'), {
            'fields': (
                'last_login', 'last_ip', 
                'failed_login_attempts', 'locked_until'
            ),
            'classes': ('collapse',)
        }),
        (_('Permisos'), {
            'fields': (
                'is_staff', 'is_superuser', 
                'groups', 'user_permissions'
            ),
            'classes': ('collapse',)
        }),
        (_('Preferencias'), {
            'fields': (
                'receive_notifications', 'receive_promotions',
                'language_preference'
            ),
            'classes': ('collapse',)
        }),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': (
                'email', 'password1', 'password2',
                'first_name', 'last_name', 'document_type',
                'document_number', 'user_type'
            ),
        }),
    )
    
    readonly_fields = [
        'last_login', 'date_joined', 'updated_at',
        'failed_login_attempts', 'locked_until'
    ]
    
    def get_full_name(self, obj):
        """Retorna el nombre completo del usuario."""
        return obj.get_full_name()
    get_full_name.short_description = 'Nombre completo'
    get_full_name.admin_order_field = 'first_name'


@admin.register(PasswordReset)
class PasswordResetAdmin(admin.ModelAdmin):
    """
    Configuración para el modelo PasswordReset en el admin.
    """
    
    list_display = [
        'user', 'created_at', 'expires_at', 
        'is_used', 'ip_address'
    ]
    
    list_filter = ['is_used', 'created_at', 'expires_at']
    search_fields = ['user__email', 'user__first_name', 'user__last_name']
    readonly_fields = ['token', 'created_at', 'expires_at']
    ordering = ['-created_at']


@admin.register(UserActivity)
class UserActivityAdmin(admin.ModelAdmin):
    """
    Configuración para el modelo UserActivity en el admin.
    """
    
    list_display = [
        'user', 'activity_type', 'timestamp', 
        'ip_address', 'description'
    ]
    
    list_filter = ['activity_type', 'timestamp']
    search_fields = [
        'user__email', 'user__first_name', 
        'user__last_name', 'description'
    ]
    
    readonly_fields = [
        'user', 'activity_type', 'description',
        'ip_address', 'user_agent', 'timestamp', 'metadata'
    ]
    
    ordering = ['-timestamp']
    
    def has_add_permission(self, request):
        """No permitir agregar actividades manualmente."""
        return False
    
    def has_change_permission(self, request, obj=None):
        """No permitir modificar actividades."""
        return False
