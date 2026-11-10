from getpass import getpass
from pathlib import Path
import secrets
from urllib.parse import quote

import psycopg
from dotenv import dotenv_values
from psycopg import sql


ROOT = Path(__file__).resolve().parents[1]
SCHEMA_FILE = ROOT / "backend" / "sql" / "001_schema.sql"
AUTH_MIGRATION_FILE = ROOT / "backend" / "sql" / "002_autenticacao_local.sql"
ENV_FILE = ROOT / "backend" / ".env"
DATABASE_NAME = "inventariar"
DATABASE_USER = "postgres"
DATABASE_HOST = "127.0.0.1"
DATABASE_PORT = 5432


def save_local_settings(database_url):
    existing = ENV_FILE.read_text(encoding="utf-8").splitlines() if ENV_FILE.exists() else []
    values = {"DATABASE_URL": database_url, "SECRET_KEY": ""}
    obsolete = {"AUTH_URL", "AUTH_PUBLISHABLE_KEY"}
    for line in existing:
        if "=" in line and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            if key.strip() == "SECRET_KEY":
                values["SECRET_KEY"] = value.strip()
    if not values["SECRET_KEY"]:
        values["SECRET_KEY"] = secrets.token_urlsafe(48)

    updated = []
    replaced = set()
    for line in existing:
        if line.lstrip().startswith("# URL pública do serviço de autenticação"):
            continue
        if "=" in line and not line.lstrip().startswith("#"):
            key = line.split("=", 1)[0].strip()
            if key in obsolete:
                continue
            if key in values:
                if key not in replaced:
                    updated.append(f"{key}={values[key]}")
                    replaced.add(key)
            else:
                updated.append(line)
        else:
            updated.append(line)
    for key, value in values.items():
        if key not in replaced:
            updated.append(f"{key}={value}")
    ENV_FILE.write_text("\n".join(updated) + "\n", encoding="utf-8")


def configure_schema(database):
    schema_exists = database.execute(
        "SELECT 1 FROM pg_namespace WHERE nspname = 'inventariar'"
    ).fetchone()
    if not schema_exists:
        database.execute(SCHEMA_FILE.read_text(encoding="utf-8"))
    else:
        tables = database.execute(
            """
            SELECT count(*)
            FROM information_schema.tables
            WHERE table_schema = 'inventariar'
              AND table_name IN ('categorias', 'locais', 'equipamentos', 'movimentacoes')
            """
        ).fetchone()[0]
        view = database.execute(
            """
            SELECT 1 FROM information_schema.views
            WHERE table_schema = 'inventariar' AND table_name = 'vw_patrimonio'
            """
        ).fetchone()
        procedures = database.execute(
            """
            SELECT count(*)
            FROM information_schema.routines
            WHERE routine_schema = 'inventariar'
              AND routine_name IN ('registrar_movimentacao', 'gerar_relatorio')
            """
        ).fetchone()[0]
        if tables != 4 or not view or procedures != 2:
            raise SystemExit(
                "O schema inventariar existe, mas está incompleto. "
                "Não apliquei alterações para evitar afetar os dados existentes."
            )
    database.commit()
    database.execute(AUTH_MIGRATION_FILE.read_text(encoding="utf-8"))


def main():
    if not SCHEMA_FILE.is_file() or not AUTH_MIGRATION_FILE.is_file():
        raise SystemExit("Não encontrei os arquivos SQL necessários dentro da pasta backend.")

    values = dotenv_values(ENV_FILE)
    database_url = values.get("DATABASE_URL", "")
    try:
        if database_url:
            with psycopg.connect(database_url, connect_timeout=5) as database:
                configure_schema(database)
        else:
            password = getpass("Digite a senha local de postgres (não aparecerá na tela): ")
            if not password:
                raise SystemExit("A senha não pode ficar vazia.")
            encoded_password = quote(password, safe="")
            database_url = (
                f"postgresql://{DATABASE_USER}:{encoded_password}"
                f"@{DATABASE_HOST}:{DATABASE_PORT}/{DATABASE_NAME}"
            )
            with psycopg.connect(
                host=DATABASE_HOST,
                port=DATABASE_PORT,
                dbname="postgres",
                user=DATABASE_USER,
                password=password,
                connect_timeout=5,
                autocommit=True,
            ) as admin:
                exists = admin.execute(
                    "SELECT 1 FROM pg_database WHERE datname = %s",
                    (DATABASE_NAME,),
                ).fetchone()
                if not exists:
                    admin.execute(
                        sql.SQL("CREATE DATABASE {}").format(sql.Identifier(DATABASE_NAME))
                    )
            with psycopg.connect(database_url, connect_timeout=5) as database:
                configure_schema(database)

        save_local_settings(database_url)
    except psycopg.OperationalError:
        raise SystemExit(
            "Não foi possível conectar ao PostgreSQL. Confira se o serviço está iniciado "
            "e se a conexão local configurada está correta."
        ) from None
    except psycopg.Error as error:
        raise SystemExit(
            f"O PostgreSQL recusou a configuração ({type(error).__name__}). "
            "O arquivo .env não foi atualizado; verifique o banco antes de tentar novamente."
        ) from None

    print("Banco inventariar verificado e configurado.")
    print("A conexão foi salva em backend/.env, arquivo ignorado pelo Git.")
    print("O login local foi preparado e uma chave de sessão segura foi gerada.")


if __name__ == "__main__":
    main()
