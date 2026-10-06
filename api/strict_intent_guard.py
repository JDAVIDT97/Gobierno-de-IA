"""Fail-closed intent guard for the organization's strict GenAI policy.

This layer is intentionally broader than the statistical classifier: security,
deception, reverse-engineering and data-abuse requests are denied before ML.
"""

from dataclasses import dataclass
from difflib import SequenceMatcher
import re
import unicodedata


@dataclass(frozen=True)
class IntentMatch:
    category: str
    rule: str
    reason: str


def normalize_intent(text: str) -> str:
    text = unicodedata.normalize("NFKD", text)
    text = "".join(ch for ch in text if not unicodedata.combining(ch)).lower()
    # Decode frequent lightweight evasions without modifying the audited input.
    text = text.translate(str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t"}))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


POLICIES = (
    (
        "Role_Evasion_Jailbreak",
        "STRICT_INTENT: POLICY_EVASION_OR_JAILBREAK",
        "La solicitud intenta evadir controles, cambiar el rol de seguridad o revelar instrucciones internas.",
        re.compile(
            r"\b(?:jailbreak|prompt injection|ignora(?:r)? (?:las )?(?:reglas|politicas|restricciones|instrucciones)|"
            r"sin restricciones|modo desarrollador|developer mode|bypass|elud(?:e|ir)|evad(?:e|ir)|"
            r"revela(?:r)? (?:el )?(?:prompt|mensaje|instrucciones) (?:del )?sistema|ignore previous instructions)\b"
        ),
    ),
    (
        "Social_Engineering",
        "STRICT_INTENT: SOCIAL_ENGINEERING_OR_PHISHING",
        "La solicitud pertenece a phishing, suplantación, engaño o ingeniería social.",
        re.compile(
            r"\b(?:phishing|phishin|pishing|pishin|fishing|fishin|ingenieria social|ingenioeria social|"
            r"spear phishing|smishing|vishing|suplant(?:a|ar|acion)|impersonat(?:e|ion)|impersonacion|"
            r"correo fraudulento|mensaje enganoso|estafa de soporte|tech support scam|"
            r"robo de identidad|robo de credenciales|captur(?:a|ar) credenciales|obtener contrasenas|"
            r"convenc(?:e|er) .{0,60}(?:credenciales|contrasena|codigo de verificacion))\b"
        ),
    ),
    (
        "Code_Exploitation",
        "STRICT_INTENT: CRITICAL_INFRASTRUCTURE_SABOTAGE",
        "La solicitud describe ciberterrorismo, sabotaje o interrupción de infraestructura crítica.",
        re.compile(
            r"\b(?:ciberterroris(?:ta|mo)|cyber ?terroris(?:t|m)|sabot(?:e|ea|ear|aje)|"
            r"(?:deshabilit(?:a|ar)|apag(?:a|ar)|interrump(?:e|ir)|manipul(?:a|ar)|compromet(?:e|er)|"
            r"tomar (?:el )?control|causar (?:una )?falla) .{0,100}"
            r"(?:infraestructura critica|planta de agua|tratamiento de agua|sistema de energia|red electrica|"
            r"central electrica|hospital|semaforos|telecomunicaciones|sistema industrial|scada|plc|ics))\b"
        ),
    ),
    (
        "Code_Exploitation",
        "STRICT_INTENT: REVERSE_ENGINEERING",
        "La política estricta bloquea solicitudes de ingeniería inversa, análisis de binarios o evasión de licencias.",
        re.compile(
            r"\b(?:ingenieria inversa|ingenioeria inversa|reverse engineering|reverse engineer|"
            r"descompil(?:a|ar)|decompil(?:e|ing)|desensambl(?:a|ar)|disassembl(?:e|ing)|"
            r"analiz(?:a|ar) (?:un )?(?:binario|firmware|malware)|crack(?:ear)? (?:una )?(?:licencia|software)|"
            r"bypass (?:de )?(?:drm|licencia)|extraer (?:el )?codigo fuente)\b"
        ),
    ),
    (
        "Code_Exploitation",
        "STRICT_INTENT: CYBERSECURITY_DOMAIN",
        "La política estricta bloquea solicitudes relacionadas con ciberseguridad, explotación o código ofensivo.",
        re.compile(
            r"\b(?:ciberseguridad|ciberseguruidad|cybersecurity|ciberterroris(?:ta|mo)|cyber ?terroris(?:t|m)|"
            r"dlp|data loss prevention|"
            r"content script interceptor|pentest(?:ing|er)?|hacking|hackear|"
            r"vulnerabilidad(?:es)?|vulnerability|exploit(?:ar|acion)?|explotar|rce|remote code execution|"
            r"inyeccion sql|sql injection|xss|cross site scripting|command injection|path traversal|"
            r"shellcode|reverse shell|payload|malware|ransomware|keylogger|botnet|rootkit|troyano|"
            r"ddos|denegacion de servicio|escalada de privilegios|privilege escalation|"
            r"movimiento lateral|credential dumping|password cracking|fuerza bruta|brute force|"
            r"backdoor|puerta trasera|zero day|dia cero|cve[- ]?\d{4})\b"
        ),
    ),
    (
        "Data_Exfiltration",
        "STRICT_INTENT: DATA_ABUSE_OR_EXFILTRATION",
        "La solicitud intenta obtener, copiar, revelar o sacar datos sin una finalidad autorizada.",
        re.compile(
            r"\b(?:exfiltr(?:a|ar|acion|ate|ation)|filtracion de datos|"
            r"filtr(?:a|ar|ado|ando) (?:(?:de )|(?:la |los |las |el ))?(?:datos|informacion|credenciales) "
            r"(?:confidencial(?:es)?|privad[oa]s?|sensibles?|intern[oa]s?|de clientes?|de usuarios?|de empleados?)|"
            r"fuga de datos|data leak|data exfiltration|"
            r"roba(?:r)? datos|steal data|dump(?:ear)? (?:de )?(?:la )?(?:base de datos|database)|"
            r"extrae(?:r)? (?:todos )?(?:los )?(?:chats|mensajes|archivos|datos) (?:privados|internos|confidenciales)|"
            r"recupera(?:r)? (?:mensajes|chats|archivos) borrados|scrap(?:e|ing) private data|"
            r"copia(?:r)? (?:datos|archivos) (?:a|hacia) (?:mi cuenta|un servidor|una nube) personal)\b"
        ),
    ),
    (
        "Legal_Misalignment",
        "STRICT_INTENT: DECEPTION_OR_UNETHICAL_CONDUCT",
        "La solicitud busca engañar, falsificar, manipular, discriminar o encubrir una conducta indebida.",
        re.compile(
            r"\b(?:falsific(?:a|ar|acion)|forg(?:e|ery)|fabricar evidencia|inventar evidencia|"
            r"oculta(?:r)? evidencia|encubrir|chantaj(?:e|ear)|blackmail|coaccion|coercion|"
            r"desinformacion|disinformation|propaganda enganosa|manipular (?:la opinion|votantes|elecciones)|"
            r"discrimin(?:a|ar|acion)|perfilamiento discriminatorio|prejuicio (?:racial|etnico|politico)|"
            r"evadir la ley|eludir la ley|fraude|soborno|bribery)\b"
        ),
    ),
)


FUZZY_ANCHORS = {
    "ciberseguridad": ("Code_Exploitation", "STRICT_INTENT: CYBERSECURITY_DOMAIN",
                       "La política estricta bloquea solicitudes relacionadas con ciberseguridad."),
    "phishing": ("Social_Engineering", "STRICT_INTENT: SOCIAL_ENGINEERING_OR_PHISHING",
                 "La solicitud pertenece a phishing o ingeniería social."),
    "ransomware": ("Code_Exploitation", "STRICT_INTENT: CYBERSECURITY_DOMAIN",
                   "La política estricta bloquea solicitudes relacionadas con código ofensivo."),
    "exfiltracion": ("Data_Exfiltration", "STRICT_INTENT: DATA_ABUSE_OR_EXFILTRATION",
                     "La solicitud intenta extraer o filtrar datos."),
}


DEFENSIVE_SECURITY_REQUEST = re.compile(
    r"\b(?:(?:controles?|medidas?|buenas practicas) (?:para|destinad[oa]s? a) )?"
    r"(?:prevenir|prevencion de|prevention of|detectar|deteccion de|reconocer|mitigar|"
    r"proteger(?:se)? (?:contra|de)|defender(?:se)? (?:contra|de)|"
    r"respuesta a|plan de respuesta a|concienciacion sobre|capacitar sobre)\b.{0,100}\b(?:"
    r"suplantacion|impersonation|robo de identidad|"
    r"filtracion(?: de datos)?|exfiltracion)\b",
    re.IGNORECASE,
)


SAFE_SECURITY_REQUEST = re.compile(
    r"(?:reconocer senales de phishing.{0,80}sin (?:crear|redactar|enviar) mensajes?"
    r"|guia publica.{0,80}proteccion contra ransomware"
    r"|corrige la ortografia.{0,80}aviso legitimo de seguridad.{0,40}sin pedir credenciales"
    r"|datos ficticios.{0,80}probar un detector de filtracion)",
    re.IGNORECASE,
)


def _near(word: str, anchor: str) -> bool:
    if len(word) < 6 or abs(len(word) - len(anchor)) > 2:
        return False
    return SequenceMatcher(None, word, anchor).ratio() >= 0.80


def match_strict_intent(text: str) -> IntentMatch | None:
    normalized = normalize_intent(text)

    if is_safe_security_request(normalized):
        return None

    # Only a precise mitigation construction is exempted. Generic words such
    # as "controles" cannot sanitize an explicit offensive verb.
    if is_defensive_security_request(normalized):
        return None

    for category, rule, reason, pattern in POLICIES:
        if pattern.search(normalized):
            return IntentMatch(category, rule, reason)

    # Small spelling errors must not bypass high-risk domain anchors.
    for token in normalized.split():
        for anchor, (category, rule, reason) in FUZZY_ANCHORS.items():
            if _near(token, anchor):
                return IntentMatch(category, rule, reason)
    return None


def is_defensive_security_request(text: str) -> bool:
    return bool(DEFENSIVE_SECURITY_REQUEST.search(normalize_intent(text)))


def is_safe_security_request(text: str) -> bool:
    return bool(SAFE_SECURITY_REQUEST.search(normalize_intent(text)))
