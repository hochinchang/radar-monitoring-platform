/**
 * chart.js — 負責 Chart.js 時間序列折線圖的建立與更新
 * 不處理資料取得，只負責繪圖邏輯。
 */

let _chart = null;

const ALERT_COLOR  = 'rgba(239, 68, 68, 0.9)';   // 紅色 — 低完整率點
const NORMAL_COLOR = 'rgba(56, 189, 248, 0.9)';   // 藍色 — 正常點
const LINE_COLOR   = 'rgba(56, 189, 248, 0.6)';
const ALERT_THRESHOLD = 90;

/**
 * 初始化或取得 Chart 實例。
 * @returns {Chart}
 */
function _getChart() {
  if (_chart) return _chart;

  const ctx = document.getElementById('completeness-chart').getContext('2d');
  _chart = new Chart(ctx, {
    type: 'line',
    data: { labels: [], datasets: [_makeDataset([])] },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          type: 'category',
          ticks: { color: '#94a3b8', maxTicksLimit: 12, maxRotation: 30 },
          grid: { color: '#1e2235' },
        },
        y: {
          min: 0,
          max: 100,
          ticks: {
            color: '#94a3b8',
            callback: v => v + '%',
          },
          grid: { color: '#1e2235' },
        },
      },
      plugins: {
        legend: { display: false },
        tooltip: {
          callbacks: {
            label: ctx => ` ${ctx.parsed.y.toFixed(1)}%`,
          },
        },
      },
    },
  });
  return _chart;
}

function _makeDataset(points) {
  return {
    label: '資料完整率',
    data: points.map(p => p.rate),
    borderColor: LINE_COLOR,
    borderWidth: 2,
    pointBackgroundColor: points.map(p =>
      p.rate < ALERT_THRESHOLD ? ALERT_COLOR : NORMAL_COLOR
    ),
    pointRadius: points.map(p => p.rate < ALERT_THRESHOLD ? 5 : 3),
    tension: 0.3,
    fill: false,
  };
}

/**
 * 以新資料更新圖表。
 * @param {{ timestamp: string, completeness_rate: number }[]} dataPoints
 */
function updateChart(dataPoints) {
  const noDataEl = document.getElementById('chart-no-data');

  if (!dataPoints || dataPoints.length === 0) {
    noDataEl.classList.remove('hidden');
    if (_chart) {
      _chart.data.labels = [];
      _chart.data.datasets[0].data = [];
      _chart.update();
    }
    return;
  }

  noDataEl.classList.add('hidden');

  const points = dataPoints.map(p => ({
    label: _formatLabel(p.timestamp),
    rate: p.completeness_rate,
  }));

  const chart = _getChart();
  chart.data.labels = points.map(p => p.label);
  chart.data.datasets[0] = _makeDataset(points);
  chart.update();
}

/** 格式化時間戳為 HH:mm 或 MM-DD HH:mm */
function _formatLabel(isoStr) {
  const d = new Date(isoStr);
  const mm = String(d.getMonth() + 1).padStart(2, '0');
  const dd = String(d.getDate()).padStart(2, '0');
  const hh = String(d.getHours()).padStart(2, '0');
  const mi = String(d.getMinutes()).padStart(2, '0');
  return `${mm}-${dd} ${hh}:${mi}`;
}
