# -*- coding: utf-8 -*-
"""
Script para generar el manuscrito revisado de Aegis DLP conservando
ESTRICTAMENTE la estructura original (mismos encabezados 1, 2.1-2.8, 3.1-3.4, 4 y exactamente las Tablas 1 a 7).

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

def set_cell_margins(cell, top=80, bottom=80, left=120, right=120):
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

def set_table_borders(table, color="CCCCCC", sz="4", val="single"):
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

def build_manuscript_exact_structure(highlight_mode=False):
    doc = Document()
    
    # Márgenes de página estándar
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

    def add_h1(text):
        return add_p(text, bold=True, size=Pt(13), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(6))

    def add_h2(text):
        return add_p(text, bold=True, size=Pt(11.5), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(4))

    def add_tbl_caption(text):
        return add_p(text, bold=True, size=Pt(10), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(3))

    def render_table(headers, data, col_widths=None, highlight_header=False, highlight_rows=False):
        tbl = doc.add_table(rows=len(data) + 1, cols=len(headers))
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(tbl)
        
        # Header
        hdr_row = tbl.rows[0]
        for idx, h_text in enumerate(headers):
            cell = hdr_row.cells[idx]
            set_cell_margins(cell, top=70, bottom=70, left=90, right=90)
            set_cell_background(cell, "F2F2F2")
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.05
            run = p.add_run(h_text)
            run.bold = True
            run.font.name = 'Times New Roman'
            run.font.size = Pt(9)
            if highlight_mode and highlight_header:
                run.font.highlight_color = WD_COLOR_INDEX.YELLOW

        # Rows
        for r_idx, row_data in enumerate(data):
            row = tbl.rows[r_idx + 1]
            bg = "FAFAFA" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, val in enumerate(row_data):
                cell = row.cells[c_idx]
                set_cell_margins(cell, top=50, bottom=50, left=90, right=90)
                set_cell_background(cell, bg)
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                p.paragraph_format.space_after = Pt(0)
                p.paragraph_format.line_spacing = 1.05
                run = p.add_run(str(val))
                run.font.name = 'Times New Roman'
                run.font.size = Pt(8.5)
                if highlight_mode and highlight_rows:
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

    # ==================== RESUMEN ====================
    add_p("Resumen", bold=True, size=Pt(11.5), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(3))
    add_p("El uso de asistentes generativos en actividades laborales incrementa el riesgo de divulgar información sensible y justifica incorporar controles antes del envío. El presente trabajo desarrolla y evalúa Aegis DLP, un sistema de inspección local que integra una extensión de navegador, reglas deterministas y un clasificador DeBERTa-v3-small adaptado mediante LoRA y ejecutado con ONNX. La investigación se estructuró como una investigación aplicada de evaluación tecnológica con pruebas controladas de laboratorio. Comprendió la construcción de un corpus dirigido de 2.743 solicitudes, una evaluación del clasificador sobre un conjunto congelado de 328 solicitudes, una comparación frente a un modelo de referencia TF-IDF con regresión logística, pruebas funcionales de autorización y bloqueo bajo una política de fallo seguro (fail-closed) y un benchmark HTTP de 1.000 solicitudes. El clasificador alcanzó una exactitud del 95,12 % (IC 95 %: [92,20 % – 97,19 %]) y un F1 macro de 0,9518, superando al modelo TF-IDF (92,68 % y 0,9245). Las 292 solicitudes restringidas recibieron categorías asociadas a bloqueo; 278 obtuvieron su categoría exacta y catorce se confundieron entre categorías restringidas, resultando en una tasa de falsos negativos operativos del 0,00 % (IC 95 %: [0,00 % – 1,26 %]). De las 36 solicitudes seguras, 34 se clasificaron correctamente y dos recibieron categorías de bloqueo (tasa de falsos positivos del 5,56 %, IC 95 %: [0,68 % – 18,66 %]). La concordancia inter-anotador entre los autores alcanzó un coeficiente Kappa de Cohen de 0,892. En un equipo AMD Ryzen 5 5600G, el endpoint obtuvo una latencia p95 de 44,375 ms y un rendimiento de 194,7 solicitudes por segundo. Se concluye que Aegis DLP constituye una solución técnicamente viable para apoyar el control local de solicitudes y la trazabilidad de decisiones mediante registros minimizados en condiciones controladas, requiriéndose estudios complementarios para determinar su generalización en flujos laborales reales.",
          is_modified=True)
    add_p("Palabras clave: auditoría informática; clasificación de texto; fuga de datos; inferencia local; inteligencia artificial generativa; seguridad informática.", 
          italic=True, space_after=Pt(10))

    # ==================== ABSTRACT ====================
    add_p("Abstract", bold=True, size=Pt(11.5), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(3))
    add_p("The use of generative AI assistants in work-related tasks increases the risk of disclosing sensitive information, justifying the implementation of controls prior to data submission. This work develops and evaluates Aegis DLP, a local inspection system that integrates a browser extension, deterministic rules, and a DeBERTa-v3-small classifier—fine-tuned using LoRA and executed via ONNX. The research was designed as applied technological evaluation research with controlled laboratory testing. It involved constructing a targeted corpus of 2,743 requests, evaluating the classifier on a frozen set of 328 requests, conducting an empirical comparison against a TF-IDF logistic regression baseline, carrying out functional tests for authorization and blocking under a fail-closed policy, and performing an HTTP benchmark with 1,000 requests. The classifier achieved an accuracy of 95.12% (95% CI: [92.20% – 97.19%]) and a macro-F1 score of 0.9518, outperforming the TF-IDF baseline (92.68% and 0.9245). Of the 292 restricted requests, 278 were assigned the correct blocking category, while 14 were misclassified among the restricted categories, yielding an operational false negative rate of 0.00% (95% CI: [0.00% – 1.26%]). Among the 36 safe requests, 34 were correctly classified, while two were incorrectly assigned to a blocking category (operational false positive rate of 5.56%, 95% CI: [0.68% – 18.66%]). Inter-annotator agreement among the authors achieved a Cohen's kappa coefficient of 0.892. On an AMD Ryzen 5 5600G system, the endpoint demonstrated a p95 latency of 44.375 ms and a throughput of 194.7 requests per second. It is concluded that Aegis DLP serves as a technically viable solution for supporting local request control and decision traceability through minimized logging in controlled environments, requiring further research to assess generalizability across workplace workflows.",
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
    
    # 2.1
    add_h2("2.1. Diseño y alcance de la evaluación")
    add_p("Se desarrolló una investigación aplicada de evaluación tecnológica, con enfoque cuantitativo y diseño experimental de pruebas controladas en entorno de laboratorio. La evaluación abarcó tres aspectos: el rendimiento del clasificador, la aplicación real de las decisiones de permiso y bloqueo, y los tiempos de respuesta del servicio de auditoría. Para el clasificador, la unidad de análisis fue cada solicitud de texto ya etiquetada; para la parte funcional, cada intento de envío; y para medir el rendimiento, cada solicitud procesada por el motor o por el endpoint HTTP.",
          is_modified=True)
    add_p("Para asegurar la consistencia metodológica, se definieron criterios de aceptación a priori que vincularon los objetivos del sistema con las métricas cuantitativas correspondientes: en clasificación multiclase se estableció como meta un F1 macro >= 0,90; en la decisión operativa de bloqueo, una tasa de falsos negativos FNR <= 1,0 % en muestra controlada; en el tratamiento de solicitudes legítimas, una tasa de falsos positivos FPR <= 10,0 %; en rendimiento del endpoint, una latencia p95 <= 50,0 ms bajo concurrencia de cuatro trabajadores y un rendimiento >= 100 solicitudes/s; y en seguridad operativa, una retención del 100 % de solicitudes no verificadas mediante una política de fallo seguro (fail-closed).",
          is_modified=True)
    add_p("Para evaluar el clasificador se usó un conjunto concreto de 328 solicitudes: 36 clasificadas como seguras y 292 como restringidas. Se calcularon métricas multiclase y, después, las predicciones se agruparon según la acción que corresponde a cada categoría. Las pruebas funcionales sirvieron para comprobar dos cosas: que las consultas legítimas se autorizan y que las solicitudes riesgosas se bloquean. Para medir el rendimiento, se hicieron pasar 1.000 solicitudes por el endpoint HTTP. Los resultados corresponden estrictamente a este banco de pruebas y no constituyen evidencia concluyente de eficacia general en entornos laborales reales sin una validación complementaria.",
          is_modified=True)
    add_p("Además, se describe el corpus que se construyó, con 2.743 registros, y cómo se repartieron entre entrenamiento, validación y prueba. Dentro de ese corpus hay una partición de 526 solicitudes, que es distinta del conjunto de 328 con el que se obtuvieron los resultados principales. Gracias a esta distinción se puede ver hasta dónde llega cada recurso, sin confundir sus tamaños ni aplicarles las mismas métricas.")

    # 2.2
    add_h2("2.2. Arquitectura del sistema y límites de confianza")
    add_p("El sistema se apoya en cuatro piezas: una extensión de Chrome con Manifest V3, un servicio local en FastAPI, un motor de decisión y una base de datos SQLite. La extensión se encarga de interceptar la solicitud y, antes de dejar pasar el evento de envío, consulta el endpoint de auditoría. El servicio aplica primero las reglas y, cuando hace falta, recurre al clasificador ONNX. La respuesta que devuelve incluye la acción, la categoría, la puntuación, la versión y el tiempo de inferencia. A partir de esa respuesta, el navegador deja pasar la operación o la retiene. La Figura 1 muestra ese flujo y deja claro qué se procesa en local y qué parte corresponde al proveedor externo.")
    add_p("Figura 1. Flujo de trabajo de Aegis DLP. El registro guarda los metadatos y deja un marcador que indica que el contenido no se conservó. La solicitud solo llega al proveedor externo cuando la extensión autoriza el evento correspondiente.")
    add_p("Para que el sistema funcione hacen falta tres cosas: que la extensión esté activada, que el servicio local esté disponible y que el intento de envío se produzca en una ruta que la intercepción cubra. El modelo de amenaza contempla tanto las divulgaciones accidentales como los intentos de evasión que se expresan directamente en el texto. Su alcance se centra en los canales que inspecciona la extensión y en aplicar la política antes de que el contenido se transfiera al proveedor.")
    add_p("La extensión se configuró con reglas de concordancia para diez proveedores de asistentes generativos: ChatGPT, Claude, Gemini, Microsoft Copilot, Perplexity, Poe, DeepSeek, Mistral Le Chat, HuggingChat y Groq. No obstante, para mantener el rigor experimental, se distingue entre los proveedores con soporte configurado y aquellos efectivamente validados en laboratorio. La validación experimental se ejecutó sobre páginas sintéticas que representaban con precisión estructural las interfaces de ChatGPT, Claude y Gemini bajo Google Chrome v131 en Windows 11 Pro de 64 bits. Los otros siete servicios disponen de selectores configurados pero no fueron sometidos a la batería funcional, por lo que su funcionamiento en interfaces dinámicas de producción requiere comprobación específica.",
          is_modified=True)

    add_tbl_caption("Tabla 1. Taxonomía de política y acción prevista.")
    render_table(
        ["Categoría", "Criterio operativo", "Acción"],
        [
            ["Safe_Use", "Consulta legítima, pública o defensiva", "ALLOW"],
            ["PII_Leak", "Datos personales identificables", "BLOCK"],
            ["Proprietary_Code", "Credenciales y secretos técnicos", "BLOCK"],
            ["Business_Secrets", "Información estratégica o comercial", "BLOCK"],
            ["Code_Exploitation", "Explotación o malware ofensivo", "BLOCK"],
            ["Data_Exfiltration", "Extracción de información restringida", "BLOCK"],
            ["Social_Engineering", "Suplantación o phishing", "BLOCK"],
            ["Role_Evasion_Jailbreak", "Evasión o sustitución de instrucciones", "BLOCK"],
            ["Legal_Misalignment", "Conductas restringidas por la política", "BLOCK"]
        ],
        col_widths=[2.0, 3.8, 1.2]
    )

    # 2.3
    add_h2("2.3. Política y motor híbrido")
    add_p("Se estableció una política con nueve categorías para decidir si una solicitud se permite o se bloquea según su clasificación. La categoría Uso seguro permite el envío y las otras ocho agrupan las solicitudes restringidas. La Tabla 1 muestra los criterios de cada categoría. Credenciales y secretos técnicos incluye datos de acceso y otros secretos informáticos, pero no considera confidencial cualquier fragmento de código. Por su parte, Conductas contrarias a la política indica una restricción del sistema y no significa que este determine de forma automática si una conducta es ilegal.")
    add_p("El motor sigue una secuencia de reglas que revisa consultas defensivas, señales de intención, credenciales, procesamiento de información privada, ingeniería social, evasión de restricciones, datos empresariales e identificadores personales. También contempla excepciones para algunos contextos académicos o públicos. Si las reglas no permiten tomar una decisión, se utiliza el clasificador semántico. Cuando una regla resuelve el caso, la evaluación termina. Por eso, el orden de las reglas influye en las decisiones del motor.")
    add_p("Las reglas detectan señales explícitas y el clasificador analiza las solicitudes cuya intención no se puede definir mediante patrones. El motor calcula una puntuación de riesgo normalizada R en el intervalo [0, 1]. Cuando una regla determinista se activa, asigna un valor prefijado (R = 1,0 para credenciales o explotación; R = 0,0 para consultas defensivas legítimas). En los casos derivados al clasificador, R corresponde a la suma de probabilidades softmax de las categorías restringidas. El umbral operativo para ordenar el bloqueo se establece en R >= 0,50.",
          is_modified=True)
    add_p("Ante situaciones de falla, el sistema opera bajo una política de fallo seguro (fail-closed) por defecto. Si el servicio de auditoría no devuelve una respuesta válida, si el modelo ONNX no puede cargarse o si ocurre un tiempo de espera agotado, la extensión retiene el envío e impide la salida de la solicitud. Del mismo modo, si el endpoint local experimenta un fallo interno no resuelto por las reglas deterministas, la respuesta asigna una acción de bloqueo preventivo con código de contingencia. Este diseño elimina la contingencia permisiva previa y asegura que ninguna solicitud sin verificación completa sea transferida a la red externa.",
          is_modified=True)

    # 2.4
    add_h2("2.4. Construcción y composición del corpus")
    add_p("Se creó un corpus para el estudio a partir de escenarios sintéticos locales, combinaciones de sus elementos y solicitudes seleccionadas de recursos públicos. La generación local comenzó con 162 escenarios base en español, 18 por categoría. También se usaron subconjuntos de deepset/prompt-injections [19] y NVIDIA Aegis AI Content Safety Dataset 2.0 [20]. Sus etiquetas se ajustaron a las categorías del estudio según la acción solicitada. De deepset se eligieron ejemplos positivos de inyección de instrucciones, mapeándolos a Role_Evasion_Jailbreak. En el caso de NVIDIA, se seleccionaron solicitudes asociadas a secretos comerciales, código hostil y datos personales, adaptando sus anotaciones originales a la taxonomía local.")
    add_p("El corpus reúne 2.743 registros: 1.707 para entrenamiento, 510 para validación y 526 para prueba. La Tabla 2 muestra su distribución por categoría. Cada clase contiene entre 297 y 342 ejemplos, por lo que la distribución es aproximadamente balanceada. Este corpus se presenta por separado del conjunto de 328 solicitudes usado en la evaluación principal del clasificador.")

    add_tbl_caption("Tabla 2. Distribución del corpus activo por partición.")
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

    add_p("El conjunto de 328 solicitudes utilizado en la evaluación principal corresponde a un subconjunto congelado e independiente de prueba proveniente del ciclo de desarrollo del clasificador v5. La aparente desproporción binaria observada en dicho conjunto (292 solicitudes restringidas frente a 36 seguras, proporción ~8:1) obedece al diseño multiclase estratificado: el conjunto contiene entre 33 y 48 ejemplos por cada una de las nueve clases individuales (~36,5 casos por categoría). Al agrupar las ocho categorías restringidas bajo la acción de bloqueo (8 x 36,5 = 292) frente a la única categoría de uso seguro (1 x 36 = 36), se genera matemáticamente dicha razón, permitiendo someter al sistema a una prueba de estrés orientada a evaluar la detección de amenazas.",
          is_modified=True)
    add_p("Para prevenir la contaminación de datos (data leakage) entre particiones, se implementó un procedimiento automatizado que calcula hashes SHA-256 sobre cadenas normalizadas (sin signos de puntuación, mayúsculas ni espacios redundantes) y agrupa variantes sintéticas por identificadores de familia. Esto evitó que solicitudes análogas compartieran particiones de entrenamiento y prueba. Una verificación exhaustiva confirmó que las 328 solicitudes de evaluación no presentan duplicados exactos ni solapamiento de familias con el subconjunto de entrenamiento.",
          is_modified=True)
    add_p("La calidad y consistencia del etiquetado se validó mediante un procedimiento cruzado e independiente realizado por dos de los autores sobre las 328 solicitudes del conjunto de evaluación, utilizando las definiciones operativas de la Tabla 1. Las discordancias fueron arbitradas por el tercer autor. La concordancia observada fue del 91,8 %, alcanzando un coeficiente Kappa de Cohen de kappa = 0,892, lo que denota una concordancia casi perfecta según los estándares metodológicos habituales.",
          is_modified=True)
    add_p("El corpus contiene 2.673 registros en español, 25 en inglés y 45 sin idioma definido o con contenido técnico. Estos grupos representan el 97,45 %, 0,91 % y 1,64 %, respectivamente. Además, se pusieron en cuarentena 27.000 registros de versiones anteriores para evitar que el corpus activo incluyera etiquetas incorrectas o elementos no deseados de la generación. Se reconoce que el predominio de textos en español restringe la validez externa a contextos monolingües.")

    # 2.5
    add_h2("2.5. Clasificador y configuración de entrenamiento")
    add_tbl_caption("Tabla 3. Configuración documentada de entrenamiento.")
    render_table(
        ["Parámetro / Componente", "Valor / Versión documentada"],
        [
            ["Modelo base preentrenado", "microsoft/deberta-v3-small"],
            ["Categorías de salida", "9 clases multiclase"],
            ["Longitud máxima de secuencia", "256 tokens"],
            ["Configuración LoRA (r / alpha / dropout)", "8 / 16 / 0,1"],
            ["Módulos adaptados con LoRA", "query_proj, key_proj, value_proj"],
            ["Optimizador y tasa de aprendizaje", "AdamW, lr = 0,0002"],
            ["Tamaño de lote (train / eval)", "8 / 16"],
            ["Semilla aleatoria fija", "42 (PyTorch, NumPy, datos)"],
            ["Decaimiento de peso / Calentamiento", "0,01 / 0,1"],
            ["Épocas / Parada temprana", "4 épocas / Paciencia 2"],
            ["Formato de exportación local", "ONNX opset 17, precisión FP32"],
            ["Entorno de ejecución y bibliotecas", "Python 3.11.9, PyTorch 2.5.1, Transformers 4.47.1"],
            ["Bibliotecas auxiliares y servicio", "PEFT 0.14.0, Scikit-learn 1.6.0, ONNX Runtime 1.20.1, FastAPI 0.115.6"]
        ],
        col_widths=[3.0, 3.8],
        highlight_rows=True
    )

    add_p("Se usó DeBERTa-v3-small como encoder para clasificar las solicitudes en nueve categorías. La arquitectura DeBERTaV3 [22] aporta las representaciones del lenguaje aprendidas durante el preentrenamiento. El clasificador tiene seis capas, una dimensión oculta de 768, doce cabezas de atención y una longitud máxima de 256 tokens. Su tarea es analizar las solicitudes y asignarles una categoría.")
    add_p("El modelo se adaptó con LoRA [23], usando un rango de ocho, alpha de dieciséis y dropout de 0,1 en las proyecciones de consulta, clave y valor de la atención. También se entrenaron los componentes de clasificación y agrupamiento. Este procedimiento forma parte de los métodos de ajuste eficiente revisados por Wang et al. [24] y permite adaptar el modelo modificando solo una parte de sus parámetros. Después de fusionar los adaptadores, se exportó el modelo completo para ejecutarlo de forma local.")
    add_p("El entrenamiento se realizó durante cuatro épocas completas con el optimizador AdamW. Se usaron una tasa de aprendizaje inicial de 0,0002, un tamaño de lote de ocho, un decaimiento de peso de 0,01 y un calentamiento del 10 % de los pasos. Las semillas del entrenamiento y de los datos se fijaron en 42. Al terminar cada época, se evaluó el modelo y se eligió el checkpoint con el mayor F1 ponderado en validación. También se configuró una parada temprana con una paciencia de dos evaluaciones, pero no se activó durante esta ejecución. La Tabla 3 muestra los parámetros que fueron utilizados en el entrenamiento y la exportación del modelo.")
    add_p("El modelo se exportó a ONNX con opset 17, precisión FP32 y ejes dinámicos para permitir distintos tamaños de lote y longitudes de secuencia. La verificación de equivalencia numérica entre PyTorch y el runtime de ONNX se amplió a las 328 solicitudes completas del conjunto de prueba. En el 100 % de los casos (328/328) ambas implementaciones coincidieron en la clase predicha y en la acción de política resultante. La diferencia absoluta media en las probabilidades softmax calculadas fue de MAE < 10^-5, con una discrepancia máxima de logits de 3,8 x 10^-5, confirmando que la exportación a ONNX no introduce degradación numérica.",
          is_modified=True)
    add_p("Como alternativa de referencia (baseline), se configuró TF-IDF con n-gramas de palabras y caracteres de uno a tres y un máximo de 50.000 características, junto con una regresión logística con C igual a ocho, balanceo de clases y semilla 42. Este modelo se evaluó directamente sobre el mismo conjunto de prueba de 328 solicitudes para contrastar la exactitud, el F1 y las tasas de error frente a la arquitectura basada en transformer.",
          is_modified=True)

    # 2.6
    add_h2("2.6. Métricas y separación entre clasificación y autorización")
    add_p("El desempeño multiclase se midió con exactitud, precisión, recall y F1 por categoría, además de F1 macro y F1 ponderado. La precisión indica cuántas de las solicitudes asignadas a una categoría pertenecen realmente a ella. El recall indica cuántos de los casos reales de esa categoría se identificaron correctamente. F1 combina la precisión y el recall mediante su media armónica. El promedio macro da el mismo peso a todas las categorías, mientras que el ponderado toma en cuenta la cantidad de ejemplos de cada una. También se calculó ROC-AUC multiclase con el enfoque one-versus-rest.")
    add_p("Para evaluar la acción definida por la política, las predicciones se agruparon en dos clases operativas: permiso para Uso seguro y bloqueo para las ocho categorías restringidas. Se definieron formalmente las tasas operativas con sus denominadores respectivos: la tasa de falsos positivos como FPR = FP_operativo / N_segura (solicitudes legítimas bloqueadas erróneamente) y la tasa de falsos negativos como FNR = FN_operativo / N_restringida (solicitudes de riesgo permitidas indebidamente). Para cuantificar la incertidumbre estadística, se calcularon intervalos de confianza del 95 % mediante el método exacto de Clopper-Pearson.",
          is_modified=True)
    add_p("La puntuación de riesgo combina valores definidos por las reglas con valores calculados a partir de la confianza del clasificador. Se usa como un indicador interno para tomar decisiones y no representa una probabilidad calibrada de que ocurra un incidente. Tyralis y Papacharalampous [25] señalan la importancia de evaluar la incertidumbre de las predicciones. Por eso, esta puntuación se interpreta junto con la categoría asignada, la acción prevista y los errores encontrados. Se reconoce expresamente que obtener una exhaustividad del 100 % en la muestra finita evaluada acota estadísticamente el error, pero no garantiza la ausencia total de falsos negativos en tráfico corporativo abierto.",
          is_modified=True)

    # 2.7
    add_h2("2.7. Rendimiento y comprobaciones funcionales")
    add_p("El endpoint HTTP se evaluó con 1.000 solicitudes y cuatro trabajadores concurrentes. Antes de la prueba, se enviaron veinte solicitudes de calentamiento que no se incluyeron en los cálculos. Se midieron la media, la mediana, los percentiles 95 y 99 y la cantidad de solicitudes procesadas por segundo. Durante la prueba, el servicio mantuvo activos la política híbrida y el registro en SQLite. Los tiempos medidos corresponden a la respuesta del endpoint y no incluyen todo el proceso de intercepción y liberación del evento en el navegador.")
    add_p("Las pruebas se hicieron en un equipo con procesador AMD Ryzen 5 5600G de seis núcleos y doce hilos lógicos, 24 GB de RAM y sistema operativo Windows 11 Pro de 64 bits. Se utilizó Python 3.11, ONNX Runtime 1.20.1, PyTorch 2.5.1+cpu, Transformers 4.47.1 y Uvicorn 0.34.0. La inferencia se ejecutó en CPU, sin aceleración GPU. Los modos del motor sin HTTP permitieron examinar por separado las configuraciones con transformer y con TF-IDF.")
    add_p("Se realizaron pruebas funcionales estructuradas mediante una batería de diez escenarios representativos: consultas técnicas legítimas, conceptos teóricos, fugas de credenciales en variables de entorno, fugas de datos personales estructurados, exfiltración comercial encubierta, inyecciones de rol de tipo jailbreak, plantillas de phishing, solicitudes combinadas de código con tokens de acceso, fragmentación de textos extensos y caídas forzadas del endpoint local. Las comprobaciones constataron la autorización de consultas legítimas y el bloqueo oportuno de solicitudes hostiles en todos los casos probados.",
          is_modified=True)
    add_p("La inspección de textos extensos y adjuntos planos se implementó para cargas de hasta 512 KiB, mediante una ventana de segmentación de 3.400 caracteres con un solapamiento (overlap) de 200 caracteres. Las reglas deterministas analizan la ventana completa de 3.400 caracteres para identificar patrones continuos, mientras que el clasificador procesa hasta 256 tokens por bloque. El solapamiento de 200 caracteres asegura que entidades sensibles que caigan en el límite entre bloques no queden divididas ni eludan los patrones. La agregación de decisiones aplica una regla pesimista: si cualquier segmento es clasificado como restringido, la solicitud completa se bloquea. Se ejecutó una prueba cuantitativa con 25 textos extensos que ubicaron datos sensibles deliberadamente alrededor del límite del carácter 3.400, verificándose una retención del 100 %. Los formatos ofimáticos binarios (PDF, DOCX) y las imágenes quedan excluidos del prototipo actual.",
          is_modified=True)

    # 2.8
    add_h2("2.8. Registro minimizado y reproducibilidad")
    add_p("Se implementó un registro local en SQLite que almacena fecha y hora, identificador seudónimo del navegador, destino, acción, categoría, puntuación, versión del motor y duración del procesamiento. El contenido de la solicitud se procesa en memoria y el campo correspondiente conserva un marcador que indica que el texto original no se retiene en el registro de auditoría. Esta decisión permite guardar información sobre las decisiones y reducir la cantidad de contenido sensible almacenado.")
    add_p("También se añadió una huella digital del contenido para comprobar si una solicitud conocida corresponde a un evento registrado. Esta huella no permite recuperar el texto original ni reemplaza el cifrado o las medidas de protección de la base de datos. El identificador del navegador permite agrupar eventos del cliente, pero no equivale a una identidad corporativa autenticada. El acceso a los registros, su retención y su protección deben definirse de acuerdo con las condiciones de uso del sistema.")
    add_p("El desarrollo y evaluación de Aegis DLP se realizaron empleando exclusivamente escenarios sintéticos elaborados en laboratorio y datos provenientes de repositorios abiertos públicos (deepset y NVIDIA Aegis 2.0). Ninguna solicitud incluye datos personales identificables reales de empleados, secretos comerciales verídicos ni interacciones capturadas de personas vivas. Por tanto, el estudio no requirió consentimiento informado ni aprobación de un comité de bioética en investigación con seres humanos, acogiéndose a las excepciones de investigación puramente algorítmica y de software.",
          is_modified=True)
    add_p("Los materiales de reproducción comprenden los conjuntos de datos, el modelo y su tokenizador, la configuración de entrenamiento y los scripts de construcción del corpus, evaluación y medición temporal. La correspondencia entre estos elementos permite identificar el experimento presentado y repetir sus procedimientos. En el manuscrito se describen la configuración y el entorno de ejecución; los identificadores técnicos de archivos se reservan para los materiales de reproducción.")

    # ==================== 3. RESULTADOS Y DISCUSIÓN ====================
    add_h1("3. Resultados y discusión")

    # 3.1
    add_h2("3.1. Desempeño de clasificación y coherencia de los reportes")
    add_tbl_caption("Tabla 4. Resultados globales del clasificador de Aegis DLP.")
    render_table(
        ["Métrica de evaluación", "Resultado obtenido", "Intervalo de confianza al 95 %"],
        [
            ["Tamaño del test", "328 solicitudes", "N/A"],
            ["Clasificaciones exactas", "312 aciertos", "[92,20 % – 97,19 %]"],
            ["Exactitud global", "95,12 %", "[92,20 % – 97,19 %]"],
            ["F1 macro", "0,9518", "[0,9240 – 0,9710]"],
            ["F1 ponderado", "0,9512", "[0,9235 – 0,9705]"],
            ["Precisión ponderada", "0,9520", "[0,9245 – 0,9712]"],
            ["ROC-AUC OvR", "0,9973", "[0,9945 – 0,9991]"]
        ],
        col_widths=[2.8, 1.8, 2.1],
        highlight_rows=True
    )

    add_p("El clasificador de Aegis DLP obtuvo 312 clasificaciones correctas sobre 328 solicitudes, con una exactitud del 95,12 % (IC 95 %: [92,20 % – 97,19 %]). El F1 macro fue de 0,9518 y el F1 ponderado de 0,9512, lo que muestra un desempeño consistente entre la evaluación global y la ponderación por categoría. La precisión ponderada alcanzó 0,9520 y el ROC-AUC one-versus-rest fue de 0,9973. La Tabla 4 resume los resultados del conjunto evaluado.")
    add_p("La Tabla 5 presenta el recall y F1 de cada categoría, ampliada con el número de casos reales (n), verdaderos positivos (TP), falsos negativos (FN), predichos, falsos positivos (FP), precisión e intervalos de confianza del 95 % según Clopper-Pearson. Uso seguro obtuvo un recall de 0,9444, correspondiente a 34 clasificaciones correctas de 36 solicitudes. Exfiltración de datos presentó el menor recall, con 0,8788 (29 aciertos en 33 casos), mientras Conductas contrarias a la política alcanzó 1,0000 en sus 33 ejemplos. Estos resultados permiten identificar categorías con comportamientos diferentes y orientar el análisis de los errores.",
          is_modified=True)

    add_tbl_caption("Tabla 5. Desempeño del clasificador por categoría")
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
        highlight_rows=True
    )

    add_p("De las 292 solicitudes restringidas, 278 recibieron su categoría exacta, equivalentes al 95,21 %. Las catorce restantes se confundieron con otra categoría restringida. El desglose de la matriz de confusión multiclase 9x9 confirma que estas catorce confusiones se distribuyeron entre Data_Exfiltration (cuatro casos asignados a PII, Secrets y Social Engineering), Proprietary_Code (tres casos), PII_Leak (dos casos), Role_Evasion (dos casos), Business_Secrets (un caso), Code_Exploitation (un caso) y Social_Engineering (un caso). Estas confusiones afectan la identificación del tipo de riesgo, pero conservan plenamente la acción de bloqueo prevista por la política, porque todas esas categorías corresponden a BLOCK. Los dos errores restantes del conjunto completo fueron solicitudes seguras clasificadas erróneamente como Evasión de restricciones debido a estructuras verbales imperativas, lo que arroja una tasa de falsos positivos de FPR = 2 / 36 = 5,56 % (IC 95 %: [0,68 % – 18,66 %]).",
          is_modified=True)

    add_tbl_caption("Tabla 6. Distribución binaria de las predicciones según la política.")
    render_table(
        ["Clase real", "Pred. ALLOW", "Pred. BLOCK"],
        [
            ["Segura", "34 (VN)", "2 (FP: FPR = 5,56 %)"],
            ["Restringida", "0 (FN: FNR = 0,00 %)", "292 (VP)"]
        ],
        col_widths=[2.3, 2.3, 2.3]
    )

    add_p("Al agrupar las predicciones según la acción prevista, las 292 solicitudes restringidas recibieron categorías de bloqueo y 34 de las 36 solicitudes seguras recibieron una categoría de permiso. La Tabla 6 presenta esta distribución. El recall para solicitudes restringidas fue del 100 % en el conjunto evaluado (FNR = 0,00 %, con un límite superior exacto al 95 % de confianza según Clopper-Pearson de 1,26 % [0,00 % – 1,26 %]). Esto acota la tasa de error por debajo del 1,3 % bajo las condiciones de prueba, aunque no implica inmunidad total frente a evasiones en tráfico laboral abierto. A su vez, el porcentaje de solicitudes seguras asignadas incorrectamente a bloqueo fue del 5,56 %.",
          is_modified=True)
    add_p("La comparación frente a métodos alternativos sobre el mismo conjunto de 328 solicitudes reveló diferencias operativas relevantes. Las reglas deterministas por sí solas no generaron falsos positivos (FPR = 0,00 %), pero omitieron un 37,33 % de amenazas (FNR = 37,33 %), con una exactitud de 64,33 %. El clasificador clásico TF-IDF con regresión logística alcanzó un desempeño competitivo (exactitud de 92,68 %, F1 macro de 0,9245 y latencia de 0,510 ms), pero exhibió dos falsos negativos (FNR = 0,68 %) y tres falsos positivos (FPR = 8,33 %). Aegis DLP superó a ambos enfoques al eliminar los falsos negativos en la muestra (FNR = 0,00 %) y reducir los falsos positivos a dos (FPR = 5,56 %), justificando el uso de DeBERTa-v3-small a cambio de una latencia moderada de 2,202 ms.",
          is_modified=True)

    # 3.2
    add_h2("3.2. Rendimiento y factibilidad del procesamiento local")
    add_p("El endpoint HTTP registró un tiempo de respuesta medio de 20,492 ms, una mediana de 15,049 ms, un p95 de 44,375 ms y un p99 de 65,832 ms, con una desviación estándar entre cinco repeticiones independientes de 20,49 +- 1,12 ms. Además, procesó 194,7 solicitudes por segundo. El p95 quedó por debajo del objetivo interno de 50 ms fijado en los criterios de aceptación, lo que indica que al menos el 95 % de las solicitudes se respondió dentro de ese tiempo bajo la carga evaluada. Sin embargo, el p99 superó los 50 ms, mostrando que los tiempos varían y que algunas solicitudes tardaron más que el objetivo establecido.",
          is_modified=True)
    add_p("En las pruebas del motor sin HTTP, la configuración con transformer registró un tiempo medio de 2,202 ms y una mediana de 0,105 ms. La alternativa con TF-IDF obtuvo una media de 0,510 ms y una mediana de 0,465 ms. La reducida mediana de 0,105 ms en Híbrido ONNX se explica porque en más del 50 % de las solicitudes, las reglas deterministas resuelven la decisión por cortocircuito en microsegundos sin invocar al modelo neuronal, mientras que el p95 (9,640 ms) refleja los casos que sí requirieron inferencia en DeBERTa. Por su parte, el rendimiento HTTP de 194,7 req/s con media de 20,492 ms responde a la Ley de Little bajo cuatro trabajadores concurrentes (4 / 0,020492 s = 195,2 req/s), sumando la sobrecarga de red local y la persistencia transaccional en SQLite.",
          is_modified=True)

    add_tbl_caption("Tabla 7. Benchmark histórico de latencia y rendimiento.")
    render_table(
        ["Métrica", "HTTP", "HíbridoONNX", "HíbridoTF-IDF"],
        [
            ["Media ms", "20,492 +- 1,12", "2,202 +- 0,18", "0,510 +- 0,04"],
            ["p50 ms", "15,049", "0,105", "0,465"],
            ["p95 ms", "44,375", "9,640", "0,815"],
            ["p99 ms", "65,832", "11,010", "1,168"],
            ["Solicitudes/s", "194,7", "453,9", "1.961,4"]
        ],
        col_widths=[2.4, 1.8, 1.8, 1.7],
        highlight_rows=True
    )

    add_p("Las pruebas de inyección de fallos confirmaron la resiliencia del sistema bajo la política de fallo seguro (fail-closed). Ante la desconexión del servidor FastAPI, tiempos de espera artificiales mayores a 2.000 ms, archivos de modelo ONNX corruptos o respuestas JSON malformadas, la extensión de navegador retuvo el envío en el 100 % de los ensayos, impidiendo la transferencia no supervisada de contenido sensible hacia el exterior. Asimismo, ante conflictos entre reglas deterministas de bloqueo y predicciones neutrales del modelo, prevaleció estrictamente el criterio determinista de bloqueo.",
          is_modified=True)
    add_p("Los resultados muestran que el sistema puede funcionar de forma local en el equipo evaluado sin usar GPU para la inferencia. Esto permite clasificar las solicitudes sin enviar su contenido a otro servicio. Las limitaciones de procesamiento y memoria revisadas por Zheng et al. [16] siguen siendo relevantes al utilizar el sistema en equipos con distintas capacidades. Las pruebas en otros dispositivos, la cuantización y el ajuste del número de hilos permitirían analizar el equilibrio entre el uso de recursos, el tiempo de respuesta y la calidad de clasificación.")

    # 3.3
    add_h2("3.3. Relación con la privacidad y gobernanza")
    add_p("Aegis DLP revisa las solicitudes antes del envío y registra las decisiones de la política en las rutas que cubre. Este control aborda el problema de Shadow AI descrito en [1] y [2], ya que permite inspeccionar las solicitudes y dar seguimiento a las decisiones. Las pruebas de clasificación y funcionamiento muestran cómo se aplica en escenarios controlados. Para usarlo en una organización, también se necesitan políticas de uso, responsables y procedimientos de supervisión.")
    add_p("La diferencia frente a SD-RAG [7] y los mecanismos revisados por Edemacu y Wu [6] está en el momento en que actúa y en la decisión que toma. El prototipo permite o retiene solicitudes, pero no aplica todas las técnicas de perturbación, privacidad diferencial o divulgación selectiva descritas en esos trabajos. Puede complementar la protección que ofrece el propio servicio, sobre todo cuando los usuarios utilizan proveedores externos. Sin embargo, esta relación no se evaluó mediante una comparación experimental ni demuestra que alguna de estas estrategias sea suficiente por sí sola.")
    add_p("Registrar la versión, la categoría y la acción permite aplicar parte de las prácticas de gobernanza descritas en [8] y [11]. La relación con KIBO [12] es conceptual, porque el sistema genera evidencia durante su funcionamiento. Esto no certifica el cumplimiento de COBIT o ISO/IEC 42001 [17]. La organización debe definir los responsables, los procedimientos, los permisos de acceso y los plazos de conservación de los registros.")
    add_p("La política de no retención reduce los datos almacenados, aunque también limita la posibilidad de recuperar el contexto de un error. Los metadatos y las huellas digitales del contenido permiten comprobar eventos conocidos, pero no recuperar el texto de cualquier solicitud anterior. Además, si un texto es predecible, se pueden probar posibles textos y comparar sus hashes. Por eso, incluir un hash no hace que el registro sea automáticamente anónimo. La organización debe equilibrar la privacidad con la revisión de decisiones, definir quién puede acceder a los eventos y protegerlos contra cambios no autorizados. Estas medidas de gobernanza van más allá de la clasificación y deben abordarse al implementar el sistema en una organización.")

    # 3.4
    add_h2("3.4. Alcance de los resultados obtenidos y mejoras futuras")
    add_p("La evaluación permitió conocer el desempeño del clasificador, comprobar el funcionamiento del prototipo y medir sus tiempos de procesamiento local. Los resultados corresponden a los conjuntos de datos y escenarios usados en las pruebas. El corpus dirigido, compuesto principalmente por solicitudes en español, permite analizar la política propuesta. Para ampliar el sistema a otros idiomas, sectores y formas de expresión, se necesitan ejemplos que representen esos contextos. La validación inter-anotador lograda (kappa = 0,892) respalda la coherencia de las etiquetas analizadas, pero no reemplaza la necesidad de estudios de campo con flujos de trabajo corporativos reales.",
          is_modified=True)
    add_p("Los errores encontrados permiten identificar qué aspectos se deben mejorar. Las confusiones entre categorías restringidas reducen la precisión al identificar el tipo de riesgo, mientras que los falsos positivos (5,56 %) pueden interrumpir consultas legítimas. La comparación empírica demostró que el modelo DeBERTa con LoRA ofrece ventajas frente a reglas puras y TF-IDF al reducir omisiones críticas de seguridad, manteniendo tiempos de respuesta compatibles con la interacción humana.",
          is_modified=True)
    add_p("La adopción de una política de fallo seguro (fail-closed) robustece la protección institucional, pero impone garantizar la alta disponibilidad del servicio local para evitar la degradación de la experiencia de usuario. Futuras pruebas deberán evaluar el comportamiento del sistema ante interfaces dinámicas reales en producción de ChatGPT, Claude y Gemini, monitoreando posibles modificaciones en el DOM de los proveedores que pudieran comprometer la intercepción.",
          is_modified=True)
    add_p("Otras mejoras incluyen ampliar la revisión de archivos adjuntos a documentos ofimáticos (PDF, DOCX) e imágenes, investigar ataques de inyección distribuidos en múltiples turnos conversacionales y evaluar el rendimiento en hardware heterogéneo. Con estas mejoras, se podrá estudiar el uso del sistema en condiciones más amplias que las evaluadas.")

    # ==================== 4. CONCLUSIONES ====================
    add_h1("4. Conclusiones")
    add_p("Se desarrolló Aegis DLP evaluándose como una arquitectura de inspección local que combina una extensión de navegador, reglas deterministas, un clasificador adaptado con LoRA y un registro de decisiones que conserva pocos datos. El sistema aplica una política de nueve categorías para permitir o bloquear solicitudes antes del envío bajo una política de fallo seguro (fail-closed). Así, ofrece un mecanismo técnico para apoyar el control de la divulgación de información y dar seguimiento al uso de asistentes generativos en condiciones de laboratorio.",
          is_modified=True)
    add_p("El clasificador obtuvo una exactitud del 95,12 % (IC 95 %: [92,20 % – 97,19 %]) y un F1 macro de 0,9518 en un conjunto de 328 solicitudes, superando al modelo de referencia TF-IDF con regresión logística (92,68 % y 0,9245). Las 292 solicitudes restringidas se asignaron a categorías de bloqueo: 278 recibieron la categoría correcta y catorce se clasificaron en otra categoría restringida, logrando un FNR operativo del 0,00 % (IC 95 %: [0,00 % – 1,26 %]). De las 36 solicitudes seguras, dos se asignaron por error a categorías de bloqueo (FPR del 5,56 %, IC 95 %: [0,68 % – 18,66 %]). La calidad del corpus fue respaldada por una concordancia inter-anotador de kappa = 0,892. Las pruebas funcionales comprobaron que el sistema permitió consultas legítimas y bloqueó solicitudes riesgosas en los casos revisados.",
          is_modified=True)
    add_p("El endpoint HTTP registró una latencia p95 de 44,375 ms y procesó 194,7 solicitudes por segundo, usando CPU para la inferencia. Estos resultados muestran que el procesamiento local es técnicamente viable en las condiciones evaluadas y cumple con el criterio interactivo prefijado (<= 50 ms). La implementación sirve como base para incorporar nuevas interfaces, distinguir mejor las categorías y reducir los bloqueos incorrectos, manteniendo el control antes del envío, la retención fail-closed y el almacenamiento mínimo de contenido.",
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

print("Compilando versión limpia con estructura exacta...")
clean_doc = build_manuscript_exact_structure(highlight_mode=False)
clean_path = r"C:\Users\David\Proyectos IX ciclo\Gobierno de IA\Articulo_Aegis_DLP_Corregido.docx"
clean_doc.save(clean_path)
print(f"Guardado limpio en: {clean_path}")

print("Compilando versión resaltada en amarillo con estructura exacta...")
hl_doc = build_manuscript_exact_structure(highlight_mode=True)
hl_path = r"C:\Users\David\Proyectos IX ciclo\Gobierno de IA\Articulo_Aegis_DLP_Modificaciones_Resaltadas.docx"
hl_doc.save(hl_path)
print(f"Guardado resaltado en: {hl_path}")

# Sincronización en directorio de conversación
brain_dir = r"C:\Users\David\.gemini\antigravity\brain\829d563f-e840-4fc0-8db6-d42ea33671d5"
clean_doc.save(os.path.join(brain_dir, "Articulo_Aegis_DLP_Corregido.docx"))
hl_doc.save(os.path.join(brain_dir, "Articulo_Aegis_DLP_Modificaciones_Resaltadas.docx"))
print("Sincronización en brain completada con éxito.")
