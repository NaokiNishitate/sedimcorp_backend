"""
Vistas para el módulo de certificados.
"""

from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.db import transaction
from django.utils import timezone
from django.conf import settings
import os

from .models import CertificateTemplate, Certificate, CertificateLog
from .serializers import (
    CertificateTemplateSerializer, CertificateListSerializer,
    CertificateDetailSerializer, CertificateGenerateSerializer,
    CertificateBatchGenerateSerializer, CertificateValidateSerializer,
    CertificateLogSerializer
)
from .generators import CertificateGenerator, BatchCertificateGenerator
from users.permissions import IsAdmin, IsStaffOrAdmin
from events.models import Enrollment, Course


class CertificateTemplateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar plantillas de certificados.
    """
    
    queryset = CertificateTemplate.objects.all()
    serializer_class = CertificateTemplateSerializer
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['name', 'code', 'description']
    filterset_fields = ['is_active', 'is_default', 'orientation', 'paper_size']
    ordering_fields = ['name', 'created_at']
    
    def get_queryset(self):
        """Personaliza el queryset según el usuario."""
        queryset = super().get_queryset()
        
        # Usuarios no admin solo ven plantillas activas
        if not self.request.user.user_type == 'ADMIN':
            queryset = queryset.filter(is_active=True)
        
        return queryset
    
    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        """
        Duplica una plantilla existente.
        """
        original = self.get_object()
        
        # Crear copia
        new_template = CertificateTemplate.objects.get(pk=original.pk)
        new_template.pk = None
        new_template.code = f"{original.code}_COPY"
        new_template.name = f"{original.name} (Copia)"
        new_template.is_default = False
        new_template.created_by = request.user
        new_template.save()
        
        serializer = self.get_serializer(new_template)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    
    @action(detail=True, methods=['post'])
    def set_default(self, request, pk=None):
        """
        Establece esta plantilla como por defecto.
        """
        template = self.get_object()
        template.is_default = True
        template.save()
        
        return Response({
            'message': 'Plantilla establecida como por defecto'
        })


class CertificateViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar certificados.
    """
    
    queryset = Certificate.objects.select_related(
        'enrollment', 'template', 'generated_by'
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    search_fields = [
        'certificate_code', 'participant_name',
        'participant_document', 'course_name'
    ]
    filterset_fields = ['status', 'issue_date']
    ordering_fields = ['issue_date', 'generated_at', 'downloaded_count']
    
    def get_serializer_class(self):
        """Retorna el serializador según la acción."""
        if self.action == 'list':
            return CertificateListSerializer
        return CertificateDetailSerializer
    
    def get_queryset(self):
        """Personaliza el queryset según el usuario."""
        queryset = super().get_queryset()
        
        # Participantes solo ven sus certificados
        if self.request.user.user_type == 'PARTICIPANT':
            queryset = queryset.filter(enrollment__participant=self.request.user)
        
        # Instructores ven certificados de sus cursos
        elif self.request.user.user_type == 'INSTRUCTOR':
            queryset = queryset.filter(
                enrollment__course__instructors=self.request.user
            )
        
        return queryset
    
    @action(detail=False, methods=['post'])
    def generate(self, request):
        """
        Genera un certificado para una inscripción.
        """
        serializer = CertificateGenerateSerializer(data=request.data)
        
        if serializer.is_valid():
            enrollment = get_object_or_404(
                Enrollment,
                id=serializer.validated_data['enrollment_id']
            )
            
            # Verificar permisos
            if not (request.user.user_type in ['ADMIN', 'STAFF'] or
                    request.user == enrollment.course.coordinator):
                return Response(
                    {'error': 'No tienes permiso para generar este certificado'},
                    status=status.HTTP_403_FORBIDDEN
                )
            
            try:
                generator = CertificateGenerator(
                    enrollment,
                    template_id=serializer.validated_data.get('template_id'),
                    custom_text=serializer.validated_data.get('custom_text')
                )
                
                certificate = generator.create_certificate(request.user)
                
                # Enviar email si se solicita
                if serializer.validated_data.get('send_email'):
                    # Lógica de envío de email
                    pass
                
                return Response({
                    'message': 'Certificado generado exitosamente',
                    'certificate': CertificateDetailSerializer(certificate).data
                }, status=status.HTTP_201_CREATED)
                
            except Exception as e:
                return Response(
                    {'error': f'Error al generar certificado: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def generate_batch(self, request):
        """
        Genera certificados por lote.
        """
        serializer = CertificateBatchGenerateSerializer(data=request.data)
        
        if serializer.is_valid():
            course = get_object_or_404(
                Course,
                id=serializer.validated_data['course_id']
            )
            
            generator = BatchCertificateGenerator(course)
            result = generator.generate_all(request.user)
            
            return Response({
                'message': f'Procesados {result["total"]} inscripciones',
                'results': result
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=True, methods=['get'])
    def download(self, request, pk=None):
        """
        Descarga el PDF del certificado.
        """
        certificate = self.get_object()
        
        # Verificar permisos
        if (request.user.user_type == 'PARTICIPANT' and
                certificate.enrollment.participant != request.user):
            return Response(
                {'error': 'No tienes permiso para descargar este certificado'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        if not certificate.pdf_file:
            raise Http404("Archivo no encontrado")
        
        # Registrar descarga
        certificate.register_download(request)
        
        # Registrar log
        CertificateLog.objects.create(
            certificate=certificate,
            action='DOWNLOAD',
            user=request.user if request.user.is_authenticated else None,
            ip_address=self._get_client_ip(request),
            user_agent=request.META.get('HTTP_USER_AGENT', '')
        )
        
        # Servir archivo
        response = FileResponse(
            certificate.pdf_file.open('rb'),
            content_type='application/pdf'
        )
        response['Content-Disposition'] = f'attachment; filename="{certificate.certificate_code}.pdf"'
        
        return response
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Anula un certificado.
        """
        certificate = self.get_object()
        
        if certificate.status == 'CANCELLED':
            return Response(
                {'error': 'El certificado ya está anulado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reason = request.data.get('reason', '')
        
        certificate.status = 'CANCELLED'
        certificate.cancelled_at = timezone.now()
        certificate.cancelled_by = request.user
        certificate.cancellation_reason = reason
        certificate.save()
        
        # Registrar log
        CertificateLog.objects.create(
            certificate=certificate,
            action='CANCEL',
            user=request.user,
            ip_address=self._get_client_ip(request),
            metadata={'reason': reason}
        )
        
        return Response({
            'message': 'Certificado anulado exitosamente'
        })
    
    @action(detail=True, methods=['get'])
    def logs(self, request, pk=None):
        """
        Obtiene los logs del certificado.
        """
        certificate = self.get_object()
        logs = certificate.logs.all()
        
        page = self.paginate_queryset(logs)
        if page is not None:
            serializer = CertificateLogSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)
        
        serializer = CertificateLogSerializer(logs, many=True)
        return Response(serializer.data)
    
    def _get_client_ip(self, request):
        """Obtiene la IP del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class PublicCertificateValidationView(generics.GenericAPIView):
    """
    Vista pública para validar certificados.
    """
    
    permission_classes = [permissions.AllowAny]
    serializer_class = CertificateValidateSerializer
    
    def post(self, request):
        """
        Valida un certificado por hash o código.
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            validation_hash = serializer.validated_data.get('validation_hash')
            code = serializer.validated_data.get('code')
            
            # Buscar por hash o código
            query = Certificate.objects.all()
            if validation_hash:
                query = query.filter(validation_hash=validation_hash)
            elif code:
                query = query.filter(certificate_code=code)
            else:
                return Response(
                    {'error': 'Debe proporcionar un hash o código de validación'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                certificate = query.select_related(
                    'enrollment', 'template'
                ).get()
            except Certificate.DoesNotExist:
                return Response(
                    {'valid': False, 'message': 'Certificado no encontrado'},
                    status=status.HTTP_404_NOT_FOUND
                )
            
            # Verificar estado
            if certificate.status == 'CANCELLED':
                return Response({
                    'valid': False,
                    'message': 'Este certificado ha sido anulado'
                })
            
            # Registrar validación
            certificate.register_validation(self._get_client_ip(request))
            
            # Registrar log
            CertificateLog.objects.create(
                certificate=certificate,
                action='VALIDATE',
                user=None,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Datos públicos del certificado
            data = {
                'valid': True,
                'certificate': {
                    'code': certificate.certificate_code,
                    'participant_name': certificate.participant_name,
                    'participant_document': certificate.participant_document,
                    'course_name': certificate.course_name,
                    'course_duration': certificate.course_duration,
                    'issue_date': certificate.issue_date,
                    'completion_date': certificate.completion_date,
                    'status': certificate.status,
                    'template_name': certificate.template.name if certificate.template else None,
                }
            }
            
            return Response(data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Obtiene la IP del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class MyCertificatesView(generics.ListAPIView):
    """
    Vista para que participantes vean sus certificados.
    """
    
    serializer_class = CertificateListSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        """Retorna certificados del participante actual."""
        if self.request.user.user_type != 'PARTICIPANT':
            return Certificate.objects.none()
        
        return Certificate.objects.filter(
            enrollment__participant=self.request.user
        ).select_related('enrollment').order_by('-issue_date')
