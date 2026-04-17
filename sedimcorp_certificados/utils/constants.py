"""
Constantes globales utilizadas en todo el proyecto.
"""

# Tipos de usuario
USER_TYPES = {
    'ADMIN': 'Administrador',
    'STAFF': 'Personal Administrativo',
    'INSTRUCTOR': 'Instructor',
    'PARTICIPANT': 'Participante',
}

# Estados de curso
COURSE_STATUS = {
    'DRAFT': 'Borrador',
    'PUBLISHED': 'Publicado',
    'IN_PROGRESS': 'En progreso',
    'COMPLETED': 'Finalizado',
    'CANCELLED': 'Cancelado',
}

# Estados de inscripción
ENROLLMENT_STATUS = {
    'PENDING': 'Pendiente',
    'CONFIRMED': 'Confirmada',
    'IN_PROGRESS': 'En progreso',
    'COMPLETED': 'Completada',
    'CERTIFIED': 'Certificado',
    'CANCELLED': 'Cancelada',
    'REFUNDED': 'Reembolsada',
}

# Métodos de pago
PAYMENT_METHODS = {
    'YAPE': 'Yape',
    'PLIN': 'Plin',
    'IZIPAY': 'Izipay',
    'TRANSFER': 'Transferencia bancaria',
    'CASH': 'Efectivo',
}

# Tipos de documento
DOCUMENT_TYPES = {
    'DNI': 'DNI',
    'CE': 'Carnet de Extranjería',
    'PASSPORT': 'Pasaporte',
    'RUC': 'RUC',
}

# Mensajes de error comunes
ERROR_MESSAGES = {
    'not_found': 'El recurso solicitado no existe',
    'permission_denied': 'No tienes permisos para realizar esta acción',
    'invalid_data': 'Los datos proporcionados son inválidos',
    'server_error': 'Error interno del servidor',
    'duplicate_entry': 'Ya existe un registro con estos datos',
}

# Configuración de email
EMAIL_TEMPLATES = {
    'welcome': 'emails/welcome.html',
    'password_reset': 'emails/password_reset.html',
    'certificate_issued': 'emails/certificate_issued.html',
    'payment_confirmed': 'emails/payment_confirmed.html',
    'enrollment_confirmed': 'emails/enrollment_confirmed.html',
}

# Roles y permisos
ROLE_HIERARCHY = {
    'ADMIN': 100,
    'STAFF': 80,
    'INSTRUCTOR': 60,
    'PARTICIPANT': 40,
}

# Límites del sistema
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
ALLOWED_FILE_TYPES = ['pdf', 'jpg', 'jpeg', 'png']
MAX_ENROLLMENTS_PER_COURSE = 100
MIN_PASSWORD_LENGTH = 8
