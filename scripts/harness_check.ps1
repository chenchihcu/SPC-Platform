Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
$failures = [System.Collections.Generic.List[string]]::new()
$skips = [System.Collections.Generic.List[string]]::new()

function Add-Failure {
    param([string]$Message)
    $script:failures.Add($Message) | Out-Null
}

function Add-Skip {
    param([string]$Message)
    $script:skips.Add($Message) | Out-Null
}

function Join-RepoPath {
    param([string]$RelativePath)
    return (Join-Path $repoRoot $RelativePath)
}

function Require-File {
    param([string]$RelativePath)
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Missing file: $RelativePath"
        return $false
    }
    return $true
}

function Require-Directory {
    param([string]$RelativePath)
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Container)) {
        Add-Failure "Missing directory: $RelativePath"
        return $false
    }
    return $true
}

function Require-Text {
    param(
        [string]$RelativePath,
        [string]$Text,
        [string]$Label
    )
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $RelativePath"
        return
    }

    $content = Get-Content -LiteralPath $path -Raw
    if (-not $content.Contains($Text)) {
        Add-Failure "Missing ${Label} in ${RelativePath}: $Text"
    }
}

function Require-NotText {
    param(
        [string]$RelativePath,
        [string]$Text,
        [string]$Label
    )
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $RelativePath"
        return
    }

    $content = Get-Content -LiteralPath $path -Raw
    if ($content.Contains($Text)) {
        Add-Failure "Forbidden ${Label} remains in ${RelativePath}: $Text"
    }
}

function Require-NormalizedSkillMirror {
    param(
        [string]$ClaudePath,
        [string]$AgentsPath,
        [string]$Label
    )
    $claudeFullPath = Join-RepoPath $ClaudePath
    $agentsFullPath = Join-RepoPath $AgentsPath
    if (-not (Test-Path -LiteralPath $claudeFullPath -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $ClaudePath"
        return
    }
    if (-not (Test-Path -LiteralPath $agentsFullPath -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $AgentsPath"
        return
    }

    $claudeContent = (
        Get-Content -LiteralPath $claudeFullPath |
            Where-Object { -not $_.StartsWith("allowed-tools:") }
    ) -join "`n"
    $agentsContent = (
        Get-Content -LiteralPath $agentsFullPath |
            Where-Object { -not $_.StartsWith("allowed-tools:") }
    ) -join "`n"
    if ($claudeContent -cne $agentsContent) {
        Add-Failure "${Label} drifted after removing Claude-only allowed-tools: $ClaudePath != $AgentsPath"
    }
}

function Require-ExactFileMirror {
    param(
        [string]$LeftPath,
        [string]$RightPath,
        [string]$Label
    )
    $leftFullPath = Join-RepoPath $LeftPath
    $rightFullPath = Join-RepoPath $RightPath
    if (-not (Test-Path -LiteralPath $leftFullPath -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $LeftPath"
        return
    }
    if (-not (Test-Path -LiteralPath $rightFullPath -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $RightPath"
        return
    }
    if ((Get-FileHash -Algorithm SHA256 -LiteralPath $leftFullPath).Hash -cne (Get-FileHash -Algorithm SHA256 -LiteralPath $rightFullPath).Hash) {
        Add-Failure "${Label} drifted: $LeftPath != $RightPath"
    }
}

function Require-SourceBaselineManifest {
    param([string]$RelativePath)
    $requiredTexts = @(
        "Source Baseline Manifest",
        "Purpose",
        "Inspection Commands",
        "Git Boundary Summary",
        "Tracked / Untracked / Ignored Summary",
        "File Classification",
        "Suspicious Items",
        "Baseline Commit Readiness",
        "Role Review Simulation",
        "Residual Risk",
        "Next Action",
        "source_baseline_status",
        "recommended-track-list",
        "recommended-ignore-list",
        "needs-user-decision-list",
        "do-not-track-list",
        "single writer per worktree",
        "local-observed",
        "audit-inference"
    )
    foreach ($text in $requiredTexts) {
        Require-Text $RelativePath $text "source baseline manifest required field"
    }
}

function Require-CodexRuleExamples {
    param([string]$RelativePath)
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Cannot check Codex rule examples; missing file: $RelativePath"
        return
    }

    $content = Get-Content -LiteralPath $path -Raw
    $ruleCount = [regex]::Matches($content, "prefix_rule\(").Count
    $matchCount = [regex]::Matches($content, "(?m)^\s*match\s*=\s*\[").Count
    $notMatchCount = [regex]::Matches($content, "(?m)^\s*not_match\s*=\s*\[").Count

    if ($ruleCount -eq 0) {
        Add-Failure "Codex command policy has no prefix_rule entries: $RelativePath"
    }
    if ($matchCount -ne $ruleCount) {
        Add-Failure "Codex command policy must include one match example per prefix_rule: $RelativePath"
    }
    if ($notMatchCount -ne $ruleCount) {
        Add-Failure "Codex command policy must include one not_match example per prefix_rule: $RelativePath"
    }
}

function Require-CodexPolicyParses {
    param([string]$RelativePath)
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Cannot parse Codex command policy; missing file: $RelativePath"
        return
    }

    $codexCommand = Get-Command codex -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($null -eq $codexCommand) {
        Add-Skip "Codex CLI not available; execpolicy parser check not executed."
        return
    }

    $policyCommands = @(
        ,@("python", "scripts/validate_db_chart_semantics.py")
        ,@(".venv/Scripts/python.exe", "scripts/validate_db_chart_semantics.py")
        ,@(".venv\Scripts\python.exe", "scripts\validate_db_chart_semantics.py")
    )
    foreach ($commandPrefix in $policyCommands) {
        $commandArgs = @(
            $commandPrefix[0],
            $commandPrefix[1],
            "--db",
            "data/spc_master.db",
            "--latest-session",
            "--output",
            "Outputs/db_chart_semantics_current",
            "--quiet"
        )
        Push-Location $repoRoot
        try {
            $policyOutput = & $codexCommand.Source execpolicy check --pretty --rules $path -- @commandArgs 2>&1
            $policyExitCode = $LASTEXITCODE
        }
        finally {
            Pop-Location
        }
        if ($policyExitCode -ne 0) {
            Add-Failure "Codex command policy parser failed for ${RelativePath}: $($policyOutput -join ' ')"
            return
        }
        if (-not (($policyOutput -join "`n").Contains('"decision": "allow"'))) {
            Add-Failure "Codex command policy did not allow prefix '$($commandPrefix -join ' ')': $RelativePath"
        }
    }
}

function Require-LineBudget {
    param(
        [string]$RelativePath,
        [int]$MaxLines,
        [string]$Label
    )
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $RelativePath"
        return
    }
    $lineCount = (Get-Content -LiteralPath $path).Count
    if ($lineCount -gt $MaxLines) {
        Add-Failure "${Label} exceeds ${MaxLines} lines: ${RelativePath} has ${lineCount} lines"
    }
}

function Require-ByteBudget {
    param(
        [string]$RelativePath,
        [int]$MaxBytes,
        [string]$Label
    )
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $RelativePath"
        return
    }
    $content = Get-Content -LiteralPath $path -Raw
    $byteCount = [System.Text.Encoding]::UTF8.GetByteCount($content)
    if ($byteCount -gt $MaxBytes) {
        Add-Failure "${Label} exceeds ${MaxBytes} bytes: ${RelativePath} has ${byteCount} bytes"
    }
}

function Require-CharBudget {
    param(
        [string]$RelativePath,
        [int]$MaxChars,
        [string]$Label
    )
    $path = Join-RepoPath $RelativePath
    if (-not (Test-Path -LiteralPath $path -PathType Leaf)) {
        Add-Failure "Cannot check ${Label}; missing file: $RelativePath"
        return
    }
    $content = Get-Content -LiteralPath $path -Raw
    if ($content.Length -gt $MaxChars) {
        Add-Failure "${Label} exceeds ${MaxChars} characters: ${RelativePath} has $($content.Length) characters"
    }
}

function Require-CursorRuleLineBudgets {
    $rulesDir = Join-RepoPath ".cursor\rules"
    if (-not (Test-Path -LiteralPath $rulesDir -PathType Container)) {
        Add-Failure "Cannot check Cursor rule line budgets; missing directory: .cursor\rules"
        return
    }
    Get-ChildItem -LiteralPath $rulesDir -Filter "*.mdc" | ForEach-Object {
        $lineCount = (Get-Content -LiteralPath $_.FullName).Count
        if ($lineCount -gt 500) {
            Add-Failure "Cursor rule exceeds official 500-line guidance: $($_.Name) has ${lineCount} lines"
        }
    }
}

$requiredFiles = @(
    "AGENTS.md",
    "CLAUDE.md",
    ".gitignore",
    ".agents\rules\agents_gateway.md",
    ".cursor\rules\agents_gateway.mdc",
    ".cursor\rules\ui_theme.mdc",
    ".cursor\rules\vibe-tools.mdc",
    ".claude\rules\ui_theme.md",
    ".codex\rules\project.rules",
    ".agents\skills\spc-db-chart-semantics-validator\SKILL.md",
    ".claude\skills\spc-db-chart-semantics-validator\SKILL.md",
    ".agents\skills\spc-change-router\SKILL.md",
    ".claude\skills\spc-change-router\SKILL.md",
    ".claude\skills\spc-change-router\route-table.json",
    ".agents\skills\spc-validation-matrix\SKILL.md",
    ".claude\skills\spc-validation-matrix\SKILL.md",
    ".agents\skills\spc-validation-matrix\scripts\run_matrix.py",
    ".claude\skills\spc-validation-matrix\scripts\run_matrix.py",
    "scripts\verify.ps1",
    "scripts\harness_check.ps1",
    "scripts\check_launch.py",
    "scripts\qt_audit.py",
    "scripts\run_release_gate.py",
    "scripts\validate_db_chart_semantics.py",
    "docs\governance\AGENTS.md",
    "docs\governance\SPC_RULES.md",
    "docs\open-questions.md",
    "docs\decision-log.md",
    "docs\harness\README.md",
    "docs\harness\ai-rules-compatibility.md",
    "docs\harness\source-baseline-manifest.md",
    "docs\harness\quality-score.md",
    "docs\harness\doc-gardening.md",
    "docs\harness\closed-loop-log.md",
    "docs\exec-plans\README.md",
    "docs\exec-plans\active\README.md",
    "docs\exec-plans\completed\README.md"
)

$requiredDirectories = @(
    ".agents",
    ".agents\rules",
    ".agents\skills\spc-db-chart-semantics-validator",
    ".claude\skills\spc-db-chart-semantics-validator",
    "docs\harness",
    "docs\exec-plans",
    "docs\exec-plans\active",
    "docs\exec-plans\completed"
)

foreach ($dir in $requiredDirectories) {
    Require-Directory $dir | Out-Null
}

foreach ($file in $requiredFiles) {
    Require-File $file | Out-Null
}

Require-Text "AGENTS.md" "## Knowledge Map" "repo knowledge map"
Require-Text "AGENTS.md" "## Closed-loop Harness" "closed-loop section"
Require-Text "AGENTS.md" "docs/open-questions.md" "active risk source pointer"
Require-Text "AGENTS.md" "docs/governance/SPC_RULES.md" "SPC authority pointer"
Require-Text "AGENTS.md" "scripts/harness_check.ps1" "harness check pointer"
Require-Text "AGENTS.md" "docs/harness/ai-rules-compatibility.md" "AI compatibility pointer"
Require-Text "AGENTS.md" "docs/harness/source-baseline-manifest.md" "source baseline manifest pointer"
Require-Text "AGENTS.md" "completion impact format" "completion impact format"
Require-Text "AGENTS.md" "Residual risk" "residual risk field"
Require-Text "AGENTS.md" "Source-Control Boundary" "source-control boundary rule"

Require-Text "CLAUDE.md" "@AGENTS.md" "Claude imports AGENTS policy"
Require-Text ".cursor\rules\agents_gateway.mdc" "](../../AGENTS.md)" "Cursor gateway uses a repo-relative AGENTS link"
Require-Text ".cursor\rules\agents_gateway.mdc" "alwaysApply: true" "Cursor gateway always-on"
Require-NotText ".cursor\rules\agents_gateway.mdc" "SPC%20platform%20v2" "stale Cursor repository path"
Require-Text ".cursor\rules\vibe-tools.mdc" "alwaysApply: false" "vibe-tools is not always-on"
Require-Text ".agents\rules\agents_gateway.md" "AGENTS.md" "Antigravity gateway points to AGENTS"
Require-Text ".agents\rules\agents_gateway.md" "New Worktree Mode" "Antigravity worktree preference"
Require-Text ".agents\rules\agents_gateway.md" "Local Mode" "Antigravity local mode boundary"
Require-Text ".agents\rules\agents_gateway.md" "L0/L1/M1/F1/F2" "Antigravity triage pointer"
Require-Text ".agents\rules\agents_gateway.md" "Traditional Chinese" "Antigravity Traditional Chinese output"

Require-Text "docs\governance\SPC_RULES.md" "Cp" "SPC rules content"
Require-Text "docs\open-questions.md" "Scope" "active risk scope field"
Require-Text "docs\open-questions.md" "Risk" "active risk risk field"
Require-Text "docs\open-questions.md" "Revalidation" "active risk revalidation field"

Require-Text "docs\harness\README.md" "repo-local system of record" "harness purpose"
Require-Text "docs\harness\README.md" "docs/open-questions.md" "harness active risk pointer"
Require-Text "docs\harness\ai-rules-compatibility.md" "AI Rules Compatibility Overview" "AI compatibility title"
Require-Text "docs\harness\ai-rules-compatibility.md" "Claim Type" "AI compatibility claim types"
Require-Text "docs\harness\ai-rules-compatibility.md" "Source Register" "AI compatibility source register"
Require-Text "docs\harness\ai-rules-compatibility.md" "Instruction Size Budget" "AI compatibility size budget"
Require-Text "docs\harness\ai-rules-compatibility.md" "project_doc_max_bytes" "Codex instruction byte limit"
Require-Text "docs\harness\ai-rules-compatibility.md" "32 KiB" "Codex default instruction budget"
Require-Text "docs\harness\ai-rules-compatibility.md" "200 lines" "Claude line guidance"
Require-Text "docs\harness\ai-rules-compatibility.md" "500 lines" "Cursor line guidance"
Require-Text "docs\harness\ai-rules-compatibility.md" "12,000 characters" "Antigravity character limit"
Require-Text "docs\harness\ai-rules-compatibility.md" "official" "AI compatibility official claim type"
Require-Text "docs\harness\ai-rules-compatibility.md" "local-observed" "AI compatibility local observed claim type"
Require-Text "docs\harness\ai-rules-compatibility.md" "audit-inference" "AI compatibility audit inference claim type"
Require-Text "docs\harness\ai-rules-compatibility.md" "not verified" "AI compatibility not verified claim type"
Require-Text "docs\harness\ai-rules-compatibility.md" "Source-Control RCA And Extended Risks" "source-control extended risks"
Require-Text "docs\harness\ai-rules-compatibility.md" "Source Control Boundary" "source-control boundary section"
Require-Text "docs\harness\ai-rules-compatibility.md" "Automation Readiness" "automation readiness section"
Require-Text "docs\harness\ai-rules-compatibility.md" "One Writer Protocol" "one-writer protocol section"
Require-Text "docs\harness\ai-rules-compatibility.md" "docs/harness/source-baseline-manifest.md" "source baseline manifest register"
Require-Text "docs\harness\ai-rules-compatibility.md" "one writer per worktree" "one-writer protocol"
Require-Text "docs\harness\ai-rules-compatibility.md" "New Worktree Mode" "Antigravity worktree protocol"
Require-SourceBaselineManifest "docs\harness\source-baseline-manifest.md"
Require-Text "docs\harness\quality-score.md" "Active risk control" "quality score active risk row"
Require-Text "docs\harness\doc-gardening.md" "Report only" "report-first automation rule"
Require-Text "docs\harness\doc-gardening.md" "Do not edit files from automation" "automation mutation boundary"
Require-Text "docs\harness\doc-gardening.md" "Changes observed" "automation changes field"
Require-Text "docs\harness\doc-gardening.md" "Impact" "automation impact field"
Require-Text "docs\harness\doc-gardening.md" "Verification status" "automation verification status field"
Require-Text "docs\harness\doc-gardening.md" "Residual risk" "automation residual risk field"
Require-Text "docs\harness\doc-gardening.md" "docs/harness/ai-rules-compatibility.md" "automation compatibility register surface"
Require-Text "docs\harness\doc-gardening.md" "docs/harness/source-baseline-manifest.md" "automation source baseline surface"
Require-Text "docs\harness\doc-gardening.md" "Source baseline manifest" "automation source baseline check"
Require-Text "docs\harness\doc-gardening.md" "Automation self-check" "automation self-check"
Require-Text "docs\harness\doc-gardening.md" ".agents/rules/agents_gateway.md" "automation Antigravity gateway surface"
Require-Text "docs\harness\doc-gardening.md" "AI rules size budget" "automation size budget check"
Require-Text "docs\harness\doc-gardening.md" "Source-control boundary" "automation source-control boundary check"
Require-Text "docs\harness\doc-gardening.md" "WindowsPowerShell" "automation full PowerShell path"
Require-Text "docs\harness\doc-gardening.md" "One-writer safety" "automation one-writer check"

Require-Text "docs\harness\closed-loop-log.md" "Changes:" "completion changes field"
Require-Text "docs\harness\closed-loop-log.md" "Impact:" "completion impact field"
Require-Text "docs\harness\closed-loop-log.md" "Verification:" "completion verification field"
Require-Text "docs\harness\closed-loop-log.md" "Residual risk:" "completion residual risk field"
Require-Text "docs\harness\closed-loop-log.md" "Next action:" "completion next action field"
Require-Text "docs\harness\closed-loop-log.md" "Debug/RCA (when applicable):" "debug RCA section"
Require-Text "docs\harness\closed-loop-log.md" "Observed:" "closed-loop observed field"
Require-Text "docs\harness\closed-loop-log.md" "Root cause:" "closed-loop root cause field"
Require-Text "docs\harness\closed-loop-log.md" "Fix:" "closed-loop fix field"
Require-Text "docs\harness\closed-loop-log.md" "Harness update needed:" "closed-loop harness update field"
Require-Text "docs\harness\closed-loop-log.md" "Destination:" "closed-loop destination field"

Require-Text "scripts\verify.ps1" "harness_check.ps1" "verify harness check call"
Require-Text ".codex\rules\project.rules" "harness_check.ps1" "project rule for harness check"
Require-Text ".codex\rules\project.rules" "scripts/verify.ps1" "project rule for verify"
Require-Text ".codex\rules\project.rules" "validate_db_chart_semantics.py" "project rule for DB semantic validation"
Require-Text ".codex\rules\project.rules" "match =" "Codex rule match examples"
Require-Text ".codex\rules\project.rules" "not_match =" "Codex rule not_match examples"
Require-Text ".codex\rules\project.rules" "WindowsPowerShell" "Codex rule supports full Windows PowerShell path"
Require-CodexRuleExamples ".codex\rules\project.rules"
Require-CodexPolicyParses ".codex\rules\project.rules"
Require-Text "scripts\validate_db_chart_semantics.py" "PRAGMA query_only = ON" "DB semantic validator query-only guard"
Require-Text "scripts\validate_db_chart_semantics.py" "EXPECTED_DENSITY_MODES" "DB semantic validator density assertion"
Require-Text "scripts\validate_db_chart_semantics.py" "_resolve_output_dir" "DB semantic validator Outputs boundary"
Require-Text "README.md" "validate_db_chart_semantics.py" "README DB semantic gate pointer"
Require-Text "docs\governance\AGENTS.md" "validate_db_chart_semantics.py" "governance DB semantic gate pointer"
Require-Text "docs\harness\README.md" "validate_db_chart_semantics.py" "harness DB semantic gate pointer"
Require-Text "docs\specs\project_architecture.md" "validate_db_chart_semantics.py" "architecture DB semantic gate pointer"
Require-Text ".claude\skills\spc-change-router\route-table.json" "validate_db_chart_semantics.py" "router DB semantic gate pointer"
Require-Text ".claude\skills\spc-change-router\SKILL.md" ".venv/Scripts/python.exe -m pytest -q" "router full analytics pytest gate"
Require-Text "CLAUDE.md" ".venv/Scripts/python.exe -m pytest -q" "Claude venv verification command"
Require-NormalizedSkillMirror ".claude\skills\spc-db-chart-semantics-validator\SKILL.md" ".agents\skills\spc-db-chart-semantics-validator\SKILL.md" "DB semantic validator skill mirror"
Require-NormalizedSkillMirror ".claude\skills\spc-change-router\SKILL.md" ".agents\skills\spc-change-router\SKILL.md" "change router skill mirror"
Require-NormalizedSkillMirror ".claude\skills\spc-validation-matrix\SKILL.md" ".agents\skills\spc-validation-matrix\SKILL.md" "validation matrix skill mirror"
Require-ExactFileMirror ".claude\skills\spc-validation-matrix\scripts\run_matrix.py" ".agents\skills\spc-validation-matrix\scripts\run_matrix.py" "validation matrix runner mirror"
Require-ByteBudget "AGENTS.md" 32768 "Codex AGENTS.md size budget"
Require-LineBudget "CLAUDE.md" 200 "Claude CLAUDE.md line budget"
Require-CursorRuleLineBudgets
Require-CharBudget ".agents\rules\agents_gateway.md" 12000 "Antigravity gateway character budget"
Require-Text ".gitignore" "Outputs/" "generated Outputs are ignored"
Require-Text ".gitignore" ".env" "local environment file is ignored"
Require-Text ".gitignore" "data/" "runtime data directory is ignored"
Require-Text ".gitignore" ".claude/settings.local.json" "Claude local settings are ignored"
Require-Text ".gitignore" ".claude/worktrees/" "Claude worktrees are ignored"
Require-Text ".gitignore" "!.cursor/rules/**" "Cursor shared rules are versionable"

if ($failures.Count -gt 0) {
    Write-Host "Harness check failed:"
    foreach ($failure in $failures) {
        Write-Host "- $failure"
    }
    exit 1
}

if ($skips.Count -gt 0) {
    Write-Host "Harness check passed with skips:"
    foreach ($skip in $skips) {
        Write-Host "- $skip"
    }
}
else {
    Write-Host "Harness check passed."
}
