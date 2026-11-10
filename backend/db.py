from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from flask import current_app
from .errors import ApiError


@contextmanager
def connection():
    url = current_app.config['DATABASE_URL']
    if not url:
        raise ApiError('PostgreSQL não configurado na API.', 503)
    try:
        # O contexto faz commit só ao concluir; qualquer exceção faz rollback.
        with psycopg.connect(url, row_factory=dict_row, connect_timeout=5) as conn:
            yield conn
    except psycopg.errors.UniqueViolation:
        raise ApiError('Tombamento já cadastrado.', 409, {'tombamento': 'Use um tombamento único.'}) from None
    except psycopg.errors.NoDataFound:
        raise ApiError('Equipamento não encontrado.', 404) from None
    except (psycopg.errors.CheckViolation, psycopg.errors.InvalidParameterValue, psycopg.errors.NotNullViolation, psycopg.errors.ForeignKeyViolation):
        raise ApiError('Dados inválidos. Verifique local, status e condição.', 422) from None
    except psycopg.OperationalError:
        raise ApiError('PostgreSQL indisponível. A operação não foi concluída.', 503) from None
    except psycopg.DatabaseError:
        raise ApiError('Falha na transação. Nenhuma alteração desta operação foi salva.', 500) from None
