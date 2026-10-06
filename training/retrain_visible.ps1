param([switch]$Experimental)
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$host.UI.RawUI.WindowTitle = 'Aegis - reentrenamiento transformer v5'
$env:USE_TF = '0'
$env:TRANSFORMERS_NO_TF = '1'
$env:PYTHONUNBUFFERED = '1'
$preflightArgs = @('training/validate_corpus.py', '--data-dir', 'data/intent_curated_v5')
$trainingArgs = @('-u', 'training/train_model.py', '--backend', 'transformer', '--epochs', '8', '--batch-size', '8', '--max-train-samples', '0', '--max-length', '256', '--data-dir', 'data/intent_curated_v5', '--output-dir', 'models/intent_candidate_v5', '--run-name', 'intent_curated_v5')
if ($Experimental) { $preflightArgs += '--experimental'; $trainingArgs += '--experimental-data' }
& .\.venv\Scripts\python.exe @preflightArgs
if ($LASTEXITCODE -ne 0) { throw 'Corpus todavía insuficiente para entrenamiento de producción. Revisar data/intent_curated_v5/quality_report.json.' }
& .\.venv\Scripts\python.exe @trainingArgs 2>&1 | Tee-Object -FilePath runs\intent_curated_v5.log
if ($LASTEXITCODE -ne 0) { throw "Entrenamiento fallido: código $LASTEXITCODE. Revisar runs/intent_curated_v5.log" }
Write-Host 'Entrenamiento terminado. Validando candidato para pruebas locales.'
& .\.venv\Scripts\python.exe training\validate_candidate.py --candidate models/intent_candidate_v5 --gate local 2>&1 | Tee-Object -FilePath runs\intent_curated_v5_acceptance.log
if ($LASTEXITCODE -ne 0) { throw 'El candidato no superó las pruebas de aceptación. No activar.' }
Write-Host 'Candidato aprobado para pruebas locales. Esperando promoción controlada al modelo activo.' -ForegroundColor Green
