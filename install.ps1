# One-command install for Windows PowerShell. Copies config, templates, CI workflow, hook. Idempotent.
param([string]$Root = ".")

$ErrorActionPreference = "SilentlyContinue"

New-Item -ItemType Directory -Force -Path "$Root\scripts", "$Root\.github\workflows", "$Root\hooks" | Out-Null
Copy-Item "scripts\lane-config.yaml" "$Root\scripts\" -Force -ErrorAction SilentlyContinue
Copy-Item "scripts\lane.py", "scripts\evidence_check.py", "scripts\doctor.py" "$Root\scripts\" -Force -ErrorAction SilentlyContinue
Copy-Item ".github\workflows\sdlc-gate.yml" "$Root\.github\workflows\" -Force -ErrorAction SilentlyContinue
Copy-Item ".github\pull_request_template.md" "$Root\.github\" -Force -ErrorAction SilentlyContinue
Copy-Item "hooks\pre-push", "hooks\pre-push.sh", "hooks\pre-push.ps1" "$Root\hooks\" -Force -ErrorAction SilentlyContinue

$py = if (Get-Command python -ErrorAction SilentlyContinue) { "python" } else { "python3" }
& $py "$Root\scripts\doctor.py" --root "$Root"
