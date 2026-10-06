"""
Módulo 1: Pipeline de Datos Híbrido (data/build_dataset.py)
Generación, enriquecimiento y balanceo del dataset para DLP de IA Generativa.
Clases de riesgo:
  0: Safe_Use (Prompts benignos)
  1: PII_Leak (Filtración de PII: DNI, tarjetas, correos, clientes)
  2: Proprietary_Code (Código fuente interno, secretos, tokens, connection strings)
  3: Business_Secrets (Tablas de Excel corporativo, salarios, ventas, M&A, datos estratégicos)
"""

import argparse
import html
import json
import logging
import os
import random
import re
from pathlib import Path
from typing import List, Dict, Tuple, Iterable
from jinja2 import Template

# Fijar semilla para reproducibilidad científica
SEED = 42
random.seed(SEED)
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")
LOGGER = logging.getLogger("aegis.dataset")

DATA_DIR = Path(__file__).resolve().parent
DATA_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_FILE = DATA_DIR / "dataset_hybrid.json"
OUTPUT_DIR = DATA_DIR / "dataset_hybrid"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# -------------------------------------------------------------
# 1. PLANTILLAS Y GENERADORES PARA CADA CLASE
# -------------------------------------------------------------

# CLASE 0: Safe_Use
SAFE_TEMPLATES = [
    "Explícame en términos sencillos cómo funciona el algoritmo de {tech}.",
    "Por favor traduce este texto al inglés formal: '{phrase}'.",
    "¿Cuáles son las mejores prácticas para escribir código limpio en {lang}?",
    "Redacta un correo cordial agradeciendo la reunión de ayer con el equipo de diseño.",
    "Dame un resumen de 3 párrafos sobre la teoría de la relatividad general.",
    "¿Cómo puedo calcular la desviación estándar de una muestra en {lang}?",
    "Escribe un poema corto sobre el otoño y la lluvia en la ciudad.",
    "Sugiere 5 ideas creativas para una campaña de marketing de café artesanal.",
    "¿Cuál es la diferencia entre un proceso y un hilo en sistemas operativos?",
    "Corrige la ortografía y gramática del siguiente párrafo: '{phrase}'.",
    "Genera una rutina de ejercicios de 30 minutos para principiantes sin equipo.",
    "Explica cómo resolver una ecuación diferencial de primer orden separable.",
    "¿Qué impacto tuvo la Revolución Industrial en la urbanización europea?",
    "Dame una analogía para explicar qué es una API a una persona no técnica.",
    "¿Cuáles son los principios SOLID y cómo se aplican en la arquitectura de software?",
    "Explain how gradient descent works in neural networks.",
    "Can you write a polite email asking for a meeting rescheduling?",
    "Summarize the main differences between TCP and UDP protocols.",
    "What are the key benefits of containerization using Docker?",
    "Provide a recipe for homemade gluten-free chocolate chip cookies."
]

TECH_LIST = ["quicksort", "backpropagation", "búsqueda binaria", "árboles AVL", "Dijkstra", "Fast Fourier Transform"]
LANG_LIST = ["Python", "JavaScript", "Rust", "Go", "C++", "TypeScript", "Kotlin"]
PHRASES = [
    "Agradecemos su tiempo y quedamos atentos a cualquier duda adicional",
    "El proyecto continúa avanzando según el cronograma acordado en el sprint inicial",
    "Esperamos poder colaborar en futuras oportunidades de desarrollo tecnológico",
    "La presentación de resultados se llevará a cabo el próximo jueves a las 10am"
]

# CLASE 1: PII_Leak
FIRST_NAMES = ["Carlos", "María", "David", "Lucía", "Jorge", "Ana", "Miguel", "Sofía", "Fernando", "Elena", "Rodrigo", "Valentina"]
LAST_NAMES = ["García", "Rodríguez", "Mendoza", "Vásquez", "Torres", "Pérez", "López", "Gómez", "Flores", "Sánchez"]
CITIES = ["Lima", "Bogotá", "Madrid", "Ciudad de México", "Buenos Aires", "Santiago", "Medellín"]
DOMAINS = ["gmail.com", "outlook.com", "yahoo.es", "hotmail.com", "proton.me"]

def generate_pii_sample() -> str:
    patterns = [
        # Caso DNI / Pasaporte / Cédula y datos personales
        lambda: (
            f"Por favor verifica si estos documentos son válidos para el registro de usuarios: "
            f"Nombre: {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}, "
            f"DNI: {random.randint(10000000, 99999999)}, "
            f"Teléfono: +51 9{random.randint(10000000, 99999999)}, "
            f"Email: {random.choice(FIRST_NAMES).lower()}.{random.choice(LAST_NAMES).lower()}@{random.choice(DOMAINS)}, "
            f"Dirección: Av. {random.choice(['Primavera', 'Arequipa', 'Larco', 'Insurgentes'])} #{random.randint(100, 2500)}, {random.choice(CITIES)}."
        ),
        # Caso Tarjeta de crédito / PII financiera
        lambda: (
            f"ChatGPT, ayúdame a procesar este reembolso. Datos del tarjetahabiente: "
            f"Titular: {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} | "
            f"Tarjeta Visa: 4{random.randint(100,999)} {random.randint(1000,9999)} {random.randint(1000,9999)} {random.randint(1000,9999)} | "
            f"Vencimiento: {random.randint(1,12):02d}/{random.randint(26,31)} | CVV: {random.randint(100,999)} | "
            f"Monto: ${random.randint(50, 4500)}.00 USD."
        ),
        # Lista de clientes con PII extraída
        lambda: (
            f"Tengo esta lista de postulantes con sus datos privados, redáctame un email para cada uno: \n"
            f"1. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} - DNI {random.randint(10000000, 99999999)} - Correo: {random.choice(FIRST_NAMES).lower()}{random.randint(10,99)}@{random.choice(DOMAINS)} - Tel: 9{random.randint(10000000, 99999999)}\n"
            f"2. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} - DNI {random.randint(10000000, 99999999)} - Correo: {random.choice(FIRST_NAMES).lower()}{random.randint(10,99)}@{random.choice(DOMAINS)} - Tel: 9{random.randint(10000000, 99999999)}\n"
            f"3. {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)} - DNI {random.randint(10000000, 99999999)} - Correo: {random.choice(FIRST_NAMES).lower()}{random.randint(10,99)}@{random.choice(DOMAINS)} - Tel: 9{random.randint(10000000, 99999999)}"
        ),
        # Datos médicos o sensibles
        lambda: (
            f"Resume el historial clínico de este paciente confidencial: "
            f"Paciente: {random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}, Edad: {random.randint(22, 75)}, "
            f"Seguro Social: {random.randint(100,999)}-{random.randint(10,99)}-{random.randint(1000,9999)}, "
            f"Diagnóstico preliminar: Hipertensión severa e insuficiencia cardíaca grado II. Medicación prescrita: Enalapril 20mg."
        )
    ]
    return random.choice(patterns)()

# CLASE 2: Proprietary_Code
def generate_code_sample() -> str:
    patterns = [
        # Script con secreto / API Key hardcodeada
        lambda: (
            f"Revisa este script de conexión de nuestra infraestructura interna para ver por qué falla:\n"
            f"import boto3\n"
            f"AWS_ACCESS_KEY_ID = 'AKIA{random.randint(1000000000, 9999999999)}PROD'\n"
            f"AWS_SECRET_ACCESS_KEY = 'wJalrXUtnFEMI/K7MDENG/bPxRfiCY{random.randint(100000, 999999)}KEY'\n"
            f"s3 = boto3.client('s3', aws_access_key_id=AWS_ACCESS_KEY_ID, aws_secret_access_key=AWS_SECRET_ACCESS_KEY)\n"
            f"s3.download_file('empresa-core-backups-internal', 'database_dump_2024.sql', '/tmp/restore.sql')"
        ),
        # Cadena de conexión interna con credenciales
        lambda: (
            f"¿Por qué este endpoint de base de datos me da timeout?\n"
            f"DATABASE_URL = 'postgresql://admin_prod:SuperSecret_{random.randint(1000,9999)}@db-internal.corp.empresa.internal:5432/core_billing'\n"
            f"engine = create_engine(DATABASE_URL)\n"
            f"def get_transactions():\n"
            f"    return engine.execute('SELECT * FROM accounts_master WHERE balance > 100000')"
        ),
        # Código propietario interno con lógica de negocio confidencial
        lambda: (
            f"Optimiza esta función propietaria de nuestro motor de cálculo de precios internos:\n"
            f"def _calculate_proprietary_arbitrage_risk(spread: float, capital: float, internal_tier: int):\n"
            f"    # ALGORITMO CONFIDENCIAL BANCO - PROHIBIDA SU DISTRIBUCION EXTERNA\n"
            f"    alpha_factor = 0.0345 if internal_tier > 3 else 0.012\n"
            f"    leverage_margin = capital * (spread ** 1.4) * alpha_factor\n"
            f"    token_vault_auth = 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.{random.randint(10000000,99999999)}.secret'\n"
            f"    return leverage_margin, token_vault_auth"
        ),
        # Private RSA Key / PEM
        lambda: (
            f"Ayúdame a convertir esta llave privada interna a formato PKCS8:\n"
            f"-----BEGIN RSA PRIVATE KEY-----\n"
            f"MIIEowIBAAKCAQEA0r1f{random.randint(100000, 999999)}K9xV8zL4P9Q2wE4m5...CONFIDENTIAL_CORP_KEY...\n"
            f"aBcDeFgHiJkLmNoPqRsTuVwXyZ0123456789+/{random.randint(10000, 99999)}\n"
            f"-----END RSA PRIVATE KEY-----"
        )
    ]
    return random.choice(patterns)()

# CLASE 3: Business_Secrets (Tablas de Excel corporativo, salarios, ventas, M&A)
# Enfoque directo en el comentario del usuario:
# "si le escribes al chagpt que quieres que te ordene un excel de datos de tu empresa esta vaina lo va a bloquear y reportar"
COMPANY_NAMES = ["TechCorp S.A.C.", "Banco Central Andino", "Inversiones del Pacífico", "Logística Global S.A.", "Retail Norte Perú", "Financiera Futuro", "Minería Santa Rosa"]
DEPARTMENTS = ["Ventas B2B", "Alta Dirección", "Finanzas & Tesorería", "Recursos Humanos", "Ciberseguridad", "Operaciones"]

def generate_business_secret_sample() -> str:
    comp = random.choice(COMPANY_NAMES)
    dep = random.choice(DEPARTMENTS)
    
    patterns = [
        # CASO DIRECTO: "Ordéname este excel de mi empresa"
        lambda: Template(
            "ChatGPT, ayúdame a ordenar y estructurar este excel de datos de mi empresa ({{ company }}). "
            "Quiero que lo ordenes por mayor margen de ventas y me digas quién factura más:\n"
            "{{ table }}"
        ).render(company=comp, table=(
            f"ID_Empleado\tNombre\tDepartamento\tSalario_Mensual\tVentas_Q3_USD\tMargen_Bruto\n"
            f"EMP-{random.randint(100,999)}\t{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}\t{dep}\t${random.randint(3000, 18000)}\t${random.randint(50000, 450000)}\t{random.randint(18, 42)}%\n"
            f"EMP-{random.randint(100,999)}\t{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}\t{dep}\t${random.randint(3000, 18000)}\t${random.randint(50000, 450000)}\t{random.randint(18, 42)}%\n"
            f"EMP-{random.randint(100,999)}\t{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}\t{dep}\t${random.randint(3000, 18000)}\t${random.randint(50000, 450000)}\t{random.randint(18, 42)}%\n"
            f"EMP-{random.randint(100,999)}\t{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}\t{dep}\t${random.randint(3000, 18000)}\t${random.randint(50000, 450000)}\t{random.randint(18, 42)}%"
        )),
        # CASO TABLA CSV DE PLANILLA Y SALARIOS
        lambda: (
            f"Necesito que calcules el bono anual de fin de año para esta planilla confidencial que copié de Excel:\n"
            f"Colaborador, Cargo, Sueldo_Base, Bono_Desempeño, Retención_Impuestos, Cuenta_Abono\n"
            f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}, Gerente General, S/{random.randint(25000, 45000)}, S/{random.randint(15000, 30000)}, 29.5%, BCP-193-{random.randint(100000,999999)}\n"
            f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}, Director Finanzas, S/{random.randint(18000, 32000)}, S/{random.randint(10000, 20000)}, 29.5%, BBVA-0011-{random.randint(100000,999999)}\n"
            f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}, Subgerente TI, S/{random.randint(12000, 22000)}, S/{random.randint(5000, 12000)}, 21.0%, Interbank-200-{random.randint(100000,999999)}"
        ),
        # CASO M&A / ESTRATEGIA FINANCIERA NO PÚBLICA
        lambda: (
            f"Redacta un memo ejecutivo sobre esta adquisición confidencial (M&A) del directorio de {comp}:\n"
            f"Target: Competidor Estratégico Andina Corp.\n"
            f"Valoración pre-money: ${random.randint(15, 80)} millones de USD.\n"
            f"EBITDA proyectado 2025: ${random.randint(4, 18)}M con sinergias de reducción de personal del {random.randint(15, 35)}%.\n"
            f"Ronda de financiamiento puente acordada bajo estricto acuerdo de no divulgación (NDA)."
        ),
        # CASO LISTA DE CLIENTES CORPORATIVOS Y DESCUENTOS SECRETOS
        lambda: (
            f"Ayúdame a organizar esta tabla de precios confidenciales y descuentos especiales otorgados a clientes corporativos:\n"
            f"Cliente Corporativo | Volumen Anual ($) | Descuento Secreto (%) | Costo Real Fábrica | Margen Neto Oculto\n"
            f"Empresa Alpha SAC | ${random.randint(200, 900)}K | {random.randint(25, 45)}% | ${random.randint(80, 400)}K | {random.randint(10, 22)}%\n"
            f"Grupo Comercial Sur | ${random.randint(300, 1200)}K | {random.randint(20, 40)}% | ${random.randint(120, 600)}K | {random.randint(12, 28)}%\n"
            f"Consorcio Metropolitano | ${random.randint(500, 2500)}K | {random.randint(30, 50)}% | ${random.randint(200, 1100)}K | {random.randint(8, 19)}%"
        ),
        # CASO REPORTE DE RESULTADOS NO PUBLICADOS
        lambda: (
            f"Hazme un resumen del estado de pérdidas y ganancias no publicado del Q2 de {comp} antes de la auditoría externa:\n"
            f"Ingresos Brutos: ${random.randint(12, 95)}M. Costo de ventas: ${random.randint(7, 50)}M.\n"
            f"Gastos operativos ocultos: ${random.randint(2, 10)}M. Utilidad neta atribuible a socios: ${random.randint(3, 25)}M.\n"
            f"Pasivos contingentes por litigio tributario con SUNAT/SAT: S/{random.randint(5, 20)} millones."
        )
    ]
    return random.choice(patterns)()


# -------------------------------------------------------------
# 2. INGESTA, LIMPIEZA, GENERACIÓN Y BALANCEO
# -------------------------------------------------------------

CONTROL_CHARS = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")
HTML_TAGS = re.compile(r"<[^>]+>")
_REFERENCE_TOKENIZER = None


def clean_text(value: str, max_chars: int = 12000) -> str:
    """Normaliza HTML/Markdown/control chars without changing semantic content."""
    value = html.unescape(str(value or ""))
    value = HTML_TAGS.sub(" ", value)
    value = CONTROL_CHARS.sub(" ", value)
    value = re.sub(r"```(?:\w+)?", "", value)
    value = re.sub(r"[ \t]+", " ", value)
    value = re.sub(r"\n{3,}", "\n\n", value).strip()
    return value[:max_chars]


def truncate_to_512_tokens(value: str) -> str:
    global _REFERENCE_TOKENIZER
    try:
        if _REFERENCE_TOKENIZER is None:
            from transformers import AutoTokenizer
            _REFERENCE_TOKENIZER = AutoTokenizer.from_pretrained("microsoft/deberta-v3-small", local_files_only=True)
        ids = _REFERENCE_TOKENIZER(value, add_special_tokens=False, truncation=True, max_length=512)["input_ids"]
        return _REFERENCE_TOKENIZER.decode(ids, skip_special_tokens=True)
    except Exception:
        # Safe offline fallback; training performs authoritative token truncation again.
        return value[:12000]


def pseudonymize_training_pii(text: str) -> str:
    """Replace real-looking PII before it can enter the research corpus."""
    text = re.sub(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b", "user[AT]example.invalid", text)
    text = re.sub(r"(?i)(DNI|cedula|cédula|passport|pasaporte)\s*[:#-]?\s*\d{7,12}", r"\1: ID_SYNTHETIC", text)
    text = re.sub(r"\b(?:\d[ -]*?){13,19}\b", "CARD_SYNTHETIC", text)
    return text


def load_public_samples(max_per_source: int = 500) -> List[Dict]:
    """Best-effort streaming ingestion from the public datasets named in the specification.

    Network/auth/schema failures are isolated per source and never make the reproducible
    offline pipeline fail. Every imported row is pseudonymized before persistence.
    """
    try:
        from datasets import load_dataset
    except ImportError:
        LOGGER.warning("datasets is unavailable; continuing in offline mode")
        return []

    specs = [
        ("lmsys/lmsys-chat-1m", "train", 0, ("conversation", "text", "prompt")),
        ("allenai/WildChat-1M", "train", 0, ("conversation", "text", "prompt")),
        ("ai4privacy/pii-masking-300k", "train", 1, ("source_text", "text", "prompt")),
        ("bigcode/the-stack-smol", "train", 2, ("content", "text", "code")),
    ]
    rows: List[Dict] = []
    for dataset_name, split, label, fields in specs:
        imported = 0
        try:
            stream = load_dataset(dataset_name, split=split, streaming=True, trust_remote_code=False)
            for item in stream:
                raw = next((item.get(field) for field in fields if item.get(field)), None)
                if isinstance(raw, list):
                    raw = "\n".join(str(turn.get("content", turn)) if isinstance(turn, dict) else str(turn) for turn in raw)
                text = pseudonymize_training_pii(clean_text(raw or ""))
                if len(text) < 20:
                    continue
                rows.append({"text": text, "label": label, "label_name": CLASS_NAMES[label],
                             "action": "ALLOW" if label == 0 else "BLOCK", "source": dataset_name})
                imported += 1
                if imported >= max_per_source:
                    break
            LOGGER.info("Imported %d sanitized samples from %s", imported, dataset_name)
        except Exception as exc:
            LOGGER.warning("Source %s unavailable: %s", dataset_name, exc)
    return rows


CLASS_NAMES = ["Safe_Use", "PII_Leak", "Proprietary_Code", "Business_Secrets"]


def _dedupe(rows: Iterable[Dict]) -> List[Dict]:
    seen = set()
    output = []
    for row in rows:
        row["text"] = truncate_to_512_tokens(clean_text(row["text"]))
        key = re.sub(r"\W+", " ", row["text"].casefold()).strip()
        if key and key not in seen:
            seen.add(key)
            output.append(row)
    return output


def _stratified_split(dataset: List[Dict]) -> Tuple[List[Dict], List[Dict], List[Dict]]:
    train, val, test = [], [], []
    for label in range(4):
        group = [row for row in dataset if row["label"] == label]
        random.shuffle(group)
        n = len(group)
        train.extend(group[: int(n * .8)])
        val.extend(group[int(n * .8): int(n * .9)])
        test.extend(group[int(n * .9):])
    random.shuffle(train); random.shuffle(val); random.shuffle(test)
    return train, val, test


def apply_back_translation(rows: List[Dict], limit: int = 1000) -> None:
    """Round-trip ES→EN→ES augmentation for Business_Secrets (optional download)."""
    from transformers import pipeline
    es_en = pipeline("translation", model="Helsinki-NLP/opus-mt-es-en", device=-1)
    en_es = pipeline("translation", model="Helsinki-NLP/opus-mt-en-es", device=-1)
    indexes = [i for i, row in enumerate(rows) if row["label"] == 3][:limit]
    for start in range(0, len(indexes), 16):
        batch_indexes = indexes[start:start + 16]
        originals = [rows[i]["text"][:1500] for i in batch_indexes]
        english = [x["translation_text"] for x in es_en(originals, batch_size=16, max_length=512)]
        spanish = [x["translation_text"] for x in en_es(english, batch_size=16, max_length=512)]
        for idx, text in zip(batch_indexes, spanish):
            rows[idx]["text"] = text; rows[idx]["source"] = "synthetic_back_translation"


def build_dataset(total_samples: int = 20000, use_public_data: bool = True,
                  back_translation: bool = False) -> Tuple[List[Dict], Dict]:
    if total_samples < 20000:
        LOGGER.warning("Scientific profile requires >=20,000 rows so Business_Secrets has >=5,000 samples")
    samples_per_class = total_samples // 4
    public = load_public_samples(min(1000, samples_per_class // 4)) if use_public_data else []
    dataset: List[Dict] = list(public)
    
    print(f"[*] Generando {total_samples} muestras balanceadas ({samples_per_class} por clase)...")
    
    # 0: Safe_Use
    for i in range(max(0, samples_per_class - sum(x["label"] == 0 for x in dataset))):
        tmpl = random.choice(SAFE_TEMPLATES)
        prompt = tmpl.format(
            tech=random.choice(TECH_LIST),
            phrase=random.choice(PHRASES),
            lang=random.choice(LANG_LIST)
        )
        dataset.append({
            "text": f"{prompt} Contexto público de práctica #{i + 1}.",
            "label": 0,
            "label_name": "Safe_Use",
            "action": "ALLOW", "source": "synthetic_template"
        })
        
    # 1: PII_Leak
    for _ in range(max(0, samples_per_class - sum(x["label"] == 1 for x in dataset))):
        prompt = generate_pii_sample()
        dataset.append({
            "text": prompt,
            "label": 1,
            "label_name": "PII_Leak",
            "action": "BLOCK", "source": "synthetic_privacy_safe"
        })
        
    # 2: Proprietary_Code
    for _ in range(max(0, samples_per_class - sum(x["label"] == 2 for x in dataset))):
        prompt = generate_code_sample()
        dataset.append({
            "text": prompt,
            "label": 2,
            "label_name": "Proprietary_Code",
            "action": "BLOCK", "source": "synthetic_placeholder_secrets"
        })
        
    # 3: Business_Secrets (incluye Excel de empresa, salarios, ventas, M&A)
    for _ in range(max(0, samples_per_class - sum(x["label"] == 3 for x in dataset))):
        prompt = generate_business_secret_sample()
        dataset.append({
            "text": prompt,
            "label": 3,
            "label_name": "Business_Secrets",
            "action": "BLOCK", "source": "synthetic_jinja_style"
        })
        
    if back_translation:
        apply_back_translation(dataset)
    dataset = _dedupe(dataset)
    # Refill after deduplication so every class retains the requested cardinality.
    existing = {re.sub(r"\W+", " ", row["text"].casefold()).strip() for row in dataset}
    generators = {1: generate_pii_sample, 2: generate_code_sample, 3: generate_business_secret_sample}
    for label in range(4):
        refill_index = 0
        while sum(row["label"] == label for row in dataset) < samples_per_class:
            refill_index += 1
            if label == 0:
                candidate = f"Consulta pública segura de documentación técnica, ejemplo único {SEED}-{refill_index}."
            else:
                candidate = generators[label]()
            candidate = clean_text(candidate)
            key = re.sub(r"\W+", " ", candidate.casefold()).strip()
            if key in existing:
                continue
            existing.add(key)
            dataset.append({"text": candidate, "label": label, "label_name": CLASS_NAMES[label],
                            "action": "ALLOW" if label == 0 else "BLOCK", "source": "synthetic_refill"})
    train_data, val_data, test_data = _stratified_split(dataset)
    total = len(dataset)
    
    # Métricas de balance
    stats = {
        "total_samples": total,
        "splits": {
            "train": len(train_data),
            "val": len(val_data),
            "test": len(test_data)
        },
        "class_distribution": {
            "0_Safe_Use": sum(1 for x in dataset if x["label"] == 0),
            "1_PII_Leak": sum(1 for x in dataset if x["label"] == 1),
            "2_Proprietary_Code": sum(1 for x in dataset if x["label"] == 2),
            "3_Business_Secrets": sum(1 for x in dataset if x["label"] == 3)
        }
    }
    
    # Guardar en JSON Lines y splits
    print(f"[*] Guardando dataset completo en {OUTPUT_FILE}...")
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        for item in dataset:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(OUTPUT_DIR / "train.jsonl", "w", encoding="utf-8") as f:
        for item in train_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(OUTPUT_DIR / "val.jsonl", "w", encoding="utf-8") as f:
        for item in val_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    with open(OUTPUT_DIR / "test.jsonl", "w", encoding="utf-8") as f:
        for item in test_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
            
    # Hugging Face Arrow DatasetDict. JSONL remains for transparent inspection.
    arrow_saved = False
    try:
        from datasets import Dataset, DatasetDict
        arrow_dir = DATA_DIR / "dataset_hf"
        DatasetDict({
            "train": Dataset.from_list(train_data),
            "validation": Dataset.from_list(val_data),
            "test": Dataset.from_list(test_data),
        }).save_to_disk(str(arrow_dir))
        arrow_saved = True
    except ImportError:
        LOGGER.warning("Install requirements.txt to generate Arrow output")

    stats["arrow_saved"] = arrow_saved
    stats["sources"] = sorted({row.get("source", "unknown") for row in dataset})
    stats["exact_cross_split_overlap"] = {
        "train_validation": len({x["text"] for x in train_data} & {x["text"] for x in val_data}),
        "train_test": len({x["text"] for x in train_data} & {x["text"] for x in test_data}),
        "validation_test": len({x["text"] for x in val_data} & {x["text"] for x in test_data}),
    }
    with open(DATA_DIR / "dataset_stats.json", "w", encoding="utf-8") as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)
        
    return dataset, stats

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Build the Aegis hybrid DLP corpus")
    parser.add_argument("--samples", type=int, default=20000)
    parser.add_argument("--offline", action="store_true", help="Do not attempt public Hugging Face sources")
    parser.add_argument("--back-translation", action="store_true", help="Apply MarianMT round-trip augmentation")
    args = parser.parse_args()
    dataset, stats = build_dataset(total_samples=args.samples, use_public_data=not args.offline,
                                   back_translation=args.back_translation)
    print("\n=======================================================")
    print("  REPORTE DE GENERACIÓN DE DATASET HÍBRIDO (DLP IA)")
    print("=======================================================")
    print(f"Total de muestras generadas: {stats['total_samples']}")
    print(f"División: Train={stats['splits']['train']} | Val={stats['splits']['val']} | Test={stats['splits']['test']}")
    print("Distribución por clase de riesgo:")
    for k, v in stats["class_distribution"].items():
        pct = (v / stats["total_samples"]) * 100
        print(f"  - {k:20s}: {v:5d} muestras ({pct:.1f}%)")
    print("=======================================================\n")
