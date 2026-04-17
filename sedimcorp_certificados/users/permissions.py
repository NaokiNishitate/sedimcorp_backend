"""
Permisos personalizados para el módulo de usuarios.
Definen reglas de acceso específicas para diferentes tipos de usuarios.
"""

from rest_framework import permissions


class IsAdmin(permissions.BasePermission):
    """
    Permiso que solo concede acceso a administradores.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.user_type == 'ADMIN' or request.user.is_superuser)
        )


class IsStaffOrAdmin(permissions.BasePermission):
    """
    Permiso que concede acceso a staff y administradores.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            (request.user.user_type in ['ADMIN', 'STAFF'] or request.user.is_staff)
        )


class IsInstructor(permissions.BasePermission):
    """
    Permiso que concede acceso solo a instructores.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'INSTRUCTOR'
        )


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    Permiso que concede acceso si el usuario es el propietario del recurso o administrador.
    """
    
    def has_object_permission(self, request, view, obj):
        # Verificar si el usuario es administrador
        if request.user.user_type == 'ADMIN' or request.user.is_superuser:
            return True
        
        # Verificar si el usuario es el propietario
        if hasattr(obj, 'user'):
            return obj.user == request.user
        elif hasattr(obj, 'id'):
            return obj == request.user
        
        return False


class IsParticipant(permissions.BasePermission):
    """
    Permiso que concede acceso solo a participantes.
    """
    
    def has_permission(self, request, view):
        return bool(
            request.user and 
            request.user.is_authenticated and 
            request.user.user_type == 'PARTICIPANT'
        )


class CanManageUsers(permissions.BasePermission):
    """
    Permiso para gestionar usuarios (crear, modificar, eliminar).
    """
    
    def has_permission(self, request, view):
        # Solo administradores y staff pueden gestionar usuarios
        if not request.user.is_authenticated:
            return False
        
        if request.user.user_type in ['ADMIN', 'STAFF']:
            return True
        
        # Los usuarios pueden crear su propia cuenta
        if request.method == 'POST' and view.action == 'create':
            return True
        
        return False
    
    def has_object_permission(self, request, view, obj):
        # Los administradores pueden gestionar cualquier usuario
        if request.user.user_type == 'ADMIN':
            return True
        
        # Los usuarios pueden gestionar su propio perfil
        return obj == request.user
