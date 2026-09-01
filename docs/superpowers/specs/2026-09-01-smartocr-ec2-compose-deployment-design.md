# SmartOCR EC2 Docker Compose 部署設計

## 目標

將 GitHub `powershawn/SmartOCR` 的 `main` 分支部署到 AWS EC2 `3.113.155.60`，使用 Docker Compose 在背景運行，並讓使用者可透過 `http://3.113.155.60`（TCP 80）開啟前端。部署不得取代或啟動既有的 `/home/ubuntu/docker/c1-backend` 專案。

## 部署來源與目錄

- GitHub repository：`https://github.com/powershawn/SmartOCR`
- 分支：`main`
- EC2 部署目錄：`/home/ubuntu/docker/smartocr`
- Compose project name：`smartocr`
- 既有 `/home/ubuntu/docker/c1-backend` 保留並維持關閉。

EC2 直接從公開 GitHub repository clone。第一次部署建立目錄；後續部署在同一目錄 fast-forward pull 指定分支，避免以複製檔案方式造成來源不一致。

## Compose 與網路設計

基礎 `docker-compose.yml` 的前端 port 改為由 `FRONTEND_PORT` 控制，預設值仍為 `8080`，確保本機開發流程不變。EC2 的 `.env` 設定 `FRONTEND_PORT=80`。

前端 Nginx 同時提供靜態頁面，並將 `/api` 與 `/health` 反向代理到 Compose 網路內的 backend。瀏覽器不直接存取 backend port。PostgreSQL 只綁定 EC2 loopback `127.0.0.1:5432`，backend `8000` 也只綁定 loopback，不對公網開放。

部署前確認 TCP 80 沒有被其他行程或容器占用。AWS Security Group 是否允許 TCP 80，則以外部 HTTP 驗證結果判定；若 EC2 本機回應正常但外部無法連線，回報 Security Group 或網路 ACL 為外部阻擋點，不擅自修改 AWS 帳戶設定。

## 環境與登入設定

遠端 `.env` 不加入 Git，包含：

- `COMPOSE_PROJECT_NAME=smartocr`
- `FRONTEND_PORT=80`
- 隨機產生的長 `JWT_SECRET`
- `ALLOW_DEV_LOGIN=true`
- `VITE_ALLOW_DEV_LOGIN=true`
- `SUPER_ADMIN_EMAIL=admin@example.com`
- `VITE_SUPER_ADMIN_EMAIL=admin@example.com`
- Google Client ID 暫時留空

這是驗收用的暫時登入模式。之後切換正式 Google OAuth 時，必須設定 Client ID、最高管理員信箱，並將兩個 dev-login 選項改為 `false` 後重建 frontend。

## Volume 持久化設計

固定 Compose project name 為 `smartocr`，避免因執行目錄或專案名稱不同而建立另一組 named volumes。

| 資料 | Docker volume / 來源 | 容器目的地 | 模式 |
|---|---|---|---|
| PostgreSQL | `smartocr_postgres_data` | `/var/lib/postgresql/data` | read-write |
| 上傳檔案 | `smartocr_uploads_data` | `/app/uploads` | read-write |
| PaddleOCR 快取 | `smartocr_paddle_models` | `/root/.paddlex` | read-write |
| 自訂模型 | `/home/ubuntu/docker/smartocr/models` | `/app/models` | read-only |

部署與重新啟動只使用 `docker compose up -d --build`、`restart` 或不帶 `-v` 的 `down`。不得執行 `docker compose down -v`，也不得 prune 正在驗收的 SmartOCR volumes。

## 部署流程

1. 本機加入可設定的 `FRONTEND_PORT`，同步更新 `.env.example`。
2. 驗證 Compose 展開設定、前端 build 與 backend tests。
3. 提交變更並推送至 GitHub `main`。
4. EC2 確認 Docker、Compose、磁碟空間和 TCP 80 狀態。
5. clone repository 到 `/home/ubuntu/docker/smartocr`，建立權限受限的 `.env`。
6. 執行 `docker compose up -d --build`。
7. 等待 database healthcheck 與所有服務啟動。
8. 執行功能、網路和 volume 驗收。

## 驗收標準

### 服務與 HTTP

- `docker compose ps` 顯示 `db`、`backend`、`frontend` 運行中，database 為 healthy。
- EC2 本機 `curl http://127.0.0.1/health` 成功並收到 backend 健康回應。
- 從本機工作站存取 `http://3.113.155.60` 收到成功 HTTP 狀態與 SmartOCR 前端內容。
- 體驗登入入口可見；不在部署驗收中寫入正式 Google OAuth 憑證。

### Volume mount 與持久性

- 使用 `docker inspect` 比對四個 mounts 的來源、目的地與讀寫模式。
- PostgreSQL `pg_isready` 成功，資料目錄位於 `smartocr_postgres_data`。
- 在 `/app/uploads` 建立唯一名稱的臨時檔，重啟 backend 後確認檔案仍存在，再移除臨時檔。
- PaddleOCR 快取目錄 `/root/.paddlex` 可寫。
- `/app/models` mount 為唯讀，來源是 repository 的 `models` 目錄。
- 再次執行 `docker compose up -d` 後，三個 named volume ID 保持不變。

## 失敗處理與回復

若 clone、build、啟動或驗收失敗，保留 repository、`.env`、build log 與 named volumes，使用 `docker compose logs` 定位問題。不自動啟動舊 `c1-backend`，不刪除 volumes，也不以清空 Docker 資料作為修復手段。

若 port 80 已被占用，先識別占用者並回報，不強制停止非 SmartOCR 服務。若磁碟空間不足，先列出 Docker 可回收項目與影響，再決定是否清理。

首次部署沒有前一個 SmartOCR release 可回滾；可安全執行不帶 `-v` 的 `docker compose down` 停止新服務，同時保留所有持久資料。後續 release 可用 Git commit 固定版本並重新執行 Compose。
