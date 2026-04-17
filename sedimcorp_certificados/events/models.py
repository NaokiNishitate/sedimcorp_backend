"""
Modelos para la gestión de eventos y cursos en SEDIMCORP.
Define cursos, módulos, inscripciones y seguimiento de participantes.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils import timezone
from django.conf import settings
import uuid


class Category(models.Model):
    """
    Categorías para clasificar los cursos (ej: Ingeniería Civil, Contabilidad, etc.)
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    name = models.CharField(
        max_length=100,
        unique=True,
        verbose_name='Nombre de categoría'
    )
    
    slug = models.SlugField(
        max_length=120,
        unique=True,
        verbose_name='Slug'
    )
    
    description = models.TextField(
        max_length=500,
        verbose_name='Descripción',
        blank=True,
        null=True
    )
    
    icon = models.CharField(
        max_length=50,
        verbose_name='Icono (clase CSS)',
        blank=True,
        null=True,
        help_text='Clase de icono de FontAwesome o similar'
    )
    
    image = models.ImageField(
        upload_to='categories/',
        verbose_name='Imagen representativa',
        blank=True,
        null=True
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='¿Activa?'
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Orden de visualización'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Categoría'
        verbose_name_plural = 'Categorías'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class Course(models.Model):
    """
    Modelo principal para cursos y eventos formativos.
    """
    
    # Niveles de dificultad
    DIFFICULTY_CHOICES = [
        ('BASIC', 'Básico'),
        ('INTERMEDIATE', 'Intermedio'),
        ('ADVANCED', 'Avanzado'),
        ('SPECIALIZED', 'Especializado'),
    ]
    
    # Modalidades del curso
    MODALITY_CHOICES = [
        ('ONLINE', 'En línea (síncrono)'),
        ('ONLINE_ASYNC', 'En línea (asíncrono)'),
        ('PRESENTIAL', 'Presencial'),
        ('MIXED', 'Mixto'),
    ]
    
    # Estados del curso
    STATUS_CHOICES = [
        ('DRAFT', 'Borrador'),
        ('PUBLISHED', 'Publicado'),
        ('IN_PROGRESS', 'En progreso'),
        ('COMPLETED', 'Finalizado'),
        ('CANCELLED', 'Cancelado'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    # Información básica
    code = models.CharField(
        max_length=20,
        unique=True,
        verbose_name='Código del curso',
        help_text='Código único para identificación interna'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='Título del curso'
    )
    
    slug = models.SlugField(
        max_length=250,
        unique=True,
        verbose_name='Slug'
    )
    
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='courses',
        verbose_name='Categoría'
    )
    
    description = models.TextField(
        max_length=2000,
        verbose_name='Descripción completa'
    )
    
    short_description = models.CharField(
        max_length=200,
        verbose_name='Descripción corta'
    )
    
    objectives = models.TextField(
        max_length=1500,
        verbose_name='Objetivos del curso'
    )
    
    requirements = models.TextField(
        max_length=1000,
        verbose_name='Requisitos previos',
        blank=True,
        null=True
    )
    
    target_audience = models.TextField(
        max_length=1000,
        verbose_name='Público objetivo',
        blank=True,
        null=True
    )
    
    # Imágenes y multimedia
    cover_image = models.ImageField(
        upload_to='courses/covers/',
        verbose_name='Imagen de portada'
    )
    
    thumbnail_image = models.ImageField(
        upload_to='courses/thumbnails/',
        verbose_name='Miniatura',
        blank=True,
        null=True
    )
    
    promotional_video = models.URLField(
        verbose_name='Video promocional',
        blank=True,
        null=True
    )
    
    # Configuración del curso
    difficulty = models.CharField(
        max_length=15,
        choices=DIFFICULTY_CHOICES,
        default='INTERMEDIATE',
        verbose_name='Nivel de dificultad'
    )
    
    modality = models.CharField(
        max_length=15,
        choices=MODALITY_CHOICES,
        default='ONLINE',
        verbose_name='Modalidad'
    )
    
    duration_hours = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Duración total (horas)'
    )
    
    duration_weeks = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Duración (semanas)'
    )
    
    hours_per_week = models.PositiveIntegerField(
        validators=[MinValueValidator(1)],
        verbose_name='Horas por semana',
        blank=True,
        null=True
    )
    
    # Capacidad y fechas
    max_participants = models.PositiveIntegerField(
        default=30,
        validators=[MinValueValidator(1)],
        verbose_name='Máximo de participantes'
    )
    
    min_participants = models.PositiveIntegerField(
        default=5,
        validators=[MinValueValidator(1)],
        verbose_name='Mínimo de participantes'
    )
    
    start_date = models.DateField(
        verbose_name='Fecha de inicio'
    )
    
    end_date = models.DateField(
        verbose_name='Fecha de fin'
    )
    
    enrollment_start = models.DateTimeField(
        verbose_name='Inicio de inscripciones'
    )
    
    enrollment_end = models.DateTimeField(
        verbose_name='Fin de inscripciones'
    )
    
    # Equipo y responsables
    coordinator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='coordinated_courses',
        verbose_name='Coordinador',
        limit_choices_to={'user_type__in': ['ADMIN', 'STAFF']}
    )
    
    instructors = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='instructed_courses',
        verbose_name='Instructores',
        limit_choices_to={'user_type': 'INSTRUCTOR'}
    )
    
    assistants = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name='assisted_courses',
        verbose_name='Asistentes',
        blank=True,
        limit_choices_to={'user_type': 'STAFF'}
    )
    
    # Precios y certificación
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio regular'
    )
    
    discount_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio con descuento',
        blank=True,
        null=True
    )
    
    early_bird_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Precio pronto pago',
        blank=True,
        null=True
    )
    
    early_bird_deadline = models.DateTimeField(
        verbose_name='Fecha límite pronto pago',
        blank=True,
        null=True
    )
    
    certificate_template = models.ForeignKey(
        'certificates.CertificateTemplate',
        on_delete=models.SET_NULL,
        related_name='courses',
        verbose_name='Plantilla de certificado',
        blank=True,
        null=True
    )
    
    certificate_text = models.TextField(
        max_length=1000,
        verbose_name='Texto del certificado',
        help_text='Texto personalizado que aparecerá en el certificado',
        blank=True,
        null=True
    )
    
    # Contenido curricular
    syllabus = models.JSONField(
        verbose_name='Plan de estudios',
        default=dict,
        blank=True,
        help_text='Estructura del contenido del curso en formato JSON'
    )
    
    learning_outcomes = models.JSONField(
        verbose_name='Resultados de aprendizaje',
        default=list,
        blank=True
    )
    
    # Metadatos y SEO
    meta_title = models.CharField(
        max_length=60,
        verbose_name='Título SEO',
        blank=True,
        null=True
    )
    
    meta_description = models.CharField(
        max_length=160,
        verbose_name='Descripción SEO',
        blank=True,
        null=True
    )
    
    meta_keywords = models.CharField(
        max_length=255,
        verbose_name='Palabras clave SEO',
        blank=True,
        null=True
    )
    
    # Estadísticas
    views_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Número de vistas'
    )
    
    enrollment_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Número de inscritos'
    )
    
    rating_avg = models.DecimalField(
        max_digits=3,
        decimal_places=2,
        default=0,
        verbose_name='Calificación promedio'
    )
    
    rating_count = models.PositiveIntegerField(
        default=0,
        verbose_name='Número de calificaciones'
    )
    
    # Estado y auditoría
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='DRAFT',
        verbose_name='Estado'
    )
    
    is_featured = models.BooleanField(
        default=False,
        verbose_name='¿Destacado?'
    )
    
    is_certifiable = models.BooleanField(
        default=True,
        verbose_name='¿Otorga certificado?'
    )
    
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='created_courses',
        verbose_name='Creado por'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    published_at = models.DateTimeField(
        verbose_name='Fecha de publicación',
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = 'Curso'
        verbose_name_plural = 'Cursos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['code', 'status']),
            models.Index(fields=['start_date', 'end_date']),
            models.Index(fields=['category', 'status']),
        ]
    
    def __str__(self):
        return f"{self.code} - {self.title}"
    
    def save(self, *args, **kwargs):
        """Override save para manejar fechas de publicación."""
        if self.status == 'PUBLISHED' and not self.published_at:
            self.published_at = timezone.now()
        super().save(*args, **kwargs)
    
    def is_enrollment_open(self):
        """Verifica si las inscripciones están abiertas."""
        now = timezone.now()
        return self.enrollment_start <= now <= self.enrollment_end
    
    def has_available_slots(self):
        """Verifica si hay cupos disponibles."""
        return self.enrollment_count < self.max_participants
    
    def get_current_price(self):
        """Retorna el precio actual aplicable."""
        now = timezone.now()
        
        # Verificar pronto pago
        if self.early_bird_price and self.early_bird_deadline:
            if now <= self.early_bird_deadline:
                return self.early_bird_price
        
        # Verificar descuento
        if self.discount_price:
            return self.discount_price
        
        return self.price
    
    def update_rating(self):
        """Actualiza el rating promedio basado en encuestas."""
        from django.db.models import Avg
        avg = self.enrollments.filter(
            survey_completed=True,
            rating__isnull=False
        ).aggregate(Avg('rating'))['rating__avg']
        
        if avg:
            self.rating_avg = round(avg, 2)
            self.rating_count = self.enrollments.filter(
                survey_completed=True,
                rating__isnull=False
            ).count()
            self.save(update_fields=['rating_avg', 'rating_count'])


class CourseModule(models.Model):
    """
    Módulos o unidades que componen un curso.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='modules',
        verbose_name='Curso'
    )
    
    title = models.CharField(
        max_length=200,
        verbose_name='Título del módulo'
    )
    
    description = models.TextField(
        max_length=1000,
        verbose_name='Descripción',
        blank=True,
        null=True
    )
    
    order = models.PositiveIntegerField(
        verbose_name='Orden'
    )
    
    duration_hours = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        verbose_name='Duración (horas)',
        validators=[MinValueValidator(0.5)]
    )
    
    objectives = models.JSONField(
        verbose_name='Objetivos del módulo',
        default=list,
        blank=True
    )
    
    content = models.JSONField(
        verbose_name='Contenido detallado',
        default=dict,
        blank=True
    )
    
    resources = models.JSONField(
        verbose_name='Recursos adicionales',
        default=list,
        blank=True
    )
    
    is_visible = models.BooleanField(
        default=True,
        verbose_name='¿Visible?'
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Módulo del curso'
        verbose_name_plural = 'Módulos del curso'
        ordering = ['course', 'order']
        unique_together = ['course', 'order']
    
    def __str__(self):
        return f"{self.course.code} - {self.title}"


class Enrollment(models.Model):
    """
    Inscripciones de participantes a cursos.
    """
    
    # Estados de inscripción
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('CONFIRMED', 'Confirmada'),
        ('IN_PROGRESS', 'En progreso'),
        ('COMPLETED', 'Completada'),
        ('CERTIFIED', 'Certificado'),
        ('CANCELLED', 'Cancelada'),
        ('REFUNDED', 'Reembolsada'),
    ]
    
    # Métodos de pago
    PAYMENT_METHOD_CHOICES = [
        ('YAPE', 'Yape'),
        ('PLIN', 'Plin'),
        ('IZIPAY', 'Izipay'),
        ('TRANSFER', 'Transferencia bancaria'),
        ('CASH', 'Efectivo'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    enrollment_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código de inscripción'
    )
    
    course = models.ForeignKey(
        Course,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name='Curso'
    )
    
    participant = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='enrollments',
        verbose_name='Participante',
        limit_choices_to={'user_type': 'PARTICIPANT'}
    )
    
    # Información de inscripción
    enrollment_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de inscripción'
    )
    
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='Estado'
    )
    
    # Información de pago
    payment_method = models.CharField(
        max_length=20,
        choices=PAYMENT_METHOD_CHOICES,
        verbose_name='Método de pago',
        blank=True,
        null=True
    )
    
    payment_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto pagado',
        validators=[MinValueValidator(0)]
    )
    
    payment_date = models.DateTimeField(
        verbose_name='Fecha de pago',
        blank=True,
        null=True
    )
    
    payment_reference = models.CharField(
        max_length=100,
        verbose_name='Referencia de pago',
        blank=True,
        null=True
    )
    
    payment_confirmed = models.BooleanField(
        default=False,
        verbose_name='Pago confirmado'
    )
    
    payment_confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='enrollment_confirmations',
        verbose_name='Confirmado por',
        blank=True,
        null=True
    )
    
    # Información académica
    attendance_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Porcentaje de asistencia',
        validators=[MinValueValidator(0), MaxValueValidator(100)]
    )
    
    final_grade = models.DecimalField(
        max_digits=4,
        decimal_places=2,
        verbose_name='Nota final',
        blank=True,
        null=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)]
    )
    
    is_approved = models.BooleanField(
        default=False,
        verbose_name='¿Aprobado?'
    )
    
    completion_date = models.DateTimeField(
        verbose_name='Fecha de finalización',
        blank=True,
        null=True
    )
    
    # Encuesta de satisfacción
    survey_completed = models.BooleanField(
        default=False,
        verbose_name='Encuesta completada'
    )
    
    rating = models.PositiveIntegerField(
        verbose_name='Calificación',
        blank=True,
        null=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    
    feedback = models.TextField(
        max_length=1000,
        verbose_name='Comentarios',
        blank=True,
        null=True
    )
    
    survey_date = models.DateTimeField(
        verbose_name='Fecha de encuesta',
        blank=True,
        null=True
    )
    
    # Auditoría
    cancelled_at = models.DateTimeField(
        verbose_name='Fecha de cancelación',
        blank=True,
        null=True
    )
    
    cancelled_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='cancelled_enrollments',
        verbose_name='Cancelado por',
        blank=True,
        null=True
    )
    
    cancellation_reason = models.TextField(
        max_length=500,
        verbose_name='Motivo de cancelación',
        blank=True,
        null=True
    )
    
    notes = models.TextField(
        max_length=500,
        verbose_name='Notas adicionales',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    class Meta:
        verbose_name = 'Inscripción'
        verbose_name_plural = 'Inscripciones'
        ordering = ['-enrollment_date']
        unique_together = ['course', 'participant']  # Un participante por curso
        indexes = [
            models.Index(fields=['enrollment_code', 'status']),
            models.Index(fields=['course', 'status']),
            models.Index(fields=['participant', 'status']),
        ]
    
    def __str__(self):
        return f"{self.enrollment_code} - {self.participant.get_full_name()} - {self.course.title}"
    
    def save(self, *args, **kwargs):
        """Override save para generar código único."""
        if not self.enrollment_code:
            self.enrollment_code = self.generate_enrollment_code()
        super().save(*args, **kwargs)
    
    def generate_enrollment_code(self):
        """Genera un código único para la inscripción."""
        import hashlib
        import time
        
        base = f"{self.participant.id}{self.course.id}{time.time()}"
        hash_object = hashlib.sha256(base.encode())
        return f"EN-{hash_object.hexdigest()[:10].upper()}"
    
    def mark_completed(self, approved=True):
        """Marca la inscripción como completada."""
        self.status = 'COMPLETED' if approved else 'CANCELLED'
        self.is_approved = approved
        self.completion_date = timezone.now()
        self.save()
    
    def can_generate_certificate(self):
        """Verifica si se puede generar certificado."""
        return (
            self.status == 'COMPLETED' and
            self.is_approved and
            self.course.is_certifiable
        )


class Attendance(models.Model):
    """
    Registro de asistencia de participantes a sesiones.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    enrollment = models.ForeignKey(
        Enrollment,
        on_delete=models.CASCADE,
        related_name='attendances',
        verbose_name='Inscripción'
    )
    
    session_date = models.DateField(
        verbose_name='Fecha de sesión'
    )
    
    session_topic = models.CharField(
        max_length=200,
        verbose_name='Tema de la sesión'
    )
    
    check_in_time = models.DateTimeField(
        verbose_name='Hora de entrada'
    )
    
    check_out_time = models.DateTimeField(
        verbose_name='Hora de salida',
        blank=True,
        null=True
    )
    
    duration_minutes = models.PositiveIntegerField(
        verbose_name='Duración (minutos)',
        validators=[MinValueValidator(1)],
        blank=True,
        null=True
    )
    
    is_present = models.BooleanField(
        default=True,
        verbose_name='¿Presente?'
    )
    
    is_late = models.BooleanField(
        default=False,
        verbose_name='¿Llegó tarde?'
    )
    
    late_minutes = models.PositiveIntegerField(
        verbose_name='Minutos de tardanza',
        default=0
    )
    
    registered_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='registered_attendances',
        verbose_name='Registrado por'
    )
    
    notes = models.TextField(
        max_length=500,
        verbose_name='Notas',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de registro'
    )
    
    class Meta:
        verbose_name = 'Asistencia'
        verbose_name_plural = 'Asistencias'
        ordering = ['-session_date', '-check_in_time']
        unique_together = ['enrollment', 'session_date']
    
    def __str__(self):
        return f"{self.enrollment.participant.get_full_name()} - {self.session_date}"
    
    def save(self, *args, **kwargs):
        """Calcula duración automáticamente."""
        if self.check_in_time and self.check_out_time:
            delta = self.check_out_time - self.check_in_time
            self.duration_minutes = int(delta.total_seconds() / 60)
        super().save(*args, **kwargs)


class Schedule(models.Model):
    """
    Horarios de sesiones para cursos.
    """
    
    DAY_CHOICES = [
        (1, 'Lunes'),
        (2, 'Martes'),
        (3, 'Miércoles'),
        (4, 'Jueves'),
        (5, 'Viernes'),
        (6, 'Sábado'),
        (7, 'Domingo'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='schedules',
        verbose_name='Curso'
    )
    
    day_of_week = models.PositiveIntegerField(
        choices=DAY_CHOICES,
        verbose_name='Día de la semana'
    )
    
    start_time = models.TimeField(
        verbose_name='Hora de inicio'
    )
    
    end_time = models.TimeField(
        verbose_name='Hora de fin'
    )
    
    room = models.CharField(
        max_length=50,
        verbose_name='Salón / Plataforma',
        blank=True,
        null=True
    )
    
    meeting_link = models.URLField(
        verbose_name='Enlace de reunión',
        blank=True,
        null=True
    )
    
    is_active = models.BooleanField(
        default=True,
        verbose_name='¿Activo?'
    )
    
    class Meta:
        verbose_name = 'Horario'
        verbose_name_plural = 'Horarios'
        ordering = ['day_of_week', 'start_time']
        unique_together = ['course', 'day_of_week', 'start_time']
    
    def __str__(self):
        day = dict(self.DAY_CHOICES).get(self.day_of_week)
        return f"{self.course.code} - {day} {self.start_time}-{self.end_time}"
