# SmartOCR 文件上傳與 AI 辨識技術文件

文件版本：1.0  
更新日期：2026-08-31  
適用系統：SmartOCR（Vue 3、FastAPI、PostgreSQL、PaddleOCR）

## 1. 文件目的

本文件說明 SmartOCR 從使用者上傳 JPG、JPEG、PNG 或 PDF 訂單，到 AI 文字辨識、欄位配對、人工確認及寫入 PostgreSQL 的完整流程，並記錄目前實際使用的 AI 模型與運算裝置。

## 2. 結論摘要

- AI OCR 框架：PaddleOCR 3.5.0
- AI 推論框架：PaddlePaddle 3.2.0
- 文字偵測模型：`PP-OCRv5_server_det`
- 文字辨識模型：`PP-OCRv5_server_rec`
- 文字行方向模型：`PP-LCNet_x1_0_textline_ori`
- 語言設定：`chinese_cht`，以繁體中文文件為主要辨識對象
- 目前運算裝置：CPU
- 目前未使用 GPU，也未使用 CUDA
- 欄位抽取方式：OCR AI 模型加上座標式規則解析
- 目前沒有使用生成式 AI 或大型語言模型（LLM）

PaddleOCR 負責找出文字位置與辨識文字；「客戶名稱」、「報價單號」、「未稅總計」等業務欄位，則由系統根據標籤、同一水平列、最近右側文字及簽核欄位下方文字等規則進行配對。

## 3. 系統元件

| 層級 | 技術 | 主要責任 |
|---|---|---|
| 前端 | Vue 3、Vite | 檔案選擇、預覽、分析進度、欄位確認與修改 |
| API | FastAPI | 驗證登入、接收檔案、啟動 OCR、回傳分析結果 |
| OCR | PaddleOCR 3.5.0 | 文字區域偵測、文字辨識、文字行方向判斷 |
| 影像處理 | Pillow、pypdfium2 | 圖片放大、方向校正、PDF 頁面轉圖片 |
| 欄位解析 | Python 座標規則 | 將 OCR 文字配對到訂單欄位 |
| ORM | SQLAlchemy Async | 訂單資料存取 |
| 資料庫 | PostgreSQL 16 | 儲存訂單、帳號、OCR 原文及結構化欄位 |
| 執行環境 | Docker Compose | 啟動前端、後端與資料庫服務 |

## 4. 完整處理流程

```text
使用者選擇檔案
        │
        ▼
Vue 前端檢查格式並建立 FormData
        │  POST /api/orders/ocr
        │  Authorization: Bearer <JWT>
        ▼
FastAPI 驗證帳號與檔案
        │
        ▼
暫存原始檔案並產生 upload_token
        │
        ▼
圖片／PDF 前處理
        │
        ▼
PaddleOCR AI 推論
        │
        ├─ 文字偵測
        ├─ 文字辨識
        └─ 文字行方向判斷
        │
        ▼
依座標與標籤進行欄位配對
        │
        ▼
回傳原始文字、每行信心分數、座標與建議欄位
        │
        ▼
使用者確認／修改欄位
        │  POST /api/orders
        ▼
原始檔案歸檔＋訂單寫入 PostgreSQL
```

### 4.1 前端上傳

前端允許的副檔名為：

- `.jpg`
- `.jpeg`
- `.png`
- `.pdf`

使用者按下「開始 AI 辨識」後，前端將檔案放入 `FormData` 的 `file` 欄位，呼叫：

```http
POST /api/orders/ocr
Content-Type: multipart/form-data
Authorization: Bearer <JWT>
```

畫面上的 AI 分析進度會從 6% 平滑增加，最高暫停在 92%；後端真正回傳結果後才會顯示 100%。因此這個百分比是使用者體驗用的階段進度，不是 PaddleOCR 回報的逐頁實際百分比。

### 4.2 後端檔案驗證與暫存

FastAPI 收到檔案後會執行以下檢查：

1. 使用者必須先登入並具有有效 JWT。
2. 副檔名必須是 JPG、JPEG、PNG 或 PDF。
3. 檔案大小不可超過 20 MB。
4. 系統產生隨機 `upload_token`，將檔案暫存在 `/app/uploads`。

OCR 是同步且較耗 CPU 的工作，因此 API 使用 `asyncio.to_thread()` 將辨識工作移到背景執行緒，避免直接阻塞 FastAPI 的非同步事件迴圈。

### 4.3 圖片與 PDF 前處理

#### 一般圖片

- 先使用 Pillow 套用 EXIF 方向，避免手機照片旋轉錯誤。
- 圖片寬度若小於 1400 像素，會使用 LANCZOS 放大。
- 放大倍率以接近 1600 像素寬為目標，最高不超過 2.5 倍。
- 放大後轉成 RGB PNG，再交給 PaddleOCR。

這項處理主要改善低解析度截圖中的小型灰色欄位文字，例如「客戶單位」、「報價單狀態」。

#### PDF

- 使用 `pypdfium2` 逐頁開啟 PDF。
- 每一頁以 2.2 倍比例渲染為 PNG。
- OCR 結果會保留頁碼，供多頁文件使用。

前處理產生的中間圖片放在暫存目錄，OCR 結束後會自動清除。

### 4.4 PaddleOCR AI 推論

OCR 引擎採延遲初始化：後端第一次收到 OCR 請求時才建立 PaddleOCR 實例，之後重複使用同一個模型實例。

目前設定如下：

```python
PaddleOCR(
    lang="chinese_cht",
    use_doc_orientation_classify=False,
    use_doc_unwarping=False,
    use_textline_orientation=True,
)
```

實際模型目錄顯示目前載入：

| 模型 | 用途 |
|---|---|
| `PP-OCRv5_server_det` | 找出頁面上的文字區域及文字框座標 |
| `PP-OCRv5_server_rec` | 將文字區域辨識為實際字串 |
| `PP-LCNet_x1_0_textline_ori` | 判斷文字行方向，降低倒置文字的辨識錯誤 |

目前關閉整份文件方向分類與文件去扭曲，但保留文字行方向判斷。

每一段辨識結果包含：

```json
{
  "text": "客戶名稱",
  "confidence": 0.9821,
  "box": [[29, 179], [96, 179], [96, 197], [29, 197]],
  "page": 1
}
```

- `text`：辨識文字
- `confidence`：該文字行的模型信心分數，範圍為 0 到 1
- `box`：文字框四個角的座標
- `page`：所在頁碼

為避免多個請求同時操作同一個 PaddleOCR 實例，目前使用預測鎖，OCR 推論會依序執行。這可提升穩定性，但大量同時上傳時會形成等待佇列。

### 4.5 結構化欄位配對

PaddleOCR 的輸出仍是文字行與座標，不會直接知道哪一段是「客戶名稱」。SmartOCR 會再執行欄位解析器：

1. 比對繁體、簡體、英文及常見 OCR 錯字的欄位標籤。
2. 一般欄位選取同一水平列、標籤右側最近的文字。
3. 遇到右側下一個欄位標籤時停止，避免跨欄抓值。
4. 客戶確認、業務確認、主管核准改為選取同欄位下方最近的文字。
5. 下方簽核值最大距離限制為 260 像素，避免抓到頁尾說明。
6. 專案名稱支援同一儲存格內的多行文字，但限制垂直範圍，避免合併上下列。
7. 日期轉成 `YYYY-MM-DD`。
8. 金額移除 `NT$`、逗號及千分位符號，再轉成數值。
9. 常見簡繁體與 OCR 誤字會進行正規化，例如 `户` 轉成 `戶`、`税` 轉成 `稅`。

目前會輸出的主要欄位如下：

- 基本資訊：客戶名稱、報價單號、客戶單位、報價日期、連絡人、專案部門、連絡電話、業務、專案名稱、電話、業務窗口、報價單狀態
- 金額資訊：未稅總計、5% 稅額、含稅總計、含稅優惠價格
- 付款與條件：付款條件、報價有效期限、備註
- 簽核資訊：客戶確認、業務確認、主管核准

### 4.6 信心指數

前端顯示的整份文件信心指數，是所有 OCR 文字行 `confidence` 的算術平均值：

```text
文件信心指數 = 所有文字行信心分數總和 ÷ 文字行數量 × 100%
```

例如畫面顯示 85%，代表所有已辨識文字行的平均分數約為 0.85。這不是每個結構化欄位各自的信心分數，也不代表所有欄位都有 85% 的正確率。

系統另外將低於 0.8 的文字行視為低信心內容，前端可顯示低信心文字數量，協助人工檢查。

### 4.7 人工確認與資料儲存

OCR 完成後，前端先顯示原始文件及結構化欄位。使用者可以確認或修改所有欄位，確認後再呼叫訂單建立 API。

儲存時會執行：

1. 建立訂單 UUID。
2. 將暫存原始檔案移至 `/app/uploads/orders/<order_id>/source.<副檔名>`。
3. 寫入 PostgreSQL `orders` 資料表。
4. 以 `owner_id` 將訂單與登入帳號關聯。

主要資料庫內容包括：

- 常用查詢欄位：訂單編號、客戶名稱、訂單日期、總金額、幣別、狀態
- `raw_text`：OCR 原始文字
- `extracted_data`：所有結構化欄位，以 PostgreSQL JSONB 儲存
- `source_path`：原始檔案保存位置
- `owner_id`：訂單擁有者
- `created_at`、`updated_at`：建立與修改時間

一般使用者只能查詢自己帳號的訂單；最高管理員可以查詢所有帳號的訂單。

## 5. CPU 與 GPU 使用狀態

### 5.1 目前實際狀態

目前系統使用 CPU 執行 PaddleOCR。

運行中容器的實際檢查結果：

```text
device=cpu
cuda_compiled=False
custom_device=[]
```

原因如下：

- Python 套件安裝的是 `paddlepaddle==3.2.0`，不是 GPU 版本。
- Docker 映像以 `python:3.11-slim` 為基礎，沒有 CUDA 執行環境。
- Docker Compose 沒有配置 NVIDIA GPU 裝置。
- 容器內的 PaddlePaddle 回報未編譯 CUDA。

因此即使主機有 NVIDIA 顯示卡，目前這個 Docker 設定也不會使用 GPU。

### 5.2 CPU 模式的特性

優點：

- 一般電腦即可啟動，不依賴 NVIDIA GPU。
- Docker 部署方式較簡單。
- 適合低到中等文件量，以及目前的單機使用情境。

限制：

- Server 等級 OCR 模型在 CPU 上的推論速度較慢。
- 多頁 PDF 或高解析度圖片會增加分析時間。
- 目前推論鎖會讓同時上傳的文件依序分析。
- 第一次使用可能需要下載模型，因此首次分析通常較久。

### 5.3 若未來改用 GPU

改用 GPU 時至少需要：

1. 主機安裝相容的 NVIDIA 驅動程式與 NVIDIA Container Toolkit。
2. 改用與 CUDA 版本相容的 PaddlePaddle GPU 套件。
3. 後端 Docker 映像加入相容的 CUDA 執行環境。
4. 在 Docker Compose 將 GPU 裝置提供給 backend 容器。
5. 重新確認 PaddlePaddle 顯示的裝置為 GPU。

PaddlePaddle GPU、CUDA 與 cuDNN 版本必須互相相容，切換前應依部署主機環境選擇版本，不建議只將套件名稱直接改成 GPU 版。

## 6. 模型 Fine-tune 擴充方式

目前先使用 PaddleOCR 官方預訓練模型。若未來累積足夠的錯誤案例，可對文字偵測模型或文字辨識模型進行 fine-tune。

Docker 已保留自訂模型掛載位置：

```text
主機 ./models  →  容器 /app/models（唯讀）
```

環境變數：

```env
OCR_DET_MODEL_DIR=/app/models/det
OCR_REC_MODEL_DIR=/app/models/rec
```

- `OCR_DET_MODEL_DIR`：自訂文字偵測 inference model
- `OCR_REC_MODEL_DIR`：自訂文字辨識 inference model

設定後重新建立或啟動 backend 容器，PaddleOCR 初始化時就會改用指定模型。

建議先蒐集以下資料再評估 fine-tune：

- OCR 錯誤的原始圖片或 PDF 頁面
- 正確文字標註
- 文字框座標標註（若要訓練偵測模型）
- 文件類型、解析度與錯誤原因
- 修改前文字、人工修改後文字及原始信心分數

如果問題主要是「文字已辨識正確，但沒有填入正確欄位」，應先調整座標與欄位解析規則；只有文字本身長期辨識錯誤，才優先考慮 fine-tune 辨識模型。

## 7. 已知限制與維運注意事項

1. 目前整體信心分數是文字行平均值，不是欄位級信心分數。
2. 欄位配對依賴版面座標與標籤規則，遇到全新格式可能需要補充規則。
3. 手寫簽名、印章、極小文字、模糊照片及嚴重傾斜文件的準確率較低。
4. 目前未開啟整頁方向分類與文件去扭曲，拍照文件若有明顯透視變形可能受影響。
5. 目前僅檢查副檔名與大小；正式對外服務建議增加 MIME／檔案特徵驗證、惡意檔案掃描與上傳頻率限制。
6. OCR 推論目前單序列執行；若同時使用人數增加，應改成工作佇列與多個 OCR worker。
7. Paddle 模型保存在 Docker volume `paddle_models`，移除該 volume 後首次辨識會重新下載模型。

## 8. 重要程式位置

| 功能 | 路徑 |
|---|---|
| 前端上傳與分析畫面 | `frontend/src/views/NewOrderView.vue` |
| OCR API | `backend/app/api/orders.py` |
| 檔案驗證與保存 | `backend/app/services/file_store.py` |
| OCR 初始化、前處理與欄位解析 | `backend/app/services/ocr.py` |
| OCR API 回傳格式 | `backend/app/schemas/order.py` |
| 訂單資料庫模型 | `backend/app/models/order.py` |
| Python 套件版本 | `backend/requirements.txt` |
| Docker 服務與模型掛載 | `docker-compose.yml` |
| 自訂模型環境變數範例 | `.env.example` |

## 9. 驗證目前運算裝置

維運人員可以在專案目錄執行以下指令確認 PaddleOCR 使用的運算裝置：

```powershell
docker exec smartocr-backend-1 python -c "import paddle; print(paddle.device.get_device()); print(paddle.device.is_compiled_with_cuda())"
```

目前預期輸出：

```text
cpu
False
```

若未來完成 GPU 部署，第一行應顯示 GPU 裝置，CUDA 檢查也應為 `True`。
