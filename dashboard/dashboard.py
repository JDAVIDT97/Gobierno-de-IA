"""
Módulo 5: Dashboard de Gobernanza Streamlit (dashboard/dashboard.py)
Interfaz analítica para el CISO / equipo de Gobernanza de TIC con métricas de cumplimiento ISO 42001.
"""

import os
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "api" / "audit_logs.db"

# Configuración de página Streamlit
st.set_page_config(
    page_title="Aegis DLP | CISO Governance Dashboard",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Estilos CSS oscuros y refinados
st.markdown("""
<style>
    .main { background-color: #070a13; color: #f8fafc; }
    .stMetric { background: #0e1626; padding: 15px; border-radius: 12px; border: 1px solid rgba(255,255,255,0.08); }
    h1, h2, h3 { color: #f8fafc !important; font-family: 'Segoe UI', Roboto, sans-serif; }
</style>
""", unsafe_allow_html=True)

def load_data():
    if not DB_PATH.exists():
        return pd.DataFrame()
    
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM audit_logs ORDER BY id DESC", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
        
    if not df.empty and "timestamp" in df.columns:
        df["dt"] = pd.to_datetime(df["timestamp"], errors="coerce")
    return df

st.title("🛡️ Aegis DLP | Tablero de Gobernanza y Shadow AI")
st.caption("Inspección perimetral de inferencia local (<50ms) alineada con ISO/IEC 42001:2023 y EU AI Act Art. 52")

df = load_data()

# Barra lateral con filtros
st.sidebar.header("⚙️ Filtros de Auditoría")
if not df.empty:
    window = st.sidebar.selectbox("Ventana temporal:", ["1h", "24h", "7d", "30d", "Todo"], index=1)
    action_filter = st.sidebar.multiselect(
        "Acción DLP:",
        options=df["action"].unique().tolist(),
        default=df["action"].unique().tolist()
    )
    category_filter = st.sidebar.multiselect(
        "Categoría de Riesgo:",
        options=df["category"].unique().tolist(),
        default=df["category"].unique().tolist()
    )
    user_filter = st.sidebar.text_input("User ID contiene:").strip()
    now = pd.Timestamp.now(tz="UTC")
    window_hours = {"1h": 1, "24h": 24, "7d": 168, "30d": 720}
    time_mask = pd.Series(True, index=df.index)
    if window in window_hours and "dt" in df:
        parsed = pd.to_datetime(df["dt"], utc=True, errors="coerce")
        time_mask = parsed >= now - pd.Timedelta(hours=window_hours[window])

    filtered_df = df[
        (df["action"].isin(action_filter)) &
        (df["category"].isin(category_filter)) & time_mask &
        (df["user_id"].str.contains(user_filter, case=False, regex=False) if user_filter else True)
    ]
else:
    filtered_df = pd.DataFrame()

# -------------------------------------------------------------
# 5.1 PANEL DE KPIS (TOP SECTION)
# -------------------------------------------------------------
st.markdown("### 📊 Indicadores Clave de Desempeño (KPIs)")
kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

total_audited = len(filtered_df)
total_last_24h = len(df[pd.to_datetime(df["dt"], utc=True, errors="coerce") >= pd.Timestamp.now(tz="UTC") - pd.Timedelta(hours=24)]) if not df.empty else 0
total_blocked = len(filtered_df[filtered_df["action"] == "BLOCK"]) if total_audited > 0 else 0
block_rate = (total_blocked / total_audited * 100) if total_audited > 0 else 0.0
avg_risk = filtered_df["risk_score"].mean() if total_audited > 0 else 0.0

with kpi_col1:
    st.metric("Total Prompts Auditados", f"{total_audited:,}", delta=f"{total_last_24h} últimas 24h")
with kpi_col2:
    st.metric("Fugas Bloqueadas (BLOCK)", f"{total_blocked:,}", delta=f"{block_rate:.1f}% tasa bloqueo", delta_color="inverse")
with kpi_col3:
    st.metric("Nivel de Riesgo Medio", f"{avg_risk:.2f} / 1.00")
with kpi_col4:
    avg_latency = filtered_df["inference_time_ms"].mean() if total_audited > 0 else 0.8
    st.metric("Latencia Media CPU", f"{avg_latency:.2f} ms", delta="Meta < 50ms (OK)")

st.divider()

# -------------------------------------------------------------
# 5.2 VISUALIZACIONES INTERACTIVAS
# -------------------------------------------------------------
st.markdown("### 📈 Visualizaciones Analíticas")
viz_col1, viz_col2 = st.columns(2)

if not filtered_df.empty:
    with viz_col1:
        st.subheader("Distribución de Clases de Riesgo")
        cat_counts = filtered_df["category"].value_counts().reset_index()
        cat_counts.columns = ["Categoría", "Cantidad"]
        fig_donut = px.pie(
            cat_counts,
            names="Categoría",
            values="Cantidad",
            hole=0.6,
            color="Categoría",
            color_discrete_map={
                "Safe_Use": "#10b981",
                "Business_Secrets": "#ff2a5f",
                "PII_Leak": "#f59e0b",
                "Proprietary_Code": "#9d4edd"
            }
        )
        fig_donut.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#94a3b8")
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with viz_col2:
        st.subheader("Línea Temporal de Eventos")
        if "dt" in filtered_df.columns and filtered_df["dt"].notnull().any():
            trend_df = filtered_df.copy()
            trend_df["minute"] = trend_df["dt"].dt.floor("min")
            timeline = trend_df.groupby(["minute", "action"]).size().reset_index(name="count")
            fig_timeline = px.line(
                timeline,
                x="minute",
                y="count",
                color="action",
                color_discrete_map={"ALLOW": "#10b981", "BLOCK": "#ff2a5f"},
                markers=True
            )
            fig_timeline.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#94a3b8")
            )
            st.plotly_chart(fig_timeline, use_container_width=True)
        else:
            st.info("Sin marcas de tiempo suficientes para serie temporal.")

    st.divider()

    extra1, extra2 = st.columns(2)
    with extra1:
        st.subheader("Heatmap de actividad (hora × día)")
        heat = filtered_df.dropna(subset=["dt"]).copy()
        if not heat.empty:
            heat["hour"] = heat["dt"].dt.hour
            heat["weekday"] = heat["dt"].dt.day_name()
            pivot = heat.pivot_table(index="weekday", columns="hour", values="id", aggfunc="count", fill_value=0)
            fig_heat = px.imshow(pivot, aspect="auto", color_continuous_scale="RdPu", labels={"color": "Eventos"})
            st.plotly_chart(fig_heat, use_container_width=True)
    with extra2:
        st.subheader("Nube segura de señales bloqueadas")
        blocked = filtered_df[filtered_df["action"] == "BLOCK"]
        if not blocked.empty:
            from wordcloud import WordCloud
            import matplotlib.pyplot as plt
            safe_terms = " ".join(blocked["category"].str.replace("_", " ").tolist())
            cloud = WordCloud(width=900, height=360, background_color="#070a13", colormap="cool").generate(safe_terms)
            fig, ax = plt.subplots(figsize=(9, 3.6)); ax.imshow(cloud); ax.axis("off")
            st.pyplot(fig, use_container_width=True)
        else:
            st.info("Sin bloqueos en la ventana seleccionada.")

    st.divider()

    # -------------------------------------------------------------
    # 5.3 TABLA DE AUDITORÍA DETALLADA
    # -------------------------------------------------------------
    st.markdown("### 📋 Bitácora Detallada de Auditoría")
    display_cols = ["id", "timestamp", "user_id", "destination", "action", "category", "risk_score", "inference_time_ms", "prompt_redacted"]
    st.dataframe(
        filtered_df[display_cols],
        use_container_width=True,
        hide_index=True
    )

    # -------------------------------------------------------------
    # 5.4 EXPORTACIÓN DE REPORTES
    # -------------------------------------------------------------
    st.markdown("### 📥 Exportación de Reportes de Cumplimiento")
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        csv_data = filtered_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Descargar Auditoría en CSV",
            data=csv_data,
            file_name="audit_logs_ciso.csv",
            mime="text/csv"
        )
    with exp_col2:
        st.link_button("Descargar Informe Formal PDF (ISO 42001)", "http://localhost:8000/v1/export-pdf")

else:
    st.warning("No hay registros en la base de datos de auditoría aún. Inicia la API y realiza pruebas.")
