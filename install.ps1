# Source-relative launcher; the shared installer owns all filesystem changes.
param([string]$Root = ".")

$ErrorActionPreference = "Stop"
$pythonCmd = $null
foreach ($candidate in @("python", "python3")) {
    # One command name can resolve to several PATH matches; validate each before deciding.
    foreach ($command in @(Get-Command $candidate -CommandType Application -ErrorAction SilentlyContinue)) {
        try {
            & $command.Source -I -B -c 'import sys; sys.exit(sys.version_info < (3, 8))' 2>$null | Out-Null
            if ($LASTEXITCODE -eq 0) {
                $pythonCmd = $command.Source
                break
            }
        } catch {
            # A command name or Windows app-execution alias is not a usable runtime.
        }
    }
    if ($pythonCmd) { break }
}
if (-not $pythonCmd) {
    [Console]::Error.WriteLine("installation failed: Python >= 3.8 required (tried python and python3); no files changed")
    exit 1
}

try {
    # Windows PowerShell must stream every native stderr line, including partial results.
    $ErrorActionPreference = "Continue"
    & $pythonCmd -I -B (Join-Path $PSScriptRoot "scripts/install.py") $Root
    exit $LASTEXITCODE
} catch {
    [Console]::Error.WriteLine("installation failed: " + $_.Exception.Message)
    exit 1
}
