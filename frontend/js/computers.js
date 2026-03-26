/**
 * computers.js — 電腦即時狀況頁面控制器
 * 系統負載/記憶體與磁碟使用率均依 Department 分組顯示。
 */

const REFRESH_INTERVAL_MS = 10_000;
let _refreshTimer = null;

const DEPT_LABELS = {
  sos:  '衛星作業科',
  dqcs: '品管科',
  rsa:  '應用科',
  wrs:  '氣象雷達科',
  mrs:  '海象雷達科',
};
const DEPT_ORDER = ['wrs', 'mrs', 'sos', 'dqcs', 'rsa'];

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

function _groupByDept(items) {
  const groups = {};
  for (const item of items) {
    const key = (item.department || '').toLowerCase() || 'other';
    if (!groups[key]) groups[key] = [];
    groups[key].push(item);
  }
  return groups;
}

function _orderedKeys(groups) {
  return [
    ...DEPT_ORDER.filter(k => groups[k]),
    ...Object.keys(groups).filter(k => !DEPT_ORDER.includes(k)),
  ];
}

function _renderSystemGrid(items) {
  const container = document.getElementById('system-container');
  if (!items || items.length === 0) {
    container.innerHTML = '<p class="loading">目前無系統資料</p>';
    return;
  }
  const groups = _groupByDept(items);
  container.innerHTML = _orderedKeys(groups).map(key => {
    const label = DEPT_LABELS[key] || key;
    const cards = groups[key].map(item => {
      const mem  = item.memory_use != null ? item.memory_use.toFixed(1) + '%' : 'N/A';
      const load = item.load_1     != null ? item.load_1.toFixed(2)           : 'N/A';
      const isAlert = item.memory_use != null && item.memory_use > 90;
      return `
        <div class="instrument-card ${isAlert ? 'alert' : ''}">
          <div class="card-title">${item.ip}</div>
          <div class="card-name">${item.equipment_name}</div>
          <div class="diff-time">${mem}</div>
          <div style="font-size:0.78rem;color:#94a3b8;margin-top:2px">記憶體使用率</div>
          <div style="font-size:0.82rem;margin-top:6px">負載(1m)：${load}</div>
          ${isAlert ? '<span class="alert-label">⚠ 記憶體過高</span>' : '<span class="ok-label">✓ 正常</span>'}
        </div>`;
    }).join('');
    return `<div class="instrument-group">
      <div class="group-header">${label}</div>
      <div class="group-cards">${cards}</div>
    </div>`;
  }).join('');
}

function _renderDiskGrid(items) {
  const container = document.getElementById('disk-container');
  if (!items || items.length === 0) {
    container.innerHTML = '<p class="loading">目前無磁碟資料</p>';
    return;
  }
  const groups = _groupByDept(items);
  container.innerHTML = _orderedKeys(groups).map(key => {
    const label = DEPT_LABELS[key] || key;
    const cards = groups[key].map(item => {
      const pct = item.used_pct != null ? item.used_pct.toFixed(1) + '%' : 'N/A';
      const isAlert = item.used_pct != null && item.used_pct > 85;
      return `
        <div class="instrument-card ${isAlert ? 'alert' : ''}">
          <div class="card-title">${item.ip}</div>
          <div class="card-name">${item.file_system || '--'}</div>
          <div class="diff-time">${pct}</div>
          <div style="font-size:0.78rem;color:#94a3b8;margin-top:2px">磁碟使用率</div>
          ${isAlert ? '<span class="alert-label">⚠ 磁碟空間不足</span>' : '<span class="ok-label">✓ 正常</span>'}
        </div>`;
    }).join('');
    return `<div class="instrument-group">
      <div class="group-header">${label}</div>
      <div class="group-cards">${cards}</div>
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
