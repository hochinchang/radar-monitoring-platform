/**
 * computers.js — 電腦即時狀況頁面控制器
 * 系統負載/記憶體與磁碟使用率均依 Department 分組顯示。
 * 三段燈號門檻：
 *   記憶體：>60% 黃、>70% 橙、>80% 紅
 *   磁碟剩餘：<10% 黃、<5% 橙、<1% 紅（Used% 換算：>90% 黃、>95% 橙、>99% 紅）
 *   CPU 更新逾時：>3分鐘 黃、>10分鐘 橙、>30分鐘 紅
 */

const REFRESH_INTERVAL_MS = 60_000;
let _refreshTimer = null;

const DEPT_LABELS = {
  sos:  '衛星作業科',
  dqcs: '品管科',
  rsa:  '應用科',
  wrs:  '氣象雷達科',
  mrs:  '海象雷達科',
};
const DEPT_ORDER = ['wrs', 'mrs', 'sos', 'dqcs', 'rsa'];

// ── 門檻常數 ──────────────────────────────────────────────
const MEM_YELLOW = 60;   // 記憶體 >60% → 黃
const MEM_ORANGE = 70;   // 記憶體 >70% → 橙
const MEM_RED    = 80;   // 記憶體 >80% → 紅

// 磁碟「剩餘空間」門檻（API 回傳 used_pct，剩餘 = 100 - used_pct）
const DISK_FREE_YELLOW = 10;  // 剩餘 <10% → 黃
const DISK_FREE_ORANGE = 5;   // 剩餘 <5%  → 橙
const DISK_FREE_RED    = 1;   // 剩餘 <1%  → 紅

// CPU 更新逾時（分鐘）
const CPU_TIMEOUT_YELLOW = 3;   // >3 分鐘未更新 → 黃
const CPU_TIMEOUT_ORANGE = 10;  // >10 分鐘未更新 → 橙
const CPU_TIMEOUT_RED    = 30;  // >30 分鐘未更新 → 紅

// ── 工具函式 ──────────────────────────────────────────────
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

// ── 燈號判斷 ──────────────────────────────────────────────

/**
 * 記憶體使用率燈號
 * @param {number|null} memPct
 * @returns {'ok'|'yellow'|'orange'|'red'}
 */
function _memLevel(memPct) {
  if (memPct == null) return 'ok';
  if (memPct > MEM_RED)    return 'red';
  if (memPct > MEM_ORANGE) return 'orange';
  if (memPct > MEM_YELLOW) return 'yellow';
  return 'ok';
}

/**
 * 磁碟剩餘空間燈號（API 回傳 used_pct）
 * @param {number|null} usedPct
 * @returns {'ok'|'yellow'|'orange'|'red'}
 */
function _diskLevel(usedPct) {
  if (usedPct == null) return 'ok';
  const free = 100 - usedPct;
  if (free < DISK_FREE_RED)    return 'red';
  if (free < DISK_FREE_ORANGE) return 'orange';
  if (free < DISK_FREE_YELLOW) return 'yellow';
  return 'ok';
}

/**
 * CPU 更新逾時燈號
 * @param {string|null} serverTimeStr  ISO 8601 字串（後端 ServerTime）
 * @returns {'ok'|'yellow'|'orange'|'red'}
 */
function _cpuTimeoutLevel(serverTimeStr) {
  if (!serverTimeStr) return 'red'; // 無資料視為最嚴重
  const lastUpdate = new Date(serverTimeStr);
  if (isNaN(lastUpdate.getTime())) return 'red';
  const diffMin = (Date.now() - lastUpdate.getTime()) / 60000;
  if (diffMin > CPU_TIMEOUT_RED)    return 'red';
  if (diffMin > CPU_TIMEOUT_ORANGE) return 'orange';
  if (diffMin > CPU_TIMEOUT_YELLOW) return 'yellow';
  return 'ok';
}

/**
 * 取最嚴重燈號（ok < yellow < orange < red）
 */
const LEVEL_RANK = { ok: 0, yellow: 1, orange: 2, red: 3 };
function _worstLevel(...levels) {
  return levels.reduce((a, b) => LEVEL_RANK[a] >= LEVEL_RANK[b] ? a : b, 'ok');
}

// ── 燈號 badge HTML ───────────────────────────────────────
function _levelBadge(level, label) {
  if (level === 'ok') return `<span class="badge-ok">✓ 正常</span>`;
  return `<span class="badge-alert-${level}">⚠ ${label}</span>`;
}

// ── 系統負載/記憶體卡片 ───────────────────────────────────
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
      const mem     = item.memory_use != null ? item.memory_use.toFixed(1) + '%' : 'N/A';
      const load    = item.load_1     != null ? item.load_1.toFixed(2)           : 'N/A';
      const memLvl  = _memLevel(item.memory_use);
      const cpuLvl  = _cpuTimeoutLevel(item.server_time);
      const worst   = _worstLevel(memLvl, cpuLvl);

      const memBadge = memLvl !== 'ok'
        ? `<div>${_levelBadge(memLvl, `記憶體 ${mem}`)}</div>`
        : '';
      const cpuBadge = cpuLvl !== 'ok'
        ? `<div>${_levelBadge(cpuLvl, 'CPU 逾時')}</div>`
        : '';
      const okBadge  = worst === 'ok'
        ? `<span class="badge-ok">✓ 正常</span>`
        : '';

      return `
        <div class="instrument-card${worst !== 'ok' ? ' level-alert-' + worst : ' level-ok'}">
          <div class="card-title">${item.ip}</div>
          <div class="card-name">${item.equipment_name || '--'}</div>
          <div class="metric-row">
            <span class="metric-label">記憶體</span>
            <span class="metric-value diff-alert-${memLvl === 'ok' ? 'ok' : memLvl}">${mem}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">負載(1m)</span>
            <span class="metric-value">${load}</span>
          </div>
          <div class="badge-row">
            ${memBadge}${cpuBadge}${okBadge}
          </div>
        </div>`;
    }).join('');
    return `<div class="instrument-group">
      <div class="group-header">${label}</div>
      <div class="group-cards">${cards}</div>
    </div>`;
  }).join('');
}

// ── 磁碟使用率卡片 ────────────────────────────────────────
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
      const usedPct  = item.used_pct;
      const freePct  = usedPct != null ? (100 - usedPct).toFixed(1) + '%' : 'N/A';
      const usedDisp = usedPct != null ? usedPct.toFixed(1) + '%' : 'N/A';
      const lvl      = _diskLevel(usedPct);

      return `
        <div class="instrument-card${lvl !== 'ok' ? ' level-alert-' + lvl : ' level-ok'}">
          <div class="card-title">${item.ip}</div>
          <div class="card-name">${item.file_system || '--'}</div>
          <div class="metric-row">
            <span class="metric-label">已用</span>
            <span class="metric-value diff-alert-${lvl === 'ok' ? 'ok' : lvl}">${usedDisp}</span>
          </div>
          <div class="metric-row">
            <span class="metric-label">剩餘</span>
            <span class="metric-value">${freePct}</span>
          </div>
          <div class="badge-row">
            ${_levelBadge(lvl, `磁碟剩餘 ${freePct}`)}
          </div>
        </div>`;
    }).join('');
    return `<div class="instrument-group">
      <div class="group-header">${label}</div>
      <div class="group-cards">${cards}</div>
    </div>`;
  }).join('');
}

// ── 資料刷新 ──────────────────────────────────────────────
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
