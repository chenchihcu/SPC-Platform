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

if ($touched.Count -eq 0) {
    # Coarse markers are a fallback for unstructured input, never extra paths
    # inferred from a precise file_path (for example AGENTS.md.bak).
    $normalizedRaw = Normalize-PathText $rawInput
    foreach ($marker in @("app\", "tests\", "scripts\", "docs\", ".agents\", ".claude\", ".cursor\", ".codex\", "CLAUDE.md", "AGENTS.md")) {
        if ($normalizedRaw.Contains($marker)) {
            Add-Unique -List $touched -Value $marker
        }
    }
}

if ($touched.Count -eq 0) {
    exit 0
}

$docs = [System.Collections.Generic.List[string]]::new()
$gates = [System.Collections.Generic.List[string]]::new()
$notes = [System.Collections.Generic.List[string]]::new()
$reviewers = [System.Collections.Generic.List[string]]::new()

# Read the Claude projection of .agents/skills/spc-change-router/route-table.json.
# The harness checks projection parity; edit canonical JSON and both SKILL tables together.
$routeTablePath = Join-Path $PSScriptRoot "..\skills\spc-change-router\route-table.json"
try {
    $routeTable = Get-Content -Raw -Encoding UTF8 -LiteralPath $routeTablePath -ErrorAction Stop | ConvertFrom-Json
    if (-not $routeTable -or -not $routeTable.surfaces) {
        throw 'Route table has no surfaces.'
    }
    foreach ($path in $touched) {
        foreach ($surface in $routeTable.surfaces) {
            if ([string]::IsNullOrWhiteSpace($surface.pathRegex)) {
                throw 'Route surface has no pathRegex.'
            }
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
} catch {
    @{
        hookSpecificOutput = @{
            hookEventName     = "PostToolBatch"
            additionalContext = "SPC path advisor WARNING: route-table.json missing, unreadable, or invalid ($routeTablePath). Path advisor is inactive until the data file is fixed."
        }
    } | ConvertTo-Json -Depth 8 -Compress
    exit 0
}

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
