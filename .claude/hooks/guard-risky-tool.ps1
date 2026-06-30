Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Read-HookInput {
    $raw = [Console]::In.ReadToEnd()
    if ([string]::IsNullOrWhiteSpace($raw)) {
        return $null
    }
    return $raw | ConvertFrom-Json
}

function Send-Decision {
    param(
        [ValidateSet("allow", "deny", "ask")]
        [string]$Decision,
        [string]$Reason
    )

    @{
        hookSpecificOutput = @{
            hookEventName = "PreToolUse"
            permissionDecision = $Decision
            permissionDecisionReason = $Reason
        }
    } | ConvertTo-Json -Depth 8 -Compress
}

function Get-ToolPath {
    param($ToolInput)

    $paths = [System.Collections.Generic.List[string]]::new()
    foreach ($name in @("file_path", "path")) {
        if ($null -ne $ToolInput -and $ToolInput.PSObject.Properties.Name -contains $name) {
            $value = [string]$ToolInput.$name
            if (-not [string]::IsNullOrWhiteSpace($value)) {
                $paths.Add($value.Replace("/", "\")) | Out-Null
            }
        }
    }
    return $paths
}

$event = Read-HookInput
if ($null -eq $event) {
    exit 0
}

$toolName = [string]$event.tool_name
$toolInput = $event.tool_input
$command = ""
if ($null -ne $toolInput -and $toolInput.PSObject.Properties.Name -contains "command") {
    $command = [string]$toolInput.command
}

if ($toolName -match "^(Bash|PowerShell)$") {
    $destructivePatterns = @(
        "(?i)\brm\s+-[^\r\n;]*r[^\r\n;]*f\b",
        "(?i)\b(Remove-Item|ri|rmdir|rd)\b[^\r\n;]*(-Recurse|-r\b)[^\r\n;]*(-Force|-f\b)",
        "(?i)\b(Remove-Item|ri|rmdir|rd)\b[^\r\n;]*(-Force|-f\b)[^\r\n;]*(-Recurse|-r\b)",
        "(?i)\bgit\s+reset\s+--hard\b",
        "(?i)\bgit\s+clean\s+-[^\r\n;]*[fdx]",
        "(?i)\bgit\s+checkout\s+--\b",
        "(?i)\bdel\s+/s\s+/q\b",
        "(?i)\bformat\s+[A-Z]:",
        "(?i)\bnetsh\s+(winsock|int)\s+.*\breset\b"
    )
    foreach ($pattern in $destructivePatterns) {
        if ($command -match $pattern) {
            Send-Decision -Decision "deny" -Reason "SPC guard: destructive or host-reset command blocked. Ask the user for an explicit recovery/destructive action before retrying."
            exit 0
        }
    }

    $dbWritePattern = "(?i)data[\\/][^`"'\s;]+\.db"
    $sqlWritePattern = "(?i)\b(insert|update|delete|drop|alter|truncate|vacuum|reindex|replace)\b"
    if ($command -match $dbWritePattern -and $command -match $sqlWritePattern) {
        Send-Decision -Decision "deny" -Reason "SPC guard: direct write against data/*.db is blocked. Use approved app services, migrations, or an explicit user-approved data operation."
        exit 0
    }
}

if ($toolName -match "^(Edit|MultiEdit|Write)$") {
    $paths = Get-ToolPath -ToolInput $toolInput
    foreach ($path in $paths) {
        if ($path -match "(?i)docs\\governance\\SPC_RULES\.md$") {
            Send-Decision -Decision "ask" -Reason "SPC guard: SPC_RULES.md is the statistical authority. Confirm this is an explicit formula/threshold/spec change before editing."
            exit 0
        }
        if ($path -match "(?i)docs\\open-questions\.md$") {
            Send-Decision -Decision "ask" -Reason "SPC guard: docs/open-questions.md is the active risk ledger. Confirm this risk-ledger edit is required for the current task."
            exit 0
        }
        if ($path -match "(?i)data\\[^\\]+\.db$") {
            Send-Decision -Decision "deny" -Reason "SPC guard: direct writes to data/*.db are blocked. Use app data services or approved scripts."
            exit 0
        }
    }
}

exit 0
