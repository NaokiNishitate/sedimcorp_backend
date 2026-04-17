"""
Vistas para el módulo de validación de certificados.
"""

from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta

from .models import ValidationAttempt, CertificateAccess
from .serializers import (
    ValidationRequestSerializer, ValidationResponseSerializer,
    ValidationStatsSerializer, CertificateAccessSerializer
)
from certificates.models import Certificate
from certificates.generators import CertificateGenerator
from users.permissions import IsAdmin


class CertificateValidationView(generics.GenericAPIView):
    """
    Vista para validar certificados (pública).
    """
    
    permission_classes = [permissions.AllowAny]
    serializer_class = ValidationRequestSerializer
    
    def post(self, request):
        """
        Valida un certificado y registra el intento.
        """
        serializer = self.get_serializer(data=request.data)
        
        if serializer.is_valid():
            # Determinar qué campo usar para la búsqueda
            validation_hash = serializer.validated_data.get('validation_hash')
            certificate_code = serializer.validated_data.get('certificate_code')
            qr_data = serializer.validated_data.get('qr_data')
            
            # Procesar QR data si viene (podría ser URL completa)
            if qr_data:
                # Extraer hash de URL si es necesario
                if qr_data.startswith(('http://', 'https://')):
                    # Asumimos que la URL termina con el hash
                    validation_hash = qr_data.split('/')[-1]
                else:
                    validation_hash = qr_data
            
            # Buscar certificado
            certificate = None
            if validation_hash:
                certificate, is_valid = CertificateGenerator.validate_certificate(validation_hash)
            elif certificate_code:
                try:
                    certificate = Certificate.objects.get(
                        certificate_code=certificate_code,
                        status__in=['GENERATED', 'DOWNLOADED', 'VALIDATED']
                    )
                    is_valid = True
                except Certificate.DoesNotExist:
                    certificate = None
                    is_valid = False
            
            # Registrar intento
            attempt = ValidationAttempt.objects.create(
                certificate=certificate,
                validation_hash=validation_hash or certificate_code or qr_data,
                was_successful=is_valid,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', '')
            )
            
            # Preparar respuesta
            if certificate and is_valid:
                # Registrar acceso
                CertificateAccess.objects.create(
                    certificate=certificate,
                    access_type='VIEW',
                    ip_address=self._get_client_ip(request),
                    user_agent=request.META.get('HTTP_USER_AGENT', ''),
                    referer=request.META.get('HTTP_REFERER', '')
                )
                
                response_data = {
                    'valid': True,
                    'message': 'Certificado válido',
                    'validation_id': attempt.id,
                    'timestamp': attempt.timestamp,
                    'certificate_data': {
                        'code': certificate.certificate_code,
                        'participant_name': certificate.participant_name,
                        'participant_document': certificate.participant_document,
                        'course_name': certificate.course_name,
                        'course_duration': certificate.course_duration,
                        'issue_date': certificate.issue_date,
                        'completion_date': certificate.completion_date,
                        'status': certificate.status
                    }
                }
            else:
                response_data = {
                    'valid': False,
                    'message': 'Certificado no encontrado o inválido',
                    'validation_id': attempt.id,
                    'timestamp': attempt.timestamp
                }
            
            return Response(response_data, status=status.HTTP_200_OK)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def _get_client_ip(self, request):
        """Obtiene la IP del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class ValidationStatsView(generics.GenericAPIView):
    """
    Vista para obtener estadísticas de validación.
    Solo accesible para administradores.
    """
    
    permission_classes = [IsAdmin]
    serializer_class = ValidationStatsSerializer
    
    def get(self, request):
        """
        Retorna estadísticas de validación.
        """
        now = timezone.now()
        last_24h = now - timedelta(hours=24)
        last_7d = now - timedelta(days=7)
        last_30d = now - timedelta(days=30)
        
        # Estadísticas generales
        total_attempts = ValidationAttempt.objects.count()
        successful_attempts = ValidationAttempt.objects.filter(was_successful=True).count()
        failed_attempts = total_attempts - successful_attempts
        
        success_rate = (successful_attempts / total_attempts * 100) if total_attempts > 0 else 0
        
        # Estadísticas por período
        last_24h_count = ValidationAttempt.objects.filter(timestamp__gte=last_24h).count()
        last_7d_count = ValidationAttempt.objects.filter(timestamp__gte=last_7d).count()
        last_30d_count = ValidationAttempt.objects.filter(timestamp__gte=last_30d).count()
        
        # Top certificados validados
        top_certificates = ValidationAttempt.objects.filter(
            was_successful=True,
            certificate__isnull=False
        ).values(
            'certificate__certificate_code',
            'certificate__participant_name',
            'certificate__course_name'
        ).annotate(
            count=Count('id')
        ).order_by('-count')[:10]
        
        data = {
            'total_attempts': total_attempts,
            'successful_attempts': successful_attempts,
            'failed_attempts': failed_attempts,
            'success_rate': round(success_rate, 2),
            'last_24h': last_24h_count,
            'last_7d': last_7d_count,
            'last_30d': last_30d_count,
            'top_certificates': list(top_certificates)
        }
        
        serializer = self.get_serializer(data)
        return Response(serializer.data)


class CertificateAccessViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar accesos a certificados.
    """
    
    queryset = CertificateAccess.objects.select_related('certificate').all()
    serializer_class = CertificateAccessSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['access_type', 'certificate']
    search_fields = ['certificate__certificate_code', 'ip_address']
    ordering_fields = ['timestamp']
    
    @action(detail=False, methods=['get'])
    def by_certificate(self, request):
        """
        Agrupa accesos por certificado.
        """
        certificate_id = request.query_params.get('certificate_id')
        
        if not certificate_id:
            return Response(
                {'error': 'Debe proporcionar certificate_id'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        accesses = self.queryset.filter(certificate_id=certificate_id)
        
        # Estadísticas por tipo
        stats = accesses.values('access_type').annotate(
            count=Count('id')
        ).order_by('-count')
        
        # Serie temporal (últimos 30 días)
        last_30d = timezone.now() - timedelta(days=30)
        timeline = accesses.filter(
            timestamp__gte=last_30d
        ).extra(
            {'date': "date(timestamp)"}
        ).values('date').annotate(
            count=Count('id')
        ).order_by('date')
        
        return Response({
            'total': accesses.count(),
            'stats': list(stats),
            'timeline': list(timeline),
            'recent': CertificateAccessSerializer(
                accesses[:10], many=True
            ).data
        })
