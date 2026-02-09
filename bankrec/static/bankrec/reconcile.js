(function () {
  "use strict";
  console.log("reconcile js loaded");

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }
  const csrftoken = getCookie("csrftoken");

  // --- Load existing matches from <script id="match-map"> ---
  const matchMapEl = document.getElementById("match-map");
  const matchPairs = matchMapEl ? (JSON.parse(matchMapEl.textContent || "{}").pairs || []) : [];

  // Quick lookup:
  // bankId -> { glId, matchId }
  // glId   -> { bankId, matchId }
  const bankToGl = new Map();
  const glToBank = new Map();

  for (const p of matchPairs) {
    bankToGl.set(String(p.bank_id), { glId: String(p.gl_id), matchId: String(p.match_id) });
    glToBank.set(String(p.gl_id), { bankId: String(p.bank_id), matchId: String(p.match_id) });
  }

  const byId = (id) => document.getElementById(id);

  function ensureTick(el) {
    if (!el) return;
    if (!el.querySelector(".tick")) {
      el.insertAdjacentHTML("beforeend", `<span class="tick" aria-hidden="true">✓</span>`);
    }
  }

  function setMatchedUI(bankId, glId, matchId) {
    const bankEl = byId(`bank-${bankId}`);
    const glEl = byId(`gl-${glId}`);
    if (!bankEl || !glEl) return;

    bankEl.classList.add("is-matched");
    glEl.classList.add("is-matched");

    bankEl.dataset.matchId = matchId;
    glEl.dataset.matchId = matchId;

    bankEl.dataset.matchedWith = glId;  // bank -> gl
    glEl.dataset.matchedWith = bankId;  // gl -> bank

    ensureTick(bankEl);
    ensureTick(glEl);
  }

  function clearHover() {
    document.querySelectorAll(".is-hover-pair").forEach(el => el.classList.remove("is-hover-pair"));
  }

  function highlightPair(el) {
    clearHover();

    const id = el.dataset.id;
    if (!id) return;

    if (el.classList.contains("bank-line")) {
      const rel = bankToGl.get(String(id));
      if (!rel) return;
      byId(`bank-${id}`)?.classList.add("is-hover-pair");
      byId(`gl-${rel.glId}`)?.classList.add("is-hover-pair");
    } else if (el.classList.contains("gl-line")) {
      const rel = glToBank.get(String(id));
      if (!rel) return;
      byId(`gl-${id}`)?.classList.add("is-hover-pair");
      byId(`bank-${rel.bankId}`)?.classList.add("is-hover-pair");
    }
  }

  // Initialize already-matched UI (✓ + matched class)
  for (const p of matchPairs) {
    setMatchedUI(String(p.bank_id), String(p.gl_id), String(p.match_id));
  }

  // --------------------------
  // Drag: GL -> Bank
  // --------------------------

let selectedBank = new Set();
let selectedGl = new Set();

function toggleSelect(el, set) {
  const id = String(el.dataset.id);
  if (set.has(id)) {
    set.delete(id);
    el.classList.remove("is-selected");
  } else {
    set.add(id);
    el.classList.add("is-selected");
  }
}

document.querySelectorAll(".bank-line").forEach(el => {
  el.addEventListener("click", () => toggleSelect(el, selectedBank));
});

document.querySelectorAll(".gl-line").forEach(el => {
  el.addEventListener("click", () => toggleSelect(el, selectedGl));
});

// match button
document.getElementById("match-btn").addEventListener("click", () => {
  if (!selectedBank.size || !selectedGl.size) {
    alert("Vælg mindst én bankpost og mindst én finanspost");
    return;
  }
  createMatchMulti([...selectedBank], [...selectedGl]);
});

function createMatchMulti(bankIds, glIds) {
  fetch(window.MATCH_CREATE_URL, {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-CSRFToken": csrftoken },
    body: JSON.stringify({
      bank_line_ids: bankIds.map(Number),
      gl_line_ids: glIds.map(Number),
    }),
  })
  .then(async r => ({ okHttp: r.ok, data: await r.json().catch(() => null) }))
  .then(({ okHttp, data }) => {
    if (!data) return alert("Teknisk fejl");
    if (data.error === "amount_mismatch") {
      alert(`Beløb stemmer ikke:\nBank: ${data.bank_amount}\nFinans: ${data.gl_amount}`);
      return;
    }
    if (data.error === "already_matched") {
      const what = data.kind === "bank" ? "Bankpost" : "Finanspost";
      alert(`${what} er allerede afstemt og kan ikke matches igen.`);
      return;
    }
    if (!okHttp || !data.ok) return alert("Kunne ikke oprette match");

    // ✅ markér alle involverede linjer som matched (✓ osv.)
    for (const b of (data.bank_lines || [])) {
      const el = document.getElementById(`bank-${b}`);
      el?.classList.add("is-matched");
      ensureTick(el);
    }

    for (const g of (data.gl_lines || [])) {
      const el = document.getElementById(`gl-${g}`);
      el?.classList.add("is-matched");
      ensureTick(el);
    }

    // ryd selection
    document.querySelectorAll(".is-selected").forEach(x => x.classList.remove("is-selected"));
    selectedBank.clear();
    selectedGl.clear();

    // (valgfrit) opdater matches-listen i bunden uden reload (append row)
  });
}


  // GL lines are draggable
  document.querySelectorAll(".gl-line").forEach(glEl => {
    glEl.addEventListener("dragstart", e => {
      e.dataTransfer.setData(
        "application/json",
        JSON.stringify({ gl_line_id: glEl.dataset.id })
      );
      glEl.classList.add("dragging");
    });

    glEl.addEventListener("dragend", () => {
      glEl.classList.remove("dragging");
    });

    // Hover highlight (only if matched)
    glEl.addEventListener("mouseenter", () => highlightPair(glEl));
    glEl.addEventListener("mouseleave", clearHover);
  });

  // Bank lines are drop targets (NOT draggable)
  document.querySelectorAll(".bank-line").forEach(bankEl => {
    bankEl.addEventListener("dragover", e => {
      e.preventDefault();
      bankEl.classList.add("drag-over");
    });

    bankEl.addEventListener("dragleave", () => {
      bankEl.classList.remove("drag-over");
    });

    bankEl.addEventListener("drop", e => {
      e.preventDefault();
      bankEl.classList.remove("drag-over");

      const payloadRaw = e.dataTransfer.getData("application/json") || "{}";
      let data;
      try {
        data = JSON.parse(payloadRaw);
      } catch {
        return;
      }

      const glLineId = data.gl_line_id;
      const bankLineId = bankEl.dataset.id;

      if (!glLineId || !bankLineId) return;

      createMatch(bankLineId, glLineId);
    });

    // Hover highlight (only if matched)
    bankEl.addEventListener("mouseenter", () => highlightPair(bankEl));
    bankEl.addEventListener("mouseleave", clearHover);
  });

function createMatch(bankLineId, glLineId) {
  fetch(window.MATCH_CREATE_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-CSRFToken": csrftoken,
    },
    body: JSON.stringify({
      bank_line_id: bankLineId,
      gl_line_id: glLineId,
    }),
  })
    .then(async (r) => {
      // Parse JSON even if status is 400
      let data = null;
      try {
        data = await r.json();
      } catch {
        data = null;
      }
      return { okHttp: r.ok, status: r.status, data };
    })
    .then(({ okHttp, data }) => {
      if (!data) {
        alert("Teknisk fejl: ugyldigt svar fra server");
        return;
      }

      // Business-level error from backend (e.g. amount mismatch)
      if (data.error === "amount_mismatch") {
        alert(`Beløb stemmer ikke:\nBank: ${data.bank_amount}\nFinans: ${data.gl_amount}`);
        return;
      }

      // Generic failure
      if (!okHttp || !data.ok) {
        alert("Kunne ikke oprette match");
        return;
      }

      // Success
      const matchId = String(data.match_id || "");

      bankToGl.set(String(bankLineId), { glId: String(glLineId), matchId });
      glToBank.set(String(glLineId), { bankId: String(bankLineId), matchId });

      setMatchedUI(String(bankLineId), String(glLineId), matchId);
    })
    .catch((err) => {
      console.error(err);
      alert("Teknisk fejl ved match");
    });
}

  // Unmatch (keep your existing behavior: reload after delete)
  document.querySelectorAll(".unmatch-btn").forEach(btn => {
    btn.addEventListener("click", () => {
      if (!confirm("Fjern dette match?")) return;

      fetch(window.MATCH_DELETE_URL, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-CSRFToken": csrftoken,
        },
        body: JSON.stringify({ match_id: btn.dataset.matchId }),
      })
        .then(r => r.json())
        .then(data => {
          if (data && data.ok) window.location.reload();
        })
        .catch(err => console.error(err));
    });
  });
})();
