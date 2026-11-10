import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

import setup_local_db
from inventariar import create_app
from inventariar.auth import create_access_token
from inventariar.errors import ApiError
from inventariar.routes import validate_auth_body
from inventariar.validation import validate_equipment, validate_movement


@pytest.fixture
def client():
    app = create_app({"TESTING": True, "DATABASE_URL": "", "SECRET_KEY": "test-key"})
    return app.test_client()


def test_equipment_validation_trims_text_and_applies_defaults():
    result = validate_equipment({
        "nome": "  Notebook  ",
        "tombamento": " IFRO-001 ",
        "categoria": " Informática ",
        "local": " Laboratório 2 ",
    })

    assert result == {
        "nome": "Notebook",
        "tombamento": "IFRO-001",
        "categoria": "Informática",
        "local": "Laboratório 2",
        "status": "ativo",
        "condicao": "excelente",
    }


def test_equipment_validation_rejects_unknown_fields():
    with pytest.raises(ApiError) as error:
        validate_equipment({"nome": "Notebook", "unexpected": True})

    assert error.value.status == 422
    assert "unexpected" in error.value.fields


def test_movement_validation_requires_reason():
    with pytest.raises(ApiError) as error:
        validate_movement({"local": "Laboratório 2", "motivo": " "})

    assert error.value.status == 422
    assert "motivo" in error.value.fields


def test_protected_endpoint_returns_json_without_a_token(client):
    response = client.get("/api/equipamentos")

    assert response.status_code == 401
    assert response.is_json
    assert response.json["error"]["message"]


def test_health_reports_missing_database_as_json(client):
    response = client.get("/api/health")

    assert response.status_code == 503
    assert response.is_json
    assert response.json["error"]["message"] == "PostgreSQL não configurado na API."


def test_database_setup_saves_encoded_url_and_preserves_settings(tmp_path, monkeypatch):
    env_file = tmp_path / ".env"
    env_file.write_text("CORS_ORIGINS=http://localhost:8080\n", encoding="utf-8")
    monkeypatch.setattr(setup_local_db, "ENV_FILE", env_file)

    setup_local_db.save_local_settings(
        "postgresql://postgres:local%3Ap%40ss@127.0.0.1:5432/inventariar"
    )

    content = env_file.read_text(encoding="utf-8")
    assert "CORS_ORIGINS=http://localhost:8080" in content
    assert "DATABASE_URL=postgresql://postgres:local%3Ap%40ss@127.0.0.1:5432/inventariar" in content
    assert "SECRET_KEY=" in content


def test_local_account_validation_normalizes_email():
    result = validate_auth_body({
        "nome": " Ana ",
        "email": " ANA@EXEMPLO.COM ",
        "password": "senha-segura-123",
    }, registration=True)

    assert result == {
        "nome": "Ana",
        "email": "ana@exemplo.com",
        "password": "senha-segura-123",
    }


def test_local_account_validation_rejects_short_password():
    with pytest.raises(ApiError) as error:
        validate_auth_body({"email": "ana@example.com", "password": "123"})

    assert error.value.status == 422
    assert "password" in error.value.fields


def test_signed_token_is_accepted_by_protected_endpoint(client):
    with client.application.app_context():
        token = create_access_token("0a93130b-8f46-43f3-8002-4c97ee193f08", "ana@example.com")

    response = client.get("/api/equipamentos", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 503
    assert response.json["error"]["message"] == "PostgreSQL não configurado na API."


def test_invalid_local_token_is_rejected(client):
    response = client.get("/api/equipamentos", headers={"Authorization": "Bearer token-invalido"})

    assert response.status_code == 401
    assert response.is_json
