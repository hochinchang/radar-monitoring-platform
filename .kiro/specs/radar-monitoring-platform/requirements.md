# 需求文件

## 簡介

雷達監控整合平台是一套網頁應用系統，部署於 Linux（Rocky 9）環境，以 MySQL 作為資料來源，提供操作人員即時監控雷達資料完整率與電腦系統狀態的能力。系統透過 Dashboard 集中呈現關鍵指標，並以自動刷新機制確保資訊即時性，同時在資料異常時主動發出警示。

---

## 詞彙表

- **平台（Platform）**：本雷達監控整合平台網頁應用系統的總稱。
- **Dashboard**：平台的主要監控畫面，集中顯示所有即時指標與圖表。
- **資料完整率（Data_Completeness_Rate）**：在指定時間區間內，實際接收到的雷達資料筆數佔預期應接收筆數的百分比。
- **缺資料警示（Missing_Data_Alert）**：當某儀器最新資料的時間差（DiffTime）超過該儀器設定的 Max_DiffTime_Threshold 時，系統產生的視覺警示訊息。
- **儀器（Instrument）**：對應 FileType，代表一種雷達資料類型或設備，每個儀器有各自獨立的 Max_DiffTime_Threshold 設定。
- **時間序列圖（Time_Series_Chart）**：以時間為 X 軸、資料完整率為 Y 軸的折線圖。
- **資料庫（Database）**：儲存雷達資料的 MySQL 資料庫。
- **刷新週期（Refresh_Interval）**：Dashboard 自動向後端重新取得最新資料的時間間隔，固定為 10 秒。
- **本地時間（Local_Time）**：伺服器或瀏覽器所在時區的當前時間。
- **UTC 時間（UTC_Time）**：協調世界時（Coordinated Universal Time）的當前時間。
- **最大時間差閾值（Max_DiffTime_Threshold）**：每個儀器允許的資料時間與現在時間的最大差距（分鐘），超過此閾值即觸發 Missing_Data_Alert。

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

### 需求 2：雷達資料完整率顯示

**使用者故事：** 身為操作人員，我希望在 Dashboard 上看到雷達資料完整率的百分比數值，以便快速掌握目前資料接收狀況。

#### 驗收標準

1. THE Dashboard SHALL 從 Database 查詢並計算 Data_Completeness_Rate，以百分比格式（例如 `98.5%`）顯示於 Dashboard 上。
2. 在yaml檔案中會記錄每個雷達每天最多的筆數，當一日已收到的資料達到或超過這個筆數時，即顯示100%，在dashboard上看到過去三天的雷達接收情況
2. WHEN 資料查詢成功，THE Dashboard SHALL 將 Data_Completeness_Rate 更新為最新計算結果。
3. IF Database 連線失敗，THEN THE Platform SHALL 在 Dashboard 上顯示「資料庫連線失敗」的錯誤提示，並保留上一次成功取得的數值。
4. IF Database 查詢回傳空結果，THEN THE Platform SHALL 在 Dashboard 上顯示「目前無資料」的提示訊息。

---

### 需求 3：缺資料警示

**使用者故事：** 身為操作人員，我希望當某儀器的最新資料時間差超過該儀器設定的最大允許時間差時能立即收到視覺警示，以便及時採取處理行動。

#### 驗收標準

1. WHEN 某 Instrument 的最新資料 DiffTime 超過該 Instrument 的 Max_DiffTime_Threshold，THE Dashboard SHALL 針對該 Instrument 顯示 Missing_Data_Alert，以醒目的視覺樣式（紅色警示區塊）呈現。
2. WHEN 某 Instrument 的最新資料 DiffTime 小於或等於該 Instrument 的 Max_DiffTime_Threshold，THE Dashboard SHALL 針對該 Instrument 隱藏 Missing_Data_Alert。
3. THE Dashboard SHALL 為每個 Instrument 各自顯示獨立的警示狀態區塊，不同 Instrument 的警示狀態互不影響。
4. THE Missing_Data_Alert SHALL 包含觸發警示的 Instrument 名稱、觸發時間戳記，以及當時的實際 DiffTime 數值（分鐘）。
5. THE Platform SHALL 從 radarFileCheck 資料表取得每個 Instrument 的最新一筆快照，以判斷即時警示狀態。
6. IF Instrument 的 Max_DiffTime_Threshold 未經設定，THEN THE Platform SHALL 使用預設值 30 分鐘作為該 Instrument 的 Max_DiffTime_Threshold。

---

### 需求 4：時間序列折線圖

**使用者故事：** 身為操作人員，我希望在 Dashboard 上看到資料完整率的時間序列折線圖，以便觀察歷史趨勢並識別異常時段。

#### 驗收標準

1. THE Dashboard SHALL 顯示一張以時間為 X 軸、Data_Completeness_Rate 為 Y 軸的 Time_Series_Chart。
2. THE Time_Series_Chart SHALL 預設顯示最近 24 小時的 Data_Completeness_Rate 歷史資料。
3. WHEN 操作人員選擇自訂時間區間，THE Time_Series_Chart SHALL 重新查詢並顯示所選區間的資料。
4. THE Time_Series_Chart 的 Y 軸 SHALL 固定顯示 0% 至 100% 的範圍。
5. WHEN 某時段的 Data_Completeness_Rate 偏低（低於 90%），THE Time_Series_Chart SHALL 以不同顏色（紅色）標示該資料點。
6. IF 所選時間區間內無資料，THEN THE Time_Series_Chart SHALL 顯示「所選區間無資料」的提示訊息。

---

### 需求 5：自動刷新機制

**使用者故事：** 身為操作人員，我希望 Dashboard 能自動定期刷新資料，以便在不手動操作的情況下持續掌握最新狀態。

#### 驗收標準

1. THE Dashboard SHALL 以 Refresh_Interval（10 秒）為週期，自動向後端重新取得最新資料並更新所有顯示元件。
2. WHEN 自動刷新觸發，THE Dashboard SHALL 在不重新載入整個頁面的情況下更新 Data_Completeness_Rate、Missing_Data_Alert 及 Time_Series_Chart。
3. THE Dashboard SHALL 顯示上一次成功刷新的時間戳記。
4. IF 自動刷新期間發生網路錯誤，THEN THE Platform SHALL 在 Dashboard 上顯示「資料更新失敗，正在重試」的提示，並於下一個 Refresh_Interval 重新嘗試。
5. THE Dashboard SHALL 提供手動刷新按鈕，WHEN 操作人員點擊手動刷新按鈕，THE Dashboard SHALL 立即執行一次資料更新並重置自動刷新計時器。

---

### 需求 6：資料庫資料存取

**使用者故事：** 身為系統，我希望能穩定地從 MySQL 資料庫取得雷達資料，以便計算資料完整率並提供給 Dashboard 顯示。

#### 驗收標準

1. THE Platform SHALL 透過設定檔管理 Database 的連線參數（主機、埠號、資料庫名稱、帳號、密碼），不得將連線參數硬編碼於程式碼中。
2. THE Platform SHALL 維護 Database 連線池，以支援 Dashboard 的並發查詢需求。
3. WHEN 查詢 Data_Completeness_Rate，THE Platform SHALL 在 5 秒內回傳查詢結果。
4. IF Database 連線中斷，THEN THE Platform SHALL 自動嘗試重新連線，重試間隔為 10 秒，最多重試 3 次。
5. IF 連續 3 次重連均失敗，THEN THE Platform SHALL 記錄錯誤日誌並在 Dashboard 顯示持續性的連線失敗警示。

---

### 需求 7：儀器時間差閾值管理

**使用者故事：** 身為操作人員，我希望能為每個儀器個別設定最大允許時間差閾值，以便根據各儀器的資料特性調整警示靈敏度。

#### 驗收標準

1. THE Platform SHALL 從 FileTypeList 資料表取得所有 Instrument 清單，作為閾值設定的儀器來源。
2. THE Dashboard SHALL 提供設定介面，讓操作人員查看所有 Instrument 及其目前的 Max_DiffTime_Threshold 設定值（單位：分鐘）。
3. WHEN 操作人員為某 Instrument 輸入新的 Max_DiffTime_Threshold，THE Platform SHALL 儲存該設定並立即套用至後續的警示判斷。
4. THE Platform SHALL 允許操作人員為每個 Instrument 個別設定 Max_DiffTime_Threshold，不同 Instrument 的閾值設定互相獨立。
5. IF 操作人員輸入的 Max_DiffTime_Threshold 為負數，THEN THE Platform SHALL 拒絕該輸入並顯示驗證錯誤訊息。
