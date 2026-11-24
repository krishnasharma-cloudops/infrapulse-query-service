# InfraPulse Query Service — Beginner Step-by-Step Guide (Hindi / Hinglish)

**Repository 2 of 3.** Backend browser aur database ke beech ka bridge hai. API (Application Programming Interface) ek URL ke through JSON data deta hai. FastAPI Python framework hai; Uvicorn HTTP server hai; psycopg PostgreSQL driver hai.

## Project ko samjhein (zero se)

InfraPulse ek server monitoring application hai. Database data rakhta hai, backend data padhta/likhta hai aur frontend browser mein data dikhata hai. Agent CPU (processor ka usage), RAM (memory ka usage) aur disk (storage ka usage) bhejta hai.

```text
Agent --> FastAPI --> PostgreSQL
Browser --> React/Vite --> FastAPI --> PostgreSQL
```

| Order | Repository | Port | Kaam |
|---|---|---|---|
| 1 | infrapulse-database | 5432 | Data store |
| 2 | infrapulse-query-service | 8000 | API |
| 3 | infrapulse-query-service (agent) | No listening port | Metrics send |
| 4 | infrapulse-dashboard | 5173 | Browser UI |

**Important:** Ye guide Ubuntu 24.04 / Ubuntu WSL ke Bash terminal ko main environment maanti hai. Windows native instructions bhi niche hain. WSL use kar rahe hain to database, Python aur Node sab WSL ke andar install karein; Windows aur WSL ke commands mix na karein. Internet initial software installation ke liye chahiye. `localhost` ka matlab apna computer hai. Port ek service ka numbered connection point hai. Command blocks mein sirf commands copy karein, output ya prompt nahi. Ek command successful hone ke baad agli command chalayein.

### Folder setup

Teeno ZIP files ek hi `InfraPulse` folder mein extract karein. Ubuntu/WSL mein is guide ka assumed path `~/InfraPulse` hai. `~` aapka home folder hai. Agar ZIP Downloads mein hain, unhe file manager se home ke InfraPulse folder mein extract kar sakte hain. WSL mein `explorer.exe .` se current Linux folder Windows Explorer mein khulta hai.

```bash
mkdir -p ~/InfraPulse
cd ~/InfraPulse
pwd
ls -a
```

`mkdir -p` folder banata hai (already ho to error nahi), `cd` folder badalta hai, `pwd` current path aur `ls -a` hidden files samet contents dikhata hai. Extract ke baad structure aisa ho:

```text
InfraPulse/
  infrapulse-database/
  infrapulse-query-service/
  infrapulse-dashboard/
```

Windows native mein `C:\Users\YOUR_NAME\InfraPulse` ke badle PowerShell mein `$HOME\InfraPulse` use karein. ZIP ko Extract All se isi folder mein extract karein. Double nested folders na banayein.

## 1. Database prerequisite check (Terminal 2)

```bash
pg_isready -h localhost -p 5432
psql -h localhost -U infrapulse -d infrapulse -c "SELECT count(*) FROM servers;"
```

Expected: accepting connections aur fresh demo setup mein 3 servers. Agar nahi, database README se start karein. Backend database schema create nahi karta.

## 2. Python install aur check

Ubuntu/WSL:

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
python3 --version
```

Python 3.10+ required; Python 3.12 recommended for this project. `python3-venv` isolated environment banane mein help karta hai. `curl` API test karne ka terminal tool hai.

Windows: https://www.python.org/downloads/ se Python 3.12 install karein, Add Python to PATH select karein. PowerShell mein `py --version` aur `py -3.12 --version` check karein.

## 3. Virtual environment aur dependencies

```bash
cd ~/InfraPulse/infrapulse-query-service
ls -a
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

`-m venv` Python ka virtual environment module chalata hai, `.venv` folder mein isolated Python packages rakhta hai. `source` activate karta hai; prompt mein `(.venv)` dikhega. `pip install -r` file mein listed dependencies install karta hai. `pip check` dependency conflicts check karta hai. Expected `No broken requirements found.` Virtual environment har naye terminal mein activate karna hai.

Windows PowerShell alternative (activation ki zaroorat nahi):

```powershell
cd "$HOME\InfraPulse\infrapulse-query-service"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

Aage Windows mein har Python command ki shuruaat `python` ke badle `.\.venv\Scripts\python.exe` se karein. Isse execution policy change karne ki zaroorat nahi.

## 4. Environment file create karein

```bash
cp .env.example .env
nano .env
```

`cp` copy banata hai; `nano` text editor hai. Windows par `Copy-Item .env.example .env` aur `notepad .env` use karein. Existing `.env` ho to overwrite na karein. File mein ye values hain:

```dotenv
POSTGRES_HOST=localhost
POSTGRES_PORT=5432
POSTGRES_DB=infrapulse
POSTGRES_USER=infrapulse
POSTGRES_PASSWORD=local-dev-password-change-me
INGEST_TOKEN=local-demo-token-change-me
ALERT_THRESHOLD=85
STALE_SECONDS=120
```

| Setting | Meaning |
|---|---|
| POSTGRES_HOST / PORT | Database ka address / port |
| POSTGRES_DB / USER | Database name / application login |
| POSTGRES_PASSWORD | Step 2 database README wala exact password |
| INGEST_TOKEN | Agent ko metrics bhejne ki permission dene wala shared secret |
| ALERT_THRESHOLD | 85% ya usse zyada utilization par alert |
| STALE_SECONDS | Last metric 120 seconds se purani ho to offline |

Nano save: Ctrl+O, Enter, Ctrl+X. `.env` local private file hai, GitHub par upload mat karein. Example password/token sirf local lab ke liye hain. Token change karein to Swagger aur agent mein bhi same value use karein. Dashboard resource bars ka color threshold fixed 85 hai; backend threshold badalne par bar color se status mismatch ho sakta hai.

## 5. API start karein (Terminal 2 running rakhein)

```bash
python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

`app.main` Python module `app/main.py` hai; colon ke baad `app` FastAPI object hai. `--env-file` configuration load karta hai, host loopback par bind hota hai, port API ka number hai. Expected `Uvicorn running on http://127.0.0.1:8000`. Ctrl+C se stop; abhi stop nahi karna.

Browser mein http://localhost:8000/docs open karein. Swagger interactive API page hai. http://localhost:8000/health/live par `{"status":"ok"}` aur http://localhost:8000/health/ready par `{"status":"ready"}` expected hai. Live sirf process batata hai; ready database table access verify karta hai.

## 6. Demo agent start karein (NEW Terminal 3)

```bash
cd ~/InfraPulse/infrapulse-query-service
source .venv/bin/activate
python -c "from dotenv import load_dotenv; load_dotenv(); from agent.demo import main; main()"
```

Windows mein folder PowerShell se open karein aur upar bataya `.venv` Python executable use karein. `-c` inline Python chalata hai; `load_dotenv()` `.env` load karta hai; `main()` demo loop shuru karta hai. Har 15 seconds ke aas-paas 3 servers sample bhejte hain. Expected logs:

```text
demo-web-01 201
demo-api-01 201
demo-db-01 201
```

201 ka matlab API ne sample accept kiya. Ye simulated data hai. Region names sirf labels hain. Terminal khula rakhein. Ab http://localhost:8000/api/v1/summary aur http://localhost:8000/api/v1/servers browser mein kholein. Demo-db-01 ki disk 91% hone ke karan warning expected hai.

## 7. API ko manually test karein (Swagger ya NEW terminal)

http://localhost:8000/docs par `POST /api/v1/metrics` expand karein, Try it out click karein. `x-ingest-token` mein `.env` token enter karein. Request body:

```json
{"hostname":"test-server-01","region":"local","cpu":95,"memory":40,"disk":30}
```

Execute click karein. Expected HTTP 201, `accepted: true` aur numeric server_id. `GET /api/v1/alerts` se CPU alert verify karein. Same body mein CPU 20 karke dobara POST karein. Active alerts se test-server ka CPU alert hatna chahiye; `GET /api/v1/alerts?active=false` mein resolved_at populated hoga. Wrong token se 401, CPU 101 se valid token ke saath 422 expected hai. Test server bhi inventory mein register ho jayega. Swagger mein GET endpoints ke Try it out se test karein.

Ubuntu curl alternative:

```bash
curl -i http://localhost:8000/health/ready
curl -s http://localhost:8000/api/v1/summary
```

`-i` HTTP status/headers dikhata hai; `-s` progress hide karta hai. Windows PowerShell mein `curl.exe` use karein.

| Method | Path | Meaning |
|---|---|---|
| GET | /health/live | API running |
| GET | /health/ready | Database reachable |
| GET | /api/v1/summary | Total, online, warning, offline, average CPU |
| GET | /api/v1/servers | Latest server metrics |
| GET | /api/v1/servers/{server_id}/metrics | History; ID ko actual numeric ID se replace karein |
| GET | /api/v1/alerts | Active alerts (active=false includes resolved) |
| POST | /api/v1/metrics | Metrics insert; token required |

## 8. Real computer monitoring (optional, demo ke badle)

Demo Terminal 3 mein Ctrl+C dabayein; API Terminal 2 running rehne dein. Terminal 3 mein:

```bash
python -m pip install -r agent/requirements.txt
python -c "from dotenv import load_dotenv; load_dotenv(); from agent.collector import main; main()"
```

Windows par command se pehle `$env:MONITOR_PATH = 'C:/'` set karein, phir `.venv` Python executable use karein. `psutil` current host CPU, RAM aur disk padhta hai. Expected `Metrics sent: 201`. WSL collector WSL environment ki measurements deta hai, native Windows ki nahi. Demo rows database mein rehti hain aur 120 seconds baad offline ho sakti hain. Remote monitoring is local guide ka part nahi hai.

## 9. Har source file ka kaam

| File | Meaning |
|---|---|
| app/main.py | FastAPI routes, queries, ingestion aur alert logic |
| app/config.py | Environment settings load karta hai |
| app/database.py | psycopg connection/transaction manage karta hai |
| app/schemas.py | Incoming JSON fields aur 0–100 range validate karta hai |
| app/logic.py | Online/warning/offline decide karta hai |
| app/__init__.py | Python package marker |
| agent/demo.py | Fake server metrics har 15 seconds bhejta hai |
| agent/collector.py | Real machine metrics read/send karta hai |
| agent/requirements.txt | Real collector ki dependency |
| requirements.txt | API ki dependencies |
| .env.example | Configuration template |
| .gitignore, LICENSE, README.md | Git exclusions, license, guide |

## 10. Troubleshooting

| Symptom | Solution |
|---|---|
| ModuleNotFoundError | Correct venv Python aur pip install check |
| Could not import app | Repo root mein cd karein |
| 503 ready | PostgreSQL running, tables aur .env credentials check |
| 401 ingestion | Agent/Swagger token API token se match karein; change ke baad API restart |
| 422 | JSON fields/ranges check |
| Address already in use | Existing API terminal stop karein ya port 8000 free karein |
| Demo retry | API ready URL aur API logs check |
| Offline | Agent running aur recent samples check |

## 11. Next repository

Terminal 2 (API) aur Terminal 3 (agent) khule rakhein. Ab dashboard README open karein. Backend ko stop karne ke liye Ctrl+C, venv se exit ke liye `deactivate` (Bash activated environment only).

## GitHub par upload (application chalane ke liye optional)

Ubuntu par `sudo apt install -y git` se Git install karein. Windows par https://git-scm.com/downloads se Git install karein. `git --version` se verify karein. GitHub.com par New repository banayein, is repo ke exact naam se. README/license initialize na karein. Public karne se pehle secrets check karein.

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
git init -b main
git add .
git status --short
git commit -m "Initial InfraPulse project"
git remote add origin https://github.com/YOUR_USERNAME/infrapulse-query-service.git
git push -u origin main
```

In commands ko **isi repository ke root folder mein** chalayein. `YOUR_USERNAME` apna GitHub username aur `REPO_NAME` is repository ka naam rakhein. `git init` local repo banata hai, `add` files stage karta hai, `status` review karata hai, `commit` snapshot banata hai, `remote` GitHub URL jodta hai, `push` upload karta hai. HTTPS authentication ke liye Git Credential Manager/browser login ya GitHub token use karein, account password nahi. `.env`, database dumps, `.venv`, `node_modules` aur `dist` upload nahi karne hain; `.gitignore` inhe exclude karta hai. `git status` mein secret dikhe to commit se pehle hata dein. Existing remote ho to `git remote -v` check karein; dobara init/push blindly na karein.

## Verification note

Commands source configuration ke against review kiye gaye hain. Live database, dependency installation aur browser end-to-end test is packaging environment mein execute nahi hua. Neeche/uper diye expected results acceptance checks hain, actual test results nahi. Local lab credentials examples hain; public access se pehle authentication, HTTPS aur secure secrets configure karein.
