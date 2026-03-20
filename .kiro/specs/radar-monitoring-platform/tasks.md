# 實作計畫：雷達監控整合平台

## 概覽

依照設計文件，以 Python（FastAPI）後端 + 純 HTML/CSS/JS 前端的前後端分離架構實作。
任務依「基礎建設 → 後端服務 → API 路由 → 前端 → 整合」順序遞增推進，每個步驟均可獨立驗證。

---

## Tasks

- [x] 1. 專案基礎建設
  - 建立目錄結構：`backend/`、`frontend/css/`、`frontend/js/`、`config/`、`logs/`、`deploy/`、`tests/unit/`、`tests/integration/`、`tests/property/`
  - 建立 `backend/requirements.txt`，列出 fastapi、uvicorn、sqlalchemy、pymysql、pyyaml、pydantic、hypothesis、pytest、httpx、pytest-mock
  - 建立 `config/config.yaml`，包含三個資料庫（FileStatus、SystemStatus、DiskStatus）連線參數及 system 區段（radar_interval_minutes、query_timeout_seconds、reconnect_interval_seconds、max_reconnect_attempts、default_max_diff_time_threshold）與 instruments 初始閾值
  - 建立 `deploy/radar-monitor.service` systemd 服務設定檔
  - _需求：6.1_

- [ ] 2. 設定管理與資料庫連線池
  - [x] 2.1 實作 `backend/config.py`
    - 使用 PyYAML 從 `config/config.yaml` 載入所有設定，提供型別安全的存取介面
    - 不得在任何地方硬編碼連線參數或閾值
    - _需求：6.1_
  - [ ]* 2.2 為 config 載入撰寫單元測試
    - 測試正常載入、缺少必要欄位時的錯誤處理
    - _需求：6.1_
  - [x] 2.3 實作 `backend/database.py`
    - 使用 SQLAlchemy 為三個資料庫（FileStatus、SystemStatus、DiskStatus）各建立獨立連線池
    - 實作 `get_engine(db_name)`、`get_session(db_name)`、`check_connection(db_name)` 介面
    - 連線中斷時自動重試，最多 3 次，間隔 10 秒；3 次均失敗後記錄 ERROR 日誌
    - _需求：6.2、6.4、6.5_
  - [ ]* 2.4 為資料庫重連邏輯撰寫屬性測試
    - **屬性 10：資料庫重連重試上限**
    - **驗證需求：6.4、6.5**
    - `# Feature: radar-monitoring-platform, Property 10: 重連次數不超過 3 次，每次間隔不少於 10 秒`
    - _需求：6.4、6.5_

- [x] 3. Pydantic 資料模型
  - 在 `backend/models.py` 定義所有 Pydantic 模型：`CompletenessResult`、`TimeSeriesPoint`、`InstrumentStatus`、`InstrumentThresholdSetting`
  - `InstrumentThresholdSetting.max_diff_time_threshold` 使用 `Field(ge=0.0)` 驗證
  - _需求：2.1、3.1、7.3、7.5_

- [ ] 4. 資料完整率服務
  - [-] 4.1 實作 `backend/services/completeness_service.py`
    - 實作 `calculate_completeness(start_time, end_time) -> CompletenessResult`，依設計文件 SQL 計算完整率
    - 實作 `get_time_series(start_time, end_time) -> list[TimeSeriesPoint]`，以小時聚合，標記 completeness_rate < 90% 的點為 is_alert=True
    - 查詢逾時上限 5 秒；空結果回傳 status="no_data"；連線失敗回傳 status="db_error" 並保留上次成功數值
    - _需求：2.1、2.2、2.3、2.4、4.1、4.2、6.3_
  - [ ]* 4.2 為完整率計算撰寫屬性測試
    - **屬性 2：資料完整率數值範圍**
    - **驗證需求：2.1**
    - `# Feature: radar-monitoring-platform, Property 2: 對任意 actual_count 與 expected_count，completeness_rate 應在 0.0–100.0 範圍內`
    - _需求：2.1_
  - [ ]* 4.3 為查詢結果處理撰寫屬性測試
    - **屬性 3：查詢結果處理一致性**
    - **驗證需求：2.2、2.3、2.4**
    - `# Feature: radar-monitoring-platform, Property 3: 查詢狀態與回應 status 欄位一致，db_error 時保留上次成功數值`
    - _需求：2.2、2.3、2.4_
  - [ ]* 4.4 為時間序列查詢邊界撰寫屬性測試
    - **屬性 7：時間序列查詢邊界**
    - **驗證需求：4.3**
    - `# Feature: radar-monitoring-platform, Property 7: 回傳資料點的時間戳記均落在 [start, end] 區間內`
    - _需求：4.3_
  - [ ]* 4.5 撰寫完整率服務單元測試
    - 測試空查詢結果顯示 status="no_data"（需求 2.4）
    - 測試預設時間區間為 24 小時（需求 4.2）
    - _需求：2.4、4.2_

- [ ] 5. 警示服務
  - [~] 5.1 實作 `backend/services/alert_service.py`
    - 實作 `get_all_instrument_statuses() -> list[InstrumentStatus]`，查詢 `radarFileCheck` 最新快照，計算 `diff_time_minutes = (NOW() - FROM_UNIXTIME(FileTime)) / 60`
    - 實作 `get_instrument_threshold(file_type) -> float`，未設定時回傳 config 預設值（30 分鐘）
    - 實作 `set_instrument_threshold(file_type, threshold_minutes) -> None`，儲存於記憶體 dict
    - FileTime 為 NULL 時，`diff_time_minutes` 為 None，`is_alert` 為 True
    - _需求：3.1、3.2、3.3、3.4、3.5、3.6_
  - [ ]* 5.2 為警示觸發邏輯撰寫屬性測試
    - **屬性 4：警示觸發邏輯一致性**
    - **驗證需求：3.1、3.2、3.3**
    - `# Feature: radar-monitoring-platform, Property 4: is_alert 與 diff_time_minutes > max_diff_time_threshold 完全一致，各儀器獨立計算`
    - _需求：3.1、3.2、3.3_
  - [ ]* 5.3 為警示物件完整性撰寫屬性測試
    - **屬性 5：警示物件完整性**
    - **驗證需求：3.4**
    - `# Feature: radar-monitoring-platform, Property 5: 觸發警示的物件必須包含 file_type、triggered_at、diff_time_minutes 三個非空欄位`
    - _需求：3.4_
  - [ ]* 5.4 為儀器時間差計算撰寫屬性測試
    - **屬性 11：儀器時間差計算正確性**
    - **驗證需求：3.5、3.6**
    - `# Feature: radar-monitoring-platform, Property 11: diff_time_minutes 為非負數；FileTime 為 NULL 時 is_alert 為 True`
    - _需求：3.5、3.6_
  - [ ]* 5.5 撰寫警示服務單元測試
    - 測試未設定閾值時預設值為 30 分鐘（需求 3.6）
    - 測試各儀器警示狀態區塊獨立（需求 3.3）
    - _需求：3.3、3.6_

- [ ] 6. 儀器閾值管理服務
  - [ ] 6.1 在 `alert_service.py` 補充閾值驗證邏輯
    - `set_instrument_threshold` 拒絕負數輸入（由 Pydantic `ge=0.0` 在路由層攔截，服務層亦需防禦性驗證）
    - 確保不同儀器的閾值設定互相獨立，修改一個不影響其他
    - _需求：7.3、7.4、7.5_
  - [ ]* 6.2 為儀器閾值設定撰寫屬性測試
    - **屬性 6：儀器閾值設定驗證**
    - **驗證需求：7.3、7.4、7.5**
    - `# Feature: radar-monitoring-platform, Property 6: 拒絕負數輸入；非負數值正確儲存；各儀器閾值互相獨立`
    - _需求：7.3、7.4、7.5_

- [ ] 7. Checkpoint — 確認後端服務層測試全數通過
  - 執行 `pytest tests/unit tests/property`，確認所有測試通過，如有問題請提出。

- [ ] 8. API 路由實作
  - [ ] 8.1 實作 `backend/routers/completeness.py`
    - `GET /api/v1/completeness/current`：呼叫 `alert_service.get_all_instrument_statuses()`，回傳 InstrumentStatus 列表；DB 錯誤時回傳 503
    - `GET /api/v1/completeness/timeseries`：接受 `start`/`end` 查詢參數（預設最近 24 小時），呼叫 `completeness_service.get_time_series()`；無資料時回傳 204
    - _需求：2.1、2.2、2.3、2.4、3.1、4.1、4.2、4.3、4.6_
  - [ ] 8.2 實作 `backend/routers/instruments.py`
    - `GET /api/v1/instruments`：從 `FileTypeList` 取得儀器清單，附帶各儀器目前閾值
    - `PUT /api/v1/instruments/{file_type}/threshold`：驗證 `max_diff_time_threshold >= 0`（Pydantic），呼叫 `alert_service.set_instrument_threshold()`；file_type 不存在回傳 404；負數回傳 422
    - _需求：7.1、7.2、7.3、7.4、7.5_
  - [ ] 8.3 實作 `backend/main.py`
    - 建立 FastAPI 應用程式，掛載 completeness 與 instruments 路由
    - 設定 logging（輸出至 `logs/app.log`，格式 `%(asctime)s [%(levelname)s] %(name)s: %(message)s`）
    - 以 FastAPI StaticFiles 提供 `frontend/` 靜態檔案
    - _需求：6.1、6.5_
  - [ ]* 8.4 撰寫 API 整合測試
    - 使用 `pytest` + `httpx` 測試各端點正常回應
    - 使用 `pytest-mock` 模擬 DB 連線失敗（503）、查詢逾時（504）情境
    - 測試 PUT 不存在的 file_type 回傳 404（需求 7.1）
    - 測試 PUT 負數閾值回傳 422（需求 7.5）
    - _需求：2.3、6.3、7.1、7.5_

- [ ] 9. 前端基礎架構
  - [ ] 9.1 建立 `frontend/index.html`
    - 頁面頂部顯示本地時間與 UTC 時間的元素（id="local-time"、id="utc-time"）
    - 資料完整率顯示區塊、儀器警示狀態區塊（每個儀器獨立）、時間序列圖容器
    - 手動刷新按鈕、上次刷新時間戳記顯示、錯誤提示區塊
    - 引入 Chart.js CDN 與 `api.js`、`chart.js`、`dashboard.js`
    - _需求：1.1、2.1、3.3、5.3、5.5_
  - [ ] 9.2 建立 `frontend/css/style.css`
    - 警示區塊紅色樣式（`.alert-block`）
    - 低完整率資料點標示樣式
    - 錯誤提示樣式
    - _需求：3.1、4.5_
  - [ ] 9.3 實作 `frontend/js/api.js`
    - 封裝所有 `fetch` 呼叫：`fetchCurrentStatus()`、`fetchTimeSeries(start, end)`、`fetchInstruments()`、`updateThreshold(fileType, value)`
    - 統一錯誤處理：網路錯誤拋出可識別的錯誤物件，供 dashboard.js 顯示提示
    - _需求：2.3、5.4、6.3_

- [ ] 10. 前端時間顯示與自動刷新
  - [ ] 10.1 實作 `frontend/js/dashboard.js` — 時間顯示
    - 頁面載入後立即顯示本地時間與 UTC 時間
    - 以 `setInterval` 每秒更新，格式 `YYYY-MM-DD HH:mm:ss`
    - _需求：1.1、1.2、1.3、1.4_
  - [ ]* 10.2 為時間格式化撰寫屬性測試
    - **屬性 1：時間格式化正確性**
    - **驗證需求：1.3、1.4**
    - `# Feature: radar-monitoring-platform, Property 1: 對任意有效 datetime，格式化輸出符合 YYYY-MM-DD HH:mm:ss`
    - _需求：1.3、1.4_
  - [ ] 10.3 實作 `frontend/js/dashboard.js` — 自動刷新控制器
    - 以 10 秒為週期呼叫 `api.js` 取得最新資料，更新完整率、警示狀態、圖表，不重新載入頁面
    - 更新 `last_refreshed_at` 時間戳記（單調遞增）
    - 網路錯誤時顯示「資料更新失敗，正在重試」，下一個週期自動重試
    - 手動刷新按鈕立即觸發更新並重置計時器
    - _需求：5.1、5.2、5.3、5.4、5.5_
  - [ ]* 10.4 為刷新時間戳記撰寫屬性測試
    - **屬性 8：刷新後時間戳記更新**
    - **驗證需求：5.3**
    - `# Feature: radar-monitoring-platform, Property 8: 成功刷新後 last_refreshed_at 不早於刷新前的時間戳記`
    - _需求：5.3_
  - [ ]* 10.5 為網路錯誤重試撰寫屬性測試
    - **屬性 9：網路錯誤重試行為**
    - **驗證需求：5.4**
    - `# Feature: radar-monitoring-platform, Property 9: 網路錯誤後立即顯示錯誤提示，下一個 Refresh_Interval 重新嘗試`
    - _需求：5.4_
  - [ ]* 10.6 撰寫自動刷新單元測試
    - 測試手動刷新按鈕觸發更新（需求 5.5）
    - 測試頁面載入後時間元素非空（需求 1.1、1.2）
    - _需求：1.1、1.2、5.5_

- [ ] 11. 前端時間序列圖
  - [ ] 11.1 實作 `frontend/js/chart.js`
    - 使用 Chart.js 繪製折線圖，X 軸為時間，Y 軸固定 0–100%
    - 預設顯示最近 24 小時資料
    - completeness_rate < 90% 的資料點以紅色標示
    - 支援自訂時間區間（重新查詢並更新圖表）
    - 無資料時顯示「所選區間無資料」提示
    - _需求：4.1、4.2、4.3、4.4、4.5、4.6_

- [ ] 12. 前端儀器警示狀態顯示
  - [ ] 12.1 在 `frontend/js/dashboard.js` 實作儀器警示渲染
    - 為每個 Instrument 各自渲染獨立的警示狀態區塊
    - is_alert=true 時顯示紅色警示區塊，包含儀器名稱、觸發時間戳記、實際 DiffTime（分鐘）
    - is_alert=false 時隱藏警示區塊
    - _需求：3.1、3.2、3.3、3.4_

- [ ] 13. 前端儀器閾值設定介面
  - [ ] 13.1 在 `frontend/index.html` 新增閾值設定區塊
    - 列出所有儀器及其目前 Max_DiffTime_Threshold（分鐘）
    - 每個儀器提供輸入欄位與儲存按鈕
    - _需求：7.2_
  - [ ] 13.2 在 `frontend/js/dashboard.js` 實作閾值設定互動
    - 呼叫 `api.js` 的 `updateThreshold()`，成功後立即更新顯示值
    - 輸入負數時顯示驗證錯誤訊息（422 回應處理）
    - file_type 不存在時顯示「找不到指定儀器」（404 回應處理）
    - _需求：7.3、7.4、7.5_

- [ ] 14. Checkpoint — 確認所有測試通過，整合前後端
  - 執行 `pytest`，確認所有單元、屬性、整合測試通過
  - 確認前端靜態檔案由 FastAPI StaticFiles 正確提供
  - 確認 `config.yaml` 中無任何硬編碼連線參數
  - 如有問題請提出。

---

## 備註

- 標記 `*` 的子任務為選填，可跳過以加速 MVP 交付
- 每個任務均標記對應需求，確保可追溯性
- 屬性測試需標記 `# Feature: radar-monitoring-platform, Property {N}: ...` 並至少執行 100 次迭代
- 閾值設定在服務重啟後回復為 config.yaml 預設值（記憶體儲存策略）
