param(
    [string]$RepoRoot = "C:\Users\kucharsk\dev\hydropattern-gui"
)

$ErrorActionPreference = "Stop"
Set-Location $RepoRoot

uv sync --dev
uv run python -c "from pathlib import Path; from hydropattern_gui.packaging_cli import build_windows_executable; r=build_windows_executable(Path('.').resolve()); print(r.stdout)"
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller build failed."
}

Write-Host "Executable built at $RepoRoot\dist\hydropattern-gui.exe"
