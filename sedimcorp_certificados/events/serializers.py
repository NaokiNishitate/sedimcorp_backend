"""
Serializadores para el módulo de eventos y cursos.
"""

from rest_framework import serializers
from django.utils import timezone
from django.db import transaction
from .models import Category, Course, CourseModule, Enrollment, Attendance, Schedule
from users.serializers import UserSerializer
from users.models import User
import re


class CategorySerializer(serializers.ModelSerializer):
    """
    Serializador para categorías de cursos.
    """
    
    courses_count = serializers.SerializerMethodField()
    
    class Meta:
        model = Category
        fields = [
            'id', 'name', 'slug', 'description', 'icon',
            'image', 'is_active', 'order', 'courses_count'
        ]
        read_only_fields = ['id', 'slug']
    
    def get_courses_count(self, obj):
        """Retorna el número de cursos activos en la categoría."""
        return obj.courses.filter(status='PUBLISHED').count()
    
    def validate_name(self, value):
        """Valida que el nombre tenga un formato adecuado."""
        if len(value) < 3:
            raise serializers.ValidationError('El nombre debe tener al menos 3 caracteres')
        return value


class CourseModuleSerializer(serializers.ModelSerializer):
    """
    Serializador para módulos de curso.
    """
    
    class Meta:
        model = CourseModule
        fields = [
            'id', 'title', 'description', 'order',
            'duration_hours', 'objectives', 'content',
            'resources', 'is_visible'
        ]
        read_only_fields = ['id']


class ScheduleSerializer(serializers.ModelSerializer):
    """
    Serializador para horarios de curso.
    """
    
    day_display = serializers.CharField(source='get_day_of_week_display', read_only=True)
    
    class Meta:
        model = Schedule
        fields = [
            'id', 'day_of_week', 'day_display', 'start_time',
            'end_time', 'room', 'meeting_link', 'is_active'
        ]
        read_only_fields = ['id']
    
    def validate(self, data):
        """Valida que la hora de fin sea posterior a la de inicio."""
        if data['start_time'] >= data['end_time']:
            raise serializers.ValidationError(
                'La hora de fin debe ser posterior a la hora de inicio'
            )
        return data


class CourseListSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para listados de cursos.
    """
    
    category_name = serializers.CharField(source='category.name', read_only=True)
    instructors_names = serializers.SerializerMethodField()
    current_price = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = [
            'id', 'code', 'title', 'slug', 'category_name',
            'short_description', 'cover_image', 'thumbnail_image',
            'difficulty', 'modality', 'duration_hours', 'duration_weeks',
            'start_date', 'end_date', 'current_price', 'status',
            'instructors_names', 'enrollment_count', 'rating_avg',
            'is_featured', 'is_enrollment_open'
        ]
    
    def get_instructors_names(self, obj):
        """Retorna los nombres de los instructores."""
        return [f"{i.get_full_name()}" for i in obj.instructors.all()]
    
    def get_current_price(self, obj):
        """Retorna el precio actual."""
        return float(obj.get_current_price())


class CourseDetailSerializer(serializers.ModelSerializer):
    """
    Serializador detallado para cursos.
    """
    
    category = CategorySerializer(read_only=True)
    category_id = serializers.PrimaryKeyRelatedField(
        queryset=Category.objects.all(),
        source='category',
        write_only=True
    )
    
    modules = CourseModuleSerializer(many=True, read_only=True)
    schedules = ScheduleSerializer(many=True, read_only=True)
    
    coordinator = UserSerializer(read_only=True)
    coordinator_id = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(user_type__in=['ADMIN', 'STAFF']),
        source='coordinator',
        write_only=True
    )
    
    instructors = UserSerializer(many=True, read_only=True)
    instructor_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(user_type='INSTRUCTOR'),
        source='instructors',
        many=True,
        write_only=True
    )
    
    assistants = UserSerializer(many=True, read_only=True)
    assistant_ids = serializers.PrimaryKeyRelatedField(
        queryset=User.objects.filter(user_type='STAFF'),
        source='assistants',
        many=True,
        write_only=True,
        required=False
    )
    
    created_by = UserSerializer(read_only=True)
    current_price = serializers.SerializerMethodField()
    available_slots = serializers.SerializerMethodField()
    
    class Meta:
        model = Course
        fields = '__all__'
        read_only_fields = [
            'id', 'code', 'slug', 'views_count', 'enrollment_count',
            'rating_avg', 'rating_count', 'created_at', 'updated_at',
            'published_at', 'created_by'
        ]
    
    def get_current_price(self, obj):
        """Retorna el precio actual."""
        return float(obj.get_current_price())
    
    def get_available_slots(self, obj):
        """Retorna los cupos disponibles."""
        return obj.max_participants - obj.enrollment_count
    
    def validate(self, data):
        """Validaciones cruzadas para fechas."""
        # Validar fechas del curso
        if 'start_date' in data and 'end_date' in data:
            if data['start_date'] >= data['end_date']:
                raise serializers.ValidationError(
                    'La fecha de fin debe ser posterior a la fecha de inicio'
                )
        
        # Validar fechas de inscripción
        if 'enrollment_start' in data and 'enrollment_end' in data:
            if data['enrollment_start'] >= data['enrollment_end']:
                raise serializers.ValidationError(
                    'La fecha de fin de inscripción debe ser posterior a la fecha de inicio'
                )
        
        return data


class EnrollmentSerializer(serializers.ModelSerializer):
    """
    Serializador para inscripciones.
    """
    
    course_title = serializers.CharField(source='course.title', read_only=True)
    participant_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = [
            'id', 'enrollment_code', 'course', 'course_title',
            'participant', 'participant_name', 'enrollment_date',
            'status', 'payment_method', 'payment_amount',
            'payment_date', 'payment_reference', 'payment_confirmed',
            'attendance_percentage', 'final_grade', 'is_approved',
            'completion_date', 'rating', 'feedback'
        ]
        read_only_fields = [
            'id', 'enrollment_code', 'enrollment_date',
            'payment_confirmed', 'attendance_percentage',
            'completion_date'
        ]
    
    def get_participant_name(self, obj):
        """Retorna el nombre completo del participante."""
        return obj.participant.get_full_name()
    
    def validate(self, data):
        """Validaciones para inscripciones."""
        course = data.get('course')
        participant = data.get('participant')
        
        # Verificar si ya existe inscripción
        if Enrollment.objects.filter(
            course=course,
            participant=participant
        ).exclude(status='CANCELLED').exists():
            raise serializers.ValidationError(
                'El participante ya está inscrito en este curso'
            )
        
        # Verificar cupos disponibles
        if course.enrollment_count >= course.max_participants:
            raise serializers.ValidationError(
                'El curso ha alcanzado el máximo de participantes'
            )
        
        return data
    
    @transaction.atomic
    def create(self, validated_data):
        """Crea una nueva inscripción."""
        enrollment = Enrollment.objects.create(**validated_data)
        
        # Incrementar contador de inscritos
        course = validated_data['course']
        course.enrollment_count += 1
        course.save(update_fields=['enrollment_count'])
        
        return enrollment


class EnrollmentDetailSerializer(serializers.ModelSerializer):
    """
    Serializador detallado para inscripciones.
    """
    
    course = CourseListSerializer(read_only=True)
    participant = UserSerializer(read_only=True)
    attendances = serializers.SerializerMethodField()
    
    class Meta:
        model = Enrollment
        fields = '__all__'
    
    def get_attendances(self, obj):
        """Retorna las asistencias del participante."""
        attendances = obj.attendances.all()
        return AttendanceSerializer(attendances, many=True).data


class AttendanceSerializer(serializers.ModelSerializer):
    """
    Serializador para asistencias.
    """
    
    participant_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Attendance
        fields = [
            'id', 'enrollment', 'participant_name', 'session_date',
            'session_topic', 'check_in_time', 'check_out_time',
            'duration_minutes', 'is_present', 'is_late',
            'late_minutes', 'notes', 'created_at'
        ]
        read_only_fields = ['id', 'duration_minutes', 'created_at']
    
    def get_participant_name(self, obj):
        """Retorna el nombre del participante."""
        return obj.enrollment.participant.get_full_name()


class EnrollmentBulkCreateSerializer(serializers.Serializer):
    """
    Serializador para creación masiva de inscripciones.
    """
    
    course_id = serializers.UUIDField()
    participant_ids = serializers.ListField(
        child=serializers.UUIDField()
    )
    payment_method = serializers.ChoiceField(
        choices=Enrollment.PAYMENT_METHOD_CHOICES
    )
    payment_amount = serializers.DecimalField(max_digits=10, decimal_places=2)
    
    def validate(self, data):
        """Valida los datos para inscripción masiva."""
        try:
            course = Course.objects.get(id=data['course_id'])
        except Course.DoesNotExist:
            raise serializers.ValidationError('Curso no encontrado')
        
        # Verificar cupos
        if course.enrollment_count + len(data['participant_ids']) > course.max_participants:
            raise serializers.ValidationError(
                f'No hay suficientes cupos. Cupos disponibles: {course.max_participants - course.enrollment_count}'
            )
        
        # Verificar participantes
        participants = User.objects.filter(
            id__in=data['participant_ids'],
            user_type='PARTICIPANT',
            is_active=True
        )
        
        if participants.count() != len(data['participant_ids']):
            raise serializers.ValidationError('Algunos participantes no son válidos')
        
        # Guardar objetos para uso posterior
        data['course'] = course
        data['participants'] = participants
        
        return data


class CourseRatingSerializer(serializers.Serializer):
    """
    Serializador para calificar un curso.
    """
    
    rating = serializers.IntegerField(
        min_value=1,
        max_value=5,
        required=True
    )
    
    feedback = serializers.CharField(
        max_length=1000,
        required=False,
        allow_blank=True
    )
    
    def validate(self, data):
        """Valida que el usuario esté inscrito en el curso."""
        enrollment = self.context.get('enrollment')
        if not enrollment:
            raise serializers.ValidationError('Inscripción no encontrada')
        
        if enrollment.survey_completed:
            raise serializers.ValidationError('Ya has calificado este curso')
        
        return data
