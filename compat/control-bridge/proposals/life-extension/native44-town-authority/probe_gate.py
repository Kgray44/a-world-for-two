"""Small reusable fail-closed gate for future owned offline Java probes.

No CLI launch. The gate is evaluated inside the same Python call that can launch
the child, so a failed separate tool call cannot fall through to another command.
"""
from __future__ import annotations
import json
import subprocess

MIN_AVAILABLE=1610612736


class GateRefused(RuntimeError):
    def __init__(self,available):
        self.available=available
        super().__init__('Offline Java memory gate refused: '+repr(available))


def live_available():
    completed=subprocess.run(['powershell.exe','-NoProfile','-Command',
        '$awftOs=Get-CimInstance Win32_OperatingSystem; [long]$awftOs.FreePhysicalMemory*1024 | ConvertTo-Json -Compress'],
        capture_output=True,text=True,timeout=15,check=True,creationflags=0x08000000)
    return json.loads(completed.stdout)


def after_gate(gate,launch):
    available=gate()
    if type(available) is not int or available<=MIN_AVAILABLE:
        raise GateRefused(available)
    # Intentionally no finally/retry branch that could launch after refusal.
    return available,launch()


def run_java(command,*,timeout,gate=live_available,launcher=subprocess.run):
    if not command or command[0].replace('\\','/').lower() not in (
        'c:/program files/java/jdk-21.0.10/bin/java.exe','c:/program files/java/jdk-21.0.10/bin/javac.exe'):
        raise ValueError('Exact owned Java21 tool required')
    if not any(v in command for v in ('-Xmx64M','-Xmx256M','-J-Xmx64M','-J-Xmx256M')) or not 0<timeout<=60:
        raise ValueError('Explicit bounded heap and finite deadline required')
    if not any(v in command for v in ('-XX:ActiveProcessorCount=1','-XX:ActiveProcessorCount=2','-J-XX:ActiveProcessorCount=1','-J-XX:ActiveProcessorCount=2')):
        raise ValueError('Explicit one/two CPU bound required')
    return after_gate(gate,lambda:launcher(command,capture_output=True,text=True,timeout=timeout,creationflags=0x08000000|0x00004000))
