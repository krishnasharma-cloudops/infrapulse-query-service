from contextlib import contextmanager
import psycopg
from psycopg.rows import dict_row
from .config import settings

@contextmanager
def connection():
    with psycopg.connect(host=settings.host, port=settings.port,
                         dbname=settings.database, user=settings.user,
                         password=settings.password, connect_timeout=5,
                         row_factory=dict_row) as conn:
        yield conn
