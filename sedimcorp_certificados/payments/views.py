"""
Vistas para el módulo de pagos.
"""

from rest_framework import viewsets, status, generics, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db import transaction
from django.utils import timezone
from django.shortcuts import get_object_or_404

from .models import PaymentMethod, Payment, PaymentTransaction, Refund
from .serializers import (
    PaymentMethodSerializer, PaymentMethodDetailSerializer,
    PaymentListSerializer, PaymentDetailSerializer,
    PaymentCreateSerializer, PaymentConfirmSerializer,
    RefundSerializer, RefundCreateSerializer, PaymentTransactionSerializer
)
from .services import PaymentServiceFactory
from users.permissions import IsAdmin, IsStaffOrAdmin, IsParticipant, IsOwnerOrAdmin


class PaymentMethodViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar métodos de pago.
    """
    
    queryset = PaymentMethod.objects.filter(is_active=True)
    serializer_class = PaymentMethodSerializer
    permission_classes = [permissions.AllowAny]
    lookup_field = 'code'
    
    def get_serializer_class(self):
        """Retorna serializador según acción."""
        if self.action == 'retrieve':
            return PaymentMethodDetailSerializer
        return PaymentMethodSerializer


class PaymentViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar pagos.
    """
    
    queryset = Payment.objects.select_related(
        'user', 'enrollment', 'payment_method'
    ).all()
    permission_classes = [permissions.IsAuthenticated]
    search_fields = ['payment_code', 'user__email', 'user__first_name', 'user__last_name']
    filterset_fields = ['status', 'payment_method', 'confirmed_at']
    ordering_fields = ['created_at', 'amount', 'confirmed_at']
    
    def get_serializer_class(self):
        """Retorna serializador según acción."""
        if self.action == 'list':
            return PaymentListSerializer
        elif self.action == 'retrieve':
            return PaymentDetailSerializer
        elif self.action == 'create':
            return PaymentCreateSerializer
        return PaymentDetailSerializer
    
    def get_queryset(self):
        """Filtra pagos según el usuario."""
        queryset = super().get_queryset()
        
        if self.request.user.user_type == 'PARTICIPANT':
            queryset = queryset.filter(user=self.request.user)
        elif self.request.user.user_type == 'INSTRUCTOR':
            queryset = queryset.filter(enrollment__course__instructors=self.request.user)
        
        return queryset
    
    @transaction.atomic
    def create(self, request, *args, **kwargs):
        """Crea un nuevo pago."""
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        payment = serializer.save()
        
        # Procesar según método de pago
        try:
            service = PaymentServiceFactory.get_service(payment.payment_method.code)
            result = service.process_payment(
                payment,
                ip_address=self._get_client_ip(request),
                user_agent=request.META.get('HTTP_USER_AGENT', ''),
                **request.data
            )
            
            return Response({
                'payment': PaymentListSerializer(payment).data,
                'processing': result
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Error al procesar pago: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """
        Confirma un pago manualmente.
        """
        payment = self.get_object()
        
        if payment.status == 'COMPLETED':
            return Response(
                {'error': 'El pago ya está confirmado'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = 'COMPLETED'
        payment.confirmed_at = timezone.now()
        payment.confirmed_by = request.user
        payment.save()
        
        # Confirmar inscripción
        payment.confirm_payment(request.user)
        
        serializer = PaymentConfirmSerializer({
            'confirmed': True,
            'message': 'Pago confirmado exitosamente'
        })
        
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """
        Cancela un pago pendiente.
        """
        payment = self.get_object()
        
        if payment.status != 'PENDING':
            return Response(
                {'error': 'Solo se pueden cancelar pagos pendientes'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        payment.status = 'CANCELLED'
        payment.save()
        
        return Response({
            'message': 'Pago cancelado exitosamente'
        })
    
    @action(detail=True, methods=['get'])
    def transactions(self, request, pk=None):
        """
        Obtiene las transacciones del pago.
        """
        payment = self.get_object()
        transactions = payment.transactions.all()
        
        from .serializers import PaymentTransactionSerializer
        serializer = PaymentTransactionSerializer(transactions, many=True)
        
        return Response(serializer.data)
    
    def _get_client_ip(self, request):
        """Obtiene la IP del cliente."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip


class RefundViewSet(viewsets.ModelViewSet):
    """
    ViewSet para gestionar reembolsos.
    """
    
    queryset = Refund.objects.select_related('payment').all()
    serializer_class = RefundSerializer
    permission_classes = [IsAdmin]
    search_fields = ['refund_code', 'payment__payment_code']
    filterset_fields = ['status', 'reason']
    ordering_fields = ['created_at', 'refund_date']
    
    @action(detail=False, methods=['post'])
    def request_refund(self, request):
        """
        Solicita un reembolso.
        """
        serializer = RefundCreateSerializer(data=request.data)
        
        if serializer.is_valid():
            payment = serializer.validated_data['payment']
            
            refund = Refund.objects.create(
                payment=payment,
                amount=serializer.validated_data['amount'],
                reason=serializer.validated_data['reason'],
                reason_text=serializer.validated_data.get('reason_text', ''),
                refund_date=timezone.now(),
                requested_by=request.user,
                status='PENDING'
            )
            
            # Actualizar estado del pago
            payment.status = 'REFUNDED'
            payment.save()
            
            return Response({
                'message': 'Solicitud de reembolso creada',
                'refund': RefundSerializer(refund).data
            }, status=status.HTTP_201_CREATED)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class PaymentTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    """
    ViewSet para consultar transacciones de pago.
    """
    
    queryset = PaymentTransaction.objects.select_related('payment').all()
    serializer_class = PaymentTransactionSerializer
    permission_classes = [IsAdmin]
    filterset_fields = ['gateway', 'status', 'payment']
    ordering_fields = ['created_at']
    
    def get_queryset(self):
        """Filtra transacciones por pago si se especifica."""
        queryset = super().get_queryset()
        payment_id = self.request.query_params.get('payment_id')
        
        if payment_id:
            queryset = queryset.filter(payment_id=payment_id)
        
        return queryset
