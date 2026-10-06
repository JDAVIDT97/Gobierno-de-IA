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
    chrome.tabs.create({ url: "http://127.0.0.1:8501/" });
  });

  try {
    const res = await fetch("http://127.0.0.1:8000/health", { method: "GET" });
    if (res.ok) {
      const data = await res.json();
      statusBadge.className = "badge-status badge-online";
      statusText.textContent = "PROTEGIDO";
      logsCount.textContent = data.total_logs_recorded;
      modelVer.textContent = `${data.model_version} (${data.model_backend})`;
    } else {
      throw new Error();
    }
  } catch (err) {
    statusBadge.className = "badge-status badge-offline";
    statusText.textContent = "OFFLINE";
    logsCount.textContent = "N/A";
  }
});
