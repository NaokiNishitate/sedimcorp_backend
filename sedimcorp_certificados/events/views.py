"""
Vistas para el módulo de eventos y cursos.
"""

from rest_framework import generics, permissions, status, viewsets, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django_filters.rest_framework import DjangoFilterBackend
import django_filters

from .models import Category, Course, CourseModule, Enrollment, Attendance, Schedule
from .serializers import (
    CategorySerializer, CourseListSerializer, CourseDetailSerializer,
    CourseModuleSerializer, EnrollmentSerializer, EnrollmentDetailSerializer,
    AttendanceSerializer, ScheduleSerializer, EnrollmentBulkCreateSerializer,
    CourseRatingSerializer
)
from .filters import CourseFilter
from users.permissions import IsAdmin, IsStaffOrAdmin, IsInstructor
from utils.helpers import paginate_queryset


class CategoryViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar categorías de cursos.
    """
    
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsStaffOrAdmin]
    lookup_field = 'slug'
    filterset_fields = ['is_active']
    search_fields = ['name', 'description']
    ordering_fields = ['order', 'name', 'created_at']
    
    def get_permissions(self):
        """Permisos según la acción."""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsAdmin]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Personaliza el queryset según el usuario."""
        queryset = Category.objects.all()
        
        # Usuarios no autenticados solo ven categorías activas
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=True, methods=['get'])
    def courses(self, request, slug=None):
        """Retorna los cursos de una categoría."""
        category = self.get_object()
        courses = category.courses.filter(status='PUBLISHED')
        
        # Paginación
        page = paginate_queryset(request, courses, CourseListSerializer)
        if page is not None:
            return page
        
        serializer = CourseListSerializer(courses, many=True, context={'request': request})
        return Response(serializer.data)


class CourseViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar cursos.
    """
    
    queryset = Course.objects.select_related(
        'category', 'coordinator', 'created_by'
    ).prefetch_related(
        'instructors', 'assistants', 'modules', 'schedules'
    )
    permission_classes = [IsStaffOrAdmin]
    lookup_field = 'slug'
    filterset_class = CourseFilter
    search_fields = ['title', 'code', 'description', 'short_description']
    ordering_fields = ['created_at', 'start_date', 'price', 'rating_avg']
    
    def get_serializer_class(self):
        """Retorna el serializador según la acción."""
        if self.action == 'list':
            return CourseListSerializer
        return CourseDetailSerializer
    
    def get_permissions(self):
        """Permisos según la acción."""
        if self.action in ['list', 'retrieve']:
            permission_classes = [permissions.AllowAny]
        else:
            permission_classes = [IsStaffOrAdmin]
        return [permission() for permission in permission_classes]
    
    def get_queryset(self):
        """Personaliza el queryset según el usuario."""
        queryset = super().get_queryset()
        
        # Usuarios no autenticados solo ven cursos publicados
        if not self.request.user.is_authenticated:
            queryset = queryset.filter(status='PUBLISHED')
        
        # Instructores ven cursos que dictan
        elif self.request.user.user_type == 'INSTRUCTOR':
            queryset = queryset.filter(
                Q(instructors=self.request.user) |
                Q(status='PUBLISHED')
            ).distinct()
        
        return queryset
    
    def perform_create(self, serializer):
        """Guarda el usuario que crea el curso."""
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def enroll(self, request, slug=None):
        """
        Inscribe a un participante en el curso.
        """
        course = self.get_object()
        
        # Verificar si el usuario es participante
        if request.user.user_type != 'PARTICIPANT':
            return Response(
                {'error': 'Solo los participantes pueden inscribirse'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Verificar inscripciones abiertas
        if not course.is_enrollment_open():
            return Response(
                {'error': 'Las inscripciones no están abiertas'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Verificar cupos
        if not course.has_available_slots():
            return Response(
                {'error': 'No hay cupos disponibles'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Crear inscripción
        enrollment_data = {
            'course': course.id,
            'participant': request.user.id,
            'payment_amount': course.get_current_price(),
            'status': 'PENDING'
        }
        
        serializer = EnrollmentSerializer(
            data=enrollment_data,
            context={'request': request}
        )
        
        if serializer.is_valid():
            enrollment = serializer.save()
            
            return Response({
                'message': 'Inscripción creada exitosamente',
                'enrollment': EnrollmentSerializer(enrollment).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'], permission_classes=[IsStaffOrAdmin])
    def bulk_enroll(self, request, slug=None):
        """
        Inscripción masiva de participantes.
        """
        course = self.get_object()
        
        serializer = EnrollmentBulkCreateSerializer(
            data={
                'course_id': str(course.id),
                **request.data
            }
        )
        
        if serializer.is_valid():
            participants = serializer.validated_data['participants']
            payment_method = serializer.validated_data['payment_method']
            payment_amount = serializer.validated_data['payment_amount']
            
            enrollments = []
            with transaction.atomic():
                for participant in participants:
                    enrollment = Enrollment.objects.create(
                        course=course,
                        participant=participant,
                        payment_method=payment_method,
                        payment_amount=payment_amount,
                        status='CONFIRMED',
                        payment_confirmed=True,
                        payment_confirmed_by=request.user,
                        payment_date=timezone.now()
                    )
                    enrollments.append(enrollment)
                
                # Actualizar contador
                course.enrollment_count += len(participants)
                course.save(update_fields=['enrollment_count'])
            
            return Response({
                'message': f'{len(enrollments)} participantes inscritos exitosamente',
                'enrollments': EnrollmentSerializer(enrollments, many=True).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def rate(self, request, slug=None):
        """
        Califica un curso completado.
        """
        try:
            enrollment = Enrollment.objects.get(
                course__slug=slug,
                participant=request.user,
                status='COMPLETED'
            )
        except Enrollment.DoesNotExist:
            return Response(
                {'error': 'Debes completar el curso para calificarlo'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        serializer = CourseRatingSerializer(
            data=request.data,
            context={'enrollment': enrollment}
        )
        
        if serializer.is_valid():
            enrollment.rating = serializer.validated_data['rating']
            enrollment.feedback = serializer.validated_data.get('feedback', '')
            enrollment.survey_completed = True
            enrollment.survey_date = timezone.now()
            enrollment.save()
            
            # Actualizar rating del curso
            enrollment.course.update_rating()
            
            return Response({
                'message': 'Gracias por tu calificación'
            }, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def enrollments(self, request, slug=None):
        """
        Lista las inscripciones del curso.
        """
        course = self.get_object()
        enrollments = course.enrollments.select_related('participant').all()
        
        # Filtros
        status_filter = request.query_params.get('status')
        if status_filter:
            enrollments = enrollments.filter(status=status_filter)
        
        # Paginación
        page = paginate_queryset(request, enrollments, EnrollmentSerializer)
        if page is not None:
            return page
        
        serializer = EnrollmentSerializer(enrollments, many=True)
        return Response(serializer.data)


class EnrollmentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar inscripciones.
    """
    
    queryset = Enrollment.objects.select_related(
        'course', 'participant'
    ).prefetch_related('attendances')
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    filterset_fields = ['status', 'payment_confirmed', 'is_approved']
    search_fields = ['enrollment_code', 'participant__email', 'participant__first_name']
    ordering_fields = ['enrollment_date', 'payment_date', 'completion_date']
    
    def get_queryset(self):
        """Filtra inscripciones según el usuario."""
        queryset = super().get_queryset()
        
        if self.request.user.user_type == 'PARTICIPANT':
            queryset = queryset.filter(participant=self.request.user)
        elif self.request.user.user_type == 'INSTRUCTOR':
            queryset = queryset.filter(course__instructors=self.request.user)
        
        return queryset
    
    def get_serializer_class(self):
        """Retorna el serializador según la acción."""
        if self.action == 'retrieve':
            return EnrollmentDetailSerializer
        return EnrollmentSerializer
    
    @action(detail=True, methods=['post'])
    def confirm_payment(self, request, pk=None):
        """
        Confirma el pago de una inscripción.
        """
        enrollment = self.get_object()
        
        if enrollment.payment_confirmed:
            return Response(
                {'error': 'El pago ya fue confirmado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        enrollment.payment_confirmed = True
        enrollment.payment_confirmed_by = request.user
        enrollment.payment_date = timezone.now()
        enrollment.status = 'CONFIRMED'
        enrollment.save()
        
        return Response({
            'message': 'Pago confirmado exitosamente',
            'enrollment': EnrollmentSerializer(enrollment).data
        })
    
    @action(detail=True, methods=['post'])
    def mark_attendance(self, request, pk=None):
        """
        Registra asistencia para la inscripción.
        """
        enrollment = self.get_object()
        
        attendance_data = {
            'enrollment': enrollment.id,
            'registered_by': request.user.id,
            **request.data
        }
        
        serializer = AttendanceSerializer(data=attendance_data)
        
        if serializer.is_valid():
            attendance = serializer.save()
            
            # Actualizar porcentaje de asistencia
            total_sessions = enrollment.course.schedules.count()
            if total_sessions > 0:
                attended = enrollment.attendances.filter(is_present=True).count()
                enrollment.attendance_percentage = (attended / total_sessions) * 100
                enrollment.save(update_fields=['attendance_percentage'])
            
            return Response({
                'message': 'Asistencia registrada',
                'attendance': AttendanceSerializer(attendance).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['post'])
    def mark_completed(self, request, pk=None):
        """
        Marca la inscripción como completada.
        """
        enrollment = self.get_object()
        
        final_grade = request.data.get('final_grade')
        is_approved = request.data.get('is_approved', final_grade and final_grade >= 13)
        
        enrollment.final_grade = final_grade
        enrollment.is_approved = is_approved
        enrollment.status = 'COMPLETED'
        enrollment.completion_date = timezone.now()
        enrollment.save()
        
        # Si está aprobado, marcar para certificación
        if is_approved:
            enrollment.status = 'CERTIFIED'
            enrollment.save()
        
        return Response({
            'message': 'Curso marcado como completado',
            'enrollment': EnrollmentSerializer(enrollment).data
        })


class PublicEnrollmentView(generics.CreateAPIView):
    """
    Vista pública para inscripciones (sin autenticación).
    """
    
    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.AllowAny]
    
    def perform_create(self, serializer):
        """Crea inscripción con estado pendiente."""
        serializer.save(status='PENDING')
