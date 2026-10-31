# -*- coding: utf-8 -*-
"""
Script para generar la Carta de Respuesta Exhaustiva a las Observaciones de INGENIUS:
Carta_Respuesta_Observaciones_INGENIUS.docx
Cubre de forma individual los 65 ítems desglosados en los 12 bloques.
"""

import os
import docx
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

def set_cell_margins(cell, top=60, bottom=60, left=80, right=80):
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

def build_exhaustive_rebuttal():
    doc = Document()
    
    for s in doc.sections:
        s.top_margin = Inches(0.98)
        s.bottom_margin = Inches(0.98)
        s.left_margin = Inches(0.79)
        s.right_margin = Inches(0.79)
        
    normal_style = doc.styles['Normal']
    normal_style.font.name = 'Times New Roman'
    normal_style.font.size = Pt(10.5)
    normal_style.font.color.rgb = RGBColor(0x11, 0x11, 0x11)
    normal_style.paragraph_format.line_spacing = 1.15
    normal_style.paragraph_format.space_after = Pt(4)

    def add_p(text, align=WD_ALIGN_PARAGRAPH.JUSTIFY, bold=False, italic=False, size=Pt(10.5), space_after=Pt(4)):
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
        return add_p(text, bold=True, size=Pt(13), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(6))

    def add_h2(text):
        return add_p(text, bold=True, size=Pt(11.5), align=WD_ALIGN_PARAGRAPH.LEFT, space_after=Pt(4))

    def add_item_box(item_code, title, requirement, response, action_taken, location):
        add_h2(f"Ítem {item_code} — {title}")
        
        tbl = doc.add_table(rows=4, cols=2)
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
        set_table_borders(tbl)
        
        headers = [
            ("Exigencia exacta del revisor", requirement),
            ("Respuesta técnica de los autores", response),
            ("Acción realizada en el manuscrito", action_taken),
            ("Ubicación exacta en el .docx", location)
        ]
        
        col_widths = [2.2, 4.6]
        
        for idx, (lbl, content) in enumerate(headers):
            cell_lbl = tbl.rows[idx].cells[0]
            cell_val = tbl.rows[idx].cells[1]
            
            set_cell_margins(cell_lbl, top=45, bottom=45, left=70, right=70)
            set_cell_margins(cell_val, top=45, bottom=45, left=70, right=70)
            
            set_cell_background(cell_lbl, "F4F5F7")
            set_cell_background(cell_val, "FFFFFF")
            
            p_lbl = cell_lbl.paragraphs[0]
            p_lbl.paragraph_format.space_after = Pt(0)
            p_lbl.paragraph_format.line_spacing = 1.05
            r_lbl = p_lbl.add_run(lbl)
            r_lbl.bold = True
            r_lbl.font.size = Pt(9)
            r_lbl.font.name = 'Times New Roman'
            
            p_val = cell_val.paragraphs[0]
            p_val.paragraph_format.space_after = Pt(0)
            p_val.paragraph_format.line_spacing = 1.05
            p_val.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            r_val = p_val.add_run(content)
            r_val.font.size = Pt(9)
            r_val.font.name = 'Times New Roman'
            
            cell_lbl.width = Inches(col_widths[0])
            cell_val.width = Inches(col_widths[1])

        doc.add_paragraph().paragraph_format.space_after = Pt(4)

    # ==================== ENCABEZADO ====================
    add_p("CARTA FORMAL DE RESPUESTA A LAS OBSERVACIONES EDITORIALES (REBUTTAL LETTER)", 
          bold=True, size=Pt(14), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(3))
    add_p("Desglose Exhaustivo Punto por Punto de los 65 Ítems (Bloques 1 al 12)", 
          italic=True, size=Pt(11), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(6))
    add_p("Revista INGENIUS — Universidad Politécnica Salesiana del Ecuador (Indexada en Scopus)", 
          bold=True, size=Pt(10), align=WD_ALIGN_PARAGRAPH.CENTER, space_after=Pt(10))

    add_p("Fecha: 29 de octubre de 2026\n"
          "Manuscrito: Aegis DLP para inspección local de solicitudes y control de divulgación en asistentes generativos\n"
          "Autores: Jesus Christopher Mecola Bernedo, Julio David Tirado Ávila, Alberto Carlos Mendoza de los Santos\n"
          "Dictamen: Modificaciones Mayores (Plazo de reenvío: 4 de noviembre de 2026)",
          bold=True, size=Pt(10), space_after=Pt(10))

    add_p("Estimado Equipo Editorial y Revisores de la Revista INGENIUS:\n\n"
          "Presentamos a continuación la respuesta exhaustiva y detallada a cada uno de los 65 ítems específicos derivados de las doce observaciones del dictamen editorial. Todas las observaciones han sido atendidas al 100 % mediante experimentos reproducibles, cálculos estadísticos formales, nuevas tablas y ajustes textuales sobrios y empíricos en el manuscrito revisado.",
          space_after=Pt(10))

    # ==================== BLOQUE 1 ====================
    add_h1("Bloque 1: Fortalecimiento del diseño metodológico y coherencia de la investigación")
    
    add_item_box(
        "1.1", "Tipo y diseño de investigación",
        "Definir explícitamente el tipo y diseño de investigación (investigación aplicada de evaluación tecnológica, enfoque cuantitativo y pruebas controladas).",
        "Aceptada y atendida. Se caracterizó formalmente la investigación justificando el diseño experimental.",
        "Se reescribió el primer párrafo de la Sección 2.1 declarando textualmente que el estudio corresponde a una investigación aplicada de evaluación tecnológica, cuantitativa y con diseño experimental de pruebas controladas en laboratorio, manipulando variables independientes de entrada sin usuarios en producción.",
        "Sección 2.1, Párrafo 1; Resumen y Abstract."
    )
    
    add_item_box(
        "1.2", "Relación entre objetivos, procedimientos, métricas y criterios",
        "Establecer la relación formal entre objetivos de investigación, procedimientos experimentales, métricas y criterios de aceptación.",
        "Aceptada y atendida. Se formuló la Matriz de Coherencia Metodológica que sistematiza el estudio.",
        "Se añadió la Tabla 1 en la Sección 2.1 con 5 columnas que vincula cada uno de los 5 objetivos específicos con el componente evaluado, procedimiento, métricas cuantitativas y criterio de éxito.",
        "Sección 2.1, Párrafo 2; Tabla 1."
    )

    add_item_box(
        "1.3", "Criterios de aceptación explícitos para las 4 dimensiones",
        "Precisar los criterios de aceptación cuantitativos para clasificación, bloqueo restringido, solicitudes seguras y rendimiento.",
        "Aceptada y atendida. Se definieron formalmente los umbrales antes de presentar resultados.",
        "Se definieron en la Sección 2.1 y Tabla 1 los cuatro criterios: Multiclase (Exactitud >= 90 %, F1 macro >= 0,90); Bloqueo (FNR operativo <= 1,0 % y retención 100 % fail-closed); Solicitudes seguras (FPR operativo <= 10,0 %); Rendimiento (latencia p95 <= 50 ms bajo 4 workers y throughput >= 100 req/s).",
        "Sección 2.1, Párrafo 2; Tabla 1."
    )

    add_item_box(
        "1.4", "Diferenciación entre pruebas controladas y entornos reales",
        "Diferenciar claramente los resultados obtenidos en pruebas controladas de afirmaciones sobre efectividad en entornos reales.",
        "Aceptada y atendida. Se acotaron todas las afirmaciones al banco de pruebas controlado de laboratorio.",
        "Se cambió 'aplicación real' por 'aplicación operativa en entorno controlado' en la Sección 2.1, y se aclaró en 2.1 y Sección 4 que las pruebas demuestran funcionamiento en laboratorio y no constituyen evidencia concluyente en tráfico organizacional real.",
        "Sección 2.1, Párrafo 3; Sección 4; Resumen."
    )

    # ==================== BLOQUE 2 ====================
    add_h1("Bloque 2: Justificación y trazabilidad del corpus de datos")

    add_item_box(
        "2.1", "Origen, generación, selección y composición (2.743 vs 328 solicitudes)",
        "Explicar el origen, procedimiento de generación, criterios de selección y composición de los 2.743 registros y la procedencia de las 328 solicitudes.",
        "Aceptada y atendida. Se desglosó la procedencia de ambos conjuntos y el rol de cada partición.",
        "En la Sección 2.4 se incorporó la Tabla 5 con el desglose por fuentes (162 escenarios expandidos, Deepset, NVIDIA). Se explicó que los 526 de prueba de la Tabla 4 fueron la partición de desarrollo interno del corpus, y se detalló la selección del conjunto congelado de 328 casos del modelo v5.",
        "Sección 2.4, Párrafos 2, 3 y 4; Tablas 4 y 5."
    )

    add_item_box(
        "2.2", "Independencia de las 328 solicitudes respecto a entrenamiento y prueba",
        "Indicar si las 328 solicitudes son completamente independientes del corpus de entrenamiento o si comparten familias.",
        "Aceptada y atendida. Se verificó la separación por familias/escenarios para garantizar independencia.",
        "Se declaró en la Sección 2.4 que las 328 solicitudes fueron seleccionadas para evaluación desacoplada del modelo v5, asegurando separación a nivel de familias y escenarios disjuntos.",
        "Sección 2.4, Párrafos 4 y 5."
    )

    add_item_box(
        "2.3", "Procedimientos para detectar duplicados y similitud semántica",
        "Describir procedimientos aplicados para detectar y eliminar duplicados y ejemplos semánticamente similares que produzcan contaminación.",
        "Aceptada y atendida. Se documentó el protocolo de auditoría en 3 niveles.",
        "Se detalló en la Sección 2.4 la auditoría en 3 niveles: (1) deduplicación exacta y normalizada con SHA-256; (2) deduplicación cuasi-exacta por Jaccard en n-gramas de caracteres (n=3..5) con umbral >= 0,85; y (3) verificación de no solapamiento de familias sintéticas.",
        "Sección 2.4, Párrafo 5."
    )

    add_item_box(
        "2.4", "Revisión de partición y re-evaluación en caso de coincidencias",
        "Revisar partición y realizar nueva evaluación con datos independientes si se identifican dependencias.",
        "Aceptada y atendida. La auditoría ejecutada constató cero fugas de datos.",
        "Se reportó en la Sección 2.4 y 3.1 que la auditoría arrojó 0 duplicados exactos y 0 pares sobre el umbral de contaminación entre los 1.707 de entrenamiento y las 328 solicitudes de evaluación.",
        "Sección 2.4, Párrafo 5; Sección 3.1, Párrafo 1."
    )

    add_item_box(
        "2.5", "Justificación de la proporción 292 restringidas vs 36 seguras (8:1)",
        "Justificar la distribución de 292 restringidas y 36 seguras en las 328 solicitudes y su impacto en las métricas.",
        "Aceptada y atendida. Se demostró la justificación matemática de la estratificación colapsada a decisión binaria.",
        "En la Sección 2.4 y 2.6 se explicó que el conjunto fue balanceado uniformemente entre las 9 clases (~36,4 por categoría). Al colapsar 8 clases en BLOCK frente a 1 en ALLOW, surge matemáticamente la razón 8:1 (292:36). Se demostró que una prevalencia del 89,02 % infla la exactitud binaria (99,39 %), por lo que la evaluación debe juzgarse mediante tasas condicionales independientes de prevalencia (TPR = 100 %, FPR = 5,56 %).",
        "Sección 2.4, Párrafo 4; Sección 2.6, Párrafo 1; Sección 3.1.2."
    )

    add_item_box(
        "2.6", "Limitaciones de representatividad del conjunto evaluado",
        "Reconocer explícitamente limitaciones de representatividad y evitar generalizar a solicitudes laborales reales.",
        "Aceptada y atendida. Se explicitaron tres limitaciones estructurales de representatividad.",
        "Se detallaron en 2.4 y 3.4 tres limitaciones: (1) prevalencia empresarial inversa (>95 % legítimas, <5 % DLP), donde un FPR = 5,56 % generaría alto volumen de falsas alarmas diarias; (2) predominio del español (97,45 %) y longitud acotada; y (3) ausencia de jerga interna específica de una empresa real.",
        "Sección 2.4, Párrafo 8; Sección 3.4, Párrafo 2."
    )

    # ==================== BLOQUE 3 ====================
    add_h1("Bloque 3: Validación de las etiquetas y calidad de la anotación")

    add_item_box(
        "3.1", "Procedimiento de anotación, instrucciones y definiciones operativas",
        "Detallar procedimiento de anotación, instrucciones, definiciones operativas de cada categoría y criterios de clasificación.",
        "Aceptada y atendida. Se formalizó la taxonomía completa con reglas operativas e indicadores.",
        "Se amplió la Tabla 3 en la Sección 2.2 incluyendo para cada una de las 9 categorías: definición operativa completa, indicadores de activación, regla de exclusión/contexto defensivo y regla de precedencia ante riesgos concurrentes.",
        "Sección 2.2; Tabla 3."
    )

    add_item_box(
        "3.2", "Quiénes anotaron y cómo se resolvieron desacuerdos",
        "Identificar quiénes realizaron la anotación y explicar resolución de casos ambiguos o desacuerdos.",
        "Aceptada y atendida. Se detalló el rol de los tres autores en el proceso de curaduría.",
        "Se especificó en la Sección 2.4 que dos autores con formación en ciberseguridad y NLP (J.M. y J.T.) realizaron la anotación independiente conforme al libro de códigos de la Tabla 3, y los desacuerdos fueron dirimidos mediante adjudicación por el tercer autor (A.M.).",
        "Sección 2.4, Párrafo 6."
    )

    add_item_box(
        "3.3", "Ampliación de la validación independiente de etiquetas",
        "Ampliar validación de etiquetas mediante revisión independiente de una muestra apropiada.",
        "Aceptada y atendida. Se realizó validación por doble anotador ciego.",
        "Se ejecutó una validación independiente sobre las 328 solicitudes completas de evaluación, superando el tamaño requerido para un nivel de confianza del 95 % con margen de error < 5 %.",
        "Sección 2.4, Párrafo 6."
    )

    add_item_box(
        "3.4", "Medida de concordancia entre evaluadores (Kappa de Cohen)",
        "Reportar medida de concordancia entre evaluadores (Kappa de Cohen) si corresponde.",
        "Aceptada y atendida. Se calcularon los coeficientes multiclase y binario.",
        "Se reportó en la Sección 2.4 un porcentaje de acuerdo del 91,8 %, un coeficiente Kappa de Cohen multiclase de kappa = 0,892 y un Kappa binario de kappa = 0,935, confirmando concordancia casi perfecta.",
        "Sección 2.4, Párrafo 6; Resumen."
    )

    add_item_box(
        "3.5", "Adaptación de etiquetas de datasets públicos (Deepset y NVIDIA)",
        "Explicar cómo se adaptaron etiquetas de datasets públicos y controles de compatibilidad con Aegis DLP.",
        "Aceptada y atendida. Se incorporó la Tabla de Homologación Taxonómica.",
        "Se presentó la Tabla 5 en la Sección 2.4 detallando el mapeo unívoco de deepset a Role_Evasion_Jailbreak y la correspondencia justificada de NVIDIA hacia PII_Leak, Proprietary_Code y Code_Exploitation.",
        "Sección 2.4, Párrafo 3; Tabla 5."
    )

    # ==================== BLOQUE 4 ====================
    add_h1("Bloque 4: Evaluación del clasificador y presentación de resultados")

    add_item_box(
        "4.1", "Matriz de confusión completa y Precisión, Recall y F1 por categoría",
        "Incorporar matriz de confusión y presentar por categoría precisión, recall y F1.",
        "Aceptada y atendida. Se expandió la Tabla 9 con métricas completas e IC y se integró la matriz 9x9.",
        "La Tabla 9 presenta n Real, TP, FN, Predichos, FP, Precisión, Recall, F1 e IC 95 % para las 9 clases. La Tabla 10 presenta la matriz de confusión 9x9 con los 312 aciertos y 16 errores.",
        "Sección 3.1.1; Tablas 9 y 10."
    )

    add_item_box(
        "4.2", "Diferenciar desempeño multiclase vs decisión operativa binaria",
        "Diferenciar desempeño multiclase del desempeño operativo final de permitir o bloquear.",
        "Aceptada y atendida. Se estructuró la Sección 3.1 en dos bloques independientes.",
        "Se dividió la Sección 3.1 en: 3.1.1 Desempeño intrínseco del clasificador multiclase (9 categorías) y 3.1.2 Desempeño en la decisión operativa binaria (ALLOW vs. BLOCK), explicando que la multiclase aporta trazabilidad en SQLite y la binaria gobierna el DOM.",
        "Sección 3.1.1 y Sección 3.1.2."
    )

    add_item_box(
        "4.3", "Análisis explícito de los 14 errores inter-restringidos y 2 casos seguros",
        "Analizar explícitamente los 14 casos confundidos entre categorías restringidas y los 2 casos seguros bloqueados.",
        "Aceptada y atendida. Se analizó la naturaleza semántica de los 16 errores observados.",
        "Se desglosaron en 3.1.1 los 14 errores inter-restringidos (4 en Data_Exfiltration, 3 en Proprietary_Code, 2 en PII_Leak, etc.), explicando que comparten señales semánticas y conservan la acción BLOCK. Los 2 falsos positivos se atribuyeron a estructuras imperativas benignas.",
        "Sección 3.1.1, Párrafo 4."
    )

    add_item_box(
        "4.4", "Tasas de Falsos Positivos (FPR) y Falsos Negativos (FNR) con denominadores",
        "Reportar FPR y FNR correspondientes a la decisión operativa definiendo claramente denominadores.",
        "Aceptada y atendida. Se formalizaron las ecuaciones y valores en la Tabla 11.",
        "En 2.6 y 3.1.2 se definieron formalmente: FPR = FP/(FP+TN) = 2/36 = 5,56 % sobre solicitudes seguras; y FNR = FN/(TP+FN) = 0/292 = 0,00 % sobre solicitudes restringidas.",
        "Sección 2.6, Párrafo 1; Sección 3.1.2; Tabla 11."
    )

    add_item_box(
        "4.5", "Intervalos de confianza (IC 95 %) para métricas principales",
        "Incorporar intervalos de confianza u otra estimación de incertidumbre para las métricas principales.",
        "Aceptada y atendida. Se incorporaron intervalos de Clopper-Pearson y Bootstrap.",
        "Se reportaron en Tablas 8, 9 y 11: Exactitud [92,20 % – 97,19 %]; FNR [0,00 % – 1,26 %]; TPR [98,74 % – 100,00 %]; FPR [0,68 % – 18,66 %]; TNR [81,34 % – 99,32 %]; y F1 macro [0,9240 – 0,9710].",
        "Sección 3.1.1 y 3.1.2; Tablas 8, 9 y 11."
    )

    add_item_box(
        "4.6", "Interpretación prudente del 100 % de exhaustividad (0 falsos negativos)",
        "Evitar interpretar exhaustividad del 100 % en el test como prueba de que no habrá falsos negativos en la realidad.",
        "Aceptada y atendida. Se aplicó la fundamentación estadística de Hanley-Lippman.",
        "En 3.1.2 se explicó que 0 FN en 292 ensayos solo acota con 95 % de confianza que la tasa real es <= 1,26 % (regla 3/n), y que ante entradas fuera de distribución o ataques avanzados sí ocurrirán falsos negativos.",
        "Sección 3.1.2, Párrafo 2."
    )

    add_item_box(
        "4.7", "Justificación de selección de métricas en relación con riesgos DLP",
        "Justificar selección de métricas y explicar cómo se relacionan con los riesgos a prevenir.",
        "Aceptada y atendida. Se vinculó cada métrica con su impacto operativo.",
        "Se detalló en 2.6 que FNR mide el riesgo de fuga no contenida (máxima severidad); FPR mide denegación de servicio interna y fricción; y F1 macro mide fidelidad forense en auditoría SQLite.",
        "Sección 2.6, Párrafo 2."
    )

    # ==================== BLOQUE 5 ====================
    add_h1("Bloque 5: Seguridad del sistema y tratamiento de fallos")

    add_item_box(
        "5.1", "Explicar y justificar política ante indisponibilidad de componentes",
        "Explicar y justificar política aplicada cuando clasificador o servicio no está disponible.",
        "Aceptada y atendida. Se unificó la política bajo el principio de fallo seguro.",
        "En la Sección 2.3 se explicó por qué se eliminó la contingencia permisiva previa y se unificó la arquitectura bajo el principio de fallo seguro (fail-closed) en extensión y backend.",
        "Sección 2.3, Párrafo 4."
    )

    add_item_box(
        "5.2", "Evaluar política Fail-Closed vs Fail-Open",
        "Evaluar política de fallo seguro (fail-closed) que impida transferencias no evaluadas.",
        "Aceptada y atendida. Se implementó fail-closed como modo obligatorio.",
        "Se estableció BLOCK_ON_ERROR como respuesta predeterminada ante caídas del modelo o API, documentando la comparativa técnica: riesgo de fuga = 0 a costa de interrupciones transitorias.",
        "Sección 2.3, Párrafo 4."
    )

    add_item_box(
        "5.3", "Pruebas de fallos de servicio, modelo, comunicación, timeout y respuestas",
        "Incorporar pruebas de fallos de servicio, modelo, timeouts y respuestas inválidas.",
        "Aceptada y atendida. Se ejecutó una batería de seis escenarios de inyección de fallos.",
        "Se implementaron y ejecutaron los escenarios F-01 a F-06: FastAPI apagado, modelo ONNX inaccesible, socket cortado, timeout > 2.000 ms, JSON malformado y SQLite bloqueado.",
        "Sección 2.7; Sección 3.2; Tabla 14."
    )

    add_item_box(
        "5.4", "Documentar comportamiento esperado y observado en fallos",
        "Documentar comportamiento esperado y observado en cada fallo (permitir, bloquear, pendiente).",
        "Aceptada y atendida. Se incorporó la Tabla de Resiliencia y Fallo Seguro.",
        "La Tabla 14 en la Sección 3.2 detalla componente afectado, mecanismo de contingencia, decisión esperada, observada y estado retenido para los 6 escenarios.",
        "Sección 3.2; Tabla 14."
    )

    add_item_box(
        "5.5", "Priorización de reglas deterministas frente al clasificador",
        "Explicar cómo se priorizan reglas deterministas frente al clasificador y resolución de contradicciones.",
        "Aceptada y atendida. Se formalizó la jerarquía de evaluación en tres niveles.",
        "En la Sección 2.3 se formalizó: Prioridad 1 (Bloqueo duro determinista por credenciales/PII estructurada, prevaleciendo sobre contextos defensivos); Prioridad 2 (Patrones de ataque explícito); y Prioridad 3 (Inferencia semántica DeBERTa).",
        "Sección 2.3, Párrafo 2."
    )

    add_item_box(
        "5.6", "Umbrales de decisión y cálculo/interpretación de niveles de riesgo",
        "Definir con precisión umbrales de decisión y cálculo de puntuaciones de riesgo.",
        "Aceptada y atendida. Se formalizó la formulación matemática de R(x).",
        "Se incorporó en 2.3 la ecuación R(x) = sum P(y=c|x) para clases restringidas, umbral operativo tau = 0,50, y la regla de baja confianza (P(Safe_Use|x) < 0,70 -> BLOCK).",
        "Sección 2.3, Párrafo 3."
    )

    add_item_box(
        "5.7", "Considerar pruebas de fallos en conclusiones de protección",
        "Considerar resultados de pruebas de fallos en las conclusiones de protección.",
        "Aceptada y atendida. Se condicionó la protección al funcionamiento fail-closed.",
        "En la Sección 4 se incorporó que la capacidad de contención depende críticamente de mantener activa la política fail-closed y la precedencia estricta de reglas deterministas sensibles.",
        "Sección 4 (Conclusiones), Párrafo 2."
    )

    # ==================== BLOQUE 6 ====================
    add_h1("Bloque 6: Pruebas funcionales e integración con proveedores")

    add_item_box(
        "6.1", "Matriz de pruebas funcionales (escenario, entrada, esperado, observado)",
        "Presentar matriz de pruebas funcionales que identifique escenario, entrada, esperado, observado y criterio.",
        "Aceptada y atendida. Se incorporó la Tabla 15 con la batería representativa.",
        "La Tabla 15 en la Sección 3.2 detalla ID, escenario, payload representativo, resultado esperado en SQLite, resultado observado en navegador y estado aprobado.",
        "Sección 3.2; Tabla 15."
    )

    add_item_box(
        "6.2", "Pruebas de solicitudes seguras, restringidas, ambiguas, multi-tipo y combinadas",
        "Incluir pruebas de solicitudes seguras, restringidas, ambiguas, con múltiples datos sensibles y combinadas.",
        "Aceptada y atendida. Se cubrieron los cinco grupos de prueba requeridos.",
        "Se documentaron en 2.7 y Tabla 15 casos seguros, restringidos de las 8 clases, consultas defensivas ambiguas, entradas multi-tipo (PII + API key) y ataques combinados (jailbreak + código propietario).",
        "Sección 2.7, Párrafo 3; Tabla 15."
    )

    add_item_box(
        "6.3", "Escenarios adversariales/evasión, errores de interfaz y funcionamiento parcial",
        "Incorporar escenarios adversariales (ofuscación, Base64, context stuffing) y errores de interfaz.",
        "Aceptada y atendida. Se evaluaron técnicas de evasión y cambios de interfaz.",
        "En 2.7 se documentó la detección de Base64 y regex, reconociendo limitaciones honestas ante dilución de contexto (>2.000 caracteres de texto benigno rodeando un secreto) y validando eventos submit por teclado (Enter/Ctrl+Enter).",
        "Sección 2.7, Párrafo 3; Sección 3.4, Párrafo 2."
    )

    add_item_box(
        "6.4", "Especificar proveedores probados, solo configurados y evaluados sintéticamente",
        "Especificar qué proveedores fueron probados, cuáles configurados y cuáles evaluados sintéticamente.",
        "Aceptada y atendida. Se incorporó la Tabla 2 de Cobertura de Proveedores.",
        "La Tabla 2 distingue los 10 proveedores del manifest: ChatGPT, Claude y Gemini (validados en páginas sintéticas locales Chrome v131 Win11) frente a los 7 configurados.",
        "Sección 2.2, Párrafo 4; Tabla 2."
    )

    add_item_box(
        "6.5", "Versiones de navegador, condiciones de ejecución y limitaciones de integración",
        "Describir versiones de navegador, condiciones de ejecución, repetición y limitaciones.",
        "Aceptada y atendida. Se documentaron las condiciones técnicas de la extensión.",
        "En 2.2 y 2.7 se especificó Google Chrome v131 en Windows 11 Pro, 3 repeticiones independientes por caso y las limitaciones de selectores DOM y alcance exclusivo a web.",
        "Sección 2.2; Sección 2.7, Párrafos 2 y 3."
    )

    add_item_box(
        "6.6", "Cuantificar casos ejecutados y aprobados sin confundir configuración con validación",
        "Cuantificar casos ejecutados y aprobados evitando presentar configuración como validación.",
        "Aceptada y atendida. Se reportó el conteo exacto de pruebas funcionales.",
        "Se reportaron 330 casos de prueba funcional ejecutados sobre páginas sintéticas de los 3 proveedores, con 330 aprobados (100 %), recalcando que los 7 proveedores restantes no fueron validados funcionalmente.",
        "Sección 2.7, Párrafo 3; Sección 3.4."
    )

    # ==================== BLOQUE 7 ====================
    add_h1("Bloque 7: Comparación con métodos alternativos (Baseline TF-IDF)")

    add_item_box(
        "7.1", "Comparar DeBERTa-v3-small + LoRA frente a TF-IDF + Regresión Logística",
        "Incorporar comparación de DeBERTa-v3-small ajustado con LoRA frente a modelo de referencia TF-IDF.",
        "Aceptada y atendida. Se evaluó formalmente el baseline clásico.",
        "Se entrenó y evaluó TF-IDF (1-3 n-gramas, 50.000 features) + Regresión Logística (C=8, balanceado) y Reglas Deterministas solas en 2.5 y 3.1.2.",
        "Sección 2.5, Párrafo 5; Sección 3.1.2."
    )

    add_item_box(
        "7.2", "Ejecutar comparación sobre mismas particiones y con criterios equivalentes",
        "Ejecutar comparación sobre mismas particiones y criterios de evaluación equivalentes.",
        "Aceptada y atendida. Ambos modelos se evaluaron sobre el mismo conjunto de 328 solicitudes.",
        "Se evaluaron bajo métricas idénticas multiclase y binarias sobre las 328 solicitudes de prueba congeladas.",
        "Sección 2.5; Sección 3.1.2; Tabla 12."
    )

    add_item_box(
        "7.3", "Comparar Exactitud, F1, FP, FN, Latencia, Recursos e Implicaciones",
        "Comparar exactitud, F1, falsos positivos/negativos, latencia, recursos e implicaciones operativas.",
        "Aceptada y atendida. Se incorporó la Tabla 12 de Comparación Integral de Modelos.",
        "La Tabla 12 compara: Reglas solas, TF-IDF, DeBERTa LoRA y Motor Híbrido Completo en Exactitud, F1 macro, FPR, FNR, latencia media, p95, RAM y tamaño en disco, discutiendo las implicaciones operativas.",
        "Sección 3.1.2; Tabla 12."
    )

    add_item_box(
        "7.4", "Justificación en caso de no realizar la comparación",
        "Si no se realiza la comparación, justificar su ausencia y delimitar conclusiones.",
        "Aceptada y atendida. La comparación fue plenamente realizada.",
        "Al haberse ejecutado empíricamente la comparación en los Ítems 7.1–7.3, este punto queda superado con evidencia cuantitativa completa.",
        "Sección 3.1.2; Tabla 12."
    )

    # ==================== BLOQUE 8 ====================
    add_h1("Bloque 8: Reproducibilidad del entrenamiento y de la inferencia")

    add_item_box(
        "8.1", "Consolidar versiones de bibliotecas, dependencias, semillas e hiperparámetros",
        "Consolidar versiones de software, modelo, semilla aleatoria, optimizador e hiperparámetros.",
        "Aceptada y atendida. Se consolidó la ficha técnica completa en la Tabla 6.",
        "La Tabla 6 en la Sección 2.5 detalla checkpoint Hugging Face, parámetros LoRA, parámetros AdamW (beta1=0,9, beta2=0,999, eps=1e-8), warmup lineal, hardware Ryzen 5 5600G y versiones congeladas de todas las librerías.",
        "Sección 2.5; Tabla 6."
    )

    add_item_box(
        "8.2", "Procedimiento de conversión PyTorch a ONNX y criterios de equivalencia",
        "Documentar conversión de PyTorch a ONNX y criterios utilizados para verificar equivalencia.",
        "Aceptada y atendida. Se describió el pipeline de exportación y criterios numéricos.",
        "En 2.5 se detalló: merge_and_unload() de LoRA, eval(), torch.onnx.export con opset 17 y dynamic_axes, check_model y los criterios de concordancia Top-1 y tolerancia MAE < 10^-5.",
        "Sección 2.5, Párrafo 3."
    )

    add_item_box(
        "8.3", "Ampliar validación de equivalencia PyTorch vs ONNX más allá de 11 casos",
        "Ampliar validación de equivalencia a un conjunto amplio de categorías y longitudes.",
        "Aceptada y atendida. Se evaluaron las 328 solicitudes completas de evaluación.",
        "En la Sección 2.5 se reportó la prueba de equivalencia ejecutada sobre las 328 solicitudes completas del conjunto de prueba.",
        "Sección 2.5, Párrafo 4."
    )

    add_item_box(
        "8.4", "Evaluación de diferencias en predicciones, etiquetas y puntuaciones",
        "Explicar diferencias entre predicciones, etiquetas y puntuaciones de confianza.",
        "Aceptada y atendida. Se reportaron métricas de fidelidad numérica.",
        "Se reportó Top-1 Label Agreement de 100,00 % (328/328), MAE en probabilidades softmax de 1,42 x 10^-6 (MAE < 10^-5) y divergencia máxima en logits de 3,8 x 10^-5.",
        "Sección 2.5, Párrafo 4."
    )

    add_item_box(
        "8.5", "Facilitar scripts, configuraciones, datos anonimizados o ejemplos reproducibles",
        "Facilitar scripts, configuraciones, datos anonimizados y ejemplos reproducibles.",
        "Aceptada y atendida. Se incorporó la declaración formal de disponibilidad.",
        "Se añadió en la Sección 2.8 el apartado de Disponibilidad de datos y código declarando el repositorio estructurado con scripts, pipeline ONNX, benchmark y corpus anonimizado.",
        "Sección 2.8, Párrafo 4."
    )

    # ==================== BLOQUE 9 ====================
    add_h1("Bloque 9: Evaluación del rendimiento y latencia")

    add_item_box(
        "9.1", "Entorno, versiones, hardware, carga, concurrencia y medición",
        "Precisar entorno, hardware, generación de carga, número de solicitudes, concurrencia y reloj.",
        "Aceptada y atendida. Se documentaron todos los detalles del banco de pruebas.",
        "En 2.7 se especificó el procesador Ryzen 5 5600G (6C/12T), 24 GB RAM, Windows 11 Pro, ONNX Runtime con 6 hilos intra-op, 4 workers en Uvicorn, ThreadPoolExecutor en localhost, 20 warmup y reloj time.perf_counter_ns().",
        "Sección 2.7, Párrafo 1."
    )

    add_item_box(
        "9.2", "Aclarar si mediciones corresponden solo al servicio o al flujo completo",
        "Explicar si mediciones corresponden solo a inferencia o al proceso completo desde navegador.",
        "Aceptada y atendida. Se delimitaron formalmente las tres capas temporales.",
        "En la Sección 2.7 y Tabla 13 se diferenciaron: Motor en memoria (evaluación directa sin HTTP ni SQLite), Endpoint HTTP de auditoría (FastAPI + bucle HTTP + motor + SQLite) e Intercepción en navegador (content script en DOM).",
        "Sección 2.7, Párrafo 2; Tabla 13."
    )

    add_item_box(
        "9.3", "Reportar mediana, percentiles de latencia y variabilidad entre ejecuciones",
        "Reportar mediana, percentiles y variabilidad entre ejecuciones.",
        "Aceptada y atendida. Se incorporó la desviación estándar y percentil 90.",
        "La Tabla 13 en la Sección 3.2 reporta media con desviación estándar (+- DE), p50, p90, p95, p99 y rendimiento sobre 5 corridas independientes.",
        "Sección 3.2, Párrafos 1 y 2; Tabla 13."
    )

    add_item_box(
        "9.4", "Aclarar discrepancias en estadísticas de latencia y separar etapas",
        "Aclarar discrepancias (p50 de 0,105 ms vs p95 de 9,64 ms en ONNX; y relación throughput vs media) y evitar comparar etapas distintas.",
        "Aceptada y atendida. Se fundamentaron matemáticamente las dos dinámicas.",
        "En 3.2 se explicó que la distribución de latencias en Híbrido ONNX es bimodal (mediana de 0,105 ms por cortocircuito de reglas en >50 % de casos y p95 de 9,64 ms por inferencia neuronal en CPU). Se demostró que el rendimiento HTTP de 194,7 req/s cumple la Ley de Little (Throughput = 4 / 0,020492 s = 195,2 req/s) para 4 clientes concurrentes más SQLite. La Tabla 13 separa visualmente el bloque A (HTTP) del bloque B (Memoria).",
        "Sección 3.2, Párrafo 2; Tabla 13."
    )

    add_item_box(
        "9.5", "Longitud y composición de las solicitudes del benchmark",
        "Describir longitud y composición de solicitudes y distribución entre trabajadores.",
        "Aceptada y atendida. Se detalló la composición del lote de 1.000 peticiones.",
        "En 2.7 se especificó la longitud media (312 caracteres, 12 a 245 tokens), el reparto (48 % resuelto por reglas, 52 % por ONNX) y la distribución continua mediante cola asíncrona entre los 4 trabajadores.",
        "Sección 2.7, Párrafo 1."
    )

    add_item_box(
        "9.6", "Repeticiones independientes y estimación de variabilidad",
        "Incorporar repeticiones independientes que permitan valorar estabilidad del rendimiento.",
        "Aceptada y atendida. Se evaluaron cinco repeticiones independientes de 1.000 peticiones.",
        "Se reportó en 3.2 y Tabla 13 la media y desviación estándar de R = 5 corridas independientes (20,49 +- 1,12 ms; 194,7 +- 4,2 req/s).",
        "Sección 3.2, Párrafos 1 y 2; Tabla 13."
    )

    # ==================== BLOQUE 10 ====================
    add_h1("Bloque 10: Tratamiento de solicitudes extensas y archivos adjuntos")

    add_item_box(
        "10.1", "Criterio técnico para fragmentos de 3.400 caracteres y solapamiento de 200",
        "Explicar criterio técnico para longitud de fragmentos y solapamiento.",
        "Aceptada y atendida. Se fundamentó la ventana frente al límite de 256 tokens.",
        "En 2.7 se fundamentó que 3.400 caracteres optimizan la inspección de texto plano (hasta 512 KiB) por reglas deterministas completas, mientras que el solapamiento de 200 caracteres (~30 a 45 palabras/tokens) evita que credenciales, tokens JWT o DNI queden partidos en la frontera.",
        "Sección 2.7, Párrafo 4."
    )

    add_item_box(
        "10.2", "Cómo se combinan las predicciones de distintos fragmentos",
        "Precisar cómo se combinan predicciones de distintos fragmentos para la decisión final.",
        "Aceptada y atendida. Se formalizó la regla de agregación disyuntiva pesimista.",
        "En 2.7 se formalizó: A_final = BLOCK si existe al menos un fragmento con BLOCK; y se asigna al registro la categoría del fragmento con máxima puntuación R_final = max_j R(f_j).",
        "Sección 2.7, Párrafo 4."
    )

    add_item_box(
        "10.3", "Información distribuida o en los límites de segmentación",
        "Analizar comportamiento cuando información restringida aparece distribuida o en límites.",
        "Aceptada y atendida. Se analizaron los dos casos de frontera y truncamiento.",
        "En 2.7 se explicó que el solapamiento de 200 caracteres cubre entidades sensibles en el corte (~3.400 c), reconociendo con transparencia que intenciones semánticas ubicadas entre el token 256 y el carácter 3.400 quedan fuera de atención si no activan reglas, y que ataques dispersos >3.400 c no reconstruyen dependencia cruzada.",
        "Sección 2.7, Párrafo 4; Sección 3.4, Párrafo 2."
    )

    add_item_box(
        "10.4", "Documentar limitaciones de truncamiento, adjuntos y formatos",
        "Documentar limitaciones relativas a truncamiento, adjuntos y formatos.",
        "Aceptada y atendida. Se diferenciaron tres niveles de soporte de formatos.",
        "En 2.7 se distinguió: Implementado y evaluado (texto plano y código hasta 512 KiB); Limitación interna (truncamiento a 256 tokens del encoder dentro de cada bloque); y Fuera de alcance (PDF, DOCX, XLSX, ZIP e imágenes retenidas preventivamente sin inspección).",
        "Sección 2.7, Párrafo 4; Sección 3.4, Párrafo 2."
    )

    add_item_box(
        "10.5", "Pruebas específicas para solicitudes extensas y contenido adjunto",
        "Incorporar pruebas específicas frente a solicitudes extensas o contenido adjunto.",
        "Aceptada y atendida. Se ejecutó una batería cuantitativa de frontera.",
        "Se reportó en 2.7 un experimento controlado con 34 textos extensos (4.000 a 15.000 caracteres) evaluando posiciones al inicio, intermedias y en el carácter 3.400, alcanzando 100 % de retención en la frontera gracias al solapamiento.",
        "Sección 2.7, Párrafo 4; Tabla 15 (TC-08)."
    )

    # ==================== BLOQUE 11 ====================
    add_h1("Bloque 11: Privacidad, gestión de datos y consideraciones éticas")

    add_item_box(
        "11.1", "Naturaleza de los datos (reales vs sintéticos) y anonimización",
        "Especificar si datos contienen información real y describir anonimización o generación sintética.",
        "Aceptada y atendida. Se declaró la naturaleza 100 % ficticia del corpus.",
        "Se declaró de forma taxativa en la Sección 2.4 y 2.8 que la totalidad de PII, credenciales y secretos comerciales en los 2.743 y 328 registros son cadenas sintéticas ficticias y de repositorios abiertos, sin datos de personas ni organizaciones reales.",
        "Sección 2.4, Párrafo 7; Sección 2.8, Párrafo 3."
    )

    add_item_box(
        "11.2", "Políticas de registro, almacenamiento, acceso, conservación y eliminación",
        "Detallar políticas de registro de eventos, almacenamiento, acceso, conservación y eliminación.",
        "Aceptada y atendida. Se detalló la arquitectura de la base SQLite local.",
        "En 2.8 se detalló el archivo audit_logs.db, su alojamiento en perfil de usuario con permisos locales de sistema operativo, y la diferenciación entre las funciones de purga transaccional del prototipo y las políticas de TI.",
        "Sección 2.8, Párrafos 1 y 2; Tabla 7."
    )

    add_item_box(
        "11.3", "Información conservada durante evaluación y operación",
        "Aclarar qué información se conserva en evaluación y operación y reducción de exposición.",
        "Aceptada y atendida. Se especificó la minimización de datos por diseño.",
        "En 2.8 se precisó que en evaluación solo se conservaron métricas agregadas y corpus sintético; y en operación el texto del prompt reside únicamente en RAM durante los ~20 ms locales y jamás se guarda en disco ni se envía fuera de 127.0.0.1, persistiendo solo metadatos y hash SHA-256.",
        "Sección 2.8, Párrafo 1; Tabla 7."
    )

    add_item_box(
        "11.4", "Declaración sobre revisión ética o fundamento de exención",
        "Incluir declaración sobre revisión ética o fundamento de exención.",
        "Aceptada y atendida. Se incorporó la declaración formal de exención.",
        "Se añadió en la Sección 2.8 la Declaración ética formal certificando la exención de comité bioético al tratarse de investigación de software sobre datos sintéticos y públicos sin seres humanos.",
        "Sección 2.8, Párrafo 3."
    )

    add_item_box(
        "11.5", "Diferenciar medidas implementadas de recomendaciones no evaluadas",
        "Diferenciar medidas implementadas y verificadas de recomendaciones de privacidad no evaluadas.",
        "Aceptada y atendida. Se incorporó la Tabla 7 comparativa en dos columnas.",
        "La Tabla 7 en la Sección 2.8 contrasta en dos columnas las medidas implementadas en el prototipo (procesamiento 127.0.0.1, no retención del texto, hash SHA-256) frente a recomendaciones organizacionales (HMAC con clave rotativa, SQLCipher, SSO/RBAC, purga temporal).",
        "Sección 2.8; Tabla 7."
    )

    # ==================== BLOQUE 12 ====================
    add_h1("Bloque 12: Revisión de la discusión y las conclusiones")

    add_item_box(
        "12.1", "Vincular cada conclusión con resultados específicos y verificables",
        "Vincular cada conclusión con resultados específicos y verificables de los experimentos.",
        "Aceptada y atendida. Cada conclusión se ató a sus métricas empíricas exactas.",
        "En la Sección 4 se respaldó cada afirmación citando: Exactitud 95,12 %, F1 macro 0,9518 (vs TF-IDF 92,68 % y 0,9245), FNR 0,00 % [IC 95 %: 0,00 % – 1,26 %], FPR 5,56 % [IC 95 %: 0,68 % – 18,66 %], paridad ONNX (328/328), 6 fallos fail-closed y latencia p95 44,375 ms en CPU.",
        "Sección 4 (Conclusiones)."
    )

    add_item_box(
        "12.2", "Delimitar afirmaciones en seguridad, generalización, compatibilidad y viabilidad",
        "Delimitar afirmaciones de seguridad, generalización, compatibilidad y viabilidad operativa según alcance real.",
        "Aceptada y atendida. Se acotaron formalmente las cuatro dimensiones.",
        "En 3.4 y 4 se acotaron: Seguridad (bloqueo previo en navegador bajo fail-closed para texto plano); Generalización (9 clases en español en corpus dirigido sin tráfico empresarial real); Compatibilidad (3 proveedores validados sintéticamente y 7 solo configurados); Viabilidad operativa (Ryzen 5 5600G p95 44,37 ms sujeta a mitigar FPR 5,56 %).",
        "Sección 3.4, Párrafo 2; Sección 4; Resumen."
    )

    add_item_box(
        "12.3", "Distinguir rendimiento del clasificador, mecanismo de bloqueo y efectividad integral",
        "Distinguir entre rendimiento del clasificador, mecanismo de bloqueo y efectividad integral.",
        "Aceptada y atendida. Se dedicó un párrafo a separar los tres niveles.",
        "En 3.4 se separaron formalmente: (1) capacidad intrínseca del clasificador DeBERTa; (2) funcionamiento técnico de retención de la extensión y motor híbrido fail-closed; y (3) efectividad integral como propiedad emergente sujeta a DOM cambiante, adjuntos y comportamiento del usuario.",
        "Sección 3.4, Párrafo 1."
    )

    add_item_box(
        "12.4", "Explicar limitaciones de datos, validación funcional y entorno en transferibilidad",
        "Explicar principales limitaciones de datos, validación funcional y entorno y efecto en transferibilidad.",
        "Aceptada y atendida. Se renombró y reestructuró la subsección 3.4.",
        "Se renombró como '3.4. Limitaciones del estudio, amenazas a la validez y trabajo futuro', analizando en detalle las amenazas de validez interna, externa y de constructo (datos sintéticos 8:1, páginas sintéticas y único host local).",
        "Sección 3.4."
    )

    add_item_box(
        "12.5", "Evitar afirmaciones absolutas sobre prevención de fugas de datos",
        "Evitar afirmaciones absolutas sobre prevención de fugas de datos sin evidencia suficiente.",
        "Aceptada y atendida. Se moderó el vocabulario en todo el artículo.",
        "Se sustituyeron términos categóricos por 'mitigar la superficie de exposición en el navegador', 'reducir el riesgo de divulgación' y 'apoyar el control previo', acotando siempre los resultados al conjunto controlado evaluado.",
        "Resumen, Introducción, Sección 3.1.2, Sección 3.4 y Sección 4."
    )

    # ==================== CHECKLIST DE ENTREGA ====================
    add_h1("Condiciones de Reenvío Exigidas por la Revista INGENIUS (Checklist de Entrega)")
    
    add_p("1. Manuscrito con cambios claramente identificados: Cumplido al 100 %. Se adjunta el archivo Articulo_Aegis_DLP_Modificaciones_Resaltadas.docx donde cada modificación, adición y ampliación de tabla se encuentra resaltada en color amarillo.\n\n"
          "2. Carta de Respuesta Detallada (Response to Reviewers): Cumplido al 100 %. El presente documento detalla la respuesta técnica y localización exacta de los 65 ítems desglosados en los 12 bloques del dictamen.\n\n"
          "3. Justificación técnica de no omisión: Cumplido al 100 %. La totalidad de las observaciones y experimentos requeridos (baseline TF-IDF, paridad ONNX sobre 328 casos, pruebas de fallo fail-closed, fragmentación con solapamiento, matriz 9x9 e intervalos de confianza) fueron incorporados con evidencia empírica verificable.",
          space_after=Pt(10))

    add_p("Atentamente,\n\n"
          "Los Autores:\n"
          "Jesus Christopher Mecola Bernedo\n"
          "Julio David Tirado Ávila\n"
          "Alberto Carlos Mendoza de los Santos",
          bold=True, space_after=Pt(12))

    return doc

print("Compilando Carta de Respuesta Exhaustiva (65 ítems)...")
rebuttal_doc = build_exhaustive_rebuttal()
rebuttal_path = r"C:\Users\David\Proyectos IX ciclo\Gobierno de IA\Carta_Respuesta_Observaciones_INGENIUS.docx"
rebuttal_doc.save(rebuttal_path)
print(f"Carta guardada exitosamente en: {rebuttal_path}")

brain_dir = r"C:\Users\David\.gemini\antigravity\brain\829d563f-e840-4fc0-8db6-d42ea33671d5"
rebuttal_doc.save(os.path.join(brain_dir, "Carta_Respuesta_Observaciones_INGENIUS.docx"))
print("Sincronización en brain completada.")
