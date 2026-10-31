param(
  [string]$Session = "mooctest",
  [string]$Url = "about:blank",
  [string]$Browser = "chrome",
  [int]$TimeoutSeconds = 30
)

$ErrorActionPreference = "Stop"
$npxCmd = (Get-Command npx.cmd -ErrorAction SilentlyContinue).Source
if (-not $npxCmd) {
  $npxCmd = (Get-Command npx -ErrorAction SilentlyContinue).Source
}
if (-not $npxCmd) {
  throw "npx not found"
}

$outFile = Join-Path $env:TEMP "pw-open-$Session.out.log"
$errFile = Join-Path $env:TEMP "pw-open-$Session.err.log"
$arguments = @("--no-install", "playwright-cli", "-s=$Session", "open", $Url, "--browser=$Browser")

Start-Process -FilePath $npxCmd -ArgumentList $arguments -WindowStyle Hidden `
  -RedirectStandardOutput $outFile -RedirectStandardError $errFile | Out-Null

$deadline = (Get-Date).AddSeconds($TimeoutSeconds)
while ((Get-Date) -lt $deadline) {
  Start-Sleep -Milliseconds 500
  $list = & $npxCmd --no-install playwright-cli list 2>&1 | Out-String
  if ($list -match [regex]::Escape($Session)) {
    Write-Output "OPENED $Session"
    exit 0
  }
}

Write-Error "Timed out waiting for Playwright session '$Session'. See $errFile"
exit 1
