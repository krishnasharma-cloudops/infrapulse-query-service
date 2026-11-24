import os, math, time, json, urllib.request, urllib.error

def main():
    url=os.getenv('API_URL','http://localhost:8000').rstrip('/')+'/api/v1/metrics'
    token=os.environ['INGEST_TOKEN']
    while True:
        t=time.time()/30
        for name,region,base,disk in [('demo-web-01','eastus',35,42),('demo-api-01','eastus',55,63),('demo-db-01','centralindia',82,91)]:
            payload=dict(hostname=name,region=region,cpu=round(base+10*math.sin(t),1),memory=round(62+12*math.cos(t),1),disk=disk)
            req=urllib.request.Request(url,data=json.dumps(payload).encode(),headers={'Content-Type':'application/json','X-Ingest-Token':token},method='POST')
            try:
                with urllib.request.urlopen(req,timeout=10) as res:
                    print(name,res.status,flush=True)
            except OSError as exc:
                print('Demo retry:',exc,flush=True)
        time.sleep(15)

if __name__=='__main__': main()
