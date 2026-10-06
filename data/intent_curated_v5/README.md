# Corpus de intención v5 — experimental, no aprobado para producción

## Qué se corrigió

Se excluyen los 27.000 registros del corpus antiguo. No se borraron los originales:
`quarantine.jsonl` conserva archivo, línea, hash, etiqueta anterior y motivo.
El generador antiguo queda deshabilitado: no puede volver a inventar nueve
categorías a partir de una etiqueta binaria ni insertar la etiqueta en el prompt.

El texto es la única entrada al modelo. `label` es el objetivo. Las columnas de
procedencia, idioma, calidad de anotación y `audit_features` son para auditoría;
no son características de entrenamiento. Los indicadores léxicos no asignan etiquetas.

## Política de clasificación

| Etiqueta | Criterio |
|---|---|
| Safe_Use | Tareas, material público o ficticio, prevención, anonimización y trabajo autorizado sin divulgación sensible. |
| PII_Leak | Divulgar, obtener o inferir información privada identificable sin autorización. |
| Proprietary_Code | Divulgar código cerrado, credenciales o secretos técnicos protegidos. |
| Business_Secrets | Divulgar planes, cifras, negociaciones o conocimientos empresariales reservados. |
| Code_Exploitation | Solicitar intrusión, malware, explotación operativa o daño informático. La enseñanza defensiva no basta para esta etiqueta. |
| Data_Exfiltration | Extraer o transmitir información privada/restringida hacia otro destino, o eludir el control de salida. |
| Social_Engineering | Suplantación, engaño para obtener acceso/datos, phishing o creación deliberada de desinformación. |
| Role_Evasion_Jailbreak | Intento de sustituir instrucciones de mayor prioridad, evadir políticas o revelar instrucciones internas. |
| Legal_Misalignment | Falsificar cumplimiento/consentimiento/evidencias, ocultar incidentes o implementar discriminación. No es una categoría residual de todo contenido dañino. |

Las categorías pueden solaparse. Para anotación de una sola clase se prioriza la
acción explícita solicitada: explotación implementada → Code_Exploitation;
engaño para obtener acceso → Social_Engineering; transferencia de datos →
Data_Exfiltration; divulgación sin transferencia explícita → categoría del dato.
Una personificación por sí sola no implica jailbreak. Los casos ambiguos requieren
revisión, no una asignación forzada. Estas decisiones son política local, no
etiquetas supuestamente suministradas por el dataset público.

## Fuentes y anotaciones

- [Deepset prompt-injections](https://huggingface.co/datasets/deepset/prompt-injections):
  solo positivos de inyección mapeados a Role_Evasion_Jailbreak. Un negativo no se
  considera Safe_Use. Su tarjeta presenta Apache-2.0 en el nivel superior y
  CC-BY-4.0 en dataset_info: discrepancia registrada, revisar antes de redistribuir.
- [NVIDIA Aegis / Nemotron Content Safety V2](https://huggingface.co/datasets/nvidia/Aegis-AI-Content-Safety-Dataset-2.0):
  tarjeta CC-BY-4.0. Se conservan únicamente prompts y anotaciones, no respuestas.
  Su clasificación de seguridad general NO equivale a las nueve clases DLP.
  Veinticinco prompts tienen revisión individual del agente con texto exacto,
  categoría y justificación en `../public_reviews_v5.py`. No es revisión humana.
- `../intent_policy_v5.py`: 162 escenarios originales en español, 18 por clase.
  Son sintéticos redactados por el agente, no ejemplos reales ni un benchmark
  independiente. No se replican con sufijos para aumentar artificialmente el tamaño.
- LibrAI/do-not-answer se investigó pero no se incorporó: además de requerir
  reconciliar la taxonomía, la tarjeta declara Apache-2.0 en metadatos y
  CC-BY-NC-SA-4.0 para los datasets en el cuerpo.

Cada descarga queda fijada a un commit del repositorio, con SHA-256 de los
archivos y copia de la tarjeta en `sources/`. `sources_manifest.json` conserva
la atribución y la revisión utilizada. No se enviaron documentos del usuario
a servicios de anotación o traducción.

## Separación y reproducción

```powershell
.\.venv\Scripts\python.exe training/build_corpus_v5.py
# Reconstrucción exacta con los snapshots locales, sin buscar nuevas revisiones:
.\.venv\Scripts\python.exe training/build_corpus_v5.py --offline
# Solo integridad (no habilita producción):
.\.venv\Scripts\python.exe training/validate_corpus.py --experimental
# Integridad, cobertura y aprobación; devuelve 1 mientras falte curación:
.\.venv\Scripts\python.exe training/validate_corpus.py
```

Se mantiene el test público en test; validación adicional solo se deriva del
train original. Duplicados normalizados/númericos nunca se reparten entre
particiones. Si hay etiquetas contradictorias, se excluye toda la familia.
No se afirma eliminar todas las paráfrasis semánticas. Traducciones o variantes
futuras deben heredar familia y partición del original, no formar nuevos tests.

`auxiliary_original_labels.jsonl` NO es un archivo de entrenamiento de nueve clases.
Conserva las etiquetas originales para futura anotación o un modelo auxiliar de
su tarea específica. No debe concatenarse directamente con train/val/test.

## Límites pendientes

Hay cobertura en español de las nueve categorías en las tres particiones: al
menos 132 ejemplos por clase en entrenamiento y 33 por clase en validación y
prueba. Las combinaciones acción-objeto pertenecen a una sola partición. Los
datos públicos se limitan a 15 ejemplos por fuente/clase/partición para que una
tarea binaria no domine la política de nueve clases. El corpus queda habilitado
para reentrenamiento y pruebas del proyecto. Antes de afirmar preparación para
producción todavía hace falta revisión humana independiente, evaluación por
idioma, adjuntos y paráfrasis fuera de estas plantillas. También deben revisarse
posibles datos personales residuales en las fuentes públicas.

El lanzador v5 verifica integridad y preparación antes de entrenar. El modo
`-Experimental` permite experimentos explícitos, guarda la advertencia de curación
en el candidato y NO habilita despliegue. No se modificó el modelo servido.
