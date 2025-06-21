// JobHunter v2 — logika frontendu (vanilla JS)
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

let currentOffer = null;
let offersById = {};

async function api(path, opts = {}) {
  const res = await fetch(path, opts);
  if (!res.ok) {
    const b = await res.json().catch(() => ({}));
    throw new Error(b.detail || res.statusText);
  }
  return res.json();
}

// ── Tabs ────────────────────────────────────────────────────────────────────
$$(".tab").forEach(t => t.addEventListener("click", () => {
  $$(".tab").forEach(x => x.classList.remove("active"));
  $$(".tab-panel").forEach(x => x.classList.remove("active"));
  t.classList.add("active");
  $("#tab-" + t.dataset.tab).classList.add("active");
  if (t.dataset.tab === "tracker") loadTracker();
  if (t.dataset.tab === "recruiters") loadRecruiters();
}));

// ── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  const { sources } = await api("/api/sources");
  const defaults = ["justjoin", "nofluffjobs", "remoteok", "weworkremotely"];
  $("#sources-box").innerHTML = sources.map(s =>
    `<label><input type="checkbox" value="${s.key}" ${defaults.includes(s.key) ? "checked" : ""}/> ${s.label}</label>`
  ).join("");

  const cfg = await api("/api/config");
  if (!cfg.ai_enabled) {
    $("#use-ai").checked = false;
    $("#use-ai").parentElement.title = "Brak ANTHROPIC_API_KEY";
  }

  const { profile } = await api("/api/profile");
  if (profile) {
    renderProfile(profile);
    const quality = await api("/api/cv-quality");
    renderQuality(quality);
  }
}

// ── CV Upload ────────────────────────────────────────────────────────────────
$("#upload-btn").addEventListener("click", async () => {
  const f = $("#cv-file").files[0];
  if (!f) return alert("Wybierz plik CV.");
  const fd = new FormData(); fd.append("file", f);
  $("#upload-btn").textContent = "Przetwarzanie...";
  try {
    const { profile, quality } = await api("/api/upload-cv", { method: "POST", body: fd });
    renderProfile(profile);
    renderQuality(quality);
  } catch (e) { alert("Błąd: " + e.message); }
  finally { $("#upload-btn").textContent = "Wgraj CV"; }
});

function renderProfile(p) {
  $("#search-btn").disabled = false;
  const skills = p.skills.length
    ? p.skills.map(s => `<span class="chip">${s}</span>`).join("")
    : '<span class="muted">Nie wykryto technologii.</span>';
  $("#profile-summary").innerHTML =
    `<div><b>${p.filename}</b> — ${p.seniority_label}, ` +
    `${p.years ? p.years + " lat dośw." : "lata dośw.: b/d"}, język: ${p.language}</div>` +
    `<div class="chips">${skills}</div>`;
}

function renderQuality(q) {
  const cls = q.score >= 70 ? "" : q.score >= 40 ? "mid" : "low";
  const top = q.top_issues.slice(0, 4);
  const issues = top.map(c =>
    `<div class="qcheck">
       <span class="ico">❌</span>
       <div><div>${c.label}</div><div class="qtip">${c.tip}</div></div>
     </div>`
  ).join("");
  const passed = q.checks.filter(c => c.passed).length;
  $("#cv-quality-box").innerHTML =
    `<div class="quality-bar">
       <span class="quality-score ${cls}">${q.score}/100</span>
       <span class="muted">Jakość CV — ${passed}/${q.checks.length} checków OK</span>
     </div>
     ${issues ? `<div class="quality-checks">${issues}</div>` : ""}`;
}

// ── Oferta z URL ─────────────────────────────────────────────────────────────
$("#url-btn").addEventListener("click", async () => {
  const url = $("#url-input").value.trim();
  if (!url) return;
  $("#url-btn").textContent = "Ładowanie...";
  try {
    const { offer } = await api("/api/offer-from-url", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });
    offersById[offer.id] = offer;
    const prev = $("#url-result");
    if (prev) prev.remove();
    const div = document.createElement("div");
    div.id = "url-result";
    div.className = "offer";
    div.innerHTML = _offerHTML(offer);
    $("#results").prepend(div);
    $("#results-count").textContent = `(z URL)`;
    bindApplyBtns(div);
    openModal(offer);
  } catch (e) { alert("Błąd: " + e.message); }
  finally { $("#url-btn").textContent = "Analizuj URL"; }
});

// ── Suwak ────────────────────────────────────────────────────────────────────
$("#min-score").addEventListener("input", e => {
  $("#min-score-val").textContent = e.target.value + "%";
});

// ── Wyszukiwanie ─────────────────────────────────────────────────────────────
$("#search-btn").addEventListener("click", async () => {
  const sources = $$("#sources-box input:checked").map(c => c.value);
  if (!sources.length) return alert("Wybierz przynajmniej jedno źródło.");
  $("#search-status").innerHTML = "🔎 Szukam ofert...";
  $("#results").innerHTML = "";
  try {
    const data = await api("/api/search", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        sources, query: $("#query").value.trim(),
        min_score: parseInt($("#min-score").value),
        remote_only: $("#remote-only").checked,
        location: $("#location").value.trim(),
        salary_min: parseInt($("#salary-min").value) || 0,
      }),
    });
    renderResults(data);
  } catch (e) {
    $("#search-status").innerHTML = `<span class="err">Błąd: ${e.message}</span>`;
  }
});

function renderGaps(gaps) {
  const panel = $("#gaps-panel");
  if (!gaps?.length) { panel.style.display = "none"; return; }
  panel.style.display = "block";
  $("#gaps").innerHTML = gaps
    .map(g => `<span class="chip missing">${g.skill} <b>×${g.count}</b></span>`)
    .join("");
}

function renderResults(data) {
  offersById = {};
  const dedup = data.total_after_dedup ?? data.total_fetched;
  let status = `Pobrano ${data.total_fetched} ofert (po deduplikacji ${dedup}), dopasowano ${data.total_matched}.`;
  const errs = Object.entries(data.errors || {});
  if (errs.length)
    status += ` <span class="err">Problem: ${errs.map(([k]) => k).join(", ")}</span>`;
  $("#search-status").innerHTML = status;
  renderGaps(data.skill_gaps);
  $("#results-count").textContent = `(${data.offers.length})`;

  if (!data.offers.length) {
    $("#results").innerHTML = "<p class='muted'>Brak ofert. Obniż próg dopasowania lub zmień filtry.</p>";
    return;
  }
  $("#results").innerHTML = data.offers.map(o => {
    offersById[o.id] = o;
    return `<div class="offer">${_offerHTML(o)}</div>`;
  }).join("");
  bindApplyBtns($("#results"));
}

function _offerHTML(o) {
  const matched = o.matched_skills.map(s => `<span class="chip matched">${s}</span>`).join("");
  const missing = o.missing_skills.slice(0, 5).map(s => `<span class="chip missing">${s}</span>`).join("");
  const kwLine = o.kw_score != null
    ? `<div class="offer-kw">Słowa kluczowe: ${o.kw_score}% pokrycia` +
      (o.kw_missing?.length ? ` | brakuje: <b>${o.kw_missing.slice(0,5).join(", ")}</b>` : "") + `</div>`
    : "";
  const srcTags = (o.sources || [o.source]).map(s => `<span class="src-tag">${s}</span>`).join("");
  const prefClass = o.preference === "like" ? "liked" : o.preference === "dislike" ? "disliked" : "";
  return `
    <div class="score-badge ${scoreClass(o.score)}">${o.score}</div>
    <div class="offer-body">
      <p class="offer-title">${o.title}</p>
      <div class="offer-meta">
        ${srcTags}
        ${o.company ? o.company + " · " : ""}${o.location || ""}
        ${o.remote ? " · 🏠 zdalnie" : ""}${o.salary ? " · 💰 " + o.salary : ""}
      </div>
      <div class="chips">${matched}${missing}</div>
      ${kwLine}
      <div class="offer-actions">
        <button class="btn-apply" data-id="${o.id}">✍️ Aplikuj</button>
        <button class="pref-btn like-btn ${prefClass}" data-id="${o.id}" title="Lubię tę ofertę">👍</button>
        <button class="pref-btn dis-btn ${prefClass}" data-id="${o.id}" title="Ignoruj">👎</button>
        <a class="btn-link" href="${o.url}" target="_blank">Otwórz ↗</a>
      </div>
    </div>`;
}

function scoreClass(s) { return s >= 70 ? "score-high" : s >= 40 ? "score-mid" : "score-low"; }

function bindApplyBtns(root) {
  (root.querySelectorAll ? root : document).querySelectorAll(".btn-apply").forEach(b =>
    b.addEventListener("click", () => openModal(offersById[b.dataset.id]))
  );
  root.querySelectorAll?.(".like-btn").forEach(b => b.addEventListener("click", () => setPref(b.dataset.id, "like")));
  root.querySelectorAll?.(".dis-btn").forEach(b => b.addEventListener("click", () => setPref(b.dataset.id, "dislike")));
}

async function setPref(id, action) {
  await api("/api/preference", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ offer_id: id, action, offer: offersById[id] || {} }),
  });
  // Usuń ignorowane z widoku.
  if (action === "dislike") {
    document.querySelectorAll(`.offer .dis-btn[data-id="${id}"]`).forEach(b => {
      b.closest(".offer")?.remove();
    });
  }
}

// ── Modal ────────────────────────────────────────────────────────────────────
function openModal(offer) {
  currentOffer = offer;
  $("#modal-title").textContent = offer.title;
  $("#modal-meta").textContent = `${offer.company || ""} · score ${offer.score}%`;
  $("#open-offer").href = offer.url;
  $("#letter-text").value = "";
  $("#suggestions-list").innerHTML = "";
  renderKwPanel(offer);
  // Reset modal tabs
  $$(".mtab").forEach(t => t.classList.remove("active"));
  $$(".mtab-panel").forEach(p => p.classList.remove("active"));
  $(".mtab[data-mtab='letter']").classList.add("active");
  $("#mpanel-letter").classList.add("active");
  $("#modal").classList.remove("hidden");
}

$("#modal-close").addEventListener("click", () => $("#modal").classList.add("hidden"));
$("#modal").addEventListener("click", e => { if (e.target.id === "modal") $("#modal").classList.add("hidden"); });

$$(".mtab").forEach(t => t.addEventListener("click", () => {
  $$(".mtab").forEach(x => x.classList.remove("active"));
  $$(".mtab-panel").forEach(p => p.classList.remove("active"));
  t.classList.add("active");
  $("#mpanel-" + t.dataset.mtab).classList.add("active");
}));

// List motywacyjny
$("#gen-letter-btn").addEventListener("click", async () => {
  if (!currentOffer) return;
  $("#gen-letter-btn").textContent = "Generowanie...";
  try {
    const res = await api("/api/cover-letter", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offer_id: currentOffer.id, use_ai: $("#use-ai").checked }),
    });
    $("#letter-text").value = res.letter;
    $("#modal-meta").textContent =
      `${currentOffer.company || ""} · score ${currentOffer.score}% · ${res.note || res.mode}`;
  } catch (e) { alert("Błąd: " + e.message); }
  finally { $("#gen-letter-btn").textContent = "Wygeneruj list"; }
});

$("#copy-letter").addEventListener("click", () => {
  navigator.clipboard.writeText($("#letter-text").value);
  $("#copy-letter").textContent = "Skopiowano ✓";
  setTimeout(() => ($("#copy-letter").textContent = "Kopiuj"), 1500);
});

$("#save-app").addEventListener("click", async () => {
  if (!currentOffer) return;
  await api("/api/track", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      offer_id: currentOffer.id, status: "do_aplikacji",
      cover_letter: $("#letter-text").value,
    }),
  });
  $("#save-app").textContent = "Zapisano ✓";
  setTimeout(() => ($("#save-app").textContent = "Zapisz aplikację"), 1500);
});

// Sugestie CV
$("#gen-suggest-btn").addEventListener("click", async () => {
  if (!currentOffer) return;
  $("#gen-suggest-btn").textContent = "Generowanie...";
  try {
    const { suggestions } = await api("/api/suggest-cv", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ offer_id: currentOffer.id }),
    });
    $("#suggestions-list").innerHTML = suggestions.map(s =>
      `<div class="suggestion ${s.priority}">
         <div class="sug-cat">${s.priority.toUpperCase()} · ${s.category}</div>
         <div class="sug-action">${s.action}</div>
       </div>`
    ).join("");
  } catch (e) { alert("Błąd: " + e.message); }
  finally { $("#gen-suggest-btn").textContent = "Generuj sugestie"; }
});

// Panel słów kluczowych
function renderKwPanel(o) {
  const matched = (o.kw_matched || []).slice(0, 20)
    .map(k => `<span class="chip ok">${k}</span>`).join("");
  const missing = (o.kw_missing || []).slice(0, 20)
    .map(k => `<span class="chip mis">${k}</span>`).join("");
  $("#kw-content").innerHTML =
    `<div class="kw-section">
       <h4>✅ Słowa kluczowe z oferty obecne w CV (${(o.kw_matched||[]).length})</h4>
       <div class="chips">${matched || '<span class="muted">Brak</span>'}</div>
     </div>
     <div class="kw-section">
       <h4>❌ Brakujące w CV — dodaj do opisów stanowisk (${(o.kw_missing||[]).length})</h4>
       <div class="chips">${missing || '<span class="muted">Wszystko pokryte!</span>'}</div>
     </div>
     <p class="muted" style="margin-top:8px">Pokrycie słów kluczowych: <b>${o.kw_score ?? "–"}%</b></p>`;
}

// ── Tracker ───────────────────────────────────────────────────────────────────
async function loadTracker() {
  const { applications, statuses } = await api("/api/tracker");
  if (!applications.length) {
    $("#tracker-list").innerHTML = "<p class='muted'>Brak aplikacji.</p>";
    return;
  }
  const rows = applications.map(a => {
    const dates = a.stage_dates || {};
    const datesStr = Object.entries(dates)
      .map(([s, d]) => `${s}: ${d.slice(0,10)}`).join(" · ");
    return `<tr>
      <td>
        <a class="btn-link" href="${a.url}" target="_blank">${a.title}</a><br/>
        <span class="muted">${a.company || ""} · ${a.source}</span>
        ${datesStr ? `<div class="stage-dates">${datesStr}</div>` : ""}
      </td>
      <td>${a.score}%</td>
      <td>
        <select class="status-sel" data-id="${a.id}">
          ${statuses.map(s => `<option ${s===a.status?"selected":""}>${s}</option>`).join("")}
        </select>
      </td>
      <td class="notes-cell">
        <textarea class="notes-ta" data-id="${a.id}" rows="2"
          style="width:100%;font-size:12px">${a.notes || ""}</textarea>
      </td>
      <td><button class="btn-danger del-btn" data-id="${a.id}">Usuń</button></td>
    </tr>`;
  }).join("");

  $("#tracker-list").innerHTML =
    `<table><thead><tr>
      <th>Oferta</th><th>Dop.</th><th>Status</th><th>Notatki</th><th></th>
    </tr></thead><tbody>${rows}</tbody></table>`;

  $$(".status-sel").forEach(sel => sel.addEventListener("change", async () => {
    await api("/api/tracker/" + sel.dataset.id, {
      method: "PATCH", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ status: sel.value }),
    });
  }));

  let notesTimer;
  $$(".notes-ta").forEach(ta => ta.addEventListener("input", () => {
    clearTimeout(notesTimer);
    notesTimer = setTimeout(() => {
      api("/api/tracker/" + ta.dataset.id + "/notes", {
        method: "PATCH", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ notes: ta.value }),
      });
    }, 800);
  }));

  $$(".del-btn").forEach(b => b.addEventListener("click", async () => {
    await api("/api/tracker/" + b.dataset.id, { method: "DELETE" });
    loadTracker();
  }));
}

// ── CRM rekruterów ────────────────────────────────────────────────────────────
async function loadRecruiters() {
  const { recruiters } = await api("/api/recruiters");
  if (!recruiters.length) {
    $("#recruiter-list").innerHTML = "<p class='muted'>Brak rekruterów.</p>";
    return;
  }
  const today = new Date().toISOString().slice(0, 10);
  const rows = recruiters.map(r => {
    const soon = r.follow_up && r.follow_up <= today;
    return `<tr class="recruiter-row">
      <td><b>${r.name}</b><br/><span class="muted">${r.company || ""}</span></td>
      <td>${r.email ? `<a class="btn-link" href="mailto:${r.email}">${r.email}</a>` : "–"}</td>
      <td>${r.linkedin ? `<a class="btn-link" href="${r.linkedin}" target="_blank">LinkedIn</a>` : "–"}</td>
      <td class="${soon ? "follow-up-soon" : "muted"}">${r.follow_up || "–"}</td>
      <td class="muted" style="font-size:12px;max-width:160px">${r.notes || ""}</td>
      <td><button class="btn-danger" onclick="deleteRecruiter(${r.id})">Usuń</button></td>
    </tr>`;
  }).join("");
  $("#recruiter-list").innerHTML =
    `<table><thead><tr>
      <th>Rekruter</th><th>E-mail</th><th>LinkedIn</th><th>Follow-up</th><th>Notatki</th><th></th>
    </tr></thead><tbody>${rows}</tbody></table>`;
}

async function deleteRecruiter(id) {
  await api("/api/recruiters/" + id, { method: "DELETE" });
  loadRecruiters();
}

$("#rec-save-btn").addEventListener("click", async () => {
  const name = $("#rec-name").value.trim();
  if (!name) return alert("Podaj imię i nazwisko.");
  await api("/api/recruiters", {
    method: "POST", headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      name, email: $("#rec-email").value.trim(),
      phone: $("#rec-phone").value.trim(), company: $("#rec-company").value.trim(),
      linkedin: $("#rec-linkedin").value.trim(), notes: $("#rec-notes").value.trim(),
      follow_up: $("#rec-followup").value || null,
    }),
  });
  ["rec-name","rec-email","rec-phone","rec-company","rec-linkedin","rec-notes","rec-followup"]
    .forEach(id => { const el = document.getElementById(id); if (el) el.value = ""; });
  loadRecruiters();
});

init();
