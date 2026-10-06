/**
 * Aegis DLP | CISO Command Center Controller (web_dashboard/app.js)
 * Dinamismo interactivo, cards en movimiento, telemetría y simulación en tiempo real.
 */

document.addEventListener("DOMContentLoaded", () => {
  const simulatorUserId = localStorage.getItem("aegisSimulatorUserId") || crypto.randomUUID();
  localStorage.setItem("aegisSimulatorUserId", simulatorUserId);
  // Referencias DOM
  const kpiTotal = document.getElementById("kpi-total");
  const kpiBlocked = document.getElementById("kpi-blocked");
  const kpiBlockRate = document.getElementById("kpi-block-rate");
  const kpiRisk = document.getElementById("kpi-risk");
  const kpiRiskMeter = document.getElementById("kpi-risk-meter");
  const kpiLatency = document.getElementById("kpi-latency");
  const auditTableBody = document.getElementById("audit-table-body");
  const highRiskUsersTable = document.getElementById("table-high-risk-users");

  function formatPeruDateTime(timestamp) {
    const date = new Date(timestamp);
    if (Number.isNaN(date.getTime())) return timestamp;
    return new Intl.DateTimeFormat("es-PE", {
      timeZone: "America/Lima",
      dateStyle: "short",
      timeStyle: "medium",
      hour12: false
    }).format(date);
  }

  // Simulador DOM
  const promptInput = document.getElementById("sim-prompt-input");
  const charCount = document.getElementById("sim-char-count");
  const btnRunAudit = document.getElementById("btn-run-audit");
  const resultCard = document.getElementById("sim-result-container");
  const resultBadge = document.getElementById("result-badge");
  const resTime = document.getElementById("res-time");
  const resScore = document.getElementById("res-score");
  const resCategory = document.getElementById("res-category");
  const resReasonBox = document.getElementById("res-reason-box");
  const resReasonText = document.getElementById("res-reason-text");
  const resRedactedText = document.getElementById("res-redacted-text");

  // Controles de Bitácora
  const logSearch = document.getElementById("log-search-input");
  const logAction = document.getElementById("log-filter-action");
  const logCategory = document.getElementById("log-filter-category");
  const btnRefreshLogs = document.getElementById("btn-refresh-logs");

  // Modal de inspección
  const inspectModal = document.getElementById("inspect-modal");
  const inspectBody = document.getElementById("inspect-modal-body");
  const btnCloseInspect = document.getElementById("btn-close-inspect");

  // Botones de prueba rápida y dock
  const btnQuickTestExcel = document.getElementById("btn-quick-test-excel");
  const dockBtnTestExcel = document.getElementById("dock-btn-test-excel");
  const dockBtnTop = document.getElementById("dock-btn-top");
  const navTabs = document.querySelectorAll(".nav-tab");
  const dockBtns = document.querySelectorAll(".dock-btn[data-target]");
  const submenuToggle = document.querySelector(".nav-submenu-toggle");
  const submenuItems = document.querySelector(".nav-submenu-items");

  // Instancias de Gráficos Chart.js
  let chartDistribution = null;
  let chartTrend = null;

  // -------------------------------------------------------------
  // 1. EFECTO DINÁMICO 3D TILT EN CARDS (CARDS EN MOVIMIENTO)
  // -------------------------------------------------------------
  const motionCards = document.querySelectorAll(".motion-card");
  motionCards.forEach(card => {
    if (card.classList.contains("panel-audit-log")) return;
    card.addEventListener("mousemove", (e) => {
      const rect = card.getBoundingClientRect();
      const x = e.clientX - rect.left;
      const y = e.clientY - rect.top;
      const centerX = rect.width / 2;
      const centerY = rect.height / 2;
      const rotateX = ((y - centerY) / centerY) * -4;
      const rotateY = ((x - centerX) / centerX) * 4;

      card.style.transform = `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) translateY(-4px)`;
    });

    card.addEventListener("mouseleave", () => {
      card.style.transform = "perspective(1000px) rotateX(0deg) rotateY(0deg) translateY(0)";
    });
  });

  // -------------------------------------------------------------
  // 2. PRESETS RÁPIDOS PARA EL SIMULADOR
  // -------------------------------------------------------------
  const PRESETS = {
    excel: `ChatGPT, ayúdame a ordenar este excel de datos de mi empresa (Inversiones Andinas SAC). Quiero que lo ordenes por mayor margen de ventas:\nID_Empleado\tNombre\tSueldo_Base\tVentas_Q3_USD\tMargen_Bruto\nEMP-101\tCarlos Mendoza\tS/14,500\t$240,000\t32%\nEMP-102\tElena Vasquez\tS/18,200\t$410,000\t38%\nEMP-103\tRodrigo Flores\tS/12,000\t$185,000\t29%`,
    pii: `ChatGPT, procesa este reembolso de cliente: Titular Juan Carlos García Mendoza, DNI: 47891245, Tarjeta Visa: 4532 8901 2345 6789, Vencimiento: 08/28, CVV: 789, Monto: $1,450.00 USD. Correo personal: jc.garcia99@gmail.com`,
    code: `Corrige este script de respaldo interno con nuestras credenciales de producción de AWS:\nimport boto3\nAWS_ACCESS_KEY_ID = "AKIAIOSFODNN7EXAMPLE"\nAWS_SECRET_ACCESS_KEY = "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY"\nDATABASE_URL = "postgresql://admin_prod:SuperSecret_Pass@core-db.internal:5432/corp_finances"`,
    safe: `Por favor explícame de forma didáctica la diferencia entre concurrencia y paralelismo en sistemas distribuidos, con 2 ejemplos prácticos en lenguaje Python.`
  };

  document.querySelectorAll(".btn-preset").forEach(btn => {
    btn.addEventListener("click", () => {
      const type = btn.dataset.preset;
      if (PRESETS[type]) {
        promptInput.value = PRESETS[type];
        updateCharCount();
        runPromptAudit();
      }
    });
  });

  promptInput.addEventListener("input", updateCharCount);

  function updateCharCount() {
    charCount.textContent = `${promptInput.value.length} / 4096 caracteres`;
  }

  // -------------------------------------------------------------
  // 3. EJECUTAR AUDITORÍA DESDE EL SIMULADOR
  // -------------------------------------------------------------
  btnRunAudit.addEventListener("click", runPromptAudit);

  async function runPromptAudit() {
    const text = promptInput.value.trim();
    if (!text) return;

    btnRunAudit.disabled = true;
    const originalContent = btnRunAudit.innerHTML;
    btnRunAudit.innerHTML = "<span class=\"btn-icon\">⏳</span><span class=\"btn-text\">Analizando con SLM...</span>";

    try {
      const res = await fetch("/v1/audit", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          user_id: simulatorUserId,
          prompt: text,
          destination: "https://chatgpt.com"
        })
      });

      const data = await res.json();
      displaySimResult(data);
      // Refrescar KPIs y bitácora tras el nuevo evento
      loadKpis();
      loadAuditLogs();
    } catch (err) {
      alert("Error al conectar con la API de Inferencia: " + err.message);
    } finally {
      btnRunAudit.disabled = false;
      btnRunAudit.innerHTML = originalContent;
    }
  }

  function displaySimResult(data) {
    resultCard.style.display = "flex";
    const isBlock = data.action === "BLOCK";

    resultBadge.className = "result-verdict " + (isBlock ? "verdict-block" : "verdict-allow");
    resultBadge.textContent = isBlock ? "⛔ BLOQUEADO (SHADOW AI NEUTRALIZADO)" : "✅ PERMITIDO (USO SEGURO)";

    resTime.textContent = `${data.inference_time_ms} ms`;
    resScore.textContent = `${(data.risk_score * 100).toFixed(1)}%`;
    resCategory.textContent = data.category;

    if (isBlock && data.reason) {
      resReasonBox.style.display = "block";
      resReasonText.textContent = data.reason;
    } else {
      resReasonBox.style.display = "none";
    }

    resRedactedText.textContent = data.redacted_preview;
  }

  // Atajos de prueba rápida para Excel (Navbar y Dock)
  function triggerQuickExcelTest() {
    promptInput.value = PRESETS.excel;
    updateCharCount();
    activateView("simulator");
    setTimeout(() => {
      runPromptAudit();
    }, 400);
  }

  if (btnQuickTestExcel) btnQuickTestExcel.addEventListener("click", triggerQuickExcelTest);
  if (dockBtnTestExcel) dockBtnTestExcel.addEventListener("click", triggerQuickExcelTest);

  // Volver arriba desde el dock
  if (dockBtnTop) {
    dockBtnTop.addEventListener("click", () => {
      window.scrollTo({ top: 0, behavior: "smooth" });
    });
  }

  // -------------------------------------------------------------
  // 4. NAVEGACIÓN SUAVE Y SCROLLSPY
  // -------------------------------------------------------------
  function activateView(view) {
    document.body.dataset.activeView = view;
    navTabs.forEach(tab => tab.classList.toggle("active", tab.dataset.view === view));
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function setupNavigation() {
    navTabs.forEach(tab => {
      tab.addEventListener("click", (e) => {
        e.preventDefault();
        activateView(tab.dataset.view);
      });
    });

    dockBtns.forEach(btn => {
      btn.addEventListener("click", () => {
        const target = btn.dataset.target;
        const view = target === "sec-kpis" ? "overview" : target.replace("sec-", "");
        activateView(view);
      });
    });

    submenuToggle?.addEventListener("click", () => {
      const isOpen = submenuToggle.getAttribute("aria-expanded") === "true";
      submenuToggle.setAttribute("aria-expanded", String(!isOpen));
      submenuItems.hidden = isOpen;
    });
  }

  setupNavigation();

  // -------------------------------------------------------------
  // 5. CARGA DE SALUD DEL SISTEMA, KPIS Y GRÁFICOS
  // -------------------------------------------------------------
  async function loadHealth() {
    try {
      const res = await fetch("/health");
      if (!res.ok) return;
      const data = await res.json();
      const navStatus = document.getElementById("nav-system-status");
      if (navStatus) {
        const backendName = (data.model_backend || "SLM").replace("-", " ").toUpperCase();
        navStatus.textContent = `${backendName} (${data.model_version || "v2.0"})`;
      }
    } catch (e) {
      console.warn("Error consultando salud del sistema:", e);
    }
  }

  async function loadKpis() {
    try {
      loadHealth();
      const res = await fetch("/v1/kpis");
      if (!res.ok) return;
      const data = await res.json();

      animateValue(kpiTotal, parseInt(kpiTotal.textContent) || 0, data.total_audited, 600);
      animateValue(kpiBlocked, parseInt(kpiBlocked.textContent) || 0, data.total_blocked, 600);
      kpiBlockRate.textContent = `${data.block_rate_pct}% tasa bloqueo`;
      kpiRisk.textContent = data.avg_risk_score.toFixed(2);
      kpiRiskMeter.style.width = `${Math.min(100, data.avg_risk_score * 100)}%`;

      renderDistributionChart(data.top_categories);
      renderTrendChart(data.recent_trend);
      renderHighRiskUsers(data.high_risk_users);
    } catch (e) {
      console.warn("Error cargando KPIs:", e);
    }
  }

  function animateValue(obj, start, end, duration) {
    if (start === end) {
      obj.textContent = end;
      return;
    }
    let startTimestamp = null;
    const step = (timestamp) => {
      if (!startTimestamp) startTimestamp = timestamp;
      const progress = Math.min((timestamp - startTimestamp) / duration, 1);
      obj.textContent = Math.floor(progress * (end - start) + start);
      if (progress < 1) {
        window.requestAnimationFrame(step);
      }
    };
    window.requestAnimationFrame(step);
  }

  function renderDistributionChart(categories) {
    const ctx = document.getElementById("chart-risk-distribution");
    if (!ctx) return;

    const labels = Object.keys(categories).length ? Object.keys(categories) : ["Safe_Use", "Business_Secrets", "PII_Leak", "Proprietary_Code"];
    const values = Object.keys(categories).length ? Object.values(categories) : [0, 0, 0, 0];

    const colorsMap = {
      Safe_Use: "#10b981",
      Business_Secrets: "#ff2a5f",
      PII_Leak: "#f59e0b",
      Proprietary_Code: "#9d4edd"
    };
    const bgColors = labels.map(l => colorsMap[l] || "#00f0ff");

    if (chartDistribution) {
      chartDistribution.data.labels = labels;
      chartDistribution.data.datasets[0].data = values;
      chartDistribution.data.datasets[0].backgroundColor = bgColors;
      chartDistribution.update();
    } else {
      chartDistribution = new Chart(ctx, {
        type: "doughnut",
        data: {
          labels: labels,
          datasets: [{
            data: values,
            backgroundColor: bgColors,
            borderColor: "#0e1626",
            borderWidth: 2,
            hoverOffset: 6
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: {
            legend: {
              position: "bottom",
              labels: {
                color: "#d7e3f0",
                padding: 16,
                boxWidth: 14,
                boxHeight: 10,
                font: { family: "Outfit", size: 12, weight: "600" }
              }
            }
          },
          cutout: "62%",
          radius: "92%"
        }
      });
    }
  }

  function renderTrendChart(trend) {
    const ctx = document.getElementById("chart-trend");
    if (!ctx) return;

    const labels = trend.map((t, idx) => `#${t.id}`).reverse();
    const riskScores = trend.map(t => t.risk_score).reverse();

    if (chartTrend) {
      chartTrend.data.labels = labels;
      chartTrend.data.datasets[0].data = riskScores;
      chartTrend.update();
    } else {
      chartTrend = new Chart(ctx, {
        type: "line",
        data: {
          labels: labels,
          datasets: [{
            label: "Nivel de Riesgo Evaluado",
            data: riskScores,
            borderColor: "#00f0ff",
            backgroundColor: "rgba(0, 240, 255, 0.1)",
            fill: true,
            tension: 0.35,
            pointRadius: 4,
            pointBackgroundColor: "#ff2a5f"
          }]
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          scales: {
            x: { grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#64748b" } },
            y: { min: 0, max: 1.0, grid: { color: "rgba(255,255,255,0.05)" }, ticks: { color: "#64748b" } }
          },
          plugins: {
            legend: { display: false }
          }
        }
      });
    }
  }

  function renderHighRiskUsers(users) {
    const tbody = highRiskUsersTable.querySelector("tbody");
    if (!users || !users.length) {
      tbody.innerHTML = "<tr><td colspan='4' class='text-center text-muted'>Sin infractores registrados aún</td></tr>";
      return;
    }
    tbody.innerHTML = users.map(u => `
      <tr>
        <td style="font-family: monospace; color: #38bdf8;">${u.user_id}</td>
        <td style="color: #ff2a5f; font-weight: 700;">${u.blocked_count}</td>
        <td>${(u.avg_risk * 100).toFixed(0)}%</td>
        <td><span class="pill pill-danger">Auditado</span></td>
      </tr>
    `).join("");
  }

  // -------------------------------------------------------------
  // 6. CARGA Y FILTRADO DE LA BITÁCORA DE AUDITORÍA
  // -------------------------------------------------------------
  async function loadAuditLogs() {
    const action = logAction.value;
    const category = logCategory.value;
    const search = logSearch.value.trim();

    let url = `/v1/logs?limit=30`;
    if (action) url += `&action=${action}`;
    if (category) url += `&category=${category}`;
    if (search) url += `&search=${encodeURIComponent(search)}`;

    try {
      const res = await fetch(url);
      if (!res.ok) return;
      const data = await res.json();

      if (!data.items.length) {
        auditTableBody.innerHTML = "<tr><td colspan='9' class='text-center text-muted'>No se encontraron eventos coincidentes.</td></tr>";
        return;
      }

      auditTableBody.innerHTML = data.items.map(item => {
        const isBlock = item.action === "BLOCK";
        const badgeClass = isBlock ? "pill-danger" : "pill-safe";
        const cleanTime = formatPeruDateTime(item.timestamp);

        return `
          <tr>
            <td style="font-family: monospace; color:#64748b;">#${item.id}</td>
            <td style="font-family: monospace;">${cleanTime}</td>
            <td style="font-family: monospace; color:#38bdf8;">${item.user_id.substring(0, 14)}</td>
            <td style="color:#94a3b8;">${item.destination ? item.destination.replace("https://", "") : "chatgpt.com"}</td>
            <td><span class="pill ${badgeClass}">${item.action}</span></td>
            <td style="font-weight: 500;">${item.category}</td>
            <td style="font-family: monospace; color:${isBlock ? '#ff2a5f' : '#10b981'}; font-weight: 700;">${(item.risk_score * 100).toFixed(0)}%</td>
            <td style="font-family: monospace; color:#00f0ff;">${item.inference_time_ms} ms</td>
            <td>
              <button class="btn-table-action" data-id="${item.id}">Ver Registro</button>
            </td>
          </tr>
        `;
      }).join("");

      // Vincular botones de ver detalle
      document.querySelectorAll(".btn-table-action").forEach(btn => {
        btn.addEventListener("click", () => {
          const logId = parseInt(btn.dataset.id);
          const found = data.items.find(i => i.id === logId);
          if (found) showInspectModal(found);
        });
      });
    } catch (e) {
      console.warn("Error cargando logs:", e);
    }
  }

  function showInspectModal(item) {
    inspectBody.innerHTML = `
      <div style="display:grid; grid-template-columns: 1fr 1fr; gap: 12px; font-size: 13px;">
        <div><strong style="color:#64748b;">ID Transacción:</strong> #${item.id}</div>
        <div><strong style="color:#64748b;">Hora de Perú:</strong> ${formatPeruDateTime(item.timestamp)}</div>
        <div><strong style="color:#64748b;">Usuario Auditado:</strong> ${item.user_id}</div>
        <div><strong style="color:#64748b;">Servicio Destino:</strong> ${item.destination}</div>
        <div><strong style="color:#64748b;">Decisión DLP:</strong> <span class="pill ${item.action === 'BLOCK' ? 'pill-danger' : 'pill-safe'}">${item.action}</span></div>
        <div><strong style="color:#64748b;">Categoría:</strong> ${item.category}</div>
        <div><strong style="color:#64748b;">Riesgo Evaluado:</strong> ${(item.risk_score * 100).toFixed(1)}%</div>
        <div><strong style="color:#64748b;">Latencia Inferencia:</strong> ${item.inference_time_ms} ms</div>
        <div style="grid-column: span 2;">
          <strong style="color:#64748b;">Hash Criptográfico SHA-256 (Inmutable):</strong>
          <pre style="background:rgba(0,0,0,0.5); padding:6px; border-radius:6px; font-size:11px; color:#38bdf8; overflow-x:auto;">${item.prompt_hash}</pre>
        </div>
        <div style="grid-column: span 2;">
          <strong style="color:#64748b;">Texto Anonimizado Registrado:</strong>
          <pre style="background:rgba(0,0,0,0.5); padding:10px; border-radius:6px; font-size:12px; color:#f1f5f9; white-space:pre-wrap; max-height:180px; overflow-y:auto;">${item.prompt_redacted}</pre>
        </div>
      </div>
    `;
    inspectModal.style.display = "flex";
  }

  btnCloseInspect.addEventListener("click", () => inspectModal.style.display = "none");
  inspectModal.addEventListener("click", (e) => {
    if (e.target === inspectModal) inspectModal.style.display = "none";
  });

  // Filtros interactivos
  logSearch.addEventListener("input", debounce(loadAuditLogs, 300));
  logAction.addEventListener("change", loadAuditLogs);
  logCategory.addEventListener("change", loadAuditLogs);
  
  btnRefreshLogs.addEventListener("click", () => {
    const icon = btnRefreshLogs.querySelector(".refresh-icon");
    if (icon) icon.style.transform = "rotate(360deg)";
    loadKpis();
    loadAuditLogs();
    setTimeout(() => {
      if (icon) icon.style.transform = "none";
    }, 500);
  });

  function debounce(func, wait) {
    let timeout;
    return (...args) => {
      clearTimeout(timeout);
      timeout = setTimeout(() => func.apply(this, args), wait);
    };
  }

  // Inicialización y Polling Suave cada 8 segundos
  loadKpis();
  loadAuditLogs();
  setInterval(() => {
    loadKpis();
    loadAuditLogs();
  }, 8000);
});
