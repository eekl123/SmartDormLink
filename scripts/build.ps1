# ============================================================================
# DormLink build helper (Windows PowerShell 5.1+ / PowerShell 7)
#
# Why this script exists:
#   hvigor refuses project paths containing non-ASCII characters, so when the
#   checkout lives in a path like "D:\<chinese>" the build is performed on an
#   ASCII working copy. On a normal ASCII-only checkout you can build directly
#   from DevEco Studio and ignore this script entirely.
#
# Usage:
#   powershell -ExecutionPolicy Bypass -File scripts\build.ps1                # debug HAP
#   powershell -ExecutionPolicy Bypass -File scripts\build.ps1 -Task test     # local unit test build
#   powershell -ExecutionPolicy Bypass -File scripts\build.ps1 -NoCopy        # build in place
# ============================================================================
param(
    [string]$Task = 'assembleHap',
    [switch]$NoCopy,
    [string]$WorkDir = 'C:\dsh_build\SmartDormLink',
    [string]$DevecoHome = 'E:\DevEco Studio'
)

$ErrorActionPreference = 'Stop'

$projectDir = Split-Path -Parent $PSScriptRoot
$utf8 = New-Object System.Text.UTF8Encoding($false)

function Write-Step([string]$Text) {
    Write-Host ("== " + $Text) -ForegroundColor Cyan
}

$nonAscii = $projectDir.ToCharArray() | Where-Object { [int]$_ -gt 127 }
$needCopy = (-not $NoCopy) -and ($null -ne $nonAscii)

$buildDir = $projectDir
if ($needCopy) {
    Write-Step "Project path contains non-ASCII chars, building from $WorkDir"
    if (Test-Path $WorkDir) { Remove-Item $WorkDir -Recurse -Force }
    New-Item -ItemType Directory -Path $WorkDir -Force | Out-Null
    robocopy $projectDir $WorkDir /E /XD node_modules oh_modules build .test .hvigor .git /NFL /NDL /NJH /NJS /NC /NS > $null
    if ($LASTEXITCODE -ge 8) { throw "robocopy failed with exit code $LASTEXITCODE" }
    $buildDir = $WorkDir
}

# --- locate DevEco bundled toolchain -----------------------------------------
$hvigorTools = Join-Path $DevecoHome 'tools\hvigor'
$nodeExe = Join-Path $DevecoHome 'tools\node\node.exe'
$jbrHome = Join-Path $DevecoHome 'jbr'
$sdkHome = Join-Path $DevecoHome 'sdk'
if (-not (Test-Path $nodeExe)) { throw "Bundled node not found: $nodeExe" }
if (-not (Test-Path (Join-Path $jbrHome 'bin\java.exe'))) { throw "Bundled JBR not found: $jbrHome" }

# --- link the bundled hvigor into the project (no network required) ----------
$ohosModules = Join-Path $buildDir 'node_modules\@ohos'
New-Item -ItemType Directory -Path $ohosModules -Force | Out-Null
foreach ($pkg in @('hvigor', 'hvigor-ohos-plugin')) {
    $link = Join-Path $ohosModules $pkg
    if (-not (Test-Path $link)) {
        cmd /c mklink /J "$link" "$hvigorTools\$pkg" > $null
    }
}

$env:DEVECO_SDK_HOME = $sdkHome
$env:JAVA_HOME = $jbrHome
$env:NODE_HOME = (Split-Path -Parent $nodeExe)
$env:NODE_PATH = (Join-Path $buildDir 'node_modules')
$env:PATH = "$jbrHome\bin;$env:NODE_HOME;$env:PATH"
if (-not $env:HVIGOR_USER_HOME) {
    $env:HVIGOR_USER_HOME = Join-Path $buildDir '.hvigor'
}

$hvigorJs = Join-Path $buildDir 'node_modules\@ohos\hvigor\bin\hvigor.js'
$args = @($hvigorJs, '--mode', 'module', '-p', 'product=default', $Task, '--no-daemon')

Write-Step "hvigor $Task (dir=$buildDir)"
# hvigor writes warnings to stderr; with ErrorActionPreference=Stop PowerShell 5.1
# would turn that into a terminating error, so relax it just for the native call.
$previousEap = $ErrorActionPreference
$ErrorActionPreference = 'Continue'
Push-Location $buildDir
try {
    & $nodeExe @args 2>&1 | ForEach-Object { Write-Host $_ }
    $code = $LASTEXITCODE
} finally {
    Pop-Location
    $ErrorActionPreference = $previousEap
}

if ($code -ne 0) { throw "hvigor failed with exit code $code" }

$hapDir = Join-Path $buildDir 'entry\build\default\outputs\default'
if (Test-Path $hapDir) {
    Get-ChildItem $hapDir -Filter *.hap | ForEach-Object {
        Write-Host ("HAP: " + $_.FullName + "  (" + [math]::Round($_.Length / 1KB, 1) + " KB)") -ForegroundColor Green
    }
}
exit 0
