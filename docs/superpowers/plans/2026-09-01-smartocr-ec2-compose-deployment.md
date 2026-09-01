# SmartOCR EC2 Docker Compose Deployment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Deploy SmartOCR from GitHub `main` to `/home/ubuntu/docker/smartocr` on EC2 and serve it on public TCP 80 with verified persistent Docker volumes.

**Architecture:** Keep the repository's development Compose file as the single service definition, but parameterize the frontend host port with `FRONTEND_PORT` so local development remains on 8080 and EC2 uses 80. EC2 clones the public repository, keeps secrets only in a mode-600 `.env`, and uses a fixed `COMPOSE_PROJECT_NAME=smartocr` so redeployments reuse the same named volumes.

**Tech Stack:** Docker Engine, Docker Compose v2, Git/GitHub, PostgreSQL 16, FastAPI, Vue 3, Nginx, PaddleOCR, pytest

---

## File map

- Create `backend/tests/test_compose_config.py`: regression test proving `FRONTEND_PORT` controls the rendered frontend publication.
- Modify `docker-compose.yml`: parameterize only the frontend host port; service topology and volume destinations stay unchanged.
- Modify `.env.example`: document stable Compose project name and the local default frontend port without adding secrets.
- Modify `README.md`: document the EC2 Compose deployment and the three persistent named volumes.

### Task 1: Add a failing Compose port regression test

**Files:**
- Create: `backend/tests/test_compose_config.py`

- [ ] **Step 1: Create the regression test**

```python
import json
import os
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def test_frontend_port_can_be_overridden_for_deployment() -> None:
    env = os.environ.copy()
    env["FRONTEND_PORT"] = "80"

    result = subprocess.run(
        ["docker", "compose", "config", "--format", "json"],
        cwd=PROJECT_ROOT,
        env=env,
        check=True,
        capture_output=True,
        text=True,
    )
    config = json.loads(result.stdout)
    publications = config["services"]["frontend"]["ports"]

    assert any(
        str(publication["published"]) == "80"
        and str(publication["target"]) == "80"
        and publication["host_ip"] == "0.0.0.0"
        for publication in publications
    )
```

- [ ] **Step 2: Run the focused test and confirm the current hard-coded port fails**

Run from the repository root:

```powershell
python -m pytest backend/tests/test_compose_config.py -v
```

Expected: one failed test because the rendered frontend publication remains `8080:80` even when `FRONTEND_PORT=80`.

### Task 2: Parameterize the frontend port and document deployment settings

**Files:**
- Modify: `docker-compose.yml`
- Modify: `.env.example`
- Modify: `README.md`

- [ ] **Step 1: Change the frontend port publication**

Replace the frontend `ports` entry in `docker-compose.yml` with:

```yaml
    ports:
      - "0.0.0.0:${FRONTEND_PORT:-8080}:80"
```

- [ ] **Step 2: Add non-secret Compose settings to `.env.example`**

Add these lines before the Google OAuth settings:

```dotenv
# 固定 Compose 專案名稱，確保重新部署沿用相同 named volumes
COMPOSE_PROJECT_NAME=smartocr
# 本機預設使用 8080；EC2 部署改為 80
FRONTEND_PORT=8080
```

- [ ] **Step 3: Add the EC2 deployment commands and volume warning to `README.md`**

Append this section before `## 常用指令`:

````markdown
## EC2 Docker Compose 部署

EC2 從 GitHub clone 後，在專案目錄建立不進版控的 `.env`：

```env
COMPOSE_PROJECT_NAME=smartocr
FRONTEND_PORT=80
ALLOW_DEV_LOGIN=true
VITE_ALLOW_DEV_LOGIN=true
```

`JWT_SECRET` 必須在伺服器上另外產生，不可提交到 Git。啟動服務：

```bash
docker compose up -d --build
```

固定 `COMPOSE_PROJECT_NAME=smartocr` 後，資料會保存在 `smartocr_postgres_data`、`smartocr_uploads_data` 與 `smartocr_paddle_models`。更新或停止服務不可加 `-v`，否則會刪除資料 volumes。
````

- [ ] **Step 4: Run the focused regression test**

```powershell
python -m pytest backend/tests/test_compose_config.py -v
```

Expected: `1 passed`.

- [ ] **Step 5: Render both development and deployment Compose configurations**

```powershell
docker compose config --quiet
$env:FRONTEND_PORT = '80'
docker compose config --format json
Remove-Item Env:FRONTEND_PORT
```

Expected: the first command exits 0; the JSON contains frontend target `80`, published `80`, host IP `0.0.0.0`, plus named volumes `postgres_data`, `uploads_data`, and `paddle_models`.

- [ ] **Step 6: Commit the configuration change**

```powershell
git add -- backend/tests/test_compose_config.py docker-compose.yml .env.example README.md
git commit -m "ops: prepare compose deployment on port 80"
```

Expected: one commit containing only the four listed files.

### Task 3: Run complete local verification and publish `main`

**Files:**
- Verify only; no additional files

- [ ] **Step 1: Run all backend tests**

```powershell
python -m pytest backend/tests -v
```

Expected: all tests pass with zero failures.

- [ ] **Step 2: Build the frontend in its existing Docker build stage**

```powershell
docker build --target build -t smartocr-frontend-verify ./frontend
```

Expected: Docker build exits 0 after `npm run build`, including `vue-tsc --noEmit` and Vite build.

- [ ] **Step 3: Verify the repository state and commit sequence**

```powershell
git diff --check
git status --short
git log -3 --oneline
```

Expected: no whitespace errors, no uncommitted files, and the deployment configuration commit follows the approved design commit `becb917`.

- [ ] **Step 4: Push the verified commits**

```powershell
git push origin main
git ls-remote --heads origin main
git rev-parse HEAD
```

Expected: the commit printed for `refs/heads/main` exactly matches local `HEAD`.

### Task 4: Perform non-destructive EC2 preflight and clone

**Files:**
- Create remotely: `/home/ubuntu/docker/smartocr/.env`
- Preserve remotely: `/home/ubuntu/docker/c1-backend`

- [ ] **Step 1: Confirm the SSH host, Docker tools, free disk, and port 80 state**

Run through the active SSH session:

```bash
hostname
whoami
docker version --format '{{.Server.Version}}'
docker compose version
df -h /
[ "$(df --output=avail -BG / | tail -1 | tr -dc '0-9')" -ge 20 ]
sudo ss -ltnp | grep -E '[:.]80[[:space:]]' || true
docker compose ls
```

Expected: host `ip-10-0-1-163`, user `ubuntu`, Docker and Compose versions print successfully, at least 20 GB remains available, port 80 has no listener, and `c1-backend` is not running. If port 80 is occupied or the 20 GB check fails, stop and report the exact blocker without stopping unrelated services or pruning data.

- [ ] **Step 2: Clone only when the deployment path is absent**

```bash
test ! -e /home/ubuntu/docker/smartocr
git clone --branch main --single-branch https://github.com/powershawn/SmartOCR /home/ubuntu/docker/smartocr
git -C /home/ubuntu/docker/smartocr rev-parse HEAD
```

Expected: clone succeeds and the remote commit equals the GitHub/local `main` commit from Task 3. If the path already exists, do not delete it; inspect its Git remote and state before deciding whether a fast-forward pull is safe.

- [ ] **Step 3: Generate the server-only environment file without printing the secret**

```bash
cd /home/ubuntu/docker/smartocr
umask 077
jwt_secret="$(openssl rand -hex 48)"
{
  printf '%s\n' 'COMPOSE_PROJECT_NAME=smartocr'
  printf '%s\n' 'FRONTEND_PORT=80'
  printf 'JWT_SECRET=%s\n' "$jwt_secret"
  printf '%s\n' 'GOOGLE_CLIENT_ID='
  printf '%s\n' 'SUPER_ADMIN_EMAIL=admin@example.com'
  printf '%s\n' 'VITE_SUPER_ADMIN_EMAIL=admin@example.com'
  printf '%s\n' 'ALLOW_DEV_LOGIN=true'
  printf '%s\n' 'VITE_ALLOW_DEV_LOGIN=true'
} > .env
unset jwt_secret
chmod 600 .env
stat -c '%a %U:%G %n' .env
```

Expected: `600 ubuntu:ubuntu .env`. The JWT value must not appear in terminal output or Git.

- [ ] **Step 4: Validate the rendered remote Compose configuration**

```bash
docker compose config --quiet
docker compose config --format json | python3 -c 'import json,sys; c=json.load(sys.stdin); print(c["name"]); print(c["services"]["frontend"]["ports"]); print(sorted(c["volumes"]))'
```

Expected: project name `smartocr`, frontend publication `0.0.0.0:80->80`, and volumes `paddle_models`, `postgres_data`, `uploads_data`.

### Task 5: Build and start SmartOCR on EC2

**Files:**
- Runtime artifacts only; no repository edits

- [ ] **Step 1: Build and start all services**

```bash
cd /home/ubuntu/docker/smartocr
docker compose up -d --build
```

Expected: images build successfully and `db`, `backend`, and `frontend` are created and started. The first PaddleOCR image build may take several minutes.

- [ ] **Step 2: Wait for PostgreSQL health and inspect service state**

```bash
db_id="$(docker compose ps -q db)"
timeout 180 sh -c 'until [ "$(docker inspect -f "{{.State.Health.Status}}" "$1" 2>/dev/null)" = healthy ]; do sleep 3; done' sh "$db_id"
docker compose ps
docker compose logs --no-color --tail=100 backend frontend db
```

Expected: database is healthy; all three services are running; logs contain no startup traceback, crash loop, or database connection failure.

- [ ] **Step 3: Verify EC2-local HTTP paths**

```bash
curl --fail --show-error --silent http://127.0.0.1/health
curl --fail --show-error --silent http://127.0.0.1/ | grep -F '<div id="app"></div>'
```

Expected: `/health` returns the backend health payload and `/` contains the Vue application mount element.

### Task 6: Verify mounts and persistence

**Files:**
- Runtime verification only; the temporary upload marker is removed after testing

- [ ] **Step 1: Inspect every container mount**

```bash
cd /home/ubuntu/docker/smartocr
for service in db backend frontend; do
  container_id="$(docker compose ps -q "$service")"
  printf '%s\n' "SERVICE=$service"
  docker inspect "$container_id" --format '{{range .Mounts}}{{println .Type .Name .Source "->" .Destination "rw=" .RW}}{{end}}'
done
```

Expected:

- db: `smartocr_postgres_data` to `/var/lib/postgresql/data`, `rw=true`
- backend: `smartocr_uploads_data` to `/app/uploads`, `rw=true`
- backend: `smartocr_paddle_models` to `/root/.paddlex`, `rw=true`
- backend: `/home/ubuntu/docker/smartocr/models` to `/app/models`, `rw=false`

- [ ] **Step 2: Verify database and Paddle cache access**

```bash
docker compose exec -T db pg_isready -U smartocr -d smartocr
docker compose exec -T backend sh -lc 'touch /root/.paddlex/.smartocr-write-test && rm /root/.paddlex/.smartocr-write-test'
```

Expected: PostgreSQL reports `accepting connections`; the Paddle cache write/remove command exits 0.

- [ ] **Step 3: Create an upload marker and record volume identities**

```bash
marker=".volume-check-$(date +%s)"
docker compose exec -T backend sh -lc "printf volume-ok > /app/uploads/$marker"
docker volume inspect smartocr_postgres_data smartocr_uploads_data smartocr_paddle_models --format '{{.Name}} {{.Mountpoint}}' | sort > /tmp/smartocr-volumes-before.txt
printf '%s\n' "$marker"
```

Expected: a unique marker filename prints and all three volumes are recorded.

- [ ] **Step 4: Restart services and prove the named volumes are reused**

```bash
docker compose restart db backend
timeout 180 sh -c 'until docker compose exec -T db pg_isready -U smartocr -d smartocr >/dev/null 2>&1; do sleep 3; done'
docker compose exec -T -e CHECK_MARKER="$marker" backend sh -lc 'test "$(cat "/app/uploads/$CHECK_MARKER")" = volume-ok'
docker compose up -d
docker volume inspect smartocr_postgres_data smartocr_uploads_data smartocr_paddle_models --format '{{.Name}} {{.Mountpoint}}' | sort > /tmp/smartocr-volumes-after.txt
diff -u /tmp/smartocr-volumes-before.txt /tmp/smartocr-volumes-after.txt
```

Expected: PostgreSQL becomes ready, the upload marker survives the backend restart, and `diff` produces no output.

- [ ] **Step 5: Remove only the temporary marker and verification files**

```bash
docker compose exec -T backend rm -f "/app/uploads/$marker"
rm -f /tmp/smartocr-volumes-before.txt /tmp/smartocr-volumes-after.txt
unset marker
```

Expected: cleanup exits 0; application data and named volumes remain intact.

### Task 7: Verify public access and capture final state

**Files:**
- Verify only; no additional files

- [ ] **Step 1: Verify public HTTP from the local workstation**

```powershell
$health = Invoke-WebRequest -UseBasicParsing -Uri 'http://3.113.155.60/health' -TimeoutSec 30
$root = Invoke-WebRequest -UseBasicParsing -Uri 'http://3.113.155.60/' -TimeoutSec 30
$health.StatusCode
$health.Content
$root.StatusCode
$root.Content -match '<div id="app"></div>'
```

Expected: both status codes are `200`, health content is the backend health payload, and the final expression is `True`. If EC2-local HTTP passed but this request times out, report the AWS Security Group/network ACL requirement for inbound TCP 80.

- [ ] **Step 2: Capture final service, volume, and disk evidence**

Run on EC2:

```bash
cd /home/ubuntu/docker/smartocr
docker compose ps
docker compose ls
docker volume inspect smartocr_postgres_data smartocr_uploads_data smartocr_paddle_models --format '{{.Name}} {{.Mountpoint}}'
df -h /
git rev-parse HEAD
```

Expected: only SmartOCR is the running Compose project, all services are up, three stable volume names print, disk has safe free space, and the deployed commit matches GitHub `main`.
