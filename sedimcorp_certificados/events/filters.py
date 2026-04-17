"""
Filtros personalizados para el módulo de cursos.
"""

import django_filters
from django.db import models
from .models import Course


class CourseFilter(django_filters.FilterSet):
    """
    Filtros avanzados para búsqueda de cursos.
    """
    
    # Filtros por rango de precios
    min_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr='gte',
        label='Precio mínimo'
    )
    
    max_price = django_filters.NumberFilter(
        field_name="price",
        lookup_expr='lte',
        label='Precio máximo'
    )
    
    # Filtros por fechas
    start_after = django_filters.DateFilter(
        field_name="start_date",
        lookup_expr='gte',
        label='Inicia después de'
    )
    
    start_before = django_filters.DateFilter(
        field_name="start_date",
        lookup_expr='lte',
        label='Inicia antes de'
    )
    
    # Filtro por categoría (slug)
    category = django_filters.CharFilter(
        field_name="category__slug",
        lookup_expr='exact',
        label='Categoría'
    )
    
    # Filtros booleanos
    is_featured = django_filters.BooleanFilter(
        field_name="is_featured",
        label='Destacados'
    )
    
    is_certifiable = django_filters.BooleanFilter(
        field_name="is_certifiable",
        label='Otorga certificado'
    )
    
    # Filtros de texto para búsqueda avanzada
    search = django_filters.CharFilter(
        method='filter_search',
        label='Búsqueda general'
    )
    
    # Filtro por modalidad
    modality = django_filters.MultipleChoiceFilter(
        choices=Course.MODALITY_CHOICES,
        label='Modalidad'
    )
    
    # Filtro por dificultad
    difficulty = django_filters.MultipleChoiceFilter(
        choices=Course.DIFFICULTY_CHOICES,
        label='Dificultad'
    )
    
    # Filtro por disponibilidad
    has_available_slots = django_filters.BooleanFilter(
        method='filter_available_slots',
        label='Con cupos disponibles'
    )
    
    class Meta:
        model = Course
        fields = {
            'status': ['exact'],
            'category': ['exact'],
            'difficulty': ['exact'],
            'modality': ['exact'],
            'duration_hours': ['gte', 'lte'],
            'duration_weeks': ['gte', 'lte'],
        }
    
    def filter_search(self, queryset, name, value):
        """
        Búsqueda en múltiples campos.
        """
        return queryset.filter(
            models.Q(title__icontains=value) |
            models.Q(description__icontains=value) |
            models.Q(short_description__icontains=value) |
            models.Q(code__icontains=value) |
            models.Q(category__name__icontains=value)
        ).distinct()
    
    def filter_available_slots(self, queryset, name, value):
        """
        Filtra cursos con cupos disponibles.
        """
        if value:
            return queryset.filter(
                enrollment_count__lt=models.F('max_participants')
            )
        return queryset
