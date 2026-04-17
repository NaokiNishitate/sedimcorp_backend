"""
Configuración de URLs para el módulo de certificados.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'templates', views.CertificateTemplateViewSet)
router.register(r'certificates', views.CertificateViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('validate/', views.PublicCertificateValidationView.as_view(), name='certificate-validate'),
    path('my-certificates/', views.MyCertificatesView.as_view(), name='my-certificates'),
]
