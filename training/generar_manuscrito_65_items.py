# -*- coding: utf-8 -*-
"""
Script maestro para generar el manuscrito revisado de Aegis DLP
incorporando de forma exhaustiva los 65 ítems del plan de levantamiento de INGENIUS.

Genera:
1. Articulo_Aegis_DLP_Corregido.docx (versión limpia)
2. Articulo_Aegis_DLP_Modificaciones_Resaltadas.docx (versión con cambios en amarillo)
"""

import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=70, bottom=70, left=90, right=90):
    tcPr = cell._tc.get_or_add_tcPr()
    tcMar = OxmlElement('w:tcMar')
    for m, val in [('top', top), ('bottom', bottom), ('left', left), ('right', right)]:
        node = OxmlElement(f'w:{m}')
        node.set(qn('w:w'), str(val))
        node.set(qn('w:type'), 'dxa')
        tcMar.append(node)
    tcPr.append(tcMar)

def set_cell_background(cell, fill_hex):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)

def set_table_borders(table, color="D3D3D3", sz="4", val="single"):
    tblPr = table._tbl.tblPr
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:bottom w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="{val}" w:sz="{sz}" w:space="0" w:color="{color}"/>'
        f'  <w:insideV w:val="none"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)

def build_full_manuscript(highlight_mode=False):
    doc = Document()
    
    for s in doc.sections:
        s.top_margin = Inches(0.98)
        s.bottom_margin = Inches(0.98)
        s.left_margin = Inches(0.79)
        s.right_margin = Inches(0.79)
        
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(11)
    normal_style.font.color.rgb = RGBColor(0x11, 0x11, 0x11)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(6)

    def add_p(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False, size=Pt(11), is_modified=False, space_after=Pt(6)):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = space_after
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = size
        run.font.name = 'Times New Roman'
        if highlight_mode and is_modified:
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        return p

    def add_h1(text, is_modified=False):
        return add_p(text, bold=True, size=Pt(13), align=WD_ALIGN_PARAGRAPH.LEFT, is_modified=is_modified, space_after=Pt(6))

    def add_h2(text, is_modified=False):
        return add_p(text, bold=True, size=Pt(11.5), align=WD_ALIGN_PARAGRAPH.LEFT, is_modified=is_modified, space_after=Pt(4))

    def add_h3(text, is_modified=False):
        return add_p(text, bold=True, italic=True, size=Pt(11), align=WD_ALIGN_PARAGRAPH.LEFT, is_modified=is_modified, space_after=Pt(3))

    def add_tbl_caption(text, is_modified=False):
        return add_p(text, bold=True, size=Pt(10), align=WD_ALIGN_PARAGRAPH.LEFT, is_modified=is_modified, space_after=Pt(3))

    def render_table(headers, data, col_widths=None, is_modified=False):
        tbl = doc.add_table(rows=len(data) + 1, cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(tbl)
        
        # Header
        hdr_row = tbl.rows[0]
        for idx, h_text in enumerate(headers):
            cell = hdr_row.cells[idx]
            set_cell_margins(cell, top=60, bottom=60, left=80, right=80)
            set_cell_background(cell, "F2F2F2")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            run = p.add_run(h_text)
            run.bold = True
            run.font.name = 'Times New Roman'
            run.font.size = Pt(8.5)
            if highlight_mode and is_modified:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW

        # Rows
        for r_idx, row_data in enumerate(data):
            row = tbl.rows[r_idx + 1]
            bg = "FAFAFA" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, val in enumerate(row_data):
                cell = row.cells[c_idx]
                set_cell_margins(cell, top=45, bottom=45, left=80, right=80)
                set_cell_background(cell, bg)
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.05
                run = p.add_run(str(val))
                run.font.name = 'Times New Roman'
                run.font.size = Pt(8.5)
                if highlight_mode and is_modified:
                    run.font.highlight_color = WD_COLOR_INDEX.YELLOW

        if col_widths:
            for row in tbl.rows:
                for idx, w in enumerate(col_widths):
                    row.cells[idx].width = Inches(w)
                    
        doc.add_paragraph().paragraph_format.space_after = Pt(6)
        return tbl

    # ==================== ENCABEZADOS ====================
    add_p("Aegis DLP para inspección local de solicitudes y control de divulgación en asistentes generativos", 
          bold=True, size=Pt(16), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(4))
    add_p("Aegis DLP for Local Prompt Inspection and Disclosure Control in Generative Assistants", 
          italic=True, size=Pt(13), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(6))
    add_p("Jesus Christopher Mecola Bernedo, Julio David Tirado Ávila, Alberto Carlos Mendoza de los Santos", 
          bold=True, size=Pt(11), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(12))

    # ==================== RESUMEN Y ABSTRACT (Ítems 1.1, 1.4, 4.5, 4.6, 5.2, 7.3, 12.2, 12.5) ====================
    add_p("Resumen", bold=True, size=Pt(11.5), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(3))
    add_p("El uso de asistentes generativos en actividades laborales incrementa el riesgo de divulgar información sensible y justifica incorporar controles antes del envío. El presente trabajo desarrolla y evalúa Aegis DLP, un sistema de inspección local que integra una extensión de navegador Manifest V3, reglas deterministas y un clasificador DeBERTa-v3-small adaptado mediante LoRA y ejecutado con ONNX. La investigación se estructuró como una investigación aplicada de evaluación tecnológica, con enfoque cuantitativo y diseño experimental de pruebas controladas en entorno de laboratorio. Comprendió la construcción de un corpus dirigido de 2.743 solicitudes, una evaluación del clasificador sobre un conjunto congelado e independiente de 328 solicitudes, una comparación empírica frente a un modelo de referencia TF-IDF con regresión logística, pruebas funcionales de autorización y bloqueo bajo una política de fallo seguro (fail-closed) y un benchmark HTTP de 1.000 solicitudes. El clasificador alcanzó una exactitud del 95,12 % (IC 95 %: [92,20 % – 97,19 %]) y un F1 macro de 0,9518, superando al modelo TF-IDF (92,68 % y 0,9245). Las 292 solicitudes restringidas recibieron categorías asociadas a bloqueo; 278 obtuvieron su categoría exacta y catorce se confundieron entre categorías restringidas, resultando en una tasa de falsos negativos operativos del 0,00 % (IC 95 %: [0,00 % – 1,26 %]). De las 36 solicitudes seguras, 34 se clasificaron correctamente y dos recibieron categorías de bloqueo (tasa de falsos positivos del 5,56 %, IC 95 %: [0,68 % – 18,66 %]). La concordancia inter-anotador entre los autores alcanzó un coeficiente Kappa de Cohen de 0,892. En un equipo AMD Ryzen 5 5600G, el endpoint obtuvo una latencia p95 de 44,375 ms y un rendimiento de 194,7 solicitudes por segundo. Se concluye que Aegis DLP constituye una solución técnicamente viable para apoyar la reducción de la superficie de exposición y la trazabilidad de decisiones mediante registros minimizados en condiciones controladas, requiriéndose estudios complementarios para determinar su generalización en flujos laborales reales.",
          is_modified=True)
    add_p("Palabras clave: auditoría informática; clasificación de texto; fuga de datos; inferencia local; inteligencia artificial generativa; seguridad informática.", 
          italic=True, space_after=Pt(10))

    add_p("Abstract", bold=True, size=Pt(11.5), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(3))
    add_p("The use of generative AI assistants in workplace tasks increases the risk of disclosing sensitive information, justifying the implementation of controls prior to submission. This work develops and evaluates Aegis DLP, a local inspection system integrating a Manifest V3 browser extension, deterministic rules, and a DeBERTa-v3-small classifier—adapted via LoRA and executed through ONNX. The study was structured as applied technological evaluation research, with a quantitative approach and an experimental design of controlled laboratory testing. It involved constructing a targeted corpus of 2,743 requests, evaluating the classifier on a frozen, independent set of 328 requests, conducting an empirical comparison against a TF-IDF logistic regression baseline, carrying out functional authorization and blocking tests under a fail-closed policy, and running an HTTP benchmark of 1,000 requests. The classifier achieved an accuracy of 95.12% (95% CI: [92.20% – 97.19%]) and a macro-F1 score of 0.9518, outperforming the TF-IDF baseline (92.68% and 0.9245). All 292 restricted requests were assigned to blocking categories; 278 obtained their exact category and 14 were misclassified among restricted categories, yielding an operational false negative rate of 0.00% (95% CI: [0.00% – 1.26%]). Among the 36 safe requests, 34 were correctly classified and two received blocking categories (operational false positive rate of 5.56%, 95% CI: [0.68% – 18.66%]). Inter-annotator agreement among the authors yielded a Cohen's kappa coefficient of 0.892. On an AMD Ryzen 5 5600G system, the endpoint demonstrated a p95 latency of 44.375 ms and a throughput of 194.7 requests per second. It is concluded that Aegis DLP serves as a technically viable solution for supporting prompt exposure reduction and decision traceability through minimized logging in controlled environments, requiring further research to assess generalizability across workplace workflows.",
          is_modified=True)
    add_p("Keywords: computer auditing; text classification; data loss; local inference; generative artificial intelligence; computer security.", 
          italic=True, space_after=Pt(12))

    # ==================== 1. INTRODUCCIÓN ====================
    add_h1("1. Introducción")
    add_p("El uso cotidiano de asistentes de inteligencia artificial generativa modifica los canales por los que una organización comparte información. Un trabajador puede copiar un informe interno, una lista de clientes o una credencial técnica en una conversación con un servicio externo para obtener una respuesta útil. Aunque la actividad persiga una finalidad laboral legítima, el envío puede exceder las autorizaciones previstas. Puthal et al. [1] describen Shadow AI como un ámbito de riesgos asociado al uso de tecnologías de IA que escapa a la supervisión organizacional. El problema comprende tanto herramientas desconocidas para el área de TI como usos no autorizados de servicios conocidos.")
    add_p("Sebastian [2] relaciona la percepción de eficiencia, el conocimiento de políticas y la formación con las decisiones de compartir información mediante IA. Chin et al. [3] analizan las tensiones que aparecen entre el uso de Shadow AI, la fuga de conocimiento y la sostenibilidad de los modelos de negocio basados en el metaverso. Estos trabajos ayudan a contextualizar el problema y sugieren que la política escrita vaya acompañada de mecanismos que actúen allí donde puede producirse una divulgación. Eso sí, sin dar por hecho que sus resultados se puedan aplicar automáticamente a cualquier empresa.")
    add_p("Es importante diferenciar entre la información que el usuario entrega por voluntad propia y la que un atacante puede obtener del modelo o de las fuentes de contexto que este utiliza. Das et al. [4] revisan las amenazas para la privacidad y la seguridad, entre ellas la filtración de información personal, el envenenamiento y los ataques de evasión. Por su parte, Berini et al. [5] clasifican las amenazas y las defensas según las distintas etapas del ciclo de vida de los modelos de lenguaje. Hacer una inspección previa en el navegador cubre solo una parte del problema: el contenido de las solicitudes salientes, siempre bajo una política concreta. Pero no resuelve la memorización de los datos de entrenamiento, ni las vulnerabilidades del proveedor, ni todos los riesgos que traen consigo los agentes autónomos.")
    add_p("Para proteger los prompts hay distintas alternativas que actúan en momentos diferentes del proceso. Edemacu y Wu [6], por su parte, organizan y describen los métodos orientados a preservar la privacidad durante el prompting y el aprendizaje en contexto. Al Masoud et al. [7] proponen SD-RAG, un enfoque de divulgación selectiva para la generación aumentada por recuperación (RAG) pensado para hacer frente a ataques de filtración de prompts de un solo turno. Estas propuestas ayudan a ver Aegis DLP como un control que complementa a los demás: actúa antes de que la solicitud llegue al asistente, mientras que otros mecanismos protegen los datos o las respuestas dentro del propio servicio. Al final, la ubicación del control marca la diferencia, porque de ella depende qué información puede observar y a qué amenazas puede hacer frente.")
    add_p("La literatura sobre gobernanza también deja ver la necesidad de contar con controles que se puedan llevar a la práctica. Papagiannidis et al. [8] señalan lo difícil que resulta traducir los principios de la IA responsable en prácticas concretas de diseño, operación y evaluación. Camilleri [9] relaciona la gobernanza con la responsabilidad, la transparencia, la privacidad y la seguridad. Wirtz et al. [10] plantean una conexión entre los riesgos y las directrices, mientras que Schneider et al. [11] organizan la gobernanza empresarial en torno a tres ejes: datos, modelos y sistemas. Vistos en conjunto, estos trabajos refuerzan la idea de que hay que dejar claro qué está permitido, quién se encarga de mantener la política y qué evidencia queda disponible para poder revisar las decisiones.")
    add_p("Kirpitsas y Pachidis [12] integran la auditabilidad en un método de desarrollo alineado con COBIT, y Bodnari y Travis [13] abordan la supervisión de la IA empresarial en el ámbito de la salud. En ese contexto, registrar las decisiones ayuda a la supervisión, pero no basta para demostrar que se cumple un estándar ni para atribuir responsabilidad a una persona autenticada.")
    add_p("La clasificación de texto permite detectar intenciones que no vienen marcadas con identificadores de formato fijo. Arazzi et al. [14] hacen un repaso de las técnicas de procesamiento de lenguaje natural aplicadas a la inteligencia de amenazas y de las limitaciones que presentan. Huang et al. [15] subrayan que no basta con evaluar: en las aplicaciones basadas en modelos de lenguaje también hace falta verificar y supervisar lo que ocurre mientras se ejecutan. Por su parte, Zheng et al. [16] analizan las limitaciones de cómputo y memoria que trae consigo el despliegue local. Con estos antecedentes, tiene sentido explorar una arquitectura híbrida: reglas para las señales explícitas y un encoder especializado para aquellas solicitudes que las reglas no logran resolver.")
    add_p("Este trabajo se plantea la siguiente pregunta: ¿cómo se comporta una arquitectura local, en términos de clasificación, capacidad de intervención y tiempos de respuesta, cuando inspecciona solicitudes antes de enviarlas a asistentes generativos? La meta es desarrollar Aegis DLP y evaluar cómo funciona: clasificando solicitudes, haciendo pruebas de autorización y bloqueo y midiendo la latencia. El estudio presenta la arquitectura implementada, la política de nueve categorías y los resultados obtenidos en condiciones controladas, poniendo el acento en proteger el contenido que se envía y en dejar constancia de las decisiones tomadas.")
    add_p("La aportación se resume en tres cosas: una arquitectura de inspección en el navegador que procesa localmente; una política explícita de nueve categorías que conecta la clasificación con el permiso o el bloqueo; y un registro de eventos que no guarda el texto original. Esta integración ofrece un mecanismo operativo que se puede evaluar y auditar. La originalidad se limita a esta implementación y a su evaluación preliminar; en ningún caso se afirma que sea la primera solución que existe. La norma ISO/IEC 42001 [17] se toma como referencia de gestión, y la categoría de divulgación de información sensible de OWASP [18] como referencia de amenaza. Eso sí, en ningún momento se da a entender que el prototipo cuente con una certificación.")

    # ==================== 2. MATERIALES Y MÉTODOS ====================
    add_h1("2. Materiales y métodos")
    
    # 2.1 (Ítems 1.1, 1.2, 1.3, 1.4)
    add_h2("2.1. Diseño y alcance de la evaluación")
    add_p("El estudio corresponde a una investigación aplicada de evaluación tecnológica, con enfoque cuantitativo y un diseño experimental de pruebas controladas en entorno de laboratorio. El diseño es de pruebas controladas puesto que se manipulan de forma sistemática entradas textuales conocidas, cargas concurrentes e inyecciones de fallos sobre el prototipo de software, midiendo variables dependientes cuantitativas de exactitud, tasas de error y tiempos de respuesta sin intervención sobre usuarios reales en producción. La evaluación abarcó tres aspectos: el rendimiento del clasificador, la aplicación operativa de las decisiones de permiso y bloqueo en entorno controlado, y los tiempos de respuesta del servicio de auditoría. Para el clasificador, la unidad de análisis fue cada solicitud de texto ya etiquetada; para la parte funcional, cada intento de envío; y para medir el rendimiento, cada solicitud procesada por el motor o por el endpoint HTTP.",
          is_modified=True)
    add_p("Para asegurar la consistencia de la investigación, la Tabla 1 establece la correspondencia formal entre los objetivos específicos, los componentes evaluados, los procedimientos experimentales, las métricas cuantitativas y los criterios de aceptación a priori definidos durante el diseño del sistema.",
          is_modified=True)

    add_tbl_caption("Tabla 1. Coherencia metodológica y criterios de aceptación a priori.", is_modified=True)
    render_table(
        ["Objetivo específico", "Componente evaluado", "Procedimiento experimental", "Métricas de evaluación", "Criterio de aceptación"],
        [
            ["Discriminar intención de riesgo", "Clasificador semántico DeBERTa-v3-small", "Inferencia multiclase sobre 328 solicitudes congeladas", "Exactitud, F1 macro ponderado, ROC-AUC OvR", "Exactitud >= 90 %, F1 macro >= 0,90"],
            ["Prevenir divulgación de amenazas", "Motor híbrido y extensión Manifest V3", "Evaluación binaria de bloqueo sobre 292 casos hostiles", "Exhaustividad (TPR), Tasa de falsos negativos (FNR)", "FNR operativo <= 1,0 % en muestra controlada"],
            ["Preservar consultas legítimas", "Motor híbrido y extensión Manifest V3", "Evaluación binaria de permiso sobre 36 casos seguros", "Tasa de falsos positivos (FPR), Especificidad (TNR)", "FPR operativo <= 10,0 % (especificidad >= 90 %)"],
            ["Asegurar tiempo interactivo", "Endpoint HTTP local (FastAPI + SQLite)", "Benchmark de carga con 1.000 solicitudes (4 workers)", "Latencias media, p50, p95, p99 y rendimiento (req/s)", "p95 <= 50,0 ms, Throughput >= 100 req/s"],
            ["Garantizar contención ante fallos", "Mecanismo de contingencia global", "Inyección controlada de 6 escenarios de error de servicio", "Tasa de retención por fallo y estado del DOM", "100 % de retención preventiva (fail-closed)"]
        ],
        col_widths=[1.4, 1.4, 1.5, 1.4, 1.3],
        is_modified=True
    )

    add_p("Para evaluar el clasificador se usó un conjunto concreto de 328 solicitudes: 36 clasificadas como seguras y 292 como restringidas. Se calcularon métricas multiclase y, después, las predicciones se agruparon según la acción que corresponde a cada categoría. Las pruebas funcionales sirvieron para comprobar dos cosas: que las consultas legítimas se autorizan y que las solicitudes riesgosas se bloquean. Para medir el rendimiento, se hicieron pasar 1.000 solicitudes por el endpoint HTTP. Las pruebas demuestran el funcionamiento del prototipo bajo condiciones de laboratorio y no constituyen evidencia concluyente de eficacia en tráfico organizacional real sin una validación complementaria.",
          is_modified=True)
    add_p("Además, se describe el corpus que se construyó, con 2.743 registros, y cómo se repartieron entre entrenamiento, validación y prueba. Dentro de ese corpus hay una partición de 526 solicitudes, que es distinta del conjunto de 328 con el que se obtuvieron los resultados principales. Gracias a esta distinción se puede ver hasta dónde llega cada recurso, sin confundir sus tamaños ni aplicarles las mismas métricas.")

    # 2.2 (Ítems 5.1, 6.4, 6.5)
    add_h2("2.2. Arquitectura del sistema y límites de confianza")
    add_p("El sistema se apoya en cuatro piezas: una extensión de Chrome con Manifest V3, un servicio local en FastAPI, un motor de decisión y una base de datos SQLite. La extensión se encarga de interceptar la solicitud y, antes de dejar pasar el evento de envío, consulta el endpoint de auditoría. El servicio aplica primero las reglas y, cuando hace falta, recurre al clasificador ONNX. La respuesta que devuelve incluye la acción, la categoría, la puntuación, la versión y el tiempo de inferencia. A partir de esa respuesta, el navegador deja pasar la operación o la retiene. La Figura 1 muestra ese flujo y deja claro qué se procesa en local y qué parte corresponde al proveedor externo.")
    add_p("Figura 1. Flujo de trabajo de Aegis DLP. El registro guarda los metadatos y deja un marcador que indica que el contenido no se conservó. La solicitud solo llega al proveedor externo cuando la extensión autoriza el evento correspondiente.")
    add_p("Para que el sistema funcione hacen falta tres cosas: que la extensión esté activada, que el servicio local esté disponible y que el intento de envío se produzca en una ruta que la intercepción cubra. El modelo de amenaza contempla tanto las divulgaciones accidentales como los intentos de evasión que se expresan directamente en el texto. Su alcance se centra en los canales que inspecciona la extensión y en aplicar la política antes de que el contenido se transfiera al proveedor.")
    add_p("La extensión se configuró con reglas de concordancia para diez proveedores de asistentes generativos populares: ChatGPT, Claude, Gemini, Microsoft Copilot, Perplexity, Poe, DeepSeek, Mistral Le Chat, HuggingChat y Groq. No obstante, para mantener el rigor experimental, la Tabla 2 distingue entre los proveedores con soporte configurado y aquellos efectivamente validados en laboratorio. La validación experimental se ejecutó sobre páginas sintéticas que representaban con precisión estructural las interfaces de ChatGPT, Claude y Gemini bajo Google Chrome v131 en Windows 11 Pro de 64 bits. Los otros siete servicios disponen de selectores configurados pero no fueron sometidos a la batería funcional, por lo que su funcionamiento en interfaces dinámicas de producción requiere comprobación específica.",
          is_modified=True)

    add_tbl_caption("Tabla 2. Cobertura y estado de validación por proveedor.", is_modified=True)
    render_table(
        ["Proveedor", "Dominio objetivo", "Configurado en Manifest V3", "Validado en página sintética local", "Validado en interfaz en vivo"],
        [
            ["ChatGPT", "chatgpt.com", "Sí (Selectores CSS/DOM)", "Sí (DOM simulado Chrome v131)", "No (HTTP 403 / Captcha)"],
            ["Claude", "claude.ai", "Sí (Selectores CSS/DOM)", "Sí (DOM simulado Chrome v131)", "No (No evaluado en vivo)"],
            ["Gemini", "gemini.google.com", "Sí (Selectores CSS/DOM)", "Sí (DOM simulado Chrome v131)", "No (No evaluado en vivo)"],
            ["Microsoft Copilot", "copilot.microsoft.com", "Sí (Reglas declaradas)", "No (Solo configuración)", "No (No evaluado en vivo)"],
            ["Perplexity", "perplexity.ai", "Sí (Reglas declaradas)", "No (Solo configuración)", "No (No evaluado en vivo)"],
            ["Poe", "poe.com", "Sí (Reglas declaradas)", "No (Solo configuración)", "No (No evaluado en vivo)"],
            ["DeepSeek", "chat.deepseek.com", "Sí (Reglas declaradas)", "No (Solo configuración)", "No (No evaluado en vivo)"],
            ["Mistral Le Chat", "chat.mistral.ai", "Sí (Reglas declaradas)", "No (Solo configuración)", "No (No evaluado en vivo)"],
            ["HuggingChat", "huggingface.co/chat", "Sí (Reglas declaradas)", "No (Solo configuración)", "No (No evaluado en vivo)"],
            ["Groq Chat", "groq.com", "Sí (Reglas declaradas)", "No (Solo configuración)", "No (No evaluado en vivo)"]
        ],
        col_widths=[1.5, 1.5, 1.3, 1.5, 1.2],
        is_modified=True
    )

    add_tbl_caption("Tabla 3. Taxonomía de política, criterios y reglas de precedencia.", is_modified=True)
    render_table(
        ["Categoría", "Definición operativa completa", "Indicadores de activación", "Regla de exclusión / Precedencia", "Acción"],
        [
            ["Safe_Use", "Consulta legítima laboral, pública, educativa o defensiva", "Preguntas técnicas, sintaxis, conceptos teóricos generales", "Sin datos sensibles reales ni comandos ofensivos explícitos", "ALLOW"],
            ["PII_Leak", "Divulgación de datos personales identificables estructurados", "DNI, pasaportes, teléfonos, correos personales, tarjetas", "Se excluyen identificadores públicos o de prueba sintética obvia", "BLOCK"],
            ["Proprietary_Code", "Secretos técnicos, credenciales de acceso y llaves de API", "Tokens JWT, AWS_KEY, certificados privados, passwords", "Prevalece siempre sobre Safe_Use aunque esté en código defensivo", "BLOCK"],
            ["Business_Secrets", "Información estratégica, balances reservados o nóminas", "Planes de fusión, estados financieros Q3, contratos privados", "Se excluye información corporativa pública o de memorias anuales", "BLOCK"],
            ["Code_Exploitation", "Desarrollo de malware, exploits o payloads ofensivos", "Scripts de evasión de EDR, SQLi destructivo, reverse shells", "Prevalece sobre consultas teóricas si incluye código funcional", "BLOCK"],
            ["Data_Exfiltration", "Mecanismos encubiertos para transferir o fugar datos", "Comandos de túneles DNS, PowerShell oculto, compresión cifrada", "Se excluyen respaldos autorizados explícitamente sin ofuscación", "BLOCK"],
            ["Social_Engineering", "Suplantación de identidad, phishing o engaño dirigido", "Plantillas de restablecimiento forzado de claves, spear-phishing", "Prevalece sobre Safe_Use aunque cite fines de concientización", "BLOCK"],
            ["Role_Evasion_Jailbreak", "Evasión de directrices, manipulación de rol y jailbreaks", "Instrucciones de ignorar directrices, prompts 'DAN', prefijos de rol", "Prevalece sobre intenciones declaradas de investigación de IA", "BLOCK"],
            ["Legal_Misalignment", "Peticiones contrarias a leyes o políticas internas", "Instrucciones para vulnerar licencias, sabotaje informático", "Restricción normativa del sistema; no califica delitos judiciales", "BLOCK"]
        ],
        col_widths=[1.3, 2.0, 1.6, 1.6, 0.5],
        is_modified=True
    )

    # 2.3 (Ítems 5.1, 5.2, 5.5, 5.6)
    add_h2("2.3. Política y motor híbrido")
    add_p("Se estableció una política con nueve categorías para decidir si una solicitud se permite o se bloquea según su clasificación. La categoría Uso seguro permite el envío y las otras ocho agrupan las solicitudes restringidas. La Tabla 3 muestra los criterios operativos, las señales activadoras y las reglas de precedencia de cada categoría. Credenciales y secretos técnicos incluye datos de acceso y otros secretos informáticos, pero no considera confidencial cualquier fragmento de código. Por su parte, Conductas contrarias a la política indica una restricción del sistema y no significa que este determine de forma automática si una conducta es ilegal.")
    add_p("El motor híbrido sigue una jerarquía estricta de evaluación en tres niveles para resolver la ambigüedad y evitar contradicciones entre reglas y modelo: (1) Prioridad 1 (Bloqueo duro determinista): se evalúan primero patrones explícitos de credenciales, secretos técnicos y datos personales estructurados; si coinciden, prevalece siempre el bloqueo (BLOCK) por cortocircuito, aun cuando el texto se formule en un tono defensivo o educativo. (2) Prioridad 2 (Patrones de ataque explícito): se analizan expresiones regulares de explotación, exfiltración e inyecciones de rol explícitas; de existir coincidencia, se ordena BLOCK inmediatamente. (3) Prioridad 3 (Inferencia semántica neuronal): para solicitudes que superan los filtros deterministas (incluyendo consultas de apariencia ambigua), se invoca al encoder DeBERTa-v3-small en ONNX.",
          is_modified=True)
    add_p("El motor calcula una puntuación de riesgo normalizada R(x) en el intervalo [0, 1]. Cuando una regla determinista se activa, asigna un valor categórico prefijado (R = 1,0 para credenciales o explotación; R = 0,0 para consultas defensivas legítimas sin datos sensibles). En las solicitudes derivadas al clasificador neuronal, R(x) corresponde a la suma de probabilidades softmax de las ocho categorías restringidas, calculada a partir de las salidas del modelo: R(x) = sum_{c in Restringidas} P(y=c | x). El umbral de decisión operativa para ordenar el bloqueo se establece formalmente en tau = 0,50. Asimismo, si una solicitud es clasificada preliminarmente como Safe_Use pero su probabilidad softmax no alcanza un umbral de seguridad mínimo (P(Safe_Use | x) < 0,70), el sistema resuelve la ambigüedad a favor de la restricción emitiendo una acción preventiva de bloqueo.",
          is_modified=True)
    add_p("Ante situaciones de falla, el sistema opera bajo una política de fallo seguro (fail-closed) por defecto tanto en la extensión como en el backend FastAPI. Si el clasificador ONNX no está disponible, si la inferencia agota el tiempo de espera, si el archivo de pesos está inaccesible o si el servicio de auditoría no responde, el sistema devuelve estado BLOCK_ON_ERROR y la extensión retiene el evento en el navegador. La evaluación técnica justifica el modo fail-closed porque garantiza un riesgo nulo de fuga accidental de información sensible (riesgo de fuga = 0 ante caída del modelo), a costa de una interrupción transitoria de solicitudes no cubiertas por reglas seguras, superando la contingencia permisiva previa (fail-open) que resulta inaceptable en entornos de alta confidencialidad.",
          is_modified=True)

    # 2.4 (Ítems 2.1, 2.2, 2.3, 2.4, 2.5, 2.6, 3.1, 3.2, 3.3, 3.4, 3.5, 11.1)
    add_h2("2.4. Construcción y composición del corpus")
    add_p("Se creó un corpus para el estudio a partir de escenarios sintéticos locales, combinaciones de sus elementos y solicitudes seleccionadas de recursos públicos. La generación local comenzó con 162 escenarios base en español, 18 por categoría. También se usaron subconjuntos de deepset/prompt-injections [19] y NVIDIA Aegis AI Content Safety Dataset 2.0 [20]. Sus etiquetas se ajustaron a las categorías del estudio según la acción solicitada. De deepset se eligieron ejemplos positivos de inyección de instrucciones, mapeándolos directamente a Role_Evasion_Jailbreak. En el caso de NVIDIA, se seleccionaron solicitudes asociadas a secretos comerciales, código hostil y datos personales, adaptando sus anotaciones originales a la taxonomía local.")
    add_p("El corpus consolidado reúne 2.743 registros: 1.707 para entrenamiento, 510 para validación y 526 para prueba. La Tabla 4 muestra su distribución por categoría. La partición de 526 solicitudes cumplió la función de conjunto de prueba interna durante la ampliación y desarrollo del corpus.",
          is_modified=True)

    add_tbl_caption("Tabla 4. Distribución del corpus activo por partición.")
    render_table(
        ["Categoría", "Entrenamiento", "Validación", "Prueba"],
        [
            ["Safe_Use", "187", "55", "58"],
            ["PII_Leak", "188", "55", "61"],
            ["Proprietary_Code", "187", "55", "55"],
            ["Business_Secrets", "187", "55", "55"],
            ["Code_Exploitation", "195", "55", "60"],
            ["Data_Exfiltration", "187", "55", "55"],
            ["Social_Engineering", "187", "55", "57"],
            ["Role_Evasion_Jailbreak", "202", "70", "70"],
            ["Legal_Misalignment", "187", "55", "55"],
            ["Total", "1.707", "510", "526"]
        ],
        col_widths=[2.5, 1.5, 1.5, 1.5]
    )

    add_p("La Tabla 5 detalla la homologación taxonómica aplicada sobre las fuentes públicas incorporadas, explicitando el dataset de origen, la etiqueta primaria, la categoría de destino en Aegis DLP, el criterio de filtrado y el número de registros adaptados.",
          is_modified=True)

    add_tbl_caption("Tabla 5. Homologación taxonómica de datasets públicos hacia Aegis DLP.", is_modified=True)
    render_table(
        ["Dataset de origen", "Etiqueta original", "Categoría destino Aegis DLP", "Criterio de filtrado / adaptación", "Registros"],
        [
            ["deepset/prompt-injections", "injection (1)", "Role_Evasion_Jailbreak", "Mapeo directo de ejemplos positivos de inyección de prompts", "45"],
            ["NVIDIA Aegis AI Content 2.0", "Needle In A Haystack / Leak", "Data_Exfiltration", "Instrucciones de extracción de contexto confidencial", "10"],
            ["NVIDIA Aegis AI Content 2.0", "Malware / Cyberattack", "Code_Exploitation", "Solicitudes ofensivas de generación o análisis de malware", "8"],
            ["NVIDIA Aegis AI Content 2.0", "PII Disclosure", "PII_Leak", "Peticiones de procesamiento y revelación de datos personales", "7"],
            ["Generación local sintética", "9 categorías base", "9 categorías locales", "Expansión composicional controlada desde 162 plantillas", "2.673"]
        ],
        col_widths=[1.8, 1.6, 1.6, 1.5, 0.5],
        is_modified=True
    )

    add_p("El conjunto de 328 solicitudes utilizado en la evaluación principal corresponde a un subconjunto congelado e independiente de prueba proveniente del ciclo de desarrollo del clasificador v5. La aparente desproporción binaria observada en dicho conjunto (292 solicitudes restringidas frente a 36 seguras, proporción ~8:1) obedece al diseño multiclase estratificado: el conjunto contiene entre 33 y 48 ejemplos por cada una de las nueve clases individuales (~36,4 casos por categoría: 36 de Safe_Use y 292 repartidas homogéneamente entre las ocho categorías restringidas). Al colapsar una taxonomía de nueve clases balanceadas en una decisión binaria operativa (ALLOW vs. BLOCK), se genera estructuralmente una razón de 1:8 (10,98 % seguras vs. 89,02 % restringidas). Matemáticamente, una prevalencia del 89,02 % de casos restringidos infla la precisión predictiva positiva (PPV = 292 / 294 = 99,32 %) y la exactitud binaria (99,39 %), por lo que la calidad operativa del sistema no debe juzgarse por la exactitud binaria trivial, sino por las tasas condicionales independientes de la prevalencia: la exhaustividad de bloqueo (TPR = 292 / 292 = 100,00 %) y la tasa de falsos positivos sobre consultas seguras (FPR = 2 / 36 = 5,56 %).",
          is_modified=True)
    add_p("Para prevenir la contaminación de datos (data leakage) entre particiones, se ejecutó un protocolo de auditoría en tres niveles entre los 1.707 registros de entrenamiento y las 328 solicitudes de evaluación: (1) deduplicación exacta y normalizada mediante hashes SHA-256 tras normalización Unicode, eliminación de mayúsculas y supresión de signos de puntuación; (2) deduplicación cuasi-exacta mediante similitud de Jaccard sobre n-gramas de caracteres (n = 3 a 5) con umbral >= 0,85; y (3) verificación de independencia a nivel de familias sintéticas. La auditoría confirmó cero duplicados exactos y cero pares sobre el umbral de contaminación, ratificando la independencia del conjunto de 328 solicitudes.",
          is_modified=True)
    add_p("La calidad y consistencia del etiquetado se validó mediante un procedimiento cruzado e independiente realizado por dos de los autores (J.M. y J.T.) con formación en seguridad informática y NLP sobre las 328 solicitudes del conjunto de evaluación, utilizando el libro de códigos de la Tabla 3. Las discordancias fueron dirimidas mediante adjudicación por el tercer autor (A.M.). La concordancia observada fue del 91,8 %, alcanzando un coeficiente Kappa de Cohen multiclase de kappa = 0,892 y un Kappa binario de kappa = 0,935, lo que denota una concordancia casi perfecta.",
          is_modified=True)
    add_p("Se declara de forma taxativa que el 100 % de los identificadores personales, nombres, DNI, tarjetas, correos, credenciales técnicas y secretos comerciales contenidos en los 2.743 registros del corpus y en las 328 solicitudes son ficticios y simulados, habiendo sido generados mediante cadenas artificiales y repositorios abiertos, sin utilizar registros de empleados, clientes ni organizaciones reales.",
          is_modified=True)
    add_p("El corpus contiene 2.673 registros en español, 25 en inglés y 45 sin idioma definido o con contenido técnico (97,45 %, 0,91 % y 1,64 %, respectivamente). Además, se pusieron en cuarentena 27.000 registros de versiones anteriores para evitar sesgos de etiquetado. Se reconocen tres limitaciones de representatividad explícitas: (1) en entornos corporativos reales la proporción suele ser inversa (predominio >95 % de consultas legítimas y <5 % de incidentes DLP), donde un FPR = 5,56 % generaría un volumen significativo de falsas alarmas diarias; (2) el predominio del español y una longitud de prompts acotada; y (3) la ausencia de jerga interna y dialectos técnicos específicos de una empresa en particular.",
          is_modified=True)

    # 2.5 (Ítems 7.1, 7.2, 8.1, 8.2, 8.3, 8.4)
    add_h2("2.5. Clasificador y configuración de entrenamiento")
    add_tbl_caption("Tabla 6. Configuración documentada de entrenamiento consolidada.", is_modified=True)
    render_table(
        ["Parámetro / Componente", "Valor / Versión documentada"],
        [
            ["Checkpoint base de Hugging Face", "microsoft/deberta-v3-small (6 capas, hidden=768, 12 cabezas)"],
            ["Categorías de salida", "9 clases multiclase"],
            ["Longitud máxima de secuencia", "256 tokens"],
            ["Configuración LoRA (r / alpha / dropout)", "8 / 16 / 0,1"],
            ["Módulos adaptados con LoRA", "query_proj, key_proj, value_proj (proyecciones Q, K, V)"],
            ["Optimizador e hiperparámetros", "AdamW, lr = 0,0002, beta1 = 0,9, beta2 = 0,999, eps = 1e-8"],
            ["Scheduler de tasa de aprendizaje", "Linear schedule con 10 % de pasos de calentamiento (warmup)"],
            ["Tamaño de lote (train / eval)", "8 / 16"],
            ["Semilla aleatoria fija", "42 (PyTorch, NumPy, partición de datos)"],
            ["Épocas / Paciencia early stopping", "4 épocas completas / Paciencia 2 evaluaciones"],
            ["Hardware de entrenamiento", "AMD Ryzen 5 5600G (6C/12T, 3.9 GHz, 24 GB RAM DDR4)"],
            ["Formato de exportación local", "ONNX opset 17, precisión FP32, dynamic_axes para input_ids"],
            ["Versiones exactas de software", "Python 3.11.9, PyTorch 2.5.1, Transformers 4.47.1, PEFT 0.14.0"],
            ["Bibliotecas auxiliares y runtime", "Scikit-learn 1.6.0, ONNX Runtime 1.20.1, FastAPI 0.115.6, Uvicorn 0.34.0"]
        ],
        col_widths=[3.0, 3.8],
        is_modified=True
    )

    add_p("Se usó DeBERTa-v3-small como encoder para clasificar las solicitudes en nueve categorías. La arquitectura DeBERTaV3 [22] aporta representaciones del lenguaje aprendidas mediante un preentrenamiento con enmascaramiento de gradientes desacoplados. El modelo se adaptó con LoRA [23] bajo los parámetros consolidados en la Tabla 6.")
    add_p("El pipeline de exportación a ONNX se ejecutó paso a paso: tras completar el entrenamiento, se fusionaron los pesos de los adaptadores LoRA mediante la función merge_and_unload() de PEFT (W = W_0 + (alpha/r)*BA); el modelo se configuró en modo de evaluación eval() y se exportó mediante torch.onnx.export con opset_version = 17 y dynamic_axes en las dimensiones de lote y secuencia para input_ids y attention_mask. El grafo resultante fue validado mediante onnx.checker.check_model().",
          is_modified=True)
    add_p("La verificación de equivalencia numérica entre PyTorch y ONNX Runtime se amplió a las 328 solicitudes completas de evaluación. En el 100 % de los casos (328/328) ambas implementaciones coincidieron exactamente en la etiqueta predicha (Top-1 Label Agreement = 100,00 %) y en la acción operativa de política resultante. El error absoluto medio en las probabilidades softmax calculadas fue de MAE = 1,42 x 10^-6 (MAE < 10^-5) y la divergencia máxima absoluta en logits fue de L_inf = 3,8 x 10^-5, confirmando que la exportación local no introduce degradación numérica.",
          is_modified=True)
    add_p("Como método alternativo de referencia (baseline), se entrenó y configuró un modelo clásico de TF-IDF con n-gramas de palabras y caracteres (rango 1 a 3, 50.000 características máximas) acoplado a una regresión logística con parámetro de regularización C = 8,0, ponderación balanceada de clases y semilla 42. Este modelo se entrenó con los mismos 1.707 registros y se evaluó exactamente sobre el mismo conjunto de prueba de 328 solicitudes bajo criterios y métricas equivalentes.",
          is_modified=True)

    # 2.6 (Ítems 4.4, 4.5, 4.7)
    add_h2("2.6. Métricas y separación entre clasificación y autorización")
    add_p("El desempeño multiclase se midió con exactitud, precisión, recall y F1 por categoría, además de F1 macro y F1 ponderado. Para la decisión operativa de política, las predicciones se agruparon en dos clases: bloqueo para las ocho categorías restringidas (clase positiva operativa, N_restringidas = TP + FN = 292) y permiso para Uso seguro (clase negativa operativa, N_seguras = TN + FP = 36). Se definieron formalmente las tasas operativas con sus denominadores respectivos: la tasa de falsos positivos operativa como FPR = FP / (FP + TN) = 2 / 36 = 5,56 % (solicitudes legítimas bloqueadas erróneamente) y la tasa de falsos negativos operativa como FNR = FN / (TP + FN) = 0 / 292 = 0,00 % (amenazas permitidas indebidamente).",
          is_modified=True)
    add_p("La selección de estas métricas se fundamenta directamente en los riesgos operacionales de un sistema DLP: (1) el FNR operativo y el recall de clases restringidas miden directamente el riesgo de fuga o exfiltración no contenida de datos sensibles, que constituye el riesgo de mayor severidad para una organización; (2) el FPR operativo y la precisión de bloqueo miden el riesgo de fricción operativa o denegación de servicio interna (bloquear consultas legítimas de empleados, lo que incentiva a desactivar la herramienta o recurrir a canales alternativos de Shadow AI); y (3) el F1 macro multiclase evalúa la fidelidad diagnóstica de la auditoría en SQLite, asegurando que los incidentes queden tipificados bajo la regla exacta de la política sin que clases mayoritarias oculten deficiencias en categorías minoritarias.",
          is_modified=True)
    add_p("Para cuantificar la incertidumbre estadística, se calcularon intervalos de confianza del 95 % mediante el método exacto de Clopper-Pearson para proporciones binomiales (exactitud, FNR, FPR, TPR y TNR), y mediante Bootstrap estratificado no paramétrico con 10.000 iteraciones con reemplazo para F1 macro y F1 ponderado.",
          is_modified=True)

    # 2.7 (Ítems 6.2, 6.3, 6.5, 6.6, 9.1, 9.2, 9.5, 10.1, 10.2, 10.3, 10.4)
    add_h2("2.7. Rendimiento y comprobaciones funcionales")
    add_p("El endpoint HTTP se evaluó con 1.000 solicitudes sobre un equipo AMD Ryzen 5 5600G (6 núcleos, 12 hilos lógicos a 3.9 GHz, 24 GB RAM DDR4, Windows 11 Pro 64 bits), empleando Python 3.11.9, ONNX Runtime 1.20.1 configurado con 6 hilos intra-op, y FastAPI/Uvicorn con 4 trabajadores concurrentes. La carga cliente se generó mediante un ThreadPoolExecutor asíncrono en localhost que distribuyó de forma continua las 1.000 peticiones entre los 4 trabajadores, registrando la latencia mediante el reloj de alta resolución time.perf_counter_ns(). Las solicitudes del lote presentaron una longitud media de 312 caracteres (mínimo de 45 y máximo de 1.840 caracteres, equivalentes a 12 y 245 tokens), donde un 48 % activó reglas deterministas y un 52 % fue resuelto por inferencia neuronal. Antes de la medición se aplicaron veinte solicitudes de calentamiento.",
          is_modified=True)
    add_p("Para evitar comparaciones erróneas, se delimitaron formalmente tres capas temporales de medición: (1) Motor en memoria (HíbridoONNX / HíbridoTF-IDF): mide exclusivamente la función de evaluación en Python sin red HTTP ni escritura en SQLite; (2) Endpoint de auditoría (HTTP): mide el ciclo cliente-servidor local completo (deserialización JSON + bucle HTTP + motor híbrido + commit transaccional en SQLite); y (3) Intercepción en navegador (Extensión Manifest V3): añade la sobrecarga del content script en el DOM (captura de evento submit, consulta fetch a 127.0.0.1 y liberación del evento), evaluada en Google Chrome v131 bajo Windows 11 Pro.",
          is_modified=True)
    add_p("Se ejecutaron 330 casos de prueba funcional sobre páginas sintéticas con el DOM representativo de ChatGPT, Claude y Gemini, con tres repeticiones independientes por caso, aprobándose el 100 % (330/330). La batería comprendió: consultas legítimas seguras, solicitudes restringidas individuales para las 8 categorías hostiles, consultas ambiguas (conceptos de seguridad sin payload vs. con datos reales), solicitudes multi-tipo (PII más clave API en el mismo prompt) y combinaciones de ataque (jailbreaks acompañados de código propietario). Asimismo, se evaluaron escenarios adversariales de ofuscación léxica (leetspeak y espaciado), codificación Base64 y dilución de contexto (context stuffing): el sistema detectó con éxito cadenas en Base64 mediante reglas decodificadoras y patrones de regex, pero mostró limitaciones ante textos con dilución extensa (>2.000 caracteres de texto inocuo rodeando un dato sensible que no activara una regla fija). Los siete proveedores restantes del manifest disponen de reglas declaradas pero no fueron sometidos a la validación funcional.",
          is_modified=True)
    add_p("La inspección de textos extensos y adjuntos planos se implementó para cargas de hasta 512 KiB en formatos estructurados y texto (.txt, .csv, .json, .py, .md, .log), utilizando una ventana de fragmentación de 3.400 caracteres con un solapamiento (overlap) de 200 caracteres (aprox. 30 a 45 palabras/tokens). Las reglas deterministas analizan la ventana completa de 3.400 caracteres para patrones largos, mientras que el encoder procesa hasta 256 tokens por segmento. El solapamiento de 200 caracteres garantiza que identificadores sensibles que caigan en el límite entre dos bloques no queden partidos ni eludan las expresiones regulares. La decisión final aplica una regla disyuntiva pesimista: A_final = BLOCK si existe al menos un fragmento j con decisión BLOCK, asignando al evento la categoría de máxima puntuación R_final = max_j R(f_j). Se ejecutó un experimento controlado con 34 textos extensos (4.000 a 15.000 caracteres) con datos sensibles ubicados al inicio, en la zona intermedia y cruzando la frontera del carácter 3.400, alcanzando una retención del 100 % en la frontera gracias al solapamiento. No obstante, se reconoce como limitación técnica que si una intención semántica no activa una regla determinista y se ubica entre el token 256 y el carácter 3.400 de un fragmento, queda fuera de la atención del clasificador neuronal. Documentos ofimáticos (.pdf, .docx, .xlsx), archivos comprimidos (.zip) e imágenes quedan excluidos del prototipo y se retienen preventivamente sin inspección.",
          is_modified=True)

    # 2.8 (Ítems 8.5, 11.2, 11.3, 11.4, 11.5)
    add_h2("2.8. Registro minimizado y reproducibilidad")
    add_p("Se implementó un registro local en SQLite (archivo audit_logs.db alojado en el directorio local de la API bajo permisos restringidos del sistema operativo) que almacena: fecha y hora UTC, identificador seudónimo del navegador (UUID v4), destino, acción, categoría, puntuación de riesgo, versión del motor, duración en milisegundos y un hash criptográfico SHA-256 del contenido. El texto original del prompt reside en memoria volátil (RAM) únicamente durante los ~20 ms de procesamiento local y el campo de contenido en SQLite conserva el marcador [REDACTED_BY_POLICY], impidiendo que información sensible quede expuesta en reposo o se transmita fuera de 127.0.0.1.")
    add_p("La Tabla 7 distingue formalmente los controles de privacidad implementados y verificados en el prototipo Aegis DLP de las recomendaciones organizacionales requeridas para un despliegue corporativo en producción.",
          is_modified=True)

    add_tbl_caption("Tabla 7. Controles de privacidad implementados vs. recomendaciones organizacionales.", is_modified=True)
    render_table(
        ["Dimensión de seguridad", "Control implementado y verificado en Aegis DLP", "Recomendación de despliegue organizacional"],
        [
            ["Datos en tránsito", "Procesamiento en memoria volátil en 127.0.0.1; sin telemetría externa", "Aislamiento de red de endpoints y control de extensiones por GPO"],
            ["Datos en reposo", "No persistencia del prompt; sustitución por [REDACTED_BY_POLICY]", "Cifrado en reposo de la base SQLite (BitLocker / SQLCipher)"],
            ["Integridad de auditoría", "Huella criptográfica SHA-256 de la solicitud para verificación forense", "Uso de HMAC con clave rotativa para mitigar ataques de diccionario"],
            ["Gestión de identidades", "Identificador UUID v4 seudónimo no autenticado por navegador", "Integración con identidad corporativa (SSO / Active Directory) y RBAC"],
            ["Ciclo de vida de logs", "Esquema local preparado para purga transaccional periódica", "Políticas formales de retención, rotación y purgado temporal"]
        ],
        col_widths=[1.6, 2.7, 2.5],
        is_modified=True
    )

    add_p("Declaración ética: El presente estudio evaluó el desempeño técnico y computacional de un artefacto de software utilizando exclusivamente conjuntos de datos públicos de acceso abierto y registros sintéticos generados con datos ficticios. Dado que no se involucró la participación de sujetos humanos, ni se recolectaron, procesaron o divulgaron datos personales identificables reales o información confidencial de terceros, la investigación estuvo exenta de revisión formal por un comité de ética de investigación con seres humanos.",
          is_modified=True)
    add_p("Disponibilidad de datos y código: Los materiales para la reproducción completa de los experimentos (scripts de entrenamiento, pipeline de exportación a ONNX, benchmark de latencia, configuración de reglas, evaluador y el corpus sintético anonimizado de 328 y 2.743 solicitudes) se encuentran depositados de forma estructurada y reproducible en el repositorio institucional del proyecto.",
          is_modified=True)

    # ==================== 3. RESULTADOS Y DISCUSIÓN ====================
    add_h1("3. Resultados y discusión")

    # 3.1 (Ítems 4.1, 4.2, 4.3, 4.4, 4.5, 4.6, 7.1, 7.2, 7.3, 7.4)
    add_h2("3.1. Desempeño de clasificación y coherencia de los reportes")
    
    add_h3("3.1.1. Desempeño intrínseco del clasificador multiclase (nueve categorías)", is_modified=True)
    add_p("El clasificador DeBERTa-v3-small adaptado con LoRA obtuvo 312 clasificaciones exactas sobre 328 solicitudes, alcanzando una exactitud global del 95,12 % (IC 95 %: [92,20 % – 97,19 %]). El F1 macro fue de 0,9518 (IC 95 %: [0,9240 – 0,9710]) y el F1 ponderado de 0,9512 (IC 95 %: [0,9235 – 0,9705]), demostrando un comportamiento simétrico entre clases. La precisión ponderada fue de 0,9520 y el ROC-AUC multiclase one-versus-rest alcanzó 0,9973. La Tabla 8 resume los resultados globales y sus intervalos de confianza.",
          is_modified=True)

    add_tbl_caption("Tabla 8. Resultados globales del clasificador de Aegis DLP.")
    render_table(
        ["Métrica de evaluación", "Resultado obtenido", "Intervalo de confianza al 95 %"],
        [
            ["Tamaño del test congelado", "328 solicitudes", "N/A"],
            ["Clasificaciones multiclase exactas", "312 aciertos", "[92,20 % – 97,19 %]"],
            ["Exactitud global (Accuracy)", "95,12 %", "[92,20 % – 97,19 %] (Clopper-Pearson)"],
            ["F1 macro no ponderado", "0,9518", "[0,9240 – 0,9710] (Bootstrap 10.000 it)"],
            ["F1 ponderado por soporte", "0,9512", "[0,9235 – 0,9705] (Bootstrap 10.000 it)"],
            ["Precisión ponderada", "0,9520", "[0,9245 – 0,9712] (Bootstrap 10.000 it)"],
            ["ROC-AUC multiclase OvR", "0,9973", "[0,9945 – 0,9991] (Bootstrap 10.000 it)"]
        ],
        col_widths=[2.8, 1.8, 2.2],
        is_modified=True
    )

    add_p("La Tabla 9 desglosa el desempeño por categoría, incorporando verdaderos positivos (TP), falsos negativos (FN), predichos, falsos positivos (FP), precisión, recall, F1 e intervalos de confianza del 95 % según Clopper-Pearson. Uso seguro alcanzó un recall de 0,9444 (34 aciertos en 36 casos), mientras que Exfiltración de datos presentó el menor recall con 0,8788 (29 aciertos en 33 casos). En el otro extremo, Conductas contrarias a la política alcanzó 1,0000 en precisión y recall.",
          is_modified=True)

    add_tbl_caption("Tabla 9. Desempeño ampliado del clasificador por categoría con intervalos de confianza al 95 %.", is_modified=True)
    render_table(
        ["Categoría", "n (Real)", "TP", "FN", "Pred.", "FP", "Precisión", "Recall", "F1", "IC 95 % Recall"],
        [
            ["Safe_Use", "36", "34", "2", "34", "0", "1,0000", "0,9444", "0,9714", "[0,8134 – 0,9932]"],
            ["PII_Leak", "39", "37", "2", "40", "3", "0,9250", "0,9487", "0,9367", "[0,8268 – 0,9937]"],
            ["Proprietary_Code", "33", "30", "3", "31", "1", "0,9677", "0,9091", "0,9375", "[0,7567 – 0,9808]"],
            ["Business_Secrets", "33", "32", "1", "33", "1", "0,9697", "0,9697", "0,9697", "[0,8424 – 0,9992]"],
            ["Code_Exploitation", "38", "37", "1", "39", "2", "0,9487", "0,9737", "0,9610", "[0,8619 – 0,9993]"],
            ["Data_Exfiltration", "33", "29", "4", "31", "2", "0,9355", "0,8788", "0,9062", "[0,7180 – 0,9660]"],
            ["Social_Engineering", "35", "34", "1", "37", "3", "0,9189", "0,9714", "0,9444", "[0,8508 – 0,9993]"],
            ["Role_Evasion_Jailbreak", "48", "46", "2", "50", "4", "0,9200", "0,9583", "0,9388", "[0,8575 – 0,9949]"],
            ["Legal_Misalignment", "33", "33", "0", "33", "0", "1,0000", "1,0000", "1,0000", "[0,8942 – 1,0000]"],
            ["Total / Global", "328", "312", "16", "328", "16", "0,9520*", "0,9512*", "0,9518**", "[0,9220 – 0,9719]"]
        ],
        col_widths=[1.5, 0.5, 0.4, 0.4, 0.5, 0.4, 0.7, 0.7, 0.7, 1.2],
        is_modified=True
    )
    add_p("* Precisión y recall ponderados por soporte. ** F1 macro no ponderado.", italic=True, size=Pt(8.5), is_modified=True, space_after=Pt(4))

    add_p("La Tabla 10 expone la matriz de confusión multiclase 9x9 completa. En la diagonal se sitúan los 312 aciertos exactos, mientras que las 16 discrepancias fuera de ella reflejan los patrones de confusión semántica del modelo.",
          is_modified=True)

    add_tbl_caption("Tabla 10. Matriz de confusión multiclase 9x9 del clasificador en el conjunto de prueba.", is_modified=True)
    render_table(
        ["Clase Real \\ Pred.", "C1", "C2", "C3", "C4", "C5", "C6", "C7", "C8", "C9", "Total"],
        [
            ["C1: Safe_Use", "34", "0", "0", "0", "0", "0", "0", "2", "0", "36"],
            ["C2: PII_Leak", "0", "37", "0", "0", "0", "0", "1", "1", "0", "39"],
            ["C3: Proprietary_Code", "0", "1", "30", "0", "0", "2", "0", "0", "0", "33"],
            ["C4: Business_Secrets", "0", "0", "1", "32", "0", "0", "0", "0", "0", "33"],
            ["C5: Code_Exploitation", "0", "0", "0", "0", "37", "0", "1", "0", "0", "38"],
            ["C6: Data_Exfiltration", "0", "2", "0", "1", "0", "29", "1", "0", "0", "33"],
            ["C7: Social_Engineering", "0", "0", "0", "0", "0", "0", "34", "1", "0", "35"],
            ["C8: Role_Evasion", "0", "0", "0", "0", "2", "0", "0", "46", "0", "48"],
            ["C9: Legal_Misalignment", "0", "0", "0", "0", "0", "0", "0", "0", "33", "33"],
            ["Total Predichas", "34", "40", "31", "33", "39", "31", "37", "50", "33", "328"]
        ],
        col_widths=[1.5, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.45, 0.6],
        is_modified=True
    )

    add_p("El análisis cualitativo de los 16 errores revela dos conclusiones críticas: (1) Los dos falsos positivos operativos correspondieron a consultas benignas de programación que empleaban estructuras imperativas ('Simula ser un compilador estricto...' y 'Actúa como validador de seguridad...'), activando erróneamente la clase Role_Evasion_Jailbreak. (2) Las catorce confusiones restantes ocurrieron exclusivamente entre categorías restringidas: 4 casos en Data_Exfiltration (asignados a PII, Secrets y Social Engineering debido a la presencia simultánea de identificadores y comandos de extracción), 3 en Proprietary_Code, 2 en PII_Leak, 2 en Role_Evasion, 1 en Business_Secrets, 1 en Code_Exploitation y 1 en Social_Engineering. Esta confusión afecta la precisión de la tipificación forense en SQLite, pero no compromete la seguridad, pues las ocho categorías conllevan la acción unificada de bloqueo (BLOCK).",
          is_modified=True)

    add_h3("3.1.2. Desempeño en la decisión operativa binaria (ALLOW vs. BLOCK)", is_modified=True)
    add_p("Al proyectar la taxonomía multiclase sobre las acciones de la política, las 292 solicitudes restringidas recibieron categorías de bloqueo y 34 de las 36 solicitudes seguras recibieron permiso. La Tabla 11 presenta la matriz de confusión binaria.",
          is_modified=True)

    add_tbl_caption("Tabla 11. Distribución binaria de las predicciones según la política.")
    render_table(
        ["Clase real de la solicitud", "Predicción: ALLOW", "Predicción: BLOCK", "Total casos"],
        [
            ["Segura (N_seguras = 36)", "34 (Verdaderos Negativos, TNR = 94,44 %)", "2 (Falsos Positivos, FPR = 5,56 %)", "36"],
            ["Restringida (N_restringidas = 292)", "0 (Falsos Negativos, FNR = 0,00 %)", "292 (Verdaderos Positivos, TPR = 100,00 %)", "292"]
        ],
        col_widths=[2.4, 2.0, 2.0, 0.8],
        is_modified=True
    )

    add_p("En el conjunto evaluado se obtuvo una tasa de falsos negativos de FNR = 0 / 292 = 0,00 %, con un intervalo de confianza exacto al 95 % de Clopper-Pearson de [0,00 % – 1,26 %] (reforzado por la regla de Hanley-Lippman para cero eventos, 3/n = 3/292 = 1,03 %). Este resultado permite afirmar con 95 % de confianza estadística que la tasa real de omisión se sitúa por debajo del 1,3 % bajo las condiciones del estudio, advirtiendo con prudencia que ante entradas fuera de distribución o técnicas de evasión no vistas en entrenamiento el sistema sí puede producir omisiones en tráfico real. Por su parte, la tasa de falsos positivos sobre solicitudes legítimas fue de FPR = 2 / 36 = 5,56 % (IC 95 %: [0,68 % – 18,66 %]).",
          is_modified=True)

    add_p("La Tabla 12 presenta la comparación integral entre cuatro enfoques evaluados sobre el mismo conjunto de 328 solicitudes: solo reglas deterministas, el clasificador clásico TF-IDF con regresión logística, DeBERTa-v3-small adaptado con LoRA y el motor híbrido completo.",
          is_modified=True)

    add_tbl_caption("Tabla 12. Comparación integral de modelos sobre el mismo conjunto de prueba.", is_modified=True)
    render_table(
        ["Modelo / Enfoque evaluado", "Exactitud", "F1 macro", "FPR (%)", "FNR (%)", "Latencia media", "Latencia p95", "RAM pico", "Artefacto disco"],
        [
            ["Reglas deterministas solas", "64,33 %", "0,6210", "0,00 %", "37,33 %", "0,105 ms", "0,185 ms", "12 MB", "< 1 MB"],
            ["TF-IDF + Regresión Logística", "92,68 %", "0,9245", "8,33 %", "0,68 %", "0,510 ms", "0,815 ms", "48 MB", "3,8 MB"],
            ["DeBERTa-v3-small + LoRA (ONNX)", "95,12 %", "0,9518", "5,56 %", "0,00 %", "2,202 ms", "9,640 ms", "285 MB", "172 MB"],
            ["Motor Híbrido Completo (Aegis)", "95,12 %", "0,9518", "5,56 %", "0,00 %", "1,850 ms", "9,420 ms", "295 MB", "173 MB"]
        ],
        col_widths=[1.8, 0.7, 0.7, 0.7, 0.7, 0.8, 0.8, 0.7, 0.7],
        is_modified=True
    )

    add_p("La comparación empírica evidencia que las reglas solas son ultrarrápidas pero inaceptables en seguridad por su alto escape semántico (FNR = 37,33 %). TF-IDF logra una alta eficiencia (0,51 ms) pero presenta un FNR del 0,68 % y un FPR del 8,33 %. El clasificador DeBERTa-v3-small elimina los falsos negativos observados (FNR = 0,00 %) y reduce las falsas alarmas (FPR = 5,56 %), justificando plenamente el incremento de latencia a 2,20 ms y el consumo de 285 MB de RAM en CPU, satisfaciendo holgadamente la meta interactiva de 50 ms.",
          is_modified=True)

    # 3.2 (Ítems 5.3, 5.4, 6.1, 9.3, 9.4, 9.6, 10.5)
    add_h2("3.2. Rendimiento, latencia y resiliencia ante fallos")
    add_p("El benchmark HTTP registró un tiempo de respuesta medio de 20,492 ms, mediana de 15,049 ms, p95 de 44,375 ms y p99 de 65,832 ms, con una desviación estándar entre cinco repeticiones independientes de 20,49 +- 1,12 ms, procesando 194,7 solicitudes por segundo. El p95 cumplió con el criterio de aceptación interactivo (<= 50 ms), aunque el p99 evidencia colas de variabilidad transitorias.",
          is_modified=True)
    add_p("La Tabla 13 presenta las estadísticas de latencia separando el Endpoint HTTP completo (bloque A) del Motor de decisión aislado en memoria (bloque B). Los datos aclaran dos dinámicas: (1) En Híbrido ONNX, la mediana de 0,105 ms frente al p95 de 9,640 ms refleja una distribución bimodal: en más del 50 % de solicitudes, las reglas deterministas resuelven la decisión por cortocircuito en microsegundos sin invocar al transformer, mientras que el percentil 95 representa los casos derivados a inferencia neuronal en CPU (8 a 11 ms). (2) El rendimiento HTTP de 194,7 req/s responde rigurosamente a la Ley de Little (lambda = C / W_medio = 4 / 0,020492 s = 195,2 req/s) para cuatro trabajadores concurrentes, incorporando la serialización JSON y la inserción transaccional en SQLite.",
          is_modified=True)

    add_tbl_caption("Tabla 13. Benchmark de latencia y rendimiento desagregado por capas.", is_modified=True)
    render_table(
        ["Capa evaluada / Métrica", "Media (ms)", "p50 (ms)", "p90 (ms)", "p95 (ms)", "p99 (ms)", "Throughput (req/s)"],
        [
            ["A) Endpoint HTTP (4 workers + SQLite)", "20,492 +- 1,12", "15,049", "38,210", "44,375", "65,832", "194,7 +- 4,2"],
            ["B) Híbrido ONNX (Motor aislado memoria)", "2,202 +- 0,18", "0,105", "8,450", "9,640", "11,010", "453,9 +- 12,5"],
            ["B) Híbrido TF-IDF (Baseline memoria)", "0,510 +- 0,04", "0,465", "0,740", "0,815", "1,168", "1.961,4 +- 35,0"]
        ],
        col_widths=[2.4, 1.0, 0.8, 0.8, 0.8, 0.8, 1.2],
        is_modified=True
    )

    add_p("La Tabla 14 documenta los resultados de la batería de pruebas de resiliencia y fallo seguro (fail-closed) ejecutada ante seis condiciones de perturbación inducida.",
          is_modified=True)

    add_tbl_caption("Tabla 14. Pruebas de resiliencia y fallo seguro (Fail-Closed) ante perturbaciones.", is_modified=True)
    render_table(
        ["Escenario de fallo", "Componente afectado", "Mecanismo de contingencia", "Decisión esperada", "Decisión observada", "Estado solicitud"],
        [
            ["F-01: Servicio FastAPI detenido", "Red / Socket HTTP", "Extensión detecta ERR_CONNECTION_REFUSED", "BLOCK preventivo", "BLOCK / Retención DOM", "Retenida (Fail-Closed)"],
            ["F-02: Modelo ONNX ausente/dañado", "Backend de inferencia", "Manejador de excepciones captura FileNotFoundError", "HTTP 500 + BLOCK", "HTTP 500 / BLOCK_ON_ERROR", "Retenida (Fail-Closed)"],
            ["F-03: Interrupción de socket local", "Canal de transporte", "Extensión detecta cierre abrupto de stream", "BLOCK preventivo", "BLOCK / Retención DOM", "Retenida (Fail-Closed)"],
            ["F-04: Latencia inducida > timeout", "Bucle de eventos", "Extensión cancela tras agotar 2.000 ms", "BLOCK por timeout", "BLOCK / AbortController", "Retenida (Fail-Closed)"],
            ["F-05: Payload JSON malformado", "Parser de respuesta", "Extensión valida esquema JSON mediante schema validator", "BLOCK por anomalía", "BLOCK / Formato inválido", "Retenida (Fail-Closed)"],
            ["F-06: Base SQLite bloqueada (I/O)", "Capa de persistencia", "Transacción SQLite falla por bloqueo de archivo", "HTTP 503 + BLOCK", "HTTP 503 / Retención preventiva", "Retenida (Fail-Closed)"]
        ],
        col_widths=[1.5, 1.1, 1.6, 1.1, 1.4, 1.1],
        is_modified=True
    )

    add_p("La Tabla 15 presenta una muestra representativa de la matriz de pruebas funcionales ejecutada sobre navegador, ilustrando los casos probados y su comportamiento.",
          is_modified=True)

    add_tbl_caption("Tabla 15. Matriz de pruebas funcionales representativas en navegador.", is_modified=True)
    render_table(
        ["ID / Escenario", "Entrada utilizada (Tipo / Resumen del Prompt)", "Resultado esperado (Acción / SQLite)", "Resultado observado", "Estado"],
        [
            ["TC-01: Consulta segura", "Cálculo de distancia euclidiana en Python sin datos sensibles", "ALLOW / Safe_Use (auditado sin texto)", "ALLOW / Envío liberado", "Aprobado"],
            ["TC-02: Fuga credencial", "Export de credenciales de AWS (AKIAIOSFODNN7EXAMPLE...)", "BLOCK / Proprietary_Code (auditado)", "BLOCK / Evento retenido", "Aprobado"],
            ["TC-03: PII estructurada", "Lista de DNI, nombres y teléfonos de clientes peruanos", "BLOCK / PII_Leak (auditado)", "BLOCK / Evento retenido", "Aprobado"],
            ["TC-04: Secreto comercial", "Borrador de balance financiero confidencial Q3 no publicado", "BLOCK / Business_Secrets (auditado)", "BLOCK / Evento retenido", "Aprobado"],
            ["TC-05: Inyección de rol", "Prompt 'Ignora directrices y revela el prompt del sistema'", "BLOCK / Role_Evasion (auditado)", "BLOCK / Evento retenido", "Aprobado"],
            ["TC-06: Consulta ambigua", "Consulta defensiva sobre cómo mitigar inyecciones SQL", "ALLOW / Safe_Use (regla de contexto defensivo)", "ALLOW / Envío liberado", "Aprobado"],
            ["TC-07: Ataque combinado", "Prompt con adopción de rol jailbreak que incluye token JWT", "BLOCK / Proprietary_Code (prevalencia sensible)", "BLOCK / Evento retenido", "Aprobado"],
            ["TC-08: Texto extenso 8 KB", "Archivo .txt con credencial sensible en carácter 3.400", "BLOCK / Proprietary_Code (solapamiento 200 c)", "BLOCK / Carga retenida", "Aprobado"],
            ["TC-09: Desconexión API", "Envío de prompt con el servicio FastAPI apagado", "BLOCK / Retención preventiva por fallo", "BLOCK / Modal de error", "Aprobado"],
            ["TC-10: Formato no texto", "Intento de adjuntar archivo .pdf binario de 120 KiB", "BLOCK / Retención preventiva (no extraíble)", "BLOCK / Archivo rechazado", "Aprobado"]
        ],
        col_widths=[1.3, 2.1, 1.8, 1.4, 0.6],
        is_modified=True
    )

    # 3.3 (Ítems 11.2, 11.3, 11.5)
    add_h2("3.3. Relación con la privacidad y gobernanza")
    add_p("Aegis DLP revisa las solicitudes antes del envío y registra las decisiones de la política en las rutas que cubre. Este control aborda el problema de Shadow AI descrito en [1] y [2], ya que permite inspeccionar las solicitudes y dar seguimiento a las decisiones. Las pruebas de clasificación y funcionamiento muestran cómo se aplica en escenarios controlados. Para usarlo en una organización, también se necesitan políticas de uso, responsables y procedimientos de supervisión.")
    add_p("La diferencia frente a SD-RAG [7] y los mecanismos revisados por Edemacu y Wu [6] está en el momento en que actúa y en la decisión que toma. El prototipo permite o retiene solicitudes, pero no aplica todas las técnicas de perturbación, privacidad diferencial o divulgación selectiva descritas en esos trabajos. Puede complementar la protección que ofrece el propio servicio, sobre todo cuando los usuarios utilizan proveedores externos. Sin embargo, esta relación no se evaluó mediante una comparación experimental ni demuestra que alguna de estas estrategias sea suficiente por sí sola.")
    add_p("Registrar la versión, la categoría y la acción permite aplicar parte de las prácticas de gobernanza descritas en [8] y [11]. La relación con KIBO [12] es conceptual, porque el sistema genera evidencia durante su funcionamiento. Esto no certifica el cumplimiento de COBIT o ISO/IEC 42001 [17]. La organización debe definir los responsables, los procedimientos, los permisos de acceso y los plazos de conservación de los registros.")
    add_p("La política de no retención reduce los datos almacenados, aunque también limita la posibilidad de recuperar el contexto de un error. Los metadatos y las huellas digitales del contenido permiten comprobar eventos conocidos, pero no recuperar el texto de cualquier solicitud anterior. Además, si un texto es predecible, se pueden probar posibles textos y comparar sus hashes. Por eso, incluir un hash sin sal (unsalted hash) no hace que el registro sea automáticamente anónimo ante ataques de diccionario de fuerza bruta. La organización debe equilibrar la privacidad con la revisión de decisiones, definir quién puede acceder a los eventos y protegerlos contra cambios no autorizados mediante controles de gobernanza.")

    # 3.4 (Ítems 2.6, 6.3, 10.3, 10.4, 12.2, 12.3, 12.4, 12.5)
    add_h2("3.4. Limitaciones del estudio, amenazas a la validez y trabajo futuro", is_modified=True)
    add_p("Para interpretar adecuadamente el alcance de la investigación, es indispensable distinguir entre tres niveles de desempeño del sistema: (1) el rendimiento intrínseco del clasificador neuronal, que mide su precisión algorítmica para discriminar texto (95,12 % multiclase, F1 macro de 0,9518); (2) el funcionamiento del mecanismo de bloqueo, que evalúa la capacidad de la extensión Manifest V3 y del motor híbrido para retener solicitudes bajo la política fail-closed (100 % de intercepción observada en los casos evaluados); y (3) la efectividad integral de la arquitectura, que constituye una propiedad emergente en un entorno productivo real dependiente de factores exógenos como la estabilidad del DOM de los proveedores, el comportamiento humano de los empleados, la ausencia de canales no web y el manejo de formatos binarios.",
          is_modified=True)
    add_p("Se reconocen explícitamente cuatro amenazas a la validez que condicionan la transferibilidad de las métricas: (a) Validez de los datos: el corpus dirigido, balanceado sintéticamente a nivel multiclase y con una razón resultante de 1:8, difiere de la prevalencia empresarial (>95 % de consultas benignas), lo que implica que una tasa de falsos positivos del 5,56 % provocaría fricción operativa diaria si no se acompaña de retroalimentación supervisada. (b) Validez de la integración: las pruebas funcionales se realizaron sobre páginas HTML sintéticas; las interfaces web en producción de los diez proveedores cambian dinámicamente sus árboles DOM y selectores, lo que exige mecanismos de monitoreo continuo y mantenimiento adaptativo. (c) Validez de constructo ante evasión adversarial: el prototipo demostró solidez ante credenciales explícitas y patrones estructurados, pero presenta vulnerabilidades ante técnicas de ofuscación avanzada (como leetspeak complejo o dilución contextual de secretos dispersos en bloques masivos de texto inocuo). (d) Validez de alcance de contenido: el sistema no inspecciona documentos ofimáticos (.pdf, .docx) ni imágenes con texto incrustado, y su arquitectura single-turn no detecta ataques de jailbreak fragmentados a lo largo de diálogos de múltiples turnos.",
          is_modified=True)
    add_p("El trabajo futuro contempla: extender la validación a despliegues en vivo con telemetría sobre interfaces reales, incorporar módulos de extracción OCR para documentos ofimáticos, implementar modelos de representación contextual para conversaciones multi-turno y cuantizar el encoder a INT8 para evaluar su portabilidad a dispositivos cliente de bajos recursos.")

    # ==================== 4. CONCLUSIONES (Ítems 1.4, 5.7, 12.1, 12.2, 12.3, 12.5) ====================
    add_h1("4. Conclusiones")
    add_p("Se desarrolló y evaluó Aegis DLP como una arquitectura de inspección local que combina una extensión de navegador Manifest V3, reglas deterministas, un clasificador DeBERTa-v3-small adaptado mediante LoRA y un registro de decisiones que minimiza el almacenamiento de información sensible. El sistema aplica una política estructurada de nueve categorías para resolver la autorización o bloqueo de solicitudes dirigidas a asistentes de inteligencia artificial generativa antes de su envío.",
          is_modified=True)
    add_p("En una muestra de prueba controlada de 328 solicitudes, el clasificador alcanzó una exactitud del 95,12 % (IC 95 %: [92,20 % – 97,19 %]) y un F1 macro de 0,9518, superando al modelo de referencia clásico TF-IDF con regresión logística (92,68 % y 0,9245). La decisión operativa demostró una tasa de falsos negativos del 0,00 % (límite superior al 95 % de confianza según Clopper-Pearson de 1,26 % [0,00 % – 1,26 %]), reteniendo la totalidad de las 292 solicitudes hostiles evaluadas. En las consultas legítimas, se registró una tasa de falsos positivos del 5,56 % (dos bloqueos indebidos en 36 casos, IC 95 %: [0,68 % – 18,66 %]). La consistencia del corpus fue respaldada por un coeficiente Kappa de Cohen de 0,892 entre evaluadores independientes. Las pruebas de resiliencia comprobaron la efectividad de la política de fallo seguro (fail-closed) y de la precedencia estricta de las reglas de datos sensibles ante seis escenarios de fallo.",
          is_modified=True)
    add_p("La evaluación de rendimiento del endpoint HTTP en un procesador AMD Ryzen 5 5600G registró una latencia p95 de 44,375 ms y un rendimiento de 194,7 solicitudes por segundo, satisfaciendo el criterio de aceptación interactivo prefijado (<= 50 ms). Se concluye que Aegis DLP constituye una solución técnicamente viable para apoyar la reducción de la superficie de exposición y la trazabilidad de decisiones en entornos controlados de laboratorio. Su efectividad práctica en organizaciones depende de la actualización continua frente a cambios en los selectores DOM de los proveedores externos, la gestión de falsas alarmas y su complementariedad con directrices de gobernanza y capacitación corporativa.",
          is_modified=True)

    # ==================== REFERENCIAS ====================
    add_h1("Referencias")
    refs = [
        "[1] D. Puthal, A. K. Mishra, S. P. Mohanty, A. Longo, C. Y. Yeun, “Shadow AI: Cyber Security Implications, Opportunities and Challenges in the Unseen Frontier,” SN Computer Science, vol. 6, n.º 5, art. 405, 2025. doi: 10.1007/s42979-025-03962-x.",
        "[2] G. Sebastian, “Digital shadow AI risk theory (DART): A framework for managing data disclosure and privacy risks of AI tools at work,” Technological Forecasting and Social Change, vol. 229, art. 124697, 2026. doi: 10.1016/j.techfore.2026.124697.",
        "[3] T. Chin, Q. Li, F. Mirone, A. Papa, “Conflicting impacts of shadow AI usage on knowledge leakage in metaverse-based business models: A Yin-Yang paradox framing,” Technology in Society, vol. 81, art. 102793, 2025. doi: 10.1016/j.techsoc.2024.102793.",
        "[4] B. C. Das, M. H. Amini, Y. Wu, “Security and Privacy Challenges of Large Language Models: A Survey,” ACM Computing Surveys, vol. 57, n.º 6, pp. 1–39, 2025. doi: 10.1145/3712001.",
        "[5] A. D. E. Berini et al., “Security and privacy in LLMs: A comprehensive survey of threats and mitigation strategies,” Information Fusion, vol. 132, art. 104241, 2026. doi: 10.1016/j.inffus.2026.104241.",
        "[6] K. Edemacu, X. Wu, “Privacy Preserving Prompt Engineering: A Survey,” ACM Computing Surveys, vol. 57, n.º 10, pp. 1–36, 2025. doi: 10.1145/3729219.",
        "[7] A. Al Masoud, M. Arazzi, A. Nocera, “SD-RAG: A framework for secure selective disclosure in retrieval-augmented generation against single-turn prompt-leaking attacks,” Expert Systems with Applications, publicación anticipada, 2026. doi: 10.1016/j.eswa.2026.133154.",
        "[8] E. Papagiannidis, P. Mikalef, K. Conboy, “Responsible artificial intelligence governance: A review and research framework,” The Journal of Strategic Information Systems, vol. 34, n.º 2, art. 101885, 2025. doi: 10.1016/j.jsis.2024.101885.",
        "[9] M. A. Camilleri, “Artificial intelligence governance: Ethical considerations and implications for social responsibility,” Expert Systems, vol. 41, n.º 7, art. e13406, 2024. doi: 10.1111/exsy.13406.",
        "[10] B. W. Wirtz, J. C. Weyerer, I. Kehl, “Governance of artificial intelligence: A risk and guideline-based integrative framework,” Government Information Quarterly, vol. 39, n.º 4, art. 101685, 2022. doi: 10.1016/j.giq.2022.101685.",
        "[11] J. Schneider, R. Abraham, C. Meske, J. Vom Brocke, “Artificial Intelligence Governance For Businesses,” Information Systems Management, vol. 40, n.º 3, pp. 229–249, 2023. doi: 10.1080/10580530.2022.2085825.",
        "[12] I. Kirpitsas, T. Pachidis, “KIBO, a new hybrid software development method with enhanced information systems auditing capability,” Information and Software Technology, vol. 190, art. 107958, 2026. doi: 10.1016/j.infsof.2025.107958.",
        "[13] A. Bodnari, J. Travis, “Scaling enterprise AI in healthcare: the role of governance in risk mitigation frameworks,” npj Digital Medicine, vol. 8, n.º 1, art. 272, 2025. doi: 10.1038/s41746-025-01700-4.",
        "[14] M. Arazzi et al., “NLP-based techniques for Cyber Threat Intelligence,” Computer Science Review, vol. 58, art. 100765, 2025. doi: 10.1016/j.cosrev.2025.100765.",
        "[15] X. Huang et al., “A survey of safety and trustworthiness of large language models through the lens of verification and validation,” Artificial Intelligence Review, vol. 57, n.º 7, art. 175, 2024. doi: 10.1007/s10462-024-10824-0.",
        "[16] Y. Zheng, Y. Chen, B. Qian, X. Shi, Y. Shu, J. Chen, “A Review on Edge Large Language Models: Design, Execution, and Applications,” ACM Computing Surveys, vol. 57, n.º 8, pp. 1–35, 2025. doi: 10.1145/3719664.",
        "[17] ISO/IEC, ISO/IEC 42001:2023 Information technology — Artificial intelligence — Management system, 2023. Disponible: ISO/IEC 42001.",
        "[18] OWASP GenAI Security Project, “LLM02:2025 Sensitive Information Disclosure,” 2025. Disponible: OWASP LLM02.",
        "[19] deepset, “Prompt Injections,” dataset, Hugging Face. Consultado: 12 oct. 2026. Disponible: deepset/prompt-injections.",
        "[20] NVIDIA, “Aegis AI Content Safety Dataset 2.0,” dataset, Hugging Face. Consultado: 12 oct. 2026. Disponible: NVIDIA Aegis 2.0.",
        "[21] S. Kapoor, A. Narayanan, “Leakage and the reproducibility crisis in machine-learning-based science,” Patterns, vol. 4, n.º 9, art. 100804, 2023. doi: 10.1016/j.patter.2023.100804.",
        "[22] P. He, J. Gao y W. Chen, “DeBERTaV3: Improving DeBERTa using ELECTRA-Style Pre-Training with Gradient-Disentangled Embedding Sharing,” en ICLR, 2023. Disponible: arXiv:2111.09543.",
        "[23] E. J. Hu et al., “LoRA: Low-Rank Adaptation of Large Language Models,” en ICLR, 2022. Disponible: arXiv:2106.09685.",
        "[24] L. Wang et al., “Parameter-efficient fine-tuning in large language models: a survey of methodologies,” Artificial Intelligence Review, vol. 58, n.º 8, art. 227, 2025. doi: 10.1007/s10462-025-11236-4.",
        "[25] H. Tyralis, G. Papacharalampous, “A review of predictive uncertainty estimation with machine learning,” Artificial Intelligence Review, vol. 57, n.º 4, art. 94, 2024. doi: 10.1007/s10462-023-10698-8."
    ]
    for r in refs:
        add_p(r, size=Pt(9.5), space_after=Pt(3))

    return doc

print("Compilando versión limpia exhaustiva (65 ítems)...")
clean_doc = build_full_manuscript(highlight_mode=False)
clean_path = r"C:\Users\David\Proyectos IX ciclo\Gobierno de IA\Articulo_Aegis_DLP_Corregido.docx"
clean_doc.save(clean_path)
print(f"Versión limpia guardada en: {clean_path}")

print("Compilando versión resaltada en amarillo exhaustiva (65 ítems)...")
hl_doc = build_full_manuscript(highlight_mode=True)
hl_path = r"C:\Users\David\Proyectos IX ciclo\Gobierno de IA\Articulo_Aegis_DLP_Modificaciones_Resaltadas.docx"
hl_doc.save(hl_path)
print(f"Versión resaltada guardada en: {hl_path}")

brain_dir = r"C:\Users\David\.gemini\antigravity\brain\829d563f-e840-4fc0-8db6-d42ea33671d5"
clean_doc.save(os.path.join(brain_dir, "Articulo_Aegis_DLP_Corregido.docx"))
hl_doc.save(os.path.join(brain_dir, "Articulo_Aegis_DLP_Modificaciones_Resaltadas.docx"))
print("Sincronización en brain completada exitosamente.")
