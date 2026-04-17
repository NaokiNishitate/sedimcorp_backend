"""
Configuración de URLs para el módulo de validación.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'accesses', views.CertificateAccessViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('verify/', views.CertificateValidationView.as_view(), name='certificate-verify'),
    path('stats/', views.ValidationStatsView.as_view(), name='validation-stats'),
]
