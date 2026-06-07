Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Convert-ToHookJson {
    param(
        [string]$EventName,
        [string]$Context
    )

    @{
        hookSpecificOutput = @{
            hookEventName = $EventName
            additionalContext = $Context
        }
    } | ConvertTo-Json -Depth 8 -Compress
}

function Resolve-RepoRoot {
    if (-not [string]::IsNullOrWhiteSpace($env:CLAUDE_PROJECT_DIR)) {
        return $env:CLAUDE_PROJECT_DIR
    }
    return (Resolve-Path (Join-Path $PSScriptRoot "..\..")).Path
}

$repoRoot = Resolve-RepoRoot
$requiredFiles = @(
    "CLAUDE.md",
    "AGENTS.md",
    "AI_RULES.md",
    "scripts\check_launch.py",
    "scripts\verify.ps1",
    "docs\open-questions.md"
)

$missing = @()
foreach ($relativePath in $requiredFiles) {
    $path = Join-Path $repoRoot $relativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        $missing += $relativePath
    }
}

$pythonCandidate = Join-Path $repoRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $pythonCandidate -PathType Leaf)) {
    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($null -ne $pythonCommand) {
        $pythonCandidate = $pythonCommand.Source
    } else {
        $pythonCandidate = ""
    }
}

$parts = [System.Collections.Generic.List[string]]::new()
$parts.Add("SPC Claude preflight: repo=$repoRoot") | Out-Null
if ($missing.Count -gt 0) {
    $parts.Add("Missing required files: $($missing -join ', ')") | Out-Null
} else {
    $parts.Add("Required repo guardrail files are present.") | Out-Null
}
if ([string]::IsNullOrWhiteSpace($pythonCandidate)) {
    $parts.Add("Python candidate was not found; use scripts/verify.ps1 -PythonExe <path> if needed.") | Out-Null
} else {
    $parts.Add("Python candidate: $pythonCandidate") | Out-Null
}
$parts.Add("Do not run full verification automatically from hooks; use explicit task gates.") | Out-Null

Convert-ToHookJson -EventName "SessionStart" -Context ($parts -join "`n")
