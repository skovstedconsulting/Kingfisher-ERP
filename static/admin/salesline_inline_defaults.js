(function () {
  // ----- helpers (no jQuery needed yet) -----
  function waitForAdminJquery(triesLeft) {
    if (window.django && window.django.jQuery) return init(window.django.jQuery);
    if (triesLeft <= 0) {
      console.warn("salesline_inline_defaults: django.jQuery never became available");
      return;
    }
    setTimeout(function () { waitForAdminJquery(triesLeft - 1); }, 50);
  }

  // start waiting (max ~5 seconds)
  waitForAdminJquery(100);

  // ----- main -----
  function init($) {
    const ITEM_SEL = 'tr.form-row select[id$="-item"]';
    const LINE_SEL = 'input[id$="-line_no"]';
    const DESC_SEL = 'input[id$="-description"]';
    const PRICE_SEL = 'input[id$="-unit_price_tx"]';

    // Cache defaults per itemId to avoid repeated fetches
    const defaultsCache = new Map();

function getAdminBasePath() {
  // Examples:
  // /admin/sales/salesoffer/123/change/  -> /admin/sales/salesoffer/
  // /admin/sales/salesoffer/add/         -> /admin/sales/salesoffer/
  const p = window.location.pathname;

  // change page
  let m = p.match(/^(.*\/)[0-9]+\/change\/$/);
  if (m) return m[1];

  // add page
  m = p.match(/^(.*\/)add\/$/);
  if (m) return m[1];

  // fallback: assume current directory
  return p.endsWith("/") ? p : (p + "/");
}

const adminBasePath = getAdminBasePath();

function getDefaults(itemId) {
  if (!itemId) return Promise.resolve(null);
  const key = String(itemId);

  if (defaultsCache.has(key)) return defaultsCache.get(key);

  const url = `${adminBasePath}item-defaults/${encodeURIComponent(key)}/`;

  const p = fetch(url, { credentials: "same-origin" })
    .then(r => (r.ok ? r.json() : null))
    .catch(() => null);

  defaultsCache.set(key, p);
  return p;
}


    function applyDefaults($row, data) {
      if (!data) return;

      const $desc = $row.find(DESC_SEL);
      const $price = $row.find(PRICE_SEL);

      if ($desc.length) $desc.val(data.description || "");
      if ($price.length) $price.val(data.unit_price_tx || "0.00");
    }

    function ensureNextLineNo($table) {
      // We store the next available number on the table to avoid rescanning every time.
      let next = parseInt($table.data("nextLineNo"), 10);
      if (!isNaN(next) && next > 0) return next;

      // Initialize by scanning existing values once
      let max = 0;
      $table.find(LINE_SEL).each(function () {
        const v = parseInt(this.value, 10);
        if (!isNaN(v) && v > max) max = v;
      });

      next = max + 10;
      $table.data("nextLineNo", next);
      return next;
    }

    function allocateLineNo($row) {
      const $lineNo = $row.find(LINE_SEL);
      if (!$lineNo.length) return;

      // If already set (or deleted row), do nothing
      const current = ($lineNo.val() || "").trim();
      if (current) return;

      const $table = $row.closest("table");
      const next = ensureNextLineNo($table);

      $lineNo.val(next);
      $table.data("nextLineNo", next + 10);
    }

    function handleItemChange(el) {
      const $el = $(el);
      const itemId = $el.val();
      const $row = $el.closest("tr.form-row");

      // Optional: also allocate line number when item is chosen
      allocateLineNo($row);

      getDefaults(itemId).then(data => applyDefaults($row, data));
    }

    function handleNewRow($row) {
      allocateLineNo($row);

      const $item = $row.find(ITEM_SEL);
      if ($item.length && $item.val()) {
        handleItemChange($item[0]);
      }
    }

    // --- event handlers for item selection ---
    // Normal dropdowns
    $(document).on("change", ITEM_SEL, function () { handleItemChange(this); });

    // autocomplete_fields (Select2)
    $(document).on("select2:select", ITEM_SEL, function () { handleItemChange(this); });

    // --- new row added (Django event) ---
    $(document).on("formset:added", function (event, row) {
      const $row = row ? (row.jquery ? row : $(row)) : null;
      if ($row && $row.length) handleNewRow($row);
    });

    // --- new row added (MutationObserver fallback) ---
    document.querySelectorAll(".inline-group tbody").forEach(function (tbody) {
      const obs = new MutationObserver(function (mutations) {
        for (const m of mutations) {
          for (const node of m.addedNodes) {
            if (!(node instanceof HTMLElement)) continue;

            if (node.matches && node.matches("tr.form-row")) {
              handleNewRow($(node));
            } else if (node.querySelectorAll) {
              node.querySelectorAll("tr.form-row").forEach(tr => handleNewRow($(tr)));
            }
          }
        }
      });

      obs.observe(tbody, { childList: true });
    });
  }
})();
