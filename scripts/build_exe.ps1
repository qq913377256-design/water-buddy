param(
    [string]$Python = ""
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
Set-Location $ProjectRoot

if (-not $Python) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) {
        $Python = $pythonCommand.Source
    } else {
        $pyCommand = Get-Command py -ErrorAction SilentlyContinue
        if ($pyCommand) {
            $Python = $pyCommand.Source
        }
    }
}

if (-not $Python -or -not (Test-Path $Python)) {
    throw "Python executable not found. Pass it explicitly, for example: .\scripts\build_exe.ps1 -Python C:\Path\To\python.exe"
}

& $Python -m venv .venv
& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -e .
& .\.venv\Scripts\python.exe -m pip install -r requirements-build.txt
& .\.venv\Scripts\python.exe -m PyInstaller --noconfirm --clean --windowed --name WaterBuddy --paths src src\water_buddy\main.py

Write-Host "Built: dist\WaterBuddy\WaterBuddy.exe"
