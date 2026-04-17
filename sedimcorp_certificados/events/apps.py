"""
Configuración de la aplicación events.
"""

from django.apps import AppConfig


class EventsConfig(AppConfig):
    """
    Configuración de la aplicación de eventos y cursos.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'events'
    verbose_name = 'Eventos y Cursos'
    
    def ready(self):
        import events.signals
