from datetime import datetime
from flask import Blueprint, g, jsonify, request
from psycopg import sql
from werkzeug.security import check_password_hash, generate_password_hash
from .auth import create_access_token, protected
from .db import connection
from .errors import ApiError
from .validation import validate_equipment, validate_movement, STATUSES, CONDITIONS

api = Blueprint('api', __name__, url_prefix='/api')


def body():
    if not request.is_json:
        raise ApiError('Use Content-Type: application/json.', 415)
    return request.get_json()


def identity(value):
    try:
        number = int(value)
        if not 0 < number <= 9223372036854775807:
            raise ValueError()
        return number
    except (ValueError, TypeError):
        raise ApiError('ID inválido.', 422) from None


def dto(row):
    # JSON preserva bigint como string para não perder precisão no JavaScript.
    return {**row, 'id': str(row['id']), 'criadoEm': row['criado_em'].isoformat(),
            'criado_em': row['criado_em'].isoformat()}


def obtain(conn, id, lock=False):
    if lock:
        found = conn.execute('SELECT id FROM inventariar.equipamentos WHERE id=%s FOR UPDATE', (id,)).fetchone()
        if not found:
            raise ApiError('Equipamento não encontrado.', 404)
    row = conn.execute('SELECT * FROM inventariar.vw_patrimonio WHERE id=%s', (id,)).fetchone()
    if not row:
        raise ApiError('Equipamento não encontrado.', 404)
    return row


def reference(conn, table, name):
    query = sql.SQL('INSERT INTO inventariar.{} (nome) VALUES (%s) ON CONFLICT (nome) DO UPDATE SET nome=EXCLUDED.nome RETURNING id').format(sql.Identifier(table))
    return conn.execute(query, (name,)).fetchone()['id']


def validate_auth_body(payload, registration=False):
    if not isinstance(payload, dict):
        raise ApiError('Envie um objeto JSON.', 400)
    allowed = {'email', 'password'} | ({'nome'} if registration else set())
    fields = {key: 'Campo não permitido.' for key in payload if key not in allowed}
    email = payload.get('email')
    password = payload.get('password')
    if not isinstance(email, str) or not 3 <= len(email.strip()) <= 254 or '@' not in email:
        fields['email'] = 'Informe um e-mail válido.'
    if not isinstance(password, str) or not 8 <= len(password) <= 128:
        fields['password'] = 'A senha deve ter de 8 a 128 caracteres.'
    result = {'email': email.strip().lower() if isinstance(email, str) else ''}
    if registration:
        name = payload.get('nome')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 120:
            fields['nome'] = 'Informe um nome de 1 a 120 caracteres.'
        result['nome'] = name.strip() if isinstance(name, str) else ''
    result['password'] = password if isinstance(password, str) else ''
    if fields:
        raise ApiError('Revise os campos indicados.', 422, fields)
    return result


def auth_response(user, status=200):
    public_user = {'id': str(user['id']), 'email': user['email'], 'nome': user['nome']}
    return jsonify(access_token=create_access_token(user['id'], user['email']), user=public_user), status


@api.post('/auth/register')
def register():
    fields = validate_auth_body(body(), registration=True)
    with connection() as conn:
        user = conn.execute(
            '''INSERT INTO inventariar.usuarios (nome, email, senha_hash)
               VALUES (%s, %s, %s)
               RETURNING id, nome, email''',
            (fields['nome'], fields['email'], generate_password_hash(fields['password'])),
        ).fetchone()
    return auth_response(user, 201)


@api.post('/auth/login')
def login():
    fields = validate_auth_body(body())
    with connection() as conn:
        user = conn.execute(
            '''SELECT id, nome, email, senha_hash
               FROM inventariar.usuarios WHERE email = %s''',
            (fields['email'],),
        ).fetchone()
    if not user or not check_password_hash(user['senha_hash'], fields['password']):
        raise ApiError('E-mail ou senha incorretos.', 401)
    return auth_response(user)


def movement(conn, id, current, fields, reason):
    local_id = reference(conn, 'locais', fields.get('local', current['local']))
    conn.execute('CALL inventariar.registrar_movimentacao(%s::bigint,%s::bigint,%s::text,%s::text,%s::text,%s::uuid)',
                 (id, local_id, fields.get('status', current['status']), fields.get('condicao', current['condicao']), reason, g.user_id))


@api.get('/health')
def health():
    with connection() as conn:
        conn.execute('SELECT 1 FROM inventariar.equipamentos LIMIT 1')
    return jsonify(status='ok', fonte='PostgreSQL')


@api.get('/equipamentos')
@protected
def list_equipment():
    conditions, args = [], []  # Listas naturais: composição dos filtros parametrizados.
    for key, allowed in [('status', STATUSES), ('condicao', CONDITIONS)]:
        value = request.args.get(key)
        if value:
            if value not in allowed:
                raise ApiError(f'Filtro {key} inválido.', 422)
            conditions.append(f'{key}=%s')
            args.append(value)
    for key in ['busca', 'local', 'tombamento']:
        value = request.args.get(key, '').strip()
        if len(value) > 200:
            raise ApiError('Filtro deve ter até 200 caracteres.', 422)
        if not value:
            continue
        if key == 'tombamento':
            conditions.append('tombamento=%s')
            args.append(value)
        elif key == 'local':
            conditions.append("position(lower(%s) in lower(local)) > 0")
            args.append(value)
        else:
            conditions.append("position(lower(%s) in lower(nome || ' ' || tombamento || ' ' || categoria || ' ' || local)) > 0")
            args.append(value)
    query = 'SELECT * FROM inventariar.vw_patrimonio'
    if conditions:
        query += ' WHERE ' + ' AND '.join(conditions)
    query += ' ORDER BY criado_em DESC, id DESC'
    with connection() as conn:
        rows = conn.execute(query, args).fetchall()
    return jsonify(equipamentos=[dto(row) for row in rows], fonte='persistidos')


@api.get('/equipamentos/<id>')
@protected
def get_equipment(id):
    with connection() as conn:
        row = obtain(conn, identity(id))
    return jsonify(equipamento=dto(row))


@api.post('/equipamentos')
@protected
def create_equipment():
    fields = validate_equipment(body())
    with connection() as conn:
        category_id = reference(conn, 'categorias', fields['categoria'])
        local_id = reference(conn, 'locais', fields['local'])
        id = conn.execute('''INSERT INTO inventariar.equipamentos
            (nome,tombamento,categoria_id,local_id,status,condicao)
            VALUES (%s,%s,%s,%s,%s,%s) RETURNING id''',
            (fields['nome'], fields['tombamento'], category_id, local_id, fields['status'], fields['condicao'])).fetchone()['id']
        row = obtain(conn, id)
    return jsonify(equipamento=dto(row)), 201, {'Location': f'/api/equipamentos/{id}'}


@api.route('/equipamentos/<id>', methods=['PUT', 'PATCH'])
@protected
def update_equipment(id):
    id = identity(id)
    fields = validate_equipment(body(), partial=request.method == 'PATCH')
    with connection() as conn:
        current = obtain(conn, id, lock=True)
        category_id = reference(conn, 'categorias', fields.get('categoria', current['categoria']))
        conn.execute('UPDATE inventariar.equipamentos SET nome=%s,tombamento=%s,categoria_id=%s WHERE id=%s',
                     (fields.get('nome', current['nome']), fields.get('tombamento', current['tombamento']), category_id, id))
        if any(fields.get(k, current[k]) != current[k] for k in ['local', 'status', 'condicao']):
            movement(conn, id, current, fields, 'Atualização pelo cadastro')
        row = obtain(conn, id)
    return jsonify(equipamento=dto(row))


@api.delete('/equipamentos/<id>')
@protected
def delete_equipment(id):
    with connection() as conn:
        deleted = conn.execute('DELETE FROM inventariar.equipamentos WHERE id=%s RETURNING id', (identity(id),)).fetchone()
        if not deleted:
            raise ApiError('Equipamento não encontrado.', 404)
    return jsonify(message='Equipamento e histórico excluídos.'), 200


@api.post('/equipamentos/<id>/movimentacoes')
@protected
def transfer_equipment(id):
    id = identity(id)
    fields = validate_movement(body())
    with connection() as conn:
        current = obtain(conn, id, lock=True)
        movement(conn, id, current, fields, fields['motivo'])
        row = obtain(conn, id)
    return jsonify(equipamento=dto(row), message='Movimentação registrada.'), 201


@api.get('/equipamentos/<id>/movimentacoes')
@protected
def list_movements(id):
    id = identity(id)
    with connection() as conn:
        obtain(conn, id)
        rows = conn.execute('''SELECT m.id, a.nome AS origem, b.nome AS destino,
            status_anterior, status_novo, condicao_anterior, condicao_nova, motivo, realizado_em
            FROM inventariar.movimentacoes m
            JOIN inventariar.locais a ON a.id=m.local_origem_id
            JOIN inventariar.locais b ON b.id=m.local_destino_id
            WHERE equipamento_id=%s ORDER BY realizado_em DESC, m.id DESC''', (id,)).fetchall()
    return jsonify(movimentacoes=[{**r, 'id': str(r['id']), 'realizado_em': r['realizado_em'].isoformat()} for r in rows])


@api.get('/relatorios/patrimonio')
@protected
def report():
    with connection() as conn:
        rows = conn.execute('''SELECT categoria,local,condicao,status,count(*) AS quantidade
            FROM inventariar.vw_patrimonio GROUP BY categoria,local,condicao,status
            ORDER BY categoria,local,condicao,status''').fetchall()
    return jsonify(relatorio=rows, total=sum(row['quantidade'] for row in rows), fonte='persistidos')
