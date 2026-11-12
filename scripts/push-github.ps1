# ============================================================================
# Push the local history to GitHub.
#
# Prerequisite (choose one):
#   A) SSH (recommended, no secret shared): the public key has been added at
#      https://github.com/settings/ssh/new and the repo already exists (empty!).
#   B) HTTPS + PAT: pass -Remote "https://<user>:<token>@github.com/<user>/<repo>.git"
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\push-github.ps1 -Remote "git@github.com:USER/REPO.git"
#   powershell -ExecutionPolicy Bypass -File scripts\push-github.ps1 -User NAME -Email MAIL
# ============================================================================
param(
    [string]$Remote = 'git@github.com:zhaoshuo/SmartDormLink.git',
    [string]$User = 'zhaoshuo',
    [string]$Email = 'zhaoshuo@users.noreply.github.com',
    [string]$KeyFile = "$env:USERPROFILE\.ssh\id_ed25519_dormlink"
)

$ErrorActionPreference = 'Continue'
$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

Write-Host '== configure identity' -ForegroundColor Cyan
git config user.name $User
git config user.email $Email

# The machine-level git config rewrites github.com to a dead proxy; neutralise it
# for this repository only, so HTTPS/SSH remotes are used as-is.
git config --unset-all url.https://gh-proxy.com/https://github.com/.insteadof 2>$null
git config --global --unset-all url.https://gh-proxy.com/https://github.com/.insteadof 2>$null

if (Test-Path $KeyFile) {
    Write-Host '== point this repo at the generated SSH key' -ForegroundColor Cyan
    git config core.sshCommand "ssh -i `"$KeyFile`" -o StrictHostKeyChecking=accept-new"
}

Write-Host '== remote' -ForegroundColor Cyan
$existing = git remote
if ($existing -contains 'origin') { git remote set-url origin $Remote } else { git remote add origin $Remote }
git remote -v

Write-Host '== verify auth' -ForegroundColor Cyan
if ($Remote -like 'git@*' -or $Remote -like 'ssh://*') {
    $probe = & ssh -i $KeyFile -o StrictHostKeyChecking=accept-new -o BatchMode=yes -T git@github.com 2>&1
    Write-Host ($probe | Select-Object -First 1)
} else {
    Write-Host '(https remote: credential prompt may appear in a GUI window)'
}

Write-Host '== push 20 commits' -ForegroundColor Cyan
git branch -M main
git push -u origin main
$code = $LASTEXITCODE

if ($code -eq 0) {
    Write-Host ''
    Write-Host 'PUSH OK. Next steps:' -ForegroundColor Green
    Write-Host '  1) open https://github.com/<user>/SmartDormLink and copy the URL'
    Write-Host '  2) fill the URL + your account name into README.md and report table 1.1'
} else {
    Write-Host ''
    Write-Host "PUSH FAILED (exit $code). Common causes:" -ForegroundColor Yellow
    Write-Host '  - repo does not exist yet  -> create an EMPTY repo on github.com first'
    Write-Host '  - key not authorised       -> add the .pub file at https://github.com/settings/ssh/new'
    Write-Host '  - proxy config             -> run: git config --global --unset url.https://gh-proxy.com/https://github.com/.insteadof'
}
exit $code
