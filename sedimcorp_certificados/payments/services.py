"""
Servicios de integración con pasarelas de pago.
Soporte para Yape, Plin e Izipay.
"""

import hashlib
import hmac
import json
import requests
from decimal import Decimal
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from .models import Payment, PaymentTransaction, PaymentMethod


class PaymentService:
    """
    Servicio base para procesamiento de pagos.
    """
    
    def __init__(self, payment_method):
        """
        Inicializa el servicio con el método de pago.
        
        Args:
            payment_method: Objeto PaymentMethod
        """
        self.method = payment_method
        self.config = payment_method.config
    
    def process_payment(self, payment, **kwargs):
        """
        Procesa un pago.
        Método a sobrescribir por cada pasarela.
        """
        raise NotImplementedError


class YapeService(PaymentService):
    """
    Servicio para pagos con Yape.
    """
    
    def __init__(self, payment_method):
        super().__init__(payment_method)
        self.yape_phone = self.config.get('phone_number', '')
        self.yape_name = self.config.get('business_name', 'SEDIMCORP')
    
    def process_payment(self, payment, **kwargs):
        """
        Procesa pago con Yape (verificación manual/automática).
        """
        # Registrar transacción
        transaction = PaymentTransaction.objects.create(
            payment=payment,
            gateway='YAPE',
            transaction_type='PAYMENT',
            gateway_transaction_id=kwargs.get('operation_code', ''),
            status='PENDING',
            request_data={
                'amount': str(payment.amount),
                'phone': payment.phone_number,
                'operation_code': kwargs.get('operation_code', '')
            },
            response_data={},
            ip_address=kwargs.get('ip_address', ''),
            user_agent=kwargs.get('user_agent', '')
        )
        
        # Para Yape, generalmente es confirmación manual
        # o mediante notificación push (webhook)
        
        return {
            'success': True,
            'transaction': transaction,
            'message': 'Pago registrado, pendiente de confirmación'
        }


class PlinService(PaymentService):
    """
    Servicio para pagos con Plin.
    """
    
    def __init__(self, payment_method):
        super().__init__(payment_method)
        self.plin_phone = self.config.get('phone_number', '')
        self.plin_name = self.config.get('business_name', 'SEDIMCORP')
    
    def process_payment(self, payment, **kwargs):
        """
        Procesa pago con Plin.
        """
        transaction = PaymentTransaction.objects.create(
            payment=payment,
            gateway='PLIN',
            transaction_type='PAYMENT',
            gateway_transaction_id=kwargs.get('operation_code', ''),
            status='PENDING',
            request_data={
                'amount': str(payment.amount),
                'phone': payment.phone_number,
                'operation_code': kwargs.get('operation_code', '')
            },
            response_data={},
            ip_address=kwargs.get('ip_address', ''),
            user_agent=kwargs.get('user_agent', '')
        )
        
        return {
            'success': True,
            'transaction': transaction,
            'message': 'Pago registrado, pendiente de confirmación'
        }


class IzipayService(PaymentService):
    """
    Servicio para pagos con Izipay (tarjeta de crédito/débito).
    """
    
    def __init__(self, payment_method):
        super().__init__(payment_method)
        self.api_key = self.config.get('api_key', '')
        self.api_secret = self.config.get('api_secret', '')
        self.endpoint = self.config.get('endpoint', 'https://api.izipay.pe/payment')
        self.is_production = self.config.get('is_production', False)
    
    def generate_signature(self, data):
        """
        Genera firma HMAC-SHA256 para Izipay.
        
        Args:
            data: Datos a firmar
            
        Returns:
            str: Firma generada
        """
        message = json.dumps(data, sort_keys=True)
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            message.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def process_payment(self, payment, **kwargs):
        """
        Procesa pago con Izipay.
        
        Args:
            payment: Objeto Payment
            **kwargs: Datos de la tarjeta y transacción
            
        Returns:
            dict: Resultado del procesamiento
        """
        # Preparar datos para Izipay
        card_data = kwargs.get('card_data', {})
        
        payment_data = {
            'amount': int(payment.amount * 100),  # Izipay usa centimos
            'currency': 'PEN',
            'orderId': payment.payment_code,
            'customer': {
                'email': payment.user.email,
                'firstName': payment.user.first_name,
                'lastName': payment.user.last_name,
                'document': payment.user.document_number,
                'phone': payment.user.phone
            },
            'card': card_data
        }
        
        # Generar firma
        signature = self.generate_signature(payment_data)
        payment_data['signature'] = signature
        
        # Registrar transacción
        transaction = PaymentTransaction.objects.create(
            payment=payment,
            gateway='IZIPAY',
            transaction_type='PAYMENT',
            gateway_transaction_id='',
            status='PROCESSING',
            request_data=payment_data,
            response_data={},
            ip_address=kwargs.get('ip_address', ''),
            user_agent=kwargs.get('user_agent', '')
        )
        
        try:
            # Enviar a Izipay
            response = requests.post(
                self.endpoint,
                json=payment_data,
                headers={
                    'Authorization': f'Bearer {self.api_key}',
                    'Content-Type': 'application/json'
                },
                timeout=30
            )
            
            result = response.json()
            
            # Actualizar transacción
            transaction.response_data = result
            transaction.gateway_transaction_id = result.get('transactionId', '')
            transaction.status = 'COMPLETED' if result.get('status') == 'success' else 'FAILED'
            transaction.save()
            
            if result.get('status') == 'success':
                payment.transaction_id = result.get('transactionId')
                payment.authorization_code = result.get('authorizationCode')
                payment.status = 'COMPLETED'
                payment.save()
                
                # Confirmar inscripción
                payment.confirm_payment(None)  # Confirmación automática
                
                return {
                    'success': True,
                    'transaction': transaction,
                    'message': 'Pago procesado exitosamente',
                    'authorization': result.get('authorizationCode')
                }
            else:
                payment.status = 'FAILED'
                payment.save()
                
                return {
                    'success': False,
                    'transaction': transaction,
                    'message': result.get('message', 'Error en el pago')
                }
                
        except Exception as e:
            transaction.status = 'FAILED'
            transaction.response_data = {'error': str(e)}
            transaction.save()
            
            payment.status = 'FAILED'
            payment.save()
            
            return {
                'success': False,
                'transaction': transaction,
                'message': f'Error de conexión: {str(e)}'
            }


class PaymentServiceFactory:
    """
    Fábrica para crear servicios de pago según el método.
    """
    
    @staticmethod
    def get_service(payment_method_code):
        """
        Obtiene el servicio correspondiente al método de pago.
        
        Args:
            payment_method_code: Código del método de pago
            
        Returns:
            PaymentService: Servicio de pago
        """
        try:
            method = PaymentMethod.objects.get(code=payment_method_code, is_active=True)
        except PaymentMethod.DoesNotExist:
            raise ValueError(f"Método de pago no encontrado: {payment_method_code}")
        
        if method.code == 'YAPE':
            return YapeService(method)
        elif method.code == 'PLIN':
            return PlinService(method)
        elif method.code == 'IZIPAY':
            return IzipayService(method)
        else:
            raise ValueError(f"Método de pago no soportado: {payment_method_code}")
