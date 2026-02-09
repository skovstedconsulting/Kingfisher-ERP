(function () {
  const bc = new BroadcastChannel("kf_inbox_preview");

  function getCookie(name) {
    const value = `; ${document.cookie}`;
    const parts = value.split(`; ${name}=`);
    if (parts.length === 2) return parts.pop().split(";").shift();
    return "";
  }
  const csrftoken = getCookie("csrftoken");

  function postToPopout({ title, url, view_url }) {
    bc.postMessage({
      type: "show_attachment",
      title: title || "",
      url: url || "",
      view_url: view_url || "",
    });
  }

  function setPreviewToUrl(url, isPdf) {
    const wrap = document.getElementById("kf-preview-wrap");
    if (!wrap) return;

    wrap.innerHTML = "";

    if (isPdf) {
      const iframe = document.createElement("iframe");
      iframe.src = url;
      iframe.style.width = "100%";
      iframe.style.height = "calc(100vh - 220px)";
      iframe.style.border = "1px solid #ddd";
      iframe.style.borderRadius = "10px";
      iframe.style.background = "#fff";
      wrap.appendChild(iframe);
    } else {
      const img = document.createElement("img");
      img.src = url;
      img.style.maxWidth = "100%";
      img.style.height = "auto";
      img.style.border = "1px solid #ddd";
      img.style.borderRadius = "10px";
      img.style.background = "#fff";
      wrap.appendChild(img);
    }
  }

  // ---------- Selection / attachment clicks ----------
  function setSelectedAttachment(btn) {
    document
      .querySelectorAll(".kf-attachment-btn")
      .forEach((b) => b.classList.remove("kf-selected-attachment"));
    btn.classList.add("kf-selected-attachment");
  }

  document.addEventListener("click", (e) => {
    const btn = e.target.closest(".kf-attachment-btn");
    if (!btn) return;

    setSelectedAttachment(btn);

    const rawUrl = btn.getAttribute("data-url") || "";
    const viewUrl = btn.getAttribute("data-view-url") || "";

    // PDF detection: if viewUrl exists, we treat it as PDF-safe
    const isPdf = !!viewUrl;
    const chosen = isPdf ? viewUrl : rawUrl;

    if (chosen) {
      setPreviewToUrl(chosen, isPdf);
      postToPopout({
        title: (btn.textContent || "").trim(),
        url: rawUrl,
        view_url: viewUrl,
      });
    }
  });

  // Select row
  document.querySelectorAll(".kf-inbox-row").forEach((row) => {
    row.addEventListener("click", () => {
      const docId = row.getAttribute("data-doc-id");
      const u = new URL(window.location.href);
      u.searchParams.set("selected", docId);
      window.location.href = u.toString();
    });
  });

  // Toggle preview
  document.getElementById("kf-toggle-preview")?.addEventListener("click", () => {
    const wrap = document.getElementById("kf-preview-wrap");
    if (!wrap) return;
    const hidden = wrap.style.display === "none";
    wrap.style.display = hidden ? "" : "none";
    document.getElementById("kf-toggle-preview").textContent = hidden
      ? "Hide preview"
      : "Show preview";
  });

  // Popout: open window and immediately send selected attachment
  document.getElementById("kf-popout-btn")?.addEventListener("click", () => {
    const selectedBtn = document.querySelector(
      ".kf-attachment-btn.kf-selected-attachment"
    );
    if (!selectedBtn) return;

    const attachmentId = selectedBtn.getAttribute("data-attachment-id");
    if (!attachmentId) return;

    const popoutUrl = `/inbox/attachment/${attachmentId}/popout/`;

    const width = Math.min(1200, screen.width * 0.9);
    const height = Math.min(900, screen.height * 0.9);
    const left = (screen.width - width) / 2;
    const top = (screen.height - height) / 2;

    const win = window.open(
      popoutUrl,
      "kf_inbox_popout",
      `popup=yes,width=${width},height=${height},left=${left},top=${top},resizable=yes,scrollbars=yes,toolbar=no,menubar=no,location=no,status=no,noopener,noreferrer`
    );
    if (win) win.focus();

    postToPopout({
      title: (selectedBtn.textContent || "").trim(),
      url: selectedBtn.getAttribute("data-url") || "",
      view_url: selectedBtn.getAttribute("data-view-url") || "",
    });
  });

  // ---------- Drag & drop ----------
  function bindDropZone(el, onFiles) {
    if (!el) return;
    el.addEventListener("dragover", (e) => {
      e.preventDefault();
      el.style.background = "#f5f7ff";
    });
    el.addEventListener("dragleave", () => {
      el.style.background = "";
    });
    el.addEventListener("drop", (e) => {
      e.preventDefault();
      el.style.background = "";
      const files = Array.from(e.dataTransfer.files || []);
      onFiles(files);
    });
  }

  // Create via Django view (so filename->title runs)
  async function uploadCreateToDjango(files) {
    if (!files || !files.length) return;

    const drop = document.getElementById("kf-drop-create");
    const createUrl = drop?.dataset.createUrl;
    if (!createUrl) throw new Error("Missing data-create-url on #kf-drop-create");

    const fd = new FormData();

    // MUST be a valid choice value in your model; keep your previous 'other' if that's valid
    fd.append("doc_type", "other");
    fd.append("title", ""); // blank -> server uses filename

    // IMPORTANT: append ALL files as "file" (matches request.FILES.getlist("file"))
    for (const f of files) fd.append("file", f);

    const resp = await fetch(createUrl, {
      method: "POST",
      headers: { "X-CSRFToken": csrftoken },
      body: fd,
      credentials: "same-origin",
    });

    // inbox_create redirects to inbox:list?selected=...
    if (resp.redirected) {
      window.location.href = resp.url;
      return;
    }

    // If not redirected, fallback refresh
    window.location.reload();
  }

  // Attach still uses your API (fine)
  const selectedRow = document.querySelector(".kf-inbox-row[style*='background']");
  const selectedId = selectedRow?.getAttribute("data-doc-id") || "";

  async function uploadAttach(docId, files) {
    if (!docId || !files || !files.length) return;

    for (let i = 0; i < files.length; i++) {
      const fd = new FormData();
      fd.append("file", files[i]);
      fd.append("is_primary", "false");
      const resp = await fetch(`/api/inbox/documents/${docId}/attach/`, {
        method: "POST",
        headers: { "X-CSRFToken": csrftoken },
        body: fd,
        credentials: "same-origin",
      });
      if (!resp.ok) throw new Error("Attach failed");
    }
    window.location.reload();
  }

  // Create drop zone + file input
  bindDropZone(document.getElementById("kf-drop-create"), (files) => {
    uploadCreateToDjango(files).catch((err) =>
      alert(err.message || "Upload failed")
    );
  });

  const createInput = document.getElementById("kf-file-create");
  if (createInput) {
    createInput.addEventListener("change", () => {
      uploadCreateToDjango(Array.from(createInput.files || [])).catch((err) =>
        alert(err.message || "Upload failed")
      );
    });
  }

  // Attach drop zone + file input
  bindDropZone(document.getElementById("kf-drop-attach"), (files) => {
    uploadAttach(selectedId, files).catch((err) =>
      alert(err.message || "Attach failed")
    );
  });

  const attachInput = document.getElementById("kf-file-attach");
  if (attachInput) {
    attachInput.addEventListener("change", () => {
      uploadAttach(selectedId, Array.from(attachInput.files || [])).catch(
        (err) => alert(err.message || "Attach failed")
      );
    });
  }

  // Popout ready: resend current selected attachment (prefer selected button)
  bc.onmessage = (e) => {
    const msg = e.data || {};
    if (msg.type === "popout_ready") {
      const selectedBtn = document.querySelector(
        ".kf-attachment-btn.kf-selected-attachment"
      );
      if (selectedBtn) {
        postToPopout({
          title: (selectedBtn.textContent || "").trim(),
          url: selectedBtn.getAttribute("data-url") || "",
          view_url: selectedBtn.getAttribute("data-view-url") || "",
        });
      }
    }
  };
})();
