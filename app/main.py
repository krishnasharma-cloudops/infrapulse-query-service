import secrets
import psycopg
from fastapi import FastAPI, Header, HTTPException, Query
from fastapi.responses import JSONResponse
from .config import settings
from .database import connection
from .schemas import MetricInput
from .logic import status

app = FastAPI(title='InfraPulse API', version='1.0.0')
@app.exception_handler(psycopg.Error)
async def database_error(request, exc):
    return JSONResponse(status_code=503, content={'detail':'Database operation unavailable'})

@app.get('/health/live')
def live():
    return {'status':'ok'}

@app.get('/health/ready')
def ready():
    with connection() as c:
        c.execute('SELECT 1 FROM servers LIMIT 1')
    return {'status':'ready'}

@app.post('/api/v1/metrics', status_code=201)
def ingest(payload: MetricInput, x_ingest_token: str = Header(default='')):
    if not settings.token or not secrets.compare_digest(x_ingest_token.encode(), settings.token.encode()):
        raise HTTPException(401, 'Invalid ingestion token')
    with connection() as c:
        server = c.execute('''
            INSERT INTO servers(hostname,region) VALUES (%s,%s)
            ON CONFLICT(hostname) DO UPDATE SET region=EXCLUDED.region RETURNING id
        ''', (payload.hostname,payload.region)).fetchone()
        sid = server['id']
        c.execute('INSERT INTO metrics(server_id,cpu,memory,disk) VALUES (%s,%s,%s,%s)',
                  (sid,payload.cpu,payload.memory,payload.disk))
        for metric in ('cpu','memory','disk'):
            value = getattr(payload,metric)
            if value >= settings.threshold:
                c.execute('''INSERT INTO alerts(server_id,metric,value) VALUES (%s,%s,%s)
                    ON CONFLICT(server_id,metric) WHERE resolved_at IS NULL
                    DO UPDATE SET value=EXCLUDED.value''',(sid,metric,value))
            else:
                c.execute('UPDATE alerts SET resolved_at=now() WHERE server_id=%s AND metric=%s AND resolved_at IS NULL',(sid,metric))
    return {'server_id':sid,'accepted':True}

@app.get('/api/v1/servers')
def servers():
    with connection() as c:
        rows = c.execute('''SELECT s.id,s.hostname,s.region,m.cpu,m.memory,m.disk,m.collected_at,
            EXTRACT(EPOCH FROM now()-m.collected_at)::float AS age_seconds
            FROM servers s LEFT JOIN LATERAL (SELECT * FROM metrics WHERE server_id=s.id
            ORDER BY collected_at DESC,id DESC LIMIT 1) m ON true ORDER BY s.hostname''').fetchall()
    for row in rows:
        row['status'] = status(row.pop('age_seconds'), [row['cpu'],row['memory'],row['disk']],settings.threshold,settings.stale_seconds)
    return rows

@app.get('/api/v1/summary')
def summary():
    rows = servers()
    active = [r for r in rows if r['status'] != 'offline']
    return {'total':len(rows), 'online':sum(r['status']=='online' for r in rows),
        'warning':sum(r['status']=='warning' for r in rows), 'offline':len(rows)-len(active),
        'avg_cpu':round(sum(r['cpu'] for r in active)/len(active),1) if active else None}

@app.get('/api/v1/servers/{server_id}/metrics')
def history(server_id: int, hours: int=Query(6,ge=1,le=168), limit: int=Query(300,ge=1,le=2000)):
    with connection() as c:
        if not c.execute('SELECT id FROM servers WHERE id=%s',(server_id,)).fetchone():
            raise HTTPException(404,'Server not found')
        rows=c.execute('''SELECT collected_at,cpu,memory,disk FROM metrics
            WHERE server_id=%s AND collected_at >= now() - %s * interval '1 hour'
            ORDER BY collected_at DESC,id DESC LIMIT %s''',(server_id,hours,limit)).fetchall()
    return list(reversed(rows))

@app.get('/api/v1/alerts')
def alerts(active: bool=True, limit: int=Query(100,ge=1,le=500)):
    with connection() as c:
        return c.execute('''SELECT a.*,s.hostname FROM alerts a JOIN servers s ON s.id=a.server_id
            WHERE (NOT %s OR a.resolved_at IS NULL) ORDER BY a.opened_at DESC,a.id DESC LIMIT %s''',(active,limit)).fetchall()
