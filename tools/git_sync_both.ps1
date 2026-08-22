param(
    [string]$HelperPath = "D:\SNTalkBot-Complete-Package\ttuhelper",
    [string]$MainPath = "D:\SNTalkBot-Complete-Package\sntalkbot",
    [string]$Message = ""
)

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

function Invoke-Git([string]$RepoPath, [string[]]$Arguments) {
    Push-Location $RepoPath
    try {
        & git @Arguments
        if ($LASTEXITCODE -ne 0) {
            throw "git $($Arguments -join ' ') failed in $RepoPath (exit $LASTEXITCODE)"
        }
    }
    finally {
        Pop-Location
    }
}

function Sync-Repository([string]$RepoPath, [string]$Label, [string]$CommitMessage) {
    if (-not (Test-Path -LiteralPath $RepoPath -PathType Container)) {
        Write-Warning "$Label folder not found: $RepoPath -- skipping."
        return
    }
    if (-not (Test-Path -LiteralPath (Join-Path $RepoPath ".git") -PathType Container)) {
        Write-Warning "$Label is not initialized as a Git repository: $RepoPath -- skipping."
        return
    }

    Write-Host "=== $Label ==="
    Invoke-Git $RepoPath @("add", "-A")

    Push-Location $RepoPath
    try {
        & git diff --cached --quiet
        $hasChanges = ($LASTEXITCODE -ne 0)
    }
    finally { Pop-Location }

    if ($hasChanges) {
        Invoke-Git $RepoPath @("commit", "-m", $CommitMessage)
    }
    else {
        Write-Host "No local changes to commit."
    }

    # Rebase local commits on top of any remote updates before pushing.
    Invoke-Git $RepoPath @("pull", "--rebase")
    Invoke-Git $RepoPath @("push")
    Write-Host "$Label synchronized successfully."
}

if (-not (Get-Command git -ErrorAction SilentlyContinue)) {
    throw "Git was not found in PATH. Install Git for Windows first."
}

if ([string]::IsNullOrWhiteSpace($Message)) {
    $Message = "Update repositories $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
}

Sync-Repository -RepoPath $HelperPath -Label "TTUHelper" -CommitMessage $Message
Sync-Repository -RepoPath $MainPath -Label "SNTalkBot" -CommitMessage $Message

Write-Host "Done."
