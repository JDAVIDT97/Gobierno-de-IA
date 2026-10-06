# Aegis DLP — gobierno local para GenAI

Aegis intercepta prompts dirigidos a ChatGPT, Claude y Gemini, clasifica el riesgo localmente, bloquea fugas y conserva una bitácora mínima sin almacenar el contenido original. Incluye dataset reproducible, DeBERTa-v3 + LoRA, ONNX, FastAPI, extensión Chrome MV3 y dashboards CISO.

## Arquitectura

`Chrome MV3 → service worker → FastAPI → motor heurístico/ONNX → SQLite → dashboards`

- Privacidad: inferencia local; el texto original nunca se guarda.
- Clases: `Safe_Use`, `PII_Leak`, `Proprietary_Code`, `Business_Secrets`.
- Seguridad: UUID v4, destinos permitidos, CORS restringido, rate limit 100/min/usuario, hash SHA-256 y constraints SQL.
- ChatGPT, Claude y Gemini retienen el envío si no pueden auditarlo; los fallos quedan registrados como `UNAUDITED` y se reflejan en el badge de estado.

## Requisitos

- Python 3.10–3.12, 16 GB RAM recomendado.
- Chrome/Chromium 120+.
- CPU x64; GPU NVIDIA opcional para acelerar entrenamiento.

## Instalación en Windows

```powershell
py -3 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
```

## Modelo incluido y entrenamiento

La descarga ZIP de GitHub y `git clone` incluyen el modelo activo **dlp-slm-v5.0,
ONNX FP32**, el tokenizador y sus informes. No se necesita Git LFS, descargar
pesos de otro servidor ni entrenar para ejecutar el software. Los pesos se
comprimen sin pérdida en `models/dlp_slm/bundle/`, en partes de hasta 40 MiB.
Al iniciar la API se reconstruye `model.onnx` y se verifica su SHA-256.
Reserve al menos 1 GB libre para el repositorio y la reconstrucción, además
del espacio de Python y sus dependencias. La primera instalación de dependencias
requiere Internet; la inferencia del modelo incluido es local.

Puede restaurar el modelo antes del primer inicio:

```powershell
python -m api.model_bundle
# O iniciar todo en Windows:
.\start.bat
```

Solo se distribuye el corpus actual `data/intent_curated_v5/`:
`train.jsonl`, `val.jsonl`, `test.jsonl`, informes y procedencia.
Se excluyen modelos candidatos, respaldos, checkpoints, corpus antiguos,
fuentes públicas originales, cuarentena, archivos auxiliares, entornos virtuales
y bases de auditoría personales. SQLite se crea automáticamente al iniciar.
El duplicado PyTorch del modelo activo se omite: ONNX contiene los pesos
necesarios para inferencia; un nuevo entrenamiento genera sus propios pesos.

**Trazabilidad:** el corpus actual contiene ampliaciones posteriores al
entrenamiento del modelo activo. Sus hashes no coinciden con los del informe
histórico `models/dlp_slm/corpus_preflight.json`; por tanto, no se afirma que
reentrenarlo reproduzca exactamente los pesos incluidos. Consulte
`DISTRIBUCION.md` para el inventario y los límites de reproducibilidad.

Para entrenar un nuevo candidato con el único corpus distribuido:

```powershell
python training/train_model.py --data-dir data/intent_curated_v5 --output-dir models/intent_candidate_v5 --epochs 4 --batch-size 8 --max-length 256
python training/validate_corpus.py --help
python training/validate_candidate.py --help
python training/promote_candidate.py --help
```

El entrenamiento transformer descarga el modelo base de Hugging Face la primera
vez. Valide el candidato antes de promoverlo; no sobrescriba el modelo activo
con un candidato sin aprobación de las pruebas. INT8 requiere validar la paridad
antes de usarlo. La distribución conserva FP32 y sus predicciones.

## Ejecución

```powershell
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

- Command Center: http://127.0.0.1:8000/
- Swagger: http://127.0.0.1:8000/docs
- Streamlit: `streamlit run dashboard/dashboard.py`
- Pruebas: `pytest`

## Extensión Chrome

1. Abra `chrome://extensions` y active **Modo desarrollador**.
2. Pulse **Cargar descomprimida**.
3. Seleccione la carpeta `extension`.
4. Mantenga la API en `127.0.0.1:8000` y pruebe en ChatGPT, Claude o Gemini.

El banner informa la inspección local. Verde `ON` significa que la última auditoría respondió; rojo `!` indica un fallo y registra únicamente metadatos `UNAUDITED` en almacenamiento local. En ChatGPT, Claude y Gemini, el mensaje se conserva sin enviar ante errores, tiempo de espera o respuestas inválidas.

### Política reforzada y actualización (1.1.0)

En `chrome://extensions`, pulse **Recargar** en **Shadow AI DLP Guard** y después recargue las pestañas de ChatGPT. La carpeta cargada debe ser `extension` de este proyecto. Los archivos modificados no se activan automáticamente en pestañas existentes.

ChatGPT, Claude, Gemini, Copilot, Perplexity, Grok, Mistral, DeepSeek, Poe y You.com usan retención *fail-closed*: Enter, clic y submit no se reanudan si la auditoría falla, expira o devuelve una respuesta inválida. Los archivos de texto, código, CSV, TSV, JSON y Markdown de hasta 512 KB se inspeccionan localmente antes de cargarse y se autorizan solo con resultado `ALLOW`; así una tarea no sensible puede continuar. PDFs, Word/Excel, ZIP, binarios, imágenes, capturas, archivos pegados y archivos arrastrados permanecen retenidos porque la extensión no puede extraer y comprobar su contenido de forma fiable antes de que el proveedor los reciba. El límite actual de auditoría es 4096 caracteres; los mensajes que lo superan se retienen con un aviso.

La cobertura de una extensión de navegador se limita a las interfaces web declaradas y no inspecciona tráfico de aplicaciones nativas, otros navegadores, API directas ni servicios GenAI aún no incluidos. Para impedir esas rutas se requiere control de red corporativo (proxy/SSE/CASB) y bloquear o inspeccionar los dominios/API de salida fuera del navegador.

Pruebas de regresión con páginas sintéticas, una extensión MV3 real y la API local encendida:

```powershell
.\.venv\Scripts\python.exe -m pytest tests/test_chatgpt_regression.py tests/test_extension.py tests/test_api.py -q
```

Estas pruebas no envían mensajes a los proveedores reales. Cubren bloqueo, permiso, errores de conexión y conservación del comportamiento de Claude/Gemini. Los cambios futuros de interfaz de los proveedores requieren volver a validar la extensión.

## Docker

```powershell
docker compose up --build
```

Para escalar horizontalmente, sustituya el rate limiter en memoria y SQLite por Redis y PostgreSQL, use HTTPS, autenticación OAuth2/JWT, gestión centralizada de políticas y workers separados. La extensión debe apuntar al dominio corporativo HTTPS.

## Seguridad y límites

Este es software defensivo de investigación. Antes de producción requiere pentest, revisión OWASP ASVS, firma/publicación administrada de la extensión, retención configurable, RBAC, SIEM y evaluación legal local. Las métricas sintéticas no sustituyen una validación externa. Deben reportarse por idioma (español/inglés) y por lenguaje de código (Python/Java) para vigilar sesgo y deriva.

No use secretos ni PII reales durante pruebas. Las fuentes públicas se consumen por streaming y se pseudonimizan antes de persistir.
