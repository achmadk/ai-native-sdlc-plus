# sdlc-pre-push (PowerShell / Windows)
# Advisory pre-push hook for Windows native git environments.
# It can inform and it never blocks: every path ends in exit 0.
# Enable: git config core.hooksPath hooks
# Silence: $env:SDLC_HOOK="off"; git push   or   git config sdlc.hook off

$ErrorActionPreference = "SilentlyContinue"

function Say($msg) {
    [Console]::Error.WriteLine("sdlc: $msg")
}

try {
    if ($env:SDLC_HOOK -eq "off") { exit 0 }
    $cfgHook = git config --get sdlc.hook 2>$null
    if ($cfgHook -eq "off") { exit 0 }

    # Check for python
    $pythonCmd = $null
    if (Get-Command python -ErrorAction SilentlyContinue) {
        $pythonCmd = "python"
    } elseif (Get-Command python3 -ErrorAction SilentlyContinue) {
        $pythonCmd = "python3"
    } else {
        Say "python not found; lane check skipped"
        exit 0
    }

    $root = git rev-parse --show-toplevel 2>$null
    if (-not $root) { exit 0 }

    $tool = Join-Path $root "scripts\evidence_check.py"
    $cfg = Join-Path $root "scripts\lane-config.yaml"
    if (-not (Test-Path $tool) -or -not (Test-Path $cfg)) {
        Say "gate scripts not found under scripts/; lane check skipped"
        exit 0
    }

    # Find default branch
    $defaultRef = git symbolic-ref -q --short refs/remotes/origin/HEAD 2>$null
    if (-not $defaultRef) {
        foreach ($candidate in @("origin/main", "origin/master")) {
            git rev-parse -q --verify "$candidate" 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $defaultRef = $candidate
                break
            }
        }
    }
    $defaultBranch = if ($defaultRef) { $defaultRef -replace "^origin/", "" } else { "" }

    # Read stdin lines from git pre-push
    $inputLines = [Console]::In.ReadToEnd() -split "`r?`n"
    foreach ($line in $inputLines) {
        if ([string]::IsNullOrWhiteSpace($line)) { continue }
        $parts = $line.Trim() -split "\s+"
        if ($parts.Count -lt 4) { continue }
        $localRef = $parts[0]
        $localSha = $parts[1]
        $remoteRef = $parts[2]
        $remoteSha = $parts[3]

        if (-not $localRef.StartsWith("refs/heads/")) { continue }
        if ($localSha -match "^0+$") { continue } # branch deletion

        $branch = $remoteRef -replace "^refs/heads/", ""
        if ($defaultBranch -and ($branch -eq $defaultBranch)) {
            Say "pushing straight to $branch: the PR gate does not run on direct pushes"
            continue
        }

        $base = ""
        if ($defaultRef) {
            $base = (git merge-base "$defaultRef" "$localSha" 2>$null).Trim()
        }
        if (-not $base) {
            Say "no merge-base with the default branch for $branch; lane check skipped"
            continue
        }

        $out = & $pythonCmd "$tool" --diff-only "--base=$base" "--head=$localSha" "--repo-root=$root" "--config=$cfg" 2>&1
        foreach ($outLine in $out) {
            [Console]::Error.WriteLine("sdlc: $outLine")
        }
    }
} catch {
    # Never block push
}

exit 0
