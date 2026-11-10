from .errors import ApiError

STATUSES = ('ativo', 'inativo')
CONDITIONS = ('excelente', 'bom', 'aceitavel', 'regular', 'ruim')
LIMITS = {'nome': 200, 'tombamento': 80, 'categoria': 120, 'local': 160}


def validate_equipment(body, partial=False):
    if not isinstance(body, dict):
        raise ApiError('Envie um objeto JSON.', 400)
    allowed = set(LIMITS) | {'status', 'condicao'}
    fields = {k: 'Campo não permitido.' for k in body if k not in allowed}
    result = {}
    for key, maximum in LIMITS.items():
        if partial and key not in body:
            continue
        value = body.get(key)
        if not isinstance(value, str) or not 1 <= len(value.strip()) <= maximum:
            fields[key] = f'Informe de 1 a {maximum} caracteres.'
        else:
            result[key] = value.strip()
    for key, choices, default in [('status', STATUSES, 'ativo'), ('condicao', CONDITIONS, 'excelente')]:
        if partial and key not in body:
            continue
        value = body.get(key, default)
        if not isinstance(value, str) or value not in choices:
            fields[key] = 'Valor permitido: ' + ', '.join(choices)
        else:
            result[key] = value
    if fields:
        raise ApiError('Revise os campos indicados.', 422, fields)
    if not result:
        raise ApiError('Informe ao menos um campo para atualizar.', 422)
    return result


def validate_movement(body):
    if not isinstance(body, dict):
        raise ApiError('Envie um objeto JSON.', 400)
    allowed = {'local', 'status', 'condicao', 'motivo'}
    if set(body) - allowed:
        raise ApiError('Há campos não permitidos na movimentação.', 422)
    result = validate_equipment({k: v for k, v in body.items() if k != 'motivo'}, partial=True)
    reason = body.get('motivo')
    if not isinstance(reason, str) or not 1 <= len(reason.strip()) <= 500:
        raise ApiError('Informe o motivo da movimentação (1 a 500 caracteres).', 422, {'motivo': 'Motivo obrigatório.'})
    result['motivo'] = reason.strip()
    return result
