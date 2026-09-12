$ErrorActionPreference = 'Stop'

$RepoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$BackendDir = Join-Path $RepoRoot 'backend'
$FrontendDir = Join-Path $RepoRoot 'frontend'
$VenvPython = Join-Path $BackendDir '.venv\Scripts\python.exe'

function Write-Step([string]$Message) {
    Write-Host "`n==> $Message" -ForegroundColor Cyan
}

function Require-Command([string]$Name, [string]$HelpText) {
    if (-not (Get-Command $Name -ErrorAction SilentlyContinue)) {
        Write-Host "缺少 $Name。$HelpText" -ForegroundColor Red
        throw "Missing required command: $Name"
    }
}

Write-Host 'Movie Production - Windows 本地安装' -ForegroundColor Green
Write-Host "项目目录: $RepoRoot"

Write-Step '检查基础环境'
Require-Command 'python' '请先安装 Python 3.11 或更高版本，并勾选 Add Python to PATH。'
Require-Command 'node' '请先安装 Node.js LTS。'
Require-Command 'npm' 'npm 通常随 Node.js 一起安装。'

$PythonVersionText = (& python --version 2>&1 | Out-String).Trim()
$NodeVersionText = (& node --version 2>&1 | Out-String).Trim()
Write-Host "Python: $PythonVersionText"
Write-Host "Node:   $NodeVersionText"

Write-Step '创建 Python 虚拟环境'
if (-not (Test-Path $VenvPython)) {
    & python -m venv (Join-Path $BackendDir '.venv')
}

Write-Step '安装后端与媒体分析依赖'
& $VenvPython -m pip install --upgrade pip
& $VenvPython -m pip install -e "$BackendDir[dev,media]"

Write-Step '运行后端测试'
Push-Location $BackendDir
try {
    & $VenvPython -m pytest -q
}
finally {
    Pop-Location
}

Write-Step '安装前端依赖并验证构建'
Push-Location $FrontendDir
try {
    & npm install
    & npm run build
}
finally {
    Pop-Location
}

Write-Step '检查可选视频工具'
$OptionalTools = @(
    @{ Name = 'ffmpeg'; Label = 'FFmpeg（最终剪辑/编码）' },
    @{ Name = 'ffprobe'; Label = 'FFprobe（视频信息检测）' },
    @{ Name = 'yt-dlp'; Label = 'yt-dlp（允许来源的视频获取）' },
    @{ Name = 'ollama'; Label = 'Ollama（本地模型，可选）' }
)
foreach ($Tool in $OptionalTools) {
    if (Get-Command $Tool.Name -ErrorAction SilentlyContinue) {
        Write-Host "[OK] $($Tool.Label)" -ForegroundColor Green
    }
    else {
        Write-Host "[可选/未安装] $($Tool.Label)" -ForegroundColor Yellow
    }
}

Write-Host "`n安装完成。" -ForegroundColor Green
Write-Host '接下来可以双击项目根目录的 START_WINDOWS.bat，或运行：'
Write-Host 'powershell -ExecutionPolicy Bypass -File .\scripts\dev.ps1' -ForegroundColor White
