"""
Microservicio Principal FastAPI (api/main.py)
Servicio de inspección local y persistencia en SQLite,
analítica y exportación de registros de auditoría.
"""

import csv
import hashlib
import io
import os
import threading
import time
from collections import defaultdict, deque
from contextlib import asynccontextmanager
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Optional, List

from fastapi import FastAPI, Depends, HTTPException, Query, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, StreamingResponse
from sqlalchemy.orm import Session
from sqlalchemy import func, desc

from .database import init_db, get_db, AuditLog
from .schemas import AuditRequest, AuditResponse, HealthResponse, KpisResponse, LogItem
from .engine import DlpEngine
from .config import settings

BASE_DIR = Path(__file__).resolve().parent.parent
WEB_DASHBOARD_DIR = BASE_DIR / "web_dashboard"


class PerUserRateLimiter:
    """Bounded, thread-safe sliding window. Replace with Redis when horizontally scaled."""
    def __init__(self, requests_per_minute: int):
        self.limit = requests_per_minute
        self.events = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, key: str) -> None:
        now = time.monotonic()
        with self.lock:
            bucket = self.events[key]
            while bucket and bucket[0] <= now - 60:
                bucket.popleft()
            if len(bucket) >= self.limit:
                raise HTTPException(status_code=429, detail="Rate limit exceeded", headers={"Retry-After": "60"})
            bucket.append(now)


rate_limiter = PerUserRateLimiter(settings.rate_limit_per_minute)

# Lifespan para inicialización limpia
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Inicializar Base de Datos
    init_db()
    # Cargar modelo en memoria
    engine = DlpEngine.get_instance()
    print("[*] FastAPI iniciado: DB lista y motor DLP precalentado.")
    yield
    print("[*] Cerrando servicios FastAPI.")

app = FastAPI(
    title="DLP Shadow AI Governance API",
    description="Prototipo de inspección local de solicitudes para GenAI y registro de decisiones.",
    version="1.0.0",
    lifespan=lifespan
)

# CORS permisivo para Chrome Extension y Web App local
app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.allowed_origins) + ["https://chatgpt.com", "https://claude.ai", "https://gemini.google.com"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

# -------------------------------------------------------------
# ENDPOINTS PRINCIPALES
# -------------------------------------------------------------

@app.post("/v1/audit", response_model=AuditResponse, summary="Auditar e inferir riesgo de un prompt")
def audit_prompt(payload: AuditRequest, db: Session = Depends(get_db)):
    """
    Endpoint principal de auditoría.
    Evalúa el texto, clasifica en una de las 4 clases de riesgo,
    anonimiza entidades sensibles y persiste el evento en SQLite para auditoría.
    """
    rate_limiter.check(str(payload.user_id))

    engine = DlpEngine.get_instance()
    try:
        eval_result = engine.evaluate(payload.prompt)
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail="AUDIT_UNAVAILABLE: envío retenido") from exc

    # Anonimización para almacenamiento forense seguro
    prompt_hash = hashlib.sha256(payload.prompt.encode("utf-8")).hexdigest()
    prompt_redacted = engine.redact_prompt(payload.prompt)
    preview = prompt_redacted[:300] + ("..." if len(prompt_redacted) > 300 else "")
    stored_summary = engine.storage_safe_summary(eval_result["category"], eval_result["action"])

    # Persistencia en Base de Datos de Auditoría
    try:
        log_entry = AuditLog(
            timestamp=datetime.now(timezone.utc).isoformat(),
            user_id=str(payload.user_id),
            prompt_hash=prompt_hash,
            prompt_redacted=stored_summary,
            destination=str(payload.destination),
            action=eval_result["action"],
            category=eval_result["category"],
            risk_score=eval_result["risk_score"],
            confidence=eval_result["confidence"],
            model_version=engine.version,
            inference_time_ms=eval_result["inference_time_ms"]
        )
        db.add(log_entry)
        db.commit()
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=503, detail="AUDIT_LOG_UNAVAILABLE: envío retenido") from e

    return AuditResponse(
        action=eval_result["action"],
        risk_score=eval_result["risk_score"],
        category=eval_result["category"],
        reason=eval_result.get("reason"),
        model_version=engine.version,
        inference_time_ms=eval_result["inference_time_ms"],
        redacted_preview=preview if settings.store_redacted_preview else stored_summary,
        matched_rules=eval_result.get("matched_rules", [])
    )

@app.get("/health", response_model=HealthResponse, summary="Chequeo de salud del servicio")
def health_check(db: Session = Depends(get_db)):
    engine = DlpEngine.get_instance()
    try:
        total_logs = db.query(func.count(AuditLog.id)).scalar() or 0
        db_ok = True
    except Exception:
        total_logs = 0
        db_ok = False

    return HealthResponse(
        status="healthy" if db_ok else "degraded",
        model_loaded=(engine.model is not None),
        model_backend=engine.backend,
        model_version=engine.version,
        database_connected=db_ok,
        total_logs_recorded=total_logs,
        system_latency_p95_target="<50ms"
    )

@app.get("/v1/logs", summary="Listar logs de auditoría con filtros")
def get_logs(
    db: Session = Depends(get_db),
    limit: int = Query(50, ge=0, le=200, description="Cantidad de registros; 0 devuelve todos los resultados filtrados."),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    category: Optional[str] = None,
    search: Optional[str] = None,
    user_id: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
):
    query = db.query(AuditLog)
    if action:
        query = query.filter(AuditLog.action == action.upper())
    if category:
        query = query.filter(AuditLog.category == category)
    if search:
        query = query.filter(
            (AuditLog.prompt_redacted.ilike(f"%{search}%")) |
            (AuditLog.user_id.ilike(f"%{search}%"))
        )
    if user_id:
        query = query.filter(AuditLog.user_id == user_id)
    if date_from:
        query = query.filter(AuditLog.timestamp >= date_from)
    if date_to:
        query = query.filter(AuditLog.timestamp <= date_to)
    
    total = query.count()
    records_query = query.order_by(desc(AuditLog.id)).offset(offset)
    if limit:
        records_query = records_query.limit(limit)
    records = records_query.all()

    return {
        "total": total,
        "offset": offset,
        "limit": limit,
        "items": [
            {
                "id": r.id,
                "timestamp": r.timestamp,
                "user_id": r.user_id,
                "prompt_hash": r.prompt_hash,
                "prompt_redacted": r.prompt_redacted,
                "destination": r.destination,
                "action": r.action,
                "category": r.category,
                "risk_score": r.risk_score,
                "confidence": r.confidence,
                "model_version": r.model_version,
                "inference_time_ms": r.inference_time_ms
            }
            for r in records
        ]
    }

@app.get("/v1/kpis", summary="Métricas analíticas para el CISO Dashboard")
def get_kpis(db: Session = Depends(get_db)):
    total = db.query(func.count(AuditLog.id)).scalar() or 0
    blocked = db.query(func.count(AuditLog.id)).filter(AuditLog.action == "BLOCK").scalar() or 0
    allowed = total - blocked
    cutoff_24h = (datetime.now(timezone.utc) - timedelta(hours=24)).isoformat()
    total_last_24h = db.query(func.count(AuditLog.id)).filter(AuditLog.timestamp >= cutoff_24h).scalar() or 0
    block_rate = round((blocked / total * 100.0), 1) if total > 0 else 0.0

    avg_risk = db.query(func.avg(AuditLog.risk_score)).scalar()
    avg_risk_val = round(float(avg_risk), 2) if avg_risk is not None else 0.0

    # Categorías
    cat_counts = {}
    rows = db.query(AuditLog.category, func.count(AuditLog.id)).group_by(AuditLog.category).all()
    for cat, cnt in rows:
        cat_counts[cat] = cnt

    # Top infractores
    high_risk_users = []
    user_rows = (
        db.query(AuditLog.user_id, func.count(AuditLog.id).label("violations"), func.avg(AuditLog.risk_score).label("avg_r"))
        .filter(AuditLog.action == "BLOCK")
        .group_by(AuditLog.user_id)
        .order_by(desc("violations"))
        .limit(5)
        .all()
    )
    for u, v_cnt, a_r in user_rows:
        high_risk_users.append({
            "user_id": u,
            "blocked_count": v_cnt,
            "avg_risk": round(float(a_r), 2)
        })

    # Actividad reciente (últimos 10 eventos)
    recent = db.query(AuditLog).order_by(desc(AuditLog.id)).limit(10).all()
    recent_trend = [
        {
            "id": r.id,
            "timestamp": r.timestamp,
            "category": r.category,
            "action": r.action,
            "risk_score": r.risk_score,
            "user_id": r.user_id
        }
        for r in recent
    ]

    return {
        "total_audited": total,
        "total_last_24h": total_last_24h,
        "total_blocked": blocked,
        "total_allowed": allowed,
        "block_rate_pct": block_rate,
        "avg_risk_score": avg_risk_val,
        "avg_inference_time_ms": db.query(func.avg(AuditLog.inference_time_ms)).scalar(),
        "top_categories": cat_counts,
        "high_risk_users": high_risk_users,
        "recent_trend": recent_trend
    }

@app.get("/v1/export-csv", summary="Exportar logs a CSV")
def export_csv(db: Session = Depends(get_db)):
    records = db.query(AuditLog).order_by(desc(AuditLog.id)).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "ID", "Timestamp", "User_ID", "Destination", "Action", 
        "Category", "Risk_Score", "Confidence", "Inference_Time_MS", "Prompt_Redacted"
    ])
    for r in records:
        writer.writerow([
            r.id, r.timestamp, r.user_id, r.destination, r.action,
            r.category, r.risk_score, r.confidence, r.inference_time_ms, r.prompt_redacted
        ])
    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit_logs_dlp.csv"}
    )

@app.get("/v1/export-pdf", summary="Generar reporte de registros de auditoría PDF")
def export_pdf(db: Session = Depends(get_db)):
    """Genera un informe formal de auditoría para el CISO usando ReportLab."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.lib import colors
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.graphics.shapes import Drawing
        from reportlab.graphics.charts.piecharts import Pie
    except ImportError:
        raise HTTPException(status_code=500, detail="ReportLab no está instalado.")

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=36, leftMargin=36, topMargin=36, bottomMargin=36)
    elements = []
    styles = getSampleStyleSheet()

    # Estilos
    title_style = ParagraphStyle(
        'TitleStyle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        textColor=colors.HexColor('#0e1726'),
        spaceAfter=12
    )
    subtitle_style = ParagraphStyle(
        'SubtitleStyle',
        parent=styles['Normal'],
        fontSize=11,
        textColor=colors.HexColor('#4a5568'),
        spaceAfter=20
    )
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=13,
        textColor=colors.HexColor('#1a365d'),
        spaceBefore=14,
        spaceAfter=8
    )
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=9,
        textColor=colors.HexColor('#2d3748'),
        leading=13
    )

    # Portada / Encabezado
    elements.append(Paragraph("INFORME DE GOBERNANZA DE IA Y PREVENCIÓN DE FUGA (DLP)", title_style))
    elements.append(Paragraph(
        f"<b>Fecha de Generación:</b> {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')} | "
        f"<b>Alcance:</b> registros locales | <b>Versión:</b> {DlpEngine.get_instance().version}",
        subtitle_style
    ))
    elements.append(Spacer(1, 10))

    # Resumen Ejecutivo
    total = db.query(func.count(AuditLog.id)).scalar() or 0
    blocked = db.query(func.count(AuditLog.id)).filter(AuditLog.action == "BLOCK").scalar() or 0
    allowed = total - blocked
    rate = round((blocked / total * 100), 1) if total > 0 else 0.0

    kpi_data = [
        ["Métrica de Gobernanza", "Valor Registrado", "Alcance"],
        ["Total Prompts Auditados", str(total), "Eventos registrados"],
        ["Solicitudes con decisión de bloqueo", str(blocked), f"{rate}% de los eventos registrados"],
        ["Prompts Autorizados (Safe_Use)", str(allowed), "Decisión del motor"],
        ["Latencia p95", "No medida en este informe", "Consultar benchmark identificado"],
        ["Inspección", "Procesamiento local", "No acredita ausencia de fugas"]
    ]
    t = Table(kpi_data, colWidths=[200, 160, 180])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#0e1726')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 9),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#cbd5e0')),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#f7fafc'), colors.white])
    ]))
    elements.append(Paragraph("1. Resumen Ejecutivo de Trazabilidad y KPIs", section_style))
    elements.append(t)
    elements.append(Spacer(1, 15))

    category_rows = db.query(AuditLog.category, func.count(AuditLog.id)).group_by(AuditLog.category).all()
    if category_rows:
        drawing = Drawing(440, 180)
        pie = Pie(); pie.x = 130; pie.y = 10; pie.width = 160; pie.height = 160
        pie.data = [count for _, count in category_rows]
        pie.labels = [f"{category}: {count}" for category, count in category_rows]
        pie.slices.strokeWidth = .5
        drawing.add(pie)
        elements.append(Paragraph("Distribución de categorías", section_style))
        elements.append(drawing)

    # Muestra de Eventos Críticos Bloqueados
    elements.append(Paragraph("2. Registro de Incidentes Críticos Mitigados (Muestra Reciente)", section_style))
    critical_logs = db.query(AuditLog).filter(AuditLog.action == "BLOCK").order_by(desc(AuditLog.id)).limit(20).all()
    if critical_logs:
        table_rows = [["ID", "Fecha/Hora", "Usuario", "Categoría", "Riesgo", "Extracto Anonimizado"]]
        for c in critical_logs:
            table_rows.append([
                str(c.id),
                c.timestamp[:19].replace("T", " "),
                c.user_id,
                c.category,
                f"{c.risk_score:.2f}",
                Paragraph(c.prompt_redacted[:100] + "...", body_style)
            ])
        t_crit = Table(table_rows, colWidths=[25, 80, 85, 90, 40, 220])
        t_crit.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#c53030')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.HexColor('#fff5f5'), colors.white]),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(t_crit)
    else:
        elements.append(Paragraph("<i>No se registran eventos críticos de bloqueo hasta la fecha.</i>", body_style))

    elements.append(Spacer(1, 20))
    elements.append(Paragraph("3. Alcance y límites del registro", section_style))
    cert_text = (
        "Este informe describe eventos registrados por el prototipo. No acredita certificación, "
        "conformidad normativa, ausencia de incidentes ni cobertura completa de interfaces. "
        "Una decisión de bloqueo no prueba por sí sola que se haya evitado un envío al proveedor."
    )
    elements.append(Paragraph(cert_text, body_style))

    doc.build(elements)
    buffer.seek(0)
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=reporte_auditoria_aegis.pdf"}
    )

# -------------------------------------------------------------
# SERVIR EL WEB DASHBOARD
# -------------------------------------------------------------

if WEB_DASHBOARD_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(WEB_DASHBOARD_DIR)), name="static")

@app.get("/", summary="Acceso al Dashboard Visual de Gobernanza")
async def root_dashboard():
    index_file = WEB_DASHBOARD_DIR / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return {"message": "DLP Shadow AI Governance API en ejecución. Visita /docs para la API o inicia el Dashboard."}

@app.get("/sandbox", summary="Entorno de Prueba Réplica de ChatGPT para Extensión")
async def sandbox_page():
    sandbox_file = WEB_DASHBOARD_DIR / "sandbox.html"
    if sandbox_file.exists():
        return FileResponse(str(sandbox_file))
    return {"error": "sandbox.html no encontrado"}
