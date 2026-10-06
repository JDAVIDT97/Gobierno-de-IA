"use strict";

// Keep the extension aligned with start.ps1, which launches FastAPI on 8000.
const API = "http://127.0.0.1:8000";
const TIMEOUT_MS = 5000;

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
