/**
 * dashboard.js — 儀器即時狀況頁面控制器
 * 依 Department 分組顯示儀器警示狀態，無趨勢圖。
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

const DISCONNECT_THRESHOLD_MIN = 14400;
const ALERT_RED    = 20;
const ALERT_ORANGE = 15;
const ALERT_YELLOW = 10;

function _alertClass(diff) {
  if (diff == null || diff > DISCONNECT_THRESHOLD_MIN) return 'disconnected';
  if (diff > ALERT_RED)    return 'alert-red';
  if (diff > ALERT_ORANGE) return 'alert-orange';
  if (diff > ALERT_YELLOW) return 'alert-yellow';
  return 'ok';
}

function _makeCard(inst) {
  const diff = inst.diff_time_minutes;
  const level = _alertClass(diff);
  const isDisconnected = level === 'disconnected';
  const isAlert = level !== 'ok' && !isDisconnected;

  let diffDisplay, statusBadge;
  if (isDisconnected) {
    diffDisplay = '<span class="diff-disconnected">斷線</span>';
    statusBadge = '<span class="badge-disconnected">⚠ 斷線</span>';
  } else {
    const diffText = diff != null ? diff.toFixed(1) + ' 分鐘' : 'N/A';
    diffDisplay = `<span class="diff-time diff-${level}">${diffText}</span>`;
    if (isAlert) {
      statusBadge = `<span class="badge-${level}">⚠ 缺資料警示</span>`;
    } else {
      statusBadge = '<span class="ok-label">✓ 正常</span>';
    }
  }

  const triggeredAt = (!isDisconnected && isAlert && inst.latest_file_time)
    ? `<div class="triggered-at">最新資料：${new Date(inst.latest_file_time).toLocaleString('zh-TW')}</div>`
    : '';

  return `
    <div class="instrument-card level-${level}">
      <div class="card-meta">${inst.ip || '--'}</div>
      <div class="card-title">${inst.file_type}</div>
      <div class="card-name">${inst.equipment_name || '--'}</div>
      <div style="margin:6px 0">${diffDisplay}</div>
      ${statusBadge}
      ${triggeredAt}
    </div>`;
}

function _renderInstruments(instruments) {
  const container = document.getElementById('instruments-container');
  if (!instruments || instruments.length === 0) {
    container.innerHTML = '<p class="loading">目前無儀器資料</p>';
    return;
  }

  // 依 department 分組
  const groups = {};
  for (const inst of instruments) {
    const key = (inst.department || '').toLowerCase() || 'other';
    if (!groups[key]) groups[key] = [];
    groups[key].push(inst);
  }

  const orderedKeys = [
    ...DEPT_ORDER.filter(k => groups[k]),
    ...Object.keys(groups).filter(k => !DEPT_ORDER.includes(k)),
  ];

  container.innerHTML = orderedKeys.map(key => {
    const label = DEPT_LABELS[key] || key;
    const cards = groups[key].map(_makeCard).join('');
    return `
      <div class="instrument-group">
        <div class="group-header">${label}</div>
        <div class="group-cards">${cards}</div>
      </div>`;
  }).join('');
}

async function _refreshData() {
  try {
    const data = await fetchCurrentStatus();
    _renderInstruments(data.instruments);
    _clearStatus();
  } catch (e) {
    _showStatus(
      e.type === 'db_error' ? '資料庫連線失敗，顯示上次資料' : '資料更新失敗，正在重試…',
      e.type === 'db_error' ? 'error' : 'warning'
    );
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
