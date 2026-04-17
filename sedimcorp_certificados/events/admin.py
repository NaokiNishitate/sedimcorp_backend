"""
Configuración del panel de administración para el módulo de eventos.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import Category, Course, CourseModule, Enrollment, Attendance, Schedule


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    """
    Configuración para categorías en el admin.
    """
    
    list_display = ['name', 'slug', 'order', 'is_active', 'courses_count']
    list_filter = ['is_active']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ('name',)}
    list_editable = ['order', 'is_active']
    
    def courses_count(self, obj):
        """Retorna el número de cursos en la categoría."""
        return obj.courses.count()
    courses_count.short_description = 'Cursos'


class CourseModuleInline(admin.TabularInline):
    """Inline para módulos en el admin de cursos."""
    model = CourseModule
    extra = 1
    fields = ['title', 'order', 'duration_hours', 'is_visible']


class ScheduleInline(admin.TabularInline):
    """Inline para horarios en el admin de cursos."""
    model = Schedule
    extra = 1
    fields = ['day_of_week', 'start_time', 'end_time', 'room', 'is_active']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    """
    Configuración para cursos en el admin.
    """
    
    list_display = [
        'code', 'title', 'category', 'status',
        'start_date', 'end_date', 'enrollment_count',
        'price', 'is_featured'
    ]
    
    list_filter = [
        'status', 'category', 'difficulty', 'modality',
        'is_featured', 'is_certifiable', 'start_date'
    ]
    
    search_fields = ['code', 'title', 'description']
    prepopulated_fields = {'slug': ('title',)}
    
    fieldsets = (
        ('Información Básica', {
            'fields': (
                'code', 'title', 'slug', 'category',
                'description', 'short_description',
                'objectives', 'requirements', 'target_audience'
            )
        }),
        ('Multimedia', {
            'fields': (
                'cover_image', 'thumbnail_image',
                'promotional_video'
            ),
            'classes': ('collapse',)
        }),
        ('Configuración Académica', {
            'fields': (
                'difficulty', 'modality', 'duration_hours',
                'duration_weeks', 'hours_per_week'
            )
        }),
        ('Fechas y Capacidad', {
            'fields': (
                'start_date', 'end_date',
                'enrollment_start', 'enrollment_end',
                'max_participants', 'min_participants'
            )
        }),
        ('Equipo', {
            'fields': (
                'coordinator', 'instructors', 'assistants'
            ),
            'classes': ('collapse',)
        }),
        ('Precios', {
            'fields': (
                'price', 'discount_price',
                'early_bird_price', 'early_bird_deadline'
            ),
            'classes': ('collapse',)
        }),
        ('Certificación', {
            'fields': (
                'certificate_template', 'certificate_text',
                'is_certifiable'
            ),
            'classes': ('collapse',)
        }),
        ('SEO', {
            'fields': (
                'meta_title', 'meta_description',
                'meta_keywords'
            ),
            'classes': ('collapse',)
        }),
        ('Estadísticas', {
            'fields': (
                'views_count', 'enrollment_count',
                'rating_avg', 'rating_count'
            ),
            'classes': ('collapse',)
        }),
        ('Estado', {
            'fields': (
                'status', 'is_featured', 'published_at'
            )
        }),
    )
    
    inlines = [CourseModuleInline, ScheduleInline]
    
    readonly_fields = [
        'views_count', 'enrollment_count',
        'rating_avg', 'rating_count', 'published_at'
    ]
    
    filter_horizontal = ['instructors', 'assistants']
    
    actions = ['publish_courses', 'feature_courses']
    
    def publish_courses(self, request, queryset):
        """Publica los cursos seleccionados."""
        updated = queryset.update(status='PUBLISHED')
        self.message_user(request, f'{updated} cursos publicados.')
    publish_courses.short_description = 'Publicar cursos seleccionados'
    
    def feature_courses(self, request, queryset):
        """Marca los cursos como destacados."""
        updated = queryset.update(is_featured=True)
        self.message_user(request, f'{updated} cursos marcados como destacados.')
    feature_courses.short_description = 'Marcar como destacados'


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    """
    Configuración para inscripciones en el admin.
    """
    
    list_display = [
        'enrollment_code', 'course', 'participant',
        'status', 'payment_confirmed', 'is_approved',
        'enrollment_date'
    ]
    
    list_filter = [
        'status', 'payment_confirmed', 'is_approved',
        'payment_method', 'enrollment_date'
    ]
    
    search_fields = [
        'enrollment_code', 'participant__email',
        'participant__first_name', 'participant__last_name',
        'course__title'
    ]
    
    readonly_fields = [
        'enrollment_code', 'enrollment_date',
        'created_at', 'updated_at'
    ]
    
    fieldsets = (
        ('Información de Inscripción', {
            'fields': (
                'enrollment_code', 'course', 'participant',
                'status', 'enrollment_date'
            )
        }),
        ('Información de Pago', {
            'fields': (
                'payment_method', 'payment_amount',
                'payment_date', 'payment_reference',
                'payment_confirmed', 'payment_confirmed_by'
            )
        }),
        ('Información Académica', {
            'fields': (
                'attendance_percentage', 'final_grade',
                'is_approved', 'completion_date'
            )
        }),
        ('Encuesta', {
            'fields': (
                'survey_completed', 'rating',
                'feedback', 'survey_date'
            )
        }),
        ('Cancelación', {
            'fields': (
                'cancelled_at', 'cancelled_by',
                'cancellation_reason'
            ),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': (
                'created_at', 'updated_at', 'notes'
            ),
            'classes': ('collapse',)
        }),
    )
    
    actions = ['confirm_payments', 'mark_completed']
    
    def confirm_payments(self, request, queryset):
        """Confirma los pagos de las inscripciones."""
        updated = queryset.update(
            payment_confirmed=True,
            payment_confirmed_by=request.user,
            payment_date=timezone.now()
        )
        self.message_user(request, f'{updated} pagos confirmados.')
    confirm_payments.short_description = 'Confirmar pagos seleccionados'
    
    def mark_completed(self, request, queryset):
        """Marca las inscripciones como completadas."""
        updated = queryset.update(
            status='COMPLETED',
            completion_date=timezone.now()
        )
        self.message_user(request, f'{updated} inscripciones completadas.')
    mark_completed.short_description = 'Marcar como completadas'


@admin.register(Attendance)
class AttendanceAdmin(admin.ModelAdmin):
    """
    Configuración para asistencias en el admin.
    """
    
    list_display = [
        'enrollment', 'session_date', 'session_topic',
        'is_present', 'is_late', 'duration_minutes'
    ]
    
    list_filter = ['is_present', 'is_late', 'session_date']
    search_fields = [
        'enrollment__participant__email',
        'enrollment__participant__first_name',
        'session_topic'
    ]
    
    readonly_fields = ['duration_minutes', 'created_at']
