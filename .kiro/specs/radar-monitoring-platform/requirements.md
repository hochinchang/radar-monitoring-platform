# 需求文件

## 簡介

雷達監控整合平台是一套網頁應用系統，部署於 Linux（Rocky 9）環境，以 MySQL 作為資料來源，提供操作人員即時監控各儀器資料時間差與電腦系統狀態的能力。系統透過 Dashboard 集中呈現關鍵指標，並以自動刷新機制確保資訊即時性。資料異常的主動推播通知由外部系統負責，本平台僅負責視覺化呈現。

---

## 詞彙表

- **平台（Platform）**：本雷達監控整合平台網頁應用系統的總稱。
- **Dashboard**：平台的主要監控畫面，集中顯示所有即時指標。
- **缺資料警示（Missing_Data_Alert）**：當某儀器最新資料的時間差（DiffTime）超過該儀器設定的閾值時，Dashboard 以顏色（黃/橙/紅）顯示的視覺提示。主動推播通知由外部系統負責。
- **儀器（Instrument）**：對應 FileType，代表一種雷達資料類型或設備，每個儀器有各自獨立的閾值設定。
- **資料庫（Database）**：儲存雷達資料的 MySQL 資料庫。
- **刷新週期（Refresh_Interval）**：Dashboard 自動向後端重新取得最新資料的時間間隔，固定為 10 秒。
- **本地時間（Local_Time）**：伺服器或瀏覽器所在時區的當前時間。
- **UTC 時間（UTC_Time）**：協調世界時（Coordinated Universal Time）的當前時間。

---

## 需求

### 需求 1：即時時間顯示

**使用者故事：** 身為操作人員，我希望在 Dashboard 上同時看到本地時間與 UTC 時間，以便在跨時區協作時能快速對齊時間基準。

#### 驗收標準

1. THE Dashboard SHALL 在頁面頂部同時顯示 Local_Time 與 UTC_Time。
2. WHEN 頁面載入完成，THE Dashboard SHALL 立即顯示當前的 Local_Time 與 UTC_Time。
3. THE Dashboard SHALL 以每秒一次的頻率更新 Local_Time 與 UTC_Time 的顯示值。
4. THE Dashboard SHALL 以 `YYYY-MM-DD HH:mm:ss` 格式顯示 Local_Time 與 UTC_Time。

---

### 需求 2：儀器資料時間差視覺顯示

**使用者故事：** 身為操作人員，我希望在 Dashboard 上看到每個儀器的最新資料時間差，並以顏色區分嚴重程度，以便快速判斷哪些儀器需要關注。

> **注意：** 主動推播通知（email、SMS、webhook 等）由另一個專案負責，本平台僅負責視覺化呈現。

#### 驗收標準

1. WHEN 某 Instrument 的最新資料 DiffTime 超過黃色閾值，THE Dashboard SHALL 以黃色顯示該 Instrument 的狀態區塊。
2. WHEN 某 Instrument 的最新資料 DiffTime 超過橙色閾值，THE Dashboard SHALL 以橙色顯示該 Instrument 的狀態區塊。
3. WHEN 某 Instrument 的最新資料 DiffTime 超過紅色閾值，THE Dashboard SHALL 以紅色顯示該 Instrument 的狀態區塊。
4. WHEN 某 Instrument 的最新資料 DiffTime 在黃色閾值以內，THE Dashboard SHALL 以綠色顯示正常狀態。
5. WHEN 某 Instrument 的 DiffTime 超過 14400 分鐘或無資料，THE Dashboard SHALL 顯示「斷線」。
6. THE Dashboard SHALL 為每個 Instrument 各自顯示獨立的狀態區塊，包含 IP、FileType、EquipmentName 與時間差數值。
7. THE Platform SHALL 從各 FileCheck 資料表取得每個 Instrument 的最新一筆快照，以判斷即時狀態。
8. THE Dashboard SHALL 依科別（Department）分組顯示儀器狀態。

---

### 需求 3：自動刷新機制

**使用者故事：** 身為操作人員，我希望 Dashboard 能自動定期刷新資料，以便在不手動操作的情況下持續掌握最新狀態。

#### 驗收標準

1. THE Dashboard SHALL 以 Refresh_Interval（10 秒）為週期，自動向後端重新取得最新資料並更新所有顯示元件。
2. WHEN 自動刷新觸發，THE Dashboard SHALL 在不重新載入整個頁面的情況下更新儀器狀態與電腦系統狀態。
3. THE Dashboard SHALL 顯示上一次成功刷新的時間戳記。
4. IF 自動刷新期間發生網路錯誤，THEN THE Platform SHALL 在 Dashboard 上顯示「資料更新失敗，正在重試」的提示，並於下一個 Refresh_Interval 重新嘗試。
5. THE Dashboard SHALL 提供手動刷新按鈕，WHEN 操作人員點擊手動刷新按鈕，THE Dashboard SHALL 立即執行一次資料更新並重置自動刷新計時器。

---

### 需求 4：資料庫資料存取

**使用者故事：** 身為系統，我希望能穩定地從 MySQL 資料庫取得資料，以便提供給 Dashboard 顯示。

#### 驗收標準

1. THE Platform SHALL 透過設定檔管理 Database 的連線參數（主機、埠號、資料庫名稱、帳號、密碼），不得將連線參數硬編碼於程式碼中。
2. THE Platform SHALL 維護 Database 連線池，以支援 Dashboard 的並發查詢需求。
3. THE Platform SHALL 在 5 秒內回傳查詢結果。
4. IF Database 連線中斷，THEN THE Platform SHALL 自動嘗試重新連線，重試間隔為 10 秒，最多重試 3 次。
5. IF 連續 3 次重連均失敗，THEN THE Platform SHALL 記錄錯誤日誌並在 Dashboard 顯示持續性的連線失敗警示。

---

### 需求 5：儀器時間差閾值管理

**使用者故事：** 身為操作人員，我希望能為每個儀器個別設定三段閾值，以便根據各儀器的資料特性調整警示靈敏度。

#### 驗收標準

1. THE Platform SHALL 從 FileTypeList 資料表取得所有 Instrument 清單，作為閾值設定的儀器來源。
2. THE Dashboard SHALL 提供設定介面，讓操作人員查看所有 Instrument 及其目前的黃色、橙色、紅色閾值（單位：分鐘）。
3. WHEN 操作人員修改閾值，THE Platform SHALL 儲存該設定至 thresholds.yaml 並立即套用至後續的狀態判斷。
4. THE Platform SHALL 允許操作人員為每個 Instrument 個別設定閾值，不同 Instrument 的閾值設定互相獨立。
5. IF 操作人員輸入的閾值為負數，THEN THE Platform SHALL 拒絕該輸入並顯示驗證錯誤訊息。

---

### 需求 6：電腦系統狀態顯示

**使用者故事：** 身為操作人員，我希望在 Dashboard 上看到各電腦的系統負載、記憶體與磁碟使用率，以便掌握硬體資源狀況。

#### 驗收標準

1. THE Dashboard SHALL 顯示各電腦的 CPU 負載（1 分鐘）、記憶體使用率（%）與磁碟使用率（%）。
2. THE Dashboard SHALL 依科別（Department）分組顯示電腦狀態。
3. WHEN 記憶體使用率超過 90%，THE Dashboard SHALL 以警示樣式顯示該電腦。
4. WHEN 磁碟使用率超過 85%，THE Dashboard SHALL 以警示樣式顯示該電腦。
