"""
Configuración del panel de administración para el módulo de pagos.
"""

from django.contrib import admin
from django.utils import timezone
from django.utils.html import format_html
from .models import PaymentMethod, Payment, PaymentTransaction, Refund


@admin.register(PaymentMethod)
class PaymentMethodAdmin(admin.ModelAdmin):
    """
    Configuración para métodos de pago en el admin.
    """
    
    list_display = [
        'code', 'name', 'is_active', 'is_default',
        'min_amount', 'max_amount', 'order'
    ]
    
    list_filter = ['is_active', 'is_default']
    search_fields = ['code', 'name']
    list_editable = ['is_active', 'is_default', 'order']
    
    fieldsets = (
        ('Información Básica', {
            'fields': ('code', 'name', 'description', 'icon')
        }),
        ('Límites y Comisiones', {
            'fields': ('min_amount', 'max_amount', 'commission_percentage', 'commission_fixed')
        }),
        ('Configuración', {
            'fields': ('config',),
            'classes': ('collapse',)
        }),
        ('Control', {
            'fields': ('is_active', 'is_default', 'order')
        }),
    )


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    """
    Configuración para pagos en el admin.
    """
    
    list_display = [
        'payment_code', 'user', 'enrollment', 'payment_method',
        'amount', 'status', 'created_at', 'confirmed_at'
    ]
    
    list_filter = ['status', 'payment_method', 'created_at']
    search_fields = ['payment_code', 'user__email', 'enrollment__enrollment_code']
    
    readonly_fields = [
        'payment_code', 'commission', 'net_amount',
        'created_at', 'updated_at', 'confirmed_at'
    ]
    
    fieldsets = (
        ('Información del Pago', {
            'fields': (
                'payment_code', 'enrollment', 'user', 'payment_method',
                'amount', 'commission', 'net_amount', 'status'
            )
        }),
        ('Datos de Transacción', {
            'fields': (
                'transaction_id', 'transaction_date', 'authorization_code',
                'payment_data'
            )
        }),
        ('Datos de Yape/Plin', {
            'fields': ('phone_number', 'operation_code'),
            'classes': ('collapse',)
        }),
        ('Datos de Transferencia', {
            'fields': ('bank_name', 'account_number', 'voucher_file'),
            'classes': ('collapse',)
        }),
        ('Auditoría', {
            'fields': ('confirmed_at', 'confirmed_by', 'notes')
        }),
    )
    
    actions = ['confirm_payments', 'cancel_payments']
    
    def confirm_payments(self, request, queryset):
        """Confirma pagos seleccionados."""
        for payment in queryset:
            if payment.status != 'COMPLETED':
                payment.status = 'COMPLETED'
                payment.confirmed_at = timezone.now()
                payment.confirmed_by = request.user
                payment.save()
                payment.confirm_payment(request.user)
        
        self.message_user(request, f'{queryset.count()} pagos confirmados.')
    confirm_payments.short_description = 'Confirmar pagos seleccionados'
    
    def cancel_payments(self, request, queryset):
        """Cancela pagos pendientes."""
        updated = queryset.filter(status='PENDING').update(
            status='CANCELLED'
        )
        self.message_user(request, f'{updated} pagos cancelados.')
    cancel_payments.short_description = 'Cancelar pagos pendientes'


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    """
    Configuración para transacciones en el admin.
    """
    
    list_display = [
        'id', 'payment', 'gateway', 'gateway_transaction_id',
        'status', 'created_at'
    ]
    
    list_filter = ['gateway', 'status', 'created_at']
    search_fields = ['gateway_transaction_id', 'payment__payment_code']
    readonly_fields = ['payment', 'gateway', 'transaction_type', 'gateway_transaction_id',
                       'status', 'status_code', 'status_message', 'request_data',
                       'response_data', 'ip_address', 'user_agent', 'created_at']
    
    def has_add_permission(self, request):
        return False
    
    def has_change_permission(self, request, obj=None):
        return False


@admin.register(Refund)
class RefundAdmin(admin.ModelAdmin):
    """
    Configuración para reembolsos en el admin.
    """
    
    list_display = [
        'refund_code', 'payment', 'amount', 'reason',
        'status', 'created_at', 'refund_date'
    ]
    
    list_filter = ['status', 'reason', 'created_at']
    search_fields = ['refund_code', 'payment__payment_code']
    readonly_fields = ['refund_code', 'created_at', 'updated_at']
    
    fieldsets = (
        ('Información del Reembolso', {
            'fields': ('refund_code', 'payment', 'amount', 'reason', 'reason_text')
        }),
        ('Estado', {
            'fields': ('status', 'refund_date', 'gateway_refund_id')
        }),
        ('Auditoría', {
            'fields': ('requested_by', 'processed_by', 'notes')
        }),
    )
    
    actions = ['process_refunds']
    
    def process_refunds(self, request, queryset):
        """Marca reembolsos como procesados."""
        updated = queryset.update(
            status='PROCESSED',
            processed_by=request.user
        )
        self.message_user(request, f'{updated} reembolsos procesados.')
    process_refunds.short_description = 'Procesar reembolsos seleccionados'
