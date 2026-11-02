param([string]$Python = "python")
$ErrorActionPreference = "Stop"
Set-Location -LiteralPath $PSScriptRoot
if (-not (Test-Path -LiteralPath ".venv\Scripts\python.exe")) {
    & $Python -m venv .venv
    if ($LASTEXITCODE -ne 0) { throw "Creating the Python environment failed." }
}
$BuildPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
& $BuildPython -m pip install -r requirements-dev.txt
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }
& $BuildPython -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed; no executable was built." }
& $BuildPython -I -m PyInstaller --noconfirm --clean DeepSeekCodeAgent.spec
if ($LASTEXITCODE -ne 0) { throw "Executable build failed." }
$SmokeOutput = Join-Path $PSScriptRoot ("build\package-check-" + [guid]::NewGuid().ToString('N'))
$BuiltExe = Join-Path $PSScriptRoot 'dist\DeepSeekCodeAgent.exe'
$SmokeProcess = Start-Process -FilePath $BuiltExe -ArgumentList @('--self-test', '--output', ('"' + $SmokeOutput + '"')) -WindowStyle Hidden -PassThru
if (-not $SmokeProcess.WaitForExit(60000)) {
    & taskkill /PID $SmokeProcess.Id /T /F | Out-Null
    throw "Packaged runtime self-test timed out."
}
$SmokeResult = Get-Content -LiteralPath (Join-Path $SmokeOutput 'self-test-result.json') -Raw | ConvertFrom-Json
if ($SmokeProcess.ExitCode -ne 0 -or -not $SmokeResult.success -or -not $SmokeResult.tls_transport_initialized) {
    throw "Packaged runtime self-test failed."
}
Write-Output "Built: $PSScriptRoot\dist\DeepSeekCodeAgent.exe"
