"""
Configuración de la aplicación payments.
"""

from django.apps import AppConfig


class PaymentsConfig(AppConfig):
    """
    Configuración de la aplicación de pagos.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'payments'
    verbose_name = 'Pagos y Transacciones'
    
    def ready(self):
        import payments.signals
        