# 實作計畫：雷達監控整合平台

## 概覽

依照設計文件，以 Python（FastAPI）後端 + 純 HTML/CSS/JS 前端的前後端分離架構實作。

---

## Tasks

- [x] 1. 專案基礎建設
  - 建立目錄結構、requirements.txt、config.yaml、systemd service 檔案
  - _需求：4.1_

- [x] 2. 設定管理與資料庫連線池
  - `config.py`：從 config.yaml 載入 DB 連線參數與系統設定
  - `database.py`：SQLAlchemy 連線池，支援三個資料庫，自動重試最多 3 次
  - _需求：4.1、4.2、4.4、4.5_

- [x] 3. Pydantic 資料模型（models.py）
  - `InstrumentStatus`、`InstrumentThresholdSetting`、`CurrentStatusResponse` 等
  - _需求：2、5_

- [x] 4. 儀器狀態服務（alert_service.py）
  - 查詢所有 FileCheck 資料表（radar/HFradar/satellite/windprofiler/DS）
  - 計算 diff_time_minutes，依 IP 查詢 SystemIPList 取得 Department
  - 無 Department 的儀器不回傳
  - 閾值從 thresholds.yaml 讀取，修改後寫回
  - _需求：2.1–2.8、5.1–5.5_

- [x] 5. 電腦系統狀態服務（system_service.py）
  - 查詢 SystemStatus.CheckList JOIN SystemIPList 取得負載/記憶體/Department
  - 查詢 DiskStatus.CheckList，透過 SystemIPList 取得 Department
  - _需求：6.1–6.4_

- [x] 6. API 路由
  - `completeness.py`：GET /api/v1/completeness/current
  - `instruments.py`：GET /api/v1/instruments、PUT /api/v1/instruments/{file_type}/threshold
  - `system.py`：GET /api/v1/system/current、GET /api/v1/disk/current
  - _需求：2、4.3、5、6_

- [x] 7. FastAPI 主程式（main.py）
  - 掛載三個 router，設定 logging，提供前端靜態檔案
  - _需求：4.1、4.5_

- [x] 8. 閾值持久化（thresholds.yaml）
  - 啟動時載入，修改後寫回，重啟後保留
  - _需求：5.3_

- [x] 9. 前端基礎架構
  - `index.html`：首頁，三個導覽入口
  - `style.css`：深色主題，儀器卡片顏色樣式（綠/黃/橙/紅/灰）
  - `api.js`：封裝所有 fetch 呼叫，統一錯誤處理
  - `clock.js`：共用時鐘，每秒更新
  - _需求：1、3.4、3.5_

- [x] 10. 儀器即時狀況頁面（instruments.html + dashboard.js）
  - 依 Department 分組顯示儀器卡片
  - 卡片顯示 IP、FileType、EquipmentName、時間差、顏色狀態
  - 超過 14400 分鐘顯示「斷線」
  - 缺資料警示時顯示最新資料時間
  - 每 10 秒自動刷新，手動刷新按鈕
  - _需求：1、2、3_

- [x] 11. 電腦即時狀況頁面（computers.html + computers.js）
  - 依 Department 分組顯示系統負載/記憶體卡片
  - 依 Department 分組顯示磁碟使用率（%）卡片
  - 記憶體 >90% 或磁碟 >85% 顯示警示樣式
  - 每 10 秒自動刷新
  - _需求：3、6_

- [x] 12. 儀器閾值設定頁面（settings.html + settings.js）
  - 列出所有儀器，顯示三段閾值（黃/橙/紅）
  - 修改後呼叫 API 寫回 thresholds.yaml
  - 負數輸入顯示驗證錯誤
  - _需求：5_

- [ ] 13. 整合測試
  - API 端點正常回應測試
  - DB 連線失敗（503）情境測試
  - PUT 負數閾值回傳 422
  - PUT 不存在 file_type 回傳 404
  - _需求：4.4、4.5、5.5_

- [ ] 14. Nginx 設定
  - 確認 `/api/v1` proxy_pass 到 backend:8000
  - 前端靜態檔案正確提供
  - _需求：4.1_

---

## 未完成項目說明

- **任務 13**：整合測試已有基礎架構（`tests/integration/test_api.py`），但需更新以反映最新 API 結構（移除完整率端點、更新閾值格式）
- **任務 14**：Nginx proxy 設定需在部署環境手動確認
