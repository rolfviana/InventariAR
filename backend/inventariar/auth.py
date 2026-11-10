from functools import wraps
from uuid import UUID

from flask import current_app, g, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from .errors import ApiError


def token_serializer():
    secret = current_app.config.get('SECRET_KEY', '')
    if not secret:
        raise ApiError('Chave local de autenticação não configurada na API.', 503)
    return URLSafeTimedSerializer(secret, salt='inventariar-login')


def create_access_token(user_id, email):
    return token_serializer().dumps({'id': str(user_id), 'email': email})


def authenticate():
    header = request.headers.get('Authorization', '')
    if not header.startswith('Bearer ') or not header[7:].strip():
        raise ApiError('Entre na sua conta para acessar o inventário.', 401)
    try:
        data = token_serializer().loads(header[7:].strip(), max_age=43200)
        return str(UUID(data['id']))
    except SignatureExpired:
        raise ApiError('Sua sessão expirou. Entre novamente.', 401) from None
    except (BadSignature, KeyError, TypeError, ValueError):
        raise ApiError('Sessão inválida. Entre novamente.', 401) from None


def protected(fn):
    @wraps(fn)
    def wrapped(*args, **kwargs):
        g.user_id = authenticate()
        return fn(*args, **kwargs)
    return wrapped
