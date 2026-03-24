/**
 * api.js — 統一封裝所有對後端的 fetch 呼叫與錯誤處理
 * 其他模組不直接發出 HTTP 請求，一律透過此模組。
 */

const API_BASE = '/api/v1';
const TIMEOUT_MS = 8000;

/**
 * 帶逾時的 fetch wrapper。
 * @returns {Promise<any>} 解析後的 JSON，或拋出含 type 的 Error
 */
async function apiFetch(path, options = {}) {
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), TIMEOUT_MS);

  try {
    const res = await fetch(API_BASE + path, {
      ...options,
      signal: controller.signal,
    });
    clearTimeout(timer);

    if (!res.ok) {
      const err = new Error(`HTTP ${res.status}`);
      err.status = res.status;
      err.type = res.status >= 500 ? 'db_error' : 'client_error';
      try { err.detail = await res.json(); } catch (_) {}
      throw err;
    }

    return await res.json();
  } catch (e) {
    clearTimeout(timer);
    if (e.name === 'AbortError') {
      const err = new Error('請求逾時');
      err.type = 'timeout';
      throw err;
    }
    if (!e.type) e.type = 'network_error';
    throw e;
  }
}

/** 取得所有儀器即時警示狀態 */
async function fetchCurrentStatus() {
  return apiFetch('/completeness/current');
}

/**
 * 取得時間序列資料
 * @param {Date} start
 * @param {Date} end
 */
async function fetchTimeSeries(start, end) {
  const s = start.toISOString();
  const e = end.toISOString();
  return apiFetch(`/completeness/timeseries?start=${encodeURIComponent(s)}&end=${encodeURIComponent(e)}`);
}

/** 取得所有儀器清單與閾值 */
async function fetchInstruments() {
  return apiFetch('/instruments');
}

/**
 * 更新儀器閾值
 * @param {string} fileType
 * @param {number} threshold
 */
async function updateThreshold(fileType, threshold) {
  return apiFetch(`/instruments/${encodeURIComponent(fileType)}/threshold`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ max_diff_time_threshold: threshold }),
  });
}
