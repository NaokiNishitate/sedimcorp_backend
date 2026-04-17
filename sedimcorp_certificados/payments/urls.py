"""
Configuración de URLs para el módulo de pagos.
"""

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views
from . import webhooks

router = DefaultRouter()
router.register(r'methods', views.PaymentMethodViewSet)
router.register(r'payments', views.PaymentViewSet)
router.register(r'refunds', views.RefundViewSet)
router.register(r'transactions', views.PaymentTransactionViewSet)

urlpatterns = [
    path('', include(router.urls)),
    
    # Webhooks
    path('webhooks/izipay/', webhooks.izipay_webhook, name='izipay-webhook'),
    path('webhooks/yape/', webhooks.yape_webhook, name='yape-webhook'),
]
