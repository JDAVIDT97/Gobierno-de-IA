# Distribución de Aegis DLP

El repositorio incluye código de API, dashboard, extensión, scripts de arranque,
dependencias fijadas, pruebas, documentación, tokenizador y el único modelo activo
`models/dlp_slm`: dlp-slm-v5.0, ONNX FP32. La compresión gzip no modifica los pesos.
Las partes de hasta 40 MiB se restauran automáticamente al iniciar la API; cada
parte y el archivo restaurado se verifican con SHA-256. El manifiesto registra
tamaño original, tamaño de las partes y hashes. Funciona con ZIP y Git sin LFS.

En Windows, instale Python 3.10–3.12 y ejecute `start.bat`. El script prepara las
dependencias y arranca la API en el puerto 8000. También puede seguir la instalación
manual del README. Cargue `extension/` como extensión descomprimida en Chrome.
Docker reconstruye el modelo al construir la imagen. La inferencia no necesita
Internet; instalar paquetes o descargar un modelo base para entrenar sí lo necesita.

El único corpus de entrenamiento distribuido es `data/intent_curated_v5/`:
1.707 ejemplos de entrenamiento, 510 de validación y 526 de prueba. Se incluyen
los tres splits, informes, documentación y manifiesto de procedencia. No se
publican fuentes originales, cuarentena ni registros auxiliares que no alimentan
el entrenamiento. Se conserva la atribución y la advertencia de discrepancia
de licencia de las fuentes públicas en el README y manifiesto del corpus.

El corpus fue ampliado después de entrenar el modelo activo. El informe histórico
del modelo registra otros hashes y conteos. El corpus distribuido permite entrenar
nuevos candidatos, pero no garantiza reconstruir exactamente los pesos activos.
Se conservan ambos informes para hacer visible esta diferencia. El modelo está
aprobado para pruebas locales según su informe; no tiene aprobación de producción.

Se excluyen del repositorio otros modelos, checkpoints, respaldos, corpus antiguos,
el duplicado PyTorch de los pesos de inferencia, entornos virtuales, cachés, logs,
`.env` y bases SQLite de auditoría. Esos archivos locales no se eliminan. SQLite
crea una base nueva al iniciar. Entrenar genera pesos PyTorch nuevos; ejecutar
el software usa el ONNX incluido y no exige entrenamiento.

Tamaño ONNX: 568.067.861 bytes; comprimido: 344.920.511 bytes (39,3 % menos),
en nueve partes. El tokenizador y los tres splits se conservan completos.
