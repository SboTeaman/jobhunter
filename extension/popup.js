const API = "http://127.0.0.1:8001";

async function api(path, opts = {}) {
  const r = await fetch(API + path, opts);
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

function scoreClass(s) {
  return s >= 70 ? "score-high" : s >= 40 ? "score-mid" : "score-low";
}

async function init() {
  // Pobierz ofertę wyciągniętą przez content.js ze storage.
  const stored = await new Promise(res =>
    chrome.storage.local.get("jobhunter_current_offer", d =>
      res(d.jobhunter_current_offer || null)
    )
  );

  const offer = stored;
  if (!offer || !offer.title) {
    document.getElementById("loading").innerHTML =
      '<span class="err">Nie udało się odczytać oferty z tej strony.</span>';
    return;
  }

  document.getElementById("source-label").textContent =
    offer.source + (offer.company ? " · " + offer.company : "");

  // Sprawdź profil CV.
  let profile;
  try {
    const { profile: p } = await api("/api/profile");
    profile = p;
  } catch (_) {}

  if (!profile) {
    document.getElementById("loading").style.display = "none";
    document.getElementById("no-cv").style.display = "block";
    return;
  }

  // Wyślij ofertę do API żeby uzyskać score.
  let scored;
  try {
    const res = await api("/api/score-offer", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(offer),
    });
    scored = res.offer;
  } catch (e) {
    document.getElementById("loading").innerHTML =
      `<span class="err">Błąd API: ${e.message}</span>`;
    return;
  }

  document.getElementById("loading").style.display = "none";
  document.getElementById("main").style.display = "block";

  const circle = document.getElementById("score-circle");
  circle.textContent = scored.score + "%";
  circle.className = "score-circle " + scoreClass(scored.score);

  document.getElementById("offer-title").textContent = offer.title;
  document.getElementById("offer-sub").textContent =
    [offer.company, offer.salary].filter(Boolean).join(" · ") || offer.source;

  // Chips: dopasowane na zielono, brakujące na czerwono.
  const chips = document.getElementById("chips");
  for (const s of (scored.matched_skills || []).slice(0, 6)) {
    chips.innerHTML += `<span class="chip ok">${s}</span>`;
  }
  for (const s of (scored.missing_skills || []).slice(0, 5)) {
    chips.innerHTML += `<span class="chip mis">${s}</span>`;
  }

  // Przyciski.
  document.getElementById("btn-save").addEventListener("click", async () => {
    try {
      await api("/api/track-ext", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ offer: scored, status: "do_aplikacji" }),
      });
      document.getElementById("msg").textContent = "✓ Zapisano!";
    } catch (e) {
      document.getElementById("msg").innerHTML = `<span class="err">${e.message}</span>`;
    }
  });

  document.getElementById("btn-open").addEventListener("click", () => {
    chrome.tabs.create({ url: API + "/?highlight=" + encodeURIComponent(scored.id || "") });
  });

  document.getElementById("btn-dis").addEventListener("click", async () => {
    try {
      await api("/api/preference", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ offer_id: scored.id, action: "dislike", offer: scored }),
      });
      document.getElementById("msg").textContent = "Oferta zignorowana — nie będzie pokazywana.";
      document.getElementById("btn-dis").disabled = true;
    } catch (_) {}
  });
}

init().catch(e => {
  document.getElementById("loading").innerHTML =
    `<span class="err">Błąd: ${e.message}</span>`;
});
