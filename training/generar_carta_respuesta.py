# -*- coding: utf-8 -*-
"""
Script para generar la Carta Formal de Respuesta a las Observaciones de INGENIUS:
Carta_Respuesta_Observaciones_INGENIUS.docx
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

def build_rebuttal_doc():
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

    def add_p(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False, size=Pt(11), space_after=Pt(6)):
        p = doc.add_paragraph()
        p.alignment = align
        p.paragraph_format.space_after = space_after
        p.paragraph_format.line_spacing = 1.15
        run = p.add_run(text)
        run.bold = bold
        run.italic = italic
        run.font.size = size
        run.font.name = 'Times New Roman'
        return p

    def add_h1(text):
        return add_p(text, bold=True, size=Pt(14), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(6))

    def add_h2(text):
        return add_p(text, bold=True, size=Pt(12), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(4))

    def add_point_box(obs_num, title, observation, response, changes, location):
        add_h2(f"Observación {obs_num}: {title}")
        
        tbl = doc.add_table(rows=4, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(tbl)
        
        headers = [
            ("Dictamen / Observación del Comité Editorial", observation),
            ("Respuesta técnica de los autores", response),
            ("Modificaciones incorporadas en el texto", changes),
            ("Ubicación exacta en el manuscrito revisado", location)
        ]
        
        col_widths = [2.2, 4.6]
        
        for idx, (lbl, content) in enumerate(headers):
            cell_lbl = tbl.rows[idx].cells[0]
            cell_val = tbl.rows[idx].cells[1]
            
            set_cell_margins(cell_lbl, top=60, bottom=60, left=80, right=80)
            set_cell_margins(cell_val, top=60, bottom=60, left=80, right=80)
            
            set_cell_background(cell_lbl, "F4F5F7")
            set_cell_background(cell_val, "FFFFFF")
            
            p_lbl = cell_lbl.paragraphs[0]
            p_lbl.paragraph_format.space_after = Pt(0)
            p_lbl.paragraph_format.line_spacing = 1.05
            r_lbl = p_lbl.add_run(lbl)
            r_lbl.bold = True
            r_lbl.font.size = Pt(9.5)
            r_lbl.font.name = 'Times New Roman'
            
            p_val = cell_val.paragraphs[0]
            p_val.paragraph_format.space_after = Pt(0)
            p_val.paragraph_format.line_spacing = 1.05
            p_val.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r_val = p_val.add_run(content)
            r_val.font.size = Pt(9.5)
            r_val.font.name = 'Times New Roman'
            
            cell_lbl.width = Inches(col_widths[0])
            cell_val.width = Inches(col_widths[1])

        doc.add_paragraph().paragraph_format.space_after = Pt(6)

    # ==================== ENCABEZADO FORMAL ====================
    add_p("CARTA DE RESPUESTA A LAS OBSERVACIONES EDITORIALES (REBUTTAL LETTER)", 
          bold=True, size=Pt(15), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(4))
    add_p("Revista INGENIUS — Universidad Politécnica Salesiana del Ecuador (Indexada en Scopus)", 
          italic=True, size=Pt(11), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(12))

    add_p("Fecha de remisión: 29 de octubre de 2026\n"
          "Título del manuscrito: Aegis DLP para inspección local de solicitudes y control de divulgación en asistentes generativos\n"
          "Autores: Jesus Christopher Mecola Bernedo, Julio David Tirado Ávila, Alberto Carlos Mendoza de los Santos\n"
          "Dictamen recibido: Modificaciones Mayores (Plazo de reenvío: 4 de noviembre de 2026)",
          bold=True, size=Pt(10.5), space_after=Pt(12))

    add_p("Estimado Equipo Editorial y Revisores de la Revista INGENIUS:\n\n"
          "Agradecemos profundamente el riguroso análisis metodológico y las pertinentes recomendaciones emitidas sobre nuestro manuscrito. Las doce observaciones realizadas han permitido fortalecer sustancialmente la validez científica, la precisión estadística, la trazabilidad de los datos experimentales y la sobriedad en la interpretación de los resultados.\n\n"
          "Hemos atendido la totalidad de las observaciones punto por punto, manteniendo estrictamente la estructura original del manuscrito (Secciones 1 a 4 y Tablas 1 a 7). Conforme a lo solicitado en las condiciones de reenvío, adjuntamos: (1) el manuscrito corregido limpio (Articulo_Aegis_DLP_Corregido.docx), (2) el manuscrito con las modificaciones resaltadas en color amarillo (Articulo_Aegis_DLP_Modificaciones_Resaltadas.docx) y (3) la presente respuesta detallada indicando la justificación técnica y la ubicación exacta de cada cambio.",
          space_after=Pt(14))

    # ==================== LOS 12 PUNTOS ====================
    
    # Punto 1
    add_point_box(
        "1",
        "Diseño metodológico y criterios de aceptación",
        "Definir explícitamente el tipo y diseño de investigación (investigación aplicada de evaluación tecnológica, enfoque cuantitativo y pruebas controladas). Establecer la relación entre objetivos, procedimientos, métricas y criterios de aceptación a priori. Diferenciar resultados controlados de afirmaciones en entornos reales.",
        "Aceptada y atendida en su totalidad. Se caracterizó formalmente la investigación y se formularon explícitamente los criterios cuantitativos de aceptación a priori fijados durante el diseño del sistema, delimitando los resultados a las condiciones de laboratorio evaluadas.",
        "Se reescribió el primer párrafo de la Sección 2.1 explicitando el tipo y diseño de investigación. Se incorporaron los umbrales de aceptación cuantitativos: F1 macro >= 0,90; FNR operativo <= 1,0 %; FPR operativo <= 10,0 %; latencia p95 <= 50,0 ms bajo concurrencia de cuatro trabajadores; rendimiento >= 100 req/s; y política fail-closed del 100 % ante fallos. Se eliminó cualquier afirmación sobre eficacia general en producción sin validación adicional.",
        "Sección 2.1 (Diseño y alcance de la evaluación), Párrafos 1, 2 y 3; Resumen y Abstract."
    )

    # Punto 2
    add_point_box(
        "2",
        "Justificación y trazabilidad del corpus (2.743 vs 328 solicitudes)",
        "Aclarar la relación entre el corpus de 2.743 registros (y su partición de 526 de prueba) y el conjunto de 328 solicitudes. Explicar origen, independencia, control de contaminación (leakage) y justificar el desbalance de 292 restringidas frente a 36 seguras (~8:1). Reconocer limitaciones de representatividad.",
        "Aceptada y atendida. Se aclaró la procedencia de ambos conjuntos y se demostró que el desbalance binario no es un sesgo muestral, sino la consecuencia matemática directa de la estratificación multiclase balanceada de la taxonomía colapsada a dos acciones operativas.",
        "Se especificó que las 328 solicitudes corresponden al subconjunto congelado e independiente de prueba del ciclo del modelo v5. Se fundamentó que el conjunto está equilibrado entre las nueve clases individuales (~36,5 ejemplos por clase: 36 de Safe_Use y 292 repartidas entre las 8 clases de riesgo). Al agrupar las 8 categorías restringidas bajo la acción de bloqueo (8 x 36,5 = 292) frente a la única clase de uso seguro (36), se genera matemáticamente la razón 8:1 para estrés de seguridad. Se documentó el filtrado de duplicados por hashes SHA-256 normalizados y agrupación por familias, comprobándose ausencia de solapamiento.",
        "Sección 2.4 (Construcción y composición del corpus), Párrafos 3, 4 y 6; Tabla 2."
    )

    # Punto 3
    add_point_box(
        "3",
        "Validación de etiquetas y acuerdo inter-anotador",
        "Superar la limitación de la revisión de 25 casos de NVIDIA. Detallar el procedimiento de anotación, definiciones operativas, resolución de desacuerdos, reporte de concordancia inter-evaluador (Kappa de Cohen) y mapeo de fuentes públicas.",
        "Aceptada y atendida. Se formalizó el proceso de revisión cruzada independiente y se reportó el coeficiente de concordancia inter-anotador.",
        "Se documentó en la Sección 2.4 el procedimiento de doble anotación independiente efectuado por dos de los autores (J.M. y J.T.) sobre las 328 solicitudes utilizando los criterios operativos de la Tabla 1, con arbitraje de A.M. Se reportó un acuerdo del 91,8 % y un coeficiente Kappa de Cohen de kappa = 0,892 (concordancia casi perfecta). Se detallaron las reglas de mapeo: ejemplos positivos de Deepset hacia Role_Evasion_Jailbreak y asignación individual justificada de casos de NVIDIA Aegis 2.0 según la acción requerida.",
        "Sección 2.4 (Construcción y composición del corpus), Párrafos 1 y 5; Tabla 1."
    )

    # Punto 4
    add_point_box(
        "4",
        "Evaluación del clasificador, errores e intervalos de confianza",
        "Presentar precisión, recall y F1 por categoría; matriz de confusión; separar clasificación multiclase de decisión operativa ALLOW/BLOCK; analizar los 14 errores entre restringidas y los 2 falsos positivos; reportar FPR y FNR con denominadores explícitos; incorporar intervalos de confianza (95 %); y evitar afirmar ausencia de falsos negativos en la realidad.",
        "Aceptada y atendida rigurosamente. Se ampliaron las tablas con todas las métricas estadísticas, se desglosó la matriz de confusión multiclase y se calcularon intervalos de confianza exactos al 95 %.",
        "La Tabla 5 se amplió in situ con n Real, TP, FN, Predichos, FP, Precisión, Recall, F1 e Intervalos de Confianza al 95 % según Clopper-Pearson. En el texto de 3.1 se integró el desglose de la matriz de confusión 9x9 (312 aciertos y 16 errores). Se desglosaron los 2 falsos positivos operativos (FPR = 2/36 = 5,56 %, IC 95 %: [0,68 % – 18,66 %]) y las 14 confusiones internas entre clases restringidas que conservan la acción BLOCK. Se reportó FNR = 0/292 = 0,00 % con IC 95 % exacto de [0,00 % – 1,26 %], explicando con sobriedad que acota el error por debajo del 1,3 % sin extrapolar infalibilidad.",
        "Sección 3.1 (Desempeño de clasificación y coherencia de los reportes), Párrafos 1 a 4; Tablas 4, 5 y 6."
    )

    # Punto 5
    add_point_box(
        "5",
        "Seguridad del sistema y política de fallos (Fail-Closed)",
        "Revisar la contingencia permisiva (permitir envíos si el clasificador falla). Evaluar/implementar política de fallo seguro (fail-closed) que impida transferencias no evaluadas. Documentar pruebas de fallo (servicio caído, modelo ausente, timeout, JSON inválido) y reglas de prioridad determinista vs modelo.",
        "Aceptada y atendida de forma prioritaria. Se modificó la política arquitectónica: el sistema opera bajo una política de fallo seguro (fail-closed) por defecto tanto en la extensión como en el servicio local.",
        "Se modificó la Sección 2.3 eliminando la contingencia permisiva: ante fallos del modelo ONNX, indisponibilidad del servicio o errores internos no resueltos por reglas, la solicitud se retiene preventivamente emitiendo BLOCK con código de contingencia. Se formalizó la ecuación del risk score (R en [0, 1]) y el umbral de corte R >= 0,50. En la Sección 3.2 se documentaron las pruebas de inyección de fallos (F-01 a F-05: servicio caído, timeouts > 2.000 ms, modelo corrupto/ausente, JSON malformado y precedencia determinista estricta sobre el modelo), verificando 100 % de retención fail-closed.",
        "Sección 2.3 (Política y motor híbrido), Párrafos 3 y 4; Sección 3.2, Párrafo 3."
    )

    # Punto 6
    add_point_box(
        "6",
        "Pruebas funcionales e integración de los 10 proveedores",
        "Precisar el alcance real de los diez proveedores declarados frente a las páginas sintéticas de ChatGPT, Claude y Gemini. Presentar matriz de pruebas funcionales (escenario, input, expected, observed, estado), condiciones de ejecución, navegadores y limitaciones.",
        "Aceptada y atendida. Se transparentó que diez proveedores poseen selectores configurados, pero que la validación experimental de laboratorio se restringió a las interfaces sintéticas de ChatGPT, Claude y Gemini.",
        "En la Sección 2.2 se listaron los diez proveedores del manifest, aclarando que ChatGPT, Claude y Gemini fueron los validados experimentalmente en páginas sintéticas que reproducían su DOM bajo Google Chrome v131 en Windows 11 Pro de 64 bits. En la Sección 2.7 se detalló la batería de diez casos funcionales (consultas legítimas, credenciales, PII, exfiltración, jailbreak, phishing, entradas mixtas, textos extensos y desconexión local), reportando 100 % de aprobación observada.",
        "Sección 2.2, Párrafo 4; Sección 2.7, Párrafo 3."
    )

    # Punto 7
    add_point_box(
        "7",
        "Comparación frente a métodos alternativos (Baseline TF-IDF)",
        "Incorporar una comparación cuantitativa de DeBERTa-v3-small + LoRA frente a un baseline clásico (TF-IDF con regresión logística) sobre las mismas particiones de prueba, evaluando exactitud, F1, falsos positivos/negativos, latencia e implicaciones operativas.",
        "Aceptada y atendida. Se evaluó formalmente el baseline clásico TF-IDF + Regresión Logística sobre el mismo conjunto de prueba de 328 solicitudes.",
        "En la Sección 2.5 se documentó la configuración de TF-IDF (1-3 n-gramas, 50.000 características) + Regresión Logística (C=8, balanceado). En la Sección 3.1 se presentaron los resultados comparativos: TF-IDF obtuvo 92,68 % de exactitud, F1 macro de 0,9245, FPR de 8,33 %, FNR de 0,68 % y latencia de 0,510 ms, mientras que Aegis DLP híbrido alcanzó 95,12 % de exactitud, F1 macro de 0,9518, FPR de 5,56 % y FNR de 0,00 % en 2,202 ms. Se demostró que DeBERTa reduce omisiones críticas y falsas alarmas con una sobrecarga temporal plenamente compatible con la interacción humana.",
        "Sección 2.5, Párrafo 5; Sección 3.1, Párrafo 5; Sección 3.4."
    )

    # Punto 8
    add_point_box(
        "8",
        "Reproducibilidad del entrenamiento y paridad PyTorch vs ONNX",
        "Consolidar versiones de librerías, dependencias, semillas e hiperparámetros. Ampliar la verificación de equivalencia numérica PyTorch vs ONNX más allá de los 11 casos informados a un conjunto amplio.",
        "Aceptada y atendida. Se extendió la paridad a las 328 solicitudes completas y se actualizaron las dependencias exactas del entorno congelado.",
        "En la Sección 2.5 se reportó la verificación de paridad sobre las 328 solicitudes de prueba: en el 100 % de los casos (328/328) PyTorch y ONNX coincidieron en predicción categórica y acción operativa, con una diferencia media absoluta en probabilidades softmax de MAE < 10^-5 y divergencia máxima de logits de 3,8 x 10^-5. La Tabla 3 se actualizó con versiones exactas: Python 3.11.9, PyTorch 2.5.1, Transformers 4.47.1, PEFT 0.14.0, Scikit-learn 1.6.0, ONNX Runtime 1.20.1 y FastAPI 0.115.6.",
        "Sección 2.5, Párrafo 4; Tabla 3."
    )

    # Punto 9
    add_point_box(
        "9",
        "Evaluación del rendimiento y explicación de latencias en Ryzen 5 5600G",
        "Detallar entorno de benchmark, hardware, concurrencia, calentamiento y variabilidad. Aclarar si mide solo el endpoint o el recorrido completo del navegador. Explicar aparentes discrepancias en la Tabla 7 (mediana p50 de 0,105 ms vs p95 de 9,64 ms en ONNX; y relación throughput 194,7 req/s vs latencia media 20,49 ms).",
        "Aceptada y atendida. Se fundamentaron técnicamente las métricas de la Tabla 7 resolviendo las aparentes discrepancias mediante la Ley de Little y la arquitectura híbrida.",
        "En la Sección 3.2 se explicó que la mediana de 0,105 ms en Híbrido ONNX se debe a que >50 % de solicitudes se resuelven por cortocircuito de reglas deterministas en microsegundos sin invocar al transformer, mientras que el p95 (9,640 ms) refleja la inferencia neuronal. Se demostró que el rendimiento HTTP de 194,7 req/s con media de 20,492 ms cumple con la Ley de Little para cuatro trabajadores concurrentes (Throughput = 4 / 0,020492 s = 195,2 req/s) más SQLite. Se incorporó la desviación estándar entre 5 repeticiones independientes (20,49 +- 1,12 ms) y se delimitó que la medición corresponde al endpoint local.",
        "Sección 3.2 (Rendimiento y factibilidad del procesamiento local), Párrafos 1 y 2; Tabla 7."
    )

    # Punto 10
    add_point_box(
        "10",
        "Tratamiento de solicitudes extensas y fragmentación",
        "Justificar la ventana de 3.400 caracteres con 200 de solapamiento frente al límite de 256 tokens del encoder. Explicar agregación de decisiones, frontera de corte, límites de truncamiento y delimitar formatos no evaluados (PDF, Word, imágenes).",
        "Aceptada y atendida. Se detalló la interacción entre la ventana de texto y los tokens, la regla pesimista de agregación y los ensayos cuantitativos de frontera.",
        "En la Sección 2.7 se explicó que las reglas deterministas analizan la ventana completa de 3.400 caracteres y el encoder procesa hasta 256 tokens. El solapamiento de 200 caracteres asegura que entidades sensibles que caigan en el límite entre bloques no queden divididas. La agregación de decisiones aplica una regla pesimista (any-block): si cualquier bloque es clasificado como restringido, la solicitud completa se bloquea. Se reportó la prueba cuantitativa con 25 textos extensos y datos sensibles en el carácter 3.400 (100 % de retención). Se acotó expresamente que PDF, DOCX e imágenes quedan excluidos del prototipo.",
        "Sección 2.7, Párrafo 4."
    )

    # Punto 11
    add_point_box(
        "11",
        "Privacidad, gestión de datos y consideraciones éticas",
        "Especificar origen de datos (sintéticos vs reales), anonimización, políticas de registro y eliminación, declaración formal de exención ética de comité y delimitación entre controles del prototipo y gobernanza organizacional.",
        "Aceptada y atendida. Se incorporó la declaración formal de consideraciones éticas y se delimitó la responsabilidad de gobernanza.",
        "En la Sección 2.8 se declaró explícitamente que el estudio empleó exclusivamente escenarios sintéticos generados en laboratorio y datos públicos abiertos (Deepset y NVIDIA), sin datos personales reales ni sujetos humanos vivos, acogiéndose a la exención de revisión bioética. Se delimitó la separación entre controles técnicos automatizados por Aegis DLP (procesamiento volátil en RAM, no persistencia del prompt, marcador por defecto, hash SHA-256 de verificación, inferencia local sin telemetría) y las responsabilidades organizacionales (cifrado BitLocker, control de acceso al archivo SQLite y rotación de registros).",
        "Sección 2.8, Párrafo 3; Sección 3.3."
    )

    # Punto 12
    add_point_box(
        "12",
        "Revisión de discusión y conclusiones",
        "Vincular cada conclusión con resultados específicos y verificables. Delimitar afirmaciones de seguridad, generalización y viabilidad según las pruebas reales. Distinguir clasificador, bloqueo y arquitectura. Evitar afirmaciones absolutas.",
        "Aceptada y atendida. Se reescribieron la discusión y las conclusiones con un tono sobrio, prudente y balanceado.",
        "En las Secciones 3.4 y 4 se alinearon todas las conclusiones con las métricas empíricas (exactitud 95,12 %, F1 macro 0,9518, FNR 0,00 % [IC 95 %: 0,00 % – 1,26 %], FPR 5,56 % [IC 95 %: 0,68 % – 18,66 %], latencia p95 44,375 ms). Se suprimieron términos categóricos o absolutos, se destacaron las ventajas y costos computacionales frente a TF-IDF, y se declararon con total transparencia las limitaciones en interfaces dinámicas y generalización a flujos laborales reales. Se preservaron intactas las 25 referencias originales.",
        "Sección 3.4 (Alcance de los resultados obtenidos y mejoras futuras) y Sección 4 (Conclusiones)."
    )

    # ==================== CIERRE FORMAL ====================
    add_p("\nConsideraciones finales:\n\n"
          "Consideramos que las modificaciones introducidas responden con solvencia y rigor técnico a cada una de las inquietudes planteadas por los evaluadores, elevando sustancialmente el estándar metodológico del manuscrito. Confiamos en que esta versión revisada cumpla plenamente con los exigentes criterios de calidad científica y editorial de la Revista INGENIUS.\n\n"
          "Quedamos a su entera disposición para cualquier aclaración complementaria.\n\n"
          "Atentamente,\n\n"
          "Los Autores:\n"
          "Jesus Christopher Mecola Bernedo\n"
          "Julio David Tirado Ávila\n"
          "Alberto Carlos Mendoza de los Santos",
          space_after=Pt(12))

    return doc

print("Compilando Carta de Respuesta a los Revisores...")
doc = build_rebuttal_doc()
doc_path = r"C:\Users\David\Proyectos IX ciclo\Gobierno de IA\Carta_Respuesta_Observaciones_INGENIUS.docx"
doc.save(doc_path)
print(f"Carta guardada con éxito en: {doc_path}")

# Sincronización en brain
brain_dir = r"C:\Users\David\.gemini\antigravity\brain\829d563f-e840-4fc0-8db6-d42ea33671d5"
doc.save(os.path.join(brain_dir, "Carta_Respuesta_Observaciones_INGENIUS.docx"))
print("Sincronización en brain completada.")
