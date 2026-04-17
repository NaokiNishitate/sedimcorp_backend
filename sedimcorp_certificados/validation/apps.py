"""
Configuración de la aplicación validation.
"""

from django.apps import AppConfig


class ValidationConfig(AppConfig):
    """
    Configuración de la aplicación de validación.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'validation'
    verbose_name = 'Validación de Certificados'

    def ready(self):
        import validation.signals
