import os, socket, json, time, urllib.request, urllib.error
import psutil

def main():
    url=os.getenv('API_URL','http://localhost:8000').rstrip('/')+'/api/v1/metrics'
    token=os.environ['INGEST_TOKEN']
    interval=max(5,int(os.getenv('COLLECT_INTERVAL','15')))
    while True:
        payload={'hostname':os.getenv('MONITORED_HOST',socket.gethostname()),
                 'region':os.getenv('REGION','local'), 'cpu':psutil.cpu_percent(interval=1),
                 'memory':psutil.virtual_memory().percent,
                 'disk':psutil.disk_usage(os.getenv('MONITOR_PATH','/')).percent}
        request=urllib.request.Request(url,data=json.dumps(payload).encode(),
                  headers={'Content-Type':'application/json','X-Ingest-Token':token},method='POST')
        try:
            with urllib.request.urlopen(request,timeout=10) as response:
                print('Metrics sent:',response.status,flush=True)
        except (OSError,urllib.error.URLError) as exc:
            print('Send failed:',exc,flush=True)
        time.sleep(interval)

if __name__=='__main__':
    main()
