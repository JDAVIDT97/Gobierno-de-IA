"""
Base de Datos y Modelos SQLAlchemy para Auditoría (api/database.py)
Persistencia en SQLite (audit_logs.db) con índices optimizados y trazabilidad ISO 42001.
"""

from pathlib import Path
import os
from datetime import datetime, timezone
from sqlalchemy import create_engine, Column, Integer, String, Float, Index, CheckConstraint, text, event
from sqlalchemy.orm import declarative_base, sessionmaker

BASE_DIR = Path(__file__).resolve().parent
DB_FILE = BASE_DIR / "audit_logs.db"
SQLALCHEMY_DATABASE_URL = os.getenv("AEGIS_DATABASE_URL", f"sqlite:///{DB_FILE.as_posix()}")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)


@event.listens_for(engine, "connect")
def configure_sqlite(dbapi_connection, _connection_record):
    if SQLALCHEMY_DATABASE_URL.startswith("sqlite"):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    timestamp = Column(String, nullable=False, default=lambda: datetime.now(timezone.utc).isoformat())
    user_id = Column(String, nullable=False, index=True)
    prompt_hash = Column(String, nullable=False)
    prompt_redacted = Column(String, nullable=False)
    destination = Column(String, nullable=True)
    action = Column(String, nullable=False, index=True)  # ALLOW / BLOCK
    category = Column(String, nullable=False)            # Safe_Use, PII_Leak, Proprietary_Code, Business_Secrets
    risk_score = Column(Float, nullable=False)
    confidence = Column(Float, nullable=False)
    model_version = Column(String, nullable=False, default="dlp-slm-v1.0")
    inference_time_ms = Column(Float, nullable=False)

    __table_args__ = (
        CheckConstraint("action IN ('ALLOW', 'BLOCK')", name="ck_audit_action"),
        CheckConstraint("risk_score >= 0 AND risk_score <= 1", name="ck_audit_risk"),
        Index("idx_timestamp", "timestamp"),
        Index("idx_user", "user_id"),
        Index("idx_action", "action"),
    )

def init_db():
    """Inicializa el esquema de la base de datos si no existe."""
    Base.metadata.create_all(bind=engine)
    # Backward-compatible hardening for SQLite databases created before v2.
    with engine.begin() as conn:
        conn.execute(text("""UPDATE audit_logs SET prompt_redacted = CASE
            WHEN action = 'ALLOW' THEN '[SAFE_PROMPT_NOT_RETAINED]'
            ELSE '[BLOCKED_CONTENT_NOT_RETAINED:' || category || ']' END
            WHERE prompt_redacted NOT LIKE '[SAFE_PROMPT_NOT_RETAINED]'
              AND prompt_redacted NOT LIKE '[BLOCKED_CONTENT_NOT_RETAINED:%'"""))
        conn.execute(text("""CREATE TRIGGER IF NOT EXISTS trg_audit_validate_insert
            BEFORE INSERT ON audit_logs WHEN NEW.action NOT IN ('ALLOW','BLOCK')
            OR NEW.risk_score < 0 OR NEW.risk_score > 1
            BEGIN SELECT RAISE(ABORT, 'invalid audit record'); END"""))
        conn.execute(text("""CREATE TRIGGER IF NOT EXISTS trg_audit_validate_update
            BEFORE UPDATE ON audit_logs WHEN NEW.action NOT IN ('ALLOW','BLOCK')
            OR NEW.risk_score < 0 OR NEW.risk_score > 1
            BEGIN SELECT RAISE(ABORT, 'invalid audit record'); END"""))

def get_db():
    """Dependencia para inyección de sesiones SQLAlchemy."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
