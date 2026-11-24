import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    host: str = os.getenv('POSTGRES_HOST', 'localhost')
    port: int = int(os.getenv('POSTGRES_PORT', '5432'))
    database: str = os.getenv('POSTGRES_DB', 'infrapulse')
    user: str = os.getenv('POSTGRES_USER', 'infrapulse')
    password: str = os.getenv('POSTGRES_PASSWORD', '')
    token: str = os.getenv('INGEST_TOKEN', '')
    threshold: float = float(os.getenv('ALERT_THRESHOLD', '85'))
    stale_seconds: int = int(os.getenv('STALE_SECONDS', '120'))

settings = Settings()
if not 0 < settings.threshold <= 100 or settings.stale_seconds <= 0:
    raise ValueError('Invalid alert threshold or stale interval')
