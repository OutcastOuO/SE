/* ══════════════════════════════════════════════════════════════
   VMS 車輛管理系統 — 前端核心邏輯
   SPA 架構：Login → Main Dashboard → Settings
   ══════════════════════════════════════════════════════════════ */

const API = '';  // same origin

// ── Application State ────────────────────────────────────────
const state = {
  currentUser: null,       // { login_account, display_name, role }
  currentView: 'login',    // 'login' | 'main' | 'settings'
  selectedPlates: new Set(),
  vehicles: [],
  destinations: [],
  loadingLevels: [],
  refreshTimer: null,
  countdownTimer: null,
};

// ══════════════════════════════════════════════════════════════
//   API Helpers
// ══════════════════════════════════════════════════════════════
async function api(method, path, body = null) {
  const opts = {
    method,
    headers: { 'Content-Type': 'application/json' },
  };
  if (body) opts.body = JSON.stringify(body);

  const res = await fetch(`${API}${path}`, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || 'API error');
  }
  if (res.status === 204) return null;
  return res.json();
}

// ══════════════════════════════════════════════════════════════
//   Toast Notifications
// ══════════════════════════════════════════════════════════════
function showToast(message, type = 'info') {
  let container = document.querySelector('.toast-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'toast-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(40px)';
    toast.style.transition = 'all 0.3s ease';
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ══════════════════════════════════════════════════════════════
//   Modal System
// ══════════════════════════════════════════════════════════════
function showModal(title, contentHTML, actions) {
  closeModal();
  const overlay = document.createElement('div');
  overlay.className = 'modal-overlay';
  overlay.id = 'vms-modal';

  const box = document.createElement('div');
  box.className = 'modal-box';
  box.innerHTML = `<h2>${title}</h2>${contentHTML}`;

  if (actions) {
    const actDiv = document.createElement('div');
    actDiv.className = 'modal-actions';
    actions.forEach(a => {
      const btn = document.createElement('button');
      btn.className = `btn ${a.cls || 'btn-secondary'}`;
      btn.textContent = a.text;
      btn.onclick = () => { a.onClick(box); };
      actDiv.appendChild(btn);
    });
    box.appendChild(actDiv);
  }

  overlay.appendChild(box);
  overlay.addEventListener('click', e => { if (e.target === overlay) closeModal(); });
  document.body.appendChild(overlay);
  return box;
}

function closeModal() {
  const m = document.getElementById('vms-modal');
  if (m) m.remove();
}

// ══════════════════════════════════════════════════════════════
//   Timer Helpers
// ══════════════════════════════════════════════════════════════
function getRemainingText(etaTime) {
  if (!etaTime) return { text: '', overdue: false };
  try {
    const eta = new Date(etaTime.replace(/-/g, '/'));
    const now = new Date();
    const diffMs = eta - now;
    const totalSec = Math.floor(diffMs / 1000);

    if (totalSec < 0) {
      const overSec = Math.abs(totalSec);
      const h = Math.floor(overSec / 3600);
      const m = Math.floor((overSec % 3600) / 60);
      return { text: `超時 ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`, overdue: true };
    }
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    return { text: `剩餘 ${String(h).padStart(2,'0')}:${String(m).padStart(2,'0')}`, overdue: false };
  } catch {
    return { text: '', overdue: false };
  }
}

function formatEtaTime(etaTime) {
  if (!etaTime) return '';
  try {
    const d = new Date(etaTime.replace(/-/g, '/'));
    return `${String(d.getMonth()+1).padStart(2,'0')}/${String(d.getDate()).padStart(2,'0')} ${String(d.getHours()).padStart(2,'0')}:${String(d.getMinutes()).padStart(2,'0')}`;
  } catch {
    return '';
  }
}

// ══════════════════════════════════════════════════════════════
//   LOGIN VIEW
// ══════════════════════════════════════════════════════════════
function renderLogin() {
  state.currentView = 'login';
  stopTimers();
  document.getElementById('app').innerHTML = `
    <div class="login-wrapper">
      <div class="login-box">
        <h1>車輛管理系統 VMS</h1>
        <p class="subtitle">Vehicle Management System</p>
        <div class="form-group">
          <label>帳號</label>
          <input type="text" id="login-account" placeholder="請輸入帳號" />
        </div>
        <div class="form-group">
          <label>密碼</label>
          <input type="password" id="login-password" placeholder="請輸入密碼" />
        </div>
        <button class="btn btn-primary btn-full" id="login-btn">登入</button>
        <div class="login-error" id="login-error"></div>
        <p class="hint">初始管理員：admin / 1234<br>首次登入後請到設定頁面修改密碼。</p>
      </div>
    </div>
  `;

  document.getElementById('login-btn').onclick = doLogin;
  document.getElementById('login-password').addEventListener('keydown', e => {
    if (e.key === 'Enter') doLogin();
  });
  document.getElementById('login-account').addEventListener('keydown', e => {
    if (e.key === 'Enter') document.getElementById('login-password').focus();
  });
}

async function doLogin() {
  const account = document.getElementById('login-account').value.trim();
  const password = document.getElementById('login-password').value.trim();
  const errEl = document.getElementById('login-error');

  try {
    const user = await api('POST', '/api/login', { login_account: account, password });
    state.currentUser = user;
    renderMain();
  } catch (e) {
    errEl.textContent = e.message;
  }
}

// ══════════════════════════════════════════════════════════════
//   MAIN DASHBOARD VIEW
// ══════════════════════════════════════════════════════════════
async function renderMain() {
  state.currentView = 'main';
  stopTimers();

  try {
    state.vehicles = await api('GET', '/api/vehicles');
  } catch (e) {
    showToast('載入車輛資料失敗: ' + e.message, 'error');
    return;
  }

  const u = state.currentUser;
  const canEdit = u && (u.role === 'admin' || u.role === 'editor');
  const roleCls = u ? `badge-${u.role}` : '';

  const appEl = document.getElementById('app');
  appEl.innerHTML = '';

  // Top bar
  const topBar = document.createElement('div');
  topBar.className = 'top-bar';
  topBar.innerHTML = `
    <h1>車輛管理系統 VMS</h1>
    <div class="top-bar-info">
      <span class="user-badge ${roleCls}">${u ? `${u.display_name} / ${u.role}` : '未登入'}</span>
      <span class="selection-count" id="sel-count">已選取: ${state.selectedPlates.size} 台</span>
    </div>
    <div class="top-bar-actions">
      ${canEdit ? '<button class="btn btn-secondary btn-sm" id="btn-settings">⚙ 設定頁面</button>' : ''}
      <button class="btn btn-secondary btn-sm" id="btn-clear-sel">清除選取</button>
      <button class="btn btn-secondary btn-sm" id="btn-refresh">↻ 重新整理</button>
      <button class="btn btn-secondary btn-sm" id="btn-export">📊 匯出出差紀錄</button>
      <button class="btn btn-secondary btn-sm" id="btn-logout">登出</button>
    </div>
  `;
  appEl.appendChild(topBar);

  if (document.getElementById('btn-settings'))
    document.getElementById('btn-settings').onclick = () => renderSettings();
  document.getElementById('btn-clear-sel').onclick = () => { state.selectedPlates.clear(); renderMain(); };
  document.getElementById('btn-refresh').onclick = () => renderMain();
  document.getElementById('btn-export').onclick = () => showExportDialog();
  document.getElementById('btn-logout').onclick = () => { state.currentUser = null; state.selectedPlates.clear(); renderLogin(); };

  // Material areas
  for (const type of ['A', 'B']) {
    const area = buildMaterialArea(type, canEdit);
    appEl.appendChild(area);
  }

  // Start timers
  startCountdownTimer();
  state.refreshTimer = setInterval(() => renderMain(), 30000);
}

function buildMaterialArea(materialType, canEdit) {
  const vehicles = state.vehicles.filter(v => v.material_type === materialType);

  const area = document.createElement('div');
  area.className = 'material-area';

  const title = document.createElement('div');
  title.className = 'material-title';
  title.setAttribute('data-type', materialType);
  title.textContent = `${materialType} 料件區`;
  area.appendChild(title);

  const cols = document.createElement('div');
  cols.className = 'status-columns';

  const statuses = [
    ['standby_empty', 'Standby 空車'],
    ['standby_full', 'Standby 滿料'],
    ['loading', 'Processing 裝料'],
    ['out', 'Processing 出差中'],
    ['repair', '修車'],
  ];

  for (const [statusKey, statusName] of statuses) {
    const col = buildStatusColumn(statusKey, statusName, vehicles, canEdit);
    cols.appendChild(col);
  }

  area.appendChild(cols);
  return area;
}

function buildStatusColumn(statusKey, statusName, allVehicles, canEdit) {
  const vehicles = allVehicles.filter(v => v.status === statusKey);

  // Sort: overdue first, then by eta_time
  vehicles.sort((a, b) => {
    const aOver = getRemainingText(a.eta_time).overdue ? 0 : 1;
    const bOver = getRemainingText(b.eta_time).overdue ? 0 : 1;
    if (aOver !== bOver) return aOver - bOver;
    return (a.eta_time || '9999').localeCompare(b.eta_time || '9999');
  });

  const col = document.createElement('div');
  col.className = 'status-column';
  col.setAttribute('data-status', statusKey);

  col.innerHTML = `
    <div class="column-header">
      <span class="column-title">${statusName}</span>
      <span class="column-count">${vehicles.length}</span>
    </div>
    <div class="column-divider"></div>
  `;

  const isStandby = statusKey === 'standby_empty' || statusKey === 'standby_full';
  const list = document.createElement('div');
  list.className = `vehicle-list${isStandby ? ' standby-grid' : ''}`;

  for (const v of vehicles) {
    const card = buildVehicleCard(v, isStandby);
    list.appendChild(card);
  }

  col.appendChild(list);

  // Drag & Drop target
  if (canEdit) {
    col.addEventListener('dragover', e => {
      e.preventDefault();
      e.dataTransfer.dropEffect = 'move';
      col.classList.add('drag-over');
    });
    col.addEventListener('dragleave', () => col.classList.remove('drag-over'));
    col.addEventListener('drop', e => {
      e.preventDefault();
      col.classList.remove('drag-over');
      handleDrop(statusKey, e.dataTransfer.getData('text/plain'));
    });
  }

  return col;
}

function buildVehicleCard(v, isStandby) {
  const card = document.createElement('div');
  const { text: remaining, overdue } = getRemainingText(v.eta_time);
  const etaDisplay = formatEtaTime(v.eta_time);

  const isSelected = state.selectedPlates.has(v.plate_no);

  let extraClass = '';
  if (isStandby) extraClass = 'card-standby';
  else extraClass = 'card-wide';
  if (isSelected) extraClass += ' selected';
  if (v.status === 'loading' && overdue) extraClass += ' loading-done';
  if (v.status === 'out' && overdue) extraClass += ' out-overdue';

  card.className = `vehicle-card ${extraClass}`;
  card.draggable = true;
  card.setAttribute('data-plate', v.plate_no);
  card.setAttribute('data-eta', v.eta_time || '');

  if (isStandby) {
    card.innerHTML = `<span class="plate-no">${v.plate_no}</span>`;
  } else {
    let infoHtml = '';
    if (v.status === 'loading') {
      if (v.loading_level) infoHtml += `<span class="card-info">裝料：${v.loading_level}</span>`;
      if (remaining) {
        const displayText = overdue ? remaining.replace('超時', '完成') : remaining;
        infoHtml += `<span class="card-timer">${displayText}</span>`;
      }
    } else if (v.status === 'out') {
      if (v.destination) infoHtml += `<span class="card-info">目的地：${v.destination}</span>`;
      if (remaining) infoHtml += `<span class="card-timer">${remaining}</span>`;
      if (etaDisplay) infoHtml += `<span class="card-eta">預計抵達：${etaDisplay}</span>`;
    } else if (v.status === 'repair') {
      if (v.repair_reason) infoHtml += `<span class="card-info">修車：${v.repair_reason}</span>`;
    }
    card.innerHTML = `<span class="plate-no">${v.plate_no}</span>${infoHtml}`;
  }

  // Click to select
  card.addEventListener('click', e => {
    e.stopPropagation();
    if (state.selectedPlates.has(v.plate_no)) {
      state.selectedPlates.delete(v.plate_no);
    } else {
      state.selectedPlates.add(v.plate_no);
    }
    refreshSelectionUI();
  });

  // Drag start
  card.addEventListener('dragstart', e => {
    card.classList.add('dragging');
    e.dataTransfer.setData('text/plain', v.plate_no);
    e.dataTransfer.effectAllowed = 'move';
  });
  card.addEventListener('dragend', () => card.classList.remove('dragging'));

  return card;
}

function refreshSelectionUI() {
  // Update selection count
  const countEl = document.getElementById('sel-count');
  if (countEl) countEl.textContent = `已選取: ${state.selectedPlates.size} 台`;

  // Toggle selected class on cards
  document.querySelectorAll('.vehicle-card').forEach(card => {
    const plate = card.getAttribute('data-plate');
    card.classList.toggle('selected', state.selectedPlates.has(plate));
  });
}

// ══════════════════════════════════════════════════════════════
//   Drag & Drop Handler
// ══════════════════════════════════════════════════════════════
async function handleDrop(targetStatus, draggedPlate) {
  if (!draggedPlate) return;

  // Determine which plates to move
  let platesToMove;
  if (state.selectedPlates.has(draggedPlate) && state.selectedPlates.size > 0) {
    platesToMove = [...state.selectedPlates];
  } else {
    platesToMove = [draggedPlate];
  }

  // Check all have same current status
  const statusSet = new Set();
  for (const p of platesToMove) {
    const v = state.vehicles.find(x => x.plate_no === p);
    if (v) statusSet.add(v.status);
  }
  if (statusSet.size > 1) {
    showToast('多選拖曳時，請只選取在同一個狀態區塊的車輛。', 'error');
    return;
  }

  const currentStatus = [...statusSet][0];
  if (currentStatus === targetStatus) return;

  // Moving OUT of "out" status → need complete-out dialog
  if (currentStatus === 'out' && targetStatus !== 'out') {
    showCompleteOutDialog(platesToMove, targetStatus);
    return;
  }

  // Moving TO certain statuses → show dialog
  if (targetStatus === 'out') {
    showOutDialog(platesToMove);
    return;
  }
  if (targetStatus === 'loading') {
    showLoadingDialog(platesToMove);
    return;
  }
  if (targetStatus === 'repair') {
    showRepairDialog(platesToMove);
    return;
  }

  // Simple status changes (standby_empty, standby_full)
  try {
    for (const p of platesToMove) {
      await api('PUT', `/api/vehicles/${encodeURIComponent(p)}/status`, { status: targetStatus });
    }
    state.selectedPlates.clear();
    renderMain();
  } catch (e) {
    showToast(e.message, 'error');
  }
}

// ══════════════════════════════════════════════════════════════
//   Status-Change Dialogs
// ══════════════════════════════════════════════════════════════

// ── Out Dialog ──────────────────────────────────────────────
async function showOutDialog(plates) {
  let destOptions = '';
  try {
    state.destinations = await api('GET', '/api/destinations');
    destOptions = state.destinations.map(d =>
      `<option value="${d.destination_name}" data-hours="${d.hours}">${d.destination_name}（${d.hours} hr）</option>`
    ).join('');
  } catch { /* ignore */ }

  if (!destOptions) {
    showToast('請先到設定頁面新增出差目的地。', 'error');
    return;
  }

  showModal(
    `${plates.length === 1 ? plates[0] : plates.length + ' 台車'} 出差設定`,
    `
      <p class="modal-subtitle">選取車輛：${plates.join('、')}</p>
      <div class="form-group">
        <label>目的地</label>
        <select id="modal-dest">${destOptions}</select>
      </div>
      <p style="font-size:0.78rem; color:var(--text-muted);">時間會根據設定頁面的「目的地對應時數」自動計算。</p>
    `,
    [
      { text: '取消', onClick: closeModal },
      {
        text: '確定', cls: 'btn-primary', onClick: async () => {
          const sel = document.getElementById('modal-dest');
          const dest = sel.value;
          const hours = parseFloat(sel.selectedOptions[0].getAttribute('data-hours'));
          closeModal();

          let errors = [];
          for (const p of plates) {
            try {
              await api('PUT', `/api/vehicles/${encodeURIComponent(p)}/out`, { destination: dest, hours });
            } catch (e) {
              errors.push(`${p}：${e.message}`);
            }
          }
          state.selectedPlates.clear();
          renderMain();
          if (errors.length) showToast(errors.join('\n'), 'error');
        }
      },
    ]
  );
}

// ── Loading Dialog ─────────────────────────────────────────
async function showLoadingDialog(plates) {
  let levelOptions = '';
  try {
    state.loadingLevels = await api('GET', '/api/loading-levels');
    levelOptions = state.loadingLevels.map(l =>
      `<option value="${l.level_name}" data-hours="${l.hours}">${l.level_name}（${l.hours} hr）</option>`
    ).join('');
  } catch { /* ignore */ }

  if (!levelOptions) {
    showToast('請先到設定頁面新增裝料等級。', 'error');
    return;
  }

  showModal(
    `${plates.length === 1 ? plates[0] : plates.length + ' 台車'} 裝料設定`,
    `
      <p class="modal-subtitle">選取車輛：${plates.join('、')}</p>
      <div class="form-group">
        <label>裝料等級</label>
        <select id="modal-level">${levelOptions}</select>
      </div>
    `,
    [
      { text: '取消', onClick: closeModal },
      {
        text: '確定', cls: 'btn-primary', onClick: async () => {
          const sel = document.getElementById('modal-level');
          const level = sel.value;
          const hours = parseFloat(sel.selectedOptions[0].getAttribute('data-hours'));
          closeModal();

          for (const p of plates) {
            try {
              await api('PUT', `/api/vehicles/${encodeURIComponent(p)}/loading`, { level, hours });
            } catch (e) {
              showToast(`${p}：${e.message}`, 'error');
            }
          }
          state.selectedPlates.clear();
          renderMain();
        }
      },
    ]
  );
}

// ── Repair Dialog ──────────────────────────────────────────
function showRepairDialog(plates) {
  showModal(
    `${plates.length === 1 ? plates[0] : plates.length + ' 台車'} 修車原因`,
    `
      <p class="modal-subtitle">選取車輛：${plates.join('、')}</p>
      <div class="form-group">
        <label>修車原因</label>
        <textarea id="modal-reason" rows="3" placeholder="例如：輪胎異常、煞車異常、引擎問題"></textarea>
      </div>
    `,
    [
      { text: '取消', onClick: closeModal },
      {
        text: '確定', cls: 'btn-primary', onClick: async (box) => {
          const reason = box.querySelector('#modal-reason').value.trim();
          if (!reason) { showToast('修車原因必填', 'error'); return; }
          closeModal();

          for (const p of plates) {
            try {
              await api('PUT', `/api/vehicles/${encodeURIComponent(p)}/repair`, { reason });
            } catch (e) {
              showToast(`${p}：${e.message}`, 'error');
            }
          }
          state.selectedPlates.clear();
          renderMain();
        }
      },
    ]
  );
}

// ── Complete Out Dialog ────────────────────────────────────
function showCompleteOutDialog(plates, toStatus) {
  const now = new Date();
  const nowText = `${now.getFullYear()}/${String(now.getMonth()+1).padStart(2,'0')}/${String(now.getDate()).padStart(2,'0')} ${String(now.getHours()).padStart(2,'0')}:${String(now.getMinutes()).padStart(2,'0')}`;

  showModal(
    `${plates.length === 1 ? plates[0] : plates.length + ' 台車'} 出差完成紀錄`,
    `
      <p class="modal-subtitle">選取車輛：${plates.join('、')}</p>
      <p style="font-size:0.82rem; color:var(--text-secondary); margin-bottom:12px;">請輸入實際完成時間。確認後，車輛才會移出「出差中」。</p>
      <div class="form-group">
        <label>實際完成時間</label>
        <input type="text" id="modal-finish-time" value="${nowText}" placeholder="例如：2026/04/27 15:30" />
      </div>
    `,
    [
      { text: '取消', onClick: closeModal },
      {
        text: '確定', cls: 'btn-primary', onClick: async (box) => {
          const finishTime = box.querySelector('#modal-finish-time').value.trim();
          if (!finishTime) { showToast('時間不可空白', 'error'); return; }
          closeModal();

          for (const p of plates) {
            try {
              await api('PUT', `/api/vehicles/${encodeURIComponent(p)}/complete-out`, {
                to_status: toStatus,
                actual_finish_time: finishTime,
              });
            } catch (e) {
              showToast(`${p}：${e.message}`, 'error');
            }
          }
          state.selectedPlates.clear();
          renderMain();
        }
      },
    ]
  );
}

// ══════════════════════════════════════════════════════════════
//   Export Dialog
// ══════════════════════════════════════════════════════════════
function showExportDialog() {
  const now = new Date();
  const todayText = `${now.getFullYear()}/${String(now.getMonth()+1).padStart(2,'0')}/${String(now.getDate()).padStart(2,'0')}`;

  showModal(
    '匯出出差紀錄',
    `
      <p class="modal-subtitle">請選擇要匯出的「實際完成時間」區間。</p>
      <div class="form-group">
        <label>起始時間</label>
        <input type="text" id="modal-export-start" value="${todayText}" placeholder="例如：2026/04/27 或 2026/04/27 08:00" />
      </div>
      <div class="form-group">
        <label>結束時間</label>
        <input type="text" id="modal-export-end" value="${todayText}" placeholder="例如：2026/04/27 或 2026/04/27 17:30" />
      </div>
      <p style="font-size:0.72rem; color:var(--text-muted);">只輸入日期時，起始自動為 00:00:00，結束自動為 23:59:59。</p>
    `,
    [
      { text: '取消', onClick: closeModal },
      {
        text: '匯出 Excel', cls: 'btn-primary', onClick: () => {
          const start = document.getElementById('modal-export-start').value.trim();
          const end = document.getElementById('modal-export-end').value.trim();
          closeModal();

          const params = new URLSearchParams();
          if (start) params.set('start', start);
          if (end) params.set('end', end);

          window.open(`/api/trip-records/export?${params}`, '_blank');
        }
      },
    ]
  );
}

// ══════════════════════════════════════════════════════════════
//   SETTINGS VIEW
// ══════════════════════════════════════════════════════════════
async function renderSettings() {
  state.currentView = 'settings';
  stopTimers();

  const u = state.currentUser;
  const isAdmin = u && u.role === 'admin';
  const roleCls = u ? `badge-${u.role}` : '';

  // Fetch latest data
  try {
    const [vehicles, destinations, loadingLevels] = await Promise.all([
      api('GET', '/api/vehicles'),
      api('GET', '/api/destinations'),
      api('GET', '/api/loading-levels'),
    ]);
    state.vehicles = vehicles;
    state.destinations = destinations;
    state.loadingLevels = loadingLevels;
  } catch (e) {
    showToast('載入設定資料失敗: ' + e.message, 'error');
  }

  const appEl = document.getElementById('app');
  appEl.innerHTML = '';

  // Top bar
  const topBar = document.createElement('div');
  topBar.className = 'top-bar';
  topBar.innerHTML = `
    <h1>⚙ 設定頁面</h1>
    <div class="top-bar-info">
      <span class="user-badge ${roleCls}">${u ? `${u.display_name} / ${u.role}` : ''}</span>
    </div>
    <div class="top-bar-actions">
      <button class="btn btn-secondary btn-sm" id="btn-back-main">← 返回主畫面</button>
      <button class="btn btn-secondary btn-sm" id="btn-refresh-settings">↻ 重新整理</button>
      <button class="btn btn-secondary btn-sm" id="btn-logout-settings">登出</button>
    </div>
  `;
  appEl.appendChild(topBar);

  document.getElementById('btn-back-main').onclick = () => renderMain();
  document.getElementById('btn-refresh-settings').onclick = () => renderSettings();
  document.getElementById('btn-logout-settings').onclick = () => { state.currentUser = null; renderLogin(); };

  const grid = document.createElement('div');
  grid.className = 'settings-grid';

  grid.appendChild(buildVehicleSettings());
  grid.appendChild(await buildDestinationSettings());
  grid.appendChild(buildLoadingSettings());
  if (isAdmin) grid.appendChild(await buildUserSettings());

  appEl.appendChild(grid);
}

// ── Vehicle Settings ────────────────────────────────────────
function buildVehicleSettings() {
  const section = document.createElement('div');
  section.className = 'settings-section';

  let rowsHTML = '';
  for (const v of state.vehicles) {
    rowsHTML += `
      <div class="settings-row" data-old-plate="${v.plate_no}">
        <label>車牌</label>
        <input type="text" class="s-plate" value="${v.plate_no}" style="width:100px" />
        <label>料件</label>
        <select class="s-material" style="width:70px">
          <option value="A" ${v.material_type === 'A' ? 'selected' : ''}>A</option>
          <option value="B" ${v.material_type === 'B' ? 'selected' : ''}>B</option>
        </select>
        <button class="btn btn-danger btn-sm s-del-vehicle" data-plate="${v.plate_no}">刪除</button>
      </div>
    `;
  }

  section.innerHTML = `
    <h3>🚛 車輛設定</h3>
    <div class="settings-add-row">
      <input type="text" id="new-plate" placeholder="新增車牌" style="width:110px" />
      <select id="new-material" style="width:70px">
        <option value="A">A</option>
        <option value="B">B</option>
      </select>
      <button class="btn btn-primary btn-sm" id="btn-add-vehicle">新增車輛</button>
    </div>
    ${rowsHTML}
    <div style="text-align:right; margin-top:12px;">
      <button class="btn btn-success btn-sm" id="btn-save-vehicles">儲存車輛設定</button>
    </div>
  `;

  // Wire events after DOM is added
  setTimeout(() => {
    document.getElementById('btn-add-vehicle')?.addEventListener('click', async () => {
      const plate = document.getElementById('new-plate').value.trim();
      const material = document.getElementById('new-material').value;
      if (!plate) { showToast('車牌不可空白', 'error'); return; }
      try {
        await api('POST', '/api/vehicles', { plate_no: plate, material_type: material });
        showToast('新增成功', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });

    document.querySelectorAll('.s-del-vehicle').forEach(btn => {
      btn.addEventListener('click', async () => {
        const plate = btn.getAttribute('data-plate');
        try {
          await api('DELETE', `/api/vehicles/${encodeURIComponent(plate)}`);
          showToast('已刪除', 'success');
          renderSettings();
        } catch (e) { showToast(e.message, 'error'); }
      });
    });

    document.getElementById('btn-save-vehicles')?.addEventListener('click', async () => {
      const rows = section.querySelectorAll('.settings-row');
      try {
        for (const row of rows) {
          const oldPlate = row.getAttribute('data-old-plate');
          const newPlate = row.querySelector('.s-plate').value.trim();
          const material = row.querySelector('.s-material').value;
          if (!newPlate) { showToast('車牌不可空白', 'error'); return; }
          await api('PUT', `/api/vehicles/${encodeURIComponent(oldPlate)}`, { new_plate_no: newPlate, material_type: material });
        }
        showToast('車輛設定已儲存', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });
  }, 0);

  return section;
}

// ── Destination Settings ────────────────────────────────────
async function buildDestinationSettings() {
  const section = document.createElement('div');
  section.className = 'settings-section';

  let rowsHTML = '';
  for (const d of state.destinations) {
    // Fetch whitelist for each destination
    let whitelistHtml = '';
    try {
      const wl = await api('GET', `/api/whitelist/${encodeURIComponent(d.destination_name)}`);
      const allCars = wl.all_cars || [];
      const selected = new Set(wl.selected || []);
      if (allCars.length > 0) {
        const checks = allCars.map(c =>
          `<label><input type="checkbox" ${selected.has(c) ? 'checked' : ''} data-dest="${d.destination_name}" data-car="${c}" class="wl-check" />${c}</label>`
        ).join('');
        whitelistHtml = `
          <div class="whitelist-area">
            <h4>允許出差車牌</h4>
            <p class="whitelist-hint">勾選後自動儲存；只有勾選的車牌可前往此目的地。</p>
            <div class="whitelist-checks">${checks}</div>
          </div>
        `;
      }
    } catch { /* ignore */ }

    rowsHTML += `
      <div class="settings-row" style="flex-direction:column; align-items:stretch;" data-old-dest="${d.destination_name}">
        <div style="display:flex; align-items:center; gap:8px; flex-wrap:wrap;">
          <label>目的地</label>
          <input type="text" class="s-dest-name" value="${d.destination_name}" style="width:120px" />
          <label>時數 hr</label>
          <input type="number" class="s-dest-hours" value="${d.hours}" step="0.5" style="width:80px" />
          <button class="btn btn-danger btn-sm s-del-dest" data-dest="${d.destination_name}">刪除</button>
        </div>
        ${whitelistHtml}
      </div>
    `;
  }

  section.innerHTML = `
    <h3>🗺️ 出差目的地設定</h3>
    <div class="settings-add-row">
      <input type="text" id="new-dest" placeholder="新增目的地" style="width:120px" />
      <input type="number" id="new-dest-hours" value="1" step="0.5" style="width:80px" />
      <button class="btn btn-primary btn-sm" id="btn-add-dest">新增目的地</button>
    </div>
    ${rowsHTML}
    <div style="text-align:right; margin-top:12px;">
      <button class="btn btn-success btn-sm" id="btn-save-dests">儲存目的地設定</button>
    </div>
  `;

  setTimeout(() => {
    document.getElementById('btn-add-dest')?.addEventListener('click', async () => {
      const name = document.getElementById('new-dest').value.trim();
      const hours = parseFloat(document.getElementById('new-dest-hours').value);
      if (!name) { showToast('目的地名稱不可空白', 'error'); return; }
      try {
        await api('POST', '/api/destinations', { destination_name: name, hours });
        showToast('新增成功', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });

    document.querySelectorAll('.s-del-dest').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await api('DELETE', `/api/destinations/${encodeURIComponent(btn.getAttribute('data-dest'))}`);
          showToast('已刪除', 'success');
          renderSettings();
        } catch (e) { showToast(e.message, 'error'); }
      });
    });

    document.getElementById('btn-save-dests')?.addEventListener('click', async () => {
      const rows = section.querySelectorAll('.settings-row');
      try {
        for (const row of rows) {
          const oldName = row.getAttribute('data-old-dest');
          const newName = row.querySelector('.s-dest-name').value.trim();
          const hours = parseFloat(row.querySelector('.s-dest-hours').value);
          if (!newName) { showToast('名稱不可空白', 'error'); return; }
          await api('PUT', `/api/destinations/${encodeURIComponent(oldName)}`, { new_name: newName, hours });
        }
        showToast('目的地設定已儲存', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });

    // Whitelist auto-save
    document.querySelectorAll('.wl-check').forEach(cb => {
      cb.addEventListener('change', async () => {
        const dest = cb.getAttribute('data-dest');
        const allChecks = document.querySelectorAll(`.wl-check[data-dest="${dest}"]`);
        const carNos = [];
        allChecks.forEach(c => { if (c.checked) carNos.push(c.getAttribute('data-car')); });
        try {
          await api('PUT', `/api/whitelist/${encodeURIComponent(dest)}`, { car_nos: carNos });
          showToast(`已儲存「${dest}」的車牌白名單`, 'success');
        } catch (e) { showToast(e.message, 'error'); }
      });
    });
  }, 0);

  return section;
}

// ── Loading Level Settings ──────────────────────────────────
function buildLoadingSettings() {
  const section = document.createElement('div');
  section.className = 'settings-section';

  let rowsHTML = '';
  for (const l of state.loadingLevels) {
    rowsHTML += `
      <div class="settings-row" data-old-level="${l.level_name}">
        <label>等級</label>
        <input type="text" class="s-level-name" value="${l.level_name}" style="width:110px" />
        <label>小時</label>
        <input type="number" class="s-level-hours" value="${l.hours}" step="0.5" style="width:80px" />
        <button class="btn btn-danger btn-sm s-del-level" data-level="${l.level_name}">刪除</button>
      </div>
    `;
  }

  section.innerHTML = `
    <h3>📦 裝料等級設定</h3>
    <div class="settings-add-row">
      <input type="text" id="new-level" placeholder="新增裝料等級" style="width:120px" />
      <input type="number" id="new-level-hours" value="0.5" step="0.5" style="width:80px" />
      <button class="btn btn-primary btn-sm" id="btn-add-level">新增裝料等級</button>
    </div>
    ${rowsHTML}
    <div style="text-align:right; margin-top:12px;">
      <button class="btn btn-success btn-sm" id="btn-save-levels">儲存裝料等級設定</button>
    </div>
  `;

  setTimeout(() => {
    document.getElementById('btn-add-level')?.addEventListener('click', async () => {
      const name = document.getElementById('new-level').value.trim();
      const hours = parseFloat(document.getElementById('new-level-hours').value);
      if (!name) { showToast('等級名稱不可空白', 'error'); return; }
      try {
        await api('POST', '/api/loading-levels', { level_name: name, hours });
        showToast('新增成功', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });

    document.querySelectorAll('.s-del-level').forEach(btn => {
      btn.addEventListener('click', async () => {
        try {
          await api('DELETE', `/api/loading-levels/${encodeURIComponent(btn.getAttribute('data-level'))}`);
          showToast('已刪除', 'success');
          renderSettings();
        } catch (e) { showToast(e.message, 'error'); }
      });
    });

    document.getElementById('btn-save-levels')?.addEventListener('click', async () => {
      const rows = section.querySelectorAll('.settings-row');
      try {
        for (const row of rows) {
          const oldLevel = row.getAttribute('data-old-level');
          const newLevel = row.querySelector('.s-level-name').value.trim();
          const hours = parseFloat(row.querySelector('.s-level-hours').value);
          if (!newLevel) { showToast('等級名稱不可空白', 'error'); return; }
          await api('PUT', `/api/loading-levels/${encodeURIComponent(oldLevel)}`, { new_level: newLevel, hours });
        }
        showToast('裝料等級設定已儲存', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });
  }, 0);

  return section;
}

// ── User Settings (admin only) ──────────────────────────────
async function buildUserSettings() {
  const section = document.createElement('div');
  section.className = 'settings-section';

  let users = [];
  try {
    users = await api('GET', '/api/users');
  } catch { /* ignore */ }

  let rowsHTML = '';
  for (const u of users) {
    rowsHTML += `
      <div class="settings-row" data-old-login="${u.login_account}">
        <label>帳號</label>
        <input type="text" class="s-user-login" value="${u.login_account}" style="width:100px" />
        <label>姓名</label>
        <input type="text" class="s-user-name" value="${u.display_name}" style="width:90px" />
        <label>新密碼</label>
        <input type="password" class="s-user-pw" placeholder="不修改留空" style="width:90px" />
        <label>權限</label>
        <select class="s-user-role" style="width:80px">
          <option value="admin" ${u.role === 'admin' ? 'selected' : ''}>admin</option>
          <option value="editor" ${u.role === 'editor' ? 'selected' : ''}>editor</option>
          <option value="viewer" ${u.role === 'viewer' ? 'selected' : ''}>viewer</option>
        </select>
        <label>啟用</label>
        <select class="s-user-active" style="width:55px">
          <option value="1" ${u.is_active === 1 ? 'selected' : ''}>1</option>
          <option value="0" ${u.is_active === 0 ? 'selected' : ''}>0</option>
        </select>
        <button class="btn btn-danger btn-sm s-del-user" data-login="${u.login_account}">刪除</button>
      </div>
    `;
  }

  section.innerHTML = `
    <h3>👤 使用者管理</h3>
    <div class="settings-add-row">
      <input type="text" id="new-user-login" placeholder="帳號" style="width:90px" />
      <input type="text" id="new-user-name" placeholder="姓名" style="width:90px" />
      <input type="password" id="new-user-pw" placeholder="密碼" style="width:80px" />
      <select id="new-user-role" style="width:80px">
        <option value="viewer">viewer</option>
        <option value="editor">editor</option>
        <option value="admin">admin</option>
      </select>
      <button class="btn btn-primary btn-sm" id="btn-add-user">新增使用者</button>
    </div>
    ${rowsHTML}
    <div style="text-align:right; margin-top:12px;">
      <button class="btn btn-success btn-sm" id="btn-save-users">儲存使用者設定</button>
    </div>
  `;

  setTimeout(() => {
    document.getElementById('btn-add-user')?.addEventListener('click', async () => {
      const login = document.getElementById('new-user-login').value.trim();
      const name = document.getElementById('new-user-name').value.trim();
      const pw = document.getElementById('new-user-pw').value.trim();
      const role = document.getElementById('new-user-role').value;
      if (!login || !name || !pw) { showToast('帳號、姓名、密碼都必填', 'error'); return; }
      try {
        await api('POST', '/api/users', { login_account: login, display_name: name, password: pw, role });
        showToast('新增成功', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });

    document.querySelectorAll('.s-del-user').forEach(btn => {
      btn.addEventListener('click', async () => {
        const login = btn.getAttribute('data-login');
        if (login === state.currentUser?.login_account) {
          showToast('不可刪除目前登入中的帳號', 'error');
          return;
        }
        try {
          await api('DELETE', `/api/users/${encodeURIComponent(login)}`);
          showToast('已刪除', 'success');
          renderSettings();
        } catch (e) { showToast(e.message, 'error'); }
      });
    });

    document.getElementById('btn-save-users')?.addEventListener('click', async () => {
      const rows = section.querySelectorAll('.settings-row');
      try {
        for (const row of rows) {
          const oldLogin = row.getAttribute('data-old-login');
          const newLogin = row.querySelector('.s-user-login').value.trim();
          const displayName = row.querySelector('.s-user-name').value.trim();
          const password = row.querySelector('.s-user-pw').value.trim();
          const role = row.querySelector('.s-user-role').value;
          const isActive = parseInt(row.querySelector('.s-user-active').value);
          if (!newLogin || !displayName) { showToast('帳號與姓名不可空白', 'error'); return; }
          await api('PUT', `/api/users/${encodeURIComponent(oldLogin)}`, {
            new_login: newLogin, display_name: displayName, password: password || null, role, is_active: isActive,
          });
        }
        showToast('使用者設定已儲存', 'success');
        renderSettings();
      } catch (e) { showToast(e.message, 'error'); }
    });
  }, 0);

  return section;
}

// ══════════════════════════════════════════════════════════════
//   Countdown Timer — 每秒更新倒數
// ══════════════════════════════════════════════════════════════
function startCountdownTimer() {
  state.countdownTimer = setInterval(() => {
    document.querySelectorAll('.vehicle-card[data-eta]').forEach(card => {
      const eta = card.getAttribute('data-eta');
      if (!eta) return;

      const timerEl = card.querySelector('.card-timer');
      if (!timerEl) return;

      const { text, overdue } = getRemainingText(eta);

      // Check status from the card's classes
      const isLoading = card.classList.contains('card-wide') && timerEl.textContent.includes('完成') || timerEl.textContent.includes('剩餘');
      const isLoadingCard = card.closest('.status-column')?.getAttribute('data-status') === 'loading';

      if (isLoadingCard) {
        timerEl.textContent = overdue ? text.replace('超時', '完成') : text;
        if (overdue && !card.classList.contains('loading-done')) {
          card.classList.add('loading-done');
        }
      } else {
        timerEl.textContent = text;
        const isOutCol = card.closest('.status-column')?.getAttribute('data-status') === 'out';
        if (isOutCol && overdue && !card.classList.contains('out-overdue')) {
          card.classList.add('out-overdue');
        }
      }
    });
  }, 1000);
}

function stopTimers() {
  if (state.refreshTimer) { clearInterval(state.refreshTimer); state.refreshTimer = null; }
  if (state.countdownTimer) { clearInterval(state.countdownTimer); state.countdownTimer = null; }
}

// ══════════════════════════════════════════════════════════════
//   INIT
// ══════════════════════════════════════════════════════════════
document.addEventListener('DOMContentLoaded', () => {
  renderLogin();
});
