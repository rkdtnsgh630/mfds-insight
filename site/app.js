/* MFDS INSIGHT — 정적 사이트. data/*.json(수집 DB에서 생성)만 읽는다. 인증키·API 호출 없음. */
(function () {
"use strict";

// ---------- 공통 ----------
const $ = (s, el) => (el || document).querySelector(s);
const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const fmt = n => (n == null || n === "" ? "–" : Math.round(n).toLocaleString("ko-KR"));
const wonM = v => { // 백만원 단위 값 → 읽기 쉬운 원화
  if (v == null) return "–";
  if (v >= 1e6) return (v / 1e6).toFixed(2) + "조원";
  if (v >= 100) return fmt(v / 100) + "억원";
  return fmt(v) + "백만원";
};
const usd = v => {
  if (v == null) return "–";
  if (v >= 1e8) return (v / 1e8).toFixed(1) + "억 달러";
  if (v >= 1e4) return fmt(v / 1e4) + "만 달러";
  return fmt(v) + " 달러";
};
const shard = k => { const d = String(k).replace(/\D/g, ""); return (d.slice(-2) || "0").padStart(2, "0"); };
const fmtBiz = b => b && b.length === 10 ? `${b.slice(0, 3)}-${b.slice(3, 5)}-${b.slice(5)}` : (b || "");

const cache = {};
function load(path) {
  if (!cache[path]) cache[path] = fetch("data/" + path).then(r => { if (!r.ok) throw new Error(path + " " + r.status); return r.json(); });
  return cache[path];
}
let META = null;
const API = id => (META && META.apis.find(a => a.id === id)) || { name: id, url: "#" };

function toast(t) { const el = $("#toast"); el.textContent = t; el.hidden = false; clearTimeout(toast.t); toast.t = setTimeout(() => el.hidden = true, 3000); }

// 데이터별 자료 기간: 날짜 필드가 있는 데이터는 첫~마지막 날짜, 없는 데이터는 '현재 등록 현황'
const PERIOD = {
  drug_permit: { n: "제품허가", basis: "허가일", note: "현재 조회되는 품목 기준" },
  drug_permit_detail: { n: "허가 상세", same: "drug_permit" },
  production_import: { n: "생산·수입실적", basis: "실적연도", note: "연간 자료" },
  recall_drug: { n: "회수·판매중지", basis: "회수명령일" },
  admin_action: { n: "행정처분", basis: "처분확정일", note: "공개 기간이 남은 처분만" },
  supply_suspend: { n: "공급중단", basis: "신고일" },
  supply_shortage: { n: "공급부족", basis: "신고일" },
  safety_letter: { n: "안전성서한", basis: "공고일" },
  company_list: { n: "업체허가", now: 1 },
  gmp: { n: "GMP 적합판정", now: 1 },
  overseas_mfr: { n: "해외제조소", now: 1 },
};
function periodRow(ids) {
  const items = ids.map(id => {
    const p = PERIOD[id]; if (!p) return "";
    if (p.same) return "";
    const c = META.coverage && META.coverage[id];
    const range = p.now ? `<b>현재 등록 현황</b>` : c ? `<b>${esc(c[0])} ~ ${esc(c[1])}</b>` : `<b>–</b>`;
    const sub = p.now ? "기간 구분 없음" : [p.basis && p.basis + " 기준", p.note].filter(Boolean).join(", ");
    return `<span class="per"><span class="pn">${esc(p.n)}</span> ${range}${sub ? ` <span class="ps">${esc(sub)}</span>` : ""}</span>`;
  }).filter(Boolean);
  return items.length ? `<div class="periods" aria-label="자료 기간"><span class="pl">자료 기간</span>${items.join("")}</div>` : "";
}
function head(title, crumb, srcIds, periodIds) {
  const src = (srcIds || []).map(id => `<a href="${esc(API(id).url)}" target="_blank" rel="noopener">${esc(API(id).name)}</a>`).join(" · ");
  return `<div class="pagehead"><div><div class="crumb">${crumb || "MFDS INSIGHT"}</div><h1>${title}</h1></div>
    <div class="meta"><span>데이터 기준일 <b>${esc(META.as_of)}</b></span>${src ? `<span>출처 <b>${src}</b></span>` : ""}</div></div>`
    + periodRow(periodIds || srcIds || []);
}
const srcline = (ids, extra) => {
  return `<div class="srcline">출처: ${ids.map(id => `<a href="${esc(API(id).url)}" target="_blank" rel="noopener">${esc(API(id).name)}</a>`).join(" · ")}${extra ? " · " + extra : ""}</div>`;
};
const panel = (title, body, sub) => `<section class="panel"><div class="ph"><div><h2>${title}</h2>${sub ? `<div class="src">${sub}</div>` : ""}</div></div>${body}</section>`;
const kpi = (label, value, sub, href) => `<div class="kpi"><div class="l">${label}</div>${href ? `<a class="v" href="${href}">${value}</a>` : `<div class="v">${value}</div>`}<div class="s">${sub || ""}</div></div>`;
const linkDrug = (seq, name) => seq ? `<a class="link" href="#drug/${esc(seq)}">${esc(name || seq)}</a>` : esc(name);
const linkCo = (biz, name) => biz ? `<a class="link" href="#company/${esc(biz)}">${esc(name || fmtBiz(biz))}</a>` : esc(name);
const statusTag = s => `<span class="st ${s === "정상" ? "ok" : (/취소|취하/.test(s) ? "bad" : "")}">${esc(s || "–")}</span>`;
const empty = t => `<div class="empty">${t || "해당 기록이 없습니다."}</div>`;

// ---------- 차트 (SVG, 외부 라이브러리 없음) ----------
function niceStep(r) { if (!(r > 0)) return 1; const p = Math.pow(10, Math.floor(Math.log10(r))); const n = r / p; return (n <= 1 ? 1 : n <= 2 ? 2 : n <= 5 ? 5 : 10) * p; }
function tick(v, f) { if (v === 0) return "0"; return f ? f(v) : (v >= 1000 ? fmt(v) : String(Math.round(v * 10) / 10)); }
// 차트는 자리만 먼저 만들고, 화면에 붙은 뒤 실제 너비(px)로 그린다 → 패널 너비와 상관없이 글자 크기가 같다
const CHARTS = new Map();
let CID = 0;
function deferChart(fn, after) { const id = "c" + (++CID); CHARTS.set(id, fn); return `<div class="chart" data-cid="${id}"></div>${after || ""}`; }
function drawCharts(root) {
  (root || document).querySelectorAll(".chart[data-cid]").forEach(el => {
    const fn = CHARTS.get(el.dataset.cid); if (!fn) return;
    const W = Math.max(280, Math.round(el.clientWidth));
    if (el._w === W) return;
    el._w = W; el.innerHTML = fn(W);
  });
}
let RZ; window.addEventListener("resize", () => { clearTimeout(RZ); RZ = setTimeout(() => drawCharts(), 150); });

function lineChart(xs, series, o = {}) {
  const all = series.flatMap(s => s.v).filter(v => v != null);
  if (!xs.length || !all.length) return empty("표시할 데이터가 없습니다.");
  const legend = series.length > 1 ? `<div class="legend">${series.map(s => `<span style="--c:${s.c}">${esc(s.n)}</span>`).join("")}</div>` : "";
  return deferChart(W => lineSvg(W, xs, series, o, all), legend);
}
function lineSvg(W, xs, series, o, all) {
  const H = o.h || 210, L = o.L || 66, R = 14, T = 12, B = 26;
  const mx = Math.max(1, ...all), step = niceStep(mx / 4), top = Math.ceil(mx / step) * step;
  const x = i => xs.length === 1 ? (L + W - R) / 2 : L + (W - L - R) * i / (xs.length - 1);
  const y = v => T + (H - T - B) * (1 - v / top);
  let g = "";
  for (let v = 0; v <= top + 1e-9; v += step) g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${tick(v, o.tf)}</text>`;
  const every = Math.ceil(xs.length / Math.max(4, Math.floor((W - L) / 56)));
  xs.forEach((t, i) => { if (i % every === 0 || i === xs.length - 1) g += `<text x="${x(i)}" y="${H - 6}" text-anchor="middle">${esc(o.xf ? o.xf(t) : t)}</text>`; });
  series.forEach(s => {
    const pts = s.v.map((v, i) => `${x(i)},${y(v || 0)}`).join(" ");
    if (s.area) g += `<polygon points="${x(0)},${y(0)} ${pts} ${x(s.v.length - 1)},${y(0)}" fill="${s.c}" opacity=".12"/>`;
    g += `<polyline points="${pts}" fill="none" stroke="${s.c}" stroke-width="2.2" stroke-linejoin="round"/>`;
    s.v.forEach((v, i) => { g += `<circle cx="${x(i)}" cy="${y(v || 0)}" r="${i === s.v.length - 1 ? 4 : 2.5}" fill="${s.c}" stroke="var(--panel)" stroke-width="1.5"><title>${esc(xs[i])} ${esc(s.n || "")}: ${esc(o.vf ? o.vf(v) : fmt(v))}</title></circle>`; });
  });
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="${esc(o.label || "시계열 그래프")}">${g}</svg>`;
}
function colChart(xs, vals, o = {}) {
  if (!xs.length) return empty("표시할 데이터가 없습니다.");
  return deferChart(W => colSvg(W, xs, vals, o));
}
function colSvg(W, xs, vals, o) {
  const H = o.h || 200, L = o.L || 66, R = 10, T = 10, B = 26;
  const mx = Math.max(1, ...vals), step = niceStep(mx / 4), top = Math.ceil(mx / step) * step;
  const bw = (W - L - R) / xs.length, y = v => T + (H - T - B) * (1 - v / top);
  let g = "";
  for (let v = 0; v <= top + 1e-9; v += step) g += `<line x1="${L}" x2="${W - R}" y1="${y(v)}" y2="${y(v)}" stroke="var(--line)"/><text x="${L - 8}" y="${y(v) + 4}" text-anchor="end">${tick(v, o.tf)}</text>`;
  const every = Math.ceil(xs.length / Math.max(4, Math.floor((W - L) / 48)));
  const bwMax = 64, pad = bw > bwMax / 0.68 ? (bw - bwMax) / 2 : bw * 0.16, bwid = Math.min(bw * 0.68, bwMax);
  vals.forEach((v, i) => {
    const x = L + i * bw + pad;
    g += `<rect x="${x}" y="${y(v)}" width="${bwid}" height="${Math.max(0, y(0) - y(v))}" rx="2" fill="${o.c || "var(--accent)"}" opacity="${i === vals.length - 1 ? 1 : .75}"><title>${esc(xs[i])}: ${esc(o.vf ? o.vf(v) : fmt(v))}</title></rect>`;
    if (i % every === 0 || i === vals.length - 1) g += `<text x="${x + bwid / 2}" y="${H - 6}" text-anchor="middle">${esc(o.xf ? o.xf(xs[i]) : xs[i])}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="${esc(o.label || "막대그래프")}">${g}</svg>`;
}
function barChart(items, o = {}) {
  if (!items.length) return empty("표시할 데이터가 없습니다.");
  return deferChart(W => barSvg(W, items, o));
}
function barSvg(W, items, o) {
  const L = o.L || (W >= 560 ? 170 : 120), R = 96, rowH = 24, H = items.length * rowH + 8, mx = Math.max(1, ...items.map(d => d.v));
  const maxc = W >= 560 ? 16 : 10;
  let g = "";
  items.forEach((d, i) => {
    const y = 4 + i * rowH, w = (W - L - R) * d.v / mx;
    const label = d.k.length > maxc ? d.k.slice(0, maxc - 1) + "…" : d.k;
    const text = `<text x="${L - 8}" y="${y + rowH / 2 + 4}" text-anchor="end" style="fill:var(--fg2)">${esc(label)}<title>${esc(d.k)}</title></text>`;
    g += (d.href ? `<a href="${esc(d.href)}">${text}</a>` : text)
      + `<rect x="${L}" y="${y + 4}" width="${Math.max(2, w)}" height="${rowH - 8}" rx="3" fill="${o.c || "var(--accent)"}"><title>${esc(d.k)}: ${esc(o.vf ? o.vf(d.v) : fmt(d.v))}</title></rect>`
      + `<text x="${L + w + 6}" y="${y + rowH / 2 + 4}">${esc(o.vf ? o.vf(d.v) : fmt(d.v))}</text>`;
  });
  return `<svg viewBox="0 0 ${W} ${H}" width="100%" height="${H}" role="img" aria-label="${esc(o.label || "막대그래프")}">${g}</svg>`;
}

// ---------- 표 (검색·필터·정렬·페이지·CSV) ----------
let TID = 0;
function table(cfg) {
  const id = "t" + (++TID), per = cfg.per || 15;
  const st = { q: "", f: (cfg.filters || []).map(() => ""), sort: cfg.sort, dir: cfg.dir || -1, page: 0 };
  const txt = cfg.text ? cfg.rows.map(r => cfg.text(r).toLowerCase()) : null;
  function rows() {
    const q = st.q.trim().toLowerCase();
    let idx = [];
    for (let i = 0; i < cfg.rows.length; i++) {
      const r = cfg.rows[i];
      if (q && txt && !txt[i].includes(q)) continue;
      if (cfg.filters && cfg.filters.some((f, j) => st.f[j] && f.get(r) !== st.f[j])) continue;
      idx.push(r);
    }
    const col = cfg.cols.find(c => c.k === st.sort);
    if (col) idx.sort((a, b) => { let va = col.v(a), vb = col.v(b); if (va == null || va === "") va = -Infinity; if (vb == null || vb === "") vb = -Infinity; return (va > vb ? 1 : va < vb ? -1 : 0) * st.dir; });
    return idx;
  }
  function draw() {
    const r = rows(), pages = Math.max(1, Math.ceil(r.length / per));
    st.page = Math.min(st.page, pages - 1);
    const sl = r.slice(st.page * per, st.page * per + per);
    $("#" + id + "-body").innerHTML = sl.map(x => "<tr>" + cfg.cols.map(c => `<td class="${c.n ? "n" : ""}${c.wrap ? " wrap" : ""}${c.clip ? " clip" : ""}"${c.clip ? ` title="${esc(c.v(x))}"` : ""}>${c.h ? c.h(x) : esc(c.v(x))}</td>`).join("") + "</tr>").join("")
      || `<tr><td colspan="${cfg.cols.length}" style="color:var(--fg3);padding:22px 12px">조건에 맞는 결과가 없습니다. 검색어나 필터를 바꿔 보세요.</td></tr>`;
    $("#" + id + "-info").textContent = `${fmt(r.length)}건 중 ${r.length ? st.page * per + 1 : 0}–${st.page * per + sl.length}`;
    document.querySelectorAll(`#${id} th button`).forEach(b => { const k = b.dataset.k; b.querySelector("i").textContent = k === st.sort ? (st.dir > 0 ? "▲" : "▼") : ""; b.closest("th").setAttribute("aria-sort", k === st.sort ? (st.dir > 0 ? "ascending" : "descending") : "none"); });
    $("#" + id + "-prev").disabled = st.page === 0; $("#" + id + "-next").disabled = st.page >= pages - 1;
  }
  const filt = (cfg.filters || []).map((f, j) => `<select id="${id}-f${j}" aria-label="${esc(f.label)}"><option value="">${esc(f.label)} 전체</option>${f.opts.map(o => `<option>${esc(o)}</option>`).join("")}</select>`).join("");
  const html = `<div id="${id}"><div class="filters">${cfg.text ? `<input id="${id}-q" type="search" placeholder="${esc(cfg.ph || "표 안에서 검색")}" value="${esc(cfg.q || "")}">` : ""}${filt}
    <span style="flex:1"></span><button class="btn" id="${id}-dl" type="button">CSV 다운로드</button></div>
    <div class="tbl-wrap"><table><thead><tr>${cfg.cols.map(c => `<th class="${c.n ? "n" : ""}" aria-sort="none"><button type="button" data-k="${c.k}">${esc(c.t)}<i aria-hidden="true"></i></button></th>`).join("")}</tr></thead><tbody id="${id}-body"></tbody></table></div>
    <div class="pager"><span id="${id}-info"></span><span class="dl"><button class="btn" id="${id}-prev" type="button">이전</button><button class="btn" id="${id}-next" type="button">다음</button></span></div></div>`;
  function bind() {
    if (cfg.q) st.q = cfg.q;
    const q = $("#" + id + "-q"); let tmr;
    if (q) q.addEventListener("input", () => { clearTimeout(tmr); tmr = setTimeout(() => { st.q = q.value; st.page = 0; draw(); }, 150); });
    (cfg.filters || []).forEach((f, j) => $("#" + id + "-f" + j).addEventListener("change", e => { st.f[j] = e.target.value; st.page = 0; draw(); }));
    document.querySelectorAll(`#${id} th button`).forEach(b => b.addEventListener("click", () => { const k = b.dataset.k; if (st.sort === k) st.dir *= -1; else { st.sort = k; st.dir = -1; } draw(); }));
    $("#" + id + "-prev").addEventListener("click", () => { st.page--; draw(); });
    $("#" + id + "-next").addEventListener("click", () => { st.page++; draw(); });
    $("#" + id + "-dl").addEventListener("click", () => {
      const r = rows();
      const csv = "﻿" + [cfg.cols.map(c => c.t).join(",")].concat(r.map(x => cfg.cols.map(c => '"' + String(c.v(x) == null ? "" : c.v(x)).replace(/"/g, '""') + '"').join(","))).join("\r\n");
      const a = document.createElement("a");
      a.href = URL.createObjectURL(new Blob([csv], { type: "text/csv;charset=utf-8" }));
      a.download = `${cfg.csv || "mfds-insight"}_${META.as_of}.csv`;
      document.body.appendChild(a); a.click(); a.remove();
      toast(`${fmt(r.length)}행을 CSV로 내려받았습니다 (기준일 ${META.as_of}).`);
    });
    draw();
  }
  return { html, bind };
}
function tabs(defs) { // defs: [{k, t, html, bind}]
  const id = "tb" + (++TID);
  const html = `<div><div class="tabs" role="tablist" id="${id}">${defs.map((d, i) => `<button role="tab" aria-selected="${i === 0}" data-i="${i}">${esc(d.t)}</button>`).join("")}</div><div id="${id}-c"></div></div>`;
  function show(i) {
    document.querySelectorAll(`#${id} button`).forEach(b => b.setAttribute("aria-selected", String(+b.dataset.i === i)));
    const d = defs[i]; $("#" + id + "-c").innerHTML = d.html; if (d.bind) d.bind(); drawCharts($("#" + id + "-c"));
  }
  return { html, bind() { document.querySelectorAll(`#${id} button`).forEach(b => b.addEventListener("click", () => show(+b.dataset.i))); show(0); } };
}

// ---------- 화면 ----------
const V = {};

V.dashboard = async () => {
  const d = await load("dashboard.json"), k = d.kpi, t = d.trend;
  const feed = (rows, f) => rows.length ? `<div class="feed">${rows.map(f).join("")}</div>` : empty();
  const r = (when, title, pill) => `<div class="r"><span class="when">${esc(when)}</span><span class="t">${title}</span>${pill || ""}</div>`;
  const html = head("종합 대시보드", "MFDS INSIGHT", [], ["drug_permit", "recall_drug", "admin_action", "supply_suspend", "supply_shortage", "safety_letter"]) + `
  <div class="kpis">
    ${kpi("유효 허가 품목", fmt(k.items_active), `전체 ${fmt(k.items_total)}개 중 상태 '정상'`, "#drugs")}
    ${kpi("품목 보유 업체", fmt(k.companies_with_items), `연결된 업체 ${fmt(k.companies_total)}곳 (사업자번호 기준)`, "#companies")}
    ${kpi("최근 30일 신규 허가", fmt(k.new_permits_30), `같은 기간 취하·만료 등 ${fmt(k.new_cancels_30)}건`)}
    ${kpi("최근 30일 회수·판매중지", fmt(k.recalls_30), `공개 누적 ${fmt(k.recalls_total)}건`, "#supply")}
    ${kpi("최근 30일 행정처분", fmt(k.admins_30), `공개 중 ${fmt(k.admins_total)}건`, "#regulation")}
    ${kpi("최근 30일 공급중단·부족", fmt(k.suspends_30 + k.shortages_30), `중단 ${fmt(k.suspends_30)} · 부족 ${fmt(k.shortages_30)}건`, "#supply")}
  </div>
  <div class="notice small">'최근 30일'은 ${esc(META.since30)} ~ ${esc(META.as_of)} 기간이며, 각 API의 날짜 필드(허가일자·회수명령일·처분확정일·신고일)를 기준으로 셉니다.</div>
  <div class="grid2">
    ${panel("월별 신규 허가 품목 수 (최근 24개월)", lineChart(t.permits.x, [{ n: "신규 허가", v: t.permits.y, c: "var(--accent)", area: true }], { xf: x => x.slice(2).replace("-", "."), label: "월별 신규 허가" }) + srcline(["drug_permit"], `허가일자 기준 · 마지막 달은 ${esc(META.as_of)}까지`))}
    ${panel("월별 안전·규제 건수", lineChart(t.recalls.x, [
      { n: "회수·판매중지", v: t.recalls.y, c: "var(--bad)" }, { n: "행정처분", v: t.admins.y, c: "var(--fg3)" }, { n: "공급중단", v: t.suspends.y, c: "var(--warn)" }],
      { xf: x => x.slice(2).replace("-", "."), label: "월별 안전·규제 건수" }) + srcline(["recall_drug", "admin_action", "supply_suspend"], "마지막 달은 기준일까지"))}
  </div>
  <div class="grid2">
    ${panel("최근 신규 허가", feed(d.new_permits.slice(0, 8), x => r(x[4], `${linkDrug(x[0], x[1])} <span class="muted">· ${linkCo(x[3], x[2])}</span>`, `<span class="pill p-new">${esc(x[5] || x[6])}</span>`)) + srcline(["drug_permit"]))}
    ${panel("최근 회수·판매중지", feed(d.recalls, x => r(x[0], `${linkDrug(x[4], x[1])} <span class="muted">· ${linkCo(x[3], x[2])} — ${esc(x[5])}</span>`, x[6] === "Y" ? `<span class="pill p-bad">강제</span>` : `<span class="pill p-mute">강제 아님</span>`)) + srcline(["recall_drug"]))}
    ${panel("최근 행정처분", feed(d.admins, x => r(x[0], `${linkCo(x[2], x[1])} <span class="muted">${x[3] ? "· " + esc(x[3]) : ""}</span>`, `<span class="pill p-mute">${esc(x[4])}</span>`)) + srcline(["admin_action"], "유형은 처분명 문구로 분류"))}
    ${panel("최근 공급중단·공급부족 신고", feed(d.suspends.map(x => ({ x, k: "중단" })).concat(d.shortages.map(x => ({ x, k: "부족" }))).sort((a, b) => b.x[0] < a.x[0] ? -1 : 1).slice(0, 8),
      o => r(o.x[0], `${linkDrug(o.x[4], o.x[1])} <span class="muted">· ${linkCo(o.x[3], o.x[2])}</span>`, `<span class="pill p-warn">${o.k}</span>`)) + srcline(["supply_suspend", "supply_shortage"]))}
    ${panel("최근 허가 취하·만료", feed(d.new_cancels.slice(0, 8), x => r(x[4], `${linkDrug(x[0], x[1])} <span class="muted">· ${linkCo(x[3], x[2])}</span>`, `<span class="pill p-mute">${esc(x[5])}</span>`)) + srcline(["drug_permit"], "취하일자 기준"))}
    ${panel("최근 안전성서한", feed(d.letters, x => r(x[0], x[2] ? `<a class="link" href="${esc(x[2])}" target="_blank" rel="noopener">${esc(x[1])}</a>` : esc(x[1]))) + srcline(["safety_letter"]))}
  </div>
  ${panel("최근 변경 감지", d.changes_recent.length ? changeList(d.changes_recent) + `<div class="srcline"><a class="link" href="#changes">변경 모니터링에서 전체 보기 (${fmt(d.changes_total)}건)</a></div>`
    : empty("아직 감지된 변경이 없습니다. 변경 이력은 첫 전체 수집(기준선, 2026-11-18) 이후 매일 비교해 쌓입니다."))}`;
  return { html };
};

function changeList(rows) {
  const ty = { added: ["추가", "p-new"], updated: ["변경", "p-warn"], removed: ["조회 안 됨", "p-bad"], reappeared: ["다시 조회", "p-ok"] };
  return `<div class="feed">${rows.map(x => {
    const [lab, cls] = ty[x[2]] || [x[2], "p-mute"];
    const target = x[6] ? linkDrug(x[6].split(",")[0], x[4] || x[3]) : (x[5] ? linkCo(x[5], x[4] || x[3]) : esc(x[4] || x[3]));
    return `<div class="r"><span class="when">${esc(x[0])}</span><span class="t">${target} <span class="muted">· ${esc(API(x[1]).name)}${x[7] && x[7].length ? " · 바뀐 항목: " + esc(x[7].join(", ")) : ""}</span></span><span class="pill ${cls}">${lab}</span></div>`;
  }).join("")}</div>`;
}

// 목록용 소재지: 업체허가 주소(r[2]) + GMP 공장 지역(r[14])을 시·도+시·군 단위로 합침
function locList(r) {
  const out = [];
  [String(r[2] || "").replace(/\s*외 \d+곳$/, "")].concat(String(r[14] || "").split(" · ")).forEach(a => {
    const k = a.split(/\s+/).filter(Boolean).slice(0, 2).join(" ");
    if (k && !out.includes(k)) out.push(k);
  });
  return out;
}

V.companies = async () => {
  const c = await load("companies_index.json"), ly = c.latest_year;
  const t = table({
    rows: c.rows, sort: "active", csv: "업체목록", ph: "업체명, 사업자번호, 지역",
    text: r => [r[1], r[0], fmtBiz(r[0]), r[2], r[13], r[14]].join(" "),
    filters: [{ label: "허가 품목", get: r => r[4] > 0 ? "품목 있음" : "품목 없음", opts: ["품목 있음", "품목 없음"] },
      { label: "업종", get: r => (r[13] || "").split("·")[0] || "업체허가 목록에 없음", opts: [...new Set(c.rows.map(r => (r[13] || "").split("·")[0] || "업체허가 목록에 없음"))].sort() }],
    cols: [
      { k: "name", t: "업체명", v: r => r[1], h: r => linkCo(r[0], r[1]) },
      { k: "biz", t: "사업자번호", v: r => fmtBiz(r[0]) },
      { k: "region", t: "소재지 (업체허가·GMP 공장)", v: r => locList(r).join(" · "), h: r => { const l = locList(r); return l.length ? `<span title="${esc(l.join(" · "))}">${esc(l[0])}${l.length > 1 ? ` <span class="muted">외 ${l.length - 1}곳</span>` : ""}</span>` : "–"; } },
      { k: "active", t: "유효 품목", v: r => r[3], n: 1, h: r => fmt(r[3]) },
      { k: "total", t: "전체 품목", v: r => r[4], n: 1, h: r => fmt(r[4]) },
      { k: "prod", t: `생산 ${ly} (백만원)`, v: r => r[5], n: 1, h: r => r[5] ? fmt(r[5]) : "–" },
      { k: "imp", t: `수입 ${ly} (달러)`, v: r => r[6], n: 1, h: r => r[6] ? fmt(r[6]) : "–" },
      { k: "gmp", t: "GMP", v: r => r[7], n: 1 },
      { k: "ovs", t: "해외제조소", v: r => r[8], n: 1 },
      { k: "adm", t: "행정처분", v: r => r[9], n: 1 },
      { k: "rec", t: "회수", v: r => r[10], n: 1 },
      { k: "sus", t: "공급중단", v: r => r[11], n: 1 },
    ],
  });
  const html = head("제약회사", "탐색", ["company_list", "drug_permit", "production_import"], ["company_list", "drug_permit", "production_import", "gmp", "overseas_mfr", "admin_action", "recall_drug", "supply_suspend"]) +
    `<div class="notice small">업체는 <b>사업자등록번호</b>로만 묶었습니다. 이름이 비슷해도 번호가 다르면 다른 업체로 표시합니다. 생산실적은 백만원, 수입실적은 달러 단위(공식 명세)라 서로 더하지 않습니다.</div>` +
    panel(`업체 목록 (${fmt(c.rows.length)}곳)`, t.html);
  return { html, bind: t.bind };
};

V.company = async biz => {
  const all = await load(`companies/${shard(biz)}.json`), c = all[biz];
  if (!c) return { html: head("업체를 찾을 수 없습니다", `<a class="link" href="#companies">제약회사</a>`) + empty(`사업자번호 ${esc(fmtBiz(biz))}에 해당하는 수집 기록이 없습니다.`) };
  const years = Object.keys(c.prod);
  const active = c.items.filter(i => i[4] === "정상").length;
  const ly = years[years.length - 1], lp = ly ? c.prod[ly] : null;
  const items = table({
    rows: c.items, sort: "date", csv: `${c.name}_품목`, ph: "품목명, 품목기준코드", per: 10,
    text: r => r[1] + " " + r[0],
    filters: [{ label: "상태", get: r => r[4], opts: [...new Set(c.items.map(r => r[4]))] }, { label: "구분", get: r => r[3], opts: ["전문", "일반"] }],
    cols: [{ k: "name", t: "품목명", v: r => r[1], h: r => linkDrug(r[0], r[1]) }, { k: "seq", t: "품목기준코드", v: r => r[0] },
      { k: "date", t: "허가일", v: r => r[2] }, { k: "spc", t: "전문/일반", v: r => r[3] }, { k: "st", t: "상태", v: r => r[4], h: r => statusTag(r[4]) }],
  });
  const tl = (rows, f) => rows.length ? `<div class="timeline">${rows.map(f).join("")}</div>` : empty();
  const tr = (d, tag, body) => `<div class="r"><span class="when">${esc(d)}</span><span>${tag}</span><span>${body}</span></div>`;
  const ovs = table({
    rows: c.overseas, sort: "country", dir: 1, csv: `${c.name}_해외제조소`, ph: "제조소명, 국가", per: 8,
    text: r => r.join(" "),
    cols: [{ k: "m", t: "해외 제조소", v: r => r[0] }, { k: "country", t: "국가", v: r => r[1] }, { k: "no", t: "제조소 번호", v: r => r[2] }],
  });
  // 소재지 = 업체허가 목록 주소 + GMP 공장 주소 (시·도 + 시·군 단위로 합쳐 중복 제거, 출처 표시)
  const locs = [];
  const addLoc = (addr, src) => {
    const k = String(addr || "").split(/\s+/).filter(Boolean).slice(0, 2).join(" ");
    if (!k) return;
    let e = locs.find(x => x.k === k); if (!e) { e = { k, src: [] }; locs.push(e); }
    if (!e.src.includes(src)) e.src.push(src);
  };
  (c.regions && c.regions.length ? c.regions : [c.region]).forEach(a => addLoc(a, c.region_from_admin ? "행정처분" : "업체허가"));
  c.gmp.forEach(g => addLoc(g[2], "GMP 공장"));
  const html = head(esc(c.name), `<a class="link" href="#companies">제약회사</a> / 업체 상세`, [], ["company_list", "drug_permit", "production_import", "gmp", "overseas_mfr", "admin_action", "recall_drug", "supply_suspend", "supply_shortage"]) + `
  <dl class="idgrid co">
    <div><dt>사업자등록번호</dt><dd>${esc(fmtBiz(biz))}</dd></div>
    <div><dt>소재지 (${locs.length}곳)</dt><dd>${locs.length ? locs.map(l => `${esc(l.k)} <span class="muted small">${esc(l.src.join("·"))}</span>`).join("<br>") : "–"}</dd></div>
    <div><dt>업종·허가</dt><dd>${c.licenses.length ? c.licenses.map(l => `${esc(l[0])} <span class="muted small">${esc(l[1] || "")}</span>`).join("<br>") : '<span class="muted">업체허가 목록에 없음</span>'}</dd></div>
    <div><dt>수집 데이터에 쓰인 상호</dt><dd>${c.names.map(esc).join("<br>")}</dd></div>
    <div class="full"><dt>GMP 적합판정 공장 (${c.gmp.length}건)</dt><dd>${c.gmp.length ? c.gmp.map(g => `${esc(g[2] || "주소 없음")} <span class="muted small">· ${esc(g[0])}${g[1] ? " · " + esc(g[1]) : ""} · 유효 ~${esc(g[3] || "–")}</span>`).join("<br>")
      + (c.gmp.length < 2 ? "" : `<p class="muted small note">공장 ${c.gmp.length}곳 모두 사업자번호 ${esc(fmtBiz(biz))} 하나로 등록되어 있어, 공장별 회수·처분 기록도 이 업체에 함께 모입니다.</p>`) : '<span class="muted">GMP 발급 기록 없음</span>'}</dd></div>
  </dl>
  <div class="kpis">
    ${kpi("유효 허가 품목", fmt(active), `전체 ${fmt(c.items.length)}개`)}
    ${kpi(`${ly || "최근"} 생산실적`, lp && lp.p ? wonM(lp.p) : "–", lp && lp.np ? `${fmt(lp.np)}건 집계` : "기록 없음")}
    ${kpi(`${ly || "최근"} 수입실적`, lp && lp.i ? usd(lp.i) : "–", lp && lp.ni ? `${fmt(lp.ni)}건 집계` : "기록 없음")}
    ${kpi("GMP 적합판정", fmt(c.gmp.length), "발급 현황")}
    ${kpi("행정처분 · 회수", `${fmt(c.admin.length)} · ${fmt(c.recall.length)}`, META.coverage && META.coverage.recall_drug ? `회수는 ${esc(META.coverage.recall_drug[0])} 이후 공개분` : "공개 중인 기록")}
    ${kpi("공급중단 · 부족", `${fmt(c.suspend.length)} · ${fmt(c.shortage.length)}`, "신고 기록")}
  </div>
  <div class="grid2">
    ${panel("연도별 생산실적 (백만원)", colChart(years, years.map(y => c.prod[y].p || 0), { vf: wonM, label: "연도별 생산실적" }) + srcline(["production_import"], "금액 단위 백만원"))}
    ${panel("연도별 수입실적 (달러)", colChart(years, years.map(y => c.prod[y].i || 0), { c: "var(--accent2)", vf: usd, tf: v => v >= 1e8 ? (v / 1e8) + "억" : v >= 1e4 ? fmt(v / 1e4) + "만" : fmt(v), label: "연도별 수입실적" }) + srcline(["production_import"], "금액 단위 달러"))}
  </div>
  ${panel(`허가 품목 (${fmt(c.items.length)})`, items.html)}
  <div class="grid2">
    ${panel(`행정처분 (${c.admin.length})`, tl(c.admin, x => tr(x[0], `<span class="pill p-mute">${esc(x[2])}</span>`, `${esc(x[3])}${x[1] ? `<div class="muted small">${esc(x[1])}</div>` : ""}`)) + srcline(["admin_action"]))}
    ${panel(`회수·판매중지 (${c.recall.length})`, tl(c.recall, x => tr(x[0], x[4] === "Y" ? `<span class="pill p-bad">강제</span>` : `<span class="pill p-mute">강제 아님</span>`, `${linkDrug(x[2], x[1])}<div class="muted small">${esc(x[3])}</div>`)) + srcline(["recall_drug"]))}
    ${panel(`공급중단 신고 (${c.suspend.length})`, tl(c.suspend, x => tr(x[0], `<span class="pill p-warn">${esc(x[3] || "중단")}</span>`, `${linkDrug(x[2], x[1])}<div class="muted small">중단일 ${esc(x[4] || "–")} · ${esc(x[5])}</div>`)) + srcline(["supply_suspend"]))}
    ${panel(`공급부족 신고 (${c.shortage.length})`, tl(c.shortage, x => tr(x[0], `<span class="pill p-warn">부족</span>`, `${linkDrug(x[2], x[1])}<div class="muted small">${esc(x[3])} · ${esc(x[4])}</div>`)) + srcline(["supply_shortage"]))}
    ${panel(`GMP 적합판정 (${c.gmp.length})`, tl(c.gmp, x => tr(x[3] ? "~" + x[3] : "–", `<span class="pill p-ok">${esc(x[0])}</span>`, `${esc(x[2])}${x[1] ? `<div class="muted small">${esc(x[1])}</div>` : ""}`)) + srcline(["gmp"], "날짜는 유효기간 만료일"))}
    ${panel(`해외 제조소 (${fmt(c.overseas_total)})`, c.overseas.length ? ovs.html + (c.overseas_total > c.overseas.length ? `<div class="srcline">상위 ${c.overseas.length}곳만 표시</div>` : "") : empty())}
  </div>`;
  return { html, bind() { items.bind(); if (c.overseas.length) ovs.bind(); } };
};

V.drugs = async q => {
  const d = await load("drugs_index.json"), rows = d.rows;
  const t = table({
    rows, sort: "permit", csv: "의약품목록", ph: "품목명, 업체명, 성분명, 품목기준코드, ATC", q,
    text: r => [r[1], r[2], r[7], r[8], r[0], r[9], r[3]].join(" "),
    filters: [{ label: "상태", get: r => r[6], opts: [...new Set(rows.map(r => r[6]))] },
      { label: "전문/일반", get: r => r[5], opts: ["전문", "일반"] },
      { label: "구분", get: r => r[10].includes("N") ? "신약" : (r[10].includes("R") ? "희귀의약품" : "기타"), opts: ["신약", "희귀의약품"] }],
    cols: [
      { k: "name", t: "품목명", v: r => r[1], h: r => linkDrug(r[0], r[1]) + (r[10].includes("N") ? '<span class="flag">신약</span>' : "") + (r[10].includes("R") ? '<span class="flag r">희귀</span>' : "") },
      { k: "entp", t: "업체", v: r => r[2], h: r => linkCo(r[3], r[2]) },
      { k: "ingr", t: "주성분", v: r => r[7] || r[8], clip: 1 },
      { k: "spc", t: "구분", v: r => r[5] },
      { k: "atc", t: "ATC", v: r => r[9] },
      { k: "permit", t: "허가일", v: r => r[4] },
      { k: "st", t: "상태", v: r => r[6], h: r => statusTag(r[6]) },
    ],
  });
  const html = head("의약품", "탐색", ["drug_permit", "drug_permit_detail"]) + panel(`허가 품목 (${fmt(rows.length)})`, t.html);
  return { html, bind: t.bind };
};

V.drug = async seq => {
  const det = await load(`drugs/${shard(seq)}.json`);
  const d = det[seq];
  let r = d && d.row;
  if (d && !r) r = (await load("drugs_index.json")).rows.find(x => x[0] === seq); // 이전 형식 데이터 대비
  if (!r || !d) return { html: head("품목을 찾을 수 없습니다", `<a class="link" href="#drugs">의약품</a>`) + empty(`품목기준코드 ${esc(seq)}에 해당하는 수집 기록이 없습니다.`) };
  const rel = d.rel || {}, prod = d.prod || {};
  const years = Object.keys(prod);
  const tl = (rows, f) => rows && rows.length ? `<div class="timeline">${rows.map(f).join("")}</div>` : empty();
  const tr = (dt, tag, body) => `<div class="r"><span class="when">${esc(dt)}</span><span>${tag}</span><span>${body}</span></div>`;
  const doc = (u, t) => u ? `<a class="btn" href="${esc(u)}" target="_blank" rel="noopener">${t}</a>` : "";
  const field = (t, v) => `<div><dt>${t}</dt><dd>${v || '<span class="muted">–</span>'}</dd></div>`;
  const prodRows = years.flatMap(y => prod[y].map(p => [y, p[0], p[1]]));
  const html = head(esc(r[1]) + (r[10].includes("N") ? ' <span class="flag">신약</span>' : "") + (r[10].includes("R") ? ' <span class="flag r">희귀</span>' : ""),
    `<a class="link" href="#drugs">의약품</a> / 품목 상세`, ["drug_permit", "drug_permit_detail"], ["drug_permit", "production_import", "recall_drug", "supply_suspend", "supply_shortage", "admin_action"]) + `
  <dl class="idgrid">
    ${field("업체", linkCo(r[3], r[2]))}
    ${field("품목기준코드", esc(r[0]))}
    ${field("상태", statusTag(r[6]) + (r[12] ? ` <span class="muted small">${esc(r[12])}</span>` : ""))}
    ${field("허가일 · 구분", `${esc(r[4])} · ${esc(r[11])}`)}
    ${field("전문/일반", esc(r[5]))}
    ${field("ATC 코드", esc(r[9]))}
    ${field("주성분", esc(r[7] || d.ingr_eng))}
    ${field("영문 성분", esc(r[8]))}
    ${field("영문 제품명", esc(d.eng))}
    ${field("분류", esc(d.type))}
    ${field("품목허가번호", esc(d.permit_no))}
    ${field("보험코드(EDI)", esc(d.edi))}
    ${field("위탁제조업체", esc(d.cnsgn))}
    ${field("마약류 구분", esc(d.narcotic))}
    ${field("재심사", esc([d.reexam, d.reexam_date].filter(Boolean).join(" · ")))}
    ${field("저장방법", esc(d.storage))}
    ${field("유효기간", esc(d.valid))}
    ${field("포장단위", esc(d.pack))}
    ${field("성상", esc(d.chart))}
    ${field("원료·분량", esc((d.material || "").replace(/\|/g, " · ")))}
    ${field("최근 변경일 · 변경 내용", `${esc(d.change_date)}${d.change_hist ? `<div class="muted small">${esc(d.change_hist)}</div>` : ""}`)}
  </dl>
  ${d.doc_ee || d.doc_ud || d.doc_nb ? panel("허가 문서 (식약처 원문)", `<div class="docs">${doc(d.doc_ee, "효능·효과")}${doc(d.doc_ud, "용법·용량")}${doc(d.doc_nb, "사용상 주의사항")}</div><div class="srcline">문서 본문은 저장하지 않고 식약처가 제공하는 원문 링크로 연결합니다.</div>`) : ""}
  <div class="grid2">
    ${panel(`회수·판매중지 (${(rel.recall || []).length})`, tl(rel.recall, x => tr(x[0], x[2] === "Y" ? `<span class="pill p-bad">강제</span>` : `<span class="pill p-mute">강제 아님</span>`, esc(x[1]))) + srcline(["recall_drug"]))}
    ${panel(`공급중단 신고 (${(rel.suspend || []).length})`, tl(rel.suspend, x => tr(x[0], `<span class="pill p-warn">${esc(x[1] || "중단")}</span>`, `중단일 ${esc(x[2] || "–")} · ${esc(x[4])}<div class="muted small">${esc(x[3])}</div>`)) + srcline(["supply_suspend"]))}
    ${panel(`공급부족 신고 (${(rel.shortage || []).length})`, tl(rel.shortage, x => tr(x[0], `<span class="pill p-warn">부족</span>`, `${esc(x[3])}<div class="muted small">${esc(x[1])}</div>`)) + srcline(["supply_shortage"]))}
    ${panel(`행정처분 (${(rel.admin || []).length})`, tl(rel.admin, x => tr(x[0], `<span class="pill p-mute">${esc(x[1])}</span>`, esc(x[2]))) + srcline(["admin_action"]))}
  </div>
  ${panel("연도별 생산·수입실적", prodRows.length ? `<div class="tbl-wrap"><table><thead><tr><th>연도</th><th>구분</th><th class="n">금액</th></tr></thead><tbody>${prodRows.map(p => `<tr><td>${esc(p[0])}</td><td>${esc(p[1])}</td><td class="n">${p[1] === "생산" ? wonM(p[2]) : usd(p[2])}</td></tr>`).join("")}</tbody></table></div>` : empty("생산·수입실적 기록이 없습니다."), "생산 백만원 · 수입 달러")}`;
  return { html };
};

V.stats = async () => {
  const s = await load("stats.json"), p = s.prod_year, py = s.permit_year;
  const tp = s.top_prod.map(x => ({ k: x[1] || fmtBiz(x[0]), v: x[2], href: "#company/" + x[0] }));
  const ti = s.top_import.map(x => ({ k: x[1] || fmtBiz(x[0]), v: x[2], href: "#company/" + x[0] }));
  const html = head("산업 통계", "분석", ["production_import", "drug_permit", "drug_permit_detail"]) + `
  <div class="notice small">생산·수입실적은 연간 자료입니다. 생산은 <b>백만원</b>, 수입은 <b>달러</b> 단위(공식 명세)라 합치지 않고 따로 보여 줍니다. 집계 건수는 API가 돌려준 행 수이며, 2020년은 다른 해보다 행이 많이 제공됩니다(원자료 그대로).</div>
  <div class="grid2">
    ${panel("연도별 의약품 생산실적", colChart(p.x, p.p, { vf: wonM, tf: v => v >= 1e6 ? (v / 1e6) + "조" : fmt(v / 100) + "억", label: "연도별 생산실적" }) + srcline(["production_import"], `행 수 ${p.np.map(fmt).join(" / ")}`))}
    ${panel("연도별 의약품 수입실적", colChart(p.x, p.i, { c: "var(--accent2)", vf: usd, tf: v => (v / 1e8).toFixed(0) + "억$", label: "연도별 수입실적" }) + srcline(["production_import"], `행 수 ${p.ni.map(fmt).join(" / ")}`))}
    ${panel(`${esc(s.latest_year)}년 생산실적 상위 업체`, barChart(tp, { vf: wonM }) + srcline(["production_import"]))}
    ${panel(`${esc(s.latest_year)}년 수입실적 상위 업체`, barChart(ti, { vf: usd, c: "var(--accent2)" }) + srcline(["production_import"]))}
  </div>
  ${panel("연도별 신규 허가·신고 품목과 취하 등", lineChart(py.x, [{ n: "허가", v: py["허가"], c: "var(--accent)" }, { n: "신고", v: py["신고"], c: "var(--accent2)" }, { n: "취하·만료·취소 (취하일 기준)", v: py.cancel, c: "var(--bad)" }], { label: "연도별 허가와 취하" }) + srcline(["drug_permit"], "허가일자·취하일자 기준, 현재 조회되는 품목만 포함"))}
  <div class="grid2">
    ${panel("유효 품목의 ATC 대분류", barChart(s.atc.map(x => ({ k: x[0] === "미상" ? "ATC 없음" : `${x[0]} ${x[1]}`, v: x[2] }))) + srcline(["drug_permit_detail"]))}
    ${panel("유효 품목의 분류 (상위 15)", barChart(s.ptype.map(x => ({ k: x[0], v: x[1] }))) + srcline(["drug_permit"]))}
    ${panel("유효 품목 전문/일반", barChart(s.spc.map(x => ({ k: x[0] + "의약품", v: x[1] }))) + srcline(["drug_permit"]))}
    ${panel("전체 품목 상태", barChart(s.status.map(x => ({ k: x[0], v: x[1] }))) + srcline(["drug_permit"]))}
  </div>`;
  return { html };
};

V.regulation = async () => {
  const g = await load("regulation.json");
  const gt = table({
    rows: g.gmp, sort: "valid", csv: "GMP적합판정", ph: "업체명, 공장 주소, 제형",
    text: r => [r[0], r[3], r[4], r[1]].join(" "),
    filters: [{ label: "구분", get: r => r[2], opts: g.gmp_kind.map(x => x[0]) }],
    cols: [{ k: "n", t: "업체", v: r => r[0], h: r => linkCo(r[1], r[0]) }, { k: "kind", t: "구분", v: r => r[2] },
      { k: "grp", t: "제형군", v: r => r[3], wrap: 1 }, { k: "addr", t: "공장 소재지", v: r => r[4] }, { k: "valid", t: "유효기간", v: r => r[5] }],
  });
  const at = table({
    rows: g.admins, sort: "date", csv: "행정처분", ph: "업체명, 품목명, 처분 내용",
    text: r => [r[1], r[3], r[5], r[6]].join(" "),
    filters: [{ label: "유형", get: r => r[8], opts: g.admin_type.map(x => x[0]) }],
    cols: [{ k: "date", t: "처분확정일", v: r => r[0] }, { k: "e", t: "업체", v: r => r[1], h: r => linkCo(r[2], r[1]) },
      { k: "type", t: "유형", v: r => r[8] }, { k: "disp", t: "처분 내용", v: r => r[5], wrap: 1 }, { k: "item", t: "품목", v: r => r[3], wrap: 1 },
      { k: "rls", t: "공개 종료일", v: r => r[7] }],
  });
  let ot = null;
  const ovsBox = `<div id="ovs-box"><button class="btn" id="ovs-load" type="button">해외 제조소 전체 목록 불러오기 (${fmt(g.overseas_total)}곳)</button></div>`;
  const html = head("규제·품질", "분석", ["gmp", "overseas_mfr", "admin_action"]) + `
  <div class="kpis">
    ${kpi("GMP 적합판정서", fmt(g.gmp.length), g.gmp_kind.map(x => `${x[0]} ${fmt(x[1])}`).join(" · "))}
    ${kpi("해외 제조소", fmt(g.overseas_total), `${g.overseas_country.length}개국 · 수입업체 ${fmt(g.overseas_companies)}곳`)}
    ${kpi("행정처분 (공개 중)", fmt(g.admins.length), g.admin_type.map(x => `${x[0]} ${x[1]}`).join(" · "))}
  </div>
  <div class="grid2">
    ${panel("해외 제조소 국가별 (상위 15)", barChart(g.overseas_country.slice(0, 15).map(x => ({ k: x[0], v: x[1] }))) + srcline(["overseas_mfr"]))}
    ${panel("연도별 행정처분 (처분확정일 기준)", colChart(g.admin_year.map(x => x[0]), g.admin_year.map(x => x[1]), { c: "var(--fg3)", label: "연도별 행정처분" }) + srcline(["admin_action"], "공개 기간이 남은 처분만 제공됨"))}
    ${panel("GMP 유효기간 만료 연도", colChart(g.gmp_valid_year.map(x => x[0]), g.gmp_valid_year.map(x => x[1]), { c: "var(--ok)", label: "GMP 유효기간 만료 연도" }) + srcline(["gmp"]))}
    ${panel("행정처분 유형", barChart(g.admin_type.map(x => ({ k: x[0], v: x[1] })), { c: "var(--fg3)" }) + srcline(["admin_action"], "처분명 문구에 '허가취소·업무정지·과징금·경고'가 들어가는지로 분류"))}
  </div>
  ${panel("행정처분 목록", at.html)}
  ${panel("GMP 적합판정서 발급 현황", gt.html)}
  ${panel("해외 제조소", ovsBox + srcline(["overseas_mfr"]))}`;
  return {
    html, bind() {
      gt.bind(); at.bind();
      $("#ovs-load").addEventListener("click", async () => {
        $("#ovs-box").innerHTML = '<div class="loading">불러오는 중…</div>';
        const o = await load("overseas.json");
        ot = table({ rows: o.rows, sort: "country", dir: 1, csv: "해외제조소", ph: "제조소명, 국가, 수입업체",
          text: r => r.join(" "), filters: [{ label: "국가", get: r => r[3], opts: g.overseas_country.map(x => x[0]) }],
          cols: [{ k: "m", t: "해외 제조소", v: r => r[2] }, { k: "country", t: "국가", v: r => r[3] }, { k: "addr", t: "주소", v: r => r[4], wrap: 1 },
            { k: "c", t: "국내 업체", v: r => r[0], h: r => linkCo(r[1], r[0]) }, { k: "no", t: "제조소 번호", v: r => r[5] }] });
        $("#ovs-box").innerHTML = ot.html; ot.bind();
      });
    },
  };
};

V.supply = async () => {
  const s = await load("supply.json"), t = s.trend;
  const rt = table({ rows: s.recalls, sort: "date", csv: "회수판매중지", ph: "제품명, 업체명, 사유", text: r => [r[1], r[2], r[5]].join(" "),
    filters: [{ label: "강제 여부", get: r => r[6] === "Y" ? "강제" : "강제 아님", opts: ["강제", "강제 아님"] }],
    cols: [{ k: "date", t: "회수명령일", v: r => r[0] }, { k: "p", t: "제품", v: r => r[1], h: r => linkDrug(r[4], r[1]) },
      { k: "e", t: "업체", v: r => r[2], h: r => linkCo(r[3], r[2]) }, { k: "why", t: "사유", v: r => r[5], wrap: 1 }, { k: "f", t: "강제 여부", v: r => r[6] === "Y" ? "강제" : "강제 아님" }] });
  const st = table({ rows: s.suspends, sort: "date", csv: "공급중단", ph: "제품명, 업체명, 사유", text: r => [r[1], r[2], r[7]].join(" "),
    filters: [{ label: "구분", get: r => r[5], opts: [...new Set(s.suspends.map(r => r[5]))] }, { label: "처리상태", get: r => r[8], opts: s.suspend_status.map(x => x[0]) }],
    cols: [{ k: "date", t: "신고일", v: r => r[0] }, { k: "p", t: "제품", v: r => r[1], h: r => linkDrug(r[4], r[1]) },
      { k: "e", t: "업체", v: r => r[2], h: r => linkCo(r[3], r[2]) }, { k: "f", t: "구분", v: r => r[5] }, { k: "sd", t: "중단(예정)일", v: r => r[6] },
      { k: "why", t: "사유", v: r => r[7], wrap: 1 }, { k: "s", t: "처리상태", v: r => r[8] }] });
  const sh = table({ rows: s.shortages, sort: "date", csv: "공급부족", ph: "제품명, 업체명, 사유", text: r => [r[1], r[2], r[5]].join(" "),
    filters: [{ label: "처리상태", get: r => r[7], opts: s.shortage_status.map(x => x[0]) }],
    cols: [{ k: "date", t: "신고일", v: r => r[0] }, { k: "p", t: "제품", v: r => r[1], h: r => linkDrug(r[4], r[1]) },
      { k: "e", t: "업체", v: r => r[2], h: r => linkCo(r[3], r[2]) }, { k: "why", t: "부족 사유", v: r => r[5], wrap: 1 },
      { k: "plan", t: "공급 예정일", v: r => r[6] }, { k: "s", t: "처리상태", v: r => r[7] }, { k: "alt", t: "대체 가능 여부·조치", v: r => r[8], wrap: 1 }] });
  const lt = table({ rows: s.letters, sort: "date", csv: "안전성서한", ph: "제목, 내용", text: r => [r[1], r[4], r[2]].join(" "),
    cols: [{ k: "date", t: "공고일", v: r => r[0] }, { k: "t", t: "제목", v: r => r[1], h: r => r[3] ? `<a class="link" href="${esc(r[3])}" target="_blank" rel="noopener">${esc(r[1])}</a>` : esc(r[1]), wrap: 1 },
      { k: "c", t: "내용", v: r => r[4], wrap: 1 }, { k: "d", t: "담당 부서", v: r => r[2] }] });
  const tb = tabs([
    { t: `회수·판매중지 (${fmt(s.recalls.length)})`, html: rt.html + srcline(["recall_drug"]), bind: rt.bind },
    { t: `공급중단 (${fmt(s.suspends.length)})`, html: st.html + srcline(["supply_suspend"], META.hidden_suspend ? `공개 비동의 ${META.hidden_suspend}건은 싣지 않음` : ""), bind: st.bind },
    { t: `공급부족 (${fmt(s.shortages.length)})`, html: sh.html + srcline(["supply_shortage"]), bind: sh.bind },
    { t: `안전성서한 (${fmt(s.letters.length)})`, html: lt.html + srcline(["safety_letter"]), bind: lt.bind },
  ]);
  const xf = x => x.slice(2).replace("-", ".");
  const html = head("공급·안전", "분석", ["recall_drug", "supply_suspend", "supply_shortage", "safety_letter"]) + `
  <div class="grid2">
    ${panel("월별 회수·판매중지 (최근 36개월)", lineChart(t.recalls.x, [{ n: "회수·판매중지", v: t.recalls.y, c: "var(--bad)", area: true }], { xf }) + srcline(["recall_drug"], "회수명령일 기준"))}
    ${panel("월별 공급중단·부족 신고 (최근 36개월)", lineChart(t.suspends.x, [{ n: "공급중단", v: t.suspends.y, c: "var(--warn)" }, { n: "공급부족", v: t.shortages.y, c: "var(--accent)" }], { xf }) + srcline(["supply_suspend", "supply_shortage"], "신고일 기준"))}
  </div>
  ${panel("목록", tb.html)}`;
  return { html, bind: tb.bind };
};

V.changes = async () => {
  const c = await load("changes.json");
  const names = { added: "추가", updated: "변경", removed: "조회 안 됨", reappeared: "다시 조회" };
  const t = table({ rows: c.rows, sort: "date", csv: "변경이력", ph: "이름, 키", text: r => [r[4], r[3], r[1]].join(" "),
    filters: [{ label: "데이터", get: r => API(r[1]).name, opts: [...new Set(c.rows.map(r => API(r[1]).name))] }, { label: "변경 유형", get: r => names[r[2]] || r[2], opts: Object.values(names) }],
    cols: [{ k: "date", t: "감지일", v: r => r[0] }, { k: "api", t: "데이터", v: r => API(r[1]).name }, { k: "type", t: "유형", v: r => names[r[2]] || r[2] },
      { k: "label", t: "대상", v: r => r[4] || r[3], h: r => r[6] ? linkDrug(r[6].split(",")[0], r[4] || r[3]) : (r[5] ? linkCo(r[5], r[4] || r[3]) : esc(r[4] || r[3])) },
      { k: "f", t: "바뀐 항목", v: r => (r[7] || []).join(", "), wrap: 1 }] });
  const base = Object.entries(c.baseline || {}).map(([k, v]) => `${esc(API(k).name)} <span class="muted">${esc((v || "").slice(0, 10))}</span>`).join(" · ");
  const html = head("변경 모니터링", "분석", []) + `
  <div class="notice small">매일 수집한 결과를 직전 수집과 비교해 추가·변경·조회 안 됨을 기록합니다. 각 데이터의 첫 전체 수집(기준선) 이전 이력은 만들지 않습니다. '조회 안 됨'은 API에서 더 이상 나오지 않는다는 뜻일 뿐, 취하·삭제로 단정하지 않습니다.</div>
  ${panel(`최근 90일 변경 (${fmt(c.rows.length)}건)`, c.rows.length ? t.html : empty("아직 감지된 변경이 없습니다. 다음 매일 수집(03:00)부터 기준선과 비교한 결과가 쌓입니다."))}
  ${panel("데이터별 기준선 수집일", `<div class="small">${base || "–"}</div>`)}`;
  return { html, bind: c.rows.length ? t.bind : null };
};

V.about = async () => {
  const cv = id => { const c = META.coverage && META.coverage[id]; return c ? `${esc(c[0])} ~ ${esc(c[1])}` : '<span class="muted">–</span>'; };
  const rows = META.apis.map(a => `<tr><td><a class="link" href="${esc(a.url)}" target="_blank" rel="noopener">${esc(a.name)}</a></td><td class="n">${fmt(a.count)}</td><td>${cv(a.id)}</td><td>${esc((a.last || "").replace("T", " ").replace("Z", " UTC"))}</td></tr>`).join("");
  const html = head("데이터 출처·기준", "안내", []) + `
  ${panel("수집 데이터", `<div class="tbl-wrap"><table><thead><tr><th>데이터 (공공데이터포털)</th><th class="n">현재 건수</th><th>자료 기간 (날짜 필드 기준)</th><th>최근 수집</th></tr></thead><tbody>${rows}</tbody></table></div>`)}
  ${panel("표시 기준", `<ul class="small" style="margin:0;padding-left:18px;line-height:1.9">
    <li>모든 수치는 식품의약품안전처 공공데이터 API가 돌려준 값입니다. 사이트가 값을 추정하거나 만들어 넣지 않습니다.</li>
    <li>업체는 사업자등록번호, 품목은 품목기준코드로만 연결합니다. 이름이 비슷하다는 이유로 같은 업체로 묶지 않습니다.</li>
    <li>생산실적은 백만원, 수입실적은 달러 단위입니다(공식 명세). 두 값을 합산하지 않습니다.</li>
    <li>공급중단 신고 중 '공개 동의하지 않음'으로 표시된 ${fmt(META.hidden_suspend)}건은 싣지 않습니다.</li>
    <li>행정처분은 공개 기간이 남은 건만 API에서 제공됩니다. 유형은 처분명 문구로 나눈 것입니다.</li>
    <li>의약품 설명서 본문(효능·용법·주의사항)은 저장하지 않고 식약처 원문 링크로 연결합니다.</li>
    <li>매일 03:00(KST) 수집합니다. 제품허가 상세는 매일 변경분만, 매월 1일 전체를 다시 받습니다.</li>
    <li>이 사이트는 공식 판단을 대신하지 않습니다. 중요한 결정 전에는 식약처 의약품안전나라 원문을 확인하세요.</li></ul>`)}
  <div class="foot">화면 데이터 생성: ${esc(META.generated_at)} (KST)</div>`;
  return { html };
};

V.search = async q => {
  const [d, c] = await Promise.all([load("drugs_index.json"), load("companies_index.json")]);
  const s = q.trim().toLowerCase(), digits = q.replace(/\D/g, "");
  const cos = c.rows.filter(r => r[1].toLowerCase().includes(s) || (digits.length >= 3 && r[0].includes(digits))).sort((a, b) => b[4] - a[4]).slice(0, 20);
  const dr = table({ rows: d.rows, sort: "permit", csv: "검색결과_의약품", ph: "결과 안에서 다시 검색", q,
    text: r => [r[1], r[2], r[7], r[8], r[0], r[9], r[3]].join(" "),
    cols: [{ k: "name", t: "품목명", v: r => r[1], h: r => linkDrug(r[0], r[1]) }, { k: "entp", t: "업체", v: r => r[2], h: r => linkCo(r[3], r[2]) },
      { k: "ingr", t: "주성분", v: r => r[7] || r[8], clip: 1 }, { k: "permit", t: "허가일", v: r => r[4] }, { k: "st", t: "상태", v: r => r[6], h: r => statusTag(r[6]) }] });
  const html = head(`'${esc(q)}' 검색 결과`, "통합검색", []) +
    panel(`업체 (${cos.length}${cos.length === 20 ? "+" : ""})`, cos.length ? `<div class="feed">${cos.map(r => `<div class="r"><span class="when">${esc(fmtBiz(r[0]))}</span><span class="t">${linkCo(r[0], r[1])} <span class="muted">· ${esc(r[2])}</span></span><span class="pill p-mute">품목 ${fmt(r[3])}/${fmt(r[4])}</span></div>`).join("")}</div>` : empty("일치하는 업체가 없습니다.")) +
    panel("의약품", dr.html);
  return { html, bind: dr.bind };
};

// ---------- 라우팅 ----------
async function route() {
  const h = decodeURIComponent((location.hash || "#dashboard").slice(1));
  const [v, ...rest] = h.split("/"), arg = rest.join("/");
  const view = V[v] ? v : "dashboard";
  const navKey = { company: "companies", drug: "drugs", search: "" }[view] ?? view;
  document.querySelectorAll("#nav a").forEach(a => a.classList.toggle("on", a.dataset.v === navKey));
  const el = $("#view");
  CHARTS.clear();
  el.innerHTML = '<div class="loading">불러오는 중…</div>';
  try {
    const r = await V[view](arg);
    if (location.hash && decodeURIComponent(location.hash.slice(1)) !== h) return; // 그 사이 다른 화면으로 이동
    el.innerHTML = r.html;
    if (r.bind) r.bind();
    drawCharts(el);
    document.title = (el.querySelector("h1") ? el.querySelector("h1").textContent + " · " : "") + "MFDS INSIGHT";
    window.scrollTo(0, 0);
  } catch (e) {
    el.innerHTML = `<div class="notice warn">데이터를 불러오지 못했습니다 (${esc(e.message)}). 잠시 후 새로고침해 주세요.</div>`;
  }
}

async function init() {
  try { META = await load("meta.json"); }
  catch (e) { $("#view").innerHTML = `<div class="notice warn">데이터를 불러오지 못했습니다 (${esc(e.message)}).</div>`; return; }
  const total = n => fmt(n);
  const drug = META.apis.find(a => a.id === "drug_permit");
  $("#scope").textContent = `기준일 ${META.as_of} · 품목 ${total(drug ? drug.count : 0)}`;
  $("#sidefoot").innerHTML = `출처: 식품의약품안전처 공공데이터 (data.go.kr)<br>기준일 ${esc(META.as_of)} · 매일 03:00 갱신`;
  $("#qform").addEventListener("submit", e => { e.preventDefault(); const q = $("#q").value.trim(); if (q) location.hash = "#search/" + encodeURIComponent(q); });
  window.addEventListener("hashchange", route);
  route();
}
init();
})();
