<#
.SYNOPSIS
Open the loopback-only Control Room through an existing trusted SSH configuration.
.EXAMPLE
.\Connect-Snowfall.ps1 -SshHost snowfall -DashboardPort 8765
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory=$true)][ValidatePattern('^[A-Za-z0-9][A-Za-z0-9._-]{0,200}$')][string]$SshHost,
    [ValidateRange(1024,65535)][int]$DashboardPort = 8765,
    [ValidateRange(1,65535)][int]$SshPort = 22,
    [ValidatePattern('^[A-Za-z_][A-Za-z0-9_.-]{0,63}$')][string]$SshUser,
    [string]$IdentityFile,
    [switch]$NoBrowser
)
$ErrorActionPreference = 'Stop'
$reserveGuard = 'C:\Users\kkids\AppData\Local\AeroStorageWatch\ReserveGuard.ps1'
if (Test-Path -LiteralPath $reserveGuard) {
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $reserveGuard -EstimatedCBytes 1048576 -EstimatedDBytes 0
    if ($LASTEXITCODE -ne 0) { throw 'The AERO storage reserve check refused launcher logs.' }
}
$ssh = (Get-Command ssh.exe -ErrorAction Stop).Source
$probe = New-Object System.Net.Sockets.TcpListener([System.Net.IPAddress]::Loopback,$DashboardPort)
try { $probe.Start() } catch { throw "Local port $DashboardPort is already occupied. Close the prior tunnel/dashboard; do not open an unrelated service." } finally { $probe.Stop() }
$arguments = @('-N','-T','-p',"$SshPort",'-o','BatchMode=yes','-o','StrictHostKeyChecking=yes',
    '-o','ExitOnForwardFailure=yes','-o','ConnectTimeout=15','-o','ServerAliveInterval=15','-o','ServerAliveCountMax=3',
    '-L',"127.0.0.1:${DashboardPort}:127.0.0.1:${DashboardPort}")
if ($SshUser) { $arguments += @('-l',$SshUser) }
if ($IdentityFile) {
    $identity = (Resolve-Path -LiteralPath $IdentityFile).Path
    if ($identity -match '["\r\n\x00]') { throw 'The identity path contains unsupported characters.' }
    $arguments += @('-i',('"'+$identity+'"'))
}
$arguments += $SshHost
$start = New-Object System.Diagnostics.ProcessStartInfo
$start.FileName = $ssh
$start.Arguments = $arguments -join ' '
$start.UseShellExecute = $false
$start.CreateNoWindow = $true
$start.RedirectStandardError = $true
$process = New-Object System.Diagnostics.Process
$process.StartInfo = $start
$started = $false
try {
    [void]$process.Start()
    $started = $true
    # Drain asynchronously; SSH cannot block on a full diagnostics pipe.
    $errors = $process.StandardError.ReadToEndAsync()
    $deadline = [DateTime]::UtcNow.AddSeconds(25)
    $ready = $false
    while ([DateTime]::UtcNow -lt $deadline -and -not $process.HasExited) {
        try {
            $response = Invoke-RestMethod -Uri "http://127.0.0.1:$DashboardPort/api/bootstrap" -TimeoutSec 2
            if ($response.app_id -eq 'awft-control-room') { $ready = $true; break }
        } catch { Start-Sleep -Milliseconds 300 }
    }
    if (-not $ready) {
        if ($process.HasExited) {
            $detail = $errors.GetAwaiter().GetResult()
            throw "SSH could not establish the trusted tunnel. Check the SSH alias, verified host key, key/agent, network or Tailscale, and remote service. $detail"
        }
        throw 'SSH connected but Control Room did not answer. Verify the remote service and matching local/remote dashboard ports.'
    }
    $url = "http://127.0.0.1:$DashboardPort/"
    if (-not $NoBrowser) { Start-Process $url -WindowStyle Hidden }
    Write-Host "Control Room: $url"
    Write-Host 'Keep this launcher running. Ctrl+C closes only its SSH tunnel; the remote Minecraft service continues.'
    $process.WaitForExit()
    if ($process.ExitCode -ne 0) { throw ('SSH disconnected: '+$errors.GetAwaiter().GetResult()) }
} finally {
    # Terminate only the exact SSH process created here. No remote stop command.
    if ($started -and -not $process.HasExited) { $process.Kill(); $process.WaitForExit() }
    $process.Dispose()
}
