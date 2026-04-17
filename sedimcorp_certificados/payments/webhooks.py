"""
Webhooks para recibir notificaciones de pasarelas de pago.
"""

import json
import hashlib
import hmac
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils import timezone
from .models import Payment, PaymentTransaction, PaymentMethod


@csrf_exempt
@require_POST
def izipay_webhook(request):
    """
    Webhook para notificaciones de Izipay.
    """
    try:
        payload = json.loads(request.body)
        
        # Obtener método de pago Izipay
        izipay_method = PaymentMethod.objects.get(code='IZIPAY')
        config = izipay_method.config
        
        # Verificar firma
        received_signature = request.headers.get('X-Signature')
        expected_signature = hmac.new(
            config.get('api_secret', '').encode('utf-8'),
            request.body,
            hashlib.sha256
        ).hexdigest()
        
        if received_signature != expected_signature:
            return JsonResponse({'error': 'Firma inválida'}, status=401)
        
        # Procesar notificación
        transaction_id = payload.get('transactionId')
        status = payload.get('status')
        order_id = payload.get('orderId')
        
        try:
            payment = Payment.objects.get(payment_code=order_id)
            
            # Registrar transacción
            PaymentTransaction.objects.create(
                payment=payment,
                gateway='IZIPAY',
                transaction_type='WEBHOOK',
                gateway_transaction_id=transaction_id,
                status=status,
                request_data={},
                response_data=payload,
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            if status == 'success':
                payment.transaction_id = transaction_id
                payment.authorization_code = payload.get('authorizationCode')
                payment.status = 'COMPLETED'
                payment.save()
                
                # Confirmar inscripción
                payment.confirm_payment(None)
                
            elif status == 'failed':
                payment.status = 'FAILED'
                payment.save()
            
        except Payment.DoesNotExist:
            return JsonResponse({'error': 'Pago no encontrado'}, status=404)
        
        return JsonResponse({'status': 'ok'})
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)


@csrf_exempt
@require_POST
def yape_webhook(request):
    """
    Webhook para notificaciones de Yape (simulado).
    """
    try:
        payload = json.loads(request.body)
        
        operation_code = payload.get('operationCode')
        phone = payload.get('phone')
        amount = payload.get('amount')
        status = payload.get('status', 'COMPLETED')
        
        # Buscar pago pendiente con estos datos
        payment = Payment.objects.filter(
            phone_number=phone,
            operation_code=operation_code,
            amount=amount,
            status='PENDING'
        ).first()
        
        if payment:
            if status == 'COMPLETED':
                payment.status = 'COMPLETED'
                payment.save()
                payment.confirm_payment(None)
            
            # Registrar transacción
            PaymentTransaction.objects.create(
                payment=payment,
                gateway='YAPE',
                transaction_type='WEBHOOK',
                gateway_transaction_id=operation_code,
                status=status,
                request_data={},
                response_data=payload,
                ip_address=request.META.get('REMOTE_ADDR', '')
            )
            
            return JsonResponse({'status': 'ok'})
        
        return JsonResponse({'error': 'Pago no encontrado'}, status=404)
        
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=400)
