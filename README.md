# InfraPulse Query Service — Complete Beginner Setup Guide

**Repository 2 of 3 | Complete the database setup first**

Python provides the application logic. FastAPI exposes REST endpoints, Uvicorn runs the API server, and psycopg connects to PostgreSQL. A collector sends resource measurements to the API. The backend does not create the database schema automatically.

## Project overview and execution order

InfraPulse is a three-tier infrastructure monitoring application. The collector sends CPU, memory (RAM), and disk usage measurements to the FastAPI backend. PostgreSQL stores those measurements and the React dashboard displays them.

```text
Collector --> FastAPI --> PostgreSQL
Browser --> React/Vite --> FastAPI --> PostgreSQL
```

| Order | Component | Port | Purpose |
|---|---|---|---|
| 1 | infrapulse-database | 5432 | Persistent data storage |
| 2 | infrapulse-query-service | 8000 | REST API |
| 3 | infrapulse-query-service agent | None | Sends measurements |
| 4 | infrapulse-dashboard | 5173 | Browser interface |

Use Ubuntu 24.04 or Ubuntu under WSL for the Bash commands in this guide. Native Windows alternatives are included where needed. Install all components in the same environment; do not mix native Windows and WSL installations. `localhost` refers to your own machine, and a port is a numbered network connection point. Run commands one at a time, checking the output before proceeding. Do not copy the terminal prompt or expected output.

## Prepare your project folder

```bash
mkdir -p ~/InfraPulse
cd ~/InfraPulse
pwd
ls -a
```

`mkdir -p` creates a directory if needed; `cd` changes directories; `pwd` prints the current location; `ls -a` lists files including hidden files. Extract the three source archives here, or clone your three populated GitHub repositories here. The final layout must be:

```text
InfraPulse/
  infrapulse-database/
  infrapulse-query-service/
  infrapulse-dashboard/
```

Avoid double-nested directories. On native Windows, use `$HOME\InfraPulse` in PowerShell and Extract All in File Explorer. In WSL, `explorer.exe .` opens the current Linux directory in Windows Explorer.

## 1. Verify the database before starting (Terminal 2)

```bash
pg_isready -h localhost -p 5432
psql -h localhost -U infrapulse -d infrapulse -c "SELECT count(*) FROM servers;"
```

The first command checks whether PostgreSQL accepts connections. The second verifies the application login and the servers table. On a freshly seeded database, expect a count of three. Complete the database README if either command fails.

## 2. Install Python

```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip curl
python3 --version
```

Python 3.10 or later is required; Python 3.12 is recommended. The venv package supports isolated dependencies, pip installs Python libraries and curl tests HTTP requests.

Native Windows: install Python 3.12 from https://www.python.org/downloads/ and enable Add Python to PATH. Open PowerShell and check `py --version` and `py -3.12 --version`.

## 3. Create a virtual environment and install dependencies

```bash
cd ~/InfraPulse/infrapulse-query-service
ls -a
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m pip check
```

`-m venv` creates an isolated Python environment in `.venv`; `source` activates it, usually showing `(.venv)` in the prompt. `pip install -r` installs the libraries listed in requirements.txt. `pip check` checks dependency compatibility. Expect `No broken requirements found.` Activate the environment again in every new Bash terminal.

Native Windows PowerShell alternative (no activation required):

```powershell
cd "$HOME\InfraPulse\infrapulse-query-service"
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pip check
```

For subsequent Python commands on native Windows, replace `python` with `.\.venv\Scripts\python.exe` rather than changing PowerShell's execution policy.

## 4. Configure environment variables

```bash
cp .env.example .env
nano .env
```

Do not overwrite an existing configured .env file. `cp` copies the template; `nano` edits it. Save with Ctrl+O, Enter, then Ctrl+X. Windows alternatives: `Copy-Item .env.example .env` and `notepad .env`.

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
| POSTGRES_HOST / POSTGRES_PORT | Database address and port |
| POSTGRES_DB / POSTGRES_USER | Database name and application role |
| POSTGRES_PASSWORD | Exact password created in the database setup |
| INGEST_TOKEN | Shared secret authorizing incoming measurements |
| ALERT_THRESHOLD | Utilization at or above 85% triggers an alert |
| STALE_SECONDS | A sample older than 120 seconds makes a server offline |

Keep .env private. If you change the token, use the same value in the collector and Swagger tests. Restart the backend after changing settings. The dashboard resource bar color uses a fixed threshold of 85, so changing the backend threshold can cause a color/status mismatch.

## 5. Start the API (keep Terminal 2 open)

```bash
python -m uvicorn app.main:app --env-file .env --host 127.0.0.1 --port 8000
```

`app.main` refers to app/main.py; `:app` selects the FastAPI object. `--env-file` loads settings, `--host` restricts access to the local machine, and `--port` selects the listening port. Expect Uvicorn running on http://127.0.0.1:8000. Ctrl+C stops the server; leave it running for now.

| URL | Expected result |
|---|---|
| http://localhost:8000/docs | Interactive Swagger documentation |
| http://localhost:8000/health/live | {"status":"ok"} |
| http://localhost:8000/health/ready | {"status":"ready"} |

Liveness checks the API process; readiness checks access to the database table.

## 6. Start the demo collector (new Terminal 3)

```bash
cd ~/InfraPulse/infrapulse-query-service
source .venv/bin/activate
python -c "from dotenv import load_dotenv; load_dotenv(); from agent.demo import main; main()"
```

`-c` executes inline Python. `load_dotenv()` loads the environment file; `main()` starts the simulation loop. The collector sends measurements for three simulated servers approximately every 15 seconds. Expected logs:

```text
demo-web-01 201
demo-api-01 201
demo-db-01 201
```

HTTP 201 means the measurement was accepted. Leave this terminal running. Open http://localhost:8000/api/v1/summary and http://localhost:8000/api/v1/servers to see JSON results. The demo database server has 91% disk usage and should show a warning with the default threshold.

## 7. Test the API manually

Open http://localhost:8000/docs, expand POST /api/v1/metrics, choose Try it out and enter your INGEST_TOKEN in x-ingest-token. Use this JSON request body:

```json
{"hostname":"test-server-01","region":"local","cpu":95,"memory":40,"disk":30}
```

Click Execute. Expect HTTP 201, accepted: true and a numeric server_id. GET /api/v1/alerts should show a CPU alert for this test server. Submit the same body with CPU changed to 20; the alert should resolve. GET /api/v1/alerts?active=false includes resolved alerts and should show resolved_at. An incorrect token should return 401 for valid input; CPU 101 should return 422 with a valid token. The test server remains in the inventory.

Command-line alternatives:

```bash
curl -i http://localhost:8000/health/ready
curl -s http://localhost:8000/api/v1/summary
```

`-i` includes HTTP headers and status; `-s` hides progress. On Windows PowerShell use curl.exe.

| Method | Path | Purpose |
|---|---|---|
| GET | /health/live | API process health |
| GET | /health/ready | Database readiness |
| GET | /api/v1/summary | Server counts and average CPU |
| GET | /api/v1/servers | Latest measurement and status for each server |
| GET | /api/v1/servers/{server_id}/metrics | Historical measurements; replace server_id with a numeric ID |
| GET | /api/v1/alerts | Active alerts; active=false includes resolved alerts |
| POST | /api/v1/metrics | Store a measurement; ingestion token required |

History supports hours=1–168 and limit=1–2000. Alerts support limit=1–500. Offline servers are excluded from the average CPU. Missing or stale samples are offline; recent measurements above or equal to the threshold are warnings; otherwise the server is online.

## 8. Optional real machine monitoring

Stop the demo collector with Ctrl+C in Terminal 3, leaving the API running. Then run:

```bash
python -m pip install -r agent/requirements.txt
python -c "from dotenv import load_dotenv; load_dotenv(); from agent.collector import main; main()"
```

The psutil library reads actual CPU, RAM and disk usage of the current environment. Expect `Metrics sent: 201`. On native Windows set `$env:MONITOR_PATH = 'C:/'` and use the virtual environment executable described earlier. WSL measurements describe WSL, not the native Windows host. Demo records remain in the database and can become offline when the collector stops.

## 9. Source files and responsibilities

| File | Purpose |
|---|---|
| app/main.py | FastAPI routes, database queries, ingestion and alert recovery |
| app/config.py | Environment settings |
| app/database.py | PostgreSQL connections and transactions |
| app/schemas.py | Input JSON validation and utilization ranges |
| app/logic.py | Determines online, warning and offline status |
| app/__init__.py | Python package marker |
| agent/demo.py | Simulates three servers |
| agent/collector.py | Reads and submits actual machine measurements |
| agent/requirements.txt | Real collector dependencies |
| requirements.txt | API dependencies |
| .env.example | Configuration template |
| .gitignore, LICENSE, README.md | Git exclusions, license and documentation |

The ingestion endpoint registers or updates a server, inserts a metric sample, opens or updates alerts at the threshold, and resolves alerts when utilization drops. Parameterized SQL is used for incoming values. A database operation error returns HTTP 503.

## 10. Troubleshooting

| Error | Action |
|---|---|
| ModuleNotFoundError | Check virtual environment and pip installation |
| Could not import app | Run Uvicorn from the repository root |
| 503 readiness error | Check PostgreSQL, schema and .env credentials |
| 401 ingestion | Match the token in API and collector; restart API after changes |
| 422 validation | Check JSON field names and utilization ranges |
| Address already in use | Stop the conflicting process or free port 8000 |
| Collector retries | Check API readiness and logs |
| Offline servers | Check collector and recent measurement timestamps |

## 11. Next step

Keep Terminal 2 (API) and Terminal 3 (collector) open. Follow `infrapulse-dashboard/README.md` to start the browser interface. To stop the backend later, press Ctrl+C. Use `deactivate` to leave an activated Bash virtual environment.

## Publish this repository to GitHub using Git clone (optional)

These instructions are for publishing the supplied source code to your own GitHub account, not for running the application. Publish each repository separately.

1. Install Git (`sudo apt install -y git` on Ubuntu, or https://git-scm.com/downloads on Windows). Verify with `git --version`.
2. Open https://github.com/new and create an empty repository named `infrapulse-query-service`. Do not initialize it with a README, license or .gitignore. Choose public or private visibility as appropriate.
3. Configure your Git identity once, using your own name and email.

```bash
git config --global user.name "Your Name"
git config --global user.email "your-email@example.com"
```

4. Clone into a separate publishing directory so that it does not conflict with your extracted source folder. Replace `YOUR_USERNAME` with your GitHub username.

```bash
mkdir -p ~/InfraPulse-publish
cd ~/InfraPulse-publish
git clone https://github.com/YOUR_USERNAME/infrapulse-query-service.git
cd infrapulse-query-service
```

An empty-repository warning is normal for a newly created repository. Copy the contents of the supplied source directory into this cloned directory, including hidden files such as `.gitignore` and `.env.example` where present. Do not replace the cloned `.git` directory. Do not copy actual secrets, database dumps, virtual environments, dependencies or build output.

5. Check the files and the destination repository before staging and committing.

```bash
git remote -v
git status
git add .
git status --short
```

`git clone` automatically configures the remote named `origin`; no `git init` or `git remote add` is necessary. `git add` stages files; `git status` lets you review them. Remove any staged secrets before committing.

```bash
git commit -m "Initial InfraPulse project"
git branch -M main
git push -u origin main
```

`git commit` records a snapshot, `git branch -M main` names the branch, and `git push` uploads the commit and sets the upstream branch. Authenticate using the browser/Git Credential Manager or a GitHub token, not your account password. Refresh the GitHub repository page and confirm the source files and README are present.

For an existing cloned repository, replace its README.md and run only:

```bash
git status
git add README.md
git commit -m "Improve English setup documentation"
git push
```

Never commit `.env`, real passwords, tokens, private SSH keys, database dumps, `.venv`, `node_modules` or `dist`. Review the staged file list even when `.gitignore` is present.

## Verification and security note

The instructions describe the supplied source configuration and expected acceptance results. They are not a claim that a live database, dependency installation or end-to-end browser deployment has been executed. The sample credentials are for a private local lab. Configure authentication, HTTPS and secure secrets before any public deployment. Read API endpoints do not currently require authentication.
