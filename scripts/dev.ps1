$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackendDir = Join-Path $RepoRoot 'backend'
$FrontendDir = Join-Path $RepoRoot 'frontend'
$BackendPython = Join-Path $BackendDir '.venv\Scripts\python.exe'

if (-not (Test-Path $BackendPython)) {
    Write-Host '尚未安装项目依赖，请先运行 scripts/setup_windows.ps1' -ForegroundColor Yellow
    exit 1
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host '未找到 npm，请先安装 Node.js LTS。' -ForegroundColor Red
    exit 1
}

Write-Host 'Starting Movie Production backend and frontend...' -ForegroundColor Green

Start-Process powershell -WorkingDirectory $BackendDir -ArgumentList @(
    '-NoExit',
    '-Command',
    "& '$BackendPython' -m uvicorn app.main:app --reload --port 8000"
)

Start-Process powershell -WorkingDirectory $FrontendDir -ArgumentList @(
    '-NoExit',
    '-Command',
    'npm run dev'
)

Start-Sleep -Seconds 3
Start-Process 'http://localhost:5173'

Write-Host 'Frontend: http://localhost:5173'
Write-Host 'Backend:  http://localhost:8000/docs'
