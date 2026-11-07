"""One dedicated, Windows-user-bound AI credential; never a character configuration.

The ciphertext lives outside the runtime home, exports and world backups. There
is no plaintext fallback and no ambient OPENAI_API_KEY discovery.
"""
from __future__ import annotations

import ctypes
import hashlib
import os
from pathlib import Path

from .common import UserError, atomic_write, contained

PREFIX = b'AWFT-DPAPI-1\0'
DEDICATED_ENV = 'SMARTVILLAGERS_API_KEY'


class _Blob(ctypes.Structure):
    _fields_ = [('size', ctypes.c_ulong), ('data', ctypes.POINTER(ctypes.c_ubyte))]


def _crypt(raw, entropy, decrypt=False):
    if os.name != 'nt':
        raise UserError('Secure credential entry requires Windows user-bound DPAPI; no plaintext credential was saved')
    raw_buffer = ctypes.create_string_buffer(raw)
    entropy_buffer = ctypes.create_string_buffer(entropy)
    source = _Blob(len(raw), ctypes.cast(raw_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    salt = _Blob(len(entropy), ctypes.cast(entropy_buffer, ctypes.POINTER(ctypes.c_ubyte)))
    result = _Blob()
    crypt32 = ctypes.WinDLL('crypt32', use_last_error=True)
    kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
    if decrypt:
        function = crypt32.CryptUnprotectData
        function.argtypes = [ctypes.POINTER(_Blob), ctypes.c_void_p, ctypes.POINTER(_Blob), ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_Blob)]
        ok = function(ctypes.byref(source), None, ctypes.byref(salt), None, None, 1, ctypes.byref(result))
    else:
        function = crypt32.CryptProtectData
        function.argtypes = [ctypes.POINTER(_Blob), ctypes.c_wchar_p, ctypes.POINTER(_Blob), ctypes.c_void_p,
                             ctypes.c_void_p, ctypes.c_ulong, ctypes.POINTER(_Blob)]
        ok = function(ctypes.byref(source), 'A World for Two dedicated OpenAI', ctypes.byref(salt), None, None, 1, ctypes.byref(result))
    function.restype = ctypes.c_int
    if not ok:
        raise UserError('Windows user-bound credential protection failed; no plaintext fallback was used')
    kernel32.LocalFree.argtypes = [ctypes.c_void_p]
    kernel32.LocalFree.restype = ctypes.c_void_p
    try:
        return ctypes.string_at(result.data, result.size)
    finally:
        kernel32.LocalFree(ctypes.cast(result.data, ctypes.c_void_p))


def _valid_key(value):
    if not isinstance(value, str) or not 20 <= len(value) <= 1024 or any(c.isspace() or ord(c) < 33 or ord(c) > 126 for c in value):
        raise UserError('Enter the dedicated OpenAI credential as one printable value; it was not logged or saved')
    return value


class CredentialStore:
    def __init__(self, layout, storage=None, root=None):
        self.layout, self.storage = layout, storage
        identity = hashlib.sha256(str(layout.home).casefold().encode('utf8')).hexdigest()[:24]
        self.root = Path(root) if root is not None else Path(os.environ.get('LOCALAPPDATA', str(Path.home() / 'AppData/Local'))) / 'AWorldForTwo/secrets'
        self.relative = identity + '/openai.dpapi'
        self.entropy = ('awft-dedicated-openai:' + identity).encode('ascii')

    @property
    def path(self):
        return contained(self.root, self.relative)

    def save(self, key):
        key = _valid_key(key)
        protected = _crypt(key.encode('utf8'), self.entropy)
        if len(protected) > 16384:
            raise UserError('Protected credential exceeds its finite allocation')
        if self.storage:
            self.storage.reserve(32768, self.root)
        atomic_write(self.path, PREFIX + protected)

    def load(self, environment=None):
        environment = os.environ if environment is None else environment
        dedicated = environment.get(DEDICATED_ENV)
        if dedicated:
            return _valid_key(dedicated), 'dedicated_environment'
        path = self.path
        if not path.is_file():
            return '', 'not_configured'
        if path.stat().st_size > 16384:
            raise UserError('Protected AI credential is unavailable; scripted mode remains available')
        raw = path.read_bytes()
        if not raw.startswith(PREFIX):
            raise UserError('Protected AI credential is unavailable; scripted mode remains available')
        try:
            key = _crypt(raw[len(PREFIX):], self.entropy, decrypt=True).decode('utf8')
            return _valid_key(key), 'windows_user_store'
        except (OSError, ValueError, UserError) as exc:
            raise UserError('Protected AI credential could not be opened for this Windows user; scripted mode remains available') from None

    def status(self):
        try:
            key, source = self.load()
            return {'configured': bool(key), 'source': source, 'error': None}
        except (OSError, ValueError, UserError):
            return {'configured': False, 'source': 'unavailable', 'error': 'Dedicated AI credential is unavailable; scripted mode remains available'}


def server_environment(layout, environment=None):
    """Only the dedicated server receives the credential; failure leaves scripted startup usable."""
    result = dict(os.environ if environment is None else environment)
    result.pop('OPENAI_API_KEY', None)
    try:
        key, _ = CredentialStore(layout).load(result)
        if key:
            result[DEDICATED_ENV] = key
        else:
            result.pop(DEDICATED_ENV, None)
    except (OSError, ValueError, UserError):
        result.pop(DEDICATED_ENV, None)
    return result
