"""
Serializadores para el módulo de pagos.
"""

from rest_framework import serializers
from .models import PaymentMethod, Payment, PaymentTransaction, Refund
from events.models import Enrollment
from users.serializers import UserSerializer


class PaymentMethodSerializer(serializers.ModelSerializer):
    """
    Serializador para métodos de pago.
    """
    
    class Meta:
        model = PaymentMethod
        fields = [
            'id', 'code', 'name', 'description', 'icon',
            'min_amount', 'max_amount', 'commission_percentage',
            'commission_fixed', 'is_active', 'order', 'config'
        ]
        read_only_fields = ['id']


class PaymentMethodDetailSerializer(serializers.ModelSerializer):
    """
    Serializador detallado para métodos de pago (con configuración).
    """
    
    class Meta:
        model = PaymentMethod
        fields = '__all__'
        read_only_fields = ['id', 'created_at', 'updated_at']


class PaymentListSerializer(serializers.ModelSerializer):
    """
    Serializador para listados de pagos.
    """
    
    user_name = serializers.CharField(source='user.get_full_name', read_only=True)
    enrollment_code = serializers.CharField(source='enrollment.enrollment_code', read_only=True)
    payment_method_name = serializers.CharField(source='payment_method.name', read_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'id', 'payment_code', 'user_name', 'enrollment_code',
            'payment_method_name', 'amount', 'status', 'created_at',
            'confirmed_at'
        ]


class PaymentDetailSerializer(serializers.ModelSerializer):
    """
    Serializador detallado para pagos.
    """
    
    user = UserSerializer(read_only=True)
    payment_method = PaymentMethodSerializer(read_only=True)
    
    class Meta:
        model = Payment
        fields = '__all__'
        read_only_fields = [
            'id', 'payment_code', 'commission', 'net_amount',
            'created_at', 'updated_at', 'confirmed_at'
        ]


class PaymentCreateSerializer(serializers.ModelSerializer):
    """
    Serializador para crear pagos.
    """
    
    enrollment_id = serializers.UUIDField(write_only=True)
    payment_method_code = serializers.CharField(write_only=True)
    
    class Meta:
        model = Payment
        fields = [
            'enrollment_id', 'payment_method_code', 'amount',
            'phone_number', 'operation_code', 'bank_name',
            'account_number', 'voucher_file'
        ]
    
    def validate(self, data):
        """Valida los datos para crear el pago."""
        # Verificar inscripción
        try:
            enrollment = Enrollment.objects.select_related('participant').get(
                id=data['enrollment_id']
            )
        except Enrollment.DoesNotExist:
            raise serializers.ValidationError('Inscripción no encontrada')
        
        # Verificar método de pago
        try:
            payment_method = PaymentMethod.objects.get(
                code=data['payment_method_code'],
                is_active=True
            )
        except PaymentMethod.DoesNotExist:
            raise serializers.ValidationError('Método de pago no válido')
        
        # Verificar montos
        if data['amount'] < payment_method.min_amount:
            raise serializers.ValidationError(
                f'El monto mínimo es {payment_method.min_amount}'
            )
        
        if payment_method.max_amount and data['amount'] > payment_method.max_amount:
            raise serializers.ValidationError(
                f'El monto máximo es {payment_method.max_amount}'
            )
        
        # Validar según método
        if payment_method.code in ['YAPE', 'PLIN']:
            if not data.get('phone_number'):
                raise serializers.ValidationError(
                    'Debe proporcionar número de teléfono para Yape/Plin'
                )
            if not data.get('operation_code'):
                raise serializers.ValidationError(
                    'Debe proporcionar código de operación'
                )
        
        elif payment_method.code == 'TRANSFER':
            if not data.get('bank_name'):
                raise serializers.ValidationError(
                    'Debe proporcionar nombre del banco'
                )
            if not data.get('voucher_file'):
                raise serializers.ValidationError(
                    'Debe adjuntar el comprobante de transferencia'
                )
        
        # Guardar objetos para crear
        data['enrollment'] = enrollment
        data['payment_method'] = payment_method
        data['user'] = enrollment.participant
        
        return data
    
    def create(self, validated_data):
        """Crea el pago."""
        # Remover campos auxiliares
        validated_data.pop('enrollment_id')
        validated_data.pop('payment_method_code')
        
        payment = Payment.objects.create(**validated_data)
        return payment


class PaymentConfirmSerializer(serializers.Serializer):
    """
    Serializador para confirmar pagos.
    """
    
    confirmed = serializers.BooleanField(read_only=True)
    message = serializers.CharField(read_only=True)


class RefundSerializer(serializers.ModelSerializer):
    """
    Serializador para reembolsos.
    """
    
    payment_code = serializers.CharField(source='payment.payment_code', read_only=True)
    user_name = serializers.CharField(source='payment.user.get_full_name', read_only=True)
    
    class Meta:
        model = Refund
        fields = '__all__'
        read_only_fields = ['id', 'refund_code', 'created_at', 'updated_at']


class RefundCreateSerializer(serializers.Serializer):
    """
    Serializador para crear reembolsos.
    """
    
    payment_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=10, decimal_places=2, required=True)
    reason = serializers.ChoiceField(choices=Refund.REASON_CHOICES, required=True)
    reason_text = serializers.CharField(required=False, allow_blank=True)
    
    def validate(self, data):
        """Valida los datos del reembolso."""
        try:
            payment = Payment.objects.get(id=data['payment_id'])
        except Payment.DoesNotExist:
            raise serializers.ValidationError('Pago no encontrado')
        
        if payment.status != 'COMPLETED':
            raise serializers.ValidationError('Solo se pueden reembolsar pagos completados')
        
        if data['amount'] > payment.amount:
            raise serializers.ValidationError(
                f'El monto no puede exceder {payment.amount}'
            )
        
        data['payment'] = payment
        return data


class PaymentTransactionSerializer(serializers.ModelSerializer):
    """
    Serializador para transacciones de pago.
    Registra las transacciones realizadas con pasarelas de pago.
    """
    
    payment_code = serializers.CharField(source='payment.payment_code', read_only=True)
    gateway_display = serializers.SerializerMethodField()
    status_display = serializers.SerializerMethodField()
    amount = serializers.DecimalField(source='payment.amount', max_digits=10, decimal_places=2, read_only=True)
    
    class Meta:
        model = PaymentTransaction
        fields = [
            'id',
            'payment',
            'payment_code',
            'amount',
            'gateway',
            'gateway_display',
            'transaction_type',
            'gateway_transaction_id',
            'status',
            'status_display',
            'status_code',
            'status_message',
            'request_data',
            'response_data',
            'ip_address',
            'user_agent',
            'created_at',
        ]
        read_only_fields = [
            'id', 'payment', 'gateway', 'gateway_transaction_id',
            'status', 'request_data', 'response_data', 'ip_address',
            'user_agent', 'created_at'
        ]
    
    def get_gateway_display(self, obj):
        """
        Retorna el nombre legible de la pasarela de pago.
        
        Returns:
            str: Nombre de la pasarela en español
        """
        gateways = {
            'YAPE': 'Yape',
            'PLIN': 'Plin',
            'IZIPAY': 'Izipay (Tarjeta)',
            'TRANSFER': 'Transferencia Bancaria',
            'CASH': 'Efectivo',
        }
        return gateways.get(obj.gateway, obj.gateway)
    
    def get_status_display(self, obj):
        """
        Retorna el estado legible de la transacción.
        
        Returns:
            str: Estado en español
        """
        status_map = {
            'PENDING': 'Pendiente',
            'PROCESSING': 'Procesando',
            'COMPLETED': 'Completada',
            'FAILED': 'Fallida',
            'CANCELLED': 'Cancelada',
            'REFUNDED': 'Reembolsada',
        }
        return status_map.get(obj.status, obj.status)
    
    def to_representation(self, instance):
        """
        Personaliza la representación de la transacción.
        Oculta datos sensibles en la respuesta.
        """
        data = super().to_representation(instance)
        
        # Ocultar datos sensibles de la tarjeta si existen
        if 'request_data' in data and isinstance(data['request_data'], dict):
            if 'card' in data['request_data']:
                card_info = data['request_data']['card']
                masked_card = {
                    'last4': card_info.get('last4', '****') if isinstance(card_info, dict) else '****',
                    'brand': card_info.get('brand', 'unknown') if isinstance(card_info, dict) else 'unknown'
                }
                data['request_data']['card'] = masked_card
            
            # Ocultar tokens y datos sensibles
            sensitive_keys = ['token', 'cvv', 'password', 'secret']
            for key in sensitive_keys:
                if key in data['request_data']:
                    data['request_data'][key] = '********'
        
        return data


class PaymentTransactionDetailSerializer(PaymentTransactionSerializer):
    """
    Serializador detallado para transacciones de pago.
    Incluye información completa del pago asociado.
    """
    
    payment_detail = PaymentDetailSerializer(source='payment', read_only=True)
    
    class Meta(PaymentTransactionSerializer.Meta):
        fields = PaymentTransactionSerializer.Meta.fields + ['payment_detail']
