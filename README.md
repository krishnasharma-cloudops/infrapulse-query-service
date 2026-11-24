# InfraPulse — Telemetry Query Service

## Simple Setup on Azure VM (Without Docker)

A step-by-step guide to deploy the InfraPulse FastAPI backend on an Ubuntu Azure Virtual Machine using Python, Uvicorn and Azure Database for PostgreSQL Flexible Server.

The query service reads server inventory, CPU, memory and disk measurements from PostgreSQL and exposes REST APIs for the InfraPulse dashboard. It also accepts authenticated metrics from the collector.

---

## Before You Begin

- An Ubuntu 24.04 Azure VM for the backend, with SSH access and outbound internet connectivity.
- An Azure Database for PostgreSQL Flexible Server with the `infrapulse` database, application user and schema already created using `infrapulse-database`.
- A frontend VM on the same virtual network (or a connected network).
- Your GitHub repository URL for `infrapulse-query-service`.

This application uses PostgreSQL, not Microsoft Azure SQL Database (SQL Server). Deploy the database first, then this service, then the dashboard.

```text
Browser -> Frontend VM (Nginx:80) -> Backend VM (FastAPI:8000)
                                          |
                                          v
                               Azure PostgreSQL (5432/TLS)
```

## 1. Open Port 8000 in Azure NSG

In the [Azure Portal](https://portal.azure.com/):

1. Open your backend Virtual Machine > **Networking** > **Network settings**.
2. Open its Network Security Group (NSG) and add an inbound rule:
   - **Source:** IP Addresses
   - **Source IP addresses:** Your frontend VM's private IP (for example, `10.0.1.4/32`).
   - **Source port ranges:** `*`
   - **Destination:** Any (for a dedicated backend NIC NSG)
   - **Destination port ranges:** `8000`
   - **Protocol:** TCP
   - **Action:** Allow
   - **Priority:** `1010` (or an unused priority before any matching deny rule)
   - **Name:** `Allow-Frontend-8000`
3. Allow TCP port `22` from your authorized SSH jump host, or your laptop's public IP if the backend has a public IP.
4. Ensure a lower-precedence deny rule blocks other inbound traffic to the backend, including port 8000 from other VNet hosts. Azure's default VNet allow rule otherwise permits internal access.

Do not expose port 8000 to the entire internet. The read APIs do not require authentication. The frontend will access the API through its private IP and Nginx reverse proxy.

The backend must also be able to reach PostgreSQL on TCP port `5432`. For private database networking, confirm VNet connectivity and private DNS resolution. For public database networking, allow only the backend's actual outbound public IP in the PostgreSQL firewall.

## 2. Connect to the Azure VM

From your laptop terminal, if the backend has a public IP:

```bash
ssh azureuser@YOUR_BACKEND_PUBLIC_IP
```

For the recommended private backend VM, use the frontend VM as an SSH jump host:

```bash
ssh -J azureuser@YOUR_FRONTEND_PUBLIC_IP azureuser@YOUR_BACKEND_PRIVATE_IP
```

Replace the placeholders with your actual IP addresses. Both VMs must have your authorized SSH public key. Keep the private key on your laptop.

All remaining commands, unless otherwise stated, run inside the backend VM's Ubuntu terminal.

## 3. Install Python, Pip and Git

```bash
sudo apt update
sudo apt install -y python3 python3-pip python3-venv git curl postgresql-client ca-certificates openssl
```

- `python3`: runs the application.
- `python3-pip`: installs Python packages.
- `python3-venv`: creates an isolated Python environment.
- `git`: downloads source code.
- `curl`: tests HTTP endpoints.
- `postgresql-client`: tests the remote database without installing a local database server.
- `ca-certificates`: provides trusted TLS certificates.
- `openssl`: generates a random ingestion token.

Verify installation:

```bash
python3 --version
git --version
psql --version
```

## 4. Clone the Repository

```bash
cd ~
git clone https://github.com/YOUR_USERNAME/infrapulse-query-service.git
cd infrapulse-query-service
ls -la
```

Replace `YOUR_USERNAME` with your GitHub username. You should see `app/`, `agent/`, `requirements.txt`, `.env.example` and `README.md`.

If you already cloned the repository, enter its existing folder instead of cloning it again.

## 5. Configure the PostgreSQL Connection

### 5.1 Test the Azure database connection

Copy the server hostname from the PostgreSQL resource's Overview page in Azure Portal.

```bash
export DB_HOST=YOUR_SERVER.postgres.database.azure.com
export PGSSLMODE=verify-full
export PGSSLROOTCERT=/etc/ssl/certs/ca-certificates.crt
psql -h "$DB_HOST" -p 5432 -U infrapulse -d infrapulse
```

Enter the application database password when prompted. Use the actual server hostname, database and username if different.

Inside the PostgreSQL prompt:

```sql
\dt
SELECT COUNT(*) FROM servers;
\q
```

The schema must already contain `servers`, `metrics` and `alerts`. If tables are missing, deploy the database repository first.

### 5.2 Create the environment file

The existing application reads database settings from `app/config.py` and connects through `app/database.py`. It uses separate environment variables, not a single `DATABASE_URL`. There is no need to edit Python source code or URL-encode the password.

```bash
cp .env.example .env
chmod 600 .env
openssl rand -hex 32
nano .env
```

Copy the generated token and replace the example values below in the file:

```dotenv
POSTGRES_HOST=YOUR_SERVER.postgres.database.azure.com
POSTGRES_PORT=5432
POSTGRES_DB=infrapulse
POSTGRES_USER=infrapulse
POSTGRES_PASSWORD="YOUR_DATABASE_PASSWORD"
PGSSLMODE=verify-full
PGSSLROOTCERT=/etc/ssl/certs/ca-certificates.crt
INGEST_TOKEN=YOUR_GENERATED_RANDOM_TOKEN
ALERT_THRESHOLD=85
STALE_SECONDS=120
API_URL=http://localhost:8000
```

| Variable | Purpose |
|---|---|
| `POSTGRES_HOST` | Azure PostgreSQL server hostname |
| `POSTGRES_PORT` | PostgreSQL port, normally 5432 |
| `POSTGRES_DB` | Application database name |
| `POSTGRES_USER` | Application database login |
| `POSTGRES_PASSWORD` | Application database password |
| `PGSSLMODE` | Require TLS and verify certificate and hostname |
| `PGSSLROOTCERT` | Trusted certificate bundle used by libpq/psycopg |
| `INGEST_TOKEN` | Shared secret required by the metrics ingestion API |
| `ALERT_THRESHOLD` | Resource warning threshold in percent |
| `STALE_SECONDS` | Time after which a missing heartbeat is treated as offline |
| `API_URL` | Local API URL used by the collector |

Save and exit Nano with `Ctrl+O`, `Enter`, `Ctrl+X`.

Use valid dotenv quoting for passwords containing quotes, backslashes or interpolation sequences. Never commit `.env` or real passwords to GitHub. Keep `.env.example` as a placeholder template only.

## 6. Install Dependencies

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
```

The virtual environment keeps the project's libraries separate from Ubuntu's system Python. It avoids the externally-managed-environment error on Ubuntu 24.04 without using `--break-system-packages`.

Verify the installed dependencies:

```bash
python -m pip check
python -m uvicorn --version
```

The requirements include FastAPI, Uvicorn, psycopg and python-dotenv.

## 7. Run the Application with Uvicorn

### Option A: Run in Foreground (Testing)

From the repository root, with the virtual environment active:

```bash
python -m uvicorn app.main:app --env-file .env --host 0.0.0.0 --port 8000
```

- `app.main:app`: loads the FastAPI application from `app/main.py`.
- `--env-file .env`: loads the database and application settings before importing the application.
- `--host 0.0.0.0`: accepts connections on the VM's network interfaces.
- `--port 8000`: listens on TCP port 8000.

Expected output includes:

```text
INFO: Application startup complete.
INFO: Uvicorn running on http://0.0.0.0:8000
```

Keep the terminal open. Press `Ctrl+C` to stop the application before switching to another run method.

### Option B: Run in Background (Simple Lab Setup)

```bash
nohup .venv/bin/python -m uvicorn app.main:app --env-file .env --host 0.0.0.0 --port 8000 > app.log 2>&1 &
echo $! > app.pid
```

`nohup` allows the process to continue after a normal SSH disconnect. Output is written to `app.log`; the process ID is saved in `app.pid`. This does not automatically restart the application after a VM reboot.

Check logs:

```bash
tail -f app.log
```

Press `Ctrl+C` to exit the log viewer without stopping the background server.

Stop the application from the same repository folder:

```bash
ps -fp "$(cat app.pid)"
```

Only if the displayed process is your InfraPulse Uvicorn process, run:

```bash
kill "$(cat app.pid)"
rm app.pid
```

Do not start both options at the same time because both use port 8000.

## 8. Test the API

Open a second SSH terminal to the backend VM and run:

```bash
curl -f http://localhost:8000/health/live
curl -f http://localhost:8000/health/ready
curl -f http://localhost:8000/api/v1/servers
curl -f http://localhost:8000/api/v1/summary
curl -f http://localhost:8000/api/v1/alerts
```

Expected liveness: `{"status":"ok"}`. Expected readiness: `{"status":"ready"}`. The remaining endpoints return JSON data. Readiness checks the database and the presence of the server table.

To open Swagger in your laptop browser without exposing port 8000 publicly, create an SSH tunnel in a new laptop terminal:

```bash
ssh -N -L 8000:127.0.0.1:8000 -J azureuser@YOUR_FRONTEND_PUBLIC_IP azureuser@YOUR_BACKEND_PRIVATE_IP
```

If the backend has a public IP and authorized SSH access, omit the `-J azureuser@YOUR_FRONTEND_PUBLIC_IP` portion and use its public IP as the destination. Keep the tunnel terminal open.

| Endpoint | URL (through SSH tunnel) |
|---|---|
| Swagger API documentation | http://localhost:8000/docs |
| Liveness | http://localhost:8000/health/live |
| Database readiness | http://localhost:8000/health/ready |
| Server inventory | http://localhost:8000/api/v1/servers |
| Dashboard summary | http://localhost:8000/api/v1/summary |
| Active alerts | http://localhost:8000/api/v1/alerts |
| Historical metrics | `http://localhost:8000/api/v1/servers/1/metrics?hours=6` (replace 1 with an existing server ID) |

## 9. Start the Demo Metrics Collector

The dashboard needs recent metrics to show changing resource usage. In a separate backend SSH terminal:

```bash
cd ~/infrapulse-query-service
source .venv/bin/activate
python -c "from dotenv import load_dotenv; load_dotenv(); from agent.demo import main; main()"
```

Expected output:

```text
demo-web-01 201
demo-api-01 201
demo-db-01 201
```

HTTP 201 means the API accepted a measurement. The demo collector sends synthetic CPU, memory and disk data approximately every 15 seconds. Keep it running while testing the dashboard. These are simulated servers, not actual Azure host measurements.

To run the demo in the background instead, stop the foreground collector first and run:

```bash
nohup .venv/bin/python -c "from dotenv import load_dotenv; load_dotenv(); from agent.demo import main; main()" > agent.log 2>&1 &
echo $! > agent.pid
tail -f agent.log
```

The same ingestion token must be used by the API and collector. To stop the background collector, verify `ps -fp "$(cat agent.pid)"` identifies the demo process, then use `kill "$(cat agent.pid)"` and `rm agent.pid`.

## 10. Verify Connectivity from the Frontend VM

Connect to your frontend VM from your laptop:

```bash
ssh azureuser@YOUR_FRONTEND_PUBLIC_IP
```

From the frontend VM:

```bash
curl -f http://YOUR_BACKEND_PRIVATE_IP:8000/health/ready
curl -f http://YOUR_BACKEND_PRIVATE_IP:8000/api/v1/servers
```

If these succeed, use the backend private IP in the frontend Nginx reverse proxy according to the `infrapulse-dashboard` README. Do not use the backend's localhost address on the frontend VM.

## 11. Troubleshooting

| Problem | What to check |
|---|---|
| SSH timeout | VM running state, NSG port 22 and jump host connectivity |
| Git clone fails | Repository URL, access permissions and outbound connectivity |
| Externally managed Python environment | Activate `.venv` before installing packages |
| Database connection timeout | PostgreSQL hostname, DNS, port 5432, networking and firewall |
| Certificate verification failure | Correct Azure hostname and trusted CA bundle |
| Password authentication failed | Application database username and password in `.env` |
| Readiness returns 503 | Database connectivity and schema initialization |
| Address already in use | Another process is listening on port 8000; check `sudo ss -ltnp` |
| Metrics return 401 | Collector and backend ingestion tokens must match |
| Frontend returns 502 | Backend process, NSG rules and Nginx upstream address |
| Servers appear offline | Check collector logs; old metrics become stale after 120 seconds by default |

## 12. Deploy Future Code Updates

Stop the running backend and collector using the appropriate foreground or background instructions above. Then, inside the existing cloned backend repository:

```bash
cd ~/infrapulse-query-service
git status
git pull --ff-only origin main
source .venv/bin/activate
python -m pip install -r requirements.txt
```

Restart the backend and collector using Sections 7 and 9, then repeat the health checks. Review any database schema changes before deploying an update. Do not overwrite the existing `.env` file.

## Final Deployment Checklist

- [ ] Azure PostgreSQL is reachable and the application schema exists.
- [ ] Backend VM can install packages and clone the repository.
- [ ] `.env` contains the correct database details and a strong ingestion token.
- [ ] Python dependencies are installed in `.venv`.
- [ ] Uvicorn is running on port 8000.
- [ ] Liveness and readiness endpoints respond successfully.
- [ ] Swagger and server inventory APIs work through the SSH tunnel.
- [ ] Demo collector reports HTTP 201 responses.
- [ ] Frontend VM can reach the backend's private IP.
- [ ] Secrets are not committed to GitHub.

## Verification and Security Note

Commands and endpoint paths were reviewed against the existing InfraPulse backend source files. Live Azure deployment was not executed for this documentation; expected outputs are acceptance checks, not recorded test results. This is a private learning deployment. Before public production use, add read API authentication, HTTPS, suitable database access controls and a persistent Linux service manager such as systemd. No Docker, Kubernetes or additional orchestration tools are required for this guide.
