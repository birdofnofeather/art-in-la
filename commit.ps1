<#
  commit.ps1 — one-command commit + sync helper for Art in LA.

  Usage:   .\commit.ps1 "your commit message"

  It: validates the data JSON files (so a corrupted file can't be committed),
  stages everything, commits, then pulls --rebase (auto-resolving the generated
  data files via the merge=ours rule) and pushes. Safe to re-run.
#>
param([Parameter(Mandatory = $true)][string]$Message)

$ErrorActionPreference = "Stop"
Set-Location -Path $PSScriptRoot

# 0) clear any stale lock from an interrupted git run
Remove-Item -Force ".git\index.lock" -ErrorAction SilentlyContinue
Remove-Item -Recurse -Force ".git\rebase-merge" -ErrorAction SilentlyContinue

# 1) refuse to commit invalid JSON data files
foreach ($f in @("public/data/venues.json","public/data/events.json","public/data/archive.json","public/data/scraped_venues.json")) {
  if (Test-Path $f) {
    try { Get-Content $f -Raw | ConvertFrom-Json | Out-Null }
    catch {
      Write-Host "ABORT: $f is not valid JSON. Restore it before committing:" -ForegroundColor Red
      Write-Host "       git checkout origin/main -- $f" -ForegroundColor Yellow
      exit 1
    }
  }
}

# 2) stage + commit (skip cleanly if nothing changed)
git add -A
git diff --cached --quiet
if ($LASTEXITCODE -eq 0) {
  Write-Host "Nothing to commit." -ForegroundColor Yellow
} else {
  git commit -m $Message
}

# 3) sync with origin then push
git pull --rebase origin main
git push origin main
Write-Host "`nDone — pushed to origin/main." -ForegroundColor Green
