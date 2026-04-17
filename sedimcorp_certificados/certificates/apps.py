"""
Configuración de la aplicación certificates.
"""

from django.apps import AppConfig


class CertificatesConfig(AppConfig):
    """
    Configuración de la aplicación de certificados.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'certificates'
    verbose_name = 'Certificados Digitales'
    
    def ready(self):
        import certificates.signals
        