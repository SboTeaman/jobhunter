// content.js — wyciąga dane oferty z aktualnej strony i odsyła do popup.
(function () {
  const host = location.hostname;

  function getText(sel) {
    const el = document.querySelector(sel);
    return el ? el.innerText.trim() : "";
  }
  function getMeta(prop) {
    const el = document.querySelector(`meta[property="${prop}"],meta[name="${prop}"]`);
    return el ? el.getAttribute("content") || "" : "";
  }

  let offer = { url: location.href, title: "", company: "", skills: [], salary: "", source: "" };

  if (host.includes("justjoin.it")) {
    offer.source = "JustJoin.it";
    offer.title = getText("h1") || getMeta("og:title");
    offer.company = getText('[data-testid="company-name"]') || getText(".css-1qdp0tm");
    const chips = [...document.querySelectorAll('[data-testid="chip-btn"]')];
    offer.skills = chips.map(c => c.innerText.trim()).filter(Boolean);
    offer.salary = getText('[data-testid="salary-label"]') || getText(".css-1pavfqb");

  } else if (host.includes("nofluffjobs.com")) {
    offer.source = "NoFluffJobs";
    offer.title = getText("h1") || getMeta("og:title");
    offer.company = getText(".company-name") || getText('[data-cy="posting-company-name"]');
    const pills = [...document.querySelectorAll(".list-tags span, .tags-list li")];
    offer.skills = pills.map(p => p.innerText.trim()).filter(Boolean);
    offer.salary = getText(".salary-label") || getText('[data-cy="salary"]');

  } else if (host.includes("pracuj.pl")) {
    offer.source = "Pracuj.pl";
    offer.title = getMeta("og:title") || getText("h1");
    offer.company = getText('[data-test="text-employerName"]') || getText(".offer-company__name");

  } else if (host.includes("theprotocol.it")) {
    offer.source = "TheProtocol";
    offer.title = getText("h1") || getMeta("og:title");
    offer.company = getMeta("og:site_name");

  } else {
    // Fallback: JSON-LD JobPosting
    offer.source = host;
    offer.title = getMeta("og:title") || document.title;
    offer.company = getMeta("og:site_name");
    const scripts = [...document.querySelectorAll('script[type="application/ld+json"]')];
    for (const s of scripts) {
      try {
        const d = JSON.parse(s.textContent);
        const job = Array.isArray(d) ? d.find(x => x["@type"] === "JobPosting") : d;
        if (job && job["@type"] === "JobPosting") {
          offer.title = job.title || offer.title;
          offer.company = (job.hiringOrganization || {}).name || offer.company;
          const skills = job.skills || [];
          offer.skills = typeof skills === "string"
            ? skills.split(",").map(s => s.trim())
            : skills;
          break;
        }
      } catch (_) {}
    }
  }

  // Wyczyść puste.
  offer.skills = offer.skills.filter(s => s && s.length > 1);

  // Ustaw dane dla popup (przez chrome.storage.session lub window).
  chrome.storage.local.set({ jobhunter_current_offer: offer });
})();
