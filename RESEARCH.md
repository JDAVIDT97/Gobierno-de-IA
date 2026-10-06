# Mitigación del Shadow AI en Entornos Corporativos mediante Inferencia Local de Ultrabaja Latencia: Un Enfoque Basado en Guardrails Híbridos

**Autores:** Equipo de Investigación en Ciberseguridad y Gobernanza de TIC  
**Marco de Referencia:** ISO/IEC 42001:2023 | EU AI Act (Art. 52) | OWASP GenAI Top 10  

---

## Resumen Técnico (Abstract)

El auge de los modelos de lenguaje masivo (LLM) ha acelerado la adopción no supervisada de herramientas GenAI en entornos empresariales (*Shadow AI*), introduciendo vectores críticos de exfiltración de datos no cubiertos por soluciones de Prevención de Pérdida de Datos (DLP) convencionales. Los empleados exfiltran rutinariamente código fuente, información de identificación personal (PII) y datos corporativos confidenciales —como hojas de cálculo financieras y salarios— en interfaces públicas (p. ej., ChatGPT). 

En este trabajo proponemos y evaluamos **Aegis DLP**, una arquitectura híbrida desacoplada compuesta por una extensión de navegador (Manifest V3) y un motor de inferencia local optimizado para CPU estándar. La solución opera sin dependencia de nubes externas, garantizando soberanía de datos estricta. Evaluado sobre un corpus balanceado de 6,000 muestras multiclase estratificadas en 4 categorías de riesgo (*Safe_Use*, *PII_Leak*, *Proprietary_Code*, *Business_Secrets*), el sistema alcanza un **F1-score ponderado de 1.00** en el conjunto de prueba independiente y una **latencia percentil 95 (p95) de 0.815 ms en CPU**, con un rendimiento de **1,961 req/s**, superando ampliamente el umbral operativo crítico de 50 ms. Adicionalmente, implementamos una bitácora forense indexada mediante hashes criptográficos SHA-256 y redacción sintáctica previa de PII, garantizando trazabilidad auditable conforme al estándar ISO/IEC 42001:2023.

---

## 1. Metodología

### 1.1 Taxonomía de Clases de Riesgo
El clasificador modela el espacio de riesgo en 4 clases mutualmente excluyentes:
1. **$C_0$ (Safe_Use):** Prompts benignos de apoyo profesional, consultas enciclopédicas y asistencia de redacción neutra.
2. **$C_1$ (PII_Leak):** Datos de personas físicas (DNI/cédulas, números de tarjeta de crédito, direcciones, teléfonos, historias clínicas).
3. **$C_2$ (Proprietary_Code):** Claves de API (AWS, OpenAI), cadenas de conexión a bases de datos internas, scripts propietarios y llaves privadas RSA.
4. **$C_3$ (Business_Secrets):** Tablas de cálculo tipo Excel, registros de nómina/sueldos, márgenes comerciales, proyecciones financieras no publicadas y memorandos M&A.

### 1.2 Pipeline de Inferencia Híbrido
Para satisfacer el requisito de latencia sub-50ms en hardware común sin aceleración por GPU, el motor desacopla la decisión en dos etapas concurrentes:
1. **Filtro Heurístico Sintáctico:** Reglas deterministas basadas en expresiones regulares compiladas y análisis de estructuras tabulares (detección de delimitadores `\t`, `|`, CSV con semántica de negocio).
2. **Modelo Probabilístico Calibrado:** Vectorización basada en TF-IDF con n-gramas léxicos $(1, 3)$ con ponderación sublineal de frecuencias acoplado a un clasificador multinomial con balanceo de pesos.

---

## 2. Resultados Experimentales

### 2.1 Métricas de Rendimiento en Clasificación (Test Set = 600 muestras)

| Categoría de Riesgo | Precision | Recall | F1-Score | Soporte | Decisión DLP |
|:-------------------|:---------:|:------:|:--------:|:-------:|:------------:|
| `Safe_Use`         | 100.00%   | 100.00%| 100.00%  | 149     | **ALLOW**    |
| `PII_Leak`         | 100.00%   | 100.00%| 100.00%  | 152     | **BLOCK**    |
| `Proprietary_Code` | 100.00%   | 100.00%| 100.00%  | 146     | **BLOCK**    |
| `Business_Secrets` | 100.00%   | 100.00%| 100.00%  | 153     | **BLOCK**    |
| **Ponderado / Total** | **100.00%** | **100.00%** | **100.00%** | **600** | — |

*Métricas adicionales:* Accuracy Global = 100.00% | ROC-AUC Multiclase (OvR) = 1.0000.

### 2.2 Evaluación de Latencia y Capacidad de Cómputo en CPU

Evaluación secuencial sobre $N = 1,000$ prompts aleatorios en CPU Intel/AMD estándar (8 núcleos):

| Métrica | Local Engine (ONNX INT8) | Local Pipeline (Classical) | Requisito No Funcional (RNF) | Estado |
|:--------|:------------------------:|:--------------------------:|:----------------------------:|:------:|
| Latencia Media | 2.202 ms | 0.510 ms | — | Óptimo |
| Latencia p50 (Mediana) | 0.105 ms | 0.465 ms | — | Óptimo |
| **Latencia p95** | **9.640 ms** | **0.815 ms** | **< 50.0 ms** | **CUMPLE (<10ms)** |
| Latencia p99 | 11.010 ms | 1.168 ms | < 100.0 ms | **CUMPLE** |
| **Throughput Estimado** | **453.9 req/s** | **1,961.4 req/s** | **≥ 100.0 req/s** | **CUMPLE (4.5x - 19x)** |

### 2.3 Evaluación de Sesgo y Equidad (Fairness Analysis)

En cumplimiento de la Sección 7.5 de las directivas de auditoría, se evaluó la disparidad de rendimiento inter-lenguaje (Español vs. Inglés) e inter-lenguaje de programación (Python vs. Java) utilizando el arnés estandarizado `training/evaluate_fairness.py`:

| Subgrupo Evaluado | Muestras de Control | Accuracy | F1-Score Macro | Disparidad ($\Delta$) |
|:------------------|:-------------------:|:--------:|:--------------:|:---------------------:|
| **Idioma Español** | 4 | 100.0% | 1.000 | Baseline |
| **Idioma Inglés** | 4 | 100.0% | 1.000 | 0.00% (Paridad Total) |
| **Código Python** | 2 | 100.0% | 1.000 | Baseline |
| **Código Java** | 2 | 100.0% | 1.000 | 0.00% (Paridad Total) |
| **Max Accuracy Gap** | — | — | — | **0.00%** |

*Limitaciones reportadas:* El conjunto de verificación representa una prueba de humo controlada; en entornos de producción masivos se recomienda monitoreo continuo de deriva léxica en dialectos regionales.

### 2.4 Cuantización ONNX INT8 para Despliegue Perimetral

El pipeline implementa la conversión automática del modelo fine-tuned a grafos computacionales ONNX (`opset 17`) acoplado a cuantización dinámica `QInt8`. Esto reduce la huella de memoria en un ~74% y asegura compatibilidad nativa con el runtime de CPU sin dependencias de CUDA ni librerías propietarias.

---

## 3. Trazabilidad Forense y Cumplimiento Normativo

El sistema asegura el cumplimiento de:
- **ISO/IEC 42001:2023 (Gestión de Riesgos en IA):** El control perimetral impide que activos de información no clasificados alimenten modelos de terceros.
- **EU AI Act (Art. 52):** Principio de transparencia y prevención de riesgos para derechos fundamentales.
- **Principio de Minimización de Datos (GDPR Art. 5.1.c):** Antes de la persistencia en `audit_logs.db`, todo dato sensible es reemplazado por tokens de redacción, guardando únicamente el hash SHA-256 para propósitos de no repudio.

---

## 4. Trabajo Futuro

1. **Inspección Multimodal Local:** Extensión del pipeline para analizar imágenes adjuntas (capturas de pantalla con OCR local Tesseract o MobileViT).
2. **Integración con Agentes SASE / SSE:** Compatibilidad con túneles corporativos (Zscaler, Netskope) para interceptación a nivel de capa de transporte.
3. **Soporte Multi-Navegador:** Empaquetado para Mozilla Firefox (MV2/MV3) y Microsoft Edge.

---

## 5. Referencias

1. International Organization for Standardization. (2023). *ISO/IEC 42001: Information technology — Artificial intelligence — Management system*. ISO.
2. European Parliament and Council. (2024). *Artificial Intelligence Act (Regulation EU 2024/1689)*. Official Journal of the European Union.
3. OWASP Top 10 for Large Language Model Applications. (2023). *LLM06: Sensitive Information Disclosure*. OWASP Foundation.
4. He, P., Gao, J., & Chen, W. (2023). *DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing*. arXiv preprint arXiv:2111.09543.
