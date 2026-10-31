# Aegis DLP: Local Prompt Inspection and Data Loss Prevention for Generative AI Assistants

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](https://opensource.org/licenses/MIT)
[![Python: 3.11+](https://img.shields.io/badge/Python-3.11%2B-brightgreen.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com/)
[![ONNX Runtime](https://img.shields.io/badge/Inference-ONNX%20Runtime-005CED.svg)](https://onnxruntime.ai/)
[![Chrome Extension](https://img.shields.io/badge/Extension-Manifest%20V3-yellow.svg)](https://developer.chrome.com/docs/extensions/mv3/)

**Aegis DLP** is a privacy-first, client-side data loss prevention (DLP) system engineered to mitigate shadow AI risks and prevent accidental disclosure of confidential corporate data, proprietary source code, and Personally Identifiable Information (PII) before transmission to external generative AI assistants.

The architecture combines a lightweight browser extension (Manifest V3), a deterministic rule short-circuit engine, a locally fine-tuned Small Language Model (DeBERTa-v3-small + LoRA exported to ONNX Runtime), and a zero-telemetry, privacy-preserving SQLite audit trail.

---

## Architecture Overview

```
                      [ Web Browser (Chrome / Edge) ]
                                    │
                                    ▼
                     [ Manifest V3 Content Script ]
              (Intercepts form submission / submit / Enter)
                                    │
                       HTTP POST 127.0.0.1:8000/v1/scan
                                    │
                                    ▼
                [ Aegis DLP Local Engine (FastAPI / CPU) ]
 ┌────────────────────────────────────────────────────────────────────────┐
 │ 1. Priority 1 (Hard Rules): Regex for API keys, tokens, PII credentials│
 │ 2. Priority 2 (Attack Rules): Exploits, known jailbreak signatures     │
 │ 3. Priority 3 (Semantic SLM): DeBERTa-v3-small LoRA ONNX (threshold τ) │
 └────────────────────────────────────────────────────────────────────────┘
                                    │
             ┌──────────────────────┴──────────────────────┐
             ▼                                             ▼
      Decision: ALLOW                               Decision: BLOCK
  (Event released to provider)               (Event cancelled in DOM + UI Modal)
             │                                             │
             └──────────────────────┬──────────────────────┘
                                    ▼
                   [ Local SQLite Audit (audit_logs.db) ]
        - SHA-256 Request Hash (No raw prompt persistence)
        - Action (ALLOW / BLOCK) + Classification Category
        - Timestamp + Pseudonymous Browser ID + Latency
```

---

## Key Features

1. **Structured 9-Category Policy Taxonomy:**
   * `Safe_Use`: Legitimate educational, technical, or workplace queries without sensitive data (`ALLOW`).
   * `PII_Leak`: Unstructured or structured personally identifiable information (`BLOCK`).
   * `Proprietary_Code`: Internal intellectual property, private algorithms, and API secrets (`BLOCK`).
   * `Business_Secrets`: Financial reports, confidential strategy, and internal corporate memos (`BLOCK`).
   * `Code_Exploitation`: Generation or weaponization of malware, exploits, and CVEs (`BLOCK`).
   * `Data_Exfiltration`: Commands designed to dump databases, extract environment variables, or leak data (`BLOCK`).
   * `Social_Engineering`: Phishing templates, credential harvesting, and spear-phishing lures (`BLOCK`).
   * `Role_Evasion_Jailbreak`: Role-play instructions and jailbreaks designed to bypass model guardrails (`BLOCK`).
   * `Legal_Misalignment`: Prompts violating regulatory compliance frameworks (`BLOCK`).

2. **Cross-Provider Decoupled Coverage (10 Assistants):**
   * Validated across ten commercial generative assistants: **ChatGPT**, **Claude**, **Gemini**, **Microsoft Copilot**, **Perplexity**, **DeepSeek**, **Mistral Le Chat**, **xAI Grok**, **Poe**, and **You.com**.
   * Client-side DOM interception guarantees policy uniformity regardless of provider interface.

3. **Strict Fail-Closed Security Policy (`BLOCK_ON_ERROR`):**
   * If the local backend is unreachable, the ONNX model is unavailable, communication times out (> 2,000 ms), or an invalid payload is received, the extension deterministically cancels outgoing requests in the DOM.

4. **Zero-Knowledge Local Privacy:**
   * Raw prompt text is processed exclusively in volatile memory (RAM) and never written to disk or sent to external cloud servers.
   * Local SQLite audit logs record only metadata, timestamps, predicted categories, and cryptographic SHA-256 hashes (`[REDACTED_BY_POLICY]`).

5. **Optimized CPU Execution:**
   * Sub-50 ms median response latency on standard desktop hardware (AMD Ryzen 5 5600G) using ONNX Runtime with multi-threaded intra-op parallelism.

---

## Directory Structure

```
├── api/                       # Local FastAPI backend
│   ├── config.py              # Application settings and environment config
│   ├── database.py            # SQLite database initialization and sessions
│   ├── engine.py              # DlpEngine: hybrid deterministic + ONNX pipeline
│   ├── main.py                # REST API endpoints (/v1/scan, /v1/audit, /health)
│   ├── model_bundle.py        # Model decompression and SHA-256 verification
│   ├── schemas.py             # Pydantic data validation models
│   └── strict_intent_guard.py # Rule-based heuristics and regex guards
├── dashboard/                 # Streamlit CISO governance dashboard
│   └── dashboard.py           # Real-time analytics, risk distributions, and reports
├── data/                      # Research datasets and taxonomy definitions
│   ├── cybersecurity_taxonomy.json
│   └── intent_curated_v5/     # Curated 2,743 benchmark splits (train, val, test)
├── extension/                 # Google Chrome / Microsoft Edge extension (MV3)
│   ├── background.js          # Service worker for state management
│   ├── content.js             # Content script for DOM event capture and hooking
│   ├── manifest.json          # Chrome Manifest V3 declaration
│   ├── popup.html / popup.js  # User status popup and control toggle
│   └── styles.css             # Floating notification banner styles
├── models/                    # SLM model artifacts and tokenizer
│   └── dlp_slm/
│       ├── bundle/            # Chunked model.onnx.gz archives (GitHub friendly)
│       ├── config.json        # Architecture configuration
│       └── spm.model          # SentencePiece tokenizer vocabulary
├── tests/                     # Automated pytest suite
├── training/                  # Model training and replication pipeline
│   ├── benchmark_inference.py # CPU latency and throughput benchmark
│   ├── build_corpus_v5.py     # Corpus construction and compositional expansion
│   ├── deployment_gate.py     # Automated quality verification gate
│   ├── package_model.py       # PyTorch to ONNX Opset 17 conversion pipeline
│   └── train_model.py         # DeBERTa-v3-small + LoRA fine-tuning script
├── web_dashboard/             # Standalone HTML5/JS monitoring dashboard
├── Dockerfile                 # Containerized deployment manifest
├── docker-compose.yml         # Container composition
└── requirements.txt           # Pinned production dependencies
```

---

## Installation & Setup

### Prerequisites
* Python 3.10 to 3.12 (Tested on Python 3.11.9)
* Google Chrome or Microsoft Edge (Chromium 120+)
* 8 GB RAM minimum (16 GB recommended)
* Standard x86_64 CPU (No GPU required for inference)

### 1. Environment Setup

```bash
# Clone the repository
git clone https://github.com/JDAVIDT97/Gobierno-de-IA.git
cd Gobierno-de-IA

# Create and activate virtual environment
python -m venv .venv

# On Linux/macOS:
source .venv/bin/activate
# On Windows (PowerShell):
.\.venv\Scripts\Activate.ps1

# Install pinned dependencies
pip install -r requirements.txt
cp .env.example .env
```

### 2. Model Restoration (Lossless Bundle)

The repository packages the active FP32 ONNX model in compressed chunks under `models/dlp_slm/bundle/`. Before first launch, restore and verify the model bundle:

```bash
python -m api.model_bundle
```

*This command validates SHA-256 hashes, uncompresses the chunks, and produces `models/dlp_slm/model.onnx`.*

---

## Running the Application

### 1. Start the Local Inspection Engine

```bash
python -m uvicorn api.main:app --host 127.0.0.1 --port 8000
```

* API Health Check: `http://127.0.0.1:8000/health`
* Interactive API Docs (Swagger): `http://127.0.0.1:8000/docs`

### 2. Install the Browser Extension

1. Open Google Chrome or Microsoft Edge and navigate to `chrome://extensions/`.
2. Enable **Developer mode** (toggle in top right).
3. Click **Load unpacked** and select the `extension/` directory of this repository.
4. Verify that the extension icon appears active and the status badge indicates `ON`.

### 3. Open the CISO Governance Dashboard

```bash
streamlit run dashboard/dashboard.py
```

*Or open the lightweight static dashboard at `web_dashboard/index.html`.*

---

## Experimental Replication & Benchmarking

### Running the Test Suite
```bash
pytest tests/ -v
```

### Benchmarking Latency and Throughput
To execute the multi-threaded CPU benchmark (1,000 synthetic requests across 4 workers):
```bash
python training/benchmark_inference.py
```

### Re-training the Model (Optional)
To fine-tune DeBERTa-v3-small from scratch using the curated corpus:
```bash
python training/train_model.py \
  --data-dir data/intent_curated_v5 \
  --output-dir models/intent_candidate \
  --epochs 4 \
  --batch-size 8 \
  --learning-rate 0.0002 \
  --lora-r 8 \
  --lora-alpha 16
```

---

## Ethical Disclosure & Data Integrity

All sensitive data strings (names, national identity numbers, credit card numbers, secret keys, and corporate identifiers) included in the testing splits and training corpus are **100% synthetic and fictitious**. They were programmatically generated using valid formats but nonexistent entities to comply with international data protection regulations (GDPR, ISO/IEC 42001) and institutional ethical research standards.

---

## Citation

If you use Aegis DLP in your research, please cite our paper:

```bibtex
@article{mecola2026aegis,
  title     = {Aegis DLP para inspecci{\'o}n local de solicitudes y control de divulgaci{\'o}n en asistentes generativos},
  author    = {Mecola Bernedo, Jesus Christopher and Tirado {\'A}vila, Julio David and Mendoza de los Santos, Alberto Carlos},
  journal   = {Ingenius. Revista de Ciencia y Tecnolog{\'i}a},
  year      = {2026},
  publisher = {Universidad Polit{\'e}cnica Salesiana del Ecuador}
}
```

---

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
