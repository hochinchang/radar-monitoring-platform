/**
 * dashboard.js — 主控制器
 * 負責時間顯示、自動刷新、儀器狀態渲染、閾值設定表格。
 * 協調 api.js 與 chart.js，不直接發出 HTTP 請求。
 */

const REFRESH_INTERVAL_MS = 10_000;

let _refreshTimer = null;

// ── 時間顯示 ────────────────────────────────────────────────

function _pad(n) { return String(n).padStart(2, '0'); }

function _formatDatetime(d) {
  return `${d.getFullYear()}-${_pad(d.getMonth()+1)}-${_pad(d.getDate())} ` +
         `${_pad(d.getHours())}:${_pad(d.getMinutes())}:${_pad(d.getSeconds())}`;
}

function _tickClock() {
  const now = new Date();
  const utc = new Date(now.getTime() + now.getTimezoneOffset() * 60000);
  document.getElementById('local-time').textContent = _formatDatetime(now);
  document.getElementById('utc-time').textContent   = _formatDatetime(utc);
}

// ── 狀態列 ──────────────────────────────────────────────────

function _showStatus(msg, type = 'error') {
  const bar = document.getElementById('status-bar');
  bar.textContent = msg;
  bar.className = `status-bar ${type}`;
}

function _clearStatus() {
  const bar = document.getElementById('status-bar');
  bar.className = 'status-bar hidden';
}

// ── 儀器卡片 ────────────────────────────────────────────────

function _renderInstruments(instruments) {
  const grid = document.getElementById('instruments-grid');
  if (!instruments || instruments.length === 0) {
    grid.innerHTML = '<p class="loading">目前無儀器資料</p>';
    return;
  }

  grid.innerHTML = instruments.map(inst => {
    const isAlert = inst.is_alert;
    const diff = inst.diff_time_minutes != null
      ? inst.diff_time_minutes.toFixed(1) + ' 分鐘'
      : 'N/A';
    const triggeredAt = inst.latest_file_time
      ? new Date(inst.latest_file_time).toLocaleString('zh-TW')
      : '--';

    return `
      <div class="instrument-card ${isAlert ? 'alert' : ''}">
        <div class="card-title">${inst.file_type}</div>
        <div class="card-name">${inst.equipment_name || inst.file_type}</div>
        <div class="diff-time">${diff}</div>
        ${isAlert
          ? `<span class="alert-label">⚠ 缺資料警示</span>
             <div class="triggered-at">最新資料：${triggeredAt}</div>`
          : `<span class="ok-label">✓ 正常</span>`
        }
      </div>`;
  }).join('');
}

// ── 閾值設定表格 ─────────────────────────────────────────────

function _renderThresholdTable(instruments) {
  const tbody = document.getElementById('threshold-tbody');
  if (!instruments || instruments.length === 0) {
    tbody.innerHTML = '<tr><td colspan="4" style="color:#64748b">無儀器資料</td></tr>';
    return;
  }

  tbody.innerHTML = instruments.map(inst => `
    <tr data-file-type="${inst.file_type}">
      <td>${inst.file_type}</td>
      <td>${inst.equipment_name || '--'}</td>
      <td>
        <input type="number" min="0" step="1"
               value="${inst.max_diff_time_threshold}"
               data-original="${inst.max_diff_time_threshold}" />
      </td>
      <td>
        <button class="btn-save" onclick="saveThreshold('${inst.file_type}', this)">儲存</button>
        <span class="save-msg"></span>
      </td>
    </tr>
  `).join('');
}

async function saveThreshold(fileType, btn) {
  const row = btn.closest('tr');
  const input = row.querySelector('input[type="number"]');
  const msgEl = row.querySelector('.save-msg');
  const val = parseFloat(input.value);

  input.classList.remove('input-error');
  msgEl.textContent = '';

  if (isNaN(val) || val < 0) {
    input.classList.add('input-error');
    msgEl.textContent = '閾值不得為負數';
    msgEl.className = 'save-msg err';
    return;
  }

  btn.disabled = true;
  try {
    await updateThreshold(fileType, val);
    input.dataset.original = val;
    msgEl.textContent = '已儲存';
    msgEl.className = 'save-msg ok';
    setTimeout(() => { msgEl.textContent = ''; }, 2000);
  } catch (e) {
    msgEl.textContent = e.status === 404 ? '找不到儀器' : '儲存失敗';
    msgEl.className = 'save-msg err';
  } finally {
    btn.disabled = false;
  }
}

// ── 資料刷新 ─────────────────────────────────────────────────

async function _refreshData() {
  // 1. 儀器即時狀態
  try {
    const data = await fetchCurrentStatus();
    _renderInstruments(data.instruments);
    _clearStatus();
  } catch (e) {
    if (e.type === 'db_error') {
      _showStatus('資料庫連線失敗，顯示上次資料', 'error');
    } else {
      _showStatus('資料更新失敗，正在重試…', 'warning');
    }
  }

  // 2. 時間序列圖
  const { start, end } = _getChartRange();
  try {
    const ts = await fetchTimeSeries(start, end);
    updateChart(ts.data);
  } catch (_) {
    // 圖表錯誤不覆蓋主狀態列，靜默保留舊圖
  }

  // 3. 更新刷新時間戳
  document.getElementById('last-refreshed').textContent =
    _formatDatetime(new Date());
}

function _getChartRange() {
  const startInput = document.getElementById('input-start').value;
  const endInput   = document.getElementById('input-end').value;
  const end   = endInput   ? new Date(endInput)   : new Date();
  const start = startInput ? new Date(startInput) : new Date(end.getTime() - 24 * 3600 * 1000);
  return { start, end };
}

function _resetRefreshTimer() {
  clearInterval(_refreshTimer);
  _refreshTimer = setInterval(_refreshData, REFRESH_INTERVAL_MS);
}

// ── 初始化 ───────────────────────────────────────────────────

async function _init() {
  // 時鐘
  _tickClock();
  setInterval(_tickClock, 1000);

  // 預設時間區間（最近 24 小時）
  const now = new Date();
  const yesterday = new Date(now.getTime() - 24 * 3600 * 1000);
  const toLocal = d => new Date(d.getTime() - d.getTimezoneOffset() * 60000)
    .toISOString().slice(0, 16);
  document.getElementById('input-start').value = toLocal(yesterday);
  document.getElementById('input-end').value   = toLocal(now);

  // 手動刷新按鈕
  document.getElementById('btn-refresh').addEventListener('click', () => {
    _refreshData();
    _resetRefreshTimer();
  });

  // 查詢按鈕
  document.getElementById('btn-query').addEventListener('click', async () => {
    const { start, end } = _getChartRange();
    if (start >= end) {
      _showStatus('起始時間必須早於結束時間', 'warning');
      return;
    }
    try {
      const ts = await fetchTimeSeries(start, end);
      updateChart(ts.data);
      _clearStatus();
    } catch (_) {
      _showStatus('查詢失敗，請稍後再試', 'error');
    }
  });

  // 載入閾值表格（只需載入一次）
  try {
    const data = await fetchInstruments();
    _renderThresholdTable(data.instruments);
  } catch (_) {
    document.getElementById('threshold-tbody').innerHTML =
      '<tr><td colspan="4" style="color:#f87171">載入失敗</td></tr>';
  }

  // 首次刷新 + 啟動自動刷新
  await _refreshData();
  _resetRefreshTimer();
}

document.addEventListener('DOMContentLoaded', _init);
