"use strict";

// Keep the extension aligned with start.ps1, which launches FastAPI on 8000.
const API = "http://127.0.0.1:8000";
const TIMEOUT_MS = 5000;
const CATEGORIES = new Set(["Safe_Use", "PII_Leak", "Proprietary_Code", "Business_Secrets", "Code_Exploitation", "Data_Exfiltration", "Social_Engineering", "Role_Evasion_Jailbreak", "Legal_Misalignment"]);

function validAuditDecision(data) {
  return data && ["ALLOW", "BLOCK"].includes(data.action) && CATEGORIES.has(data.category) &&
    (data.action === "ALLOW") === (data.category === "Safe_Use") &&
    Number.isFinite(data.risk_score) && data.risk_score >= 0 && data.risk_score <= 1 &&
    Number.isFinite(data.inference_time_ms) && data.inference_time_ms >= 0 &&
    typeof data.model_version === "string" && data.model_version.length > 0 &&
    Array.isArray(data.matched_rules) && data.matched_rules.every(rule => typeof rule === "string");
}

async function setBadge(tabId, online) {
  if (!tabId) return;
  await chrome.action.setBadgeText({ tabId, text: online ? "ON" : "!" });
  await chrome.action.setBadgeBackgroundColor({ tabId, color: online ? "#16a34a" : "#dc2626" });
}

async function recordUnaudited(payload, reason) {
  const { unauditedEvents = [] } = await chrome.storage.local.get("unauditedEvents");
  unauditedEvents.push({ timestamp: new Date().toISOString(), destination: payload.destination,
    prompt_hash_unavailable: true, status: "UNAUDITED", reason: String(reason).slice(0, 160) });
  await chrome.storage.local.set({ unauditedEvents: unauditedEvents.slice(-100) });
}

async function ensureContent(tabId) {
  const version = chrome.runtime.getManifest().version;
  let state;
  try { state = await chrome.tabs.sendMessage(tabId, { type: "AEGIS_CONTENT_STATUS" }); }
  catch { /* No receiver: install the interceptor into the existing document. */ }
  if (state?.active && state.version === version) return state;
  if (state?.active) throw new Error(`La pestaña mantiene la versión ${state.version}; recárgala para cargar ${version}.`);
  const [{ result: alreadyLoaded }] = await chrome.scripting.executeScript({
    target: { tabId }, func: () => Boolean(globalThis.__aegisDlpGuard)
  });
  if (alreadyLoaded) throw new Error("El script anterior no terminó de iniciar. Recarga esta pestaña para reiniciarlo.");
  await chrome.scripting.insertCSS({ target: { tabId }, files: ["styles.css"] });
  await chrome.scripting.executeScript({ target: { tabId }, files: ["content.js"] });
  state = await chrome.tabs.sendMessage(tabId, { type: "AEGIS_CONTENT_STATUS" });
  if (!state?.active || state.version !== version) throw new Error("No se pudo iniciar el interceptor en esta página.");
  return state;
}

chrome.runtime.onMessage.addListener((message, _sender, sendResponse) => {
  if (message?.type !== "AEGIS_ENSURE_CONTENT" || !Number.isInteger(message.tabId)) return false;
  ensureContent(message.tabId).then(
    state => sendResponse({ ok: true, state }),
    error => sendResponse({ ok: false, error: error.message })
  );
  return true;
});

chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message?.type !== "AEGIS_AUDIT") return false;
  (async () => {
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), TIMEOUT_MS);
    try {
      const response = await fetch(`${API}/v1/audit`, { method: "POST",
        headers: { "Content-Type": "application/json" }, body: JSON.stringify(message.payload),
        signal: controller.signal });
      const data = await response.json().catch(() => null);
      if (!response.ok) {
        const detail = Array.isArray(data?.detail)
          ? data.detail.map(item => `${item.loc?.join(".") || "request"}: ${item.msg}`).join("; ")
          : data?.detail;
        throw new Error(detail ? `HTTP ${response.status}: ${detail}` : `HTTP ${response.status}`);
      }
      if (!validAuditDecision(data)) throw new Error("Invalid audit response: send retained");
      await setBadge(sender.tab?.id, true);
      sendResponse({ ok: true, data });
    } catch (error) {
      await recordUnaudited(message.payload, error);
      await setBadge(sender.tab?.id, false);
      // The content script retains protected traffic on every audit failure.
      sendResponse({ ok: false, failOpen: false, error: String(error) });
    } finally {
      clearTimeout(timeout);
    }
  })();
  return true;
});

chrome.runtime.onInstalled.addListener(() => {
  chrome.action.setBadgeBackgroundColor({ color: "#64748b" });
});
