param(
    [ValidateSet('open','start','stop','install','repair','backup','diagnose','update','restore')]
    [string]$Action = 'open'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path -Parent $PSScriptRoot
$dataRoot = if ($env:AWFT_HOME) { $env:AWFT_HOME } else { 'D:\A World for Two' }
$guard = 'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1'
try {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $guard -EstimatedCBytes 67108864 -EstimatedDBytes 268435456
    if ($LASTEXITCODE -ne 0) { throw 'The 30 GiB storage reserve check rejected startup.' }
    $python = (Get-Command python -ErrorAction Stop).Source
    & $python -c 'import sys; assert sys.version_info >= (3,12); import psutil; assert psutil.__version__ == "7.2.2"'
    if ($LASTEXITCODE -ne 0) {
        if ($Action -ne 'install') { throw 'Double-click Install first to set up the pinned Python dependency.' }
        $venv = Join-Path $dataRoot 'runtime\python'
        $setupTemp = Join-Path $dataRoot 'runtime\setup-temp'
        New-Item -ItemType Directory -Path $setupTemp -Force | Out-Null
        $env:TEMP = $setupTemp
        $env:TMP = $setupTemp
        & $python -m venv --copies $venv
        if ($LASTEXITCODE -ne 0) { throw 'Python environment creation failed; Python 3.12 or later is required.' }
        $python = Join-Path $venv 'Scripts\python.exe'
        & $python -m pip install --disable-pip-version-check --no-cache-dir --require-hashes -r (Join-Path $PSScriptRoot 'requirements-windows.txt')
        if ($LASTEXITCODE -ne 0) { throw 'The pinned dependency could not be installed. See Diagnose.' }
    }
    $ownedPython = Join-Path $dataRoot 'runtime\python\Scripts\python.exe'
    if (Test-Path -LiteralPath $ownedPython) { $python = $ownedPython }
    $logs = Join-Path $dataRoot 'logs'
    New-Item -ItemType Directory -Path $logs -Force | Out-Null
    $stamp = Get-Date -Format 'yyyyMMdd-HHmmss-ffff'
    $route = if ($Action -eq 'update') { 'mods' } elseif ($Action -eq 'restore') { 'backups' } else { 'overview' }
    $command = if ($Action -in @('update','restore')) { 'open' } else { $Action }
    $arguments = @('-u', '-m', 'control_room', $command, '--home', ('"' + $dataRoot + '"'))
    Start-Process -FilePath $python -ArgumentList $arguments -WorkingDirectory $repo -WindowStyle Hidden `
        -RedirectStandardOutput (Join-Path $logs "control-room-$stamp.out.log") `
        -RedirectStandardError (Join-Path $logs "control-room-$stamp.err.log") | Out-Null
    Start-Process "http://127.0.0.1:8765/#$route"
} catch {
    Add-Type -AssemblyName System.Windows.Forms
    [System.Windows.Forms.MessageBox]::Show($_.Exception.Message, 'A World for Two', 'OK', 'Warning') | Out-Null
    exit 1
}
