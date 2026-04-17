"""
Configuración de URLs para el módulo de eventos.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'categories', views.CategoryViewSet)
router.register(r'courses', views.CourseViewSet)
router.register(r'enrollments', views.EnrollmentViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('public/enroll/', views.PublicEnrollmentView.as_view(), name='public-enroll'),
]
