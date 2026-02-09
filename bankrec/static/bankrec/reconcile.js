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

  // --------------------------
  // Matches: many-to-many safe maps
  // --------------------------

  const matchMapEl = document.getElementById("match-map");
  const matchMapRaw = matchMapEl ? JSON.parse(matchMapEl.textContent || "{}") : {};

  // Backwards compat:
  // old: { pairs: [{bank_id, gl_id, match_id}, ...] }
  // new: { matches: [{match_id, bank_ids:[..], gl_ids:[..]}, ...] }
  const matchPairs = matchMapRaw?.pairs || [];
  const matchGroups = matchMapRaw?.matches || [];

  // matchId -> { bankIds:Set<string>, glIds:Set<string> }
  const matchIdToGroup = new Map();

  // bankId -> Set<matchId>
  const bankToMatchIds = new Map();

  // glId -> Set<matchId>
  const glToMatchIds = new Map();

  const byId = (id) => document.getElementById(id);

  function mapAddSet(map, key, val) {
    key = String(key);
    val = String(val);
    if (!map.has(key)) map.set(key, new Set());
    map.get(key).add(val);
  }

  function ensureGroup(matchId) {
    matchId = String(matchId);
    if (!matchIdToGroup.has(matchId)) {
      matchIdToGroup.set(matchId, { bankIds: new Set(), glIds: new Set() });
    }
    return matchIdToGroup.get(matchId);
  }

  function addRelation(matchId, bankId, glId) {
    matchId = String(matchId);
    bankId = String(bankId);
    glId = String(glId);

    const g = ensureGroup(matchId);
    g.bankIds.add(bankId);
    g.glIds.add(glId);

    mapAddSet(bankToMatchIds, bankId, matchId);
    mapAddSet(glToMatchIds, glId, matchId);
  }

  // Ingest NEW grouped format
  for (const m of matchGroups) {
    const matchId = m.match_id ?? m.id;
    if (!matchId) continue;

    const bankIds = (m.bank_ids || m.bank_lines || []);
    const glIds = (m.gl_ids || m.gl_lines || []);

    const g = ensureGroup(matchId);
    for (const b of bankIds) {
      g.bankIds.add(String(b));
      mapAddSet(bankToMatchIds, b, matchId);
    }
    for (const gl of glIds) {
      g.glIds.add(String(gl));
      mapAddSet(glToMatchIds, gl, matchId);
    }
  }

  // Ingest OLD pairs format
  for (const p of matchPairs) {
    if (!p) continue;
    addRelation(p.match_id, p.bank_id, p.gl_id);
  }

  function ensureTick(el) {
    if (!el) return;
    if (!el.querySelector(".tick")) {
      el.insertAdjacentHTML("beforeend", `<span class="tick" aria-hidden="true">✓</span>`);
    }
  }

  function markMatched(el, matchId) {
    if (!el) return;
    el.classList.add("is-matched");
    ensureTick(el);

    // store one or more match ids (comma separated)
    const cur = (el.dataset.matchIds || "")
      .split(",")
      .map(s => s.trim())
      .filter(Boolean);
    if (!cur.includes(String(matchId))) cur.push(String(matchId));
    el.dataset.matchIds = cur.join(",");
  }

  function applyMatchedUIFromMaps() {
    for (const [matchId, grp] of matchIdToGroup.entries()) {
      for (const b of grp.bankIds) markMatched(byId(`bank-${b}`), matchId);
      for (const g of grp.glIds) markMatched(byId(`gl-${g}`), matchId);
    }
  }

  function clearHover() {
    document.querySelectorAll(".is-hover-pair").forEach(el => el.classList.remove("is-hover-pair"));
  }

  function highlightByMatchIds(matchIds) {
    clearHover();
    if (!matchIds || matchIds.size === 0) return;

    for (const mid of matchIds) {
      const grp = matchIdToGroup.get(String(mid));
      if (!grp) continue;

      for (const b of grp.bankIds) byId(`bank-${b}`)?.classList.add("is-hover-pair");
      for (const g of grp.glIds) byId(`gl-${g}`)?.classList.add("is-hover-pair");
    }
  }

  function highlightPair(el) {
    const id = el?.dataset?.id;
    if (!id) return;

    if (el.classList.contains("bank-line")) {
      highlightByMatchIds(bankToMatchIds.get(String(id)) || new Set());
    } else if (el.classList.contains("gl-line")) {
      highlightByMatchIds(glToMatchIds.get(String(id)) || new Set());
    }
  }

  // Initialize already-matched UI (✓ + matched class)
  applyMatchedUIFromMaps();

  // --------------------------
  // Multi-select (click) matching
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

  const matchBtn = document.getElementById("match-btn");
  if (matchBtn) {
    matchBtn.addEventListener("click", () => {
      if (!selectedBank.size || !selectedGl.size) {
        alert("Vælg mindst én bankpost og mindst én finanspost");
        return;
      }
      createMatchMulti([...selectedBank], [...selectedGl]);
    });
  }

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

        const matchId = String(data.match_id || "");
        const bankLines = data.bank_lines || [];
        const glLines = data.gl_lines || [];

        // Update maps so hover-highlighting works without reload
        const grp = ensureGroup(matchId);
        for (const b of bankLines) {
          grp.bankIds.add(String(b));
          mapAddSet(bankToMatchIds, b, matchId);
          markMatched(byId(`bank-${b}`), matchId);
        }
        for (const g of glLines) {
          grp.glIds.add(String(g));
          mapAddSet(glToMatchIds, g, matchId);
          markMatched(byId(`gl-${g}`), matchId);
        }

        // clear selection UI
        document.querySelectorAll(".is-selected").forEach(x => x.classList.remove("is-selected"));
        selectedBank.clear();
        selectedGl.clear();
      })
      .catch(err => {
        console.error(err);
        alert("Teknisk fejl");
      });
  }

  // --------------------------
  // Drag: GL -> Bank (single)
  // --------------------------

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

    // Hover highlight
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

    // Hover highlight
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

        if (data.error === "amount_mismatch") {
          alert(`Beløb stemmer ikke:\nBank: ${data.bank_amount}\nFinans: ${data.gl_amount}`);
          return;
        }
        if (data.error === "already_matched") {
          const what = data.kind === "bank" ? "Bankpost" : "Finanspost";
          alert(`${what} er allerede afstemt og kan ikke matches igen.`);
          return;
        }

        if (!okHttp || !data.ok) {
          alert("Kunne ikke oprette match");
          return;
        }

        const matchId = String(data.match_id || "");
        const bankLines = data.bank_lines || [String(bankLineId)];
        const glLines = data.gl_lines || [String(glLineId)];

        // Update maps + UI
        const grp = ensureGroup(matchId);
        for (const b of bankLines) {
          grp.bankIds.add(String(b));
          mapAddSet(bankToMatchIds, b, matchId);
          markMatched(byId(`bank-${b}`), matchId);
        }
        for (const g of glLines) {
          grp.glIds.add(String(g));
          mapAddSet(glToMatchIds, g, matchId);
          markMatched(byId(`gl-${g}`), matchId);
        }
      })
      .catch((err) => {
        console.error(err);
        alert("Teknisk fejl ved match");
      });
  }

  // --------------------------
  // Unmatch (reload after delete)
  // --------------------------

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
