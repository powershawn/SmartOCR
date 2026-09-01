# SmartOCR 科技感 Favicon 設計

## 目標

為 SmartOCR 製作一個在瀏覽器分頁小尺寸下仍清楚可辨識的科技感 favicon，取代目前沒有明確 favicon 的狀態。圖示須呼應 OCR 掃描功能與現有深色、青綠色介面，不改動頁面內容或其他品牌元件。

## 視覺方向

採用「掃描框＋電路節點」構圖：

- 深海軍藍圓角方形底，延續網站 `#07111f` 的暗色科技風。
- 四角使用青綠色掃描框，形成文件辨識與取景器意象。
- 中央放置三條簡化文字線，表示 OCR 文件內容。
- 四周配置少量電路節點與短連線，傳達 AI 與數位處理。
- 主色使用現有介面的青綠色系，搭配少量亮青色高光；不使用漸層、陰影或細碎文字。

圖形必須以 16×16 顯示效果為硬限制：線條不可過細，元素數量保持精簡，中央留出負空間，縮小後仍能看出掃描框與文件線條。

## 實作方式

- 新增 `frontend/public/favicon.svg`，使用純 SVG 幾何圖形，不引用外部字型、圖片、腳本或網路資源。
- SVG 使用方形 `viewBox`，背景、掃描框、文字線和節點均以向量繪製。
- 在 `frontend/index.html` 的 `<head>` 加入明確的 SVG favicon `<link>`。
- 保留既有 `theme-color` 與頁面標題，不修改 Vue 元件或全站 CSS。

只提供單一 SVG favicon。現代目標瀏覽器均可直接使用 SVG；目前不增加 PNG、ICO 或 Apple Touch Icon，以避免維護多份輸出。

## 驗收

- SVG 為有效 XML，具有 `viewBox`，且不包含外部引用或嵌入腳本。
- `frontend/index.html` 正確指向 `/favicon.svg`，MIME type 為 `image/svg+xml`。
- frontend production build 成功。
- Docker 重新建置並部署後，`/favicon.svg` 回應 HTTP 200 且內容類型正確。
- 瀏覽器分頁可顯示新圖示；若瀏覽器快取舊圖示，使用硬重新整理或重新開啟分頁確認。

## 部署範圍

變更提交到 GitHub `main` 後，在 EC2 `/home/ubuntu/docker/smartocr` 以 fast-forward pull 更新，只重新建置並重建 frontend 服務。Backend、PostgreSQL 與三個既有 named volumes 不重建、不刪除，也不執行 `docker compose down -v`。
