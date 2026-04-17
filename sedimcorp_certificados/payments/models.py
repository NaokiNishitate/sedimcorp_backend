"""
Modelos para el módulo de pagos.
Integración con pasarelas de pago: Yape, Plin, Izipay.
"""

from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.conf import settings
import uuid


class PaymentMethod(models.Model):
    """
    Métodos de pago disponibles en el sistema.
    """
    
    METHOD_CHOICES = [
        ('YAPE', 'Yape'),
        ('PLIN', 'Plin'),
        ('IZIPAY', 'Izipay (Tarjeta)'),
        ('TRANSFER', 'Transferencia Bancaria'),
        ('CASH', 'Efectivo'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    code = models.CharField(
        max_length=20,
        unique=True,
        choices=METHOD_CHOICES,
        verbose_name='Código'
    )
    
    name = models.CharField(
        max_length=100,
        verbose_name='Nombre'
    )
    
    description = models.TextField(
        max_length=500,
        verbose_name='Descripción',
        blank=True,
        null=True
    )
    
    # Configuración específica
    config = models.JSONField(
        verbose_name='Configuración',
        default=dict,
        help_text='Configuración específica del método (API keys, números, etc.)'
    )
    
    # Límites y comisiones
    min_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Monto mínimo'
    )
    
    max_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto máximo',
        blank=True,
        null=True
    )
    
    commission_percentage = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0,
        verbose_name='Comisión (%)'
    )
    
    commission_fixed = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Comisión fija'
    )
    
    # Control
    is_active = models.BooleanField(
        default=True,
        verbose_name='¿Activo?'
    )
    
    is_default = models.BooleanField(
        default=False,
        verbose_name='¿Por defecto?'
    )
    
    icon = models.CharField(
        max_length=50,
        verbose_name='Icono',
        blank=True,
        null=True
    )
    
    order = models.PositiveIntegerField(
        default=0,
        verbose_name='Orden'
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
        verbose_name = 'Método de pago'
        verbose_name_plural = 'Métodos de pago'
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name
    
    def calculate_commission(self, amount):
        """
        Calcula la comisión para un monto dado.
        
        Args:
            amount: Monto base
            
        Returns:
            Decimal: Comisión total
        """
        percentage = amount * (self.commission_percentage / 100)
        return percentage + self.commission_fixed


class Payment(models.Model):
    """
    Registro de pagos realizados.
    """
    
    # Estados del pago
    STATUS_CHOICES = [
        ('PENDING', 'Pendiente'),
        ('PROCESSING', 'Procesando'),
        ('COMPLETED', 'Completado'),
        ('FAILED', 'Fallido'),
        ('REFUNDED', 'Reembolsado'),
        ('CANCELLED', 'Cancelado'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    payment_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código de pago'
    )
    
    enrollment = models.ForeignKey(
        'events.Enrollment',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='Inscripción'
    )
    
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='Usuario'
    )
    
    payment_method = models.ForeignKey(
        PaymentMethod,
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name='Método de pago'
    )
    
    # Montos
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Monto'
    )
    
    commission = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0,
        verbose_name='Comisión'
    )
    
    net_amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Monto neto',
        help_text='Monto después de comisión'
    )
    
    # Estados
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='PENDING',
        verbose_name='Estado'
    )
    
    # Datos de transacción
    transaction_id = models.CharField(
        max_length=100,
        verbose_name='ID de transacción',
        blank=True,
        null=True
    )
    
    transaction_date = models.DateTimeField(
        verbose_name='Fecha de transacción',
        blank=True,
        null=True
    )
    
    authorization_code = models.CharField(
        max_length=100,
        verbose_name='Código de autorización',
        blank=True,
        null=True
    )
    
    # Datos específicos del método
    payment_data = models.JSONField(
        verbose_name='Datos de pago',
        default=dict,
        blank=True
    )
    
    # Para Yape/Plin
    phone_number = models.CharField(
        max_length=9,
        verbose_name='Número de teléfono',
        blank=True,
        null=True
    )
    
    operation_code = models.CharField(
        max_length=50,
        verbose_name='Código de operación',
        blank=True,
        null=True
    )
    
    # Para transferencia
    bank_name = models.CharField(
        max_length=100,
        verbose_name='Banco',
        blank=True,
        null=True
    )
    
    account_number = models.CharField(
        max_length=50,
        verbose_name='Número de cuenta',
        blank=True,
        null=True
    )
    
    voucher_file = models.FileField(
        upload_to='payments/vouchers/',
        verbose_name='Comprobante',
        blank=True,
        null=True
    )
    
    # Auditoría
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    updated_at = models.DateTimeField(
        auto_now=True,
        verbose_name='Última actualización'
    )
    
    confirmed_at = models.DateTimeField(
        verbose_name='Fecha de confirmación',
        blank=True,
        null=True
    )
    
    confirmed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='payment_confirmations',
        verbose_name='Confirmado por',
        blank=True,
        null=True
    )
    
    # Notas
    notes = models.TextField(
        max_length=500,
        verbose_name='Notas',
        blank=True,
        null=True
    )
    
    class Meta:
        verbose_name = 'Pago'
        verbose_name_plural = 'Pagos'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['payment_code', 'status']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['enrollment', 'status']),
        ]
    
    def __str__(self):
        return f"{self.payment_code} - {self.user.get_full_name()} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """Genera código único si no existe."""
        if not self.payment_code:
            self.payment_code = self.generate_payment_code()
        
        # Calcular monto neto
        if not self.net_amount:
            self.commission = self.payment_method.calculate_commission(self.amount)
            self.net_amount = self.amount - self.commission
        
        super().save(*args, **kwargs)
    
    def generate_payment_code(self):
        """Genera un código único para el pago."""
        import secrets
        return f"PAY-{secrets.token_hex(6).upper()}"
    
    def confirm_payment(self, confirmed_by):
        """
        Confirma el pago y actualiza la inscripción.
        """
        self.status = 'COMPLETED'
        self.confirmed_at = timezone.now()
        self.confirmed_by = confirmed_by
        self.save()
        
        # Actualizar inscripción
        enrollment = self.enrollment
        enrollment.status = 'CONFIRMED'
        enrollment.payment_confirmed = True
        enrollment.payment_confirmed_by = confirmed_by
        enrollment.payment_date = timezone.now()
        enrollment.save()


class PaymentTransaction(models.Model):
    """
    Registro detallado de transacciones con pasarelas de pago.
    """
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.CASCADE,
        related_name='transactions',
        verbose_name='Pago'
    )
    
    # Datos de la transacción
    gateway = models.CharField(
        max_length=50,
        verbose_name='Pasarela'
    )
    
    transaction_type = models.CharField(
        max_length=50,
        verbose_name='Tipo de transacción'
    )
    
    gateway_transaction_id = models.CharField(
        max_length=100,
        verbose_name='ID en pasarela'
    )
    
    # Estados
    status = models.CharField(
        max_length=50,
        verbose_name='Estado'
    )
    
    status_code = models.CharField(
        max_length=20,
        verbose_name='Código de estado',
        blank=True,
        null=True
    )
    
    status_message = models.TextField(
        verbose_name='Mensaje de estado',
        blank=True,
        null=True
    )
    
    # Datos de la transacción
    request_data = models.JSONField(
        verbose_name='Datos de solicitud',
        default=dict
    )
    
    response_data = models.JSONField(
        verbose_name='Datos de respuesta',
        default=dict
    )
    
    # Auditoría
    ip_address = models.GenericIPAddressField(
        verbose_name='Dirección IP'
    )
    
    user_agent = models.TextField(
        verbose_name='User Agent',
        blank=True,
        null=True
    )
    
    created_at = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Fecha de creación'
    )
    
    class Meta:
        verbose_name = 'Transacción de pago'
        verbose_name_plural = 'Transacciones de pago'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.gateway} - {self.gateway_transaction_id} - {self.status}"


class Refund(models.Model):
    """
    Reembolsos de pagos.
    """
    
    REASON_CHOICES = [
        ('DUPLICATE', 'Pago duplicado'),
        ('CANCELLATION', 'Cancelación de curso'),
        ('ERROR', 'Error en el monto'),
        ('OTHER', 'Otro'),
    ]
    
    id = models.UUIDField(
        primary_key=True,
        default=uuid.uuid4,
        editable=False,
        verbose_name='ID'
    )
    
    refund_code = models.CharField(
        max_length=50,
        unique=True,
        verbose_name='Código de reembolso'
    )
    
    payment = models.ForeignKey(
        Payment,
        on_delete=models.PROTECT,
        related_name='refunds',
        verbose_name='Pago original'
    )
    
    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)],
        verbose_name='Monto a reembolsar'
    )
    
    reason = models.CharField(
        max_length=20,
        choices=REASON_CHOICES,
        verbose_name='Motivo'
    )
    
    reason_text = models.TextField(
        max_length=500,
        verbose_name='Descripción del motivo',
        blank=True,
        null=True
    )
    
    # Datos de transacción de reembolso
    gateway_refund_id = models.CharField(
        max_length=100,
        verbose_name='ID de reembolso en pasarela',
        blank=True,
        null=True
    )
    
    refund_date = models.DateTimeField(
        verbose_name='Fecha de reembolso'
    )
    
    status = models.CharField(
        max_length=20,
        choices=[
            ('PENDING', 'Pendiente'),
            ('PROCESSED', 'Procesado'),
            ('FAILED', 'Fallido'),
        ],
        default='PENDING',
        verbose_name='Estado'
    )
    
    # Auditoría
    requested_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='refund_requests',
        verbose_name='Solicitado por'
    )
    
    processed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name='processed_refunds',
        verbose_name='Procesado por',
        blank=True,
        null=True
    )
    
    notes = models.TextField(
        max_length=500,
        verbose_name='Notas',
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
        verbose_name = 'Reembolso'
        verbose_name_plural = 'Reembolsos'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.refund_code} - {self.payment.payment_code} - {self.amount}"
    
    def save(self, *args, **kwargs):
        """Genera código único si no existe."""
        if not self.refund_code:
            import secrets
            self.refund_code = f"REF-{secrets.token_hex(6).upper()}"
        super().save(*args, **kwargs)
