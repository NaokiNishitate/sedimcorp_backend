"""
Serializadores para el módulo de validación.
"""

from rest_framework import serializers
from .models import ValidationAttempt, CertificateAccess
from certificates.models import Certificate


class ValidationRequestSerializer(serializers.Serializer):
    """
    Serializador para solicitudes de validación.
    """
    
    validation_hash = serializers.CharField(
        required=False,
        help_text='Hash de validación del certificado'
    )
    
    certificate_code = serializers.CharField(
        required=False,
        help_text='Código del certificado'
    )
    
    qr_data = serializers.CharField(
        required=False,
        help_text='Datos del código QR'
    )
    
    def validate(self, data):
        """Valida que al menos un campo esté presente."""
        if not any([data.get('validation_hash'),
                    data.get('certificate_code'),
                    data.get('qr_data')]):
            raise serializers.ValidationError(
                'Debe proporcionar validation_hash, certificate_code o qr_data'
            )
        return data


class ValidationResponseSerializer(serializers.Serializer):
    """
    Serializador para respuestas de validación.
    """
    
    valid = serializers.BooleanField()
    message = serializers.CharField()
    
    # Datos públicos del certificado (solo si es válido)
    certificate_data = serializers.DictField(required=False)
    
    # Datos de la validación
    validation_id = serializers.UUIDField(required=False)
    timestamp = serializers.DateTimeField(required=False)


class ValidationStatsSerializer(serializers.Serializer):
    """
    Serializador para estadísticas de validación.
    """
    
    total_attempts = serializers.IntegerField()
    successful_attempts = serializers.IntegerField()
    failed_attempts = serializers.IntegerField()
    success_rate = serializers.FloatField()
    
    # Estadísticas por período
    last_24h = serializers.IntegerField()
    last_7d = serializers.IntegerField()
    last_30d = serializers.IntegerField()
    
    # Top certificados validados
    top_certificates = serializers.ListField(child=serializers.DictField())


class CertificateAccessSerializer(serializers.ModelSerializer):
    """
    Serializador para accesos a certificados.
    """
    
    certificate_code = serializers.CharField(
        source='certificate.certificate_code',
        read_only=True
    )
    
    class Meta:
        model = CertificateAccess
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']
