const roles = {
  student: "学生", advisor: "指导教师", manager: "场地管理员", admin: "系统管理员",
};
const states = {
  DRAFT: ["草稿", ""],
  PENDING_ADVISOR: ["待指导教师初审", "pending"],
  PENDING_VENUE: ["待场地管理员终审", "pending"],
  APPROVED: ["预约已批准", "approved"],
  REJECTED: ["已驳回", "rejected"],
  CANCELLED: ["已取消", ""],
  FINISHED: ["已结束", ""],
};
const approvalStates = { advisor: "PENDING_ADVISOR", manager: "PENDING_VENUE" };

function dateAt(day, offset) {
  const result = new Date(day + "T12:00:00Z");
  result.setUTCDate(result.getUTCDate() + offset);
  return result.toISOString().slice(0, 10);
}

const byId = id => document.getElementById(id);
const content = byId("content");
const dialog = byId("dialog");
let data;
let account;
let schedule;
let inventory;
let draft = {};
let toastTimer;
let writing = false;
let bookingStock;
let refreshNumber = 0;

const navigation = {
  home: ["工作台", "⌂"],
  venues: ["场地检索", "▤"],
  schedule: ["排期日历", "▦"],
  booking: ["发起预约", "＋"],
  history: ["我的申请", "▧"],
  approvals: ["待办审批", "✓"],
  assets: ["物资台账", "▣"],
  locks: ["场地锁定", "◷"],
  users: ["用户管理", "♙"],
  audit: ["审计日志", "▤"],
  dictionary: ["基础字典", "▥"],
  reset: ["数据初始化", "↻"],
  profile: ["个人中心", ""],
};
const menus = {
  student: ["home", "venues", "schedule", "booking", "history"],
  advisor: ["home", "approvals", "venues", "schedule"],
  manager: ["home", "approvals", "venues", "schedule", "assets", "locks"],
  admin: ["home", "users", "dictionary", "audit", "reset"],
};

function escape(value = "") {
  return String(value ?? "").replace(/[&<>"']/g, char => ({
    "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
  })[char]);
}

const venueById = id => data.venues.find(venue => venue.id === id);
const userById = id => data.users.find(user => user.id === id);
const reservationById = id => data.reservations.find(item => item.id === Number(id));
const own = () => data.reservations.filter(item => item.user === account.id);
const pending = () => data.reservations.filter(item => item.detailed && item.status === approvalStates[account.role]);
const isPending = item => Object.values(approvalStates).includes(item.status);
const sorted = records => [...records].sort((a, b) => b.created.localeCompare(a.created) || b.id - a.id);
const status = key => `<span class="status ${states[key][1]}">${states[key][0]}</span>`;
const venueStatus = venue => `<span class="status ${venue.maintenance ? "" : "available"}">${venue.maintenance ? "维护检修中" : "正常开放"}</span>`;
const code = item => item.code;
const range = item => `${item.start}–${item.end}`;
const button = (label, action, value = "", style = "") =>
  `<button type="button" class="button ${style}" data-action="${action}" data-value="${escape(value)}">${label}</button>`;
const link = (label, page, style = "") => `<a class="button ${style}" href="#${page}">${label}</a>`;
const options = (items, value) => items.map(([id, label]) =>
  `<option value="${escape(id)}" ${String(id) === String(value) ? "selected" : ""}>${escape(label)}</option>`).join("");
const optionList = list => list.map(value => [value, value]);
const field = (label, html, extra = "") => `<label class="field ${extra}">${label}${html}</label>`;
const panel = (title, html, action = "") =>
  `<section class="panel"><div class="section-head"><h2>${title}</h2>${action}</div>${html}</section>`;
const body = html => `<div class="section-body">${html}</div>`;
const empty = message => `<div class="empty">${message}</div>`;
const table = (headings, rows, message = "暂无记录") => rows.length
  ? `<div class="table-wrap"><table><thead><tr>${headings.map(label => `<th scope="col">${label}</th>`).join("")}</tr></thead>
     <tbody>${rows.map(columns => `<tr>${columns.map(value => `<td>${value}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`
  : empty(message);

async function api(path, method = "GET", payload = {}) {
  const options = { method };
  if (method !== "GET") {
    options.headers = { "Content-Type": "application/json" };
    options.body = JSON.stringify(payload);
  }
  let response;
  try {
    response = await fetch("/api" + path, options);
  } catch {
    throw new Error("无法连接系统，请稍后重试。");
  }
  const result = await response.json().catch(() => ({}));
  if (!response.ok) throw Object.assign(new Error(result.message || "请求未成功。"), { status: response.status, field: result.field });
  return result;
}

async function loadWorkspace() {
  const number = ++refreshNumber;
  const result = await api("/workspace");
  if (number !== refreshNumber) return false;
  data = result;
  account = data.account;
  schedule ??= { date: data.suggestedDate, venue: "all", mode: "week" };
  inventory ??= { date: data.suggestedDate, start: "14:00", end: "16:30" };
  bookingStock = undefined;
  return true;
}

function showLogin() {
  refreshNumber++;
  account = data = schedule = inventory = bookingStock = undefined;
  draft = {};
  if (dialog.open) dialog.close();
  render();
}

async function mutate(path, { method = "POST", payload, error, page, message, signOut = false } = {}) {
  if (writing) return;
  writing = true;
  refreshNumber++;
  if (error) error.textContent = "";
  try {
    const result = await api(path, method, payload);
    if (signOut) showLogin();
    else {
      await loadWorkspace();
      if (dialog.open) dialog.close();
      if (page) {
        draft = {};
        go(page);
      } else render();
    }
    notify(result.message || message || "操作已完成。");
  } catch (failure) {
    if (failure.status === 401) showLogin();
    if (failure.field === "people" && byId("people-error")) byId("people-error").textContent = failure.message;
    else if (error?.isConnected && !error.closest("[hidden]")) {
      error.textContent = failure.message;
      error.scrollIntoView({ block: "nearest" });
    } else notify(failure.message);
  } finally {
    writing = false;
  }
}

function notify(message) {
  const toast = byId("toast");
  toast.textContent = message;
  toast.hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { toast.hidden = true; }, 3500);
}

function showDialog(title, html) {
  dialog.innerHTML = `<div class="section-head"><h2 id="dialog-title">${escape(title)}</h2>
    ${button("关闭", "close")}</div>${body(html)}`;
  if (!dialog.open) dialog.showModal();
}

function go(page) {
  if (location.hash !== "#" + page) window.history.pushState(null, "", "#" + page);
  render();
}

function pageHead(page, title, subtitle, action = "") {
  return `<nav class="crumb" aria-label="面包屑">${page === "home" ? "首页" : `<a href="#home">首页</a><span aria-hidden="true">/</span>${navigation[page][0]}`}</nav>
    <section class="page-head"><div class="header-row"><div><h1>${title}</h1>
    <p class="subhead">${subtitle}</p></div>${action}</div></section>`;
}

function render() {
  const brand = `<div class="brand"><span class="brand-mark" aria-hidden="true"><span class="brand-building"></span></span>
    <div><strong>校园活动与场地调度系统</strong></div></div>`;
  byId("topbar").innerHTML = brand + (account ? `<div class="account"><a href="#profile">${account.name}</a>
    <span class="role">${roles[account.role]}</span><button class="exit" data-action="logout">退出登录</button></div>` : "");
  byId("shell").hidden = !account;
  byId("login").hidden = Boolean(account);
  if (!account) {
    byId("login").innerHTML = `<section class="panel"><h1>系统登录</h1>
      <p class="subhead">请使用校内学号或工号登录。</p>
      <form id="login-form">
        ${field("学号 / 工号", '<input name="username" autocomplete="username" required>')}
        ${field("密码", '<input type="password" name="password" autocomplete="current-password" required>')}
        <p class="error" role="alert"></p><button class="button primary">登录</button>
      </form>
      </section>`;
    return;
  }
  const allowed = menus[account.role];
  const target = location.hash.slice(1);
  const page = [...allowed, "profile"].includes(target) ? target : "home";
  byId("sidebar").innerHTML = `<nav aria-label="功能导航"><p class="nav-heading">业务导航</p><div class="nav-links">
    ${allowed.map(key => `<a class="nav-link" href="#${key}" ${key === page ? 'aria-current="page"' : ""}>
      <span class="nav-icon" aria-hidden="true">${navigation[key][1]}</span>${navigation[key][0]}</a>`).join("")}</div></nav>`;
  content.innerHTML = pages[page]();
  syncBooking();
  syncInventory();
}

function bookingRows(records, approval = false) {
  const headings = ["活动名称", ...(approval ? ["申请人"] : []), "预约场地", "使用日期及时间", "审批状态", "操作"];
  return table(headings, records.map(item => [
    `<span class="record-title">${escape(item.title)}</span><span class="small">${code(item)}</span>`,
    ...(approval ? [escape(item.applicant)] : []),
    escape(venueById(item.venue).name),
    `<span class="keep">${item.date}</span><span class="small keep">${range(item)}</span>`,
    status(item.status),
    `<button type="button" class="text-button keep" data-action="record" data-value="${item.id}">${approval ? "办理审批" : "查看详情"}</button>`,
  ]), approval ? "当前没有待办申请" : "没有符合条件的申请");
}

function stat(icon, label, count, page) {
  return `<a class="stat" href="#${page}"><span class="stat-icon" aria-hidden="true">${icon}</span>
    <div><small>${label}</small><strong>${count}</strong></div></a>`;
}

function home() {
  const welcome = `${account.name} · ${account.department}`;
  if (account.role === "student") {
    const records = own();
    return pageHead("home", "预约工作台", welcome, link("＋ 发起活动预约", "booking", "primary")) +
      `<div class="stats">${stat("▧", "我的申请", records.length, "history")}${stat("◷", "审核中", records.filter(isPending).length, "history")}
      ${stat("✓", "已批准", records.filter(item => item.status === "APPROVED").length, "history")}
      ${stat("▤", "开放场地", data.venues.filter(venue => !venue.maintenance).length, "venues")}</div>` +
      panel("近期申请", bookingRows(sorted(records).slice(0, 3)), `<a class="text-button" href="#history">查看全部</a>`) +
      panel("场地排期概览", body(scheduleView(true)), `<a class="text-button" href="#schedule">查看完整日历</a>`);
  }
  if (account.role === "admin") {
    return pageHead("home", "系统管理工作台", welcome) +
      `<div class="stats">${stat("♙", "系统账号", data.users.length, "users")}${stat("▤", "审计记录", data.audit.length, "audit")}</div>` +
      panel("管理入口", body(`<div class="toolbar">${link("用户管理", "users")}${link("基础字典", "dictionary")}${link("审计日志", "audit")}${link("数据初始化", "reset")}</div>`));
  }
  return pageHead("home", account.role === "advisor" ? "指导教师工作台" : "场地管理工作台", welcome,
    link("进入审批台", "approvals", "primary")) +
    `<div class="stats">${stat("◷", "待办审批", pending().length, "approvals")}
    ${stat("▤", "开放场地", data.venues.filter(venue => !venue.maintenance).length, "venues")}</div>` +
    panel("我的待办事项", bookingRows(sorted(pending()).slice(0, 4), true));
}

const minutes = time => Number(time.slice(0, 2)) * 60 + Number(time.slice(3, 5));
const timeAt = minute => `${String(Math.floor(minute / 60)).padStart(2, "0")}:${String(minute % 60).padStart(2, "0")}`;
const times = Array.from({ length: 48 }, (_, index) => timeAt(index * 30));

function bar(item, title, kind, action, value, bounds) {
  const span = minutes(bounds.end) - minutes(bounds.start);
  const left = (minutes(item.start) - minutes(bounds.start)) * 100 / span;
  const width = (minutes(item.end) - minutes(item.start)) * 100 / span;
  const description = `${title} ${range(item)}`;
  return `<button type="button" class="bar ${kind}" style="left:${left}%;width:${width}%"
    title="${escape(description)}" aria-label="${escape(description)}" data-action="${action}" data-value="${escape(value)}">${escape(title)}</button>`;
}

function scheduleView(compact = false) {
  const weekdays = "日一二三四五六";
  const weekday = new Date(schedule.date + "T12:00:00Z").getUTCDay();
  const monday = dateAt(schedule.date, -(weekday + 6) % 7);
  const days = Array.from({ length: 7 }, (_, index) => dateAt(monday, index));
  let venues = schedule.venue === "all" ? data.venues : data.venues.filter(venue => venue.id === schedule.venue);
  if (compact && schedule.venue === "all") venues = venues.slice(0, 3);
  const visibleIds = new Set(venues.map(venue => venue.id));
  const reservations = data.reservations.filter(item => visibleIds.has(item.venue) && item.date === schedule.date
    && ["APPROVED", "PENDING_VENUE", "FINISHED"].includes(item.status));
  const locks = data.locks.filter(item => visibleIds.has(item.venue) && item.date === schedule.date);
  const first = Math.floor(Math.min(480, ...venues.map(venue => minutes(venue.open)),
    ...[...reservations, ...locks].map(item => minutes(item.start))) / 120) * 120;
  const last = Math.ceil(Math.max(1320, ...venues.map(venue => minutes(venue.close)),
    ...[...reservations, ...locks].map(item => minutes(item.end))) / 120) * 120;
  const bounds = { start: timeAt(first), end: timeAt(last) };
  const axes = Array.from({ length: (last - first) / 120 + 1 }, (_, index) => timeAt(first + index * 120));
  return `<div class="toolbar schedule-toolbar">
    <div class="toolbar">
      <label>日期 <input type="date" id="schedule-date" value="${schedule.date}"></label>
      <label>场地 <select id="schedule-venue">${options([["all", "全部场地"], ...data.venues.map(venue => [venue.id, venue.name])], schedule.venue)}</select></label>
      ${compact ? "" : `<label>视图 <select id="schedule-mode">${options([["week", "周历与时间轴"], ["day", "每日时间轴"]], schedule.mode)}</select></label>`}
    </div>
    <div class="legend"><span>已批准</span><span class="legend-pending">审核中</span><span class="legend-closed">不可用</span></div>
    </div>
    ${schedule.mode === "week" || compact ? `<div class="week" aria-label="本周日期">${days.map((day, index) =>
      `<button type="button" class="day" data-action="day" data-value="${day}" aria-pressed="${day === schedule.date}"
      aria-label="${day} 星期${weekdays[(index + 1) % 7]}">周${weekdays[(index + 1) % 7]}<strong>${day.slice(5).replace("-", "/")}</strong></button>`).join("")}</div>` : ""}
    <div class="timeline-wrap" tabindex="0" aria-label="场地时间轴"><div class="timeline" style="--timeline-columns:${axes.length - 1}">
      <span></span><div class="ticks">${axes.map(time => `<span>${time}</span>`).join("")}</div>
      ${venues.map(venue => {
        const closed = venue.maintenance ? [bounds] : [
          ...(venue.open > bounds.start ? [{ start: bounds.start, end: venue.open }] : []),
          ...(venue.close < bounds.end ? [{ start: venue.close, end: bounds.end }] : []),
        ];
        return `<div class="lane-title">${escape(venue.name)}<span class="small">${escape(venue.id)}</span></div><div class="lane">
          ${closed.map(period => bar(period, venue.maintenance ? "维护检修" : "闭馆", "closed", "venue", venue.id, bounds)).join("")}
          ${venue.maintenance ? "" : locks.filter(item => item.venue === venue.id).map(item => bar(item, item.reason, "closed", "lock-detail", item.id, bounds)).join("")}
          ${reservations.filter(item => item.venue === venue.id).map(item =>
            bar(item, item.title, venue.maintenance ? "closed" : item.status === "PENDING_VENUE" ? "pending" : "", "record", item.id, bounds)).join("")}</div>`;
      }).join("")}</div></div>`;
}

function venuePage() {
  return pageHead("venues", "场地检索", "按楼宇、场地类型、容量或开放状态查找场地。",
    account.role === "manager" ? button("新增场地", "new-venue", "", "primary") : "") +
    `<section class="panel">${body(`<div class="toolbar" id="venue-filters">
      <input id="venue-query" type="search" placeholder="场地名称或编号" aria-label="场地名称或编号">
      <select id="building" aria-label="楼宇">${options([["", "全部楼宇"], ...optionList([...new Set(data.venues.map(venue => venue.building))])], "")}</select>
      <select id="venue-type" aria-label="场地类型">${options([["", "全部类型"], ...optionList([...new Set(data.venues.map(venue => venue.type))])], "")}</select>
      <label>容量 <select id="capacity" aria-label="容量"><option value="">不限</option><option value="0,50">50 人及以下</option><option value="51,100">51–100 人</option><option value="101,9999">101 人及以上</option></select></label>
      <select id="venue-status" aria-label="开放状态"><option value="">全部状态</option><option value="open">正常开放</option><option value="closed">维护检修中</option></select>
      </div><div id="venue-results">${venueResults(data.venues, 1)}</div>`)}</section>`;
}

function venueResults(venues, page) {
  if (!venues.length) return empty("没有符合条件的场地");
  const perPage = 6;
  const total = Math.ceil(venues.length / perPage);
  return `<p class="subhead">共 ${venues.length} 处场地</p><div class="venue-grid">
    ${venues.slice((page - 1) * perPage, page * perPage).map(venue => `<article class="venue-card">
      <div class="card-head"><h2>${escape(venue.name)}</h2>${venueStatus(venue)}</div>
      <p class="muted">${escape(venue.id)} · ${escape(venue.building)} · ${escape(venue.type)}</p>
      <p>容量 ${venue.capacity} 人 · ${venue.open}–${venue.close}</p>
      <p class="muted">${escape(venue.setup)}</p>
      <div class="actions">${button("场地详情", "venue", venue.id)}${button("查看排期", "venue-schedule", venue.id)}
      ${account.role === "manager" ? button("编辑", "edit-venue", venue.id) : ""}</div></article>`).join("")}</div>
    ${total > 1 ? `<div class="toolbar"><span>第 ${page} / ${total} 页</span>
    ${page > 1 ? button("上一页", "venue-page", page - 1) : ""}${page < total ? button("下一页", "venue-page", page + 1) : ""}</div>` : ""}`;
}

function filterVenues(page = 1) {
  const query = byId("venue-query").value.trim().toLowerCase();
  const building = byId("building").value;
  const type = byId("venue-type").value;
  const [min, max] = (byId("capacity").value || "0,9999").split(",").map(Number);
  const statusFilter = byId("venue-status").value;
  const results = data.venues.filter(venue =>
    `${venue.name} ${venue.id}`.toLowerCase().includes(query) &&
    (!building || venue.building === building) && (!type || venue.type === type) &&
    min <= venue.capacity && max >= venue.capacity &&
    (!statusFilter || venue.maintenance === (statusFilter === "closed")));
  byId("venue-results").innerHTML = venueResults(results, page);
}

function timeSelect(name, value) {
  return `<select name="${name}" required>${options(optionList(times), value)}</select>`;
}

function booking() {
  const venue = venueById(draft.venue);
  const eligible = data.venues.filter(item => !item.maintenance || item === venue);
  const selection = eligible.map(item => [item.id, `${item.name}（${item.capacity} 人）`]);
  const equipment = bookingEquipment();
  return pageHead("booking", draft.id ? "编辑活动预约" : "发起活动预约", "填写活动方案，选择场地、使用时段及借用物资。") +
    `<form id="booking-form" novalidate>
      ${panel("活动信息", body(`<div class="form-grid">
        ${field("活动名称", `<input name="title" maxlength="128" required value="${escape(draft.title)}">`)}
        ${field("活动类型", `<select name="type">${options(optionList(data.activityTypes), draft.type)}</select>`)}
        ${field("预期参加人数", `<input name="people" type="number" min="1" max="${venue?.capacity ?? 9999}" required value="${escape(draft.people)}">
          <span class="error" id="people-error" aria-live="polite"></span>`)}
        ${field("活动方案与安全安排", `<textarea name="description" maxlength="4000" required>${escape(draft.description)}</textarea>`, "full")}
      </div>`))}
      ${panel("场地与使用时段", body(`<div class="form-grid">
        ${field("预约场地", `<select name="venue" id="booking-venue" required>${options([["", "请选择场地"], ...selection], draft.venue)}</select>`)}
        ${field("使用日期", `<input name="date" type="date" min="${data.today}" value="${draft.date || (schedule.date >= data.today ? schedule.date : data.suggestedDate)}" required>`)}
        ${field("开始时间", timeSelect("start", draft.start || "14:00"))}
        ${field("结束时间", timeSelect("end", draft.end || "16:30"))}
        <p class="subhead full" id="venue-hours"></p>
        <p class="error full" id="booking-error" role="alert"></p>
      </div>`))}
      ${panel("借用物资", body(equipment.length ? `<div class="equipment-list">${equipment.map(item =>
        `<label><span>${escape(item.name)}（${escape(item.unit)}）<small class="small" id="available-${escape(item.id)}">${item.enabled ? `单次限借 ${item.limit}` : "已停用，请将数量改为 0。"}</small></span>
        <input name="equipment-${escape(item.id)}" type="number" min="0" max="${item.enabled ? item.limit : 0}" value="${draft.equipment?.[item.id] || 0}" aria-label="${escape(item.name)}借用数量"></label>`).join("")}</div>` : empty("暂无可借物资")))}
      <div class="actions form-actions">${link("返回工作台", "home")}${button("保存草稿", "save-draft")}
        <button type="submit" class="button primary">提交审批</button></div>
    </form>`;
}

function bookingEquipment() {
  return data.equipment.filter(item => item.enabled || draft.equipment?.[item.id]);
}

function stockQuery({ date, start, end }) {
  return date && start < end ? new URLSearchParams({ date, start, end }).toString() : "";
}

function bookingValues(form) {
  const values = Object.fromEntries(new FormData(form));
  const equipment = Object.fromEntries(bookingEquipment()
    .map(item => [item.id, Number(values["equipment-" + item.id] || 0)]).filter(([, qty]) => qty !== 0));
  return {
    title: values.title.trim(), type: values.type, people: Number(values.people), description: values.description.trim(),
    venue: values.venue, date: values.date, start: values.start, end: values.end, equipment,
  };
}

function syncBooking() {
  const form = byId("booking-form");
  if (!form) return;
  const item = bookingValues(form);
  const venue = venueById(item.venue);
  form.elements.people.max = venue?.capacity ?? 9999;
  byId("people-error").textContent = venue && item.people > venue.capacity ? `场地容量为 ${venue.capacity} 人。` : "";
  byId("venue-hours").textContent = venue ? `开放时段 ${venue.open}–${venue.close} · 每 30 分钟为一个预约单位` : "请先选择场地。";
  const query = stockQuery(item);
  if (bookingStock?.query === query && bookingStock.form === form) return;
  const request = { query, form };
  bookingStock = request;
  const showStock = (items, unavailable = false) => {
    if (bookingStock !== request || !form.isConnected) return;
    const available = new Map(items.map(item => [item.id, item.available]));
    for (const item of bookingEquipment().filter(item => item.enabled)) {
      const extra = available.has(item.id) ? ` · 当前时段可借 ${available.get(item.id)}` : "";
      byId("available-" + item.id).textContent = `单次限借 ${item.limit}${unavailable ? " · 暂时无法查询余量" : extra}`;
    }
  };
  showStock([]);
  if (query) api("/equipments?" + query).then(result => showStock(result.items)).catch(() => showStock([], true));
}

function saveBooking(submit) {
  const form = byId("booking-form");
  const item = bookingValues(form);
  const error = byId("booking-error");
  if (submit && !form.reportValidity()) return;
  mutate(draft.id ? "/reservations/" + draft.id : "/reservations", {
    method: draft.id ? "PATCH" : "POST",
    payload: { ...item, draft: !submit },
    error, page: "history",
    message: submit ? "申请已提交，等待指导教师初审。" : "草稿已保存。",
  });
}

function historyRows() {
  const query = byId("record-query").value.trim().toLowerCase();
  const state = byId("record-status").value;
  const rows = sorted(own()).filter(item => (!state || item.status === state) &&
    `${item.title} ${venueById(item.venue).name} ${code(item)}`.toLowerCase().includes(query));
  byId("record-results").innerHTML = bookingRows(rows);
}

function history() {
  return pageHead("history", "我的申请", "查看预约进度、审批意见及历史记录。", link("＋ 发起活动预约", "booking", "primary")) +
    panel("申请记录", body(`<div class="toolbar">
      <input id="record-query" type="search" placeholder="活动名称、场地或编号" aria-label="搜索申请">
      <select id="record-status" aria-label="审批状态">${options([["", "全部状态"], ...Object.entries(states).map(([key, value]) => [key, value[0]])], "")}</select>
    </div><div id="record-results">${bookingRows(sorted(own()))}</div>`));
}

function approvals() {
  return pageHead("approvals", account.role === "advisor" ? "待办初审" : "场地审批台账",
    account.role === "advisor" ? "审阅活动方案，填写初审意见。" : "核对场地时段与物资余量，确认预约安排。",
    button("刷新待办", "refresh")) +
    panel("待办申请", body(`<div class="toolbar"><label>排序 <select id="approval-sort">
      <option value="created">按申请时间</option><option value="date">按活动日期</option></select></label></div>
      <div id="approval-results">${bookingRows(sorted(pending()), true)}</div>`));
}

function facts(pairs) {
  return `<dl class="facts">${pairs.map(([label, value]) => `<dt>${label}</dt><dd>${escape(value)}</dd>`).join("")}</dl>`;
}

function recordDetail(item) {
  const actionable = pending().includes(item);
  const mine = item.user === account.id;
  const venue = venueById(item.venue);
  const summary = facts([["预约场地", venue.name], ["使用日期", item.date], ["时间", range(item)], ["审批状态", states[item.status][0]]]);
  const cancel = item.canCancel ? button("取消预约", "ask-cancel", item.id, "danger") : "";
  const adjust = item.canReschedule ? button("调整排期", "reschedule", item.id, "primary") : "";
  if (!item.detailed) {
    showDialog(item.title, summary + `<div class="actions form-actions">${cancel}${adjust}</div>`);
    return;
  }
  const equipment = data.equipment.filter(row => item.equipment[row.id]).map(row => `${row.name} ${item.equipment[row.id]} ${row.unit}`);
  const issue = item.reviewIssue;
  showDialog(item.title, summary +
    facts([["申请编号", code(item)], ["申请人", item.applicant], ["活动类型", item.type], ["预期人数", `${item.people || "未填写"}${item.people ? " 人" : ""}`],
      ["活动方案", item.description || "未填写"], ["借用物资", equipment.join("、") || "无"]]) +
    `<h3>审批记录</h3><ol class="steps">${item.history.map(step =>
      `<li><strong>${escape(step.title)}</strong><span class="small">${escape(step.by)} · ${escape(step.at)}</span>
        ${step.comment ? `<div>${escape(step.comment)}</div>` : ""}</li>`).join("")}</ol>` +
    (actionable ? `<form id="approve-form" data-value="${item.id}">
      <p class="${issue ? "error" : "subhead"}">场地及物资核验：${escape(issue || "该时段可安排。")}</p>
      ${field("审批意见", '<textarea name="comment" placeholder="驳回时请填写至少 5 个字的原因"></textarea>')}
      <p class="error" role="alert"></p><div class="actions form-actions">
      <button class="button danger" name="decision" value="reject">驳回</button>
      <button class="button primary" name="decision" value="approve">${account.role === "advisor" ? "初审通过" : "终审批准"}</button></div></form>` : "") +
    `<div class="actions form-actions">
      ${mine && ["DRAFT", "REJECTED"].includes(item.status) ? button("编辑申请", "edit-record", item.id, "primary") : ""}
      ${mine && item.status === "DRAFT" ? button("删除草稿", "delete-record", item.id, "danger") : ""}
      ${cancel}${adjust}
    </div>`);
}

function approve(form, decision) {
  mutate(`/approvals/${form.dataset.value}/audit`, {
    payload: { decision: decision === "reject" ? "REJECTED" : "APPROVED", comment: form.elements.comment.value },
    error: form.querySelector(".error"),
  });
}

function venueDetail(venue) {
  showDialog(venue.name, facts([
    ["场地编号", venue.id], ["所属楼宇", venue.building], ["场地类型", venue.type],
    ["核定容量", venue.capacity + " 人"], ["配套设备", venue.setup],
    ["开放时段", venue.open + "–" + venue.close], ["开放状态", venue.maintenance ? "维护检修中" : "正常开放"],
  ]) + `<div class="actions form-actions">${button("查看排期", "venue-schedule", venue.id)}
    ${account.role === "student" && !venue.maintenance ? button("预约此场地", "venue-booking", venue.id, "primary") : ""}</div>`);
}

function editVenue(venue = {}) {
  showDialog(venue.id ? "编辑场地" : "新增场地", `<form id="venue-form" data-value="${escape(venue.id)}">
    <div class="form-grid">
      ${field("场地编号", `<input name="id" maxlength="32" value="${escape(venue.id)}" ${venue.id ? "readonly" : "required"}>`)}
      ${field("场地名称", `<input name="name" value="${escape(venue.name)}" required>`)}
      ${field("所属楼宇", `<input name="building" value="${escape(venue.building)}" required>`)}
      ${field("场地类型", `<input name="type" value="${escape(venue.type)}" required>`)}
      ${field("核定容量", `<input name="capacity" type="number" min="1" value="${escape(venue.capacity)}" required>`)}
      ${field("开放状态", `<select name="maintenance">${options([[0, "正常开放"], [1, "维护检修中"]], Number(Boolean(venue.maintenance)))}</select>`)}
      ${field("开放时间", timeSelect("open", venue.open || "08:00"))}
      ${field("闭馆时间", timeSelect("close", venue.close || "22:00"))}
      ${field("固定设备", `<input name="setup" value="${escape(venue.setup)}">`, "full")}
    </div>${dialogSubmit("保存场地")}</form>`);
}

function dialogSubmit(label) {
  return `<p class="error" role="alert"></p><div class="actions form-actions">
    ${button("取消", "close")}<button class="button primary">${label}</button></div>`;
}

function reschedule(item) {
  const venues = data.venues.filter(venue => !venue.maintenance || venue.id === item.venue);
  showDialog("调整排期", `<form id="reschedule-form" data-value="${item.id}"><div class="form-grid">
    ${field("场地", `<select name="venue">${options(venues.map(venue => [venue.id, venue.name]), item.venue)}</select>`)}
    ${field("使用日期", `<input type="date" name="date" value="${item.date}" min="${data.today}" required>`)}
    ${field("开始时间", timeSelect("start", item.start))}
    ${field("结束时间", timeSelect("end", item.end))}
    ${field("调整原因", '<textarea name="comment" maxlength="500"></textarea>', "full")}
    </div>${dialogSubmit("保存排期")}</form>`);
}

function inventoryTable(items) {
  return table(["物资编号", "物资名称", "总库存", "单次限借", "时段可借", "状态", "操作"],
    items.map(item => [escape(item.id), escape(item.name), `${item.total} ${escape(item.unit)}`,
      `${item.limit} ${escape(item.unit)}`, item.enabled ? `${item.available} ${escape(item.unit)}` : "—",
      item.enabled ? "可借用" : "已停用",
      button("编辑", "edit-equipment", item.id)]));
}

async function syncInventory() {
  const output = byId("inventory-results");
  if (!output) return;
  const query = stockQuery(inventory);
  output.dataset.query = query;
  if (!query) {
    output.innerHTML = empty("请选择有效的日期和时段。");
    return;
  }
  try {
    const { items } = await api("/equipments?" + query);
    if (output.isConnected && output.dataset.query === query) output.innerHTML = inventoryTable(items);
  } catch (error) {
    if (error.status === 401) showLogin();
    else if (output.isConnected && output.dataset.query === query) output.textContent = error.message;
  }
}

function assets() {
  return pageHead("assets", "物资台账", "选择使用日期和时段，查看该时段剩余的可借物资。",
    button("新增物资", "new-equipment", "", "primary")) +
    panel("校内活动物资", body(`<form class="toolbar" id="inventory-form">
      <label>日期 <input name="date" type="date" value="${inventory.date}"></label>
      <label>开始时间 ${timeSelect("start", inventory.start)}</label>
      <label>结束时间 ${timeSelect("end", inventory.end)}</label>
      </form><div id="inventory-results" aria-live="polite">${empty("正在查询库存…")}</div>`));
}

function editEquipment(item = {}) {
  showDialog(item.id ? "编辑物资" : "新增物资", `<form id="equipment-form" data-value="${escape(item.id)}">
    <div class="form-grid">
      ${field("物资编号", `<input name="id" maxlength="32" value="${escape(item.id)}" ${item.id ? "readonly" : "required"}>`)}
      ${field("物资名称", `<input name="name" value="${escape(item.name)}" required>`)}
      ${field("计量单位", `<input name="unit" value="${escape(item.unit)}" required>`)}
      ${field("总库存", `<input name="total" type="number" min="0" value="${escape(item.total)}" required>`)}
      ${field("单次限借", `<input name="limit" type="number" min="1" value="${escape(item.limit)}" required>`)}
      ${field("借用状态", `<select name="enabled">${options([[1, "可借用"], [0, "已停用"]], Number(item.enabled ?? true))}</select>`)}
    </div>${dialogSubmit("保存物资")}</form>`);
}

function locks() {
  return pageHead("locks", "场地锁定", "登记设备检修、考试等临时不可预约的时段。", button("新增锁定", "new-lock", "", "primary")) +
    panel("锁定记录", table(["场地", "日期", "时段", "锁定原因", "操作"], data.locks.map(item =>
      [escape(venueById(item.venue).name), item.date, range(item), escape(item.reason), button("解除锁定", "ask-unlock", item.id)])));
}

function newLock() {
  showDialog("新增场地锁定", `<form id="lock-form"><div class="form-grid">
    ${field("场地", `<select name="venue">${options(data.venues.map(venue => [venue.id, venue.name]), schedule.venue)}</select>`)}
    ${field("日期", `<input type="date" name="date" value="${schedule.date < data.today ? data.today : schedule.date}" min="${data.today}" required>`)}
    ${field("开始时间", timeSelect("start", "08:00"))}
    ${field("结束时间", timeSelect("end", "10:00"))}
    ${field("锁定原因", '<textarea name="reason" required></textarea>', "full")}
    </div>${dialogSubmit("保存锁定")}</form>`);
}

function profile() {
  const info = data.profile;
  return pageHead("profile", "个人中心", `${account.name} · ${account.department}`) +
    panel("联系信息", body(`<form id="profile-form"><div class="form-grid">
      ${field("联系电话", `<input type="tel" name="phone" maxlength="20" value="${escape(info.phone)}">`)}
      ${field("电子邮箱", `<input type="email" name="email" maxlength="64" value="${escape(info.email)}">`)}
      </div><p class="error" role="alert"></p><div class="actions form-actions spaced"><button class="button primary">保存联系信息</button></div></form>`)) +
    panel("修改密码", body(`<form id="password-form"><div class="form-grid">
      ${field("当前密码", '<input type="password" name="current" autocomplete="current-password" required>')}
      ${field("新密码（至少 6 位）", '<input type="password" name="password" minlength="6" autocomplete="new-password" required>')}
      ${field("确认新密码", '<input type="password" name="confirm" minlength="6" autocomplete="new-password" required>')}
      </div><p class="error" role="alert"></p><div class="actions form-actions spaced"><button class="button primary">修改密码</button></div></form>`));
}

function users() {
  return pageHead("users", "用户管理", "维护账号的角色、启用状态及密码。") +
    panel("账号列表", table(["账号", "姓名", "所属单位", "角色", "状态", "操作"], data.users.map(user =>
      [user.id, user.name, user.department, roles[user.role], user.enabled ? "已启用" : "已停用",
        button("编辑账号", "edit-user", user.id)])));
}

function editUser(user) {
  showDialog("编辑账号", `<form id="user-form" data-value="${user.id}"><div class="form-grid">
    ${field("账号", `<input value="${user.id}" readonly>`)}
    ${field("角色", `<select name="role">${options(Object.entries(roles), user.role)}</select>`)}
    ${field("账号状态", `<select name="enabled">${options([[1, "已启用"], [0, "已停用"]], Number(user.enabled))}</select>`)}
    ${field("重置密码（留空保留当前密码）", '<input type="password" name="password" minlength="6" autocomplete="new-password">')}
    </div>${dialogSubmit("保存账号")}</form>`);
}

function dictionary() {
  return pageHead("dictionary", "基础字典", "查看预约类型、场地类型及审批状态。") +
    panel("活动类型", body(data.activityTypes.join("、"))) +
    panel("场地类型", body([...new Set(data.venues.map(venue => venue.type))].map(escape).join("、"))) +
    panel("预约状态", body(Object.keys(states).map(status).join(" ")));
}

function audit() {
  return pageHead("audit", "审计日志", "查询申请、审批及管理操作记录。") +
    panel("操作记录", body(`<div class="toolbar"><input type="search" id="audit-query" aria-label="筛选审计日志"
    placeholder="申请编号、操作人或操作"></div><div id="audit-results">${auditTable()}</div>`));
}

function auditTable(query = "") {
  const records = data.audit.filter(row => `${row.code || ""} ${row.by} ${row.title} ${row.comment}`.toLowerCase().includes(query));
  return table(["时间", "申请编号", "操作人", "操作", "意见"], records.map(row =>
    [row.at, row.code || "—", escape(row.by), escape(row.title), escape(row.comment || "—")]));
}

function reset() {
  return pageHead("reset", "数据初始化", "恢复预置的演示账号、场地、物资及预约记录。") +
    panel("恢复演示数据", body(button("恢复演示数据", "ask-reset", "", "danger")));
}

function confirmAction(title, message, label, action, value) {
  showDialog(title, `<p>${message}</p><p class="error" role="alert"></p><div class="actions form-actions">
    ${button("返回", "close")}${button(label, action, value, "danger")}</div>`);
}

const pages = {
  home, venues: venuePage, booking, history, approvals, assets, locks, profile, users, audit, dictionary, reset,
  schedule: () => pageHead("schedule", "排期日历", "查看各场地的预约、审核中时段和临时锁定。") +
    panel("场地时段", body(scheduleView())),
};

const actions = {
  close: () => dialog.close(),
  logout: () => mutate("/auth/logout", { signOut: true }),
  refresh: refreshWorkspace,
  day: date => { schedule.date = date; render(); },
  "venue-page": page => filterVenues(Number(page)),
  venue: id => venueDetail(venueById(id)),
  "new-venue": () => editVenue(),
  "edit-venue": id => editVenue(venueById(id)),
  "venue-schedule": id => { schedule.venue = id; if (dialog.open) dialog.close(); go("schedule"); },
  "venue-booking": id => { draft = { venue: id }; dialog.close(); go("booking"); },
  "save-draft": () => saveBooking(false),
  record: id => recordDetail(reservationById(id)),
  "edit-record": id => { draft = { ...reservationById(id) }; dialog.close(); go("booking"); },
  "delete-record": id => confirmAction("删除草稿", "删除后无法恢复这份草稿。", "确认删除", "confirm-delete", id),
  "confirm-delete": id => mutate("/reservations/" + id, { method: "DELETE", error: dialog.querySelector(".error") }),
  "ask-cancel": id => confirmAction("取消预约", "取消后将释放预约的场地时段及已占用的物资。", "确认取消", "cancel-record", id),
  "cancel-record": id => mutate(`/reservations/${id}/cancel`, { error: dialog.querySelector(".error") }),
  reschedule: id => reschedule(reservationById(id)),
  "new-equipment": () => editEquipment(),
  "edit-equipment": id => editEquipment(data.equipment.find(item => item.id === id)),
  "new-lock": newLock,
  "lock-detail": id => {
    const item = data.locks.find(lock => lock.id === Number(id));
    showDialog("不可预约时段", facts([["场地", venueById(item.venue).name], ["日期", item.date], ["时段", range(item)], ["原因", item.reason]]));
  },
  "ask-unlock": id => confirmAction("解除锁定", "解除后该时段将按常规开放及排期显示。", "确认解除", "unlock", id),
  unlock: id => mutate("/venue-locks/" + id, { method: "DELETE", error: dialog.querySelector(".error") }),
  "edit-user": id => editUser(userById(id)),
  "ask-reset": () => confirmAction("恢复演示数据", "现有数据库中的账号修改、预约和审计记录将被清除。", "确认恢复", "confirm-reset"),
  "confirm-reset": () => mutate("/admin/reset-demo", { error: dialog.querySelector(".error"), signOut: true }),
};

document.addEventListener("click", event => {
  if (event.target.closest(".skip-link")) {
    event.preventDefault();
    (account ? content : byId("login")).focus();
    return;
  }
  const control = event.target.closest("[data-action]");
  if (control) actions[control.dataset.action](control.dataset.value);
});

document.addEventListener("input", event => {
  const { target } = event;
  if (target.closest("#venue-filters")) filterVenues();
  if (target.closest("#booking-form")) {
    byId("booking-error").textContent = "";
    syncBooking();
  }
  if (["record-query", "record-status"].includes(target.id)) historyRows();
  if (target.id === "audit-query") byId("audit-results").innerHTML = auditTable(target.value.trim().toLowerCase());
});

document.addEventListener("change", ({ target }) => {
  if (target.id.startsWith("schedule-")) {
    if (target.value) schedule[target.id.slice("schedule-".length)] = target.value;
    render();
    byId(target.id)?.focus();
  }
  if (target.id === "approval-sort") {
    const records = sorted(pending());
    if (target.value === "date") records.sort((first, second) => `${first.date}${first.start}`.localeCompare(`${second.date}${second.start}`));
    byId("approval-results").innerHTML = bookingRows(records, true);
  }
  if (target.form?.id === "inventory-form") {
    inventory = Object.fromEntries(new FormData(target.form));
    syncInventory();
  }
});

document.addEventListener("submit", event => {
  event.preventDefault();
  const form = event.target;
  const values = Object.fromEntries(new FormData(form));
  const error = form.querySelector(".error");
  const id = form.dataset.value;
  switch (form.id) {
    case "booking-form":
      saveBooking(true);
      break;
    case "approve-form":
      approve(form, event.submitter?.value || "approve");
      break;
    case "login-form":
      mutate("/auth/login", { payload: values, error, page: "home", message: "已登录。" });
      break;
    case "venue-form":
      mutate(id ? "/venues/" + encodeURIComponent(id) : "/venues", {
        method: id ? "PATCH" : "POST", error, payload: { ...values, maintenance: values.maintenance === "1" },
      });
      break;
    case "equipment-form":
      mutate(id ? "/equipments/" + encodeURIComponent(id) : "/equipments", {
        method: id ? "PATCH" : "POST", error, payload: { ...values, enabled: values.enabled === "1" },
      });
      break;
    case "lock-form":
      mutate("/venue-locks", { payload: values, error });
      break;
    case "reschedule-form":
      mutate(`/reservations/${id}/schedule`, { method: "PATCH", payload: values, error });
      break;
    case "profile-form":
      mutate("/auth/profile", { method: "PATCH", payload: values, error });
      break;
    case "password-form":
      mutate("/auth/password", { method: "PATCH", payload: values, error });
      break;
    case "user-form":
      mutate("/admin/users/" + encodeURIComponent(id), {
        method: "PATCH", payload: { ...values, enabled: values.enabled === "1" }, error,
      });
      break;
  }
});

async function refreshWorkspace() {
  if (writing) {
    render();
    return;
  }
  try {
    if (await loadWorkspace()) render();
  } catch (error) {
    if (error.status === 401) showLogin();
    else {
      if (!account) showLogin();
      notify(error.message);
    }
  }
}

window.addEventListener("hashchange", () => {
  if (!account || ["#booking", "#profile"].includes(location.hash)) render();
  else refreshWorkspace();
});
refreshWorkspace();
