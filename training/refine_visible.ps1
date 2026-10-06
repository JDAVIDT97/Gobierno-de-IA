$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath (Split-Path -Parent $PSScriptRoot)
$host.UI.RawUI.WindowTitle = 'Aegis - refinamiento transformer v5 FP32'
$env:USE_TF = '0'
$env:TRANSFORMERS_NO_TF = '1'
$env:PYTHONUNBUFFERED = '1'
& .\.venv\Scripts\python.exe training\validate_corpus.py --data-dir data\intent_curated_v5
if ($LASTEXITCODE -ne 0) { throw 'El corpus no superó el preflight.' }
& .\.venv\Scripts\python.exe -u training\train_model.py --backend transformer --model models\intent_candidate_v5 --epochs 4 --batch-size 8 --learning-rate 0.00005 --max-train-samples 0 --max-length 256 --data-dir data\intent_curated_v5 --output-dir models\intent_candidate_v5_refined --run-name intent_curated_v5_refined 2>&1 | Tee-Object -FilePath runs\intent_curated_v5_refined.log
if ($LASTEXITCODE -ne 0) { throw 'El refinamiento falló.' }
& .\.venv\Scripts\python.exe training\validate_candidate.py --candidate models\intent_candidate_v5_refined --gate local 2>&1 | Tee-Object -FilePath runs\intent_curated_v5_refined_acceptance.log
if ($LASTEXITCODE -ne 0) { throw 'El candidato refinado no superó la aceptación. No activar.' }
Write-Host 'Candidato FP32 aprobado para pruebas locales. Esperando promoción controlada.' -ForegroundColor Green
