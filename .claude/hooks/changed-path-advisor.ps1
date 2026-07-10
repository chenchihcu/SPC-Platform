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
$reviewers = [System.Collections.Generic.List[string]]::new()

# 路由定義正本: ..\skills\spc-change-router\route-table.json(2026-07-10 起 hook 改讀資料檔,
# 與 spc-change-router SKILL.md 的人類可讀表同源;改路由改 JSON,勿改回硬編碼)
$routeTablePath = Join-Path $PSScriptRoot "..\skills\spc-change-router\route-table.json"
$routeTable = $null
try {
    $routeTable = Get-Content -Raw -LiteralPath $routeTablePath -ErrorAction Stop | ConvertFrom-Json
} catch {}
if (-not $routeTable -or -not $routeTable.surfaces) {
    @{
        hookSpecificOutput = @{
            hookEventName     = "PostToolBatch"
            additionalContext = "SPC path advisor WARNING: route-table.json missing or unreadable ($routeTablePath). Path advisor is inactive until the data file is fixed."
        }
    } | ConvertTo-Json -Depth 8 -Compress
    exit 0
}

foreach ($path in $touched) {
    foreach ($surface in $routeTable.surfaces) {
        if ($path -match $surface.pathRegex) {
            foreach ($d in $surface.docs) { Add-Unique -List $docs -Value $d }
            if (-not [string]::IsNullOrWhiteSpace($surface.reviewer)) {
                Add-Unique -List $reviewers -Value $surface.reviewer
            }
            foreach ($g in $surface.gates) {
                $gateText = if (-not [string]::IsNullOrWhiteSpace($g.when)) { "$($g.cmd) ($($g.when))" } else { $g.cmd }
                Add-Unique -List $gates -Value $gateText
            }
            foreach ($n in $surface.notes) { Add-Unique -List $notes -Value $n }
        }
    }
}

# --- 舊硬編碼路由(2026-07-10 前行為,保留供回退比對;正本已移至 route-table.json) ---
# ui-theme:      (?i)(^|\\)app\\ui\\|(^|\\)app\\charts\\|AI_RULES\.md$
#                docs: AI_RULES.md, docs/specs/ui_state_semantics.md
#                gates: python scripts/qt_audit.py app/ ; python scripts/check_launch.py
# analytics:     (?i)(^|\\)app\\analytics\\|chart_registry\.py|docs\\governance\\SPC_RULES\.md$
#                docs: docs/governance/SPC_RULES.md, .claude/skills/analytics-engine-contract/SKILL.md
#                gates: python -m pytest -q ; run_matrix.py --quick / note: payload shape
# report-export: (?i)(^|\\)app\\services\\report_|pptx_report_builder\.py|diagnostic_excel_exporter\.py
#                docs: README.md, docs/specs/project_architecture.md / gates: pytest ; check_launch / note: parity
# docs-harness:  (?i)(^|\\)docs\\|AGENTS\.md$|CLAUDE\.md$|\.claude\\|scripts\\harness_check\.ps1
#                docs: AGENTS.md, docs/harness/README.md / gates: harness_check.ps1
# release:       (?i)(release|validation|golden_dataset|run_release_gate|release_check)
#                docs: docs/open-questions.md / gates: run_release_gate.py / note: Watchlist #7
# ---------------------------------------------------------------------------------

if ($docs.Count -eq 0 -and $gates.Count -eq 0 -and $notes.Count -eq 0) {
    exit 0
}

$contextLines = [System.Collections.Generic.List[string]]::new()
$contextLines.Add("SPC path advisor: do not auto-run full verification from hooks; choose explicit gates before completion.") | Out-Null
if ($docs.Count -gt 0) {
    $contextLines.Add("Read/confirm source docs: $($docs -join ', ')") | Out-Null
}
if ($reviewers.Count -gt 0) {
    $contextLines.Add("Prefer reviewer subagent: $($reviewers -join ', ')") | Out-Null
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
