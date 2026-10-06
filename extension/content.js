/**
 * Shadow AI DLP Guard - Content Script Interceptor (extension/content.js)
 * Intercepta eventos submit en ChatGPT, Claude y Gemini en tiempo real (<50ms).
 */

(function () {
  if (globalThis.__aegisDlpGuard) return;
  globalThis.__aegisDlpGuard = true;
  const isSandbox = ["http://127.0.0.1:8000", "http://localhost:8000"].includes(location.origin) && /^\/sandbox(?:\/|$)/.test(location.pathname);
  const isChatGPT = location.hostname === "chatgpt.com" || location.hostname.endsWith(".chatgpt.com") ||
    location.hostname === "chat.openai.com";
  const isClaude = location.hostname === "claude.ai" || location.hostname.endsWith(".claude.ai");
  const isGemini = location.hostname === "gemini.google.com";
  const isOtherGenAi = new Set([
    "copilot.microsoft.com", "www.perplexity.ai", "grok.com", "chat.mistral.ai",
    "chat.deepseek.com", "poe.com", "you.com"
  ]).has(location.hostname) || (location.hostname === "x.com" && location.pathname.startsWith("/i/grok"));
  console.log("%c[DLP Guard] Activo en " + window.location.hostname, "color: #00f0ff; font-weight: bold;");

  // Aegis must never authorize a send that it could not inspect. All protected
  // GenAI surfaces therefore use the same fail-closed path.
  const strictInterception = isChatGPT || isClaude || isGemini || isOtherGenAi || isSandbox;
  let isAuditing = false;
  let bypassNextSubmit = false;
  let cachedInput = null;
  const approvedFileInputs = new WeakSet();
  const INSPECTABLE_FILE_TYPES = new Set([
    "txt", "md", "csv", "tsv", "json", "xml", "html", "css", "js", "ts", "py",
    "java", "c", "cpp", "cs", "sql", "yaml", "yml", "log", "rst"
  ]);
  const MAX_INSPECTABLE_FILE_BYTES = 512 * 1024;
  const INPUT_SELECTOR = "#prompt-textarea, main div[contenteditable='true'], div[contenteditable='true'], textarea, [role='textbox']";
  const SEND_BUTTON_SELECTOR = "button[data-testid*='send'], button[data-test-id*='send'], button[aria-label*='Send'], button[aria-label*='Enviar'], button[aria-label*='Submit'], button[type='submit']";
  const chatGPTSendSelector = "button#composer-submit-button, " + SEND_BUTTON_SELECTOR;
  const eventRoot = strictInterception ? window : document;

  // Generar ID anónimo persistente por sesión de navegador
  let anonymousUserId = crypto.randomUUID();
  chrome.storage.local.get("anonymousUserId").then(({ anonymousUserId: saved }) => {
    anonymousUserId = saved || crypto.randomUUID();
    if (!saved) chrome.storage.local.set({ anonymousUserId });
  }).catch(error => console.warn("[DLP Guard] Identidad temporal activa:", error));

  // Localizar campo de entrada en ChatGPT, Claude o Gemini
  function findInputElement() {
    if (strictInterception) {
      // querySelector with a comma list follows DOM order, not selector priority.
      for (const selector of ["#prompt-textarea", "textarea[name='prompt-textarea']", "main [contenteditable='true']", "main [contenteditable='plaintext-only']", "main textarea"]) {
        const input = [...document.querySelectorAll(selector)].find(el =>
          el.getClientRects().length && !el.disabled && el.getAttribute("aria-hidden") !== "true" &&
          getComputedStyle(el).visibility !== "hidden");
        if (input) return (cachedInput = input);
      }
      return (cachedInput = null);
    }
    cachedInput = document.querySelector(INPUT_SELECTOR);
    return cachedInput;
  }

  const observer = new MutationObserver(() => {
    if (!cachedInput || !document.contains(cachedInput)) findInputElement();
  });
  observer.observe(document.documentElement, { childList: true, subtree: true });

  function findSendButton() {
    return document.querySelector(SEND_BUTTON_SELECTOR);
  }

  function resumeSubmission(inputEl, sendBtn) {
    if (strictInterception) {
      // Bypass only the synchronous approved click and its default submit event.
      bypassNextSubmit = true;
      try {
        const button = (sendBtn?.isConnected && sendBtn) ||
          (inputEl.closest("form") || document).querySelector(chatGPTSendSelector);
        if (button && !button.disabled) button.click();
        else inputEl.closest("form")?.requestSubmit();
      } finally {
        bypassNextSubmit = false;
      }
      return;
    }
    bypassNextSubmit = true;
    const button = sendBtn || findSendButton();
    if (button && !button.disabled) button.click();
    else {
      const form = inputEl?.closest("form");
      if (form) form.requestSubmit();
      else inputEl?.dispatchEvent(new InputEvent("input", { bubbles: true, inputType: "insertText" }));
    }
    setTimeout(() => { bypassNextSubmit = false; }, 750);
  }

  function showConsentBanner() {
    const key = `policyAccepted:${location.hostname}`;
    chrome.storage.local.get(key).then(result => {
      if (result[key]) return;
      const banner = document.createElement("div");
      banner.id = "aegis-policy-banner";
      banner.setAttribute("role", "status");
      banner.innerHTML = `<span>🛡️ Política TIC activa: los prompts se inspeccionan localmente para prevenir fugas.</span><button type="button">Entendido</button>`;
      Object.assign(banner.style, { position:"fixed", bottom:"16px", left:"50%", transform:"translateX(-50%)",
        zIndex:"2147483647", background:"#0f172a", color:"white", padding:"12px 16px", borderRadius:"10px",
        display:"flex", gap:"14px", alignItems:"center", boxShadow:"0 8px 30px #0008", font:"14px system-ui" });
      banner.querySelector("button").addEventListener("click", () => {
        chrome.storage.local.set({ [key]: true }); banner.remove();
      });
      document.body.appendChild(banner);
    });
  }
  if (document.body) showConsentBanner();
  else document.addEventListener("DOMContentLoaded", showConsentBanner, { once: true });

  function showAuditError(message) {
    document.getElementById("aegis-audit-error")?.remove();
    const notice = document.createElement("div");
    notice.id = "aegis-audit-error";
    notice.setAttribute("role", "alert");
    notice.textContent = message;
    Object.assign(notice.style, { position: "fixed", top: "16px", left: "50%", transform: "translateX(-50%)",
      zIndex: "2147483647", background: "#7f1d1d", color: "white", padding: "16px", borderRadius: "10px", font: "14px system-ui" });
    notice.addEventListener("click", () => notice.remove());
    document.body.appendChild(notice);
  }

  // Extraer texto del campo
  function getPromptText(el) {
    if (!el) return "";
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
      return el.value.trim();
    }
    return (el.innerText || el.textContent || "").trim();
  }

  function hasSelectedAttachment() {
    return [...document.querySelectorAll("input[type='file']")].some(input => input.files?.length > 0);
  }

  function blockAttachment(message) {
    showAuditError(message || "Envío detenido: los adjuntos, imágenes y archivos no se pueden enviar a una IA externa.");
  }

  function fileExtension(file) {
    return (file.name.split(".").pop() || "").toLowerCase();
  }

  async function auditFilesAndRelease(input, files) {
    if (isAuditing) return;
    if (!files.length || files.length > 3) {
      input.value = "";
      blockAttachment("Carga bloqueada: adjunta entre 1 y 3 archivos por vez para poder inspeccionarlos.");
      return;
    }
    const unsupported = files.find(file => !INSPECTABLE_FILE_TYPES.has(fileExtension(file)) || file.size > MAX_INSPECTABLE_FILE_BYTES);
    if (unsupported) {
      input.value = "";
      blockAttachment(`Carga bloqueada: ${unsupported.name} no puede inspeccionarse localmente. Solo se permiten archivos de texto/código/CSV/JSON de hasta 512 KB.`);
      return;
    }
    isAuditing = true;
    try {
      const contents = await Promise.all(files.map(async file => ({ name: file.name, text: await file.text() })));
      // Inspect all the file, in overlapping fragments compatible with the
      // API prompt limit. A sensitive value cannot hide after the first 4 KB.
      for (const file of contents) {
        const chunkSize = 3400;
        for (let start = 0; start < file.text.length; start += chunkSize - 200) {
          const auditText = `[ADJUNTO_LOCAL:${file.name}:segmento ${start}]\n${file.text.slice(start, start + chunkSize)}`;
          const response = await chrome.runtime.sendMessage({ type: "AEGIS_AUDIT", payload: {
            user_id: anonymousUserId,
            prompt: auditText,
            destination: isSandbox ? window.location.origin + "/sandbox" : window.location.origin
          }});
          if (!response?.ok || response.data?.action !== "ALLOW") {
            input.value = "";
            if (response?.data?.action === "BLOCK") showBlockModal(response.data, auditText);
            else blockAttachment("Carga detenida: no se pudo completar la auditoría local del archivo.");
            return;
          }
          if (start + chunkSize >= file.text.length) break;
        }
      }
      // The original event was stopped while inspection ran. Re-dispatch only
      // after an ALLOW; pages receive the same selected FileList and may queue it.
      approvedFileInputs.add(input);
      input.dispatchEvent(new Event("change", { bubbles: true }));
      showAuditError("Archivo revisado localmente y autorizado para adjuntar.");
    } catch (error) {
      input.value = "";
      blockAttachment(`Carga detenida: ${error.message}`);
    } finally {
      isAuditing = false;
    }
  }

  // Limpiar el campo cuando se bloquea
  function clearInputElement(el) {
    if (!el) return;
    if (el.tagName === "TEXTAREA" || el.tagName === "INPUT") {
      el.value = "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
    } else {
      el.innerText = "";
      el.innerHTML = "";
      el.dispatchEvent(new Event("input", { bubbles: true }));
    }
  }

  // Desplegar Modal Animado de Bloqueo
  function showBlockModal(data, originalPrompt) {
    // Eliminar modal anterior si existe
    const existing = document.getElementById("dlp-guard-modal-root");
    if (existing) existing.remove();

    const root = document.createElement("div");
    root.id = "dlp-guard-modal-root";
    root.className = "dlp-overlay-fadeIn";

    const categoryLabels = {
      Business_Secrets: "Secretos de Negocio / Excel Corporativo",
      PII_Leak: "Filtración de Datos Personales (PII)",
      Proprietary_Code: "Código Propietario / Secretos Técnicos",
      Safe_Use: "Uso Seguro"
    };

    const catTitle = categoryLabels[data.category] || data.category;
    const riskPct = Math.round(data.risk_score * 100);

    root.innerHTML = `
      <div class="dlp-modal-card" role="dialog" aria-modal="true" aria-labelledby="dlp-title">
        <div class="dlp-modal-glow"></div>
        <div class="dlp-modal-header">
          <div class="dlp-alert-badge">
            <span class="dlp-pulse-dot"></span>
            <span>BLOQUEO PREVENTIVO DLP</span>
          </div>
          <button class="dlp-close-btn" id="dlp-modal-close" aria-label="Cerrar">&times;</button>
        </div>

        <div class="dlp-modal-body">
          <div class="dlp-icon-container">
            <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="#ff2a5f" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
              <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"></path>
              <line x1="12" y1="8" x2="12" y2="12"></line>
              <line x1="12" y1="16" x2="12.01" y2="16"></line>
            </svg>
          </div>

          <h2 id="dlp-title" class="dlp-headline">Intento de Fuga de Datos Detectado</h2>
          <p class="dlp-subline">El envío a la IA Generativa ha sido neutralizado por la política corporativa de Gobernanza de TIC.</p>

          <div class="dlp-details-grid">
            <div class="dlp-detail-item">
              <span class="dlp-label">Categoría de Riesgo:</span>
              <span class="dlp-val dlp-highlight">${catTitle}</span>
            </div>
            <div class="dlp-detail-item">
              <span class="dlp-label">Nivel de Riesgo Evaluado:</span>
              <span class="dlp-val dlp-danger">${riskPct}% (Crítico)</span>
            </div>
            <div class="dlp-detail-item full-width">
              <span class="dlp-label">Motivo de Bloqueo:</span>
              <span class="dlp-val">${data.reason || "El prompt contiene datos confidenciales no autorizados."}</span>
            </div>
            <div class="dlp-detail-item full-width">
              <span class="dlp-label">Tiempo de Inferencia Local:</span>
              <span class="dlp-val dlp-metric">${data.inference_time_ms} ms (SLM On-Device)</span>
            </div>
          </div>

          <div class="dlp-compliance-note">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="#00f0ff" stroke-width="2">
              <circle cx="12" cy="12" r="10"></circle>
              <line x1="12" y1="16" x2="12" y2="12"></line>
              <line x1="12" y1="8" x2="12.01" y2="8"></line>
            </svg>
            <span>Evento registrado en bitácora de auditoría SHA-256 conforme a <b>ISO/IEC 42001</b> y <b>EU AI Act</b>.</span>
          </div>
        </div>

        <div class="dlp-modal-footer">
          <button class="dlp-btn-action" id="dlp-btn-ack">Entendido y Cumplir Política</button>
        </div>
      </div>
    `;

    document.body.appendChild(root);

    // Eventos de cierre
    const closeFn = () => root.remove();
    document.getElementById("dlp-modal-close").addEventListener("click", closeFn);
    document.getElementById("dlp-btn-ack").addEventListener("click", closeFn);
    root.addEventListener("click", (e) => {
      if (e.target === root) closeFn();
    });
    document.addEventListener("keydown", function escListener(e) {
      if (e.key === "Escape") {
        closeFn();
        document.removeEventListener("keydown", escListener);
      }
    });
  }

  // Interceptar y auditar
  async function auditAndProcess(text, inputEl, sendBtn) {
    if (isAuditing || bypassNextSubmit || (!text && !hasSelectedAttachment())) return;
    // File contents cannot be inspected safely by a DOM interceptor and some
    // providers upload them before the text submit. Retain them fail-closed.
    if (hasSelectedAttachment()) {
      blockAttachment();
      return;
    }
    isAuditing = true;
    document.getElementById("aegis-audit-error")?.remove();

    try {
      const auditText = text;
      if (strictInterception && auditText.length > 4096) throw new Error("El prompt y su contexto adjunto superan el límite de 4096 caracteres de la API. Divídelo para auditarlo.");
      let auditTimer;
      const request = chrome.runtime.sendMessage({ type: "AEGIS_AUDIT", payload: {
          user_id: anonymousUserId,
          prompt: auditText,
          destination: isSandbox ? window.location.origin + "/sandbox" : window.location.origin
        }});
      const response = await (strictInterception ? Promise.race([request, new Promise((_, reject) => {
        auditTimer = setTimeout(() => reject(new Error("La API no respondió a tiempo.")), 6500);
      })]).finally(() => clearTimeout(auditTimer)) : request);
      if (!response?.ok) throw new Error(response?.error || "Backend unavailable");
      const result = response.data;
      if (strictInterception && !["ALLOW", "BLOCK"].includes(result?.action)) throw new Error("Respuesta de auditoría inválida.");
      if (strictInterception && (!inputEl.isConnected || getPromptText(inputEl) !== text)) {
        showAuditError("El mensaje cambió durante la revisión. Pulsa Enviar nuevamente para auditar el texto actual.");
        return;
      }

      if (result.action === "BLOCK") {
        // BLOQUEO: Neutralizar texto inmediatamente y mostrar alerta
        clearInputElement(inputEl);
        showBlockModal(result, text);
      } else {
        // PERMITIDO (ALLOW): Reanudar envío normal
        resumeSubmission(inputEl, sendBtn);
      }
    } catch (err) {
      if (strictInterception) {
        console.warn("[DLP Guard] Envío retenido:", err);
        showAuditError("Envío detenido: no se pudo completar la auditoría. Comprueba que Aegis esté iniciado y recarga la pestaña si actualizaste la extensión. " + err.message);
        return;
      }
      console.warn("[DLP Guard] Backend no disponible (fail-open por continuidad operativa):", err);
      // Fail-open: permitir envío sin bloquear al usuario en caso de caída del backend
      resumeSubmission(inputEl, sendBtn);
    } finally {
      isAuditing = false;
    }
  }

  // Escuchar teclas en el DOM
  eventRoot.addEventListener("keydown", function (e) {
    if (bypassNextSubmit) return;
    if (e.key === "Enter" && !e.shiftKey && !(strictInterception && e.isComposing)) {
      const inputEl = findInputElement();
      if (inputEl && (inputEl === e.target || inputEl.contains(e.target))) {
        const text = getPromptText(inputEl);
        if (text) {
          e.preventDefault();
          e.stopPropagation();
          if (strictInterception) e.stopImmediatePropagation();
          auditAndProcess(text, inputEl, null);
        }
      }
    }
  }, true);

  // Escuchar clic en botones de envío
  eventRoot.addEventListener("click", function (e) {
    if (bypassNextSubmit) return;
    const btn = e.target.closest?.(strictInterception ? chatGPTSendSelector : SEND_BUTTON_SELECTOR);
    if (btn) {
      const inputEl = findInputElement();
      if (inputEl) {
        const text = getPromptText(inputEl);
        if (text || hasSelectedAttachment()) {
          e.preventDefault();
          e.stopPropagation();
          if (strictInterception) e.stopImmediatePropagation();
          auditAndProcess(text, inputEl, btn);
        }
      }
    }
  }, true);

  if (strictInterception) eventRoot.addEventListener("submit", function (e) {
    if (bypassNextSubmit) return;
    const inputEl = findInputElement();
    if (!inputEl || inputEl.closest("form") !== e.target) return;
    const text = getPromptText(inputEl);
    if (!text && !hasSelectedAttachment()) return;
    e.preventDefault();
    e.stopImmediatePropagation();
    auditAndProcess(text, inputEl, e.submitter);
  }, true);

  // Do not let a file/image reach an upload queue where a provider may begin
  // transfer before its textual submit button is clicked.
  eventRoot.addEventListener("paste", function (e) {
    if (!strictInterception || bypassNextSubmit) return;
    const items = [...(e.clipboardData?.items || [])];
    if (items.some(item => item.kind === "file" || item.type.startsWith("image/"))) {
      e.preventDefault();
      e.stopImmediatePropagation();
      blockAttachment("Pegado bloqueado: las imágenes y archivos no pueden enviarse a una IA externa.");
    }
  }, true);

  eventRoot.addEventListener("drop", function (e) {
    if (!strictInterception || bypassNextSubmit) return;
    if (e.dataTransfer?.files?.length) {
      e.preventDefault();
      e.stopImmediatePropagation();
      blockAttachment("Archivo arrastrado retenido: selecciona el archivo con el botón Adjuntar para inspeccionarlo localmente antes de cargarlo.");
    }
  }, true);

  eventRoot.addEventListener("change", function (e) {
    if (!strictInterception) return;
    const input = e.target;
    if (!input?.matches?.("input[type='file']") || !input.files?.length) return;
    if (approvedFileInputs.has(input)) {
      approvedFileInputs.delete(input);
      return;
    }
    e.stopImmediatePropagation();
    auditFilesAndRelease(input, [...input.files]);
  }, true);

})();
