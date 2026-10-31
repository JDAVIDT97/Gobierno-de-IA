$ErrorActionPreference='Stop'
$root=Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $root
$env:UV_CACHE_DIR=Join-Path $root 'artifacts/runtime/cache'
$env:UV_PYTHON_INSTALL_DIR=Join-Path $root 'artifacts/runtime/python'
if(-not (Get-Command uv -ErrorAction SilentlyContinue)){throw 'Se requiere uv instalado desde su distribución oficial.'}
uv python install 3.12.13
if($LASTEXITCODE -ne 0){throw 'No se pudo obtener el intérprete aislado'}
$python=Join-Path $env:UV_PYTHON_INSTALL_DIR 'cpython-3.12.13-windows-x86_64-none/python.exe'
$venv=Join-Path $root 'artifacts/runtime/venv'
if(-not (Test-Path -LiteralPath "$venv/Scripts/python.exe")){
    uv venv --python $python $venv
    if($LASTEXITCODE -ne 0){throw 'No se pudo crear el entorno de revisión'}
}
uv pip sync --python "$venv/Scripts/python.exe" -r (Join-Path $root 'artifacts/cierre_ingenius_20261029/requirements-lock.txt')
if($LASTEXITCODE -ne 0){throw 'No se pudieron instalar las dependencias fijadas'}
$env:PLAYWRIGHT_BROWSERS_PATH=Join-Path $root 'artifacts/runtime/browsers'
& "$venv/Scripts/python.exe" -m playwright install chromium
if($LASTEXITCODE -ne 0){throw 'No se pudo instalar el navegador de pruebas'}
Write-Output 'Entorno preparado. Consultar README_REPRODUCCION.md antes de ejecutar pruebas.'
