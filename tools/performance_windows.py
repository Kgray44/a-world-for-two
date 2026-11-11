"""Small read-only Windows host sensors. Missing measurements remain unavailable."""
from __future__ import annotations

import ctypes
from ctypes import wintypes
import os


def memory_pressure():
    if os.name != 'nt':
        return {'available': False, 'reason': 'Windows sensor on another platform'}

    class Information(ctypes.Structure):
        _fields_ = [('cb', wintypes.DWORD)] + [(name, ctypes.c_size_t) for name in (
            'CommitTotal', 'CommitLimit', 'CommitPeak', 'PhysicalTotal', 'PhysicalAvailable',
            'SystemCache', 'KernelTotal', 'KernelPaged', 'KernelNonpaged', 'PageSize')]
        _fields_ += [(name, wintypes.DWORD) for name in ('HandleCount', 'ProcessCount', 'ThreadCount')]

    data = Information()
    data.cb = ctypes.sizeof(data)
    api = ctypes.WinDLL('psapi', use_last_error=True).GetPerformanceInfo
    api.argtypes = (ctypes.POINTER(Information), wintypes.DWORD)
    api.restype = wintypes.BOOL
    if not api(ctypes.byref(data), data.cb):
        return {'available': False, 'winerror': ctypes.get_last_error()}
    return {'available': True, 'commit_bytes': data.CommitTotal * data.PageSize,
            'commit_limit_bytes': data.CommitLimit * data.PageSize,
            'commit_peak_since_boot_bytes': data.CommitPeak * data.PageSize,
            'physical_available_bytes': data.PhysicalAvailable * data.PageSize,
            'physical_total_bytes': data.PhysicalTotal * data.PageSize,
            'commit_headroom_bytes': (data.CommitLimit - data.CommitTotal) * data.PageSize}


class PagingCounters:
    """PDH rates use successive observations, never a zero-filled first sample."""
    COUNTERS = {
        'pages_input_per_second': r'\Memory\Pages Input/sec',
        'page_read_operations_per_second': r'\Memory\Page Reads/sec',
        'disk_seconds_per_transfer_host': r'\PhysicalDisk(_Total)\Avg. Disk sec/Transfer',
    }

    def __init__(self):
        self.query, self.counters, self.errors = ctypes.c_void_p(), {}, {}
        self.api = None
        if os.name != 'nt':
            self.errors['all'] = 'Windows PDH unavailable'
            return
        try:
            self.api = ctypes.WinDLL('pdh')
            self.api.PdhOpenQueryW.argtypes = (wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p))
            self.api.PdhAddEnglishCounterW.argtypes = (ctypes.c_void_p, wintypes.LPCWSTR, ctypes.c_size_t, ctypes.POINTER(ctypes.c_void_p))
            self.api.PdhCollectQueryData.argtypes = (ctypes.c_void_p,)
            self.api.PdhCloseQuery.argtypes = (ctypes.c_void_p,)
            for name in ('PdhOpenQueryW', 'PdhAddEnglishCounterW', 'PdhCollectQueryData', 'PdhCloseQuery', 'PdhGetFormattedCounterValue'):
                getattr(self.api, name).restype = wintypes.LONG
            code = self.api.PdhOpenQueryW(None, 0, ctypes.byref(self.query))
            if code:
                raise OSError('PDH open status ' + str(code))
            for name, path in self.COUNTERS.items():
                handle = ctypes.c_void_p()
                code = self.api.PdhAddEnglishCounterW(self.query, path, 0, ctypes.byref(handle))
                if code:
                    self.errors[name] = 'PDH add status ' + str(code)
                else:
                    self.counters[name] = handle
            self.api.PdhCollectQueryData(self.query)
        except (OSError, AttributeError) as error:
            self.errors['all'] = type(error).__name__
            self.close()

    def sample(self):
        import math
        if self.api is None or not self.query.value:
            return {'available': False, 'errors': self.errors.copy()}

        class Value(ctypes.Structure):
            _fields_ = [('status', wintypes.DWORD), ('value', ctypes.c_double)]

        result = {'errors': self.errors.copy()}
        code = self.api.PdhCollectQueryData(self.query)
        if code:
            return {'available': False, 'errors': {'collect': str(code)}}
        api = self.api.PdhGetFormattedCounterValue
        api.argtypes = (ctypes.c_void_p, wintypes.DWORD, ctypes.POINTER(wintypes.DWORD), ctypes.POINTER(Value))
        for name, handle in self.counters.items():
            value = Value()
            code = api(handle, 0x200, None, ctypes.byref(value))  # PDH_FMT_DOUBLE
            if code or value.status not in (0, 1) or not math.isfinite(value.value) or value.value < 0:
                result['errors'][name] = 'PDH status ' + str(code or value.status)
            else:
                result[name] = value.value
        result['available'] = len(result) > 1
        return result

    def close(self):
        if self.api is not None and self.query.value:
            self.api.PdhCloseQuery(self.query)
            self.query = ctypes.c_void_p()
