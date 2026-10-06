"""
Motor Híbrido de Detección y Anonimización DLP (api/engine.py)
Combina reglas heurísticas de alta velocidad (detección de tablas Excel, PII, secretos)
con el modelo probabilístico SLM entrenado para clasificación de riesgo en <50ms.
"""

import json
import os
import re
import time
from pathlib import Path
from typing import Dict, Any, List, Tuple
import joblib
import numpy as np

from api.strict_intent_guard import is_defensive_security_request, is_safe_security_request, match_strict_intent

BASE_DIR = Path(__file__).resolve().parent.parent
MODEL_DIR = BASE_DIR / "models" / "dlp_slm"
MODEL_PATH = MODEL_DIR / "model.joblib"

CLASS_NAMES = ["Safe_Use", "PII_Leak", "Proprietary_Code", "Business_Secrets", "Code_Exploitation", "Data_Exfiltration", "Social_Engineering", "Role_Evasion_Jailbreak", "Legal_Misalignment"]

# -------------------------------------------------------------
# PATRONES HEURÍSTICOS (REGEX) DE ALTA VELOCIDAD
# -------------------------------------------------------------

# Secretos y credenciales de código
REGEX_AWS_KEY = re.compile(r'\bAKIA[0-9A-Z]{16}\b')
REGEX_OPENAI_KEY = re.compile(r'\bsk-[a-zA-Z0-9_\-]{20,}\b')
REGEX_PRIVATE_KEY = re.compile(r'-----BEGIN\s+[A-Z\s]*PRIVATE\s+KEY-----.*?-----END\s+[A-Z\s]*PRIVATE\s+KEY-----', re.IGNORECASE | re.DOTALL)
REGEX_CONN_STR = re.compile(r'(?:postgres|postgresql|mysql|mongodb|redis|sqlserver):\/\/[^\s:]+:[^\s@]+@[^\s]+', re.IGNORECASE)
REGEX_GENERIC_SECRET = re.compile(r'(?:api[_\-\s]?key|access[_\-\s]?key[_\-\s]?id|secret[_\-\s]?(?:access[_\-\s]?)?key|password|contrase(?:ñ|n)a|token|auth)\s*[:=]\s*[\'"][^\'"]{8,}[\'"]', re.IGNORECASE)

# PII
REGEX_EMAIL = re.compile(r'\b[A-Za-z0-9._%+\-]+@[A-Za-z0-9.\-]+\.[A-Za-z]{2,}\b')
REGEX_CARD = re.compile(r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13}|6(?:011|5[0-9]{2})[0-9]{12})\b|\b(?:\d{4}[\s\-]){3}\d{4}\b')
REGEX_PHONE = re.compile(r'(?:\+\d{1,3}[ \-]?)?(?:9\d{8}|\(\d{2,3}\)[ \-]?\d{6,8}|\b\d{3}[ \-]\d{3}[ \-]\d{4}\b)')
REGEX_DNI = re.compile(r'(?:DNI|C\.?I\.?|C[eé]dula|Pasaporte|Doc)[\s:]*([0-9]{7,10})', re.IGNORECASE)
REGEX_SSN = re.compile(r'\b\d{3}-\d{2}-\d{4}\b')
REGEX_IBAN = re.compile(r'\b[A-Z]{2}\d{2}[A-Z0-9]{11,30}\b')
REGEX_IP_ADDRESS = re.compile(r'\b(?:25[0-5]|2[0-4]\d|1?\d?\d)(?:\.(?:25[0-5]|2[0-4]\d|1?\d?\d)){3}\b')
REGEX_BEARER_TOKEN = re.compile(r'\bBearer\s+[A-Za-z0-9._~+/=-]{16,}\b', re.IGNORECASE)
REGEX_JWT = re.compile(r'\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b')
REGEX_NATIONAL_ID = re.compile(r'\b(?:ruc|rut|nif|nie|cpf|cuit|cedula|cédula|passport|pasaporte)\s*[:#-]?\s*[A-Z0-9.-]{7,14}\b', re.IGNORECASE)
REGEX_SENSITIVE_RECORD = re.compile(r'\b(?:historia\s+cl[ií]nica|diagn[oó]stico|resultado\s+(?:m[eé]dico|de\s+laboratorio)|patient\s+record|medical\s+record|cuenta\s+bancaria|bank\s+account)\b', re.IGNORECASE)

# Detección de Excel / Tablas corporativas / Secretos de Negocio
# Diseñado para detectar: "si le escribes al chatgpt que quieres que te ordene un excel de datos de tu empresa"
REGEX_EXCEL_PROMPT = re.compile(r'(?:orden(?:a|ar|ame)|ay[uú]dame\s+a\s+filtrar|filtr(?:a|ar|ame)|analiz(?:a|ar|ame)|proces(?:a|ar|ame)|estructur(?:a|ar|ame)|organiz(?:a|ar|ame)|revis(?:a|ar))\s+(?:este\s+|los\s+datos\s+de\s+este\s+)?(?:excel|csv|archivo|tabla|planilla|reporte|documento)(?:\s+con\s+[^\n]{0,100})?\s+(?:de\s+(?:mi\s+|nuestra\s+)?(?:empresa|compa[nñ][ií]a|negocio|banco|organizaci[oó]n)|con\s+(?:datos?\s+de\s+)?(?:clientes?|usuarios?|empleados?|proveedores?))', re.IGNORECASE)
REGEX_BUSINESS_KEYWORDS = re.compile(r'\b(?:salario|salary|sueldo|planilla|payroll|n[oó]mina|ebitda|utilidad\s+neta|net\s+income|margen|margin|m&a|adquisici[oó]n\s+confidencial|confidential\s+acquisition|nda|facturaci[oó]n\s+anual|annual\s+revenue|clientes?\s+corporativos?|corporate\s+clients?|datos?\s+de\s+clientes?|informaci[oó]n\s+de\s+clientes?|costo\s+real\s+f[aá]brica|descuento\s+secreto)\b', re.IGNORECASE)
REGEX_CONFIDENTIAL_CONTEXT = re.compile(r'\b(?:confidencial|confidential|intern[oa]|internal|no\s+publicad[oa]|unpublished|secreto|secret|empresa|company|corporativ[oa]|corporate|directorio|board)\b', re.IGNORECASE)
REGEX_ATTACHMENT = re.compile(r'\[\s*adjunto\s+detectado\s*\]', re.IGNORECASE)
REGEX_FILE_DATA_CONTEXT = re.compile(r'\b(?:excel|csv|archivo|tabla|planilla|reporte|documento|datos?)\b', re.IGNORECASE)
REGEX_ACADEMIC_TASK = re.compile(r'\b(?:tarea|trabajo\s+(?:acad[eé]mico|escolar)|ejercicio|gu[ií]a\s+de\s+estudio|ensayo|monograf[ií]a|fotos[ií]ntesis|homework|assignment|study\s+guide)\b', re.IGNORECASE)
REGEX_PUBLIC_OR_SYNTHETIC_CONTEXT = re.compile(r'\b(?:p[uú]blic[oa]s?|fictici[oa]s?|sint[eé]tic[oa]s?|datos?\s+de\s+ejemplo|sample\s+data|public\s+(?:text|data)|sin\s+datos?\s+(?:personales|privados|sensibles|reales))\b', re.IGNORECASE)

# Intent-based protection: a prompt may leak private context even where the
# sensitive values are stored in the AI account/history and are not pasted.
REGEX_PRIVATE_SOURCE = re.compile(r'\b(?:mis\s+(?:chats?|conversaciones|mensajes|historial(?:es)?|datos\s+personales)|(?:chats?|conversaciones|mensajes|historial)\s+(?:de\s+mi\s+cuenta|privad[oa]s?|personal(?:es)?)|mi\s+perfil\s+(?:digital|personal)|my\s+(?:chats?|conversations?|history|personal\s+data|profile))\b', re.IGNORECASE)
REGEX_EXTERNAL_DISCLOSURE = re.compile(r'\b(?:public(?:a|ar|arlo|arla|arlo[s]?|arla[s]?|aci[oó]n)|carpeta\s+p[uú]blica|sub(?:e|ir|elo|ela)\s+(?:a\s+)?(?:internet|la\s+web|una\s+web)|compart(?:e|ir|elo|ela)\s+(?:en|con)\s+(?:internet|el\s+p[uú]blico)|hacer(?:lo)?\s+p[uú]blic[oa]|upload\s+(?:it\s+)?(?:to\s+)?(?:the\s+)?(?:internet|web)|public\s+(?:folder|profile))\b', re.IGNORECASE)
REGEX_SENSITIVE_TARGET = re.compile(r'\b(?:datos?\s+(?:personales|privados|sensibles|confidenciales|de\s+clientes?|de\s+empleados?|de\s+usuarios?)|informaci[oó]n\s+(?:privada|personal|confidencial|interna)|credenciales?|contrase(?:ñ|n)as?|claves?\s+(?:privadas?|api)|tokens?|dni|ruc|cuentas?\s+bancarias?|tarjetas?|historial(?:es)?|chats?|mensajes?\s+privados?|base\s+de\s+datos|archivos?\s+internos?)\b', re.IGNORECASE)
REGEX_DATA_ACQUISITION = re.compile(r'\b(?:extra(?:e|er|eme|igan)|obt[eé]n|recopil(?:a|ar|ame)|recolect(?:a|ar)|dame|muestra|lista(?:me)?(?=\s+(?:los?|las?|todos?|todas?|mis?|datos?|informaci[oó]n|mensajes?|chats?))|enumera|revela|descarga|exporta|copia|saca|busca|identifica|recupera|lee)\b', re.IGNORECASE)
# Processing a private account source still discloses that source to the
# external AI, even when the user does not explicitly say "export". Include
# common conjugations, English variants and the observed "filteres" typo.
REGEX_PRIVATE_DATA_PROCESSING = re.compile(
    r'\b(?:'
    r'filtr(?:a|ar|ame|e|es|en|emos)|filteres|filter(?:s|ed|ing)?|'
    r'analiz(?:a|ar|ame|as|e|es|en)|analys(?:e|es|ed|ing)|analyz(?:e|es|ed|ing)|'
    r'proces(?:a|ar|ame|as|e|es|en)|process(?:es|ed|ing)?|'
    r'resum(?:e|ir|eme|es|an)|summari[sz](?:e|es|ed|ing)|'
    r'clasific(?:a|ar|ame|as|an)|classif(?:y|ies|ied|ying)|'
    r'perfil(?:a|ar|ame|es)|perfilar|profil(?:e|es|ed|ing)|'
    r'elabora(?:r)?\s+(?:mi|un)\s+perfil|genera(?:r)?\s+(?:mi|un)\s+perfil|'
    r'build\s+(?:my|a)\s+profile|create\s+(?:my|a)\s+profile'
    r')\b',
    re.IGNORECASE,
)
REGEX_POLICY_EVASION = re.compile(r'\b(?:evad(?:e|ir|e?lo)|elud(?:e|ir)|bypass|salt(?:a|ar)|ignor(?:a|ar)\s+(?:las?\s+)?(?:restricciones|controles|pol[ií]ticas|seguridad)|desactiv(?:a|ar)\s+(?:la\s+)?(?:seguridad|protecci[oó]n)|jailbreak|prompt\s*injection|ignore\s+(?:previous|prior|system)\s+instructions?|revela\s+(?:el\s+)?(?:prompt|instrucciones)\s+(?:del\s+)?sistema)\b', re.IGNORECASE)
REGEX_CYBERABUSE = re.compile(r'\b(?:c[oó]mo\s+(?:hackear|robar\s+datos|infectar|vulnerar)|crea(?:r)?\s+(?:un\s+)?(?:malware|ransomware|phishing|keylogger)|(?:exploit(?:ar)?|explotar)\s+(?:una\s+)?vulnerabilidad|ataque\s+(?:ddos|de\s+phishing|ransomware)|roba(?:r)?\s+(?:credenciales|contrase(?:ñ|n)as?|datos))\b', re.IGNORECASE)
REGEX_IMPERSONATION = re.compile(r'\b(?:en\s+nombre\s+del?|haci[eé]ndote\s+pasar\s+por|suplant(?:a|ar)|fing(?:e|ir)\s+ser|como\s+(?:el|la)\s+(?:director|gerente|jefe|administrador)|(?:director|gerente|jefe)\s+de\s+(?:ti|tecnolog[ií]a|seguridad|sistemas))\b', re.IGNORECASE)
REGEX_CREDENTIAL_LURE = re.compile(r'\b(?:restable(?:ce|zcan|cer)\s+(?:su\s+)?contrase(?:ñ|n)a|verifi(?:ca|quen|car)\s+(?:su\s+)?cuenta|ingresa(?:r)?\s+(?:tu|su)\s+(?:contrase(?:ñ|n)a|c[oó]digo|credenciales?)|entrega(?:r)?\s+(?:tus?|sus?)\s+(?:credenciales?|contrase(?:ñ|n)as?|c[oó]digos?))\b', re.IGNORECASE)
REGEX_DECEPTIVE_DELIVERY = re.compile(r'\b(?:enlace\s+(?:externo|urgente|de\s+verificaci[oó]n)|link\s+(?:externo|urgente)|correo\s+(?:electr[oó]nico\s+)?urgente|tono\s+(?:muy\s+)?(?:autoritario|cre[ií]ble)|urgencia\s+(?:falsa|inmediata)|debido\s+a\s+un\s+fallo\s+del\s+sistema)\b', re.IGNORECASE)

def detect_tabular_structure(text: str) -> bool:
    """Detecta si el prompt contiene filas tabulares copiadas de Excel, CSV o TSV."""
    lines = text.strip().split('\n')
    if len(lines) < 2:
        return False
    
    tsv_count = 0
    pipe_count = 0
    csv_count = 0
    
    for line in lines:
        if line.count('\t') >= 2:
            tsv_count += 1
        if line.count('|') >= 3:
            pipe_count += 1
        if line.count(',') >= 3 or line.count(';') >= 3:
            csv_count += 1
            
    return tsv_count >= 2 or pipe_count >= 2 or csv_count >= 3

class DlpEngine:
    """Motor de inferencia DLP Singleton."""
    _instance = None

    def __init__(self):
        self.model = None
        self.tokenizer = None
        self.backend = "heuristic"
        self.version = "dlp-slm-v2.0"
        self.load_model()

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = DlpEngine()
        return cls._instance

    def load_model(self):
        from api.model_bundle import restore_model
        restore_model(MODEL_DIR)
        config_path = MODEL_DIR / "config.json"
        config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
        policy_path = MODEL_DIR / 'aegis_config.json'
        policy = json.loads(policy_path.read_text(encoding='utf-8')) if policy_path.exists() else config
        self.version = f"dlp-slm-v{policy.get('version', '2.0.0')}"
        # ONNX is the production CPU path; no data leaves the host.
        onnx_path = MODEL_DIR / "model.int8.onnx" if (MODEL_DIR / "model.int8.onnx").exists() else MODEL_DIR / "model.onnx"
        if policy.get("backend") != "classical" and onnx_path.exists() and (MODEL_DIR / "tokenizer_config.json").exists():
            try:
                import onnxruntime as ort
                from transformers import AutoTokenizer
                self.tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR, local_files_only=True)
                options = ort.SessionOptions(); options.intra_op_num_threads = max(1, (os.cpu_count() or 2) // 2)
                self.model = ort.InferenceSession(str(onnx_path), sess_options=options, providers=["CPUExecutionProvider"])
                self.backend = "onnx-transformer"
                print(f"[+] ONNX SLM loaded from {MODEL_DIR}")
                return
            except Exception as exc:
                print(f"[!] ONNX load failed; trying fallback: {exc}")
        if MODEL_PATH.exists():
            try:
                self.model = joblib.load(MODEL_PATH)
                self.backend = "classical-fallback"
                print(f"[+] Modelo DLP cargado con éxito en memoria desde {MODEL_PATH}")
            except Exception as e:
                print(f"[!] Error al cargar modelo joblib: {e}")
                self.model = None
        else:
            print(f"[!] Archivo de modelo no encontrado en {MODEL_PATH}. Modo heurístico activo.")

    def redact_prompt(self, text: str) -> str:
        """Anonimiza entidades sensibles del prompt antes de persistir en auditoría."""
        redacted = text
        redacted = REGEX_OPENAI_KEY.sub("[API_KEY_REDACTED]", redacted)
        redacted = REGEX_AWS_KEY.sub("[AWS_KEY_REDACTED]", redacted)
        redacted = REGEX_PRIVATE_KEY.sub("[PRIVATE_KEY_REDACTED]", redacted)
        redacted = REGEX_CONN_STR.sub("[CONN_STR_REDACTED]", redacted)
        redacted = REGEX_GENERIC_SECRET.sub("[SECRET_REDACTED]", redacted)
        redacted = REGEX_BEARER_TOKEN.sub("[AUTH_TOKEN_REDACTED]", redacted)
        redacted = REGEX_JWT.sub("[JWT_REDACTED]", redacted)
        redacted = REGEX_CARD.sub("[CARD_REDACTED]", redacted)
        redacted = REGEX_EMAIL.sub("[EMAIL_REDACTED]", redacted)
        redacted = REGEX_DNI.sub("DNI: [REDACTED]", redacted)
        redacted = REGEX_SSN.sub("[SSN_REDACTED]", redacted)
        redacted = REGEX_IBAN.sub("[IBAN_REDACTED]", redacted)
        redacted = REGEX_NATIONAL_ID.sub("[NATIONAL_ID_REDACTED]", redacted)
        redacted = REGEX_PHONE.sub("[PHONE_REDACTED]", redacted)
        return redacted

    def storage_safe_summary(self, category: str, action: str) -> str:
        """Never persist source prompt content, including business secrets."""
        return "[SAFE_PROMPT_NOT_RETAINED]" if action == "ALLOW" else f"[BLOCKED_CONTENT_NOT_RETAINED:{category}]"

    def _predict_proba(self, prompt: str):
        if self.backend == "onnx-transformer":
            encoded = self.tokenizer(prompt, return_tensors="np", truncation=True, max_length=512)
            inputs = {name: encoded[name] for name in ("input_ids", "attention_mask") if name in encoded}
            logits = self.model.run(["logits"], inputs)[0][0]
            logits = logits - np.max(logits)
            exp = np.exp(logits)
            return exp / exp.sum()
        return self.model.predict_proba([prompt])[0]

    def evaluate(self, prompt: str) -> Dict[str, Any]:
        """
        Evalúa el prompt combinando heurísticas prioritarias y el modelo ML.
        Devuelve decisión ALLOW/BLOCK, categoría, score y desglose.
        """
        t0 = time.perf_counter()
        rules_matched = []

        if is_safe_security_request(prompt):
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "ALLOW", "risk_score": 0.01, "category": "Safe_Use",
                "reason": "Solicitud educativa o defensiva con contexto seguro explícito.",
                "matched_rules": ["POLICY: SAFE_SECURITY_GUIDANCE"],
                "inference_time_ms": round(dt, 2), "confidence": 0.99,
            }

        # Organization policy is fail-closed for the complete security and
        # unethical-intent domains. This deterministic layer precedes secrets,
        # safe academic wording and the probabilistic Transformer.
        strict_match = match_strict_intent(prompt)
        if strict_match:
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK", "risk_score": 0.99,
                "category": strict_match.category, "reason": strict_match.reason,
                "matched_rules": [strict_match.rule],
                "inference_time_ms": round(dt, 2), "confidence": 0.99,
            }
        
        # 1. Reglas de Código Propietario y Secretos Técnicos
        if REGEX_PRIVATE_KEY.search(prompt):
            rules_matched.append("HEURISTIC: PRIVATE_KEY_DETECTED")
        if REGEX_AWS_KEY.search(prompt):
            rules_matched.append("HEURISTIC: AWS_KEY_DETECTED")
        if REGEX_OPENAI_KEY.search(prompt):
            rules_matched.append("HEURISTIC: API_TOKEN_DETECTED")
        if REGEX_CONN_STR.search(prompt):
            rules_matched.append("HEURISTIC: DATABASE_CONNECTION_STRING")
        if REGEX_GENERIC_SECRET.search(prompt):
            rules_matched.append("HEURISTIC: GENERIC_SECRET")
        if REGEX_BEARER_TOKEN.search(prompt) or REGEX_JWT.search(prompt):
            rules_matched.append("HEURISTIC: AUTH_TOKEN")

        if rules_matched:
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK",
                "risk_score": 0.99,
                "category": "Proprietary_Code",
                "reason": "Intento de exfiltración de credenciales, llaves de cifrado o conexión a bases de datos internas corporativas.",
                "matched_rules": rules_matched,
                "inference_time_ms": round(dt, 2),
                "confidence": 0.99
            }

        # Intent policy runs before ML. It catches a planned extraction even if
        # the values reside in a chat, account, database or file rather than in
        # the typed prompt itself.
        has_private_source = bool(REGEX_PRIVATE_SOURCE.search(prompt))
        has_sensitive_target = bool(REGEX_SENSITIVE_TARGET.search(prompt))
        has_collection_intent = bool(REGEX_DATA_ACQUISITION.search(prompt))
        has_private_processing_intent = bool(REGEX_PRIVATE_DATA_PROCESSING.search(prompt))
        has_external_disclosure = bool(REGEX_EXTERNAL_DISCLOSURE.search(prompt))
        is_social_engineering = ((REGEX_IMPERSONATION.search(prompt) and REGEX_CREDENTIAL_LURE.search(prompt))
                                 or (REGEX_CREDENTIAL_LURE.search(prompt) and REGEX_DECEPTIVE_DELIVERY.search(prompt)))
        if is_social_engineering:
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK", "risk_score": 0.99, "category": "PII_Leak",
                "reason": "La solicitud contiene indicios de phishing: suplantación, urgencia engañosa o captura de credenciales mediante enlaces externos.",
                "matched_rules": ["HEURISTIC: SOCIAL_ENGINEERING_PHISHING_INTENT"],
                "inference_time_ms": round(dt, 2), "confidence": 0.99,
            }
        if REGEX_POLICY_EVASION.search(prompt):
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK", "risk_score": 0.99, "category": "Role_Evasion_Jailbreak",
                "reason": "La solicitud intenta anular políticas, saltar controles o revelar instrucciones internas.",
                "matched_rules": ["HEURISTIC: POLICY_EVASION_INTENT"],
                "inference_time_ms": round(dt, 2), "confidence": 0.99,
            }
        if REGEX_CYBERABUSE.search(prompt):
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK", "risk_score": 0.99, "category": "Code_Exploitation",
                "reason": "La solicitud pide explotación operativa, malware o acceso informático no autorizado.",
                "matched_rules": ["HEURISTIC: CODE_EXPLOITATION_INTENT"],
                "inference_time_ms": round(dt, 2), "confidence": 0.99,
            }
        if ((has_private_source and (has_collection_intent or has_private_processing_intent or has_external_disclosure))
                or (has_sensitive_target and (has_collection_intent or has_external_disclosure))):
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK",
                "risk_score": 0.98,
                "category": "PII_Leak",
                "reason": "El prompt solicita acceder, procesar, extraer o divulgar información privada, sensible o interna.",
                "matched_rules": ["HEURISTIC: PRIVATE_DATA_PROCESSING_OR_EXFILTRATION_INTENT"],
                "inference_time_ms": round(dt, 2),
                "confidence": 0.99,
            }

        if is_defensive_security_request(prompt):
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "ALLOW", "risk_score": 0.01, "category": "Safe_Use",
                "reason": "Orientación defensiva de ciberseguridad sin instrucciones operativas de abuso.",
                "matched_rules": ["POLICY: DEFENSIVE_SECURITY_GUIDANCE"],
                "inference_time_ms": round(dt, 2), "confidence": 0.99,
            }

        # 2. Reglas de Excel Corporativo y Secretos de Negocio
        is_tabular = detect_tabular_structure(prompt)
        has_biz_keyword = bool(REGEX_BUSINESS_KEYWORDS.search(prompt))
        has_excel_intent = bool(REGEX_EXCEL_PROMPT.search(prompt))

        has_confidential_context = bool(REGEX_CONFIDENTIAL_CONTEXT.search(prompt))
        has_attachment = bool(REGEX_ATTACHMENT.search(prompt))
        has_file_data_context = bool(REGEX_FILE_DATA_CONTEXT.search(prompt))
        if ((has_biz_keyword and (is_tabular or has_confidential_context or has_attachment))
                or has_excel_intent
                or (has_attachment and has_file_data_context)):
            if is_tabular:
                rules_matched.append("HEURISTIC: TABULAR_EXCEL_STRUCTURE")
            if has_biz_keyword:
                rules_matched.append("HEURISTIC: CONFIDENTIAL_BUSINESS_METRICS")
            if has_excel_intent:
                rules_matched.append("HEURISTIC: EXCEL_CORPORATE_PROMPT_INTENT")
            if has_attachment:
                rules_matched.append("HEURISTIC: SENSITIVE_ATTACHMENT_CONTEXT")
                
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK",
                "risk_score": 0.97,
                "category": "Business_Secrets",
                "reason": "Detección de datos tabulares de Excel corporativo / estados financieros / planillas confidenciales de la empresa prohibidas para GenAI externa.",
                "matched_rules": rules_matched,
                "inference_time_ms": round(dt, 2),
                "confidence": 0.98
            }

        # 3. Reglas Heurísticas de PII
        card_match = REGEX_CARD.search(prompt)
        email_matches = REGEX_EMAIL.findall(prompt)
        dni_match = REGEX_DNI.search(prompt)
        phone_match = REGEX_PHONE.search(prompt)
        ssn_match = REGEX_SSN.search(prompt)
        
        iban_match = REGEX_IBAN.search(prompt)
        national_id_match = REGEX_NATIONAL_ID.search(prompt)
        sensitive_record_match = REGEX_SENSITIVE_RECORD.search(prompt)
        # IPs alone can be public; block only where accompanied by an internal
        # context, credentials, or a private RFC1918 address.
        internal_ip_match = any(part.startswith(("10.", "192.168.", "172.16.", "172.17.", "172.18.", "172.19.", "172.2", "172.30.", "172.31.")) for part in REGEX_IP_ADDRESS.findall(prompt))
        if card_match or email_matches or dni_match or phone_match or ssn_match or iban_match or national_id_match or sensitive_record_match or internal_ip_match:
            if card_match:
                rules_matched.append("HEURISTIC: CREDIT_CARD_DATA")
            if email_matches:
                rules_matched.append(f"HEURISTIC: EMAIL_PII ({len(email_matches)})")
            if dni_match:
                rules_matched.append("HEURISTIC: CITIZEN_ID_DNI")
            if phone_match:
                rules_matched.append("HEURISTIC: PHONE_PII")
            if ssn_match:
                rules_matched.append("HEURISTIC: SSN_PII")
            if iban_match:
                rules_matched.append("HEURISTIC: IBAN_FINANCIAL_PII")
            if national_id_match:
                rules_matched.append("HEURISTIC: NATIONAL_ID_PII")
            if sensitive_record_match:
                rules_matched.append("HEURISTIC: HEALTH_OR_BANK_RECORD")
            if internal_ip_match:
                rules_matched.append("HEURISTIC: INTERNAL_NETWORK_ADDRESS")

            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "BLOCK",
                "risk_score": 0.94,
                "category": "PII_Leak",
                "reason": "El prompt contiene datos personales identificables (PII) que violan las normativas de protección de datos (GDPR / Ley de Protección de Datos Personales).",
                "matched_rules": rules_matched,
                "inference_time_ms": round(dt, 2),
                "confidence": 0.95
            }

        # Academic wording is only a safe signal after every explicit abuse,
        # evasion, leakage and sensitive-data rule has been evaluated.
        if ((REGEX_ACADEMIC_TASK.search(prompt) or REGEX_PUBLIC_OR_SYNTHETIC_CONTEXT.search(prompt))
                and not is_tabular and not has_biz_keyword and not has_private_source
                and not has_confidential_context and not has_attachment):
            dt = (time.perf_counter() - t0) * 1000.0
            return {
                "action": "ALLOW", "risk_score": 0.03, "category": "Safe_Use",
                "reason": None, "matched_rules": ["HEURISTIC: ACADEMIC_NON_SENSITIVE_CONTENT"],
                "inference_time_ms": round(dt, 2), "confidence": 0.97,
            }

        # 4. Inferencia con Modelo de Machine Learning (SLM)
        if self.model is not None:
            try:
                probas = self._predict_proba(prompt)
                pred_idx = int(np.argmax(probas))
                pred_class = CLASS_NAMES[pred_idx]
                confidence = float(probas[pred_idx])

                dt = (time.perf_counter() - t0) * 1000.0

                if pred_class == "Safe_Use":
                    # Riesgo bajo
                    risk_score = round(float(1.0 - confidence), 3)
                    return {
                        "action": "ALLOW",
                        "risk_score": min(risk_score, 0.15),
                        "category": "Safe_Use",
                        "reason": None,
                        "matched_rules": ["ML_MODEL: SAFE_USE_CLASSIFIED"],
                        "inference_time_ms": round(dt, 2),
                        "confidence": round(confidence, 3)
                    }
                else:
                    # Riesgo alto detectado por el modelo
                    reasons = {
                        "PII_Leak": "El modelo clasificó el prompt como fuga potencial de datos personales o clientes.",
                        "Proprietary_Code": "El modelo detectó algoritmos propietarios, secretos o código fuente no autorizado.",
                        "Business_Secrets": "El modelo detectó información estratégica o comercial confidencial de la organización.",
                        "Code_Exploitation": "El modelo detectó intención de explotación de vulnerabilidades.",
                        "Data_Exfiltration": "El modelo detectó intención de recolectar o exfiltrar información.",
                        "Social_Engineering": "El modelo detectó ingeniería social o phishing.",
                        "Role_Evasion_Jailbreak": "El modelo detectó evasión de restricciones o jailbreaking.",
                        "Legal_Misalignment": "El modelo detectó una intención de incumplimiento legal o conducta antiética."
                    }
                    return {
                        "action": "BLOCK",
                        "risk_score": round(max(confidence, 0.85), 3),
                        "category": pred_class,
                        "reason": reasons.get(pred_class, "Violación de política de gobernanza GenAI corporativa."),
                        "matched_rules": [f"ML_MODEL: {pred_class.upper()}"],
                        "inference_time_ms": round(dt, 2),
                        "confidence": round(confidence, 3)
                    }
            except Exception as e:
                print(f"[!] Error en inferencia ML: {e}")

        # Fallback de seguridad (por defecto ALLOW si no hay indicios de riesgo)
        dt = (time.perf_counter() - t0) * 1000.0
        return {
            "action": "ALLOW",
            "risk_score": 0.05,
            "category": "Safe_Use",
            "reason": None,
            "matched_rules": ["FALLBACK: DEFAULT_SAFE"],
            "inference_time_ms": round(dt, 2),
            "confidence": 0.90
        }
