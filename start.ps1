<#
.SYNOPSIS
    Script de arranque local para Aegis DLP (Sin Docker).
.DESCRIPTION
    Verifica o crea el entorno virtual (.venv), instala dependencias,
    inicia la API FastAPI (puerto 8000) y el Dashboard Streamlit (puerto 8501),
    verifica la salud del sistema y abre el navegador automáticamente.
.PARAMETER NoBrowser
    No abrir el navegador automáticamente tras iniciar.
.PARAMETER SkipStreamlit
    Iniciar únicamente la API FastAPI y omitir el dashboard de Streamlit.
.PARAMETER Headless
    Ejecutar procesos en segundo plano sin abrir ventanas de terminal secundarias.
#>

[CmdletBinding()]
param(
    [switch]$NoBrowser = $false,
    [switch]$SkipStreamlit = $false,
    [switch]$Headless = $false
)

$ErrorActionPreference = "Stop"
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8

$ROOT_DIR = $PSScriptRoot
if (-not $ROOT_DIR) {
    $ROOT_DIR = (Get-Location).Path
}

function Print-Banner {
    Clear-Host
    Write-Host ""
    Write-Host " ========================================================================= " -ForegroundColor DarkCyan
    Write-Host "           🛡️  AEGIS DLP - SISTEMA DE GOBERNANZA DE IA LOCAL              " -ForegroundColor Cyan
    Write-Host "       Prototipo de inspección local y registro de decisiones             " -ForegroundColor Gray
    Write-Host " ========================================================================= " -ForegroundColor DarkCyan
    Write-Host ""
}

function Find-SystemPython {
    $candidates = @("python", "py")
    foreach ($cmd in $candidates) {
        try {
            $ver = & $cmd --version 2>&1
            if ($LASTEXITCODE -eq 0 -and ($ver -match "Python 3\.(1[0-3]|[0-9])")) {
                return $cmd
            }
        } catch {
            continue
        }
    }
    return $null
}

function Free-Port($port) {
    try {
        $conns = Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue
        if ($conns) {
            foreach ($conn in $conns) {
                $pidToKill = $conn.OwningProcess
                Write-Host "  [!] Puerto $port ocupado por PID $pidToKill. Liberándolo..." -ForegroundColor Yellow
                Stop-Process -Id $pidToKill -Force -ErrorAction SilentlyContinue
            }
            Start-Sleep -Milliseconds 800
        }
    } catch {
        # Silently continue if permission or query fails
    }
}

Print-Banner

# -------------------------------------------------------------
# 1. VERIFICACIÓN / CREACIÓN DE ENTORNO VIRTUAL (.venv)
# -------------------------------------------------------------
$venvDir = Join-Path $ROOT_DIR ".venv"
$venvPython = Join-Path $venvDir "Scripts\python.exe"
$venvPip = Join-Path $venvDir "Scripts\pip.exe"
$reviewPython = Join-Path $ROOT_DIR "artifacts\runtime\venv\Scripts\python.exe"
if (Test-Path -LiteralPath $reviewPython) {
    $venvDir = Join-Path $ROOT_DIR "artifacts\runtime\venv"
    $venvPython = $reviewPython
    $venvPip = Join-Path $venvDir "Scripts\pip.exe"
}

if (-not (Test-Path $venvPython)) {
    Write-Host "[*] Entorno virtual no detectado. Configurando .venv..." -ForegroundColor Cyan
    $sysPython = Find-SystemPython
    if (-not $sysPython) {
        Write-Host "[-] ERROR: No se encontró Python 3.10+ en el sistema." -ForegroundColor Red
        Write-Host "    Instala Python 3.10 o superior desde https://www.python.org y agrégalo al PATH." -ForegroundColor Yellow
        exit 1
    }
    Write-Host "  -> Utilizando: $sysPython" -ForegroundColor Gray
    & $sysPython -m venv "$venvDir"
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        Write-Host "[-] ERROR al crear el entorno virtual en $venvDir" -ForegroundColor Red
        exit 1
    }
    Write-Host "  [+] Entorno virtual creado exitosamente." -ForegroundColor Green
    
    Write-Host "[*] Instalando dependencias de requirements.txt (esto puede tardar unos minutos la primera vez)..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip --quiet
    & $venvPython -m pip install -r (Join-Path $ROOT_DIR "requirements.txt")
    if ($LASTEXITCODE -ne 0) {
        Write-Host "[-] Advertencia: Hubo advertencias o errores durante la instalación de dependencias." -ForegroundColor Yellow
    } else {
        Write-Host "  [+] Dependencias instaladas correctamente." -ForegroundColor Green
    }
} else {
    Write-Host "[+] Entorno virtual detectado: $venvDir" -ForegroundColor Green
    # Verificar rápidamente dependencias clave
    $checkImports = & $venvPython -c "import fastapi, uvicorn, onnxruntime, streamlit; print('OK')" 2>$null
    if ($checkImports -notmatch "OK") {
        Write-Host "[*] Faltan librerías clave en .venv. Instalando requirements.txt..." -ForegroundColor Yellow
        & $venvPython -m pip install -r (Join-Path $ROOT_DIR "requirements.txt")
    }
}

# -------------------------------------------------------------
# 2. CONFIGURACIÓN .env
# -------------------------------------------------------------
$envFile = Join-Path $ROOT_DIR ".env"
$envExample = Join-Path $ROOT_DIR ".env.example"
if (-not (Test-Path $envFile) -and (Test-Path $envExample)) {
    Write-Host "[*] Generando archivo .env desde .env.example..." -ForegroundColor Cyan
    Copy-Item $envExample $envFile
    Write-Host "  [+] Archivo .env configurado." -ForegroundColor Green
}

# -------------------------------------------------------------
# 3. VERIFICACIÓN DE MODELOS SLM
# -------------------------------------------------------------
$modelPath = Join-Path $ROOT_DIR "models\dlp_slm\model.onnx"
& $venvPython -m api.model_bundle
if ($LASTEXITCODE -ne 0) { throw "No se pudo restaurar el modelo ONNX." }
if (Test-Path $modelPath) {
    Write-Host "[+] Modelo ONNX SLM verificado: models/dlp_slm/model.onnx" -ForegroundColor Green
} else {
    Write-Host "[!] ADVERTENCIA: No se encontró el modelo ONNX en models/dlp_slm/model.onnx" -ForegroundColor Yellow
    Write-Host "    El motor funcionará en modo heurístico/fallback." -ForegroundColor Yellow
}

# -------------------------------------------------------------
# 4. LIMPIEZA DE PUERTOS
# -------------------------------------------------------------
Write-Host "[*] Verificando puertos (8000, 8501)..." -ForegroundColor Cyan
Free-Port 8000
if (-not $SkipStreamlit) {
    Free-Port 8501
}

# -------------------------------------------------------------
# 5. INICIAR SERVICIOS
# -------------------------------------------------------------
$pidsList = @()

Write-Host "[*] Levantando FastAPI Backend (Uvicorn en 127.0.0.1:8000)..." -ForegroundColor Cyan
if ($Headless) {
    $apiProcess = Start-Process -FilePath $venvPython `
        -ArgumentList "-m", "uvicorn", "api.main:app", "--host", "127.0.0.1", "--port", "8000", "--reload" `
        -WorkingDirectory $ROOT_DIR `
        -PassThru -NoNewWindow
} else {
    $apiCmd = "cd '$ROOT_DIR'; `$host.UI.RawUI.WindowTitle = 'Aegis DLP - FastAPI API (8000)'; & '$venvPython' -m uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload"
    $apiProcess = Start-Process -FilePath "powershell.exe" `
        -ArgumentList "-NoExit", "-Command", $apiCmd `
        -WorkingDirectory $ROOT_DIR `
        -PassThru
}
$pidsList += $apiProcess.Id

if (-not $SkipStreamlit) {
    Write-Host "[*] Levantando Streamlit CISO Dashboard (Puerto 8501)..." -ForegroundColor Cyan
    if ($Headless) {
        $stProcess = Start-Process -FilePath $venvPython `
            -ArgumentList "-m", "streamlit", "run", "dashboard/dashboard.py", "--server.port", "8501", "--server.headless", "true" `
            -WorkingDirectory $ROOT_DIR `
            -PassThru -NoNewWindow
    } else {
        $stCmd = "cd '$ROOT_DIR'; `$host.UI.RawUI.WindowTitle = 'Aegis DLP - Streamlit Dashboard (8501)'; & '$venvPython' -m streamlit run dashboard/dashboard.py --server.port 8501 --server.headless true"
        $stProcess = Start-Process -FilePath "powershell.exe" `
            -ArgumentList "-NoExit", "-Command", $stCmd `
            -WorkingDirectory $ROOT_DIR `
            -PassThru
    }
    $pidsList += $stProcess.Id
}

# Guardar PIDs para detención posterior
$pidFilePath = Join-Path $ROOT_DIR ".aegis_pids.json"
$pidsList | ConvertTo-Json | Out-File -FilePath $pidFilePath -Encoding UTF8 -Force

# -------------------------------------------------------------
# 6. VERIFICAR SALUD DE LA API
# -------------------------------------------------------------
Write-Host "[*] Esperando a que el motor de inferencia esté listo en http://127.0.0.1:8000/health..." -ForegroundColor Cyan
$healthy = $false
$retries = 30

for ($i = 1; $i -le $retries; $i++) {
    Start-Sleep -Seconds 1
    try {
        $response = Invoke-RestMethod -Uri "http://127.0.0.1:8000/health" -Method Get -TimeoutSec 2 -ErrorAction SilentlyContinue
        if ($response -and $response.status -eq "healthy") {
            $healthy = $true
            break
        }
    } catch {
        Write-Host "." -NoNewline -ForegroundColor Gray
    }
}
Write-Host ""

if ($healthy) {
    Write-Host "[+] ¡Sistema Aegis DLP iniciado con éxito!" -ForegroundColor Green
} else {
    Write-Host "[!] El servidor tardó más de lo esperado en responder. Revisa la ventana de FastAPI para ver los registros." -ForegroundColor Yellow
}

# -------------------------------------------------------------
# 7. ABRIR NAVEGADOR
# -------------------------------------------------------------
if (-not $NoBrowser) {
    Start-Sleep -Milliseconds 500
    # Abrir la réplica de ChatGPT (sandbox de prueba de la extensión)
    Start-Process "http://127.0.0.1:8000/sandbox"
    # Abrir el Command Center Web
    Start-Process "http://127.0.0.1:8000/"
    if (-not $SkipStreamlit) {
        Start-Process "http://localhost:8501"
    }
}

# -------------------------------------------------------------
# 8. PANEL DE INFORMACIÓN Y CONTROL
# -------------------------------------------------------------
Write-Host ""
Write-Host " ========================================================================= " -ForegroundColor DarkCyan
Write-Host "                    SERVICIOS DISPONIBLES EN LOCAL                        " -ForegroundColor Green
Write-Host " ========================================================================= " -ForegroundColor DarkCyan
Write-Host "  🌐 Web Command Center:        http://127.0.0.1:8000/" -ForegroundColor White
Write-Host "  🧪 Sandbox ChatGPT (Pruebas): http://127.0.0.1:8000/sandbox" -ForegroundColor Yellow
Write-Host "  📊 Streamlit CISO Dashboard:  http://localhost:8501/" -ForegroundColor White
Write-Host "  📖 Swagger API Docs:          http://127.0.0.1:8000/docs" -ForegroundColor Gray
Write-Host " ========================================================================= " -ForegroundColor DarkCyan
Write-Host ""
Write-Host "  🧩 CÓMO ACTIVAR LA EXTENSIÓN EN GOOGLE CHROME:" -ForegroundColor Magenta
Write-Host "   1. Abre Chrome y entra a: chrome://extensions" -ForegroundColor White
Write-Host "   2. Activa la casilla 'Modo de desarrollador' (arriba a la derecha)." -ForegroundColor White
Write-Host "   3. Haz clic en 'Cargar descomprimida' (Load unpacked)." -ForegroundColor White
Write-Host "   4. Selecciona la carpeta: $ROOT_DIR\extension" -ForegroundColor Cyan
Write-Host "   5. ¡Listo! Abre el Sandbox (http://127.0.0.1:8000/sandbox) y verás" -ForegroundColor White
Write-Host "      el badge verde 'ON' interceptando prompts en tiempo real." -ForegroundColor Green
Write-Host ""
Write-Host " ========================================================================= " -ForegroundColor DarkCyan
Write-Host "  [Presiona 'Q' o Ctrl+C en esta consola para detener todos los servicios]  " -ForegroundColor Red
Write-Host " ========================================================================= " -ForegroundColor DarkCyan
Write-Host ""

# -------------------------------------------------------------
# 9. BUCLE DE ESCUCHA PARA APAGADO LIMPIO
# -------------------------------------------------------------
try {
    while ($true) {
        if ([Console]::KeyAvailable) {
            $key = [Console]::ReadKey($true)
            if ($key.Key -eq [ConsoleKey]::Q -or ($key.Modifiers -band [ConsoleModifiers]::Control -and $key.Key -eq [ConsoleKey]::C)) {
                break
            }
        }
        Start-Sleep -Milliseconds 400
    }
} finally {
    Write-Host ""
    Write-Host "[*] Deteniendo todos los servicios de Aegis DLP..." -ForegroundColor Yellow
    
    # Detener por PID guardados
    if (Test-Path $pidFilePath) {
        try {
            $pids = Get-Content $pidFilePath -Raw | ConvertFrom-Json
            foreach ($p in $pids) {
                Stop-Process -Id $p -Force -ErrorAction SilentlyContinue
            }
            Remove-Item $pidFilePath -Force -ErrorAction SilentlyContinue
        } catch {}
    }
    
    # Asegurar liberación de puertos
    Free-Port 8000
    Free-Port 8501
    
    Write-Host "[+] Todos los servicios han sido cerrados limpiamente. ¡Hasta pronto!" -ForegroundColor Green
    Write-Host ""
}
