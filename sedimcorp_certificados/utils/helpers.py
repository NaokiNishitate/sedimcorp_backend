"""
Funciones auxiliares utilizadas en todo el proyecto.
Incluye generación de tokens, envío de emails, paginación y validaciones.
"""

import uuid
import hashlib
import secrets
import hmac
from datetime import datetime, timedelta
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
from rest_framework.response import Response
import logging

logger = logging.getLogger(__name__)


def generate_token(length=32):
    """
    Genera un token seguro aleatorio.
    
    Args:
        length (int): Longitud del token en bytes (el resultado será el doble en hexadecimal)
    
    Returns:
        str: Token hexadecimal seguro
    """
    return secrets.token_hex(length)


def generate_unique_code(prefix='', length=10):
    """
    Genera un código único aleatorio.
    
    Args:
        prefix (str): Prefijo para el código
        length (int): Longitud del código
    
    Returns:
        str: Código único generado
    """
    random_part = secrets.token_hex(length // 2).upper()
    return f"{prefix}{random_part}"[:length]


def generate_enrollment_code(course_code, participant_id):
    """
    Genera un código único para inscripción.
    
    Args:
        course_code (str): Código del curso
        participant_id (uuid): ID del participante
    
    Returns:
        str: Código de inscripción
    """
    base = f"{course_code}{participant_id}{uuid.uuid4()}"
    hash_object = hashlib.sha256(base.encode())
    return f"EN-{hash_object.hexdigest()[:10].upper()}"


def generate_validation_hash(data):
    """
    Genera un hash SHA-256 para validación de certificados.
    
    Args:
        data (str): Datos para generar el hash
    
    Returns:
        str: Hash SHA-256
    """
    if isinstance(data, str):
        data = data.encode('utf-8')
    return hashlib.sha256(data).hexdigest()


def generate_signature(payload, secret):
    """
    Genera una firma HMAC-SHA256 para webhooks.
    
    Args:
        payload (dict): Datos a firmar
        secret (str): Secreto para la firma
    
    Returns:
        str: Firma HMAC-SHA256
    """
    import json
    message = json.dumps(payload, sort_keys=True).encode('utf-8')
    signature = hmac.new(
        secret.encode('utf-8'),
        message,
        hashlib.sha256
    ).hexdigest()
    return signature


def send_email_template(subject, template_name, context, to_emails, from_email=None):
    """
    Envía un email usando una plantilla HTML.
    
    Args:
        subject (str): Asunto del email
        template_name (str): Nombre de la plantilla
        context (dict): Contexto para la plantilla
        to_emails (list): Lista de destinatarios
        from_email (str): Email remitente (opcional)
    
    Returns:
        bool: True si se envió correctamente, False en caso contrario
    """
    try:
        # Renderizar plantilla HTML
        html_message = render_to_string(template_name, context)
        plain_message = strip_tags(html_message)
        
        # Enviar email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=from_email or settings.DEFAULT_FROM_EMAIL,
            recipient_list=to_emails,
            html_message=html_message,
            fail_silently=False,
        )
        logger.info(f"Email enviado correctamente a {to_emails}")
        return True
        
    except Exception as e:
        logger.error(f"Error enviando email a {to_emails}: {str(e)}")
        return False


def paginate_queryset(request, queryset, serializer_class):
    """
    Función auxiliar para paginar querysets.
    
    Args:
        request: Objeto request de Django
        queryset: QuerySet a paginar
        serializer_class: Clase serializadora
    
    Returns:
        Response or None: Respuesta paginada o None si no se pudo paginar
    """
    page_size = request.query_params.get('page_size', 20)
    page = request.query_params.get('page', 1)
    
    paginator = Paginator(queryset, page_size)
    
    try:
        paginated_queryset = paginator.page(page)
    except PageNotAnInteger:
        paginated_queryset = paginator.page(1)
    except EmptyPage:
        paginated_queryset = paginator.page(paginator.num_pages)
    
    serializer = serializer_class(paginated_queryset, many=True, context={'request': request})
    
    return Response({
        'count': paginator.count,
        'total_pages': paginator.num_pages,
        'current_page': paginated_queryset.number,
        'next': paginated_queryset.has_next(),
        'previous': paginated_queryset.has_previous(),
        'results': serializer.data
    })


def format_currency(amount):
    """
    Formatea un monto a moneda peruana.
    
    Args:
        amount (float): Monto a formatear
    
    Returns:
        str: Monto formateado
    """
    return f"S/ {amount:,.2f}"


def get_client_ip(request):
    """
    Obtiene la dirección IP real del cliente.
    
    Args:
        request: Objeto request de Django
    
    Returns:
        str: Dirección IP
    """
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0]
    else:
        ip = request.META.get('REMOTE_ADDR')
    return ip


def validate_peruvian_document(document_type, document_number):
    """
    Valida documentos de identidad peruanos.
    
    Args:
        document_type (str): Tipo de documento
        document_number (str): Número de documento
    
    Returns:
        bool: True si es válido
    """
    if document_type == 'DNI':
        return len(document_number) == 8 and document_number.isdigit()
    elif document_type == 'RUC':
        return len(document_number) == 11 and document_number.isdigit()
    elif document_type == 'CE':
        return len(document_number) >= 9 and len(document_number) <= 12
    return True


def calculate_age(birth_date):
    """
    Calcula la edad basada en la fecha de nacimiento.
    
    Args:
        birth_date (date): Fecha de nacimiento
    
    Returns:
        int: Edad calculada
    """
    from django.utils import timezone
    today = timezone.now().date()
    age = today.year - birth_date.year
    if today.month < birth_date.month or (today.month == birth_date.month and today.day < birth_date.day):
        age -= 1
    return age


def truncate_string(text, max_length=100, suffix='...'):
    """
    Trunca un texto a la longitud máxima especificada.
    
    Args:
        text (str): Texto a truncar
        max_length (int): Longitud máxima
        suffix (str): Sufijo a agregar
    
    Returns:
        str: Texto truncado
    """
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_date_range(start_date, end_date):
    """
    Parsea un rango de fechas y retorna una lista de fechas.
    
    Args:
        start_date (date): Fecha de inicio
        end_date (date): Fecha de fin
    
    Returns:
        list: Lista de fechas en el rango
    """
    from datetime import timedelta
    dates = []
    current = start_date
    while current <= end_date:
        dates.append(current)
        current += timedelta(days=1)
    return dates


def format_file_size(size_in_bytes):
    """
    Formatea el tamaño de un archivo en unidades legibles.
    
    Args:
        size_in_bytes (int): Tamaño en bytes
    
    Returns:
        str: Tamaño formateado
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024.0:
            return f"{size_in_bytes:.1f} {unit}"
        size_in_bytes /= 1024.0
    return f"{size_in_bytes:.1f} TB"


def clean_phone_number(phone):
    """
    Limpia y formatea un número de teléfono peruano.
    
    Args:
        phone (str): Número de teléfono
    
    Returns:
        str: Número formateado
    """
    # Eliminar caracteres no numéricos
    cleaned = ''.join(filter(str.isdigit, phone))
    
    # Formato para celular (9 dígitos)
    if len(cleaned) == 9 and cleaned.startswith('9'):
        return cleaned
    
    # Formato para teléfono fijo (7 dígitos con código de área)
    elif len(cleaned) == 7:
        return f"044{cleaned}"
    
    return cleaned
