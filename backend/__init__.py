from flask import Flask, jsonify
from flask_cors import CORS
from werkzeug.exceptions import HTTPException
from .config import settings
from .errors import ApiError
from .routes import api


def create_app(overrides=None):
    app = Flask(__name__)
    app.config.update(settings())
    if overrides:
        app.config.update(overrides)
    CORS(app, resources={r'/api/*': {'origins': app.config['CORS_ORIGINS']}},
         allow_headers=['Authorization', 'Content-Type'], methods=['GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'OPTIONS'])
    app.register_blueprint(api)

    @app.errorhandler(ApiError)
    def api_error(error):
        return jsonify(error={'message': error.message, 'fields': error.fields}), error.status

    @app.errorhandler(HTTPException)
    def http_error(error):
        messages = {400: 'JSON inválido.', 404: 'Endpoint não encontrado.', 405: 'Método não permitido.', 413: 'JSON muito grande.'}
        return jsonify(error={'message': messages.get(error.code, 'Requisição inválida.'), 'fields': {}}), error.code

    @app.errorhandler(Exception)
    def unexpected(error):
        # Não incluir parâmetros, DSN, tokens ou exceções brutas na resposta/log.
        app.logger.error('Falha interna não prevista: %s', type(error).__name__)
        return jsonify(error={'message': 'Falha interna. A operação não foi concluída.', 'fields': {}}), 500

    @app.after_request
    def private_response(response):
        response.headers['Cache-Control'] = 'no-store'
        return response

    return app
