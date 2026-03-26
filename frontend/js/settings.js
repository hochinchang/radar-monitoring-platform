/**
 * settings.js — 儀器閾值設定頁面控制器
 */

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

async function _init() {
  _tickClock();
  setInterval(_tickClock, 1000);
  try {
    const data = await fetchInstruments();
    _renderThresholdTable(data.instruments);
  } catch (_) {
    document.getElementById('threshold-tbody').innerHTML =
      '<tr><td colspan="4" style="color:#f87171">載入失敗</td></tr>';
  }
}

document.addEventListener('DOMContentLoaded', _init);
