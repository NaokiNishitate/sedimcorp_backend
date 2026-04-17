"""
Configuración de la aplicación users.
"""

from django.apps import AppConfig


class UsersConfig(AppConfig):
    """
    Configuración de la aplicación de usuarios.
    """
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'users'
    verbose_name = 'Usuarios'
    
    def ready(self):
        import users.signals
