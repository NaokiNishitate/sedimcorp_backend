"""
Configuración de URLs para el módulo de usuarios.
"""

from django.urls import path
from . import views

urlpatterns = [
    # Autenticación y registro
    path('register/', views.RegisterView.as_view(), name='user-register'),
    path('login/', views.LoginView.as_view(), name='user-login'),
    path('logout/', views.LogoutView.as_view(), name='user-logout'),
    path('me/', views.CurrentUserView.as_view(), name='user-me'),
    
    # Gestión de contraseñas
    path('change-password/', views.ChangePasswordView.as_view(), name='change-password'),
    path('reset-password/', views.PasswordResetRequestView.as_view(), name='password-reset-request'),
    path('reset-password/confirm/', views.PasswordResetConfirmView.as_view(), name='password-reset-confirm'),
    
    # CRUD de usuarios
    path('', views.UserListView.as_view(), name='user-list'),
    path('<uuid:pk>/', views.UserDetailView.as_view(), name='user-detail'),
    path('<uuid:pk>/activities/', views.UserActivityView.as_view(), name='user-activities'),
]
