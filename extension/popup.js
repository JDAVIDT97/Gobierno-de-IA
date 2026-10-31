/**
 * Popup Script (extension/popup.js)
 * Comprueba estado de salud del backend FastAPI en localhost:8000
 */

document.addEventListener("DOMContentLoaded", async () => {
  const statusBadge = document.getElementById("status-badge");
  const statusText = document.getElementById("status-text");
  const logsCount = document.getElementById("logs-count");
  const modelVer = document.getElementById("model-ver");
  const openDashBtn = document.getElementById("open-dash-btn");

  openDashBtn.addEventListener("click", () => {
    chrome.tabs.create({ url: "http://127.0.0.1:8000/" });
  });

  try {
    const res = await fetch("http://127.0.0.1:8000/health", { method: "GET" });
    if (res.ok) {
      const data = await res.json();
      statusBadge.className = "badge-status badge-online";
      statusText.textContent = "API CONECTADA";
      logsCount.textContent = data.total_logs_recorded;
      modelVer.textContent = `${data.model_version} (${data.model_backend})`;
      const [tab] = await chrome.tabs.query({ active: true, currentWindow: true });
      try {
        const recovery = await chrome.runtime.sendMessage({ type: "AEGIS_ENSURE_CONTENT", tabId: tab.id });
        if (!recovery?.ok) throw new Error(recovery?.error || "No se pudo comprobar la captura.");
        const state = recovery.state;
        if (!state?.active || state.version !== chrome.runtime.getManifest().version) throw new Error("Recarga la pestaña");
        if (!state.editorReady) {
          statusBadge.className = "badge-status badge-offline";
          statusText.textContent = "EDITOR NO DETECTADO";
          document.querySelector(".footer-sub").textContent = "El interceptor responde, pero no encuentra el campo del mensaje. No se ha confirmado la captura en esta vista.";
          return;
        }
        statusText.textContent = "CAPTURA ACTIVA";
        document.querySelector(".footer-sub").textContent = "Interceptor activo en esta pestaña. Cada envío se revisa antes de autorizarse.";
      } catch (error) {
        statusBadge.className = "badge-status badge-offline";
        statusText.textContent = "RECARGA LA PESTAÑA";
        document.querySelector(".footer-sub").textContent = error.message;
      }
    } else {
      throw new Error();
    }
  } catch (err) {
    statusBadge.className = "badge-status badge-offline";
    statusText.textContent = "OFFLINE";
    logsCount.textContent = "N/A";
  }
});
