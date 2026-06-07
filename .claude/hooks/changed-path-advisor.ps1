Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Add-Unique {
    param(
        [System.Collections.Generic.List[string]]$List,
        [string]$Value
    )
    if (-not [string]::IsNullOrWhiteSpace($Value) -and -not $List.Contains($Value)) {
        $List.Add($Value) | Out-Null
    }
}

function Normalize-PathText {
    param([string]$Value)
    return $Value.Replace("/", "\")
}

$rawInput = [Console]::In.ReadToEnd()
if ([string]::IsNullOrWhiteSpace($rawInput)) {
    exit 0
}

$touched = [System.Collections.Generic.List[string]]::new()
$pathRegex = '"(?:file_path|path)"\s*:\s*"([^"]+)"'
foreach ($match in [regex]::Matches($rawInput, $pathRegex)) {
    $path = $match.Groups[1].Value.Replace("\\", "\").Replace("\/", "/")
    Add-Unique -List $touched -Value (Normalize-PathText $path)
}

$normalizedRaw = Normalize-PathText $rawInput
foreach ($marker in @("app\", "tests\", "scripts\", "docs\", ".claude\", "CLAUDE.md", "AGENTS.md", "AI_RULES.md")) {
    if ($normalizedRaw.Contains($marker)) {
        Add-Unique -List $touched -Value $marker
    }
}

if ($touched.Count -eq 0) {
    exit 0
}

$docs = [System.Collections.Generic.List[string]]::new()
$gates = [System.Collections.Generic.List[string]]::new()
$notes = [System.Collections.Generic.List[string]]::new()

foreach ($path in $touched) {
    if ($path -match "(?i)(^|\\)app\\ui\\|(^|\\)app\\charts\\|AI_RULES\.md$") {
        Add-Unique -List $docs -Value "AI_RULES.md"
        Add-Unique -List $docs -Value "docs/specs/ui_state_semantics.md"
        Add-Unique -List $gates -Value "python scripts/qt_audit.py app/"
        Add-Unique -List $gates -Value "python scripts/check_launch.py"
    }
    if ($path -match "(?i)(^|\\)app\\analytics\\|chart_registry\.py|docs\\governance\\SPC_RULES\.md$") {
        Add-Unique -List $docs -Value "docs/governance/SPC_RULES.md"
        Add-Unique -List $docs -Value ".claude/skills/analytics-engine-contract/SKILL.md"
        Add-Unique -List $gates -Value "python -m pytest -q"
        Add-Unique -List $gates -Value "python .claude/skills/spc-validation-matrix/scripts/run_matrix.py --quick"
        Add-Unique -List $notes -Value "Preserve engine payload shape: chart_type, data, statistics, metadata."
    }
    if ($path -match "(?i)(^|\\)app\\services\\report_|pptx_report_builder\.py|diagnostic_excel_exporter\.py") {
        Add-Unique -List $docs -Value "README.md"
        Add-Unique -List $docs -Value "docs/specs/project_architecture.md"
        Add-Unique -List $gates -Value "python -m pytest -q"
        Add-Unique -List $gates -Value "python scripts/check_launch.py"
        Add-Unique -List $notes -Value "Check UI/report/PPTX/Excel evidence parity before completion."
    }
    if ($path -match "(?i)(^|\\)docs\\|AGENTS\.md$|CLAUDE\.md$|\.claude\\|scripts\\harness_check\.ps1") {
        Add-Unique -List $docs -Value "AGENTS.md"
        Add-Unique -List $docs -Value "docs/harness/README.md"
        Add-Unique -List $gates -Value "pwsh -NoProfile -ExecutionPolicy Bypass -File scripts/harness_check.ps1"
    }
    if ($path -match "(?i)(release|validation|golden_dataset|run_release_gate|release_check)") {
        Add-Unique -List $docs -Value "docs/open-questions.md"
        Add-Unique -List $gates -Value "python scripts/run_release_gate.py"
        Add-Unique -List $notes -Value "Keep Watchlist #7 numbering stable."
    }
}

if ($docs.Count -eq 0 -and $gates.Count -eq 0 -and $notes.Count -eq 0) {
    exit 0
}

$contextLines = [System.Collections.Generic.List[string]]::new()
$contextLines.Add("SPC path advisor: do not auto-run full verification from hooks; choose explicit gates before completion.") | Out-Null
if ($docs.Count -gt 0) {
    $contextLines.Add("Read/confirm source docs: $($docs -join ', ')") | Out-Null
}
if ($gates.Count -gt 0) {
    $contextLines.Add("Suggested verification: $($gates -join ' ; ')") | Out-Null
}
if ($notes.Count -gt 0) {
    $contextLines.Add("Notes: $($notes -join ' ')") | Out-Null
}

@{
    hookSpecificOutput = @{
        hookEventName = "PostToolBatch"
        additionalContext = ($contextLines -join "`n")
    }
} | ConvertTo-Json -Depth 8 -Compress
