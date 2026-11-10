"""Configuracao centralizada, carregada ao criar a aplicacao."""
import os
from pathlib import Path
from dotenv import load_dotenv


def settings():
    load_dotenv(Path(__file__).resolve().parents[1] / '.env', override=False)
    return {
        'DATABASE_URL': os.getenv('DATABASE_URL', ''),
        'SECRET_KEY': os.getenv('SECRET_KEY', ''),
        'CORS_ORIGINS': [x.strip() for x in os.getenv('CORS_ORIGINS', 'http://localhost:8080').split(',') if x.strip()],
        'MAX_CONTENT_LENGTH': 16 * 1024,
    }
