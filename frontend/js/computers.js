/**
 * computers.js — 電腦即時狀況頁面控制器
 */

const REFRESH_INTERVAL_MS = 10_000;
let _refreshTimer = null;

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

function _showStatus(msg, type = 'error') {
  const bar = document.getElementById('status-bar');
  bar.textContent = msg;
  bar.className = `status-bar ${type}`;
}
function _clearStatus() {
  document.getElementById('status-bar').className = 'status-bar hidden';
}

function _renderSystemGrid(items) {
  const grid = document.getElementById('system-grid');
  if (!items || items.length === 0) {
    grid.innerHTML = '<p class="loading">目前無系統資料</p>';
    return;
  }
  grid.innerHTML = items.map(item => {
    const memPct = item.memory_use != null ? item.memory_use.toFixed(1) + '%' : 'N/A';
    const load   = item.load_1    != null ? item.load_1.toFixed(2)        : 'N/A';
    const isAlert = item.memory_use != null && item.memory_use > 90;
    return `
      <div class="instrument-card ${isAlert ? 'alert' : ''}">
        <div class="card-title">${item.ip}</div>
        <div class="card-name">${item.equipment_name || item.ip}</div>
        <div class="diff-time">${memPct}</div>
        <div style="font-size:0.78rem;color:#94a3b8;margin-top:4px">記憶體使用率</div>
        <div style="font-size:0.82rem;margin-top:6px">負載(1m)：${load}</div>
        ${isAlert ? '<span class="alert-label">⚠ 記憶體過高</span>' : '<span class="ok-label">✓ 正常</span>'}
      </div>`;
  }).join('');
}

function _renderDiskGrid(items) {
  const grid = document.getElementById('disk-grid');
  if (!items || items.length === 0) {
    grid.innerHTML = '<p class="loading">目前無磁碟資料</p>';
    return;
  }
  grid.innerHTML = items.map(item => {
    const used    = item.used != null ? item.used.toFixed(1) + ' GB' : 'N/A';
    const isAlert = item.used != null && item.used_pct != null && item.used_pct > 85;
    return `
      <div class="instrument-card ${isAlert ? 'alert' : ''}">
        <div class="card-title">${item.ip}</div>
        <div class="card-name">${item.file_system || '--'}</div>
        <div class="diff-time">${used}</div>
        <div style="font-size:0.78rem;color:#94a3b8;margin-top:4px">已使用</div>
        ${isAlert ? '<span class="alert-label">⚠ 磁碟空間不足</span>' : '<span class="ok-label">✓ 正常</span>'}
      </div>`;
  }).join('');
}

async function _refreshData() {
  try {
    const [sysData, diskData] = await Promise.all([
      fetchSystemStatus(),
      fetchDiskStatus(),
    ]);
    _renderSystemGrid(sysData.items);
    _renderDiskGrid(diskData.items);
    _clearStatus();
  } catch (e) {
    _showStatus('資料更新失敗，正在重試…', 'warning');
  }
  document.getElementById('last-refreshed').textContent = _formatDatetime(new Date());
}

function _resetRefreshTimer() {
  clearInterval(_refreshTimer);
  _refreshTimer = setInterval(_refreshData, REFRESH_INTERVAL_MS);
}

async function _init() {
  _tickClock();
  setInterval(_tickClock, 1000);

  document.getElementById('btn-refresh').addEventListener('click', () => {
    _refreshData();
    _resetRefreshTimer();
  });

  await _refreshData();
  _resetRefreshTimer();
}

document.addEventListener('DOMContentLoaded', _init);
