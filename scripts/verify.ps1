param(
    [string]$PythonExe
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Add-UniqueCandidate {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Value
    )
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return
    }
    if (-not $List.Contains($Value)) {
        $List.Add($Value)
    }
}

function Get-UserProfilePath {
    if (-not [string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
        return $env:USERPROFILE
    }

    $fallback = [Environment]::GetFolderPath("UserProfile")
    if (-not [string]::IsNullOrWhiteSpace($fallback)) {
        return $fallback
    }

    return "C:\Users\user"
}

function Test-PythonRuntime {
    param([string]$PythonPath)

    if (-not (Test-Path -LiteralPath $PythonPath -PathType Leaf)) {
        return $false
    }

    try {
        & $PythonPath -V *> $null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        & $PythonPath -c "import PySide6, numpy, pandas, matplotlib" *> $null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        & $PythonPath -m ruff --version *> $null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        & $PythonPath -m mypy --version *> $null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        & $PythonPath -m pytest --version *> $null
        if ($LASTEXITCODE -ne 0) {
            return $false
        }
        return $true
    } catch {
        return $false
    }
}

function Resolve-PythonExe {
    param([string]$RepoRoot, [string]$Override)

    if (-not [string]::IsNullOrWhiteSpace($Override)) {
        if (Test-PythonRuntime -PythonPath $Override) {
            return $Override
        }
        throw "Python override path is invalid or missing required dependencies/tools: $Override"
    }

    $userProfilePath = Get-UserProfilePath
    $candidates = [System.Collections.Generic.List[string]]::new()
    Add-UniqueCandidate -List $candidates -Value (Join-Path $RepoRoot ".venv\Scripts\python.exe")
    Add-UniqueCandidate -List $candidates -Value (Join-Path $userProfilePath ".cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe")
    Add-UniqueCandidate -List $candidates -Value (Join-Path $userProfilePath "AppData\Local\Python\bin\python.exe")

    $pythonCmd = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCmd) {
        Add-UniqueCandidate -List $candidates -Value $pythonCmd.Source
    }

    foreach ($candidate in $candidates) {
        if (Test-PythonRuntime -PythonPath $candidate) {
            return $candidate
        }
    }

    throw "No valid python executable with PySide6/numpy/pandas/matplotlib and ruff/mypy/pytest found. Use -PythonExe <path>."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$userProfilePath = Get-UserProfilePath
if ([string]::IsNullOrWhiteSpace($env:USERPROFILE)) {
    $env:USERPROFILE = $userProfilePath
}
if ([string]::IsNullOrWhiteSpace($env:HOME)) {
    $env:HOME = $userProfilePath
}
$env:MPLCONFIGDIR = Join-Path $repoRoot ".matplotlib"
$resolvedPython = Resolve-PythonExe -RepoRoot $repoRoot -Override $PythonExe

Write-Host "Using Python: $resolvedPython"

Push-Location $repoRoot
try {
    $env:PYTHONPATH = $repoRoot
    $env:QT_QPA_PLATFORM = "offscreen"
    $env:MPLBACKEND = "Agg"

    Write-Host ""
    Write-Host "[1/6] python -m ruff check ."
    & $resolvedPython -m ruff check .
    if ($LASTEXITCODE -ne 0) {
        throw "ruff check failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "[2/6] python -m mypy app"
    & $resolvedPython -m mypy app
    if ($LASTEXITCODE -ne 0) {
        throw "mypy failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "[3/6] python -m pytest -q"
    & $resolvedPython -m pytest -q
    if ($LASTEXITCODE -ne 0) {
        throw "pytest failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "[4/6] python scripts/qt_audit.py app/"
    & $resolvedPython scripts/qt_audit.py app/
    if ($LASTEXITCODE -ne 0) {
        throw "qt_audit failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "[5/6] python scripts/check_launch.py"
    & $resolvedPython scripts/check_launch.py
    if ($LASTEXITCODE -ne 0) {
        throw "check_launch failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "[6/6] scripts\harness_check.ps1"
    & (Join-Path $repoRoot "scripts\harness_check.ps1")
    if ($LASTEXITCODE -ne 0) {
        throw "harness_check failed with exit code $LASTEXITCODE"
    }

    Write-Host ""
    Write-Host "Verification passed."
} finally {
    Pop-Location
}
