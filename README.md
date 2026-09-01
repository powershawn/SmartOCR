# SmartOCR 智慧訂單辨識平台

完整的 Vue 3 + FastAPI + PostgreSQL 訂單 OCR 系統。使用者可上傳 JPG、JPEG、PNG 或 PDF，由 PaddleOCR 擷取文字，人工確認／修改後才寫入資料庫。

## 已包含功能

- Google Social Login（Google Identity Services）
- JWT API 驗證
- 一般帳號只能讀寫自己的訂單
- 指定最高管理員可檢視、篩選及修改所有帳號訂單
- 圖片與多頁 PDF OCR
- OCR 平均信心、逐行文字／頁碼／信心分數、原始文字與結構化結果保存
- 低於 80% 的辨識行醒目標示，方便人工對照原始文件
- 訂單上傳、擷取、確認修改、儲存、查詢與篩選
- 全站 API 錯誤彈窗與易讀的欄位錯誤提示
- PaddleOCR 預訓練模型與自訂 fine-tune 模型目錄
- 響應式科技風操作介面
- Docker Compose 一鍵啟動

## 快速啟動

需求：Docker Desktop（建議配置至少 6 GB 記憶體）。

```powershell
Copy-Item .env.example .env
docker compose up --build
```

啟動後開啟：

- 網頁：http://localhost:8080
- API 文件：http://localhost:8000/docs
- 健康檢查：http://localhost:8000/health

## 同一網路共用

前端服務已綁定 `0.0.0.0:8080`。同一個 Wi-Fi／LAN 的使用者可以用這台電腦的區網 IP 開啟，例如：

```text
http://192.168.1.100:8080
```

在 Windows 執行 `ipconfig`，從目前使用中的網路介面找到「IPv4 位址」。若其他裝置無法開啟，請以系統管理員身分執行以下指令，允許 Windows 防火牆的 TCP 8080：

```powershell
New-NetFirewallRule -DisplayName "SmartOCR Web" -Direction Inbound -Protocol TCP -LocalPort 8080 -Action Allow -Profile Private
```

只有網頁的 `8080` 對區網開放。PostgreSQL `5432` 與 FastAPI 開發文件 `8000` 維持只允許本機連線，避免資料庫與管理介面直接暴露在區網。

> Google Identity Services 通常只允許 `localhost` 使用 HTTP；以區網 IP 使用正式 Google 登入時，需要具有有效憑證的 HTTPS 網址，並將該網址加入 Google OAuth 的 Authorized JavaScript origins。本機開發體驗登入不受此限制，但不應用於正式環境。

第一次執行 OCR 時，PaddleOCR 會下載預訓練模型，因此會比之後辨識久。模型會保存在 Docker volume，不會每次重抓。

## 設定 Google 登入

1. 到 [Google Cloud Console](https://console.cloud.google.com/apis/credentials) 建立 OAuth 2.0 Client ID，應用程式類型選「Web application」。
2. 在 Authorized JavaScript origins 加入 `http://localhost:8080`；若使用 Vite 開發模式，再加入 `http://localhost:5173`。
3. 將 Client ID 填入 `.env` 的 `GOOGLE_CLIENT_ID`。
4. 將最高管理員的 Google 信箱填入 `SUPER_ADMIN_EMAIL`。
5. 正式環境把 `ALLOW_DEV_LOGIN` 與 `VITE_ALLOW_DEV_LOGIN` 都設為 `false`，並使用安全的 `JWT_SECRET`。
6. 重新執行 `docker compose up --build`，讓 Client ID 寫入前端建置。

指定的 `SUPER_ADMIN_EMAIL` 第一次成功登入時會自動取得 `admin` 角色；其他帳號為 `user`。管理員權限在 API 端判斷，不只是在畫面上隱藏選項。

## 開發體驗登入

範例環境預設開啟開發登入，可在沒有 Google Client ID 時先測試：

- 「體驗一般帳號」：只能看到自己的訂單。
- 「體驗最高管理員」：使用預設 `admin@example.com`，可查看所有資料。

若修改 `SUPER_ADMIN_EMAIL`，請將 `VITE_SUPER_ADMIN_EMAIL` 設為相同信箱，讓管理員體驗按鈕使用相同設定。

## 訂單資料

`orders` 表的主要欄位：

| 欄位 | 說明 |
|---|---|
| `owner_id` | 訂單所屬帳號 |
| `order_number` | 訂單編號 |
| `customer_name` | 客戶名稱 |
| `order_date` | 訂單日期 |
| `total_amount` / `currency` | 金額與幣別 |
| `raw_text` | OCR 原始文字 |
| `extracted_data` | OCR 行、座標、信心分數與建議欄位（JSONB） |
| `source_path` | 容器內的原始文件位置 |

開發版啟動時由 SQLAlchemy 自動建立 `users` 與 `orders` 表。若要進正式環境，建議下一階段導入 Alembic 管理 schema migration，並將檔案儲存換成 S3 相容物件儲存。

## 使用 fine-tune 模型

目前使用 PaddleOCR 預訓練繁體中文模型。若辨識結果不足：

1. 收集並標註實際訂單樣本，分別訓練 detection／recognition 模型。
2. 匯出 PaddleOCR inference model。
3. 將模型放在 `./models/det` 與 `./models/rec`。
4. 在 `.env` 設定：

```env
OCR_DET_MODEL_DIR=/app/models/det
OCR_REC_MODEL_DIR=/app/models/rec
```

5. 重新啟動 backend。OCR 服務已封裝在 `backend/app/services/ocr.py`，訂單 API 與 UI 不必修改。

## 專案結構

```text
SmartOCR/
├─ frontend/                Vue 3 + Vite
├─ backend/                 FastAPI + PaddleOCR
│  └─ app/
│     ├─ api/               登入、訂單、管理員 API
│     ├─ models/            SQLAlchemy 資料模型
│     ├─ schemas/           API 資料驗證
│     └─ services/          OCR 與檔案保存
├─ models/                  自訂 inference model 掛載點
├─ docker-compose.yml
└─ .env.example
```

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

## 常用指令

```powershell
# 背景啟動
docker compose up -d --build

# 查看服務狀態
docker compose ps

# 查看後端記錄
docker compose logs -f backend

# 停止（保留資料）
docker compose down

# 停止並刪除資料庫、上傳檔與模型快取
docker compose down -v
```

最後一個指令會永久刪除 Docker volumes，請只在確定不需保留資料時使用。
