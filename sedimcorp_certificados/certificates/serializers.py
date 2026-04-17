"""
Serializadores para el módulo de certificados.
"""

from rest_framework import serializers
from .models import CertificateTemplate, Certificate, CertificateLog
from events.serializers import EnrollmentSerializer
from users.serializers import UserSerializer


class CertificateTemplateSerializer(serializers.ModelSerializer):
    """
    Serializador para plantillas de certificados.
    """
    
    created_by_name = serializers.CharField(source='created_by.get_full_name', read_only=True)
    
    class Meta:
        model = CertificateTemplate
        fields = '__all__'
        read_only_fields = ['id', 'code', 'created_at', 'updated_at', 'created_by']
    
    def validate_code(self, value):
        """Valida que el código sea único."""
        if CertificateTemplate.objects.filter(code=value).exists():
            raise serializers.ValidationError('Ya existe una plantilla con este código')
        return value
    
    def create(self, validated_data):
        """Crea plantilla con código generado si no se proporciona."""
        if 'code' not in validated_data:
            import secrets
            validated_data['code'] = f"TMP-{secrets.token_hex(4).upper()}"
        validated_data['created_by'] = self.context['request'].user
        return super().create(validated_data)


class CertificateListSerializer(serializers.ModelSerializer):
    """
    Serializador simplificado para listados de certificados.
    """
    
    participant_name = serializers.CharField(read_only=True)
    course_title = serializers.CharField(source='course_name', read_only=True)
    
    class Meta:
        model = Certificate
        fields = [
            'id', 'certificate_code', 'participant_name',
            'course_title', 'issue_date', 'status',
            'downloaded_count', 'validated_at'
        ]


class CertificateDetailSerializer(serializers.ModelSerializer):
    """
    Serializador detallado para certificados.
    """
    
    enrollment_details = EnrollmentSerializer(source='enrollment', read_only=True)
    template_details = CertificateTemplateSerializer(source='template', read_only=True)
    generated_by_details = UserSerializer(source='generated_by', read_only=True)
    
    class Meta:
        model = Certificate
        fields = '__all__'
        read_only_fields = [
            'id', 'certificate_code', 'validation_hash',
            'validation_url', 'generated_at', 'downloaded_count'
        ]


class CertificateGenerateSerializer(serializers.Serializer):
    """
    Serializador para generar certificados.
    """
    
    enrollment_id = serializers.UUIDField(required=True)
    template_id = serializers.UUIDField(required=False)
    custom_text = serializers.CharField(required=False, allow_blank=True)
    send_email = serializers.BooleanField(default=False)
    
    def validate_enrollment_id(self, value):
        """Valida que la inscripción exista y sea elegible."""
        from events.models import Enrollment
        
        try:
            enrollment = Enrollment.objects.select_related(
                'participant', 'course'
            ).get(id=value)
        except Enrollment.DoesNotExist:
            raise serializers.ValidationError('Inscripción no encontrada')
        
        # Verificar que esté completado y aprobado
        if enrollment.status != 'COMPLETED' or not enrollment.is_approved:
            raise serializers.ValidationError(
                'La inscripción no está completada o aprobada'
            )
        
        # Verificar que no tenga certificado
        if hasattr(enrollment, 'certificate'):
            raise serializers.ValidationError(
                'Esta inscripción ya tiene un certificado generado'
            )
        
        return value


class CertificateBatchGenerateSerializer(serializers.Serializer):
    """
    Serializador para generación masiva de certificados.
    """
    
    course_id = serializers.UUIDField(required=True)
    template_id = serializers.UUIDField(required=False)
    enrollment_ids = serializers.ListField(
        child=serializers.UUIDField(),
        required=False
    )
    send_emails = serializers.BooleanField(default=False)
    
    def validate_course_id(self, value):
        """Valida que el curso exista."""
        from events.models import Course
        
        try:
            course = Course.objects.get(id=value)
        except Course.DoesNotExist:
            raise serializers.ValidationError('Curso no encontrado')
        
        return value


class CertificateValidateSerializer(serializers.Serializer):
    """
    Serializador para validación de certificados.
    """
    
    validation_hash = serializers.CharField(required=True)
    code = serializers.CharField(required=False)


class CertificateLogSerializer(serializers.ModelSerializer):
    """
    Serializador para registros de certificados.
    """
    
    action_display = serializers.CharField(source='get_action_display', read_only=True)
    username = serializers.CharField(source='user.get_full_name', read_only=True)
    
    class Meta:
        model = CertificateLog
        fields = '__all__'
        read_only_fields = ['id', 'timestamp']
